import hashlib
import hmac
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
import redis.asyncio as aioredis

from app.database import get_db
from app.redis_client import get_redis
from app.schemas.webhook import WhatsAppWebhookPayload
from app.services import auth as auth_service
from app.services import session as session_service
from app.services import message as message_service
from app.services import config as config_service
from app.services import commands as commands_service
from app.services.ai_pipeline import count_ai_today
from app.services.rate_limiter import check_rate_limit
from app.services.whatsapp import normalize_phone, send_whatsapp_message, send_whatsapp_buttons, send_whatsapp_cta_url, send_whatsapp_list
from app.services.session import clear_session
from app.models.user import User
from app.models.session import Session
from app.config import settings
from app.worker.tasks.message_tasks import process_message_task

router = APIRouter(prefix="/webhook", tags=["Webhook"])

_WEBHOOK_FLOOD_LIMIT = 60   # máx requests por IP por minuto (issue #8)


async def _check_webhook_flood(redis: aioredis.Redis, ip: str) -> bool:
    """Retorna True se IP excedeu o limite de requests por minuto."""
    key = f"webhook_flood:{ip}:{int(__import__('time').time() // 60)}"
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, 90)
    return count > _WEBHOOK_FLOOD_LIMIT


def _verify_whatsapp_signature(body: bytes, signature_header: str | None) -> bool:
    """Valida assinatura HMAC-SHA256 enviada pela Meta."""
    app_secret = getattr(settings, "WHATSAPP_APP_SECRET", "")
    if not app_secret:
        return False  # Sem segredo configurado, rejeita tudo
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(
        app_secret.encode(), body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header)


def extract_phone_and_message(payload: WhatsAppWebhookPayload) -> tuple[str | None, str | None]:
    """
    Extrai telefone e texto do payload da Meta WhatsApp Cloud API.
    Estrutura: entry[0].changes[0].value.messages[0]
    """
    try:
        entries = payload.entry or []
        for entry in entries:
            for change in entry.get("changes", []):
                value = change.get("value", {})
                messages = value.get("messages", [])
                for msg in messages:
                    if msg.get("from") == value.get("metadata", {}).get("phone_number_id"):
                        continue

                    raw_phone = msg.get("from")
                    if not raw_phone:
                        continue

                    phone = normalize_phone(raw_phone)
                    msg_type = msg.get("type", "")

                    if msg_type == "text":
                        text = msg.get("text", {}).get("body", "")
                        return phone, text

                    if msg_type == "interactive":
                        interactive = msg.get("interactive", {})
                        itype = interactive.get("type", "")
                        if itype == "button_reply":
                            text = interactive.get("button_reply", {}).get("id", "")
                            return phone, text
                        if itype == "list_reply":
                            text = interactive.get("list_reply", {}).get("id", "")
                            return phone, text

                    return phone, None
    except Exception:
        pass
    return None, None


@router.get("/whatsapp")
async def whatsapp_webhook_verify(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
):
    if hub_mode == "subscribe" and hub_verify_token == settings.WHATSAPP_VERIFY_TOKEN:
        return Response(content=hub_challenge, media_type="text/plain")
    return Response(content="Forbidden", status_code=403)


@router.post("/whatsapp")
async def whatsapp_webhook(
    request: Request,
    payload: WhatsAppWebhookPayload,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    client_ip = request.client.host if request.client else "unknown"
    if await _check_webhook_flood(redis, client_ip):
        return Response(content="Too Many Requests", status_code=429)

    body = await request.body()
    sig = request.headers.get("X-Hub-Signature-256")
    if not _verify_whatsapp_signature(body, sig):
        return Response(content="Unauthorized", status_code=401)

    if payload.object != "whatsapp_business_account":
        return {"status": "ignored", "object": payload.object}

    phone, message_text = extract_phone_and_message(payload)
    if not phone:
        return {"status": "ignored", "reason": "no phone extracted"}
    if message_text is None:
        return {"status": "ignored", "reason": "unsupported message type"}

    session_status = await session_service.get_session_status(redis, phone)

    if session_status != "autenticado":
        await auth_service.get_or_create_session(db, phone)
        token = await auth_service.create_login_token(db, phone)
        await session_service.set_session_status(redis, phone, "aguardando_login")
        login_url = f"{settings.APP_URL}/login?token={token.token}"
        await send_whatsapp_cta_url(
            phone=phone,
            body=(
                "👋 *Bem-vindo ao Assistente IA!*\n\n"
                "Para começar, toque no botão abaixo para fazer seu login.\n\n"
                f"⏱ _Link válido por {settings.LOGIN_TOKEN_EXPIRE_MINUTES} minutos._\n\n"
                "_Após o login, envie qualquer mensagem para conversar com a IA._"
            ),
            button_text="🔑 Fazer Login",
            url=login_url,
            footer="Oráculo IA",
        )
        return {"status": "ok", "authenticated": False}

    user_id_str = await session_service.get_session_user(redis, phone)
    user: User | None = None
    if user_id_str:
        result = await db.execute(select(User).where(User.id == user_id_str))
        user = result.scalar_one_or_none()

    sess_result = await db.execute(select(Session).where(Session.telefone == phone))
    sess_record = sess_result.scalar_one_or_none()
    if sess_record:
        ref = sess_record.last_activity or sess_record.authenticated_at
        if ref:
            ref_utc = ref if ref.tzinfo else ref.replace(tzinfo=timezone.utc)
            age = datetime.now(timezone.utc) - ref_utc
            expire_hours = getattr(settings, "WHATSAPP_SESSION_EXPIRE_HOURS", 24)
            if age > timedelta(hours=expire_hours):
                await session_service.set_session_status(redis, phone, "aguardando_login")
                await auth_service.get_or_create_session(db, phone)
                token = await auth_service.create_login_token(db, phone)
                login_url = f"{settings.APP_URL}/login?token={token.token}"
                reply = (
                    "⏳ *Sessão expirada por inatividade.*\n\n"
                    "Toque no botão abaixo para fazer login novamente.\n\n"
                    f"⏱ _Link válido por {settings.LOGIN_TOKEN_EXPIRE_MINUTES} minutos._"
                )
                await send_whatsapp_cta_url(
                    phone=phone,
                    body=reply,
                    button_text="🔑 Fazer Login",
                    url=login_url,
                    footer="Oráculo IA",
                )
                await message_service.log_message(db, phone, None, message_text or "", reply)
                return {"status": "ok", "session_expired": True}

    await db.execute(
        update(Session)
        .where(Session.telefone == phone)
        .values(last_activity=datetime.now(timezone.utc))
    )
    await db.commit()

    if not user:
        await session_service.set_session_status(redis, phone, "aguardando_login")
        await auth_service.get_or_create_session(db, phone)
        token = await auth_service.create_login_token(db, phone)
        login_url = f"{settings.APP_URL}/login?token={token.token}"
        reply = (
            "⚠️ *Sessão expirada.*\n\n"
            "Toque no botão abaixo para fazer login novamente.\n\n"
            f"⏱ _Link válido por {settings.LOGIN_TOKEN_EXPIRE_MINUTES} minutos._"
        )
        await send_whatsapp_cta_url(
            phone=phone,
            body=reply,
            button_text="🔑 Fazer Login",
            url=login_url,
            footer="Oráculo IA",
        )
        await message_service.log_message(db, phone, None, message_text or "", reply)
        return {"status": "ok", "session_expired": True}

    if user.status_conta != "ativo" or not user.is_active:
        reply = "⛔ Sua conta não está ativa. Entre em contato com o administrador."
        await send_whatsapp_message(phone, reply)
        return {"status": "ok", "account_inactive": True}

    config = await config_service.get_or_create_config(db, user.id)
    text = (message_text or "").strip()

    if not config.bot_ativo:
        reply = "🔇 *Bot desativado.*\n\nAcesse o painel web para reativá-lo em Configurações."
        await send_whatsapp_message(phone, reply)
        await message_service.log_message(db, phone, user.id, text, reply)
        return {"status": "ok", "bot_inactive": True}

    mensagens_hoje = await message_service.count_today(db, user.id)
    if mensagens_hoje >= config.limite_diario:
        reply = (
            f"⛔ *Limite diário atingido.*\n\n"
            f"Você usou {config.limite_diario} mensagens hoje. "
            "Volte amanhã ou contate o administrador para ampliar o limite."
        )
        await send_whatsapp_message(phone, reply)
        await message_service.log_message(db, phone, user.id, text, reply)
        return {"status": "ok", "limit_reached": True}

    if commands_service.is_command(text):
        reply = await commands_service.handle_command(text, user, config, mensagens_hoje)
        if reply == "__LOGOUT__":
            await clear_session(redis, phone)
            nome = config.nome_assistente if config else "Assistente"
            msg = (
                f"👋 Até logo! Você foi desconectado do *{nome}*.\n\n"
                "_Envie qualquer mensagem quando quiser se reconectar._"
            )
            await send_whatsapp_message(phone, msg)
            await message_service.log_message(db, phone, user.id, text, msg)
            return {"status": "ok", "type": "logout"}

        if reply == "__LIST_MENU__":
            nome = config.nome_assistente if config else "Assistente"
            await send_whatsapp_list(
                phone=phone,
                title=f"🤖 {nome}",
                description="Olá! Sou seu assistente com IA. O que deseja fazer?",
                button_text="Ver opções",
                footer="Oráculo IA",
                sections=[
                    {
                        "title": "Comandos",
                        "rows": [
                            {"title": "📊 Status", "description": "Ver seu uso do dia", "rowId": "status"},
                            {"title": "⚙️ Configurações", "description": "Ver configurações do bot", "rowId": "config"},
                            {"title": "❓ Ajuda", "description": "Como usar o sistema", "rowId": "ajuda"},
                            {"title": "🚪 Sair", "description": "Desconectar do assistente", "rowId": "sair"},
                        ],
                    }
                ],
            )
            await message_service.log_message(db, phone, user.id, text, "[menu enviado]")
            return {"status": "ok", "type": "command"}

        if reply:
            await send_whatsapp_message(phone, reply)
            await message_service.log_message(db, phone, user.id, text, reply)
            return {"status": "ok", "type": "command"}

    allowed, rate_msg = await check_rate_limit(redis, str(user.id))
    if not allowed:
        await send_whatsapp_message(phone, rate_msg)
        await message_service.log_message(db, phone, user.id, text, rate_msg)
        return {"status": "ok", "rate_limited": True}

    if config.ia_ativa:
        ia_hoje = await count_ai_today(db, user.id)
        if ia_hoje >= config.limite_ia_diario:
            reply = (
                f"⛔ *Limite de IA atingido.*\n\n"
                f"Você usou {config.limite_ia_diario} consultas de IA hoje. "
                "O limite será resetado amanhã."
            )
            await send_whatsapp_message(phone, reply)
            await message_service.log_message(db, phone, user.id, text, reply)
            return {"status": "ok", "ia_limit_reached": True}

        config_data = {
            "email": user.email,
            "nome": user.nome,
            "perfil": user.perfil,
            "bot_ativo": config.bot_ativo,
            "ia_ativa": config.ia_ativa,
            "limite_diario": config.limite_diario,
            "limite_ia_diario": config.limite_ia_diario,
            "nivel_detalhe": config.nivel_detalhe,
            "nome_assistente": config.nome_assistente,
            "idioma": config.idioma,
        }

        ack = f"⏳ _{config.nome_assistente} está processando sua consulta..._"
        await send_whatsapp_message(phone, ack)

        process_message_task.apply_async(
            kwargs={
                "phone": phone,
                "text": text,
                "user_id": str(user.id),
                "config_data": config_data,
            }
        )
        return {"status": "ok", "type": "queued"}
    else:
        reply = (
            f"👋 Olá! Sou o *{config.nome_assistente}*.\n\n"
            "🔇 A inteligência artificial está desativada para sua conta.\n"
            "Acesse o painel web em *Configurações* para reativá-la.\n\n"
            "_Digite *menu* para ver os comandos disponíveis._"
        )
        await send_whatsapp_message(phone, reply)
        await message_service.log_message(db, phone, user.id, text, reply)
        return {"status": "ok", "type": "default_reply"}

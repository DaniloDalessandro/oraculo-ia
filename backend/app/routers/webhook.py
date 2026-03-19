from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
import redis.asyncio as aioredis

from app.database import get_db
from app.redis_client import get_redis
from app.schemas.webhook import EvolutionWebhookPayload
from app.services import auth as auth_service
from app.services import session as session_service
from app.services import message as message_service
from app.services import config as config_service
from app.services import commands as commands_service
from app.services.ai_pipeline import count_ai_today
from app.services.rate_limiter import check_rate_limit
from app.services.whatsapp import normalize_phone, send_whatsapp_message, send_whatsapp_buttons, send_whatsapp_cta_url, send_whatsapp_list
from app.models.user import User
from app.models.session import Session
from app.config import settings
from app.worker.tasks.message_tasks import process_message_task

router = APIRouter(prefix="/webhook", tags=["Webhook"])

MESSAGE_EVENTS = {"messages.upsert", "MESSAGES_UPSERT"}


def extract_phone_and_message(
    payload: EvolutionWebhookPayload,
) -> tuple[str | None, str | None]:
    data = payload.data or {}
    key = data.get("key", {})
    raw_phone = key.get("remoteJid") or data.get("remoteJid")
    if not raw_phone:
        return None, None
    if "g.us" in raw_phone:
        return None, None
    if key.get("fromMe"):
        return None, None
    phone = normalize_phone(raw_phone)
    message_obj = data.get("message", {})
    text = (
        message_obj.get("conversation")
        or message_obj.get("extendedTextMessage", {}).get("text")
        # Resposta de lista interativa (sendList)
        or message_obj.get("listResponseMessage", {}).get("singleSelectReply", {}).get("selectedRowId")
        # Resposta de botão nativo (sendButtons)
        or message_obj.get("buttonsResponseMessage", {}).get("selectedButtonId")
        or ""
    )
    return phone, text


@router.post("/whatsapp")
async def whatsapp_webhook(
    payload: EvolutionWebhookPayload,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    event = payload.event or ""
    if event and event not in MESSAGE_EVENTS:
        return {"status": "ignored", "event": event}

    phone, message_text = extract_phone_and_message(payload)
    if not phone:
        return {"status": "ignored", "reason": "no phone extracted"}

    session_status = await session_service.get_session_status(redis, phone)

    # ── Não autenticado ──────────────────────────────────────────────────────
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

    # ── Busca usuário ────────────────────────────────────────────────────────
    user_id_str = await session_service.get_session_user(redis, phone)
    user: User | None = None
    if user_id_str:
        result = await db.execute(select(User).where(User.id == user_id_str))
        user = result.scalar_one_or_none()

    await db.execute(
        update(Session)
        .where(Session.telefone == phone)
        .values(last_activity=datetime.now(timezone.utc))
    )
    await db.commit()

    if not user:
        reply = "⚠️ *Sessão expirada.*\n\nEnvie qualquer mensagem para receber um novo link de acesso."
        await send_whatsapp_message(phone, reply)
        await session_service.set_session_status(redis, phone, "nao_autenticado")
        await message_service.log_message(db, phone, None, message_text or "", reply)
        return {"status": "ok", "session_expired": True}

    # ── Conta inativa ou desativada ──────────────────────────────────────────
    if user.status_conta != "ativo" or not user.is_active:
        reply = "⛔ Sua conta não está ativa. Entre em contato com o administrador."
        await send_whatsapp_message(phone, reply)
        return {"status": "ok", "account_inactive": True}

    config = await config_service.get_or_create_config(db, user.id)
    text = (message_text or "").strip()

    # ── Bot desativado ───────────────────────────────────────────────────────
    if not config.bot_ativo:
        reply = "🔇 *Bot desativado.*\n\nAcesse o painel web para reativá-lo em Configurações."
        await send_whatsapp_message(phone, reply)
        await message_service.log_message(db, phone, user.id, text, reply)
        return {"status": "ok", "bot_inactive": True}

    # ── Limite diário de mensagens ───────────────────────────────────────────
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

    # ── Comandos pré-definidos ───────────────────────────────────────────────
    if commands_service.is_command(text):
        reply = await commands_service.handle_command(text, user, config, mensagens_hoje)
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

    # ── Rate limiting por minuto ─────────────────────────────────────────────
    allowed, rate_msg = await check_rate_limit(redis, str(user.id))
    if not allowed:
        await send_whatsapp_message(phone, rate_msg)
        await message_service.log_message(db, phone, user.id, text, rate_msg)
        return {"status": "ok", "rate_limited": True}

    # ── Processamento com IA via Celery ──────────────────────────────────────
    if config.ia_ativa:
        # Verifica limite diário específico de IA
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

        # Serializa config para Celery (não pode passar objetos ORM)
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

        # Envia ack imediato e processa em background
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
        # IA desativada: resposta padrão
        reply = (
            f"👋 Olá! Sou o *{config.nome_assistente}*.\n\n"
            "🔇 A inteligência artificial está desativada para sua conta.\n"
            "Acesse o painel web em *Configurações* para reativá-la.\n\n"
            "_Digite *menu* para ver os comandos disponíveis._"
        )
        await send_whatsapp_message(phone, reply)
        await message_service.log_message(db, phone, user.id, text, reply)
        return {"status": "ok", "type": "default_reply"}

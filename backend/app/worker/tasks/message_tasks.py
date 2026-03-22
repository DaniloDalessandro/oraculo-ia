"""
Task Celery: processamento assíncrono de mensagens com IA.

Fluxo:
  webhook (fast) → enfileira process_message_task → worker executa pipeline IA → responde WhatsApp
"""

import asyncio
import time

from celery import Task
from celery.exceptions import SoftTimeLimitExceeded

from app.worker.celery_app import celery_app
from app.services.structured_logger import celery_logger, log_event


class _AsyncTask(Task):
    """Base para tasks que executam código async via asyncio.run()."""

    def run_async(self, coro):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
            asyncio.set_event_loop(None)


@celery_app.task(
    bind=True,
    base=_AsyncTask,
    name="app.worker.tasks.message_tasks.process_message_task",
    queue="fila_ia",
    max_retries=3,
    default_retry_delay=5,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=30,
)
def process_message_task(
    self,
    phone: str,
    text: str,
    user_id: str,
    config_data: dict,
):
    """
    Processa uma mensagem com IA e envia resposta via WhatsApp.

    Args:
        phone: número WhatsApp normalizado
        text: mensagem do usuário
        user_id: UUID do usuário como string
        config_data: dict com campos de UserConfig
    """
    start = time.time()
    log_event(celery_logger, "task_started",
              task_id=self.request.id, phone=phone, user_id=user_id)
    try:
        self.run_async(_async_process(phone, text, user_id, config_data))
        duration_ms = int((time.time() - start) * 1000)
        log_event(celery_logger, "task_completed",
                  task_id=self.request.id, duration_ms=duration_ms)
    except SoftTimeLimitExceeded:
        log_event(celery_logger, "task_soft_timeout", level="warning",
                  task_id=self.request.id, phone=phone)
        try:
            asyncio.run(_send_timeout_message(phone))
        except Exception:
            pass
        raise
    except Exception as exc:
        # Se esgotou todas as retries, notifica o usuário (issue #7)
        if self.request.retries >= self.max_retries:
            log_event(celery_logger, "task_failed_permanently", level="error",
                      task_id=self.request.id, phone=phone, error=str(exc))
            try:
                asyncio.run(_send_error_message(phone))
            except Exception:
                pass
        raise


async def _async_process(
    phone: str,
    text: str,
    user_id: str,
    config_data: dict,
) -> None:
    """Async core do processamento: DB + Redis + IA + WhatsApp."""
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from sqlalchemy import select
    import redis.asyncio as aioredis
    import uuid as uuid_module

    from app.config import settings
    from app.models.user import User
    from app.models.user_config import UserConfig
    # Importar todos os modelos relacionados para que o SQLAlchemy configure os mappers corretamente
    from app.models.session import Session  # noqa: F401
    from app.models.login_token import LoginToken  # noqa: F401
    from app.models.message import Message  # noqa: F401
    from app.models.ai_query_log import AIQueryLog  # noqa: F401
    from app.models.venda import Venda  # noqa: F401
    from app.services import message as message_service
    from app.services.ai_pipeline import process_ai_message
    from app.services.cache import get_cached, set_cached
    from app.services.whatsapp import send_whatsapp_message

    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    AsyncSess = async_sessionmaker(engine, expire_on_commit=False)
    redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

    try:
        async with AsyncSess() as db:
            # Reconstrói objetos User e UserConfig a partir dos dados serializados
            user = User()
            user.id = uuid_module.UUID(user_id)
            user.email = config_data.get("email", "")
            user.nome = config_data.get("nome")
            user.perfil = config_data.get("perfil", "cliente")

            config = UserConfig()
            config.user_id = uuid_module.UUID(user_id)
            config.bot_ativo = config_data.get("bot_ativo", True)
            config.ia_ativa = config_data.get("ia_ativa", True)
            config.limite_diario = config_data.get("limite_diario", 100)
            config.limite_ia_diario = config_data.get("limite_ia_diario", 50)
            config.nivel_detalhe = config_data.get("nivel_detalhe", "normal")
            config.nome_assistente = config_data.get("nome_assistente", "Assistente")
            config.idioma = config_data.get("idioma", "pt-BR")

            # Cache check
            cached = await get_cached(redis, user_id, text)
            if cached:
                await send_whatsapp_message(phone, cached)
                await message_service.log_message(db, phone, user.id, text, cached)
                return

            # Processa com IA
            reply = await process_ai_message(
                db=db,
                redis=redis,
                user=user,
                config=config,
                telefone=phone,
                question=text,
            )

            # Armazena no cache apenas respostas válidas (não erros)
            from app.services.ai_pipeline import _ERR_AI_FAILED, _ERR_SQL_EXEC, _ERR_TIMEOUT
            if reply not in (_ERR_AI_FAILED, _ERR_SQL_EXEC, _ERR_TIMEOUT):
                await set_cached(redis, user_id, text, reply)

            # Envia resposta e registra no histórico de mensagens
            await send_whatsapp_message(phone, reply)
            await message_service.log_message(db, phone, user.id, text, reply)
    finally:
        await redis.aclose()
        await engine.dispose()


async def _send_timeout_message(phone: str) -> None:
    from app.services.whatsapp import send_whatsapp_message
    await send_whatsapp_message(
        phone,
        "⏱ Sua consulta demorou muito para processar. "
        "Por favor, reformule a pergunta e tente novamente."
    )


async def _send_error_message(phone: str) -> None:
    from app.services.whatsapp import send_whatsapp_message
    await send_whatsapp_message(
        phone,
        "⚠️ Não consegui processar sua mensagem após várias tentativas. "
        "Por favor, tente novamente em alguns instantes."
    )

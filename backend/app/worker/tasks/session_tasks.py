"""
Task Celery periódica: expira sessões WhatsApp inativas.
Executada via Celery Beat a cada hora.
"""

import asyncio

from app.worker.celery_app import celery_app
from app.services.structured_logger import celery_logger, log_event


@celery_app.task(
    name="app.worker.tasks.session_tasks.expire_sessions_task",
    queue="fila_mensagens",
)
def expire_sessions_task():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        expired = loop.run_until_complete(_async_expire())
        log_event(celery_logger, "sessions_expired", count=expired)
        return expired
    finally:
        loop.close()
        asyncio.set_event_loop(None)


async def _async_expire() -> int:
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    # Importa todos os modelos para configurar os mappers corretamente
    from app.models.user import User  # noqa: F401
    from app.models.session import Session  # noqa: F401
    from app.models.login_token import LoginToken  # noqa: F401
    from app.models.message import Message  # noqa: F401
    from app.models.audit_log import AuditLog  # noqa: F401
    from app.services.auth import expire_whatsapp_sessions
    from app.config import settings

    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    AsyncSess = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with AsyncSess() as db:
            return await expire_whatsapp_sessions(db)
    finally:
        await engine.dispose()

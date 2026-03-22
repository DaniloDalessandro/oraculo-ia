import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app.redis_client import close_redis, init_redis
from app.routers import admin, ai_logs, auth, dashboard, health, messages, settings as settings_router, webhook

import app.models.audit_log  # noqa: F401

logger = logging.getLogger(__name__)


_APP_URL_REDIS_KEY = "app:frontend_url"


async def _create_initial_admin():
    """Cria o admin inicial se nenhum usuário existir e ADMIN_EMAIL estiver configurado."""
    if not settings.ADMIN_EMAIL or not settings.ADMIN_SENHA:
        return
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy import select, func
    from app.models.user import User
    from app.core.security import hash_password
    async with engine.begin() as conn:
        result = await conn.execute(select(func.count()).select_from(User.__table__))
        count = result.scalar()
    if count and count > 0:
        return
    from app.database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        admin = User(
            email=settings.ADMIN_EMAIL,
            senha_hash=hash_password(settings.ADMIN_SENHA),
            nome="Admin",
            perfil="administrador",
            status_conta="ativo",
            is_active=True,
        )
        session.add(admin)
        await session.commit()
    logger.info("Admin inicial criado: %s", settings.ADMIN_EMAIL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await _create_initial_admin()
    await init_redis()

    from app.redis_client import get_redis as _get_redis
    _redis = await _get_redis()
    try:
        cached_url = await _redis.get(_APP_URL_REDIS_KEY)
        if cached_url:
            settings.APP_URL = cached_url
            logger.info("APP_URL restaurado do Redis: %s", cached_url)
    except Exception as exc:
        logger.warning("Não foi possível restaurar APP_URL do Redis: %s", exc)

    _DUMMY = {"changeme", "dev-secret-key-change-in-production-32chars!!",
               "seu-token-aqui", "seu-phone-number-id-aqui", "um-token-secreto-qualquer", ""}
    _critical = {
        "SECRET_KEY": settings.SECRET_KEY,
        "WHATSAPP_TOKEN": settings.WHATSAPP_TOKEN,
        "WHATSAPP_PHONE_NUMBER_ID": settings.WHATSAPP_PHONE_NUMBER_ID,
    }
    for name, val in _critical.items():
        if val in _DUMMY:
            logger.warning("AVISO: %s nao foi configurado. Funcionalidades podem falhar.", name)

    # Valida AI_PROVIDER (issue #13)
    _valid_providers = {"groq", "gemini", "openai"}
    if settings.AI_PROVIDER not in _valid_providers:
        logger.warning(
            "AI_PROVIDER='%s' é inválido. Use: %s. Usando 'openai' como fallback.",
            settings.AI_PROVIDER, ", ".join(_valid_providers)
        )

    # Valida alinhamento de timeouts (issue #15)
    if settings.AI_TIMEOUT_SECONDS >= settings.CELERY_TASK_SOFT_TIME_LIMIT:
        logger.warning(
            "AI_TIMEOUT_SECONDS (%ds) deve ser menor que CELERY_TASK_SOFT_TIME_LIMIT (%ds).",
            settings.AI_TIMEOUT_SECONDS, settings.CELERY_TASK_SOFT_TIME_LIMIT
        )

    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        logger.warning(
            "SMTP nao configurado (SMTP_USER/SMTP_PASSWORD vazios). "
            "Funcionalidades de e-mail (recuperacao de senha, notificacoes) estao desativadas."
        )

    yield
    await close_redis()
    await engine.dispose()


app = FastAPI(
    title="Oraculo IA — Backend",
    description="Sistema de chatbot corporativo com WhatsApp + IA",
    version="0.5.0",
    lifespan=lifespan,
)

_cors_origins = [
    "http://localhost:3001",
    "http://localhost:3000",
    settings.APP_URL,
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(set(_cors_origins)),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

app.include_router(health.router)
app.include_router(webhook.router)
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(dashboard.router)
app.include_router(settings_router.router)
app.include_router(messages.router)
app.include_router(ai_logs.router)

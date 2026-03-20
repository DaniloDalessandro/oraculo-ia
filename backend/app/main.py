import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app.redis_client import close_redis, init_redis
from app.routers import admin, ai_logs, auth, dashboard, health, messages, settings as settings_router, webhook

# Garante que todos os modelos estão registrados no metadata antes do create_all
import app.models.audit_log  # noqa: F401

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await init_redis()

    # Item 11: valida configuração SMTP na inicialização
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(webhook.router)
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(dashboard.router)
app.include_router(settings_router.router)
app.include_router(messages.router)
app.include_router(ai_logs.router)

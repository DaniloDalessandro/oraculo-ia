from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.redis_client import close_redis, init_redis
from app.routers import ai_logs, auth, dashboard, health, messages, settings, webhook


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await init_redis()
    yield
    await close_redis()
    await engine.dispose()


app = FastAPI(
    title="Oraculo IA — Backend",
    description="Sistema de chatbot corporativo com WhatsApp + IA",
    version="0.4.0",
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
app.include_router(dashboard.router)
app.include_router(settings.router)
app.include_router(messages.router)
app.include_router(ai_logs.router)

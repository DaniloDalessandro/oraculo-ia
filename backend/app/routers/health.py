from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
import redis.asyncio as aioredis

from app.config import settings
from app.redis_client import get_redis

router = APIRouter(tags=["Health"])

_APP_URL_REDIS_KEY = "app:frontend_url"


@router.get("/health")
async def health():
    return {"status": "ok", "service": "oraculo-backend"}


class AppUrlPayload(BaseModel):
    url: str


@router.get("/internal/app-url")
async def get_app_url(
    authorization: str | None = Header(default=None),
    redis: aioredis.Redis = Depends(get_redis),
):
    """Retorna APP_URL atual (chamado pelo administrador para diagnóstico)."""
    expected = f"Bearer {settings.SECRET_KEY}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")
    cached = await redis.get(_APP_URL_REDIS_KEY)
    return {"app_url": settings.APP_URL, "redis_url": cached}


@router.post("/internal/set-app-url")
async def set_app_url(
    payload: AppUrlPayload,
    authorization: str | None = Header(default=None),
    redis: aioredis.Redis = Depends(get_redis),
):
    """Atualiza APP_URL em memória e Redis (chamado pelo tunnel ao iniciar)."""
    expected = f"Bearer {settings.SECRET_KEY}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")

    settings.APP_URL = payload.url
    await redis.set(_APP_URL_REDIS_KEY, payload.url)
    return {"status": "ok", "app_url": settings.APP_URL}

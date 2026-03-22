from fastapi import APIRouter
from pydantic import BaseModel
from app.config import settings

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health():
    return {"status": "ok", "service": "oraculo-backend"}


class AppUrlPayload(BaseModel):
    url: str


@router.post("/internal/set-app-url")
async def set_app_url(payload: AppUrlPayload):
    """Atualiza APP_URL em memória (chamado pelo tunnel ao iniciar)."""
    settings.APP_URL = payload.url
    return {"status": "ok", "app_url": settings.APP_URL}

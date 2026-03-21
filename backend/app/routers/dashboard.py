import httpx
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import redis.asyncio as aioredis

from app.core.dependencies import get_current_administrador
from app.database import get_db
from app.redis_client import get_redis
from app.models.user import User
from app.models.session import Session, SessionStatus
from app.models.ai_query_log import AIQueryLog
from app.schemas.dashboard import DashboardStats, RecentMessage
from app.services import message as message_service
from app.services.cache import get_cache_stats
from app.config import settings
from app.worker.celery_app import celery_app

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


async def check_whatsapp_connected() -> bool:
    """Verifica conectividade com WhatsApp Cloud API via Graph API."""
    try:
        url = (
            f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}"
            f"/{settings.WHATSAPP_PHONE_NUMBER_ID}"
            "?fields=display_phone_number,verified_name"
        )
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(
                url,
                headers={"Authorization": f"Bearer {settings.WHATSAPP_TOKEN}"},
            )
            return resp.status_code == 200
    except Exception:
        pass
    return False


def _count_active_workers() -> int:
    try:
        inspect = celery_app.control.inspect(timeout=1.0)
        active = inspect.active()
        return len(active) if active else 0
    except Exception:
        return 0


@router.get("/stats", response_model=DashboardStats)
async def get_stats(
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
    current_user: User = Depends(get_current_administrador),
):
    total_mensagens = await message_service.get_total(db)
    mensagens_hoje = await message_service.get_today_total(db)

    result = await db.execute(
        select(func.count(Session.id)).where(Session.status == SessionStatus.autenticado)
    )
    usuarios_ativos = result.scalar_one() or 0

    recentes = await message_service.get_recent(db, limit=5)
    ultimas = [
        RecentMessage(
            telefone=m.telefone,
            mensagem_usuario=m.mensagem_usuario,
            resposta_sistema=m.resposta_sistema,
            created_at=m.created_at,
        )
        for m in recentes
    ]

    whatsapp_conectado = await check_whatsapp_connected()

    # Sprint 4: métricas de IA de hoje
    from datetime import date, datetime, timezone
    today_start = datetime.combine(date.today(), datetime.min.time()).replace(tzinfo=timezone.utc)

    r_ia_hoje = await db.execute(
        select(func.count(AIQueryLog.id)).where(AIQueryLog.created_at >= today_start)
    )
    total_ia_hoje = r_ia_hoje.scalar_one() or 0

    r_tempo = await db.execute(
        select(func.avg(AIQueryLog.tempo_execucao_ms)).where(
            AIQueryLog.created_at >= today_start,
            AIQueryLog.erro.is_(None),
        )
    )
    tempo_medio = float(r_tempo.scalar_one() or 0.0)

    r_erros = await db.execute(
        select(func.count(AIQueryLog.id)).where(
            AIQueryLog.created_at >= today_start,
            AIQueryLog.erro.isnot(None),
        )
    )
    total_erros = r_erros.scalar_one() or 0
    taxa_erro = round((total_erros / total_ia_hoje * 100) if total_ia_hoje else 0.0, 1)

    # Cache stats
    cache_stats = await get_cache_stats(redis)
    hits = cache_stats.get("hits", 0)
    misses = cache_stats.get("misses", 0)
    total_cache = hits + misses
    cache_hit_rate = round((hits / total_cache * 100) if total_cache else 0.0, 1)

    workers_ativos = _count_active_workers()

    return DashboardStats(
        total_mensagens=total_mensagens,
        usuarios_ativos=usuarios_ativos,
        mensagens_hoje=mensagens_hoje,
        whatsapp_conectado=whatsapp_conectado,
        ultimas_mensagens=ultimas,
        total_ia_hoje=total_ia_hoje,
        tempo_medio_resposta_ms=round(tempo_medio, 1),
        taxa_erro_ia_pct=taxa_erro,
        workers_ativos=workers_ativos,
        cache_hit_rate=cache_hit_rate,
    )

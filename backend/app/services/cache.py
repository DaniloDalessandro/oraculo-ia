"""
Cache de respostas IA no Redis.

Evita reprocessar a mesma pergunta dentro do TTL configurado.
Chave: ai_cache:{user_id}:{md5(pergunta_normalizada)}
"""

import hashlib

import redis.asyncio as aioredis

from app.config import settings
from app.services.structured_logger import ai_logger, log_event


def _make_key(user_id: str, question: str) -> str:
    normalized = question.lower().strip()
    q_hash = hashlib.md5(normalized.encode()).hexdigest()
    return f"ai_cache:{user_id}:{q_hash}"


async def get_cached(
    redis: aioredis.Redis, user_id: str, question: str
) -> str | None:
    if not settings.AI_CACHE_ENABLED:
        return None
    key = _make_key(user_id, question)
    cached = await redis.get(key)
    if cached:
        log_event(ai_logger, "cache_hit", user_id=user_id, key=key)
    return cached


async def set_cached(
    redis: aioredis.Redis,
    user_id: str,
    question: str,
    response: str,
    ttl: int | None = None,
) -> None:
    if not settings.AI_CACHE_ENABLED:
        return
    key = _make_key(user_id, question)
    effective_ttl = ttl or settings.AI_CACHE_TTL_SECONDS
    await redis.set(key, response, ex=effective_ttl)
    log_event(ai_logger, "cache_set", user_id=user_id, ttl=effective_ttl)


async def invalidate_user_cache(redis: aioredis.Redis, user_id: str) -> int:
    """Remove todas as entradas de cache de um usuário."""
    pattern = f"ai_cache:{user_id}:*"
    keys = await redis.keys(pattern)
    if keys:
        await redis.delete(*keys)
    return len(keys)


async def get_cache_stats(redis: aioredis.Redis) -> dict:
    """Retorna estatísticas de uso do cache para o dashboard."""
    try:
        info = await redis.info("stats")
        hits = info.get("keyspace_hits", 0)
        misses = info.get("keyspace_misses", 0)
        total = hits + misses
        hit_rate = round(hits / total * 100, 1) if total > 0 else 0.0
        return {"hits": hits, "misses": misses, "hit_rate_pct": hit_rate}
    except Exception:
        return {"hits": 0, "misses": 0, "hit_rate_pct": 0.0}

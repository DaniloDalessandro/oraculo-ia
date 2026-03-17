"""
Rate limiting por usuário via Redis.

Janela deslizante de 1 minuto usando INCR + EXPIRE.
Permite burst configurável acima do limite base.
"""

import time

import redis.asyncio as aioredis

from app.config import settings
from app.services.structured_logger import webhook_logger, log_event


async def check_rate_limit(
    redis: aioredis.Redis, user_id: str
) -> tuple[bool, str]:
    """
    Verifica se o usuário está dentro do rate limit por minuto.

    Returns:
        (permitido: bool, mensagem_erro: str)
    """
    window = int(time.time() // 60)
    key = f"rate:minute:{user_id}:{window}"

    count = await redis.incr(key)
    if count == 1:
        # Primeiro request nesta janela — define expiração
        await redis.expire(key, 70)  # 10s de tolerância

    limit = settings.RATE_LIMIT_PER_MINUTE + settings.RATE_LIMIT_BURST

    if count > limit:
        log_event(
            webhook_logger,
            "rate_limit_exceeded",
            level="warning",
            user_id=user_id,
            count=count,
            limit=limit,
        )
        return False, (
            f"Voce enviou muitas mensagens. "
            f"Limite: {settings.RATE_LIMIT_PER_MINUTE} por minuto. "
            "Aguarde um momento e tente novamente."
        )

    return True, ""


async def get_minute_usage(redis: aioredis.Redis, user_id: str) -> int:
    """Retorna quantas mensagens o usuário enviou no minuto atual."""
    window = int(time.time() // 60)
    key = f"rate:minute:{user_id}:{window}"
    val = await redis.get(key)
    return int(val) if val else 0

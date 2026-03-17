from typing import Optional
import redis.asyncio as aioredis
from app.config import settings

_redis_client: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    return _redis_client


async def init_redis() -> None:
    global _redis_client
    _redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)


async def close_redis() -> None:
    if _redis_client:
        await _redis_client.aclose()

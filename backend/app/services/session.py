from typing import Optional
import redis.asyncio as aioredis

SESSION_TTL_SECONDS = 86400 * 7  # 7 dias


async def get_session_status(redis: aioredis.Redis, phone: str) -> str:
    status = await redis.get(f"session:{phone}:status")
    return status or "nao_autenticado"


async def set_session_status(redis: aioredis.Redis, phone: str, status: str) -> None:
    await redis.set(f"session:{phone}:status", status, ex=SESSION_TTL_SECONDS)


async def get_session_user(redis: aioredis.Redis, phone: str) -> Optional[str]:
    return await redis.get(f"session:{phone}:user_id")


async def set_session_user(redis: aioredis.Redis, phone: str, user_id: str) -> None:
    await redis.set(f"session:{phone}:user_id", user_id, ex=SESSION_TTL_SECONDS)


async def clear_session(redis: aioredis.Redis, phone: str) -> None:
    await redis.delete(f"session:{phone}:status", f"session:{phone}:user_id")

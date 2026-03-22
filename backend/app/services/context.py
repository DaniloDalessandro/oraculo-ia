"""
Contexto conversacional por usuário armazenado no Redis.
Mantém os últimos N pares de (pergunta, resposta) para enriquecer
o prompt da IA com histórico recente.
"""

import json
from typing import Any

import redis.asyncio as aioredis

CONTEXT_TTL_SECONDS = 3600  # 1 hora de inatividade limpa o contexto


async def get_context(redis: aioredis.Redis, user_id: str) -> list[dict[str, str]]:
    """Retorna lista de mensagens no formato [{role, content}, ...]."""
    raw = await redis.get(f"ai_context:{user_id}")
    if not raw:
        return []
    try:
        return json.loads(raw)
    except Exception:
        return []


async def add_to_context(
    redis: aioredis.Redis,
    user_id: str,
    question: str,
    answer: str,
    max_pairs: int = 5,
) -> None:
    """Adiciona novo par ao contexto, mantendo no máximo max_pairs pares."""
    ctx = await get_context(redis, user_id)
    ctx.append({"role": "user", "content": question})
    ctx.append({"role": "assistant", "content": answer})
    ctx = ctx[-(max_pairs * 2):]
    await redis.set(f"ai_context:{user_id}", json.dumps(ctx), ex=CONTEXT_TTL_SECONDS)


async def clear_context(redis: aioredis.Redis, user_id: str) -> None:
    await redis.delete(f"ai_context:{user_id}")


def format_history_for_prompt(context: list[dict[str, str]]) -> str:
    """Converte lista de mensagens para texto legível para o prompt."""
    if not context:
        return "Nenhum histórico anterior."
    lines = []
    for msg in context:
        role = "Usuário" if msg["role"] == "user" else "Assistente"
        lines.append(f"{role}: {msg['content']}")
    return "\n".join(lines)

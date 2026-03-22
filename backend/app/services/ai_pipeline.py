"""Pipeline de IA — chama o agente Groq e gerencia contexto, log e contagem."""

import time
import uuid
from datetime import datetime, timezone

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.ai_query_log import AIQueryLog
from app.models.user import User
from app.models.user_config import UserConfig
from app.services import context as context_service
from app.services.ai import run_agent


_ERR_AI_FAILED = (
    "Desculpe, não consegui processar sua pergunta no momento. "
    "Tente reformulá-la de outra forma ou tente novamente em instantes."
)


async def process_ai_message(
    db: AsyncSession,
    redis: aioredis.Redis,
    user: User,
    config: UserConfig,
    telefone: str,
    question: str,
) -> str:
    """Ponto de entrada do pipeline de IA."""
    start_ms = int(time.time() * 1000)
    user_id_str = str(user.id)

    ctx = await context_service.get_context(redis, user_id_str)

    resposta_final = _ERR_AI_FAILED
    sql_gerado: str | None = None
    erro: str | None = None

    try:
        resposta_final, sql_gerado = await run_agent(
            db=db,
            question=question,
            history=ctx,
            nome_assistente=config.nome_assistente,
            nivel_detalhe=config.nivel_detalhe,
        )
    except Exception as exc:
        erro = f"agent_error: {exc}"
        resposta_final = _ERR_AI_FAILED

    await context_service.add_to_context(
        redis, user_id_str, question, resposta_final, settings.AI_CONTEXT_SIZE
    )

    tempo_ms = int(time.time() * 1000) - start_ms
    log = AIQueryLog(
        user_id=user.id,
        telefone=telefone,
        pergunta_original=question,
        sql_gerado=sql_gerado,
        resultado_bruto=None,
        resposta_final=resposta_final,
        tempo_execucao_ms=tempo_ms,
        modelo_usado=settings.GROQ_MODEL,
        erro=erro,
    )
    db.add(log)
    try:
        await db.commit()
    except Exception:
        await db.rollback()

    return resposta_final


async def count_ai_today(db: AsyncSession, user_id: uuid.UUID) -> int:
    """Conta quantas queries de IA o usuário fez hoje."""
    from datetime import date
    from sqlalchemy import select, func

    today_start = datetime.combine(date.today(), datetime.min.time()).replace(
        tzinfo=timezone.utc
    )
    result = await db.execute(
        select(func.count(AIQueryLog.id)).where(
            AIQueryLog.user_id == user_id,
            AIQueryLog.created_at >= today_start,
        )
    )
    return result.scalar_one() or 0

"""
Pipeline principal de IA da Sprint 3.

Fluxo:
  Pergunta → Contexto Redis → Text-to-SQL → Validação → Execução → Formatação → Log
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.ai_query_log import AIQueryLog
from app.models.user import User
from app.models.user_config import UserConfig
from app.services import ai as ai_service
from app.services import context as context_service
from app.services.sql_executor import (
    SQLExecutionError,
    execute_safe,
    format_result_for_prompt,
)
from app.services.sql_validator import SQLValidationError, validate_and_prepare


# Mensagens amigáveis para cada tipo de erro
_ERR_AI_FAILED = (
    "Desculpe, não consegui processar sua pergunta no momento. "
    "Tente reformulá-la de outra forma ou tente novamente em instantes."
)
_ERR_SQL_INVALID = (
    "Sua pergunta gerou uma consulta que não pôde ser executada por questões de segurança. "
    "Tente perguntar de outra forma, focando em contagens ou listagens simples."
)
_ERR_SQL_EXEC = (
    "Ocorreu um erro ao buscar os dados. Por favor, tente novamente ou reformule sua pergunta."
)
_ERR_NO_DATA = "Não encontrei dados para essa consulta. Tente um período diferente ou outra pergunta."
_ERR_TIMEOUT = (
    "A consulta demorou muito para ser processada. "
    "Tente uma pergunta mais específica para reduzir o volume de dados."
)


async def _save_log(
    db: AsyncSession,
    user: User,
    telefone: str,
    pergunta: str,
    sql_gerado: str | None,
    resultado_bruto: str | None,
    resposta_final: str | None,
    tempo_ms: int | None,
    erro: str | None,
) -> None:
    log = AIQueryLog(
        user_id=user.id,
        telefone=telefone,
        pergunta_original=pergunta,
        sql_gerado=sql_gerado,
        resultado_bruto=resultado_bruto,
        resposta_final=resposta_final,
        tempo_execucao_ms=tempo_ms,
        modelo_usado=settings.OPENAI_MODEL,
        erro=erro,
    )
    db.add(log)
    try:
        await db.commit()
    except Exception:
        await db.rollback()


async def process_ai_message(
    db: AsyncSession,
    redis: aioredis.Redis,
    user: User,
    config: UserConfig,
    telefone: str,
    question: str,
) -> str:
    """
    Executa o pipeline completo de IA e retorna a resposta final.

    1. Carrega contexto conversacional do Redis
    2. Gera SQL com LangChain/OpenAI
    3. Valida SQL (segurança)
    4. Executa SQL no PostgreSQL
    5. Formata resposta em PT-BR
    6. Salva contexto atualizado
    7. Registra log de auditoria
    """
    start_ms = int(time.time() * 1000)
    user_id_str = str(user.id)
    nome = config.nome_assistente
    nivel = config.nivel_detalhe

    sql_gerado: str | None = None
    resultado_bruto: str | None = None
    resposta_final: str | None = None
    erro: str | None = None

    # ── 1. Contexto ─────────────────────────────────────────────────────────
    ctx = await context_service.get_context(redis, user_id_str)
    history_text = context_service.format_history_for_prompt(ctx)

    try:
        # ── 2. Gera SQL ──────────────────────────────────────────────────────
        try:
            raw_sql = await ai_service.generate_sql(question, history_text)
        except asyncio.TimeoutError:
            resposta_final = _ERR_TIMEOUT
            erro = "timeout:sql_generation"
            await _save_log(db, user, telefone, question, None, None, resposta_final,
                            int(time.time() * 1000) - start_ms, erro)
            return resposta_final
        except Exception as exc:
            resposta_final = _ERR_AI_FAILED
            erro = f"ai_generation_error: {exc}"
            await _save_log(db, user, telefone, question, None, None, resposta_final,
                            int(time.time() * 1000) - start_ms, erro)
            return resposta_final

        sql_gerado = raw_sql

        # ── 3. Valida SQL ────────────────────────────────────────────────────
        try:
            validated_sql = validate_and_prepare(raw_sql)
        except SQLValidationError as exc:
            # SQL inválido: tenta resposta geral sem banco
            resposta_final = await _try_general_fallback(question, history_text, nome)
            erro = f"sql_validation: {exc}"
            await _save_log(db, user, telefone, question, sql_gerado, None,
                            resposta_final, int(time.time() * 1000) - start_ms, erro)
            await context_service.add_to_context(redis, user_id_str, question,
                                                  resposta_final, settings.AI_CONTEXT_SIZE)
            return resposta_final

        # ── 4. Executa SQL ───────────────────────────────────────────────────
        try:
            result = await execute_safe(db, validated_sql)
        except SQLExecutionError as exc:
            resposta_final = _ERR_SQL_EXEC
            erro = f"sql_execution: {exc}"
            await _save_log(db, user, telefone, question, sql_gerado, None,
                            resposta_final, int(time.time() * 1000) - start_ms, erro)
            return resposta_final

        resultado_bruto = json.dumps(result, ensure_ascii=False)
        data_text = format_result_for_prompt(result)

        # ── 5. Formata resposta ──────────────────────────────────────────────
        if result["row_count"] == 0:
            # Sem dados — pede para a IA gerar resposta amigável
            resposta_final = await ai_service.format_response(
                question, "Nenhum dado encontrado.", nome, nivel
            )
        else:
            try:
                resposta_final = await ai_service.format_response(
                    question, data_text, nome, nivel
                )
            except Exception as exc:
                # Fallback: retorna dados brutos formatados
                resposta_final = f"Resultado:\n{data_text}"
                erro = f"response_format_error: {exc}"

        # ── 6. Atualiza contexto ─────────────────────────────────────────────
        await context_service.add_to_context(
            redis, user_id_str, question, resposta_final, settings.AI_CONTEXT_SIZE
        )

        # ── 7. Log de auditoria ──────────────────────────────────────────────
        tempo_ms = int(time.time() * 1000) - start_ms
        await _save_log(
            db, user, telefone, question, sql_gerado, resultado_bruto,
            resposta_final, tempo_ms, erro
        )

        return resposta_final

    except Exception as exc:
        resposta_final = _ERR_AI_FAILED
        erro = f"unexpected: {exc}"
        await _save_log(db, user, telefone, question, sql_gerado, resultado_bruto,
                        resposta_final, int(time.time() * 1000) - start_ms, erro)
        return resposta_final


async def _try_general_fallback(question: str, history: str, nome: str) -> str:
    """Fallback: responde sem banco quando SQL não pode ser gerado."""
    try:
        return await ai_service.general_response(question, history, nome)
    except Exception:
        return _ERR_AI_FAILED


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

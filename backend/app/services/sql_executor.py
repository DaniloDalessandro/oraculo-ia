"""
Execução segura de SQL validado via SQLAlchemy com timeout e limite de resultados.
"""

import asyncio
import json
from datetime import datetime, date
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings


class SQLExecutionError(Exception):
    pass


def _serialize_value(v: Any) -> Any:
    """Converte tipos Python não-serializáveis para JSON."""
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, UUID):
        return str(v)
    if isinstance(v, bytes):
        return v.decode("utf-8", errors="replace")
    return v


def _rows_to_json(rows, keys: list[str]) -> list[dict]:
    return [
        {k: _serialize_value(v) for k, v in zip(keys, row)} for row in rows
    ]


async def execute_safe(db: AsyncSession, sql: str) -> dict[str, Any]:
    """
    Executa uma query SELECT validada e retorna resultados como dict serializável.

    Returns:
        {
            "columns": [...],
            "rows": [...],
            "row_count": int,
            "truncated": bool   # True se bateu o LIMIT
        }
    """
    try:
        result = await asyncio.wait_for(
            _run_query(db, sql),
            timeout=settings.AI_TIMEOUT_SECONDS,
        )
        return result
    except asyncio.TimeoutError:
        raise SQLExecutionError(
            f"A consulta demorou mais de {settings.AI_TIMEOUT_SECONDS} segundos e foi cancelada."
        )
    except SQLExecutionError:
        raise
    except Exception as exc:
        raise SQLExecutionError(f"Erro ao executar consulta: {exc}") from exc


async def _run_query(db: AsyncSession, sql: str) -> dict[str, Any]:
    try:
        result = await db.execute(text(sql))
    except Exception as exc:
        raise SQLExecutionError(f"Erro SQL: {exc}") from exc

    keys = list(result.keys())
    rows = result.fetchall()

    serialized = _rows_to_json(rows, keys)
    truncated = len(rows) >= settings.AI_SQL_ROW_LIMIT

    return {
        "columns": keys,
        "rows": serialized,
        "row_count": len(rows),
        "truncated": truncated,
    }


def format_result_for_prompt(result: dict[str, Any], max_chars: int = 3000) -> str:
    """Converte resultado SQL em texto compacto para o prompt da IA."""
    if result["row_count"] == 0:
        return "Nenhum dado encontrado."

    lines = [f"Colunas: {', '.join(result['columns'])}"]
    lines.append(f"Total de linhas: {result['row_count']}")
    if result.get("truncated"):
        lines.append(f"(resultado limitado a {settings.AI_SQL_ROW_LIMIT} linhas)")
    lines.append("")

    for row in result["rows"]:
        row_str = " | ".join(f"{k}={v}" for k, v in row.items())
        lines.append(row_str)

    text_out = "\n".join(lines)
    if len(text_out) > max_chars:
        text_out = text_out[:max_chars] + "\n... (truncado para caber no prompt)"

    return text_out

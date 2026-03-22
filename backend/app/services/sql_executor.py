"""
Execução segura de SQL validado via SQLAlchemy com timeout e limite de resultados.
"""

import asyncio
import time as _time
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
        await db.execute(text("SET LOCAL transaction_read_only = on"))
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


_schema_cache: tuple[str, set[str]] | None = None
_schema_cache_ts: float = 0.0
_SCHEMA_TTL = 300  # 5 minutos


async def _fetch_schema_from_db(db: AsyncSession) -> tuple[str, set[str]]:
    """
    Consulta information_schema para descrever todas as tabelas públicas.

    Returns:
        (schema_description_str, allowed_tables_set)
    """
    col_result = await db.execute(text("""
        SELECT
            c.table_name,
            c.column_name,
            c.data_type,
            c.character_maximum_length,
            c.is_nullable,
            c.column_default
        FROM information_schema.columns c
        INNER JOIN information_schema.tables t
            ON t.table_name = c.table_name AND t.table_schema = c.table_schema
        WHERE c.table_schema = 'public'
          AND t.table_type = 'BASE TABLE'
        ORDER BY c.table_name, c.ordinal_position
    """))
    col_rows = col_result.fetchall()

    pk_result = await db.execute(text("""
        SELECT kcu.table_name, kcu.column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
            ON kcu.constraint_name = tc.constraint_name
           AND kcu.table_schema = tc.table_schema
        WHERE tc.constraint_type = 'PRIMARY KEY'
          AND tc.table_schema = 'public'
    """))
    pk_set: set[tuple[str, str]] = {(r[0], r[1]) for r in pk_result.fetchall()}

    fk_result = await db.execute(text("""
        SELECT
            kcu.table_name,
            kcu.column_name,
            ccu.table_name AS ref_table
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
            ON kcu.constraint_name = tc.constraint_name
           AND kcu.table_schema = tc.table_schema
        JOIN information_schema.constraint_column_usage ccu
            ON ccu.constraint_name = tc.constraint_name
           AND ccu.table_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
          AND tc.table_schema = 'public'
    """))
    fk_map: dict[tuple[str, str], str] = {
        (r[0], r[1]): r[2] for r in fk_result.fetchall()
    }

    tables: dict[str, list[str]] = {}
    allowed: set[str] = set()

    for table_name, col_name, data_type, char_max, nullable, default in col_rows:
        if table_name not in tables:
            tables[table_name] = []
            allowed.add(table_name)

        type_str = data_type
        if char_max:
            type_str += f"({char_max})"

        flags: list[str] = []
        if (table_name, col_name) in pk_set:
            flags.append("PK")
        if (table_name, col_name) in fk_map:
            flags.append(f"FK→{fk_map[(table_name, col_name)]}")
        if nullable == "NO":
            flags.append("NOT NULL")

        flag_str = f"  [{', '.join(flags)}]" if flags else ""
        tables[table_name].append(f"  {col_name:<30} {type_str}{flag_str}")

    lines: list[str] = ["=== SCHEMA DO BANCO DE DADOS ===\n"]
    for tbl in sorted(tables):
        lines.append(f"TABELA: {tbl}")
        lines.extend(tables[tbl])
        lines.append("")

    schema_str = "\n".join(lines).strip()
    return schema_str, allowed


async def get_schema_and_tables(db: AsyncSession) -> tuple[str, set[str]]:
    """
    Retorna (descrição_do_schema, conjunto_de_tabelas_permitidas).

    Resultado é cacheado por _SCHEMA_TTL segundos por processo.
    """
    global _schema_cache, _schema_cache_ts
    now = _time.time()
    if _schema_cache and (now - _schema_cache_ts) < _SCHEMA_TTL:
        return _schema_cache
    try:
        result = await _fetch_schema_from_db(db)
        _schema_cache = result
        _schema_cache_ts = now
        return result
    except Exception as exc:
        raise SQLExecutionError(f"Erro ao obter schema do banco: {exc}") from exc

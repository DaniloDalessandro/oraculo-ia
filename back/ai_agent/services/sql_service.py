"""
SQL Service

Executa consultas SQL de forma segura usando a conexão do Django.
Aplica timeout, limite de linhas e retorna resultado estruturado.
"""
import logging
import re
from typing import Any, Dict, List

from django.db import connection, OperationalError, ProgrammingError

logger = logging.getLogger("ai_agent")

# Limite padrão de linhas retornadas
DEFAULT_ROW_LIMIT = int(500)

# Timeout em milissegundos para PostgreSQL (statement_timeout)
QUERY_TIMEOUT_MS = int(30_000)  # 30 segundos


class SQLExecutionError(Exception):
    """Erro durante execução de SQL."""
    pass


def _set_pg_timeout(cursor):
    """Define statement_timeout no PostgreSQL, se disponível."""
    engine = connection.settings_dict.get("ENGINE", "")
    if "postgresql" in engine or "postgis" in engine:
        try:
            cursor.execute(f"SET LOCAL statement_timeout = {QUERY_TIMEOUT_MS};")
        except Exception:
            pass


def execute_query(sql: str, row_limit: int = DEFAULT_ROW_LIMIT) -> Dict[str, Any]:
    """
    Executa um SQL SELECT e retorna resultado estruturado.

    Returns:
        {
            "columns": [...],
            "rows": [...],
            "row_count": int,
            "truncated": bool,
        }

    Raises:
        SQLExecutionError: em caso de erro de execução.
    """
    original_limit = _extract_limit(sql)

    # Garantir que temos um limite
    sql_with_limit = _apply_limit(sql, row_limit)

    try:
        with connection.cursor() as cursor:
            _set_pg_timeout(cursor)
            cursor.execute(sql_with_limit)

            columns = [desc[0] for desc in (cursor.description or [])]
            rows_raw = cursor.fetchall()

        # Serializar valores
        rows = [
            [_serialize_value(v) for v in row]
            for row in rows_raw
        ]

        truncated = original_limit is None and len(rows) >= row_limit
        limited_by_sql = original_limit is not None

        logger.info(
            "SQL executado com sucesso: %d linhas retornadas (truncated=%s).",
            len(rows),
            truncated,
        )

        return {
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
            "truncated": truncated,
            "limited_by_sql": limited_by_sql,
            "limit_value": original_limit,
        }

    except (OperationalError, ProgrammingError) as exc:
        error_msg = str(exc)
        logger.warning("Erro na execução SQL: %s", error_msg)
        raise SQLExecutionError(f"Erro ao executar a consulta: {error_msg}") from exc
    except Exception as exc:
        logger.error("Erro inesperado na execução SQL.", exc_info=True)
        raise SQLExecutionError("Erro inesperado ao executar a consulta.") from exc


def _apply_limit(sql: str, row_limit: int) -> str:
    """
    Adiciona LIMIT à consulta se não houver um.
    Preserva queries que já têm LIMIT menor ou igual ao limite.
    """
    clean = sql.strip().rstrip(";")

    # Verificar se já existe LIMIT
    existing_limit = _extract_limit(clean)
    if existing_limit is not None:
        if existing_limit <= row_limit:
            return clean  # Manter o LIMIT original menor
        # Substituir por limite mais restrito
        return re.sub(
            r"\bLIMIT\s+\d+\b",
            f"LIMIT {row_limit}",
            clean,
            flags=re.IGNORECASE,
        )

    return f"{clean} LIMIT {row_limit}"


def _extract_limit(sql: str) -> int | None:
    """Retorna o primeiro LIMIT numerico da consulta, quando existir."""
    match = re.search(r"\bLIMIT\s+(\d+)\b", sql, re.IGNORECASE)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def preflight_query(sql: str, row_limit: int = DEFAULT_ROW_LIMIT) -> None:
    """
    Compila a consulta no PostgreSQL sem executar os dados.

    EXPLAIN sem ANALYZE valida aliases, colunas, GROUP BY, tipos e sintaxe,
    mas nao executa a consulta. Isso captura erros que o validador estatico nao ve.
    """
    sql_with_limit = _apply_limit(sql, row_limit)

    try:
        with connection.cursor() as cursor:
            _set_pg_timeout(cursor)
            cursor.execute(f"EXPLAIN {sql_with_limit}")
            cursor.fetchall()
    except (OperationalError, ProgrammingError) as exc:
        error_msg = str(exc)
        logger.warning("Preflight SQL falhou: %s", error_msg)
        raise SQLExecutionError(f"SQL nao compila no PostgreSQL: {error_msg}") from exc
    except Exception as exc:
        logger.error("Erro inesperado no preflight SQL.", exc_info=True)
        raise SQLExecutionError("Erro inesperado ao validar a consulta no PostgreSQL.") from exc


def _serialize_value(value: Any) -> Any:
    """Converte tipos não-serializáveis para string."""
    if value is None:
        return None
    if isinstance(value, (int, float, bool)):
        return value
    if isinstance(value, str):
        return value
    # Datas, decimais, UUIDs, etc.
    try:
        import decimal
        if isinstance(value, decimal.Decimal):
            return float(value)
    except ImportError:
        pass
    return str(value)


def rows_to_dict_list(result: Dict[str, Any]) -> List[Dict]:
    """Converte resultado em lista de dicionários coluna→valor."""
    columns = result.get("columns", [])
    rows = result.get("rows", [])
    return [dict(zip(columns, row)) for row in rows]

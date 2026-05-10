"""
SQL Executor Tool

Executa consultas SQL validadas de forma segura.
"""
import json
import logging
from typing import Any, Dict

from ai_agent.services.sql_service import execute_query, rows_to_dict_list, SQLExecutionError

logger = logging.getLogger("ai_agent")


def sql_executor_tool(sql: str, row_limit: int = 200) -> Dict[str, Any]:
    """
    Executa um SQL SELECT validado e retorna resultado estruturado.

    Args:
        sql: Consulta SQL validada (somente SELECT).
        row_limit: Número máximo de linhas a retornar.

    Returns:
        {
            "success": bool,
            "columns": list,
            "rows": list,
            "row_count": int,
            "truncated": bool,
            "dict_rows": list[dict],
            "error": str ou None,
        }
    """
    try:
        result = execute_query(sql, row_limit=row_limit)
        dict_rows = rows_to_dict_list(result)

        return {
            "success": True,
            "columns": result["columns"],
            "rows": result["rows"],
            "row_count": result["row_count"],
            "truncated": result["truncated"],
            "limited_by_sql": result.get("limited_by_sql", False),
            "limit_value": result.get("limit_value"),
            "dict_rows": dict_rows,
            "error": None,
        }

    except SQLExecutionError as exc:
        logger.warning("Falha na execução SQL: %s", exc)
        return {
            "success": False,
            "columns": [],
            "rows": [],
            "row_count": 0,
            "truncated": False,
            "limited_by_sql": False,
            "limit_value": None,
            "dict_rows": [],
            "error": str(exc),
        }


def format_result_for_llm(result: Dict[str, Any], max_rows: int = 50) -> str:
    """Formata resultado de SQL em texto legível para o LLM."""
    if not result["success"]:
        return f"Erro na execução: {result['error']}"

    if result["row_count"] == 0:
        return "A consulta não retornou dados."

    lines = []
    columns = result["columns"]

    # Cabeçalho
    lines.append(" | ".join(str(c) for c in columns))
    lines.append("-" * (len(lines[0])))

    # Linhas (limitado)
    for row in result["rows"][:max_rows]:
        lines.append(" | ".join(str(v) if v is not None else "NULL" for v in row))

    if result["truncated"] or result["row_count"] > max_rows:
        lines.append(
            f"\n... ({result['row_count']} linhas no total"
            + (" — resultado truncado pelo limite" if result["truncated"] else "")
            + ")"
        )

    if result.get("limited_by_sql"):
        limit_value = result.get("limit_value") or result["row_count"]
        lines.append(
            "\nATENCAO: a consulta tem LIMIT "
            f"{limit_value}; as {result['row_count']} linhas retornadas sao uma listagem limitada, "
            "nao necessariamente o total real de registros."
        )

    return "\n".join(lines)

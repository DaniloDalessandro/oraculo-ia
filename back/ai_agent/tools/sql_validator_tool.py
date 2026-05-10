"""
SQL Validator Tool

Valida a segurança e a correção estrutural da consulta SQL antes de executar.
"""
import logging
from typing import Dict, List

from ai_agent.validators.sql_safety import validate_sql, extract_table_names
from ai_agent.services.schema_service import schema_service
from ai_agent.services.sql_service import SQLExecutionError, preflight_query

logger = logging.getLogger("ai_agent")


def sql_validator_tool(
    sql: str,
    validate_against_schema: bool = True,
) -> Dict:
    """
    Valida a consulta SQL em múltiplas camadas.

    Returns:
        {
            "is_valid": bool,
            "errors": list[str],
            "warnings": list[str],
            "tables_referenced": list[str],
        }
    """
    errors: List[str] = []
    warnings: List[str] = []

    # Camada 1: Validação de segurança
    known_tables = schema_service.get_table_names() if validate_against_schema else None
    is_safe, safety_error = validate_sql(sql, known_tables=known_tables)

    if not is_safe:
        logger.warning("SQL bloqueado pelo validador de segurança: %s", safety_error)
        return {
            "is_valid": False,
            "errors": [safety_error],
            "warnings": [],
            "tables_referenced": [],
        }

    # Camada 2: Verificar tabelas e colunas existem no schema
    tables_referenced = extract_table_names(sql)

    if validate_against_schema:
        schema = schema_service.introspect()

        for table in tables_referenced:
            if table not in schema:
                errors.append(f"Tabela '{table}' não existe no banco de dados.")
            else:
                # Verificar colunas basicamente
                _warn_suspicious_joins(sql, table, schema, warnings)

    # Camada 3: Avisos de boas práticas
    sql_upper = sql.upper()

    if "SELECT *" in sql_upper:
        warnings.append("Uso de SELECT * detectado. Prefira selecionar colunas específicas.")

    if "LIMIT" not in sql_upper and any(
        kw in sql_upper for kw in ("FROM", "JOIN")
    ):
        # Sem LIMIT em listagem — avisar (o executor aplicará limite automático)
        warnings.append(
            "Consulta sem LIMIT explícito. O executor aplicará o limite padrão."
        )

    if not errors and validate_against_schema:
        try:
            preflight_query(sql, row_limit=1)
        except SQLExecutionError as exc:
            errors.append(str(exc))

    if errors:
        logger.warning("SQL inválido: %s", errors)

    is_valid = len(errors) == 0
    return {
        "is_valid": is_valid,
        "errors": errors,
        "warnings": warnings,
        "tables_referenced": tables_referenced,
    }


def _warn_suspicious_joins(
    sql: str, table: str, schema: dict, warnings: list
) -> None:
    """Detecta JOINs sem cláusula ON que podem gerar produto cartesiano."""
    import re

    joins_without_on = re.findall(
        r"\bJOIN\s+\S+\s+(?!ON|USING|LATERAL)",
        sql,
        re.IGNORECASE,
    )
    if joins_without_on:
        warnings.append(
            f"Possível JOIN sem cláusula ON detectado. Verifique a condição de join."
        )

"""
Camada de segurança para validação de SQL gerado pela IA.

Regras:
- Apenas SELECT é permitido
- Apenas tabelas existentes no banco podem ser consultadas (lista dinâmica)
- LIMIT é injetado automaticamente se ausente
- Palavras-chave perigosas bloqueiam a query
- Comentários SQL são removidos antes da análise
"""

import re
import sqlparse
from sqlparse.sql import Statement
from sqlparse.tokens import Keyword, DML, Punctuation

from app.config import settings

BLOCKED_KEYWORDS: set[str] = {
    "DELETE",
    "UPDATE",
    "INSERT",
    "DROP",
    "ALTER",
    "TRUNCATE",
    "CREATE",
    "REPLACE",
    "EXECUTE",
    "EXEC",
    "CALL",
    "GRANT",
    "REVOKE",
    "COPY",
    "VACUUM",
    "ANALYZE",
    "REINDEX",
    "CLUSTER",
    "COMMENT",
    "SECURITY",
    "SUPERUSER",
    "pg_read_file",
    "pg_ls_dir",
    "pg_stat",
    "information_schema",
    "pg_catalog",
    ";",   # bloqueia múltiplas statements
}


class SQLValidationError(Exception):
    """Raised quando a query gerada pela IA não passa na validação de segurança."""

    pass


def _strip_comments(sql: str) -> str:
    """Remove comentários SQL (-- linha e /* bloco */)."""
    sql = re.sub(r"--[^\n]*", " ", sql)
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    return sql.strip()


def _extract_table_names(sql: str) -> set[str]:
    """Extrai todos os nomes de tabelas referenciados na query."""
    tables: set[str] = set()

    parsed = sqlparse.parse(sql)
    if not parsed:
        return tables

    for statement in parsed:
        _collect_tables_from_statement(statement, tables)

    return tables


def _collect_tables_from_statement(statement: Statement, tables: set[str]) -> None:
    from_seen = False

    for token in statement.flatten():
        ttype = token.ttype
        val_upper = token.value.upper().strip()

        if ttype in (Keyword, DML):
            if val_upper in ("FROM", "JOIN", "INNER JOIN", "LEFT JOIN", "RIGHT JOIN",
                             "FULL JOIN", "CROSS JOIN", "INTO"):
                from_seen = True
            elif val_upper in (
                "WHERE", "GROUP", "ORDER", "HAVING", "LIMIT", "OFFSET",
                "UNION", "INTERSECT", "EXCEPT", "ON", "SET", "VALUES",
            ):
                from_seen = False
            continue

        if ttype is Punctuation:
            from_seen = False
            continue

        if from_seen and token.ttype is not None:
            name = token.value.strip().strip('"').strip("'").lower()
            if name and re.match(r"^[a-z_][a-z0-9_]*$", name):
                tables.add(name)
            from_seen = False


def _inject_limit(sql: str, limit: int) -> str:
    """Garante que a query tem LIMIT, injetando se necessário."""
    upper = sql.upper()
    if "LIMIT" in upper:
        sql = re.sub(
            r"\bLIMIT\s+(\d+)\b",
            lambda m: f"LIMIT {min(int(m.group(1)), limit)}",
            sql,
            flags=re.IGNORECASE,
        )
    else:
        sql = sql.rstrip().rstrip(";")
        sql = f"{sql}\nLIMIT {limit}"
    return sql


def validate_and_prepare(raw_sql: str, allowed_tables: set[str] | None = None) -> str:
    """
    Valida e prepara a query SQL gerada pela IA.

    Args:
        raw_sql: SQL gerado pela IA (pode conter markdown, comentários, etc.)
        allowed_tables: conjunto de tabelas permitidas (obtido dinamicamente do banco).
                        Se None, não valida tabelas (modo permissivo).

    Returns:
        SQL limpo, validado e com LIMIT injetado.

    Raises:
        SQLValidationError: se a query falhar em qualquer verificação de segurança.
    """
    sql = re.sub(r"```(?:sql)?", "", raw_sql, flags=re.IGNORECASE).strip()
    sql = sql.strip("`").strip()

    sql = _strip_comments(sql)

    if not sql:
        raise SQLValidationError("Query vazia gerada pela IA.")

    statements_count = len([s for s in sqlparse.parse(sql) if s.get_type()])
    if statements_count > 1:
        raise SQLValidationError("Múltiplas statements SQL não são permitidas.")

    sql_upper = sql.upper()
    for blocked in BLOCKED_KEYWORDS:
        pattern = r"\b" + re.escape(blocked.upper()) + r"\b"
        if re.search(pattern, sql_upper):
            raise SQLValidationError(
                f"Operação '{blocked}' não é permitida por questões de segurança."
            )

    parsed = sqlparse.parse(sql)
    if not parsed:
        raise SQLValidationError("Não foi possível interpretar o SQL gerado.")

    stmt_type = parsed[0].get_type()
    if stmt_type != "SELECT":
        raise SQLValidationError(
            f"Apenas consultas SELECT são permitidas. Tipo detectado: '{stmt_type}'."
        )

    referenced_tables = _extract_table_names(sql)
    if allowed_tables is not None and referenced_tables:
        unauthorized = referenced_tables - allowed_tables
        if unauthorized:
            raise SQLValidationError(
                f"Tabelas não encontradas no banco: {', '.join(unauthorized)}. "
                f"Tabelas disponíveis: {', '.join(sorted(allowed_tables))}."
            )

    sql = _inject_limit(sql, settings.AI_SQL_ROW_LIMIT)

    return sql

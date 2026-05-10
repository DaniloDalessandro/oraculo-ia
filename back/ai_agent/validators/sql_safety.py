"""
SQL Safety Validator

Garante que toda consulta SQL é somente leitura (SELECT).
Bloqueia qualquer operação de escrita, alteração ou acesso indevido.
"""
import re
from typing import Tuple, List, Set

# Operações de escrita absolutamente proibidas
WRITE_KEYWORDS: Set[str] = {
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE",
    "CREATE", "GRANT", "REVOKE", "EXECUTE", "EXEC", "CALL",
    "MERGE", "REPLACE", "UPSERT", "COPY", "VACUUM", "REINDEX",
    "CLUSTER", "CHECKPOINT", "REFRESH",
}

# Funções perigosas do banco
DANGEROUS_FUNCTIONS: Set[str] = {
    "PG_SLEEP", "PG_READ_FILE", "PG_READ_BINARY_FILE",
    "LO_IMPORT", "LO_EXPORT", "LO_CREAT", "LO_CREATE", "LO_UNLINK",
    "XP_CMDSHELL", "SP_EXECUTESQL", "DBMS_OUTPUT", "UTL_FILE",
    "PG_RELOAD_CONF", "PG_ROTATE_LOGFILE", "PG_START_BACKUP",
}

# Tabelas que nunca devem ser acessadas pelo agente
FORBIDDEN_TABLES: Set[str] = {
    "auth_user",
    "auth_password",
    "auth_permission",
    "auth_group",
    "auth_group_permissions",
    "auth_user_groups",
    "auth_user_user_permissions",
    "django_session",
    "django_migrations",
    "django_content_type",
    "django_admin_log",
    "authtoken_token",
    "ai_agent_aIagentlog",
    "ai_agent_aiagentlog",
}

# Padrões de acesso a informações do sistema
FORBIDDEN_SCHEMA_PATTERNS: List[str] = [
    r"PG_SHADOW",
    r"PG_ROLES",
    r"PG_USER",
    r"PG_AUTHID",
    r"PG_AUTH_MEMBERS",
    r"INFORMATION_SCHEMA\s*\.\s*(USER|ROUTINE|PRIVILEGE|ROLE|APPLICABLE)",
    r"PG_CATALOG\s*\.\s*PG_(USER|AUTH|SHADOW|ROLES)",
]


def _strip_strings(sql: str) -> str:
    """Remove string literals para evitar falsos positivos."""
    return re.sub(r"'[^']*'", "''", sql)


def _has_line_comments(sql: str) -> bool:
    """Verifica presença de comentários de linha (--)."""
    clean = _strip_strings(sql)
    return "--" in clean


def _has_block_comments(sql: str) -> bool:
    """Verifica presença de comentários de bloco (/* */)."""
    return "/*" in sql


def _count_statements(sql: str) -> int:
    """Conta o número de statements SQL (separados por ;)."""
    clean = _strip_strings(sql).rstrip()
    # Remove trailing semicolon before counting
    if clean.endswith(";"):
        clean = clean[:-1]
    return clean.count(";") + 1


def validate_sql(
    sql: str,
    known_tables: List[str] = None,
) -> Tuple[bool, str]:
    """
    Valida se o SQL é seguro para execução.

    Retorna:
        (is_valid: bool, error_message: str)
    """
    if not sql or not sql.strip():
        return False, "Consulta SQL vazia."

    stripped = sql.strip()

    # 1. Verificar comentários proibidos
    if _has_line_comments(stripped):
        return False, "Comentários SQL (--) não são permitidos na consulta."
    if _has_block_comments(stripped):
        return False, "Comentários de bloco (/* */) não são permitidos."

    # 2. Deve começar com SELECT
    first_token = stripped.split()[0].upper()
    if first_token not in ("SELECT", "WITH"):
        return False, (
            f"A consulta deve começar com SELECT ou WITH. "
            f"Encontrado: '{first_token}'."
        )

    # 3. Apenas um statement
    if _count_statements(stripped) > 1:
        return False, "Múltiplos comandos SQL não são permitidos."

    sql_clean = _strip_strings(stripped)
    sql_upper = sql_clean.upper()

    # 4. Verificar palavras-chave de escrita
    for keyword in WRITE_KEYWORDS:
        pattern = r"\b" + re.escape(keyword) + r"\b"
        if re.search(pattern, sql_upper):
            return False, f"Operação proibida detectada: '{keyword}'."

    # 5. Verificar funções perigosas
    for func in DANGEROUS_FUNCTIONS:
        pattern = r"\b" + re.escape(func) + r"\s*\("
        if re.search(pattern, sql_upper):
            return False, f"Função perigosa detectada: '{func}'."

    # 6. Verificar tabelas proibidas
    for table in FORBIDDEN_TABLES:
        pattern = r"\b" + re.escape(table.upper()) + r"\b"
        if re.search(pattern, sql_upper):
            return False, f"Acesso à tabela '{table}' não é permitido."

    # 7. Verificar acesso a informações de sistema
    for pat in FORBIDDEN_SCHEMA_PATTERNS:
        if re.search(pat, sql_upper):
            return False, "Acesso a informações do sistema não é permitido."

    # 8. Validar tabelas referenciadas contra schema conhecido
    if known_tables:
        referenced = extract_table_names(sql)
        known_lower = {t.lower() for t in known_tables}
        # Também permite subqueries com aliases e palavras reservadas
        reserved = {"lateral", "unnest", "values", "dual", "generate_series"}
        for table in referenced:
            if table not in known_lower and table not in reserved:
                return (
                    False,
                    f"Tabela '{table}' não encontrada no banco de dados. "
                    f"Verifique o nome da tabela.",
                )

    return True, ""


def extract_table_names(sql: str) -> List[str]:
    """Extrai nomes de tabelas referenciadas em uma consulta SQL.

    Rastreia profundidade de parênteses para ignorar FROM dentro de funções
    como EXTRACT(MONTH FROM col) e exclui aliases de CTEs.
    """
    clean = _strip_strings(sql)

    # Aliases de CTEs não são tabelas reais
    cte_aliases = {
        m.lower()
        for m in re.findall(
            r"\b([a-zA-Z_][a-zA-Z0-9_]*)\s+AS\s*\(",
            clean,
            flags=re.IGNORECASE,
        )
    }

    reserved = {"lateral", "unnest", "values", "dual", "generate_series"}
    tables: List[str] = []

    tokens = re.findall(r"[()]|[a-zA-Z_][a-zA-Z0-9_]*", clean)

    depth = 0
    expect_table = False

    for token in tokens:
        if token == "(":
            depth += 1
            expect_table = False
        elif token == ")":
            depth -= 1
            expect_table = False
        elif token.upper() in ("FROM", "JOIN"):
            # FROM dentro de funções (EXTRACT, TRIM etc.) fica em depth > 0 — ignorar
            expect_table = depth == 0
        elif expect_table:
            name = token.lower()
            if name not in reserved and name not in cte_aliases:
                tables.append(name)
            expect_table = False
        elif token.upper() != "AS":
            expect_table = False

    return tables

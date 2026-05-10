"""
Database Profile Tool

Gera perfil analítico completo do banco para dar contexto preciso ao LLM:
  - Contagem de linhas por tabela
  - % de NULL por coluna (evita filtros em colunas vazias)
  - Cardinalidade (quantos valores distintos)
  - Amostras de valores para colunas categóricas
  - Range real de datas e estatísticas de colunas numéricas

Resultado é cacheado por 1h — só roda quando o cache expira ou é invalidado.
"""
import logging
from typing import Any, Dict, List, Optional, Tuple

from django.db import connection

from ai_agent.services.schema_service import schema_service
from ai_agent.validators.sql_safety import FORBIDDEN_TABLES

logger = logging.getLogger("ai_agent")

# ─── Limites ──────────────────────────────────────────────────────────────── #

MAX_TABLES_TO_PROFILE = 30
MAX_TEXT_COLS = 12          # máx colunas texto por tabela
MAX_NUMERIC_COLS = 10       # máx colunas numéricas por tabela
MAX_DATE_COLS = 6           # máx colunas de data por tabela
MAX_SAMPLE_VALUES = 25      # valores distintos a mostrar
CARDINALITY_CATEGORICAL = 60  # acima disso → texto livre (não mostra amostras)
HIGH_NULL_THRESHOLD = 30    # % de NULL acima disso → aviso para o LLM

SENSITIVE_COLUMN_KEYWORDS = (
    "senha", "password", "secret", "token", "hash",
    "cpf", "cnpj", "rg", "passaporte", "credential",
)


def _is_sensitive(col: str) -> bool:
    lower = col.lower()
    return any(kw in lower for kw in SENSITIVE_COLUMN_KEYWORDS)


# ─── Queries de perfil ────────────────────────────────────────────────────── #

def _row_count_and_nulls(
    table: str, columns: List[str]
) -> Tuple[int, Dict[str, int]]:
    """
    Uma única query por tabela:
    SELECT COUNT(*), COUNT(col1), COUNT(col2), ...
    COUNT(col) ignora NULL — (total - count_col) = quantidade de NULLs.
    """
    if not columns:
        return 0, {}

    col_exprs = ", ".join(f'COUNT("{c}") AS c_{i}' for i, c in enumerate(columns))
    sql = f'SELECT COUNT(*) AS total, {col_exprs} FROM "{table}"'

    try:
        with connection.cursor() as cursor:
            cursor.execute(sql)
            row = cursor.fetchone()

        if not row:
            return 0, {}

        total = row[0] or 0
        null_counts = {
            columns[i]: total - (row[i + 1] or 0)
            for i in range(len(columns))
        }
        return total, null_counts
    except Exception as exc:
        logger.debug("row_count_and_nulls falhou em %s: %s", table, exc)
        return 0, {}


def _null_pct(null_count: int, total: int) -> float:
    if not total:
        return 0.0
    return round(100.0 * null_count / total, 1)


def _date_ranges(table: str, date_cols: List[str]) -> Dict[str, Dict]:
    if not date_cols:
        return {}

    parts = []
    for c in date_cols:
        parts.append(f'MIN("{c}") AS min_{c.replace(" ", "_")}')
        parts.append(f'MAX("{c}") AS max_{c.replace(" ", "_")}')

    try:
        with connection.cursor() as cursor:
            cursor.execute(f'SELECT {", ".join(parts)} FROM "{table}"')
            row = cursor.fetchone()

        if not row:
            return {}

        result = {}
        for i, c in enumerate(date_cols):
            mn, mx = row[i * 2], row[i * 2 + 1]
            result[c] = {
                "min": str(mn)[:10] if mn else None,
                "max": str(mx)[:10] if mx else None,
            }
        return result
    except Exception as exc:
        logger.debug("date_ranges falhou em %s: %s", table, exc)
        return {}


def _numeric_stats(table: str, numeric_cols: List[str]) -> Dict[str, Dict]:
    if not numeric_cols:
        return {}

    parts = []
    for c in numeric_cols:
        parts.append(f'MIN("{c}")')
        parts.append(f'MAX("{c}")')
        parts.append(f'ROUND(AVG("{c}")::numeric, 2)')

    try:
        with connection.cursor() as cursor:
            cursor.execute(f'SELECT {", ".join(parts)} FROM "{table}"')
            row = cursor.fetchone()

        if not row:
            return {}

        result = {}
        for i, c in enumerate(numeric_cols):
            mn, mx, avg = row[i * 3], row[i * 3 + 1], row[i * 3 + 2]
            result[c] = {
                "min": float(mn) if mn is not None else None,
                "max": float(mx) if mx is not None else None,
                "avg": float(avg) if avg is not None else None,
            }
        return result
    except Exception as exc:
        logger.debug("numeric_stats falhou em %s: %s", table, exc)
        return {}


def _cardinality(table: str, col: str) -> Optional[int]:
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                f'SELECT COUNT(DISTINCT "{col}") FROM "{table}" WHERE "{col}" IS NOT NULL'
            )
            row = cursor.fetchone()
        return int(row[0]) if row else None
    except Exception:
        return None


def _sample_values(table: str, col: str, limit: int = MAX_SAMPLE_VALUES) -> List[str]:
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                f'SELECT DISTINCT "{col}" FROM "{table}" '
                f'WHERE "{col}" IS NOT NULL ORDER BY "{col}" LIMIT {limit}'
            )
            return [str(r[0]) for r in cursor.fetchall()]
    except Exception:
        return []


# ─── Tool principal ───────────────────────────────────────────────────────── #

def database_profile_tool(max_tables: int = MAX_TABLES_TO_PROFILE) -> Dict[str, Any]:
    """
    Gera perfil analítico completo do banco.

    Retorna dict:
      {
        "table_name": {
          "row_count": int,
          "columns": {
            "col_name": {
              "type": "date" | "numeric" | "text" | "categorical",
              "null_pct": float,
              "min": ..., "max": ...,          # datas e numéricos
              "avg": float,                    # numéricos
              "cardinality": int,              # texto
              "sample_values": [...],          # texto categórico
            }
          }
        }
      }
    """
    schema = schema_service.introspect()
    profiles: Dict[str, Any] = {}
    tables_profiled = 0

    for table_name, info in schema.items():
        if table_name in FORBIDDEN_TABLES:
            continue
        if tables_profiled >= max_tables:
            break
        if "error" in info:
            continue

        date_cols = info.get("date_columns", [])[:MAX_DATE_COLS]
        numeric_cols = [
            c for c in info.get("numeric_columns", [])
            if not _is_sensitive(c)
        ][:MAX_NUMERIC_COLS]
        text_cols = [
            c for c in info.get("text_columns", [])
            if not _is_sensitive(c)
        ][:MAX_TEXT_COLS]

        all_cols = date_cols + numeric_cols + text_cols
        if not all_cols:
            tables_profiled += 1
            continue

        # ── 1. Row count + null counts (1 query) ──────────────────────
        row_count, null_counts = _row_count_and_nulls(table_name, all_cols)

        # ── 2. Date ranges (1 query) ──────────────────────────────────
        date_info = _date_ranges(table_name, date_cols)

        # ── 3. Numeric stats (1 query) ────────────────────────────────
        num_info = _numeric_stats(table_name, numeric_cols)

        # ── 4. Text: cardinalidade + amostras (por coluna) ────────────
        text_info: Dict[str, Dict] = {}
        for col in text_cols:
            null_count = null_counts.get(col, 0)
            npct = _null_pct(null_count, row_count)

            card = _cardinality(table_name, col)
            entry: Dict[str, Any] = {"null_pct": npct}

            if card is not None:
                entry["cardinality"] = card
                if card <= CARDINALITY_CATEGORICAL:
                    entry["type"] = "categorical"
                    entry["sample_values"] = _sample_values(table_name, col)
                else:
                    entry["type"] = "text"
                    entry["sample_values"] = []
            else:
                entry["type"] = "text"
                entry["sample_values"] = []

            text_info[col] = entry

        # ── Montar perfil da tabela ───────────────────────────────────
        col_profiles: Dict[str, Any] = {}

        for col in date_cols:
            dr = date_info.get(col, {})
            col_profiles[col] = {
                "type": "date",
                "null_pct": _null_pct(null_counts.get(col, 0), row_count),
                "min": dr.get("min"),
                "max": dr.get("max"),
            }

        for col in numeric_cols:
            ns = num_info.get(col, {})
            col_profiles[col] = {
                "type": "numeric",
                "null_pct": _null_pct(null_counts.get(col, 0), row_count),
                "min": ns.get("min"),
                "max": ns.get("max"),
                "avg": ns.get("avg"),
            }

        for col in text_cols:
            col_profiles[col] = text_info[col]

        profiles[table_name] = {
            "row_count": row_count,
            "columns": col_profiles,
        }

        tables_profiled += 1
        logger.debug("Profile: %s (%d linhas, %d cols)", table_name, row_count, len(col_profiles))

    logger.info("Profile concluído: %d tabelas.", len(profiles))
    return profiles


# ─── Formatador para LLM ─────────────────────────────────────────────────── #

def format_profiles_for_llm(profiles: Dict[str, Any]) -> str:
    """
    Formata o perfil em texto estruturado e acionável para o LLM.

    Exemplo de saída:
      [atracoes] 12.543 linhas
        DATA  data_atracacao: 2020-01-15 → 2025-11-30
        DATA  desatracacao: 2020-01-20 → 2025-12-01
        NUM   tonelagem: min=0 / max=45.000 / avg=8.234  ⚠ 12% NULL
        CAT   tipo_carga [8 valores]: 'GRANEL SÓLIDO', 'GRANEL LÍQUIDO', ...
        TEXT  observacao [234 valores distintos]  ⚠ 67% NULL — evite filtros
    """
    if not profiles:
        return "Perfil do banco indisponível."

    lines = ["=== PERFIL DO BANCO DE DADOS ===\n"]

    for table_name, tinfo in profiles.items():
        row_count = tinfo.get("row_count", 0)
        lines.append(f"[{table_name}] {row_count:,} linhas".replace(",", "."))

        for col, cinfo in tinfo.get("columns", {}).items():
            ctype = cinfo.get("type", "text")
            npct = cinfo.get("null_pct", 0.0)
            null_warn = f"  ⚠ {npct}% NULL" if npct >= HIGH_NULL_THRESHOLD else (
                f"  ({npct}% NULL)" if npct > 5 else ""
            )
            avoid = " — evite filtros nesta coluna" if npct >= HIGH_NULL_THRESHOLD else ""

            if ctype == "date":
                mn, mx = cinfo.get("min") or "?", cinfo.get("max") or "?"
                lines.append(f"  DATA  {col}: {mn} → {mx}{null_warn}")

            elif ctype == "numeric":
                mn = cinfo.get("min")
                mx = cinfo.get("max")
                avg = cinfo.get("avg")
                stats = []
                if mn is not None:
                    stats.append(f"min={_fmt_num(mn)}")
                if mx is not None:
                    stats.append(f"max={_fmt_num(mx)}")
                if avg is not None:
                    stats.append(f"avg={_fmt_num(avg)}")
                stat_str = " / ".join(stats) if stats else "sem dados"
                lines.append(f"  NUM   {col}: {stat_str}{null_warn}")

            elif ctype == "categorical":
                card = cinfo.get("cardinality", "?")
                samples = cinfo.get("sample_values", [])
                sample_str = ", ".join(f"'{v}'" for v in samples[:15])
                if len(samples) > 15:
                    sample_str += f", ... (+{len(samples) - 15})"
                lines.append(f"  CAT   {col} [{card} valores]: {sample_str}{null_warn}{avoid}")

            else:  # text livre
                card = cinfo.get("cardinality")
                card_str = f" [{card} distintos]" if card else ""
                lines.append(f"  TEXT  {col}{card_str}{null_warn}{avoid}")

        lines.append("")

    return "\n".join(lines)


def _fmt_num(v) -> str:
    """Formata número de forma compacta (sem casas desnecessárias)."""
    try:
        f = float(v)
        if f == int(f) and abs(f) < 1_000_000:
            return f"{int(f):,}".replace(",", ".")
        return f"{f:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return str(v)

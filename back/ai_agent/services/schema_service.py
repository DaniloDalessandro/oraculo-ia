"""
Schema Service

Lê e cacheia o schema completo do banco de dados.
Usa a API de introspecção do Django para compatibilidade com SQLite e PostgreSQL.
"""
import time
import logging
from typing import Any, Dict, List, Optional

from django.db import connection

logger = logging.getLogger("ai_agent")

# TTL do cache em segundos (5 minutos)
SCHEMA_CACHE_TTL = int(300)

# Prefixos de tabelas internas do Django a ignorar
EXCLUDED_PREFIXES = (
    "django_",
    "auth_",
    "ai_agent_",
)


class SchemaService:
    """Serviço singleton de introspecção do schema do banco."""

    def __init__(self):
        self._cache: Optional[Dict[str, Any]] = None
        self._cache_time: float = 0.0

    # ------------------------------------------------------------------ #
    # Controle de cache
    # ------------------------------------------------------------------ #

    def _is_cache_valid(self) -> bool:
        return (
            self._cache is not None
            and (time.monotonic() - self._cache_time) < SCHEMA_CACHE_TTL
        )

    def invalidate_cache(self):
        self._cache = None
        self._cache_time = 0.0

    # ------------------------------------------------------------------ #
    # Introspecção principal
    # ------------------------------------------------------------------ #

    def introspect(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Retorna o schema completo do banco.
        Usa cache se disponível e dentro do TTL.
        """
        if not force_refresh and self._is_cache_valid():
            return self._cache  # type: ignore[return-value]

        schema: Dict[str, Any] = {}

        with connection.cursor() as cursor:
            all_tables = connection.introspection.table_names(cursor)

            for table_name in sorted(all_tables):
                if self._should_exclude(table_name):
                    continue
                try:
                    schema[table_name] = self._introspect_table(cursor, table_name)
                except Exception as exc:
                    logger.warning(
                        "Falha ao introspectar tabela '%s': %s", table_name, exc
                    )
                    schema[table_name] = {
                        "error": str(exc),
                        "columns": [],
                        "primary_keys": [],
                        "foreign_keys": {},
                        "indexes": [],
                        "date_columns": [],
                        "numeric_columns": [],
                        "text_columns": [],
                    }

        self._cache = schema
        self._cache_time = time.monotonic()
        logger.info("Schema introspectado: %d tabelas.", len(schema))
        return schema

    def _should_exclude(self, table_name: str) -> bool:
        return any(table_name.startswith(p) for p in EXCLUDED_PREFIXES)

    def _resolve_type_name(self, type_code) -> str:
        """Converte type_code do backend para nome legível."""
        try:
            rev = connection.introspection.data_types_reverse
            if isinstance(type_code, int) and type_code in rev:
                return rev[type_code]
        except Exception:
            pass
        return str(type_code) if type_code else "unknown"

    def _introspect_table(self, cursor, table_name: str) -> Dict[str, Any]:
        """Introspecta uma tabela individualmente."""
        # Colunas
        try:
            raw_cols = connection.introspection.get_table_description(cursor, table_name)
        except Exception:
            raw_cols = []

        # Constraints (PK, FK, índices)
        try:
            constraints = connection.introspection.get_constraints(cursor, table_name)
        except Exception:
            constraints = {}

        pk_cols: set = set()
        fk_map: Dict[str, Dict] = {}
        index_cols: set = set()

        for _name, info in constraints.items():
            cols = info.get("columns", [])
            if info.get("primary_key"):
                pk_cols.update(cols)
            if info.get("foreign_key"):
                fk_target = info["foreign_key"]  # (table, column)
                for col in cols:
                    fk_map[col] = {
                        "to_table": fk_target[0] if len(fk_target) > 0 else "?",
                        "to_column": fk_target[1] if len(fk_target) > 1 else "?",
                    }
            if info.get("index") and not info.get("primary_key"):
                index_cols.update(cols)

        # Classificação semântica das colunas
        columns: List[Dict] = []
        date_columns: List[str] = []
        numeric_columns: List[str] = []
        text_columns: List[str] = []

        for col in raw_cols:
            type_name = self._resolve_type_name(col.type_code)
            type_lower = type_name.lower()
            name_lower = col.name.lower()

            col_info: Dict[str, Any] = {
                "name": col.name,
                "type": type_name,
                "nullable": bool(col.null_ok),
                "default": str(col.default) if col.default is not None else None,
                "is_pk": col.name in pk_cols,
                "is_fk": col.name in fk_map,
                "fk_target": fk_map.get(col.name),
                "is_indexed": col.name in index_cols,
            }
            columns.append(col_info)

            # Heurísticas de classificação
            is_date = any(
                t in type_lower for t in ("date", "time", "timestamp", "interval")
            ) or any(
                kw in name_lower
                for kw in ("data", "date", "dt_", "_dt", "hora", "time", "_em", "criado", "atualizado")
            )
            is_numeric = any(
                t in type_lower
                for t in ("int", "float", "decimal", "numeric", "real", "double", "bigint", "smallint")
            )
            is_text = any(
                t in type_lower for t in ("char", "text", "varchar", "string")
            )

            if is_date:
                date_columns.append(col.name)
            elif is_numeric and col.name not in pk_cols and col.name not in fk_map:
                numeric_columns.append(col.name)
            elif is_text and col.name not in pk_cols:
                text_columns.append(col.name)

        return {
            "columns": columns,
            "primary_keys": list(pk_cols),
            "foreign_keys": fk_map,
            "indexes": list(index_cols),
            "date_columns": date_columns,
            "numeric_columns": numeric_columns,
            "text_columns": text_columns,
        }

    # ------------------------------------------------------------------ #
    # Resumo textual para o LLM
    # ------------------------------------------------------------------ #

    def get_text_summary(self, schema: Dict = None) -> str:
        """Gera resumo textual do schema para incluir no contexto do LLM."""
        if schema is None:
            schema = self.introspect()

        lines = ["=== SCHEMA DO BANCO DE DADOS ===\n"]

        for table_name in sorted(schema.keys()):
            info = schema[table_name]
            if "error" in info:
                lines.append(f"TABELA: {table_name} [ERRO NA INTROSPECÇÃO]\n")
                continue

            lines.append(f"TABELA: {table_name}")
            for col in info["columns"]:
                markers = []
                if col["is_pk"]:
                    markers.append("PK")
                if col["is_fk"] and col["fk_target"]:
                    t = col["fk_target"]
                    markers.append(f"FK→{t['to_table']}.{t['to_column']}")
                if col["is_indexed"]:
                    markers.append("IDX")
                if col["nullable"]:
                    markers.append("NULL")

                m = f" [{', '.join(markers)}]" if markers else ""
                lines.append(f"  - {col['name']} ({col['type']}){m}")

            if info["date_columns"]:
                lines.append(f"  📅 Datas: {', '.join(info['date_columns'])}")
            if info["numeric_columns"]:
                lines.append(f"  🔢 Numéricos: {', '.join(info['numeric_columns'])}")
            if info["foreign_keys"]:
                for col_name, fk in info["foreign_keys"].items():
                    lines.append(
                        f"  🔗 {col_name} → {fk['to_table']}.{fk['to_column']}"
                    )
            lines.append("")

        return "\n".join(lines)

    def get_table_names(self) -> List[str]:
        return list(self.introspect().keys())

    def get_column_names(self, table_name: str) -> List[str]:
        schema = self.introspect()
        if table_name not in schema:
            return []
        return [c["name"] for c in schema[table_name].get("columns", [])]


# Singleton
schema_service = SchemaService()

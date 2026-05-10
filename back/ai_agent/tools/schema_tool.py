"""
Schema Inspector Tool

Lê e resume o schema completo do banco de dados.
"""
import json
import logging
from typing import Any, Dict

from ai_agent.services.schema_service import schema_service

logger = logging.getLogger("ai_agent")


def schema_inspector_tool(force_refresh: bool = False) -> Dict[str, Any]:
    """
    Lê o schema completo do banco e retorna:
    - schema estruturado (dict)
    - resumo textual para o LLM
    - lista de tabelas
    - colunas de data, numéricas e texto por tabela
    - mapeamento de chaves estrangeiras (relacionamentos)
    """
    schema = schema_service.introspect(force_refresh=force_refresh)
    text_summary = schema_service.get_text_summary(schema)
    table_names = list(schema.keys())

    # Mapa de relacionamentos para análise semântica
    relationships = {}
    fact_tables = []
    dimension_tables = []

    for table, info in schema.items():
        fks = info.get("foreign_keys", {})
        if fks:
            relationships[table] = {
                col: fk_info for col, fk_info in fks.items()
            }

        # Heurística: tabelas com muitas FKs são prováveis tabelas fato
        fk_count = len(fks)
        col_count = len(info.get("columns", []))
        if fk_count >= 2 or col_count > 10:
            fact_tables.append(table)
        else:
            dimension_tables.append(table)

    logger.info(
        "Schema inspecionado: %d tabelas (%d fato, %d dimensão).",
        len(table_names),
        len(fact_tables),
        len(dimension_tables),
    )

    return {
        "schema": schema,
        "text_summary": text_summary,
        "table_names": table_names,
        "relationships": relationships,
        "probable_fact_tables": fact_tables,
        "probable_dimension_tables": dimension_tables,
    }

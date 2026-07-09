"""
Entity Resolution Tools — ferramentas do agente entity_resolver.

Resolvem mencoes livres de texto (navio, berco, carga, operador) para os
valores exatos gravados em atracacoes_navio/cargas_atracacao: pre-filtro
ILIKE parametrizado para achar candidatos, ranking por similaridade com
difflib (stdlib, mesma tecnica ja usada em semantic_search_service.py),
com fallback de full-scan quando o pre-filtro nao encontra nada (cobre
typos onde o token nem aparece como substring do valor real).
"""
from __future__ import annotations

import logging
from difflib import SequenceMatcher
from typing import List, Tuple

from django.db import connection
from langchain_core.tools import tool

logger = logging.getLogger("ai_agent")

_TOP_N = 5
_PREFILTER_LIMIT = 200
_FULLSCAN_LIMIT = 2000


def _rank_candidates(query: str, candidates: List[str], top_n: int = _TOP_N) -> List[Tuple[str, float]]:
    q = query.strip().lower()
    scored = [
        (c, SequenceMatcher(None, q, c.strip().lower()).ratio())
        for c in candidates if c
    ]
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored[:top_n]


def _resolve_column_value(table: str, column: str, query: str) -> str:
    """Pre-filtro ILIKE parametrizado sobre `table`/`column` fixos (nao controlados
    pelo LLM); fallback de full-scan se o pre-filtro nao achar candidatos."""
    token = query.strip()
    if not token:
        return "Nenhum termo de busca informado."

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                f"SELECT DISTINCT {column} FROM {table} WHERE {column} ILIKE %s LIMIT %s",
                [f"%{token}%", _PREFILTER_LIMIT],
            )
            candidates = [row[0] for row in cursor.fetchall() if row[0]]

            if not candidates:
                cursor.execute(
                    f"SELECT DISTINCT {column} FROM {table} LIMIT %s",
                    [_FULLSCAN_LIMIT],
                )
                candidates = [row[0] for row in cursor.fetchall() if row[0]]

        if not candidates:
            return f"Nenhum valor encontrado na coluna {table}.{column}."

        ranked = _rank_candidates(token, candidates)
        lines = [f"'{value}' (score {score:.2f})" for value, score in ranked]
        return "Candidatos mais proximos: " + "; ".join(lines)

    except Exception as exc:
        logger.warning("[entity_resolution_tools] Falha ao resolver %s.%s: %s", table, column, exc)
        return f"Erro ao resolver valor: {exc}"


def make_entity_resolution_tools() -> list:
    """Cria as ferramentas de resolucao de entidade do agente entity_resolver."""

    @tool
    def resolve_ship_name(query: str) -> str:
        """
        Resolve o nome de um navio mencionado livremente na pergunta para o valor
        exato armazenado em atracacoes_navio.navio. Use sempre que a pergunta citar
        um navio por nome, mesmo com erro de digitacao ou variacao de grafia.
        """
        return _resolve_column_value("atracacoes_navio", "navio", query)

    @tool
    def resolve_berth(query: str) -> str:
        """
        Resolve um berco mencionado livremente (numero ou descricao) para o valor
        exato armazenado em atracacoes_navio.berco.
        """
        return _resolve_column_value("atracacoes_navio", "berco", query)

    @tool
    def resolve_cargo_name(query: str) -> str:
        """
        Resolve o nome de uma carga/produto mencionado livremente (ex: 'soja',
        'fertilizante') para o valor exato armazenado em cargas_atracacao.nome_carga.
        """
        return _resolve_column_value("cargas_atracacao", "nome_carga", query)

    @tool
    def resolve_operator(query: str) -> str:
        """
        Resolve o nome de um operador/empresa mencionado livremente para o valor
        exato armazenado em cargas_atracacao.operador.
        """
        return _resolve_column_value("cargas_atracacao", "operador", query)

    return [resolve_ship_name, resolve_berth, resolve_cargo_name, resolve_operator]

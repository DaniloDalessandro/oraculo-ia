"""
Agent Service — LangGraph-powered orchestrator.

Mantém a interface pública idêntica à versão anterior para compatibilidade
com os Django views (run_agent retorna o mesmo dict de resposta).

O pipeline de 16 etapas foi substituído por um LangGraph StateGraph
definido em ai_agent/graph/graph.py.
"""
from __future__ import annotations

import logging
import time
from typing import Any

from ai_agent.logs.logger import log_error

logger = logging.getLogger("ai_agent")


class AgentError(Exception):
    """Erro controlado do agente — seguro para exibir ao usuário."""


def run_agent(
    question: str,
    user=None,
    conversation_history: list[dict] | None = None,
) -> dict[str, Any]:
    """
    Executa o agente completo via LangGraph.

    Args:
        question: Pergunta em linguagem natural.
        user: Usuário Django (opcional).
        conversation_history: Lista de {role, text} da conversa atual.

    Returns:
        {answer, intent, sql, validation_sql, filters, chart, status}
    """
    from ai_agent.graph.graph import get_graph

    start_time = time.monotonic()

    initial_state: dict[str, Any] = {
        # Entrada
        "question": question,
        "user": user,
        "conversation_history": conversation_history or [],
        # Valores padrão para evitar KeyError nos nós
        "resolved_question": question,
        "messages": [],
        "intent": "",
        "confidence": "medium",
        "needs_cross_check": False,
        "is_ambiguous": False,
        "ambiguity_confidence": 0.95,
        "follow_up_questions": [],
        "wants_chart": False,
        "detail_level": "normal",
        "schema_info": {},
        "schema_text": "",
        "samples_text": "",
        "port_context": "",
        "preferences": {},
        "generated_sql": "",
        "sql_validation": {},
        "sql_result": {},
        "entities_resolved": {},
        "sql_strategy": "",
        "result_validation": {},
        "cross_check": {"performed": False},
        "stat_analysis": {
            "stat_context_text": "",
            "confidence_score": 0,
            "data_quality_score": 0,
            "analyses_run": [],
            "warnings": [],
        },
        "intel_analysis": {"ran": False, "intel_context_text": "", "news_found": 0},
        "chart": {"should_render": False},
        "final_answer": "",
        "status": "running",
        "error": "",
        "from_cache": False,
        "db_changes": {"has_changes": False, "changes": []},
        "learning_hint": "",
        "context_hint": "",
        "elapsed_ms": 0,
    }

    try:
        graph = get_graph()
        final_state = graph.invoke(initial_state)

        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        final_state["elapsed_ms"] = elapsed_ms

        response = _build_response(final_state, elapsed_ms)

        # Cacheia respostas bem-sucedidas que não vieram do cache
        if final_state.get("status") == "success" and not final_state.get("from_cache"):
            try:
                from ai_agent.tools.cache_lookup_tool import cache_response
                cache_response(
                    final_state.get("resolved_question") or question,
                    response,
                    final_state.get("intent", ""),
                )
            except Exception:
                pass

        return response

    except Exception as exc:
        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        log_error("Erro inesperado no agente", exc, {"question": question})
        logger.error("[Agent] Erro inesperado: %s", exc, exc_info=True)

        return {
            "answer": (
                "Ocorreu um erro interno ao processar sua pergunta. "
                "Por favor, tente novamente ou reformule a pergunta."
            ),
            "intent": "",
            "sql": "",
            "validation_sql": "",
            "filters": {
                "intent": "",
                "tables_used": [],
                "row_count": 0,
                "truncated": False,
                "limited_by_sql": False,
                "limit_value": None,
                "cross_check_performed": False,
                "execution_time_ms": elapsed_ms,
                "from_cache": False,
                "resolved_question": question,
                "db_changes_detected": False,
                "db_changes": [],
                "stat_confidence": 0,
                "stat_quality": 0,
                "stat_analyses": [],
                "stat_warnings": [],
                "intel_ran": False,
                "intel_news_found": 0,
                "intel_scope": "",
                "intel_risk_level": "",
            },
            "chart": {"should_render": False},
            "status": "error",
        }


def _build_response(state: dict[str, Any], elapsed_ms: int) -> dict[str, Any]:
    """Constrói o dict de resposta no formato esperado pelo Django view."""
    result = state.get("sql_result", {})
    cross_check = state.get("cross_check", {})
    db_changes = state.get("db_changes", {})
    stat_analysis = state.get("stat_analysis", {})
    intel_analysis = state.get("intel_analysis", {})

    return {
        "answer": state.get("final_answer", ""),
        "intent": state.get("intent", ""),
        "sql": state.get("generated_sql", ""),
        "validation_sql": cross_check.get("check_sql", ""),
        "filters": {
            "intent": state.get("intent", ""),
            "tables_used": state.get("sql_validation", {}).get("tables_referenced", []),
            "row_count": result.get("row_count", 0),
            "truncated": result.get("truncated", False),
            "limited_by_sql": result.get("limited_by_sql", False),
            "limit_value": result.get("limit_value"),
            "cross_check_performed": cross_check.get("performed", False),
            "execution_time_ms": elapsed_ms,
            "from_cache": state.get("from_cache", False),
            "resolved_question": state.get("resolved_question") or state.get("question", ""),
            "db_changes_detected": db_changes.get("has_changes", False),
            "db_changes": db_changes.get("changes", []),
            "stat_confidence": stat_analysis.get("confidence_score", 0),
            "stat_quality": stat_analysis.get("data_quality_score", 0),
            "stat_analyses": stat_analysis.get("analyses_run", []),
            "stat_warnings": stat_analysis.get("warnings", []),
            "intel_ran": intel_analysis.get("ran", False),
            "intel_news_found": intel_analysis.get("news_found", 0),
            "intel_scope": intel_analysis.get("scope", ""),
            "intel_risk_level": intel_analysis.get("risk_level", ""),
            "sql_strategy": state.get("sql_strategy", ""),
            "entities_resolved": state.get("entities_resolved", {}),
        },
        "chart": state.get("chart", {"should_render": False}),
        "status": state.get("status", "error"),
    }

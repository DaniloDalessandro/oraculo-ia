"""
LangGraph StateGraph — Orquestrador principal do Oraculo AI.

Fluxo:
  START
    → validate_input ────────────────────────────────── [erro] → END
    → detect_db_changes
    → detect_save_intent ────────────────────────────── [port_learning] → END
    → resolve_context
    → check_cache ───────────────────────────────────── [cache_hit] → END
    → load_context ──────────────────────────────────── [sem tabelas] → END
    → check_ambiguity ───────────────────────────────── [clarificação] → END
    → load_db_profile
    → find_similar_sql
    → generate_sql ──────────────────────────────────── [falha] → END
    → execute_sql ───────────────────────────────────── [falha] → END
    → validate_result
    → cross_check (condicional: só se needs_cross_check=True)
    → analyze
    → build_chart
    → generate_answer
    → save_learning
    → log_interaction
    → END
"""
from __future__ import annotations

import logging
from typing import Literal

from langgraph.graph import StateGraph, END, START

from ai_agent.graph.state import AgentState
from ai_agent.graph.nodes import (
    validate_input_node,
    detect_db_changes_node,
    detect_save_intent_node,
    resolve_context_node,
    check_cache_node,
    load_context_node,
    check_ambiguity_node,
    load_db_profile_node,
    find_similar_sql_node,
    generate_sql_node,
    execute_sql_node,
    validate_result_node,
    cross_check_node,
    analyze_node,
    build_chart_node,
    generate_answer_node,
    save_learning_node,
    log_interaction_node,
)

logger = logging.getLogger("ai_agent")


# ─── Roteadores ───────────────────────────────────────────────────────────── #

def _route_after_validate(state: AgentState) -> Literal["detect_db_changes", "__end__"]:
    return "__end__" if state.get("status") == "error" else "detect_db_changes"


def _route_after_save_intent(state: AgentState) -> Literal["resolve_context", "__end__"]:
    return "__end__" if state.get("intent") == "port_learning" else "resolve_context"


def _route_after_cache(state: AgentState) -> Literal["load_context", "__end__"]:
    return "__end__" if state.get("from_cache") else "load_context"


def _route_after_load_context(state: AgentState) -> Literal["check_ambiguity", "__end__"]:
    return "__end__" if state.get("status") == "error" else "check_ambiguity"


def _route_after_ambiguity(state: AgentState) -> Literal["load_db_profile", "__end__"]:
    if state.get("status") == "clarifying" or state.get("intent") == "clarification":
        return "__end__"
    return "load_db_profile"


def _route_after_generate_sql(state: AgentState) -> Literal["execute_sql", "__end__"]:
    if state.get("status") == "partial" or not state.get("generated_sql"):
        return "__end__"
    return "execute_sql"


def _route_after_execute_sql(state: AgentState) -> Literal["validate_result", "__end__"]:
    sql_result = state.get("sql_result", {})
    if not sql_result.get("success") or state.get("status") == "partial":
        return "__end__"
    return "validate_result"


def _route_after_validate_result(state: AgentState) -> Literal["cross_check", "analyze"]:
    return "cross_check" if state.get("needs_cross_check") else "analyze"


# ─── Builder ──────────────────────────────────────────────────────────────── #

def build_graph() -> StateGraph:
    """Constrói e compila o grafo do agente."""
    graph = StateGraph(AgentState)

    # Adiciona nós
    graph.add_node("validate_input",      validate_input_node)
    graph.add_node("detect_db_changes",   detect_db_changes_node)
    graph.add_node("detect_save_intent",  detect_save_intent_node)
    graph.add_node("resolve_context",     resolve_context_node)
    graph.add_node("check_cache",         check_cache_node)
    graph.add_node("load_context",        load_context_node)
    graph.add_node("check_ambiguity",     check_ambiguity_node)
    graph.add_node("load_db_profile",     load_db_profile_node)
    graph.add_node("find_similar_sql",    find_similar_sql_node)
    graph.add_node("generate_sql",        generate_sql_node)
    graph.add_node("execute_sql",         execute_sql_node)
    graph.add_node("validate_result",     validate_result_node)
    graph.add_node("cross_check",         cross_check_node)
    graph.add_node("analyze",             analyze_node)
    graph.add_node("build_chart",         build_chart_node)
    graph.add_node("generate_answer",     generate_answer_node)
    graph.add_node("save_learning",       save_learning_node)
    graph.add_node("log_interaction",     log_interaction_node)

    # Edges fixas
    graph.add_edge(START,               "validate_input")
    graph.add_edge("detect_db_changes", "detect_save_intent")
    graph.add_edge("resolve_context",   "check_cache")
    graph.add_edge("load_db_profile",   "find_similar_sql")
    graph.add_edge("find_similar_sql",  "generate_sql")
    graph.add_edge("cross_check",       "analyze")
    graph.add_edge("analyze",           "build_chart")
    graph.add_edge("build_chart",       "generate_answer")
    graph.add_edge("generate_answer",   "save_learning")
    graph.add_edge("save_learning",     "log_interaction")
    graph.add_edge("log_interaction",   END)

    # Edges condicionais
    graph.add_conditional_edges("validate_input",     _route_after_validate)
    graph.add_conditional_edges("detect_save_intent", _route_after_save_intent)
    graph.add_conditional_edges("check_cache",        _route_after_cache)
    graph.add_conditional_edges("load_context",       _route_after_load_context)
    graph.add_conditional_edges("check_ambiguity",    _route_after_ambiguity)
    graph.add_conditional_edges("generate_sql",       _route_after_generate_sql)
    graph.add_conditional_edges("execute_sql",        _route_after_execute_sql)
    graph.add_conditional_edges("validate_result",    _route_after_validate_result)

    compiled = graph.compile()
    logger.info("[Graph] LangGraph compilado com sucesso.")
    return compiled


# Singleton — compilado uma única vez
_compiled: StateGraph | None = None


def get_graph() -> StateGraph:
    global _compiled
    if _compiled is None:
        _compiled = build_graph()
    return _compiled

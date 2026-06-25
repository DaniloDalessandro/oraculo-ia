"""
AgentState — Estado compartilhado do LangGraph.

Cada nó do grafo recebe o estado completo e retorna um dict parcial
com apenas os campos que ele modificou.
"""
from __future__ import annotations

from typing import Any, Annotated
from typing_extensions import TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    # ── Entrada ────────────────────────────────────────────────────────────── #
    question: str
    user: Any
    conversation_history: list[dict[str, str]]

    # ── Pergunta resolvida (follow-up expandido) ────────────────────────────── #
    resolved_question: str

    # ── Classificação de intenção ──────────────────────────────────────────── #
    intent: str
    confidence: str
    needs_cross_check: bool
    is_ambiguous: bool
    ambiguity_confidence: float
    follow_up_questions: list[str]
    wants_chart: bool
    detail_level: str

    # ── Contexto carregado em paralelo ────────────────────────────────────── #
    schema_info: dict[str, Any]
    schema_text: str
    samples_text: str
    port_context: str
    preferences: dict[str, Any]

    # ── SQL ───────────────────────────────────────────────────────────────── #
    generated_sql: str
    sql_validation: dict[str, Any]
    sql_result: dict[str, Any]

    # ── Validação semântica + cross-check ─────────────────────────────────── #
    result_validation: dict[str, Any]
    cross_check: dict[str, Any]

    # ── Análise estatística + inteligência externa ────────────────────────── #
    stat_analysis: dict[str, Any]
    intel_analysis: dict[str, Any]

    # ── Gráfico ───────────────────────────────────────────────────────────── #
    chart: dict[str, Any]

    # ── Saída ─────────────────────────────────────────────────────────────── #
    final_answer: str
    status: str
    error: str
    from_cache: bool

    # ── Interno ───────────────────────────────────────────────────────────── #
    db_changes: dict[str, Any]
    learning_hint: str
    context_hint: str
    elapsed_ms: int

    # ── Mensagens LangChain (acumuladas com add_messages) ─────────────────── #
    messages: Annotated[list[BaseMessage], add_messages]

"""
Supervisor multiagente para entendimento de pergunta + geracao de SQL.

Substitui generate_sql_node + execute_sql_node como unidade, atras da
feature flag USE_MULTI_AGENT_SQL (ver graph.py). Construido do zero a
cada chamada — mesmo padrao nao-memoizado de analyze_node — porque as
ferramentas do agente sql_writer fecham sobre um dict `session`
especifico da requisicao.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Tuple

from langgraph.prebuilt import create_react_agent
from langgraph_supervisor import create_supervisor

from ai_agent.services.llm_service import get_llm
from ai_agent.tools.entity_resolution_tools import make_entity_resolution_tools
from ai_agent.tools.sql_agent_tools import make_sql_agent_tools
from ai_agent.prompts.multi_agent_sql_prompts import (
    SUPERVISOR_PROMPT,
    ENTITY_AGENT_PROMPT,
    SQL_AGENT_PROMPT,
)

logger = logging.getLogger("ai_agent")

RECURSION_LIMIT = 40


def build_sql_supervisor(
    question: str,
    schema_text: str,
    samples_text: str,
    port_context: str,
    intent: str,
    prefs: Dict[str, Any],
    learning_hint: str,
) -> Tuple[Any, Dict[str, Any]]:
    """Monta o supervisor + os 2 agentes especialistas desta requisicao.

    Retorna (app_compilado, session) — `session` e preenchido pela
    ferramenta run_sql do sql_writer com o ultimo SQL/resultado validos.
    """
    session: Dict[str, Any] = {}
    llm = get_llm()

    entity_agent = create_react_agent(
        llm,
        make_entity_resolution_tools(),
        name="entity_resolver",
        prompt=ENTITY_AGENT_PROMPT.format(question=question),
    )

    sql_agent = create_react_agent(
        llm,
        make_sql_agent_tools(session),
        name="sql_writer",
        prompt=SQL_AGENT_PROMPT.format(
            question=question,
            intent=intent,
            schema=schema_text or "Schema indisponivel.",
            samples=samples_text or "Amostras nao disponiveis.",
            port_context=port_context or "",
            learning_hint=learning_hint or "",
            preferred_limit=prefs.get("preferred_limit", 50),
            preferred_date_field=prefs.get("preferred_date_field", "desatracacao"),
        ),
    )

    app = create_supervisor(
        [entity_agent, sql_agent],
        model=llm,
        prompt=SUPERVISOR_PROMPT.format(question=question, intent=intent),
    ).compile()

    return app, session

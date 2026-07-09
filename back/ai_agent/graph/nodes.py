"""
Nós do LangGraph — cada função recebe AgentState e retorna dict parcial.

Fluxo:
  validate_input → detect_db_changes → detect_save_intent
    → resolve_context → check_cache → load_context → check_ambiguity
    → load_db_profile → find_similar_sql → generate_sql → execute_sql
    → validate_result → [cross_check] → analyze → build_chart
    → generate_answer → save_learning → log_interaction → END
"""
from __future__ import annotations

import json
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from ai_agent.services.llm_service import get_llm, get_structured_llm, invoke_llm
from ai_agent.services.cache_service import cache_service
from ai_agent.services.learning_service import learning_service
from ai_agent.services.schema_service import schema_service
from ai_agent.tools.schema_tool import schema_inspector_tool
from ai_agent.services.memory_service import resolve_with_context, build_context_hint
from ai_agent.tools.sql_executor_tool import sql_executor_tool, format_result_for_llm
from ai_agent.tools.sql_validator_tool import sql_validator_tool
from ai_agent.tools.database_profile_tool import database_profile_tool, format_profiles_for_llm
from ai_agent.tools.port_context_builder_tool import port_context_builder_tool
from ai_agent.tools.port_learning_tool import is_save_intent, port_learning_tool
from ai_agent.tools.learning_tool import (
    find_similar_sql, build_learning_hint,
    save_learned_interaction, mark_sql_failure,
)
from ai_agent.tools.chart_planner_tool import chart_planner_tool
from ai_agent.tools.chart_data_builder_tool import chart_data_builder_tool
from ai_agent.tools.chart_validator_tool import chart_validator_tool
from ai_agent.tools.cache_lookup_tool import (
    get_cached_response, get_cached_sql_result, cache_sql_result,
    get_cached_profile, cache_profile,
)
from ai_agent.tools.conversation_manager_tool import (
    detect_conversation_state, build_clarification_response,
)
from ai_agent.tools.classifier_tool import (
    question_classifier_tool, detect_chart_request, detect_detail_level,
)
from ai_agent.tools.answer_tool import _format_validation, _format_cross_check
from ai_agent.prompts.system_prompt import SYSTEM_PROMPT
from ai_agent.prompts.sql_prompt import SQL_GENERATION_PROMPT
from ai_agent.prompts.answer_prompt import ANSWER_GENERATION_PROMPT
from ai_agent.prompts.validation_prompt import RESULT_VALIDATION_PROMPT
from ai_agent.logs.logger import log_interaction, log_error

logger = logging.getLogger("ai_agent")

MAX_SQL_RETRIES = 3

_SQL_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


# ─── Pydantic schemas para structured output ──────────────────────────────── #

class ResultValidationOutput(BaseModel):
    is_valid: bool
    issues: list[str] = []
    warnings: list[str] = []
    confidence: str = "high"
    suggestion: str = ""


# ─── Helpers ──────────────────────────────────────────────────────────────── #

def _clean_sql(raw: str) -> str:
    raw = _SQL_RE.sub("", raw)
    block = re.search(r"```(?:sql)?\s*(.*?)```", raw, re.DOTALL | re.IGNORECASE)
    if block:
        raw = block.group(1)
    else:
        match = re.search(r"\b(SELECT|WITH)\b", raw, re.IGNORECASE)
        if match:
            raw = raw[match.start():]
    return "\n".join(line for line in raw.strip().splitlines() if line.strip())


def _is_terminal(state: dict) -> bool:
    return state.get("status") in ("error", "clarifying", "port_learning")


# ─── Nós do grafo ─────────────────────────────────────────────────────────── #

def validate_input_node(state: dict) -> dict:
    """Valida a pergunta de entrada."""
    question = state.get("question", "").strip()
    if not question:
        return {"status": "error", "final_answer": "A pergunta não pode estar vazia.", "error": "empty_question"}
    if len(question) > 2000:
        return {"status": "error", "final_answer": "A pergunta é muito longa. Limite: 2000 caracteres.", "error": "question_too_long"}
    return {}


def detect_db_changes_node(state: dict) -> dict:
    """Detecta mudanças no esquema do banco."""
    try:
        from ai_agent.tools.db_change_detector_tool import detect_db_changes, format_changes_for_log
        changes = detect_db_changes()
        if changes.get("has_changes"):
            logger.info("[Graph] Mudanças no banco: %s", format_changes_for_log(changes))
        return {"db_changes": changes}
    except Exception:
        return {"db_changes": {"has_changes": False, "changes": []}}


def detect_save_intent_node(state: dict) -> dict:
    """Detecta se o usuário quer salvar conhecimento portuário."""
    question = state["question"]
    if not is_save_intent(question):
        return {}
    try:
        result = port_learning_tool(question, user=state.get("user"))
        return {
            "final_answer": result["message"],
            "intent": "port_learning",
            "status": "success" if result["saved"] else "error",
        }
    except Exception as exc:
        return {"final_answer": str(exc), "status": "error", "intent": "port_learning"}


def resolve_context_node(state: dict) -> dict:
    """Resolve perguntas de acompanhamento usando o histórico conversacional."""
    history = state.get("conversation_history") or []
    question = state["question"]

    if not history:
        return {"resolved_question": question, "context_hint": ""}

    resolved = resolve_with_context(question, history)
    context_hint = build_context_hint(history)

    if resolved != question:
        logger.info("[Graph] Follow-up resolvido: '%s' → '%s'", question[:60], resolved[:80])

    return {"resolved_question": resolved, "context_hint": context_hint}


def check_cache_node(state: dict) -> dict:
    """Verifica o cache de resposta completa."""
    question = state.get("resolved_question") or state["question"]
    cached = get_cached_response(question)
    if cached:
        logger.info("[Graph] Cache hit para: %s", question[:60])
        return {
            "from_cache": True,
            "final_answer": cached.get("answer", ""),
            "intent": cached.get("intent", ""),
            "generated_sql": cached.get("sql", ""),
            "chart": cached.get("chart", {"should_render": False}),
            "status": "success",
        }
    return {"from_cache": False}


def load_context_node(state: dict) -> dict:
    """Carrega schema, preferências, contexto portuário e classificação em paralelo."""
    question = state.get("resolved_question") or state["question"]
    user = state.get("user")

    def _prefs():
        return learning_service.get_user_preferences(user)

    def _schema():
        return schema_inspector_tool()

    def _port():
        return port_context_builder_tool(question)

    def _classify():
        cls = question_classifier_tool(question)
        wants_chart = detect_chart_request(question, cls.get("intent", ""))
        detail_level = detect_detail_level(question)
        return cls, wants_chart, detail_level

    with ThreadPoolExecutor(max_workers=4) as pool:
        f_prefs = pool.submit(_prefs)
        f_schema = pool.submit(_schema)
        f_port = pool.submit(_port)
        f_cls = pool.submit(_classify)

        prefs = f_prefs.result()
        schema_info = f_schema.result()
        port_context = f_port.result() or ""
        classification, wants_chart, detail_level = f_cls.result()

    if not schema_info.get("table_names"):
        return {
            "status": "error",
            "final_answer": "O banco de dados não possui tabelas acessíveis. Verifique a configuração.",
            "error": "no_tables",
        }

    return {
        "preferences": prefs,
        "schema_info": schema_info,
        "schema_text": schema_info.get("text_summary", ""),
        "port_context": port_context,
        "intent": classification.get("intent", "listagem"),
        "confidence": classification.get("confidence", "medium"),
        "needs_cross_check": classification.get("needs_cross_check", False),
        "is_ambiguous": classification.get("is_ambiguous", False),
        "ambiguity_confidence": classification.get("ambiguity_confidence", 0.95),
        "follow_up_questions": classification.get("follow_up_questions", []),
        "wants_chart": wants_chart,
        "detail_level": detail_level,
    }


def check_ambiguity_node(state: dict) -> dict:
    """Detecta perguntas ambíguas e retorna pedido de clarificação."""
    intent = state.get("intent", "")
    confidence = state.get("confidence", "high")
    is_ambiguous = state.get("is_ambiguous", False)
    ambig_conf = state.get("ambiguity_confidence", 0.95)
    follow_ups = state.get("follow_up_questions") or []
    history = state.get("conversation_history") or []

    conv_state = detect_conversation_state(history)
    was_clarifying = conv_state.get("was_clarifying", False)

    # Intenção claramente ambígua
    if intent == "ambigua" and confidence in ("high", "medium"):
        if not follow_ups:
            follow_ups = [
                "Qual período você deseja analisar (mês, ano específico)?",
                "Sobre qual métrica, berço ou navio?",
            ]
        return {
            "final_answer": build_clarification_response(follow_ups),
            "intent": "clarification",
            "status": "clarifying",
        }

    # Confiança muito baixa no contexto da conversa
    if is_ambiguous and ambig_conf < 0.60 and not was_clarifying:
        if follow_ups:
            return {
                "final_answer": build_clarification_response(follow_ups),
                "intent": "clarification",
                "status": "clarifying",
            }

    return {}


def load_db_profile_node(state: dict) -> dict:
    """Carrega perfil do banco (cardinalidade, amostras) com cache de 1h."""
    try:
        profiles = get_cached_profile()
        if profiles is None:
            logger.info("[Graph] Gerando perfil do banco...")
            profiles = database_profile_tool()
            cache_profile(profiles)
        return {"samples_text": format_profiles_for_llm(profiles)}
    except Exception as exc:
        log_error("Falha ao coletar perfil do banco", exc)
        return {"samples_text": "Perfil do banco indisponível."}


def find_similar_sql_node(state: dict) -> dict:
    """Busca SQL similar no banco de aprendizado."""
    question = state.get("resolved_question") or state["question"]
    intent = state.get("intent", "")
    similar = find_similar_sql(question, intent)
    return {"learning_hint": build_learning_hint(similar)}


def generate_sql_node(state: dict) -> dict:
    """Gera SQL com LLM e lógica de retry (até 3 tentativas)."""
    question = state.get("resolved_question") or state["question"]
    prefs = state.get("preferences") or {}

    last_error: str | None = None

    for attempt in range(1, MAX_SQL_RETRIES + 1):
        retry_hint = state.get("learning_hint", "")
        if last_error:
            retry_hint = (
                f"{retry_hint}\n\n"
                "TENTATIVA ANTERIOR INVÁLIDA:\n"
                f"- Erro: {last_error}\n"
                "- Gere uma consulta nova corrigindo esse erro.\n"
                "- Em subqueries/CTEs, não use aliases internos no SELECT ou ORDER BY externo; "
                "referencie apenas as colunas expostas pela subquery."
            )

        prompt = SQL_GENERATION_PROMPT.format(
            schema=state.get("schema_text", ""),
            samples=state.get("samples_text") or "Amostras não disponíveis.",
            port_context=state.get("port_context") or "",
            intent=state.get("intent", "listagem"),
            question=question,
            context_hint=state.get("context_hint") or "",
            learning_hint=retry_hint,
            preferred_date_field=prefs.get("preferred_date_field", "desatracacao"),
            preferred_limit=prefs.get("preferred_limit", 50),
        )

        try:
            raw = invoke_llm([HumanMessage(content=prompt)])
            sql = _clean_sql(raw)

            if not sql.strip().upper().startswith(("SELECT", "WITH")):
                last_error = "SQL não começa com SELECT ou WITH"
                logger.warning("[Graph] SQL inválido tentativa %d: %s", attempt, last_error)
                continue

            validation = sql_validator_tool(sql)
            if validation["is_valid"]:
                logger.info("[Graph] SQL gerado (tentativa %d): %d chars", attempt, len(sql))
                return {"generated_sql": sql, "sql_validation": validation}

            last_error = "; ".join(validation["errors"])
            logger.warning("[Graph] SQL inválido tentativa %d: %s", attempt, last_error)

        except Exception as exc:
            last_error = str(exc)
            logger.warning("[Graph] Falha SQL tentativa %d: %s", attempt, exc)

    msg = (
        f"Não foi possível gerar uma consulta válida após {MAX_SQL_RETRIES} tentativas. "
        f"Último erro: {last_error}"
    )
    mark_sql_failure(question)
    return {"status": "partial", "error": msg, "final_answer": msg}


def execute_sql_node(state: dict) -> dict:
    """Executa o SQL gerado, verificando o cache de resultados primeiro."""
    sql = state.get("generated_sql", "")
    if not sql:
        return {"status": "error", "error": "Nenhum SQL para executar."}

    # Cache de resultado SQL
    cached = get_cached_sql_result(sql)
    if cached:
        logger.info("[Graph] Cache hit para resultado SQL.")
        cached["from_cache"] = True
        return {"sql_result": cached}

    result = sql_executor_tool(sql, row_limit=200)

    if not result["success"]:
        mark_sql_failure(state.get("resolved_question") or state["question"])
        msg = f"Erro ao executar a consulta: {result.get('error', 'desconhecido')}"
        return {"sql_result": result, "status": "partial", "error": msg, "final_answer": msg}

    cache_sql_result(sql, result, state.get("intent", ""))
    return {"sql_result": result}


def multi_agent_sql_node(state: dict) -> dict:
    """
    Substitui generate_sql_node + execute_sql_node como unidade quando
    USE_MULTI_AGENT_SQL esta habilitado (ver graph.py). Um supervisor
    (langgraph-supervisor) coordena os agentes entity_resolver e sql_writer.

    Sucesso: {generated_sql, sql_validation, sql_result, entities_resolved,
    sql_strategy: "multi_agent"}.
    Falha: {status: "partial", error, final_answer, sql_strategy} — mesmo
    contrato de falha de generate_sql_node/execute_sql_node, para
    _route_after_execute_sql continuar funcionando sem alteracao.
    Qualquer excecao cai para o caminho deterministico existente, marcado
    como sql_strategy="multi_agent_fallback" para nao poluir a comparacao
    A/B entre os dois caminhos.
    """
    question = state.get("resolved_question") or state["question"]
    prefs = state.get("preferences") or {}

    try:
        from ai_agent.graph.multi_agent_sql import build_sql_supervisor, RECURSION_LIMIT

        app, session = build_sql_supervisor(
            question=question,
            schema_text=state.get("schema_text", ""),
            samples_text=state.get("samples_text", ""),
            port_context=state.get("port_context", ""),
            intent=state.get("intent", "listagem"),
            prefs=prefs,
            learning_hint=state.get("learning_hint", ""),
        )

        agent_result = app.invoke(
            {"messages": [{"role": "user", "content": question}]},
            config={"recursion_limit": RECURSION_LIMIT},
        )

        entities_text = ""
        for msg in agent_result.get("messages", []):
            content = getattr(msg, "content", "")
            if isinstance(content, str) and "ENTIDADES RESOLVIDAS" in content:
                entities_text = content

        sql = session.get("sql", "")
        result = session.get("result")

        if not sql or not result or not result.get("success"):
            msg = "O agente multiagente nao produziu uma consulta SQL valida."
            mark_sql_failure(question)
            return {"status": "partial", "error": msg, "final_answer": msg, "sql_strategy": "multi_agent"}

        logger.info(
            "[Graph] Multiagente concluiu SQL: %d chars, %d linhas",
            len(sql), result.get("row_count", 0),
        )

        return {
            "generated_sql": sql,
            "sql_validation": session.get("validation", {}),
            "sql_result": result,
            "entities_resolved": {"raw_text": entities_text},
            "sql_strategy": "multi_agent",
        }

    except Exception as exc:
        logger.warning("[Graph] Pipeline multiagente falhou, usando fallback deterministico: %s", exc)
        fallback = generate_sql_node(state)
        fallback["sql_strategy"] = "multi_agent_fallback"
        if fallback.get("status") == "partial":
            return fallback

        exec_result = execute_sql_node({**state, **fallback})
        return {**fallback, **exec_result, "sql_strategy": "multi_agent_fallback"}


def validate_result_node(state: dict) -> dict:
    """Valida semanticamente o resultado usando structured output Pydantic."""
    question = state.get("resolved_question") or state["question"]
    intent = state.get("intent", "")
    sql = state.get("generated_sql", "")
    result = state.get("sql_result", {})

    result_preview = format_result_for_llm(result, max_rows=15)

    prompt = RESULT_VALIDATION_PROMPT.format(
        question=question,
        intent=intent,
        sql=sql,
        result_preview=result_preview,
        row_count=result.get("row_count", 0),
        truncated=result.get("truncated", False),
    )

    try:
        structured_llm = get_structured_llm(ResultValidationOutput)
        validation = structured_llm.invoke([HumanMessage(content=prompt)])
        return {"result_validation": validation.model_dump()}
    except Exception as exc:
        logger.warning("[Graph] Structured validation falhou, usando fallback: %s", exc)
        # Fallback: JSON manual
        try:
            raw = invoke_llm([HumanMessage(content=prompt)])
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                data = json.loads(match.group())
                return {"result_validation": data}
        except Exception:
            pass
        return {"result_validation": {"is_valid": True, "issues": [], "warnings": [], "confidence": "medium", "suggestion": ""}}


def cross_check_node(state: dict) -> dict:
    """Executa cross-check com SQL alternativo (apenas quando necessário)."""
    result = state.get("sql_result", {})
    if result.get("row_count", 0) <= 1:
        return {"cross_check": {"performed": False}}

    from ai_agent.tools.cross_check_tool import cross_check_tool
    try:
        cross = cross_check_tool(
            question=state.get("resolved_question") or state["question"],
            schema_text=state.get("schema_text", ""),
            main_sql=state.get("generated_sql", ""),
            main_result=result,
        )
        return {"cross_check": cross}
    except Exception as exc:
        logger.warning("[Graph] Cross-check falhou: %s", exc)
        return {"cross_check": {"performed": False}}


def analyze_node(state: dict) -> dict:
    """
    Sub-agente de análise inteligente (create_react_agent do LangGraph).

    O agente decide quais ferramentas usar com base na pergunta e nos dados:
    - Análise estatística (tendências, anomalias, sazonalidade)
    - Inteligência externa (notícias, eventos globais)
    - KPIs operacionais portuários
    """
    from langgraph.prebuilt import create_react_agent
    from ai_agent.tools.lc_tools import make_analysis_tools

    question = state.get("resolved_question") or state["question"]
    result = state.get("sql_result", {})
    intent = state.get("intent", "")

    # Sem dados → pular análise
    if not result.get("success") or result.get("row_count", 0) == 0:
        return {
            "stat_analysis": {
                "stat_context_text": "",
                "confidence_score": 0,
                "data_quality_score": 0,
                "analyses_run": [],
                "warnings": [],
            },
            "intel_analysis": {"ran": False, "intel_context_text": "", "news_found": 0},
        }

    tools = make_analysis_tools(question, result, intent)
    llm = get_llm()

    result_summary = format_result_for_llm(result, max_rows=20)

    system_prompt = (
        "Você é um analista sênior de dados portuários.\n\n"
        f"Pergunta do usuário: {question}\n"
        f"Intenção detectada: {intent}\n"
        f"Dados disponíveis ({result.get('row_count', 0)} linhas):\n{result_summary}\n\n"
        "INSTRUÇÕES:\n"
        "1. Use describe_data() primeiro para entender a estrutura dos dados.\n"
        "2. Use run_statistical_analysis() para detectar tendências, anomalias e padrões.\n"
        "3. Use run_external_intelligence() APENAS se houver anomalias relevantes ou o usuário perguntar 'por que'.\n"
        "4. Use calculate_port_kpis() APENAS se os dados contiverem métricas operacionais (PLR, tonelagem, horas).\n"
        "5. Seja seletivo — não execute análises desnecessárias.\n"
        "6. Retorne um resumo conciso e estruturado dos insights encontrados em português."
    )

    try:
        agent = create_react_agent(llm, tools)
        agent_result = agent.invoke({
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Execute a análise dos dados e retorne os insights encontrados."},
            ]
        })

        # Extrai a última mensagem do assistente
        analysis_text = ""
        for msg in reversed(agent_result.get("messages", [])):
            content = getattr(msg, "content", "")
            if content and not getattr(msg, "tool_call_id", None) and not getattr(msg, "tool_calls", None):
                if isinstance(content, str) and len(content) > 10:
                    analysis_text = content
                    break

        logger.info("[Graph] Sub-agente de análise concluído: %d chars", len(analysis_text))

        return {
            "stat_analysis": {
                "stat_context_text": analysis_text,
                "confidence_score": 0.85,
                "data_quality_score": 0.85,
                "analyses_run": ["intelligent_analysis"],
                "warnings": [],
            },
            "intel_analysis": {"ran": True, "intel_context_text": "", "news_found": 0},
        }

    except Exception as exc:
        logger.warning("[Graph] Sub-agente de análise falhou, usando fallback: %s", exc)
        # Fallback: usar skills originais diretamente
        try:
            from ai_agent.tools.statistics_skill import run_statistics_skill
            from ai_agent.tools.external_intelligence_skill import run_external_intelligence_skill

            stat = run_statistics_skill(question=question, result=result, agent_intent=intent)
            intel = run_external_intelligence_skill(
                question=question, result=result, stat_analysis=stat, intent=intent,
            )
            return {"stat_analysis": stat, "intel_analysis": intel}
        except Exception as exc2:
            logger.warning("[Graph] Fallback de análise também falhou: %s", exc2)
            return {
                "stat_analysis": {"stat_context_text": "", "confidence_score": 0, "data_quality_score": 0, "analyses_run": [], "warnings": []},
                "intel_analysis": {"ran": False, "intel_context_text": "", "news_found": 0},
            }


def build_chart_node(state: dict) -> dict:
    """Monta payload de gráfico se o usuário solicitou explicitamente."""
    if not state.get("wants_chart"):
        return {"chart": {"should_render": False}}

    result = state.get("sql_result", {})
    if not result.get("success") or result.get("row_count", 0) == 0:
        return {"chart": {"should_render": False}}

    try:
        question = state.get("resolved_question") or state["question"]
        plan = chart_planner_tool(question=question, intent=state.get("intent", ""), result=result)
        if not plan.get("should_render"):
            return {"chart": {"should_render": False}}

        data = chart_data_builder_tool(result=result, plan=plan)
        validation = chart_validator_tool(plan=plan, data=data)

        if not validation.get("can_render"):
            return {"chart": {"should_render": False}}

        return {"chart": {
            "should_render": True,
            "type": plan.get("type", "bar"),
            "title": plan.get("title", ""),
            "description": plan.get("description", ""),
            "x_key": plan.get("x_key", ""),
            "y_keys": plan.get("y_keys", []),
            "data": data,
            "warnings": validation.get("warnings", []),
        }}
    except Exception as exc:
        log_error("Falha no pipeline de gráfico", exc)
        return {"chart": {"should_render": False}}


def _clean_answer_formatting(text: str) -> str:
    """Remove negrito/italico (*) e travessao (—) que a LLM insira apesar da instrucao do prompt."""
    text = re.sub(r"\*+", "", text)
    text = text.replace("—", ",")
    return text


def generate_answer_node(state: dict) -> dict:
    """Gera a resposta final usando LCEL: SystemMessage + prompt → LLM → StrOutputParser."""
    from langchain_core.output_parsers import StrOutputParser

    question = state.get("resolved_question") or state["question"]
    intent = state.get("intent", "")
    sql = state.get("generated_sql", "")
    result = state.get("sql_result", {})
    result_validation = state.get("result_validation", {})
    cross_check = state.get("cross_check", {})
    port_context = state.get("port_context", "")
    detail_level = state.get("detail_level", "normal")
    stat_analysis = state.get("stat_analysis", {})
    intel_analysis = state.get("intel_analysis", {})

    # Combina contexto estatístico + inteligência externa
    stat_context = stat_analysis.get("stat_context_text", "")
    intel_text = intel_analysis.get("intel_context_text", "")
    combined_context = f"{stat_context}\n\n{intel_text}".strip() if intel_text else stat_context

    result_text = format_result_for_llm(result, max_rows=50)
    validation_summary = _format_validation(result_validation)
    cross_check_summary = _format_cross_check(cross_check)

    prompt = ANSWER_GENERATION_PROMPT.format(
        question=question,
        intent=intent,
        detail_level=detail_level,
        port_context=port_context or "",
        result=result_text,
        validation=validation_summary,
        cross_check=cross_check_summary,
        stat_context=combined_context,
    )

    try:
        chain = get_llm() | StrOutputParser()
        answer = chain.invoke([
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ])
        answer = _clean_answer_formatting(answer)
        logger.info("[Graph] Resposta gerada: %d chars", len(answer))
        return {"final_answer": answer, "status": "success"}

    except Exception as exc:
        logger.error("[Graph] Falha ao gerar resposta: %s", exc)
        if not result.get("success") or result.get("row_count", 0) == 0:
            return {"final_answer": "Nenhum dado encontrado para esta consulta.", "status": "success"}
        return {
            "final_answer": (
                f"Consulta executada com sucesso. "
                f"{result.get('row_count', 0)} linha(s) retornada(s). "
                "Não foi possível formatar a resposta neste momento."
            ),
            "status": "success",
        }


def save_learning_node(state: dict) -> dict:
    """Salva a interação bem-sucedida no banco de aprendizado."""
    if state.get("from_cache") or state.get("status") != "success":
        return {}

    sql = state.get("generated_sql", "")
    question = state.get("resolved_question") or state["question"]
    chart = state.get("chart", {})

    if not sql:
        return {}

    try:
        save_learned_interaction(
            question=question,
            intent=state.get("intent", ""),
            sql=sql,
            execution_time_ms=state.get("elapsed_ms", 0),
            chart_type=chart.get("type", "") if chart.get("should_render") else "",
        )
    except Exception as exc:
        logger.warning("[Graph] Falha ao salvar aprendizado: %s", exc)

    return {}


def log_interaction_node(state: dict) -> dict:
    """Registra a interação para auditoria."""
    try:
        log_interaction(
            question=state.get("question", ""),
            detected_intent=state.get("intent", ""),
            generated_sql=state.get("generated_sql", ""),
            validation_sql=state.get("cross_check", {}).get("check_sql", ""),
            sql_result=state.get("sql_result", {}).get("dict_rows", []),
            final_answer=state.get("final_answer", ""),
            status=state.get("status", "error"),
            error_message=state.get("error", ""),
            execution_time_ms=state.get("elapsed_ms", 0),
            user=state.get("user"),
        )
    except Exception as exc:
        logger.warning("[Graph] Falha ao logar interação: %s", exc)
    return {}

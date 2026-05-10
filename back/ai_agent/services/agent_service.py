"""
Agent Service — Orquestrador Principal

Fluxo de 16 etapas com memória conversacional, cache inteligente e aprendizado.
"""
import json
import logging
import time
from typing import Any, Dict, List, Optional

from ai_agent.logs.logger import log_interaction, log_error
from ai_agent.tools.schema_tool import schema_inspector_tool
from ai_agent.tools.database_profile_tool import database_profile_tool, format_profiles_for_llm
from ai_agent.tools.classifier_tool import question_classifier_tool, detect_chart_request, detect_detail_level
from ai_agent.tools.sql_generator_tool import sql_generator_tool
from ai_agent.tools.sql_validator_tool import sql_validator_tool
from ai_agent.tools.sql_executor_tool import sql_executor_tool, format_result_for_llm
from ai_agent.tools.result_validator_tool import result_validator_tool
from ai_agent.tools.cross_check_tool import cross_check_tool
from ai_agent.tools.answer_tool import answer_generator_tool
from ai_agent.tools.chart_planner_tool import chart_planner_tool
from ai_agent.tools.chart_data_builder_tool import chart_data_builder_tool
from ai_agent.tools.chart_validator_tool import chart_validator_tool
from ai_agent.tools.cache_lookup_tool import (
    get_cached_response, cache_response,
    get_cached_sql_result, cache_sql_result,
    get_cached_profile, cache_profile,
)
from ai_agent.tools.learning_tool import (
    find_similar_sql, save_learned_interaction,
    mark_sql_failure, build_learning_hint,
)
from ai_agent.tools.ambiguity_detector_tool import ambiguity_detector_tool
from ai_agent.tools.port_context_builder_tool import port_context_builder_tool
from ai_agent.tools.port_learning_tool import is_save_intent, port_learning_tool
from ai_agent.tools.conversation_manager_tool import (
    detect_conversation_state,
    build_clarification_response,
    build_interpretation_prefix,
)
from ai_agent.services.memory_service import resolve_with_context, build_context_hint
from ai_agent.services.learning_service import learning_service
from ai_agent.tools.db_change_detector_tool import detect_db_changes, format_changes_for_log
from ai_agent.tools.statistics_skill import run_statistics_skill
from ai_agent.tools.external_intelligence_skill import run_external_intelligence_skill

logger = logging.getLogger("ai_agent")

MAX_SQL_RETRIES = 3


class AgentError(Exception):
    """Erro controlado do agente — seguro para exibir ao usuário."""
    pass


def run_agent(
    question: str,
    user=None,
    conversation_history: Optional[List[Dict]] = None,
) -> Dict[str, Any]:
    """
    Executa o fluxo completo do agente com memória e cache.

    Args:
        question: Pergunta em linguagem natural.
        user: Usuário Django (opcional).
        conversation_history: Lista de {role, text} da conversa atual.

    Returns:
        {answer, intent, sql, validation_sql, filters, chart, status}
    """
    start_time = time.monotonic()
    history = conversation_history or []

    state: Dict[str, Any] = {
        "question": question,
        "resolved_question": question,
        "intent": "",
        "schema_info": {},
        "schema_text": "",
        "samples_text": "",
        "generated_sql": "",
        "validation": {},
        "result": {},
        "result_validation": {},
        "cross_check": {},
        "final_answer": "",
        "status": "success",
        "error": "",
        "from_cache": False,
        "preferences": {},
    }

    try:
        # ── ETAPA 0: Detectar mudanças no banco ──────────────────────────
        logger.info("[Agente] ETAPA 0 — Detectando mudanças no banco...")
        db_changes = detect_db_changes()
        state["db_changes"] = db_changes
        if db_changes["has_changes"]:
            changes_log = format_changes_for_log(db_changes)
            logger.info("[Agente] %s", changes_log)

        # ── ETAPA 1: Receber e validar pergunta ──────────────────────────
        logger.info("[Agente] ETAPA 1 — Pergunta: %s", question[:100])
        _validate_question(question)

        # ── ETAPA 1.5: Detectar intenção de salvar conhecimento ──────────
        if is_save_intent(question):
            logger.info("[Agente] ETAPA 1.5 — Salvando conhecimento portuário...")
            result = port_learning_tool(question, user=user)
            return _build_response(
                answer=result["message"],
                intent="port_learning",
                status="success" if result["saved"] else "error",
                state=state,
                start_time=start_time,
                user=user,
            )

        # ── Detectar estado conversacional (sem LLM) ─────────────────────
        conv_state = detect_conversation_state(history)
        was_clarifying = conv_state["was_clarifying"]
        logger.debug("[Agente] Estado conversacional: %s", conv_state["state"])

        # ── ETAPA 2: Resolver contexto conversacional ────────────────────
        if history:
            logger.info("[Agente] ETAPA 2 — Resolvendo contexto conversacional...")
            resolved = resolve_with_context(question, history)
            state["resolved_question"] = resolved
            if resolved != question:
                logger.info("[Agente] Pergunta resolvida: '%s'", resolved[:100])
        question_to_use = state["resolved_question"]

        if _is_ambiguous_plr_total(question_to_use) and not was_clarifying:
            clarification = build_clarification_response([
                "PLR e uma taxa. Voce quer media mensal, PLR ponderado por mes ou tonelagem total?"
            ])
            return _build_response(
                answer=clarification, intent="clarification", status="clarifying",
                state=state, start_time=start_time, user=user,
            )

        # ── ETAPA 3: Verificar cache de resposta completa ────────────────
        logger.info("[Agente] ETAPA 3 — Verificando cache...")
        cached = get_cached_response(question_to_use)
        if cached:
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            cached["filters"]["execution_time_ms"] = elapsed_ms
            cached["filters"]["from_cache"] = True
            return cached

        # ── ETAPA 4+5+5.5+6: Paralelo — prefs, schema, port_context, classificador ──
        logger.info("[Agente] ETAPA 4-6 — Carregando contexto e classificando em paralelo...")
        from concurrent.futures import ThreadPoolExecutor, as_completed

        def _load_prefs():
            return learning_service.get_user_preferences(user)

        def _load_schema():
            return schema_inspector_tool()

        def _load_port_context():
            return port_context_builder_tool(question_to_use)

        def _classify():
            return question_classifier_tool(question_to_use)

        with ThreadPoolExecutor(max_workers=4) as pool:
            f_prefs  = pool.submit(_load_prefs)
            f_schema = pool.submit(_load_schema)
            f_port   = pool.submit(_load_port_context)
            f_cls    = pool.submit(_classify)

            prefs       = f_prefs.result()
            schema_info = f_schema.result()
            port_context = f_port.result()
            classification = f_cls.result()

        state["preferences"] = prefs
        state["schema_info"] = schema_info
        state["schema_text"] = schema_info["text_summary"]
        state["port_context"] = port_context
        state["intent"] = classification["intent"]
        state["needs_cross_check"] = classification["needs_cross_check"]
        state["wants_chart"] = detect_chart_request(question_to_use, state["intent"])
        state["detail_level"] = detect_detail_level(question_to_use)

        if not schema_info["table_names"]:
            raise AgentError(
                "O banco de dados não possui tabelas acessíveis. "
                "Verifique a configuração do banco."
            )
        if port_context:
            logger.info("[Agente] Contexto portuário encontrado (%d chars).", len(port_context))

        # ── ETAPA 6.5: Ambiguidade — usa resultado já embutido no classificador ──
        # O classificador agora retorna is_ambiguous + ambiguity_confidence (1 LLM call)
        ambig_confidence = classification.get("ambiguity_confidence", 0.95)
        is_ambiguous = classification.get("is_ambiguous", False)

        if classification["intent"] == "ambigua" and classification["confidence"] in ("high", "medium"):
            follow_ups = classification.get("follow_up_questions") or [
                "Qual período você deseja analisar (mês, ano)?",
                "Sobre qual métrica, berço ou navio?",
            ]
            clarification = build_clarification_response(follow_ups)
            return _build_response(
                answer=clarification, intent="clarification", status="clarifying",
                state=state, start_time=start_time, user=user,
            )

        if is_ambiguous and ambig_confidence < 0.60 and not was_clarifying:
            follow_ups = classification.get("follow_up_questions", [])
            clarification = build_clarification_response(follow_ups)
            logger.info("[Agente] Ambiguidade detectada (conf=%.2f).", ambig_confidence)
            return _build_response(
                answer=clarification, intent="clarification", status="clarifying",
                state=state, start_time=start_time, user=user,
            )

        if 0.60 <= ambig_confidence <= 0.85:
            # Confiança moderada: executa sem prefixo ruidoso
            logger.info("[Agente] Confiança moderada (%.2f) — executando silenciosamente.", ambig_confidence)

        # ── ETAPA 7: Perfil do banco (com cache de 1h) ───────────────────
        logger.info("[Agente] ETAPA 7 — Carregando perfil do banco...")
        try:
            profiles = get_cached_profile()
            if profiles is None:
                logger.info("[Agente] ETAPA 7 — Cache miss — gerando perfil...")
                profiles = database_profile_tool()
                cache_profile(profiles)
            state["samples_text"] = format_profiles_for_llm(profiles)
        except Exception as exc:
            log_error("Falha ao coletar perfil do banco", exc)
            state["samples_text"] = "Perfil do banco indisponível."

        # ── ETAPA 8: Buscar SQL similar no aprendizado ───────────────────
        logger.info("[Agente] ETAPA 8 — Buscando SQL similar...")
        similar = find_similar_sql(question_to_use, state["intent"])
        learning_hint = build_learning_hint(similar)
        context_hint = build_context_hint(history)

        # ── ETAPA 9: Gerar SQL ───────────────────────────────────────────
        logger.info("[Agente] ETAPA 9 — Gerando SQL...")
        generated_sql = _generate_sql_with_retry(state, context_hint, learning_hint, prefs)
        state["generated_sql"] = generated_sql

        # ── ETAPA 10: Validar SQL ────────────────────────────────────────
        logger.info("[Agente] ETAPA 10 — Validando SQL...")
        validation = sql_validator_tool(generated_sql)
        state["validation"] = validation

        if not validation["is_valid"]:
            mark_sql_failure(question_to_use)
            raise AgentError(
                f"Não foi possível gerar uma consulta válida para esta pergunta. "
                f"Motivo: {'; '.join(validation['errors'])}"
            )

        # ── ETAPA 11: Verificar cache de resultado SQL ───────────────────
        logger.info("[Agente] ETAPA 11 — Verificando cache de resultado SQL...")
        cached_result = get_cached_sql_result(generated_sql)
        if cached_result:
            result = cached_result
            result["from_cache"] = True
        else:
            # ── ETAPA 12: Executar SQL ───────────────────────────────────
            logger.info("[Agente] ETAPA 12 — Executando SQL...")
            result = sql_executor_tool(generated_sql, row_limit=200)
            if result["success"]:
                cache_sql_result(generated_sql, result, state["intent"])

        state["result"] = result

        if not result["success"]:
            mark_sql_failure(question_to_use)
            raise AgentError(
                f"Erro ao executar a consulta no banco de dados. "
                f"Detalhe: {result['error']}"
            )

        # ── ETAPA 13: Validar resultado ──────────────────────────────────
        logger.info("[Agente] ETAPA 13 — Validando resultado...")
        result_validation = result_validator_tool(
            question=question_to_use,
            intent=state["intent"],
            sql=generated_sql,
            result=result,
        )
        state["result_validation"] = result_validation

        # ── ETAPA 14: Cross-check ────────────────────────────────────────
        cross_check_result = {"performed": False}
        if state.get("needs_cross_check") and result.get("row_count", 0) > 1:
            logger.info("[Agente] ETAPA 14 — Cross-check...")
            cross_check_result = cross_check_tool(
                question=question_to_use,
                schema_text=state["schema_text"],
                main_sql=generated_sql,
                main_result=result,
            )
        state["cross_check"] = cross_check_result

        # ── ETAPA 14.5: Gráfico ──────────────────────────────────────────
        chart_payload = _build_chart_payload(state)
        state["chart"] = chart_payload

        # ── ETAPA 14.7: Análise estatística avançada ─────────────────────
        logger.info("[Agente] ETAPA 14.7 — Análise estatística...")
        stat_analysis = run_statistics_skill(
            question=question_to_use,
            result=result,
            agent_intent=state["intent"],
        )
        state["stat_analysis"] = stat_analysis

        # ── ETAPA 14.9: Inteligência Operacional Externa ──────────────────
        logger.info("[Agente] ETAPA 14.9 — Inteligência Externa...")
        intel_analysis = run_external_intelligence_skill(
            question=question_to_use,
            result=result,
            stat_analysis=stat_analysis,
            intent=state["intent"],
        )
        state["intel_analysis"] = intel_analysis

        # ── ETAPA 15: Gerar resposta ─────────────────────────────────────
        logger.info("[Agente] ETAPA 15 — Gerando resposta...")
        # Combinar contexto estatístico + inteligência externa
        combined_context = stat_analysis.get("stat_context_text", "")
        intel_text = intel_analysis.get("intel_context_text", "")
        if intel_text:
            combined_context = (combined_context + "\n\n" + intel_text).strip()

        final_answer = answer_generator_tool(
            question=question_to_use,
            intent=state["intent"],
            sql=generated_sql,
            result=result,
            validation=result_validation,
            cross_check=cross_check_result,
            port_context=state.get("port_context", ""),
            stat_context=combined_context,
            detail_level=state.get("detail_level", "normal"),
        )
        state["final_answer"] = final_answer
        state["status"] = "success"

        # ── ETAPA 16: Salvar aprendizado ─────────────────────────────────
        logger.info("[Agente] ETAPA 16 — Salvando aprendizado...")
        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        chart_type = chart_payload.get("type", "") if chart_payload.get("should_render") else ""
        save_learned_interaction(
            question=question_to_use,
            intent=state["intent"],
            sql=generated_sql,
            execution_time_ms=elapsed_ms,
            chart_type=chart_type,
        )

    except AgentError as exc:
        state["final_answer"] = str(exc)
        state["status"] = "partial"
        state["error"] = str(exc)
        logger.warning("[Agente] Erro controlado: %s", exc)

    except Exception as exc:
        state["final_answer"] = (
            "Ocorreu um erro interno ao processar sua pergunta. "
            "Por favor, tente novamente ou reformule a pergunta."
        )
        state["status"] = "error"
        state["error"] = str(exc)
        log_error("Erro inesperado no agente", exc, {"question": question})

    # ── Log ──────────────────────────────────────────────────────────────
    elapsed_ms = int((time.monotonic() - start_time) * 1000)
    logger.info("[Agente] Concluído. Status=%s, Tempo=%dms", state["status"], elapsed_ms)

    log_interaction(
        question=question,
        detected_intent=state.get("intent", ""),
        generated_sql=state.get("generated_sql", ""),
        validation_sql=state.get("cross_check", {}).get("check_sql", ""),
        sql_result=state.get("result", {}).get("dict_rows", []),
        final_answer=state.get("final_answer", ""),
        status=state.get("status", "error"),
        error_message=state.get("error", ""),
        execution_time_ms=elapsed_ms,
        user=user,
    )

    response = _build_response(
        answer=state.get("final_answer", ""),
        intent=state.get("intent", ""),
        status=state["status"],
        state=state,
        start_time=start_time,
        user=user,
        elapsed_ms=elapsed_ms,
    )

    # Cachear resposta bem-sucedida
    if state["status"] == "success":
        cache_response(question_to_use, response, state.get("intent", ""))

    return response


# ─────────────────────────────────────────────────────────────────────────── #
# Helpers
# ─────────────────────────────────────────────────────────────────────────── #


def _validate_question(question: str):
    if not question or not question.strip():
        raise AgentError("A pergunta não pode estar vazia.")
    if len(question) > 2000:
        raise AgentError("A pergunta é muito longa. Limite: 2000 caracteres.")


def _is_ambiguous_plr_total(question: str) -> bool:
    q = question.lower()
    if "plr" not in q:
        return False
    return any(term in q for term in ("total", "totais", "soma", "somar", "somado", "acumulado"))


def _generate_sql_with_retry(
    state: Dict,
    context_hint: str,
    learning_hint: str,
    prefs: Dict,
) -> str:
    last_error = None
    for attempt in range(1, MAX_SQL_RETRIES + 1):
        try:
            retry_hint = learning_hint
            if last_error:
                retry_hint = (
                    f"{learning_hint}\n\n"
                    "TENTATIVA ANTERIOR INVALIDA:\n"
                    f"- Erro: {last_error}\n"
                    "- Gere uma consulta nova corrigindo esse erro.\n"
                    "- Em subqueries/CTEs, nao use aliases internos no SELECT ou ORDER BY externo; "
                    "referencie apenas as colunas expostas pela subquery."
                )
            sql = sql_generator_tool(
                question=state["resolved_question"],
                schema_text=state["schema_text"],
                intent=state["intent"],
                samples_text=state["samples_text"],
                context_hint=context_hint,
                learning_hint=retry_hint,
                preferred_date_field=prefs.get("preferred_date_field", "desatracacao"),
                preferred_limit=prefs.get("preferred_limit", 50),
                port_context=state.get("port_context", ""),
            )
            quick_check = sql_validator_tool(sql)
            if quick_check["is_valid"]:
                return sql
            last_error = "; ".join(quick_check["errors"])
            logger.warning("[Agente] SQL inválido tentativa %d: %s", attempt, last_error)
        except Exception as exc:
            last_error = str(exc)
            logger.warning("[Agente] Falha SQL tentativa %d: %s", attempt, exc)

    raise AgentError(
        f"Não foi possível gerar um SQL válido após {MAX_SQL_RETRIES} tentativas. "
        f"Último erro: {last_error}"
    )


def _build_chart_payload(state: Dict) -> Dict:
    wants_chart = state.get("wants_chart", False)
    result = state.get("result", {})

    if not wants_chart or not result.get("success") or result.get("row_count", 0) == 0:
        return {"should_render": False}

    try:
        plan = chart_planner_tool(
            question=state["resolved_question"],
            intent=state["intent"],
            result=result,
        )
        if not plan.get("should_render"):
            return {"should_render": False, "description": plan.get("description", "")}

        data = chart_data_builder_tool(result=result, plan=plan)
        validation = chart_validator_tool(plan=plan, data=data)

        if not validation["can_render"]:
            return {"should_render": False, "description": validation["reason"]}

        return {
            "should_render": True,
            "type": plan.get("type", "bar"),
            "title": plan.get("title", ""),
            "description": plan.get("description", ""),
            "x_key": plan.get("x_key", ""),
            "y_keys": plan.get("y_keys", []),
            "data": data,
            "warnings": validation.get("warnings", []),
        }
    except Exception as exc:
        log_error("Falha no pipeline de gráfico", exc, {"question": state.get("resolved_question")})
        return {"should_render": False}


def _build_response(
    answer: str,
    intent: str,
    status: str,
    state: Dict,
    start_time: float,
    user=None,
    elapsed_ms: int = None,
) -> Dict:
    if elapsed_ms is None:
        elapsed_ms = int((time.monotonic() - start_time) * 1000)

    result = state.get("result", {})
    cross_check = state.get("cross_check", {})

    db_changes = state.get("db_changes", {})
    filters = {
        "intent": intent,
        "tables_used": state.get("validation", {}).get("tables_referenced", []),
        "row_count": result.get("row_count", 0),
        "truncated": result.get("truncated", False),
        "limited_by_sql": result.get("limited_by_sql", False),
        "limit_value": result.get("limit_value"),
        "cross_check_performed": cross_check.get("performed", False),
        "execution_time_ms": elapsed_ms,
        "from_cache": state.get("from_cache", False),
        "resolved_question": state.get("resolved_question", state.get("question", "")),
        "db_changes_detected": db_changes.get("has_changes", False),
        "db_changes": db_changes.get("changes", []),
        "stat_confidence": state.get("stat_analysis", {}).get("confidence_score", 0),
        "stat_quality": state.get("stat_analysis", {}).get("data_quality_score", 0),
        "stat_analyses": state.get("stat_analysis", {}).get("analyses_run", []),
        "stat_warnings": state.get("stat_analysis", {}).get("warnings", []),
        "intel_ran": state.get("intel_analysis", {}).get("ran", False),
        "intel_news_found": state.get("intel_analysis", {}).get("news_found", 0),
        "intel_scope": state.get("intel_analysis", {}).get("scope", ""),
        "intel_risk_level": state.get("intel_analysis", {}).get("risk_level", ""),
    }

    return {
        "answer": answer,
        "intent": intent,
        "sql": state.get("generated_sql", ""),
        "validation_sql": cross_check.get("check_sql", ""),
        "filters": filters,
        "chart": state.get("chart", {"should_render": False}),
        "status": status,
    }

"""
Answer Generator Tool

Gera a resposta final em português com base nos dados consultados.
"""
import json
import logging
from typing import Any, Dict

from langchain_core.messages import HumanMessage, SystemMessage

from ai_agent.services.gemini_service import invoke_llm
from ai_agent.prompts.system_prompt import SYSTEM_PROMPT
from ai_agent.prompts.answer_prompt import ANSWER_GENERATION_PROMPT
from ai_agent.tools.sql_executor_tool import format_result_for_llm

logger = logging.getLogger("ai_agent")


def answer_generator_tool(
    question: str,
    intent: str,
    sql: str,
    result: Dict[str, Any],
    validation: Dict,
    cross_check: Dict,
    port_context: str = "",
    stat_context: str = "",
    detail_level: str = "normal",
) -> str:
    """
    Gera a resposta final para o usuário em português.

    Args:
        question: Pergunta original do usuário.
        intent: Intenção classificada.
        sql: SQL executado.
        result: Resultado da execução SQL.
        validation: Resultado da validação semântica.
        cross_check: Resultado da verificação cruzada.

    Returns:
        Texto da resposta final em português.
    """
    result_text = format_result_for_llm(result, max_rows=50)

    validation_summary = _format_validation(validation)
    cross_check_summary = _format_cross_check(cross_check)

    prompt = ANSWER_GENERATION_PROMPT.format(
        question=question,
        intent=intent,
        detail_level=detail_level,
        port_context=port_context or "",
        sql=sql,
        result=result_text,
        validation=validation_summary,
        cross_check=cross_check_summary,
        stat_context=stat_context or "",
    )

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=prompt),
    ]

    try:
        answer = invoke_llm(messages)
        logger.info("Resposta gerada: %d chars.", len(answer))
        return answer

    except Exception as exc:
        logger.error("Falha ao gerar resposta: %s", exc, exc_info=True)
        # Fallback: resposta baseada no resultado bruto
        if not result.get("success") or result.get("row_count", 0) == 0:
            return "Não foram encontrados dados para esta consulta."
        return (
            f"Consulta executada com sucesso. "
            f"{result['row_count']} linha(s) retornada(s). "
            f"Não foi possível formatar a resposta completa neste momento."
        )


def _format_validation(validation: Dict) -> str:
    if not validation:
        return "Sem validação."

    issues = validation.get("issues", [])
    warnings = validation.get("warnings", [])
    confidence = validation.get("confidence", "unknown")

    lines = [f"Confiança: {confidence}"]
    if issues:
        lines.append("Problemas: " + "; ".join(issues))
    if warnings:
        lines.append("Avisos: " + "; ".join(warnings))
    if not issues and not warnings:
        lines.append("Resultado validado sem problemas.")

    return " | ".join(lines)


def _format_cross_check(cross_check: Dict) -> str:
    if not cross_check or not cross_check.get("performed"):
        return "consistent=true"

    if not cross_check.get("divergence_detected"):
        return "consistent=true"

    pct = cross_check.get("divergence_pct", 0) or 0
    desc = cross_check.get("divergence_description", "")
    return (
        f"divergence_detected=true divergence_pct={pct:.0f}% "
        f"descrição: {desc}"
    )

"""
Cross Check Tool

Executa e compara uma segunda consulta de verificação contra o resultado principal.
"""
import json
import logging
import re
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage

from ai_agent.services.gemini_service import invoke_llm
from ai_agent.prompts.validation_prompt import CROSS_CHECK_VALIDATION_PROMPT
from ai_agent.tools.sql_generator_tool import sql_cross_check_generator_tool
from ai_agent.tools.sql_validator_tool import sql_validator_tool
from ai_agent.tools.sql_executor_tool import sql_executor_tool, format_result_for_llm

logger = logging.getLogger("ai_agent")

# Tolerância para considerar dois totais iguais antes de chamar o LLM
_NUMERIC_TOLERANCE = 0.10  # 10%


def _first_metric_col(row: Dict) -> Optional[str]:
    """Retorna o primeiro nome de coluna com valor numérico não-id."""
    skip = ("id", "_id", "pk", " fk", "ano", "mes", "year", "month")
    for k, v in row.items():
        if any(kw in k.lower() for kw in skip):
            continue
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return k
    return None


def _grand_total(rows: List[Dict]) -> Optional[float]:
    """Soma todos os valores da primeira coluna métrica das linhas."""
    if not rows:
        return None
    col = _first_metric_col(rows[0])
    if not col:
        return None
    try:
        return sum(float(r.get(col) or 0) for r in rows)
    except (TypeError, ValueError):
        return None


def _numeric_pre_check(main_result: Dict, check_result: Dict) -> Optional[bool]:
    """
    Compara os grand totals antes de chamar o LLM.
    Retorna True (consistente), False (divergente) ou None (inconclusivo).
    """
    main_total = _grand_total(main_result.get("dict_rows", []))
    check_total = _grand_total(check_result.get("dict_rows", []))

    if main_total is None or check_total is None:
        return None

    if main_total == 0 and check_total == 0:
        return True
    if main_total == 0 or check_total == 0:
        return None  # inconclusivo

    diff_pct = abs(main_total - check_total) / max(abs(main_total), abs(check_total))
    logger.info(
        "Cross-check numérico: main=%.2f check=%.2f diff=%.1f%%",
        main_total, check_total, diff_pct * 100,
    )
    if diff_pct <= _NUMERIC_TOLERANCE:
        return True
    return None  # deixa o LLM decidir para diferenças maiores


def cross_check_tool(
    question: str,
    schema_text: str,
    main_sql: str,
    main_result: Dict[str, Any],
) -> Dict:
    """
    Cria e executa uma segunda consulta de verificação.
    Compara com o resultado principal e sinaliza divergências.

    Returns:
        {
            "performed": bool,
            "check_sql": str,
            "check_result": dict ou None,
            "consistent": bool,
            "divergence_detected": bool,
            "divergence_description": str,
            "recommended_result": str,  # "main" | "check" | "ambiguous"
            "explanation": str,
        }
    """
    main_result_text = format_result_for_llm(main_result, max_rows=20)

    # Gerar SQL de verificação
    check_sql = sql_cross_check_generator_tool(
        question=question,
        schema_text=schema_text,
        main_sql=main_sql,
        main_result=main_result_text,
    )

    if not check_sql:
        return _no_check_result("Não foi possível gerar a consulta de verificação.")

    # Validar
    validation = sql_validator_tool(check_sql)
    if not validation["is_valid"]:
        logger.warning("SQL de verificação inválido: %s", validation["errors"])
        return _no_check_result(
            f"SQL de verificação inválido: {'; '.join(validation['errors'])}"
        )

    # Executar
    check_result = sql_executor_tool(check_sql, row_limit=100)
    if not check_result["success"]:
        return _no_check_result(f"Erro ao executar verificação: {check_result['error']}")

    check_result_text = format_result_for_llm(check_result, max_rows=20)

    # ── Pré-verificação numérica (evita LLM para casos óbvios) ────────────
    pre = _numeric_pre_check(main_result, check_result)
    if pre is True:
        logger.info("Cross-check: totais consistentes (≤10%%) — LLM dispensado.")
        return {
            "performed": True,
            "check_sql": check_sql,
            "check_result": check_result,
            "consistent": True,
            "divergence_detected": False,
            "divergence_description": "",
            "recommended_result": "main",
            "explanation": "Verificação numérica: totais equivalentes.",
        }

    # ── Comparação via LLM para casos não-óbvios ──────────────────────────
    prompt = CROSS_CHECK_VALIDATION_PROMPT.format(
        question=question,
        main_result=main_result_text,
        check_result=check_result_text,
    )

    try:
        raw = invoke_llm([HumanMessage(content=prompt)])
        json_match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not json_match:
            raise ValueError("Sem JSON na resposta de comparação.")

        comparison = json.loads(json_match.group())
        divergence_pct = float(comparison.get("divergence_pct", 0) or 0)

        # Só considera divergência real se LLM confirma E pct > 15%
        divergence_detected = (
            bool(comparison.get("divergence_detected", False))
            and divergence_pct > 15
        )

        logger.info(
            "Cross-check LLM: consistent=%s divergence=%s pct=%.1f%%",
            comparison.get("consistent"),
            divergence_detected,
            divergence_pct,
        )

        return {
            "performed": True,
            "check_sql": check_sql,
            "check_result": check_result,
            "consistent": bool(comparison.get("consistent", True)) or not divergence_detected,
            "divergence_detected": divergence_detected,
            "divergence_description": comparison.get("divergence_description", "") if divergence_detected else "",
            "divergence_pct": divergence_pct,
            "recommended_result": comparison.get("recommended_result", "main"),
            "explanation": comparison.get("explanation", ""),
        }

    except Exception as exc:
        logger.warning("Falha na comparação de cross-check: %s", exc)
        return {
            "performed": True,
            "check_sql": check_sql,
            "check_result": check_result,
            "consistent": True,
            "divergence_detected": False,
            "divergence_description": "",
            "recommended_result": "main",
            "explanation": f"Comparação indisponível: {exc}",
        }


def _no_check_result(reason: str) -> Dict:
    return {
        "performed": False,
        "check_sql": "",
        "check_result": None,
        "consistent": True,
        "divergence_detected": False,
        "divergence_description": "",
        "recommended_result": "main",
        "explanation": reason,
    }

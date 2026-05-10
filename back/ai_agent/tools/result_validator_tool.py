"""
Result Validator Tool

Valida o resultado da consulta SQL por heurísticas rápidas (sem LLM).
Elimina uma chamada LLM desnecessária no fluxo do agente.
"""
import logging
from typing import Any, Dict

logger = logging.getLogger("ai_agent")

# Intenções que esperam exatamente 1 linha
_SINGLE_ROW_INTENTS = {"totalizacao", "media"}
# Intenções que esperam múltiplas linhas
_MULTI_ROW_INTENTS = {"ranking", "listagem", "evolucao_temporal", "comparacao"}


def result_validator_tool(
    question: str,
    intent: str,
    sql: str,
    result: Dict[str, Any],
) -> Dict:
    """
    Valida o resultado da consulta por heurísticas determinísticas.

    Returns:
        {
            "is_valid": bool,
            "issues": [str],
            "warnings": [str],
            "confidence": str,
            "suggestion": str,
            "has_data": bool,
        }
    """
    row_count = result.get("row_count", 0)
    truncated = result.get("truncated", False)
    dict_rows = result.get("dict_rows", [])
    columns = result.get("columns", [])

    issues: list[str] = []
    warnings: list[str] = []

    # Sem dados
    if row_count == 0:
        return {
            "is_valid": True,
            "issues": [],
            "warnings": ["A consulta não retornou dados. Verifique os filtros."],
            "confidence": "high",
            "suggestion": "",
            "has_data": False,
        }

    # Truncado
    if truncated:
        warnings.append(f"Resultado limitado — exibindo primeiros {row_count} registros.")

    # Intent espera 1 linha mas veio muitas
    if intent in _SINGLE_ROW_INTENTS and row_count > 50:
        warnings.append(f"Intenção '{intent}' esperava resultado agregado, mas retornou {row_count} linhas. Verifique o GROUP BY.")

    # Intent espera múltiplas linhas mas veio 1
    if intent in _MULTI_ROW_INTENTS and row_count == 1:
        warnings.append("Resultado com apenas 1 linha para uma análise comparativa/temporal.")

    # Valores todos nulos em colunas numéricas
    for col in columns:
        vals = [r.get(col) for r in dict_rows[:20]]
        non_null = [v for v in vals if v is not None]
        if len(vals) > 0 and len(non_null) == 0:
            issues.append(f"Coluna '{col}' retornou apenas valores nulos.")

    # SQL sem WHERE em perguntas específicas (berço, navio, cliente)
    sql_upper = sql.upper()
    q_lower = question.lower()
    if "WHERE" not in sql_upper and any(w in q_lower for w in ("berço", "berco", "navio", "cliente", "operador")):
        warnings.append("Consulta sem filtro WHERE — pode estar retornando dados de todos os registros.")

    confidence = "low" if issues else ("medium" if warnings else "high")

    return {
        "is_valid": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "confidence": confidence,
        "suggestion": "",
        "has_data": True,
    }

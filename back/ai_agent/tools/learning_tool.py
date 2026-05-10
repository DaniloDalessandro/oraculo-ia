"""
Learning Tool

Interface para o sistema de aprendizado do agente.
Busca SQLs similares anteriores e salva novas interações.
"""
import logging
from typing import Dict, Optional

from ai_agent.services.learning_service import learning_service

logger = logging.getLogger("ai_agent")


def find_similar_sql(question: str, intent: str = "") -> Optional[Dict]:
    """
    Busca SQL de consulta similar já validada.

    Returns:
        dict com question_pattern, generated_sql, similarity ou None
    """
    return learning_service.find_similar(question, intent)


def save_learned_interaction(
    question: str,
    intent: str,
    sql: str,
    execution_time_ms: int = 0,
    chart_type: str = "",
) -> None:
    """Salva uma interação bem-sucedida no banco de aprendizado."""
    learning_service.save(
        question=question,
        intent=intent,
        sql=sql,
        execution_time_ms=execution_time_ms,
        chart_type=chart_type,
    )


def mark_sql_failure(question: str) -> None:
    """Penaliza entradas similares após falha na execução."""
    learning_service.mark_failure(question)


def build_learning_hint(similar: Optional[Dict]) -> str:
    """
    Monta texto de hint para incluir no prompt de geração SQL.

    Args:
        similar: Resultado de find_similar_sql ou None.

    Returns:
        String com hint ou string vazia.
    """
    if not similar:
        return ""

    score = similar.get("similarity", 0)
    times = similar.get("times_used", 1)

    return (
        f"\nCONSULTA SIMILAR ANTERIOR (similaridade={score:.0%}, usada {times}x):\n"
        f"Pergunta: {similar['question_pattern']}\n"
        f"SQL validada:\n{similar['generated_sql']}\n"
        f"Use como referência, adaptando para a pergunta atual.\n"
    )

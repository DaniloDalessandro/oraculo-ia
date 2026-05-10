"""
Logger do Agente IA

Registra todas as interações do agente no banco de dados e nos logs do Django.
"""
import json
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("ai_agent")


def log_interaction(
    question: str,
    detected_intent: str = "",
    generated_sql: str = "",
    validation_sql: str = "",
    sql_result: Any = None,
    final_answer: str = "",
    status: str = "success",
    error_message: str = "",
    execution_time_ms: int = 0,
    user=None,
) -> Optional["AIAgentLog"]:
    """
    Persiste o log de uma interação no banco de dados.
    Importação tardia para evitar problemas de importação circular.
    """
    try:
        from ai_agent.models import AIAgentLog

        result_preview = ""
        if sql_result is not None:
            try:
                preview = sql_result[:5] if isinstance(sql_result, list) else sql_result
                result_preview = json.dumps(preview, ensure_ascii=False, default=str)[:2000]
            except Exception:
                result_preview = str(sql_result)[:2000]

        log_entry = AIAgentLog.objects.create(
            user=user,
            question=question[:2000],
            detected_intent=detected_intent[:100],
            generated_sql=generated_sql[:5000],
            validation_sql=validation_sql[:5000],
            sql_result_preview=result_preview,
            final_answer=final_answer[:5000],
            status=status,
            error_message=error_message[:2000],
            execution_time_ms=execution_time_ms,
        )

        log_level = logging.INFO if status == "success" else logging.WARNING
        logger.log(
            log_level,
            "[AIAgent] status=%s intent=%s time=%dms | %s",
            status,
            detected_intent,
            execution_time_ms,
            question[:100],
        )

        return log_entry

    except Exception as e:
        logger.error("[AIAgent] Falha ao registrar log: %s", str(e), exc_info=True)
        return None


def log_error(message: str, exc: Exception = None, context: Dict = None):
    """Registra um erro interno do agente (sem expor ao usuário)."""
    logger.error(
        "[AIAgent] %s | context=%s",
        message,
        json.dumps(context or {}, default=str)[:500],
        exc_info=exc is not None,
    )

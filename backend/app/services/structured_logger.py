"""
Logger estruturado em JSON para observabilidade em produção.
Substitui prints e logs simples por JSON mensurável.
"""

import logging
import sys
import time
from contextvars import ContextVar
from functools import wraps
from typing import Any, Callable

from pythonjsonlogger import jsonlogger

# Context var para propagar request_id ao longo do ciclo de vida
_request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


def _get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = jsonlogger.JsonFormatter(
            fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger


# Loggers por domínio
webhook_logger = _get_logger("oraculo.webhook")
ai_logger = _get_logger("oraculo.ai")
celery_logger = _get_logger("oraculo.celery")
export_logger = _get_logger("oraculo.export")
app_logger = _get_logger("oraculo.app")


def log_event(
    logger: logging.Logger,
    event: str,
    level: str = "info",
    **kwargs: Any,
) -> None:
    """Emite log estruturado com campos extras."""
    extra = {"event": event, "request_id": _request_id_var.get(), **kwargs}
    getattr(logger, level)(event, extra=extra)


def timed(logger: logging.Logger, event: str):
    """Decorator que mede e loga o tempo de execução de funções async."""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                duration_ms = int((time.perf_counter() - start) * 1000)
                log_event(logger, event, duration_ms=duration_ms, status="ok")
                return result
            except Exception as exc:
                duration_ms = int((time.perf_counter() - start) * 1000)
                log_event(logger, event, level="error",
                          duration_ms=duration_ms, status="error", error=str(exc))
                raise
        return wrapper
    return decorator

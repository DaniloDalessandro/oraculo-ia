"""
Cache Lookup Tool

Verifica e armazena resultados em cache Redis.
Suporta cache por pergunta completa e por SQL.
"""
import logging
from typing import Any, Dict, Optional

from ai_agent.services.cache_service import cache_service, TTL_SHORT, TTL_MEDIUM, TTL_LONG

logger = logging.getLogger("ai_agent")

# Intenções que merecem cache mais longo (dados históricos mudam pouco)
_LONG_CACHE_INTENTS = {"comparacao", "evolucao_temporal", "totalizacao"}


def get_cached_response(question: str) -> Optional[Dict]:
    """Retorna resposta cacheada para a pergunta, ou None."""
    key = cache_service.question_key(question)
    result = cache_service.get(key)
    if result:
        logger.info("Cache HIT para pergunta: '%s'", question[:60])
        result["from_cache"] = True
    return result


def cache_response(question: str, response: Dict, intent: str = "") -> None:
    """Armazena a resposta completa em cache."""
    # Não cachear erros ou resultados parciais
    if response.get("status") in ("error", "ambiguous"):
        return

    ttl = TTL_MEDIUM if intent in _LONG_CACHE_INTENTS else TTL_SHORT
    key = cache_service.question_key(question)
    cache_service.set(key, response, ttl=ttl)
    logger.debug("Cache SET (ttl=%ds) para: '%s'", ttl, question[:60])


def get_cached_sql_result(sql: str) -> Optional[Dict]:
    """Retorna resultado cacheado para um SQL específico."""
    key = cache_service.result_key(sql)
    result = cache_service.get(key)
    if result:
        logger.info("Cache HIT para SQL (hash=%s)", key[-8:])
    return result


def cache_sql_result(sql: str, result: Dict, intent: str = "") -> None:
    """Armazena resultado de execução SQL em cache."""
    if not result.get("success"):
        return
    ttl = TTL_MEDIUM if intent in _LONG_CACHE_INTENTS else TTL_SHORT
    key = cache_service.result_key(sql)
    cache_service.set(key, result, ttl=ttl)


def get_cached_profile() -> Optional[Dict]:
    """Retorna perfil do banco cacheado, ou None se expirado/inexistente."""
    key = cache_service.profile_key()
    result = cache_service.get(key)
    if result:
        logger.info("Cache HIT: perfil do banco (1h)")
    return result


def cache_profile(profile: Dict) -> None:
    """Armazena perfil do banco em cache por 1 hora."""
    key = cache_service.profile_key()
    cache_service.set(key, profile, ttl=TTL_LONG)
    logger.debug("Cache SET: perfil do banco (TTL=1h)")


def invalidate_profile() -> None:
    """Invalida o cache do perfil do banco (chamar após carga de dados)."""
    cache_service.delete(cache_service.profile_key())
    logger.info("Cache do perfil do banco invalidado.")


def invalidate_all() -> None:
    """Invalida todo o cache do agente (use após migrations ou carga de dados)."""
    cache_service.invalidate_prefix("oraculo:")
    logger.info("Cache invalidado completamente.")

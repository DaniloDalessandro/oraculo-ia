"""
Cache Service — Redis com fallback em memória.

TTLs:
  SHORT  =  5 min  → dashboards, rankings, KPIs
  MEDIUM = 30 min  → comparativos anuais
  LONG   = 24h     → schema, embeddings
"""
import hashlib
import json
import logging
import os
from typing import Any, Optional

logger = logging.getLogger("ai_agent")

TTL_SHORT = 5 * 60
TTL_MEDIUM = 30 * 60
TTL_LONG = 24 * 60 * 60

REDIS_URL = os.environ.get("REDIS_URL", "redis://oraculo-redis:6379/0")


class CacheService:
    def __init__(self):
        self._client = None
        self._mem: dict = {}  # fallback em memória

    # ------------------------------------------------------------------ #
    # Conexão lazy
    # ------------------------------------------------------------------ #

    def _get_client(self):
        if self._client is not None:
            return self._client
        try:
            import redis
            self._client = redis.from_url(REDIS_URL, decode_responses=True, socket_connect_timeout=2)
            self._client.ping()
            logger.info("CacheService: Redis conectado em %s", REDIS_URL)
        except Exception as exc:
            logger.warning("CacheService: Redis indisponível (%s). Usando cache em memória.", exc)
            self._client = None
        return self._client

    # ------------------------------------------------------------------ #
    # API pública
    # ------------------------------------------------------------------ #

    def get(self, key: str) -> Optional[Any]:
        client = self._get_client()
        try:
            if client:
                raw = client.get(key)
                return json.loads(raw) if raw else None
        except Exception:
            pass
        return self._mem.get(key)

    def set(self, key: str, value: Any, ttl: int = TTL_SHORT) -> None:
        client = self._get_client()
        serialized = json.dumps(value, default=str)
        try:
            if client:
                client.setex(key, ttl, serialized)
                return
        except Exception:
            pass
        self._mem[key] = json.loads(serialized)

    def delete(self, key: str) -> None:
        client = self._get_client()
        try:
            if client:
                client.delete(key)
        except Exception:
            pass
        self._mem.pop(key, None)

    def invalidate_prefix(self, prefix: str) -> None:
        """Remove todas as chaves que começam com o prefixo (só Redis)."""
        client = self._get_client()
        try:
            if client:
                keys = client.keys(f"{prefix}*")
                if keys:
                    client.delete(*keys)
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    # Helpers de chave
    # ------------------------------------------------------------------ #

    @staticmethod
    def _hash(text: str) -> str:
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    def schema_key(self) -> str:
        return "oraculo:schema:full"

    def profile_key(self) -> str:
        return "oraculo:db:profile"

    def result_key(self, sql: str) -> str:
        return f"oraculo:result:{self._hash(sql)}"

    def question_key(self, question: str) -> str:
        normalized = question.strip().lower()
        return f"oraculo:question:{self._hash(normalized)}"


cache_service = CacheService()

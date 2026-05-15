"""
DB Change Detector Tool

Detecta mudanças no banco de dados (inserções, exclusões, atualizações)
comparando snapshots de contagem de linhas por tabela armazenados no Redis.

Executado como ETAPA 0 do agente — antes de qualquer consulta — para:
- Invalidar caches obsoletos quando dados mudaram
- Informar o agente sobre o estado atual do banco
- Logar mudanças detectadas para auditoria
"""
import logging
import time as _time
from typing import Dict, List, Any

from django.db import connection

from ai_agent.services.cache_service import cache_service, TTL_MEDIUM

logger = logging.getLogger("ai_agent")

_SNAPSHOT_KEY = "db_snapshot:row_counts"
_SNAPSHOT_TTL = TTL_MEDIUM

# Cache in-memory: evita queries ao banco a cada request do agente.
# Só re-executa a verificação real a cada 5 minutos por processo Django.
_LOCAL_CACHE: Dict = {}
_LOCAL_TTL = 5 * 60  # segundos

# Tabelas a ignorar (sistema / auth / django internals)
_IGNORED_PREFIXES = (
    "auth_", "django_", "ai_agent_aiagentlog", "ai_agent_aiagentfeedback",
)


def _get_row_estimates() -> Dict[str, int]:
    """
    Retorna estimativas de linhas por tabela usando pg_stat_user_tables.
    Uma única query vs N COUNT(*) — muito mais rápido.
    Estimativas são suficientes para detecção de mudança.
    """
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT relname, n_live_tup
            FROM pg_stat_user_tables
            WHERE schemaname = 'public'
            ORDER BY relname
        """)
        rows = cursor.fetchall()

    counts: Dict[str, int] = {}
    for name, n_live in rows:
        if not any(name.startswith(p) for p in _IGNORED_PREFIXES):
            counts[name] = int(n_live or 0)
    return counts


def detect_db_changes() -> Dict[str, Any]:
    """
    Compara contagem atual de linhas com snapshot anterior no Redis.
    Usa cache in-memory de 5 minutos para evitar queries a cada request.

    Returns:
        {
            "has_changes": bool,
            "changes": [{"table": str, "type": "insert"|"delete", "delta": int}],
            "snapshot_age_s": int | None,
            "current_counts": {table: count},
        }
    """
    # Cache in-memory: retorna resultado anterior se ainda dentro do TTL
    now = _time.monotonic()
    if _LOCAL_CACHE.get("result") and now - _LOCAL_CACHE.get("ts", 0) < _LOCAL_TTL:
        logger.debug("db_change_detector: cache in-memory ativo — pulando queries.")
        return _LOCAL_CACHE["result"]

    current = _get_row_estimates()

    previous = cache_service.get(_SNAPSHOT_KEY)

    changes: List[Dict[str, Any]] = []

    if previous:
        prev_counts: Dict[str, int] = previous.get("counts", {})

        for table, cur_count in current.items():
            if cur_count < 0:
                continue
            prev_count = prev_counts.get(table)

            if prev_count is None:
                # Tabela nova
                changes.append({"table": table, "type": "new_table", "delta": cur_count})
            elif cur_count > prev_count:
                delta = cur_count - prev_count
                changes.append({"table": table, "type": "insert", "delta": delta})
                logger.info(
                    "db_change_detector: +%d linhas inseridas em '%s' (era %d, agora %d)",
                    delta, table, prev_count, cur_count,
                )
            elif cur_count < prev_count:
                delta = prev_count - cur_count
                changes.append({"table": table, "type": "delete", "delta": delta})
                logger.info(
                    "db_change_detector: -%d linhas removidas de '%s' (era %d, agora %d)",
                    delta, table, prev_count, cur_count,
                )

        # Tabelas removidas
        for table in prev_counts:
            if table not in current:
                changes.append({"table": table, "type": "dropped_table", "delta": 0})
    else:
        logger.info("db_change_detector: Nenhum snapshot anterior — criando baseline.")

    # Salva snapshot atualizado
    cache_service.set(_SNAPSHOT_KEY, {"counts": current}, ttl=_SNAPSHOT_TTL)

    has_changes = bool(changes)

    if has_changes:
        # Invalida caches de respostas e SQL para forçar reavaliação com dados novos
        cache_service.invalidate_prefix("qa:")
        cache_service.invalidate_prefix("sql:")
        logger.info(
            "db_change_detector: %d mudança(s) detectada(s) — caches invalidados.",
            len(changes),
        )
    else:
        logger.info("db_change_detector: Nenhuma mudança detectada.")

    result = {
        "has_changes": has_changes,
        "changes": changes,
        "current_counts": current,
    }

    # Salva no cache in-memory (próximos requests dentro de 5 min pularão as queries)
    _LOCAL_CACHE["result"] = result
    _LOCAL_CACHE["ts"] = now

    return result


def format_changes_for_log(result: Dict[str, Any]) -> str:
    """Formata as mudanças detectadas para log/contexto do agente."""
    if not result["has_changes"]:
        return ""

    lines = []
    for c in result["changes"]:
        t = c["type"]
        tbl = c["table"]
        delta = c["delta"]
        if t == "insert":
            lines.append(f"  +{delta} linhas inseridas em '{tbl}'")
        elif t == "delete":
            lines.append(f"  -{delta} linhas removidas de '{tbl}'")
        elif t == "new_table":
            lines.append(f"  Nova tabela detectada: '{tbl}' ({delta} linhas)")
        elif t == "dropped_table":
            lines.append(f"  Tabela removida: '{tbl}'")

    return "MUDANÇAS NO BANCO DETECTADAS DESDE A ÚLTIMA CONSULTA:\n" + "\n".join(lines)

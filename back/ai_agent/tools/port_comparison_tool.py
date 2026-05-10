"""
Port Comparison Tool

Pesquisa na web se outros portos brasileiros e internacionais
tiveram comportamento similar, ajudando a determinar se o problema
é local, regional, nacional ou global.
"""
import logging
from typing import Any, Dict, List

from ai_agent.tools.external_news_search_tool import _ddg_search

logger = logging.getLogger("ai_agent")

_BR_PORTS = ["Santos", "Paranaguá", "Suape", "Rio Grande", "Pecém", "Vila do Conde"]
_INTL_ROUTES = ["Canal de Suez", "Mar Vermelho", "Estreito de Malaca", "Cabo da Boa Esperança"]


def port_comparison_tool(
    cargo_type: str = "",
    period: str = "",
    anomaly_direction: str = "queda",
) -> Dict[str, Any]:
    """
    Verifica se outros portos tiveram comportamento semelhante no período.

    Args:
        cargo_type:        Tipo de carga afetada
        period:            Período da anomalia
        anomaly_direction: "queda" ou "aumento"

    Returns:
        {
            "scope": "local|regional|nacional|global",
            "scope_confidence": float,
            "port_news": [...],
            "similar_ports": [...],
            "scope_explanation": str,
        }
    """
    period_text = period or "2025"
    direction_text = "queda movimentação" if anomaly_direction == "queda" else "aumento congestionamento"

    # Buscar notícias de portos brasileiros similares
    queries = [
        f"porto brasileiro {direction_text} {cargo_type} {period_text}",
        f"congestionamento portuário Brasil {period_text}",
        f"logística marítima Brasil {cargo_type} {period_text}",
        f"Canal de Suez Mar Vermelho impacto Brasil {period_text}",
    ]

    all_port_news: List[Dict] = []
    seen_urls = set()

    for query in queries:
        results = _ddg_search(query, max_results=3, region="br-pt")
        for r in results:
            url = r.get("url", "")
            if url and url not in seen_urls and url.startswith("http"):
                seen_urls.add(url)
                all_port_news.append(r)

    # Determinar escopo baseado nas notícias encontradas
    scope, scope_confidence = _determine_scope(all_port_news, cargo_type)

    # Identificar portos mencionados nas notícias
    similar_ports = _extract_mentioned_ports(all_port_news)

    explanation = _build_scope_explanation(scope, similar_ports, anomaly_direction, cargo_type)

    logger.info("[PortComparison] Scope=%s conf=%.2f ports=%s", scope, scope_confidence, similar_ports)

    return {
        "scope": scope,
        "scope_confidence": scope_confidence,
        "port_news": all_port_news[:6],
        "similar_ports": similar_ports,
        "scope_explanation": explanation,
    }


def _determine_scope(news: List[Dict], cargo_type: str) -> tuple:
    """Determina o escopo do problema baseado nas notícias."""
    if not news:
        return "local", 0.40

    text_all = " ".join(
        (r.get("title", "") + " " + r.get("summary", "")).lower()
        for r in news
    )

    global_kw = ["canal de suez", "mar vermelho", "global", "mundial", "internacional", "houthi", "cape horn"]
    national_kw = ["brasil", "porto santos", "paranaguá", "suape", "rio grande", "pecém"]
    regional_kw = ["nordeste", "maranhão", "pará", "norte", "itaqui", "são luís"]

    global_hits = sum(1 for kw in global_kw if kw in text_all)
    national_hits = sum(1 for kw in national_kw if kw in text_all)
    regional_hits = sum(1 for kw in regional_kw if kw in text_all)

    if global_hits >= 2:
        return "global", min(0.5 + global_hits * 0.1, 0.90)
    if national_hits >= 2:
        return "nacional", min(0.5 + national_hits * 0.08, 0.85)
    if regional_hits >= 1:
        return "regional", 0.65
    return "local", 0.50


def _extract_mentioned_ports(news: List[Dict]) -> List[str]:
    """Extrai nomes de portos mencionados nas notícias."""
    all_ports = _BR_PORTS + ["Itaqui", "São Luís"]
    mentioned = []
    text_all = " ".join(
        (r.get("title", "") + " " + r.get("summary", "")).lower()
        for r in news
    )
    for port in all_ports:
        if port.lower() in text_all and port not in mentioned:
            mentioned.append(port)
    return mentioned


def _build_scope_explanation(
    scope: str, similar_ports: List[str], direction: str, cargo: str
) -> str:
    scope_labels = {
        "global": "O comportamento parece ser global, afetando múltiplos portos e rotas internacionais.",
        "nacional": "O comportamento parece ser de escala nacional, afetando outros portos brasileiros.",
        "regional": "O comportamento parece ser regional, limitado ao Norte/Nordeste do Brasil.",
        "local": "O comportamento parece ser local, específico ao Porto do Itaqui.",
    }
    base = scope_labels.get(scope, "Escopo indeterminado.")
    if similar_ports:
        base += f" Portos com movimento similar identificados: {', '.join(similar_ports)}."
    return base

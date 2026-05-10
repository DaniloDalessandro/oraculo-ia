"""
External News Search Tool

Pesquisa notícias reais na web usando DuckDuckGo.
Retorna resultados com title, summary, source, date e URL real.
NUNCA inventa links — apenas retorna o que a busca encontrar.
"""
import logging
from typing import Any, Dict, List

logger = logging.getLogger("ai_agent")

# Mapeamento cargo → palavras-chave de pesquisa
_CARGO_KEYWORDS: Dict[str, List[str]] = {
    "fertilizante": ["fertilizante", "potássio", "ureia", "NPK", "Russia Ukraine fertilizer"],
    "graos": ["soja", "milho", "trigo", "grãos", "agronegócio", "safra"],
    "petroleo": ["petróleo", "combustível", "bunker", "crude oil", "OPEP"],
    "minerio": ["minério de ferro", "minério", "iron ore", "Vale", "China demanda"],
    "celulose": ["celulose", "papel", "eucalipto", "pulp market"],
    "combustivel": ["combustível", "diesel", "gasolina", "etanol", "GNL"],
    "container": ["contêiner", "container", "frete marítimo", "congestionamento portuário"],
    "geral": ["porto marítimo", "logística marítima", "frete global", "shipping"],
}

_PORT_KEYWORDS = [
    "porto Santos", "porto Paranaguá", "porto Itaqui", "porto Suape",
    "porto Rio Grande", "congestionamento porto brasileiro",
    "Canal de Suez", "Mar Vermelho", "Houthi", "bloqueio marítimo",
]

_GLOBAL_EVENTS = [
    "guerra Rússia Ucrânia logística",
    "crise logística global 2024 2025",
    "alta frete marítimo",
    "economia China commodities",
    "crise cadeia suprimentos",
]


def _ddg_search(query: str, max_results: int = 5, region: str = "br-pt") -> List[Dict]:
    """Executa busca real no DuckDuckGo. Retorna lista de resultados."""
    try:
        from duckduckgo_search import DDGS
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, region=region, max_results=max_results):
                results.append({
                    "title": r.get("title", ""),
                    "summary": r.get("body", "")[:300],
                    "source": r.get("source") or _extract_domain(r.get("href", "")),
                    "url": r.get("href", ""),
                    "date": r.get("published", ""),
                })
        return results
    except Exception as exc:
        logger.warning("[NewsSearch] DuckDuckGo falhou para '%s': %s", query, exc)
        return []


def _extract_domain(url: str) -> str:
    """Extrai domínio de uma URL."""
    try:
        from urllib.parse import urlparse
        return urlparse(url).netloc or url
    except Exception:
        return url


def _score_relevance(result: Dict, keywords: List[str]) -> float:
    """Pontua relevância de um resultado para os keywords dados."""
    text = (result.get("title", "") + " " + result.get("summary", "")).lower()
    hits = sum(1 for kw in keywords if kw.lower() in text)
    return round(min(hits / max(len(keywords), 1), 1.0), 2)


def external_news_search_tool(
    anomaly_description: str,
    cargo_type: str = "",
    period: str = "",
    max_results_per_query: int = 4,
) -> Dict[str, Any]:
    """
    Pesquisa notícias externas relevantes para uma anomalia operacional detectada.

    Args:
        anomaly_description: Descrição da anomalia (ex: "queda 18% fertilizante jan/2025")
        cargo_type:          Tipo de carga afetada (ex: "fertilizante")
        period:              Período afetado (ex: "janeiro 2025")
        max_results_per_query: Máximo de resultados por busca

    Returns:
        {
            "news": [...],
            "total_found": int,
            "queries_executed": [...],
        }
    """
    queries = []
    all_results: List[Dict] = []
    relevance_keywords: List[str] = []

    # Query principal com a anomalia
    base_query = f"porto logística {anomaly_description}"
    if period:
        base_query += f" {period}"
    queries.append(base_query)

    # Queries por tipo de carga
    cargo_key = _detect_cargo_key(cargo_type)
    if cargo_key and cargo_key in _CARGO_KEYWORDS:
        kws = _CARGO_KEYWORDS[cargo_key]
        relevance_keywords.extend(kws)
        for kw in kws[:2]:  # max 2 queries por cargo
            queries.append(f"{kw} impacto logístico Brasil {period or '2025'}")

    # Queries de eventos globais
    for ev in _GLOBAL_EVENTS[:2]:
        queries.append(ev)

    # Queries de outros portos
    queries.append("congestionamento porto brasileiro logística marítima 2025")

    # Executar buscas (com deduplicação por URL)
    seen_urls = set()
    for query in queries[:6]:  # máximo 6 queries para não demorar
        results = _ddg_search(query, max_results=max_results_per_query)
        for r in results:
            url = r.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                r["relevance_score"] = _score_relevance(r, relevance_keywords or [anomaly_description])
                all_results.append(r)

    # Ordenar por relevância
    all_results.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)

    # Filtrar apenas com URL válida
    all_results = [r for r in all_results if r.get("url", "").startswith("http")]

    logger.info(
        "[NewsSearch] %d notícias encontradas em %d queries para: %s",
        len(all_results), len(queries), anomaly_description[:60],
    )

    return {
        "news": all_results[:15],  # máximo 15 notícias no total
        "total_found": len(all_results),
        "queries_executed": queries,
    }


def _detect_cargo_key(cargo_type: str) -> str:
    """Mapeia texto livre de cargo para chave interna."""
    ct = cargo_type.lower()
    if any(w in ct for w in ["fertil", "potáss", "ureia", "npk"]):
        return "fertilizante"
    if any(w in ct for w in ["soja", "milho", "grão", "cereal", "trigo"]):
        return "graos"
    if any(w in ct for w in ["petró", "crude", "oleo", "óleo"]):
        return "petroleo"
    if any(w in ct for w in ["minério", "ferro", "iron"]):
        return "minerio"
    if any(w in ct for w in ["celulose", "papel", "pulp"]):
        return "celulose"
    if any(w in ct for w in ["combust", "diesel", "gasolina", "gnl"]):
        return "combustivel"
    if any(w in ct for w in ["contêiner", "container"]):
        return "container"
    return "geral"

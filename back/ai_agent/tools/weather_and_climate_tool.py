"""
Weather and Climate Tool

Pesquisa fatores climáticos e meteorológicos que podem ter impactado
a operação portuária no período analisado.
"""
import logging
from typing import Any, Dict, List

from ai_agent.tools.external_news_search_tool import _ddg_search

logger = logging.getLogger("ai_agent")

_CLIMATE_EVENTS = [
    "tempestade tropical", "ciclone", "furacão", "seca extrema",
    "enchente", "El Niño", "La Niña", "ventos fortes porto",
    "maré alta", "chuvas intensas", "fenômeno climático",
]

_PORT_REGION = "São Luís Maranhão Itaqui"


def weather_and_climate_tool(
    period: str = "",
    region: str = "Maranhão São Luís",
) -> Dict[str, Any]:
    """
    Verifica fatores climáticos que podem ter afetado a operação portuária.

    Args:
        period: Período de análise
        region: Região geográfica do porto

    Returns:
        {
            "climate_events": [...],
            "climate_news": [...],
            "climate_risk_level": "alto|medio|baixo",
            "climate_summary": str,
        }
    """
    period_text = period or "2024 2025"

    queries = [
        f"clima extremo {region} {period_text} porto",
        f"El Niño La Niña Brasil logística {period_text}",
        f"tempestade chuvas {region} {period_text}",
        f"fenômeno climático impacto porto maranhão {period_text}",
        f"seca nordeste Brasil {period_text} impacto agronegócio",
    ]

    climate_news: List[Dict] = []
    seen_urls: set = set()

    for query in queries[:4]:  # limitar a 4 queries
        results = _ddg_search(query, max_results=3, region="br-pt")
        for r in results:
            url = r.get("url", "")
            if url and url not in seen_urls and url.startswith("http"):
                seen_urls.add(url)
                climate_news.append(r)

    # Detectar eventos climáticos mencionados
    detected_events = _detect_climate_events(climate_news)

    # Calcular nível de risco climático
    risk_level = _assess_climate_risk(detected_events, climate_news)

    summary = _build_climate_summary(detected_events, risk_level, period)

    logger.info(
        "[WeatherClimate] %d eventos detectados, risco=%s, %d notícias",
        len(detected_events), risk_level, len(climate_news),
    )

    return {
        "climate_events": detected_events,
        "climate_news": climate_news[:5],
        "climate_risk_level": risk_level,
        "climate_summary": summary,
    }


def _detect_climate_events(news: List[Dict]) -> List[str]:
    """Detecta eventos climáticos mencionados nas notícias."""
    text_all = " ".join(
        (r.get("title", "") + " " + r.get("summary", "")).lower()
        for r in news
    )
    detected = []
    for event in _CLIMATE_EVENTS:
        if event.lower() in text_all:
            detected.append(event)
    # Adicionar El Niño/La Niña se mencionado
    if "el niño" in text_all or "el nino" in text_all:
        if "El Niño" not in detected:
            detected.append("El Niño")
    if "la niña" in text_all or "la nina" in text_all:
        if "La Niña" not in detected:
            detected.append("La Niña")
    return detected


def _assess_climate_risk(events: List[str], news: List[Dict]) -> str:
    """Avalia o nível de risco climático."""
    high_risk_kw = ["ciclone", "furacão", "enchente", "seca extrema", "emergência climática"]
    medium_risk_kw = ["el niño", "la niña", "tempestade", "chuvas intensas"]

    text_all = " ".join(
        (r.get("title", "") + " " + r.get("summary", "")).lower()
        for r in news
    )

    if any(kw in text_all for kw in high_risk_kw):
        return "alto"
    if any(kw in text_all for kw in medium_risk_kw) or len(events) >= 2:
        return "medio"
    return "baixo"


def _build_climate_summary(events: List[str], risk_level: str, period: str) -> str:
    if not events:
        return f"Nenhum evento climático significativo identificado para o período {period or 'analisado'}."

    risk_labels = {"alto": "ALTO", "medio": "MÉDIO", "baixo": "BAIXO"}
    events_text = ", ".join(events[:4])
    return (
        f"Risco climático {risk_labels.get(risk_level, 'NÃO AVALIADO')} "
        f"para o período {period or 'analisado'}. "
        f"Eventos identificados: {events_text}."
    )

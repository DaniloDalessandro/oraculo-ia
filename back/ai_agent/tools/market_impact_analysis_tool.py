"""
Market Impact Analysis Tool

Analisa impacto de fatores de mercado (commodities, câmbio, frete)
sobre a operação portuária detectada.
"""
import logging
from typing import Any, Dict, List

logger = logging.getLogger("ai_agent")

# Mapeamento cargo → commodities e métricas de mercado relevantes
_MARKET_FACTORS: Dict[str, Dict] = {
    "fertilizante": {
        "commodities": ["Ureia (FOB Meio-Golfo)", "Cloreto de Potássio", "DAP", "MAP"],
        "indices": ["Baltic Fertilizer Index", "Preço do gás natural europeu"],
        "currencies": ["USD/BRL", "RUB/USD"],
        "supply_risks": ["Exportações russas", "Exportações bielorrussas", "Capacidade de Marrocos"],
        "demand_drivers": ["Safra brasileira", "Plantio soja/milho", "Demanda global de alimentos"],
    },
    "graos": {
        "commodities": ["Soja CBOT", "Milho CBOT", "Trigo CBOT", "Farelo de soja"],
        "indices": ["WASDE (USDA)", "Prêmio de exportação"],
        "currencies": ["USD/BRL"],
        "supply_risks": ["El Niño/La Niña", "Safra Argentina", "Exportações Ucrânia"],
        "demand_drivers": ["Demanda chinesa", "Demanda europeia", "Preços de proteína animal"],
    },
    "petroleo": {
        "commodities": ["Brent crude", "WTI", "Bunker VLSFO", "Diesel marítimo"],
        "indices": ["OPEP+ produção", "Estoques EIA"],
        "currencies": ["USD/BRL", "PETRO"],
        "supply_risks": ["Conflitos Oriente Médio", "Sanções Venezuela/Irã", "Decisões OPEP"],
        "demand_drivers": ["Crescimento global", "Demanda China", "Transição energética"],
    },
    "minerio": {
        "commodities": ["Minério de ferro 62% Fe", "Aço HRC China", "Coque metalúrgico"],
        "indices": ["Baltic Dry Index", "Índice de aço chinês"],
        "currencies": ["CNY/USD", "USD/BRL"],
        "supply_risks": ["Clima no Pará/Minas Gerais", "Regulações Vale"],
        "demand_drivers": ["Construção civil China", "Produção de aço global"],
    },
    "container": {
        "commodities": ["Frete spot Xangai-Brasil", "Freightwave SONAR"],
        "indices": ["SCFI (Shanghai Containerized Freight Index)", "Drewry WCI"],
        "currencies": ["USD/BRL"],
        "supply_risks": ["Escassez de contêineres", "Desvio Cabo Boa Esperança", "Ataques Mar Vermelho"],
        "demand_drivers": ["Consumo global", "Importações brasileiras", "E-commerce"],
    },
    "geral": {
        "commodities": ["Frete marítimo global", "Petróleo Brent"],
        "indices": ["Baltic Dry Index (BDI)", "Harpex"],
        "currencies": ["USD/BRL"],
        "supply_risks": ["Congestionamento portuário", "Escassez de navios"],
        "demand_drivers": ["Comércio global", "Economia brasileira"],
    },
}


def market_impact_analysis_tool(
    cargo_type: str = "",
    anomaly_direction: str = "queda",
    magnitude_pct: float = 0.0,
    period: str = "",
) -> Dict[str, Any]:
    """
    Analisa fatores de mercado relevantes para a anomalia detectada.

    Args:
        cargo_type:        Tipo de carga afetada
        anomaly_direction: "queda" ou "aumento"
        magnitude_pct:     Magnitude da variação em %
        period:            Período afetado

    Returns:
        Dict com fatores de mercado relevantes, impacto estimado e análise
    """
    ct_key = _detect_cargo_key(cargo_type)
    factors = _MARKET_FACTORS.get(ct_key, _MARKET_FACTORS["geral"])

    # Determinar impacto esperado
    direction_text = "redução" if anomaly_direction == "queda" else "aumento"
    impact_magnitude = "significativo" if magnitude_pct > 15 else "moderado" if magnitude_pct > 5 else "leve"

    # Montar análise estruturada
    relevant_risks = factors["supply_risks"] if anomaly_direction == "queda" else factors["demand_drivers"]
    relevant_drivers = factors["demand_drivers"] if anomaly_direction == "queda" else factors["supply_risks"]

    analysis = {
        "cargo_type": cargo_type or "geral",
        "anomaly_direction": anomaly_direction,
        "magnitude_pct": magnitude_pct,
        "impact_magnitude": impact_magnitude,
        "commodities_to_monitor": factors["commodities"],
        "market_indices": factors["indices"],
        "relevant_currencies": factors["currencies"],
        "supply_risk_factors": relevant_risks,
        "demand_factors": relevant_drivers,
        "market_context_text": _build_market_context(
            cargo_type, direction_text, impact_magnitude, factors, period
        ),
    }

    logger.info(
        "[MarketImpact] Cargo=%s dir=%s magnitude=%.1f%% impacto=%s",
        ct_key, anomaly_direction, magnitude_pct, impact_magnitude,
    )

    return analysis


def _build_market_context(
    cargo_type: str,
    direction_text: str,
    impact_magnitude: str,
    factors: Dict,
    period: str,
) -> str:
    lines = [
        f"**Análise de Mercado** ({period or 'período analisado'})",
        f"Carga: {cargo_type or 'geral'} | Variação: {direction_text} {impact_magnitude}",
        "",
        "Commodities relevantes: " + ", ".join(factors["commodities"][:3]),
        "Índices de referência: " + ", ".join(factors["indices"][:2]),
        "Fatores de risco de oferta: " + "; ".join(factors["supply_risks"][:2]),
        "Fatores de demanda: " + "; ".join(factors["demand_drivers"][:2]),
    ]
    return "\n".join(lines)


def _detect_cargo_key(cargo_type: str) -> str:
    ct = (cargo_type or "").lower()
    if any(w in ct for w in ["fertil", "potáss", "ureia", "npk"]):
        return "fertilizante"
    if any(w in ct for w in ["soja", "milho", "grão", "cereal", "trigo"]):
        return "graos"
    if any(w in ct for w in ["petró", "crude", "oleo"]):
        return "petroleo"
    if any(w in ct for w in ["minério", "ferro"]):
        return "minerio"
    if any(w in ct for w in ["contêiner", "container"]):
        return "container"
    return "geral"

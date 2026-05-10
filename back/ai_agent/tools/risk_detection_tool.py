"""
Risk Detection Tool

Detecta e classifica riscos operacionais externos que podem
ter causado anomalias na operação portuária.
Combina heurísticas de risco com análise LLM.
"""
import logging
from typing import Any, Dict, List

logger = logging.getLogger("ai_agent")

# Riscos conhecidos e seus indicadores textuais
_RISK_PATTERNS: List[Dict] = [
    {
        "risk_id": "guerra_russia_ucrania",
        "name": "Guerra Rússia-Ucrânia",
        "type": "geopolitico",
        "indicators": ["rússia", "ucrânia", "guerra", "conflito leste europeu", "sanção russa"],
        "affected_cargos": ["fertilizante", "grãos", "trigo", "potássio", "ureia"],
        "severity": "alto",
        "description": "Conflito reduziu exportações russas e ucranianas de fertilizantes e grãos",
    },
    {
        "risk_id": "mar_vermelho_houthi",
        "name": "Ataques Houthi no Mar Vermelho",
        "type": "maritimo",
        "indicators": ["houthi", "mar vermelho", "suez", "desvio", "cabo boa esperança"],
        "affected_cargos": ["container", "geral", "petróleo"],
        "severity": "alto",
        "description": "Ataques forçaram desvio de navios, aumentando frete e tempo de trânsito",
    },
    {
        "risk_id": "crise_logistica_global",
        "name": "Crise Logística Global",
        "type": "logistico",
        "indicators": ["frete alto", "congestionamento", "escassez navio", "shortage container"],
        "affected_cargos": ["container", "geral"],
        "severity": "medio",
        "description": "Alta no frete marítimo e congestionamento em portos globais",
    },
    {
        "risk_id": "china_economia",
        "name": "Desaceleração Econômica da China",
        "type": "economico",
        "indicators": ["china", "pib chinês", "construção china", "demanda chinesa"],
        "affected_cargos": ["minério", "soja", "celulose"],
        "severity": "medio",
        "description": "Queda na demanda chinesa afeta exportações brasileiras de commodities",
    },
    {
        "risk_id": "cambio_dolar",
        "name": "Alta do Dólar / Instabilidade Cambial",
        "type": "economico",
        "indicators": ["dólar", "câmbio", "real desvalorizado", "inflação", "juros fed"],
        "affected_cargos": ["fertilizante", "geral", "petróleo"],
        "severity": "medio",
        "description": "Alta do dólar encarece importações e afeta competitividade",
    },
    {
        "risk_id": "greve_trabalhadores",
        "name": "Greve / Paralisação Trabalhista",
        "type": "operacional",
        "indicators": ["greve", "paralisação", "trabalhadores porto", "sindicato", "pausa operacional"],
        "affected_cargos": ["geral"],
        "severity": "alto",
        "description": "Greves paralisam operações portuárias diretamente",
    },
    {
        "risk_id": "el_nino_seca",
        "name": "El Niño / Seca",
        "type": "climatico",
        "indicators": ["el niño", "seca", "estiagem", "hidrovia", "hidroelétrica"],
        "affected_cargos": ["grãos", "soja", "milho"],
        "severity": "medio",
        "description": "Seca reduz produção agrícola e afeta hidrovias de escoamento",
    },
    {
        "risk_id": "ferrovia_interrupcao",
        "name": "Interrupção Ferroviária",
        "type": "logistico",
        "indicators": ["ferrovia", "trilho", "trem", "interrupção ferroviária", "VLI", "VALE logística"],
        "affected_cargos": ["grãos", "minério", "fertilizante"],
        "severity": "alto",
        "description": "Interrupção ferroviária corta principal modal de acesso ao porto",
    },
]


def risk_detection_tool(
    news_context: List[Dict] = None,
    cargo_type: str = "",
    anomaly_description: str = "",
    correlation_result: Dict = None,
) -> Dict[str, Any]:
    """
    Detecta e classifica riscos operacionais externos.

    Args:
        news_context:         Notícias encontradas
        cargo_type:           Tipo de carga afetada
        anomaly_description:  Descrição da anomalia
        correlation_result:   Resultado do global_event_correlation_tool

    Returns:
        {
            "detected_risks": [...],
            "primary_risk": {...},
            "risk_summary": str,
            "overall_risk_level": "alto|medio|baixo",
        }
    """
    news_context = news_context or []
    correlation_result = correlation_result or {}

    # Construir texto de contexto para buscar indicadores
    context_text = anomaly_description.lower()
    for r in news_context:
        context_text += " " + (r.get("title", "") + " " + r.get("summary", "")).lower()

    # Hipóteses do correlation tool
    hypotheses_text = " ".join(
        h.get("event", "").lower()
        for h in correlation_result.get("hypotheses", [])
    )
    context_text += " " + hypotheses_text

    # Detectar riscos por padrão
    detected_risks = []
    for pattern in _RISK_PATTERNS:
        hit_count = sum(1 for ind in pattern["indicators"] if ind.lower() in context_text)
        # Boost se cargo é afetado
        cargo_match = any(
            c.lower() in cargo_type.lower()
            for c in pattern["affected_cargos"]
        ) if cargo_type else False

        if hit_count > 0 or cargo_match:
            confidence = min(hit_count * 0.2 + (0.15 if cargo_match else 0), 0.95)
            if confidence > 0.10:
                detected_risks.append({
                    **pattern,
                    "confidence": round(confidence, 2),
                    "indicator_hits": hit_count,
                    "cargo_match": cargo_match,
                })

    # Ordenar por confiança
    detected_risks.sort(key=lambda x: x["confidence"], reverse=True)

    primary_risk = detected_risks[0] if detected_risks else None
    overall_risk_level = _calculate_overall_risk(detected_risks)

    risk_summary = _build_risk_summary(detected_risks, overall_risk_level)

    logger.info(
        "[RiskDetection] %d riscos detectados, nível=%s, primary=%s",
        len(detected_risks),
        overall_risk_level,
        primary_risk.get("name", "N/A") if primary_risk else "N/A",
    )

    return {
        "detected_risks": detected_risks[:5],
        "primary_risk": primary_risk,
        "risk_summary": risk_summary,
        "overall_risk_level": overall_risk_level,
    }


def _calculate_overall_risk(risks: List[Dict]) -> str:
    if not risks:
        return "baixo"
    top_severities = [r.get("severity", "baixo") for r in risks[:3]]
    if "alto" in top_severities and risks[0].get("confidence", 0) > 0.5:
        return "alto"
    if "alto" in top_severities or "medio" in top_severities:
        return "medio"
    return "baixo"


def _build_risk_summary(risks: List[Dict], level: str) -> str:
    if not risks:
        return "Nenhum risco externo significativo identificado."
    level_labels = {"alto": "ALTO", "medio": "MÉDIO", "baixo": "BAIXO"}
    risk_names = [r["name"] for r in risks[:3]]
    return (
        f"Nível de risco externo: {level_labels.get(level, level.upper())}. "
        f"Principais fatores identificados: {', '.join(risk_names)}."
    )

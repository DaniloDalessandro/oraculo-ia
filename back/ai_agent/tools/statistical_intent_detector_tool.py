"""
Statistical Intent Detector Tool

Detecta intenção estatística na pergunta do usuário sem LLM.
Retorna o tipo de análise mais adequada para os dados.
"""
import re
from typing import Dict

# Mapa de palavras-chave para intenção estatística
_PATTERNS: list[tuple[str, list[str]]] = [
    ("forecast",          ["preveja", "previsao", "previsão", "projeção", "projetar", "projetar", "estimar", "próximos meses", "próximo ano", "tendência futura"]),
    ("correlation",       ["correlação", "correlacao", "correlaciona", "relação entre", "impacto de", "influência", "influencia", "afeta", "depende de"]),
    ("seasonality",       ["sazonalidade", "sazonal", "recorrente", "todo ano", "todo mês", "padrão mensal", "padrão anual", "epoca", "época"]),
    ("anomaly",           ["anomalia", "anomalias", "outlier", "outliers", "fora do padrão", "atipico", "atípico", "incomum", "estranho", "suspeito"]),
    ("trend",             ["tendência", "tendencia", "crescimento", "queda", "evolução", "evolucao", "historico", "histórico", "ao longo", "por mes", "por ano", "mensal", "anual"]),
    ("distribution",      ["distribuição", "distribuicao", "frequência", "frequencia", "histograma", "como se distribuem"]),
    ("descriptive",       ["média", "media", "mediana", "desvio", "variância", "variancia", "minimo", "mínimo", "maximo", "máximo", "quartil", "percentil", "estatísticas", "estatisticas"]),
    ("ranking",           ["ranking", "top", "maior", "menor", "melhor", "pior", "mais alto", "mais baixo", "classifique", "ordene"]),
    ("comparison",        ["compare", "comparar", "versus", "vs", "diferença", "diferenca", "entre", "variação", "variacao"]),
    ("kpi",               ["kpi", "indicador", "performance", "eficiência", "eficiencia", "produtividade", "throughput", "ocupação", "ocupacao", "utilização", "utilizacao"]),
    ("operational",       ["tempo médio", "tempo medio", "permanência", "permanencia", "fila", "berço", "berco", "atracação", "atracacao", "operação", "operacao"]),
]

# Intenções que implicam análise estatística rica
_STAT_INTENTS = {"forecast", "correlation", "seasonality", "anomaly", "trend", "distribution", "descriptive"}


def statistical_intent_detector_tool(question: str, agent_intent: str = "") -> Dict:
    """
    Detecta intenção estatística na pergunta.

    Returns:
        {
            "stat_intent": str,
            "confidence": float,
            "needs_trend": bool,
            "needs_anomaly": bool,
            "needs_forecast": bool,
            "needs_correlation": bool,
            "needs_descriptive": bool,
            "needs_kpi": bool,
            "needs_seasonality": bool,
        }
    """
    q = question.lower()
    scores: dict[str, int] = {}

    for intent, keywords in _PATTERNS:
        score = sum(1 for kw in keywords if kw in q)
        if score:
            scores[intent] = score

    # Boost por intent do classificador principal
    _AGENT_BOOST = {
        "evolucao_temporal": ["trend", "seasonality", "forecast"],
        "ranking":           ["ranking", "anomaly"],
        "comparacao":        ["comparison", "descriptive"],
        "media":             ["descriptive"],
        "totalizacao":       ["descriptive", "kpi"],
        "analise_por_berco": ["kpi", "operational"],
        "analise_por_carga": ["kpi", "operational"],
    }
    for boosted in _AGENT_BOOST.get(agent_intent, []):
        scores[boosted] = scores.get(boosted, 0) + 1

    if not scores:
        stat_intent = "descriptive"
        confidence = 0.5
    else:
        stat_intent = max(scores, key=lambda k: scores[k])
        total = sum(scores.values())
        confidence = round(min(scores[stat_intent] / max(total, 1) + 0.3, 0.99), 2)

    return {
        "stat_intent":        stat_intent,
        "confidence":         confidence,
        "needs_trend":        any(k in scores for k in ["trend", "forecast", "seasonality"]),
        "needs_anomaly":      "anomaly" in scores or "ranking" in scores,
        "needs_forecast":     "forecast" in scores,
        "needs_correlation":  "correlation" in scores,
        "needs_descriptive":  True,  # sempre
        "needs_kpi":          any(k in scores for k in ["kpi", "operational"]),
        "needs_seasonality":  "seasonality" in scores or "trend" in scores,
    }

"""
Global Event Correlation Tool

Usa o LLM para correlacionar eventos externos globais com anomalias
operacionais detectadas no porto.
"""
import json
import logging
import re
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage, SystemMessage
from ai_agent.services.gemini_service import invoke_llm

logger = logging.getLogger("ai_agent")

_SYSTEM = """
Você é um analista de inteligência operacional e geopolítica especializado em logística portuária.
Sua função é correlacionar eventos externos (guerras, crises, sanções, clima, economia)
com anomalias operacionais detectadas em portos.

Dado o contexto de uma anomalia portuária e notícias relevantes encontradas,
identifique os eventos externos mais prováveis que podem ter causado ou contribuído
para a anomalia.

Regras obrigatórias:
1. NUNCA afirme causalidade absoluta — use linguagem de correlação e hipótese.
2. Classifique cada hipótese com um confidence_score (0.0 a 1.0).
3. Diferencie claramente: fato operacional, hipótese, correlação, inferência.
4. Ordene hipóteses do mais ao menos provável.
5. Seja estratégico e executivo na análise.

Responda EXCLUSIVAMENTE com JSON:
{
  "hypotheses": [
    {
      "event": "descrição do evento externo",
      "event_type": "geopolitico|economico|climatico|logistico|sanitario|outro",
      "description": "explicação de como este evento pode ter afetado o porto",
      "confidence_score": 0.85,
      "correlation_strength": "alta|media|baixa",
      "evidence": ["evidência 1", "evidência 2"],
      "cargo_types_affected": ["fertilizante", "grãos"],
      "time_match": true
    }
  ],
  "overall_confidence": 0.78,
  "primary_cause_category": "geopolitico|economico|climatico|logistico|interno",
  "analysis_summary": "resumo executivo de 2-3 linhas"
}
"""

# Correlações conhecidas cargo → eventos globais
_KNOWN_CORRELATIONS = {
    "fertilizante": [
        "Guerra Rússia-Ucrânia (redução exportações russas de fertilizantes)",
        "Sanções econômicas à Rússia e Bielorrússia",
        "Alta do dólar encarecendo importações",
        "Aumento do custo do gás natural (insumo para ureia)",
    ],
    "graos": [
        "Safra brasileira (sazonalidade de exportação)",
        "Demanda chinesa por soja e milho",
        "Bloqueio de exportação ucraniana de grãos",
        "El Niño / La Niña afetando produção agrícola",
    ],
    "petroleo": [
        "Decisões de produção da OPEP+",
        "Tensões no Oriente Médio",
        "Flutuações do preço do Brent",
        "Crise energética global",
    ],
    "minerio": [
        "Demanda da China por minério (construção civil / aço)",
        "Regulações ambientais chinesas",
        "Problemas em mineradoras brasileiras",
    ],
    "container": [
        "Congestionamento em portos globais",
        "Ataques Houthi no Mar Vermelho / desvio pelo Cabo da Boa Esperança",
        "Alta do frete marítimo global",
        "Escassez de contêineres",
    ],
    "geral": [
        "Alta do frete marítimo global",
        "Congestionamento em portos internacionais",
        "Crise de cadeia de suprimentos pós-pandemia",
        "Flutuações cambiais (dólar/real)",
    ],
}


def global_event_correlation_tool(
    anomaly_description: str,
    cargo_type: str = "",
    period: str = "",
    news_context: List[Dict] = None,
    stat_context: str = "",
) -> Dict[str, Any]:
    """
    Correlaciona eventos globais com a anomalia operacional detectada.

    Args:
        anomaly_description: Descrição da anomalia detectada
        cargo_type:          Tipo de carga afetado
        period:              Período afetado
        news_context:        Notícias encontradas pelo external_news_search_tool
        stat_context:        Contexto estatístico da anomalia

    Returns:
        Dict com hypotheses, overall_confidence e analysis_summary
    """
    news_context = news_context or []

    # Montar contexto de notícias para o LLM
    news_text = ""
    if news_context:
        headlines = [f"- [{r.get('source','')}] {r.get('title','')}: {r.get('summary','')[:150]}"
                     for r in news_context[:8]]
        news_text = "NOTÍCIAS ENCONTRADAS:\n" + "\n".join(headlines)

    # Correlações conhecidas para o cargo
    ct_key = _detect_cargo_key(cargo_type)
    known = _KNOWN_CORRELATIONS.get(ct_key, _KNOWN_CORRELATIONS["geral"])
    known_text = "CORRELAÇÕES CONHECIDAS PARA ESTE TIPO DE CARGA:\n" + "\n".join(f"- {k}" for k in known)

    prompt = f"""
ANOMALIA DETECTADA:
{anomaly_description}

CARGA AFETADA: {cargo_type or "não especificada"}
PERÍODO: {period or "não especificado"}

CONTEXTO ESTATÍSTICO:
{stat_context or "Não disponível"}

{news_text}

{known_text}

Analise a anomalia e correlacione com possíveis causas externas.
"""

    try:
        raw = invoke_llm([
            SystemMessage(content=_SYSTEM),
            HumanMessage(content=prompt),
        ])
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            raise ValueError("JSON não encontrado na resposta")
        result = json.loads(match.group())
        logger.info(
            "[Correlation] %d hipóteses, confiança=%.2f",
            len(result.get("hypotheses", [])),
            result.get("overall_confidence", 0),
        )
        return result
    except Exception as exc:
        logger.warning("[Correlation] Falha: %s", exc)
        return {
            "hypotheses": [],
            "overall_confidence": 0.0,
            "primary_cause_category": "desconhecido",
            "analysis_summary": "Análise de correlação indisponível.",
        }


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

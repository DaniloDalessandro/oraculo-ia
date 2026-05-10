"""
External Operational Intelligence Skill — Orchestrador

Analista de Inteligência Operacional e Geopolítica.

Detecta anomalias operacionais e correlaciona com eventos externos
(guerras, sanções, crises climáticas, logística global, commodities).

Roda como ETAPA 14.9 — após análise estatística, antes da resposta final.
"""
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional

from ai_agent.tools.external_news_search_tool import external_news_search_tool
from ai_agent.tools.global_event_correlation_tool import global_event_correlation_tool
from ai_agent.tools.market_impact_analysis_tool import market_impact_analysis_tool
from ai_agent.tools.port_comparison_tool import port_comparison_tool
from ai_agent.tools.weather_and_climate_tool import weather_and_climate_tool
from ai_agent.tools.risk_detection_tool import risk_detection_tool

logger = logging.getLogger("ai_agent")

# Keywords que indicam que o usuário quer investigação de causas
_INVESTIGATION_KW = frozenset([
    "por que", "porque", "causa", "motivo", "razão", "explique", "explica",
    "queda", "redução", "diminuição", "aumento", "crescimento", "variação",
    "anomalia", "problema", "crise", "impacto", "efeito", "influência",
    "o que aconteceu", "o que causou", "por qual motivo", "como explicar",
    "análise", "analise", "investigar", "investigação", "contexto",
])

# Keywords de carga para detectar tipo
_CARGO_PATTERNS = {
    "fertilizante": ["fertil", "potáss", "ureia", "npk", "adubo"],
    "grãos": ["soja", "milho", "trigo", "grão", "cereal"],
    "petróleo": ["petró", "crude", "bunker", "combustív"],
    "minério": ["minério", "ferro", "iron ore"],
    "celulose": ["celulose", "papel", "pulp"],
    "contêiner": ["contêiner", "container"],
    "geral": [],
}


def should_run_intelligence(
    question: str,
    stat_analysis: Dict,
    intent: str,
) -> bool:
    """
    Decide se a skill de inteligência externa deve rodar.

    Roda quando:
    1. Anomalias foram detectadas na análise estatística, OU
    2. O usuário usa palavras de investigação, OU
    3. O intent é evolucao_temporal ou comparacao (alto potencial de anomalia)
    """
    q = question.lower()

    # Verificar pergunta de investigação explícita
    if any(kw in q for kw in _INVESTIGATION_KW):
        return True

    # Verificar intents analíticos
    if intent in ("evolucao_temporal", "comparacao", "media"):
        return True

    # Verificar anomalias detectadas pela skill estatística
    analyses = stat_analysis.get("analyses_run", [])
    if "anomaly" in analyses:
        return True

    # Verificar se há contexto estatístico com queda/aumento
    stat_text = stat_analysis.get("stat_context_text", "").lower()
    if any(w in stat_text for w in ["anomalia", "queda", "redução", "declínio", "aumento atípico"]):
        return True

    return False


def _extract_intel_context(
    question: str,
    result: Dict,
    stat_analysis: Dict,
) -> Dict[str, Any]:
    """Extrai contexto relevante para a análise de inteligência."""
    q = question.lower()

    # Detectar tipo de carga mencionado
    cargo_type = ""
    for cargo, patterns in _CARGO_PATTERNS.items():
        if any(p in q for p in patterns):
            cargo_type = cargo
            break

    # Tentar extrair cargo dos dados do resultado
    if not cargo_type and result.get("dict_rows"):
        first_row = result["dict_rows"][0] if result["dict_rows"] else {}
        for col in ["carga", "tipo_carga", "descricao_carga", "mercadoria"]:
            if col in first_row and first_row[col]:
                cargo_type = str(first_row[col])
                break

    # Detectar período mencionado
    period = ""
    period_match = re.search(
        r"(jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)[a-z]*/?\s*(\d{4})"
        r"|(\d{4})"
        r"|(último[s]?\s+mes[e]?s?|último[s]?\s+ano[s]?)",
        q, re.IGNORECASE
    )
    if period_match:
        period = period_match.group(0)

    # Detectar direção da anomalia
    direction = "queda"
    if any(w in q for w in ["aumento", "crescimento", "alta", "subiu", "cresceu"]):
        direction = "aumento"

    # Extrair magnitude da análise estatística
    magnitude_pct = 0.0
    stat_text = stat_analysis.get("stat_context_text", "")
    pct_match = re.search(r"(\d+(?:\.\d+)?)\s*%", stat_text)
    if pct_match:
        magnitude_pct = float(pct_match.group(1))

    # Construir descrição da anomalia
    anomaly_desc = f"{direction} operacional"
    if cargo_type:
        anomaly_desc += f" de {cargo_type}"
    if period:
        anomaly_desc += f" em {period}"
    if magnitude_pct:
        anomaly_desc += f" ({magnitude_pct:.1f}%)"

    return {
        "cargo_type": cargo_type,
        "period": period,
        "direction": direction,
        "magnitude_pct": magnitude_pct,
        "anomaly_description": anomaly_desc,
    }


def run_external_intelligence_skill(
    question: str,
    result: Dict[str, Any],
    stat_analysis: Dict[str, Any],
    intent: str = "",
) -> Dict[str, Any]:
    """
    Orquestra a análise de inteligência operacional externa.

    Args:
        question:      Pergunta original do usuário
        result:        Resultado SQL
        stat_analysis: Resultado da skill estatística (ETAPA 14.7)
        intent:        Intenção classificada

    Returns:
        {
            "intel_context_text": str,       # injetado na resposta final
            "ran": bool,
            "news_found": int,
            "hypotheses_count": int,
            "scope": str,
            "risk_level": str,
        }
    """
    if not should_run_intelligence(question, stat_analysis, intent):
        logger.info("[Intel] Skill não acionada para esta consulta.")
        return {"intel_context_text": "", "ran": False}

    logger.info("[Intel] ETAPA 14.9 — Análise de Inteligência Externa iniciada.")

    ctx = _extract_intel_context(question, result, stat_analysis)
    cargo_type = ctx["cargo_type"]
    period = ctx["period"]
    direction = ctx["direction"]
    magnitude_pct = ctx["magnitude_pct"]
    anomaly_desc = ctx["anomaly_description"]

    # ── Paralelizar as buscas independentes ──────────────────────────────────
    news_result: Dict = {}
    port_result: Dict = {}
    weather_result: Dict = {}
    market_result: Dict = {}

    def _run_news():
        return external_news_search_tool(
            anomaly_description=anomaly_desc,
            cargo_type=cargo_type,
            period=period,
        )

    def _run_port():
        return port_comparison_tool(
            cargo_type=cargo_type,
            period=period,
            anomaly_direction=direction,
        )

    def _run_weather():
        return weather_and_climate_tool(period=period)

    def _run_market():
        return market_impact_analysis_tool(
            cargo_type=cargo_type,
            anomaly_direction=direction,
            magnitude_pct=magnitude_pct,
            period=period,
        )

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {
            pool.submit(_run_news): "news",
            pool.submit(_run_port): "port",
            pool.submit(_run_weather): "weather",
            pool.submit(_run_market): "market",
        }
        for future in as_completed(futures, timeout=30):
            key = futures[future]
            try:
                if key == "news":
                    news_result = future.result()
                elif key == "port":
                    port_result = future.result()
                elif key == "weather":
                    weather_result = future.result()
                elif key == "market":
                    market_result = future.result()
            except Exception as exc:
                logger.warning("[Intel] Sub-tool '%s' falhou: %s", key, exc)

    news_list: List[Dict] = news_result.get("news", [])

    # ── Correlação e detecção de riscos (dependem das notícias) ──────────────
    correlation_result = global_event_correlation_tool(
        anomaly_description=anomaly_desc,
        cargo_type=cargo_type,
        period=period,
        news_context=news_list,
        stat_context=stat_analysis.get("stat_context_text", ""),
    )

    risk_result = risk_detection_tool(
        news_context=news_list,
        cargo_type=cargo_type,
        anomaly_description=anomaly_desc,
        correlation_result=correlation_result,
    )

    # ── Montar texto de contexto para a resposta ──────────────────────────────
    intel_text = _build_intel_context_text(
        anomaly_desc=anomaly_desc,
        news_list=news_list,
        correlation_result=correlation_result,
        risk_result=risk_result,
        port_result=port_result,
        weather_result=weather_result,
        market_result=market_result,
        cargo_type=cargo_type,
    )

    logger.info(
        "[Intel] Concluído. news=%d hipóteses=%d risks=%d scope=%s",
        len(news_list),
        len(correlation_result.get("hypotheses", [])),
        len(risk_result.get("detected_risks", [])),
        port_result.get("scope", "?"),
    )

    return {
        "intel_context_text": intel_text,
        "ran": True,
        "news_found": len(news_list),
        "hypotheses_count": len(correlation_result.get("hypotheses", [])),
        "scope": port_result.get("scope", "desconhecido"),
        "risk_level": risk_result.get("overall_risk_level", "baixo"),
    }


# ── Montagem do bloco de texto ────────────────────────────────────────────────

def _build_intel_context_text(
    anomaly_desc: str,
    news_list: List[Dict],
    correlation_result: Dict,
    risk_result: Dict,
    port_result: Dict,
    weather_result: Dict,
    market_result: Dict,
    cargo_type: str,
) -> str:
    """Monta o bloco de inteligência externa para injetar na resposta final."""
    sections: List[str] = []

    sections.append("INTELIGÊNCIA OPERACIONAL EXTERNA:")

    # Hipóteses de correlação
    hypotheses = correlation_result.get("hypotheses", [])
    if hypotheses:
        sections.append("\nFATORES EXTERNOS CORRELACIONADOS:")
        for h in hypotheses[:4]:
            conf = int(h.get("confidence_score", 0) * 100)
            strength = h.get("correlation_strength", "").upper()
            sections.append(
                f"- [{h.get('event_type','').upper()}] {h.get('event','')} "
                f"(confiança {conf}%, correlação {strength}): {h.get('description','')[:150]}"
            )
        summary = correlation_result.get("analysis_summary", "")
        if summary:
            sections.append(f"\nAnálise: {summary}")

    # Riscos detectados
    risks = risk_result.get("detected_risks", [])
    risk_level = risk_result.get("overall_risk_level", "baixo")
    if risks:
        sections.append(f"\nRISCOS EXTERNOS (nível geral: {risk_level.upper()}):")
        for r in risks[:3]:
            conf = int(r.get("confidence", 0) * 100)
            sections.append(
                f"- {r['name']} [{r.get('severity','').upper()}] (conf. {conf}%): {r.get('description','')[:120]}"
            )

    # Escopo do problema
    scope = port_result.get("scope", "")
    if scope:
        scope_label = {"global": "GLOBAL", "nacional": "NACIONAL", "regional": "REGIONAL", "local": "LOCAL"}
        sections.append(f"\nESCOPO DO PROBLEMA: {scope_label.get(scope, scope.upper())}")
        explanation = port_result.get("scope_explanation", "")
        if explanation:
            sections.append(explanation)

    # Clima
    climate_risk = weather_result.get("climate_risk_level", "baixo")
    climate_summary = weather_result.get("climate_summary", "")
    if climate_summary and climate_risk != "baixo":
        sections.append(f"\nFATOR CLIMÁTICO: {climate_summary}")

    # Notícias com links reais
    real_news = [n for n in news_list if n.get("url", "").startswith("http")]
    if real_news:
        sections.append("\nNOTÍCIAS RELACIONADAS (fontes reais):")
        for i, n in enumerate(real_news[:6], 1):
            title = n.get("title", "Sem título")[:100]
            source = n.get("source", "")
            url = n.get("url", "")
            date = n.get("date", "")
            date_str = f" ({date})" if date else ""
            sections.append(f"{i}. {title}{date_str} — {source}\n   {url}")

    # Aviso epistêmico
    sections.append(
        "\nOBSERVAÇÃO: Os fatores acima são correlações hipotéticas baseadas em dados externos. "
        "Não representam causalidade confirmada. Nível de confiança varia por hipótese."
    )

    return "\n".join(sections)

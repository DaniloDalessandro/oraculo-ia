"""
Advanced Statistical Analysis Skill — Orchestrador

Coordena todos os tools estatísticos e gera um bloco de contexto
enriquecido para ser injetado na resposta final do agente.

Roda entre ETAPA 14 (cross-check) e ETAPA 15 (resposta final).
"""
import logging
from typing import Any, Dict, List, Optional

from ai_agent.tools.statistical_intent_detector_tool import statistical_intent_detector_tool
from ai_agent.tools.data_quality_tool import data_quality_tool
from ai_agent.tools.descriptive_statistics_tool import descriptive_statistics_tool
from ai_agent.tools.trend_analysis_tool import trend_analysis_tool
from ai_agent.tools.seasonality_detection_tool import seasonality_detection_tool
from ai_agent.tools.anomaly_detection_tool import anomaly_detection_tool
from ai_agent.tools.forecast_tool import forecast_tool
from ai_agent.tools.correlation_analysis_tool import correlation_analysis_tool
from ai_agent.tools.operational_kpi_tool import operational_kpi_tool

logger = logging.getLogger("ai_agent")


def run_statistics_skill(
    question: str,
    result: Dict[str, Any],
    agent_intent: str = "",
) -> Dict[str, Any]:
    """
    Executa o pipeline estatistico completo sobre os dados do resultado SQL.

    Args:
        question:     Pergunta original do usuario.
        result:       Resultado do sql_executor_tool.
        agent_intent: Intencao classificada pelo agente.

    Returns:
        {
            "stat_context_text": str,
            "confidence_score":  float,
            "data_quality_score": float,
            "sample_size":       int,
            "warnings":          [str],
            "stat_intent":       str,
            "analyses_run":      [str],
        }
    """
    rows: List[Dict] = result.get("dict_rows", [])
    columns: List[str] = result.get("columns", [])
    n = len(rows)

    if n == 0 or not columns:
        return _empty()

    # 1. Detectar intencao estatistica
    stat_intent_result = statistical_intent_detector_tool(question, agent_intent)
    stat_intent = stat_intent_result["stat_intent"]
    logger.info("[Stats] Intent=%s conf=%.2f", stat_intent, stat_intent_result["confidence"])

    # 2. Qualidade dos dados (sempre)
    quality = data_quality_tool(rows, columns)
    numeric_cols = quality["numeric_columns"]
    date_cols    = quality["date_columns"]

    logger.info(
        "[Stats] quality=%.2f n=%d numeric=%s",
        quality["quality_score"], n, numeric_cols,
    )

    if not quality["is_sufficient"]:
        return {
            "stat_context_text":  _format_quality_only(quality),
            "confidence_score":   quality["quality_score"],
            "data_quality_score": quality["quality_score"],
            "sample_size":        n,
            "warnings":           quality["warnings"],
            "stat_intent":        stat_intent,
            "analyses_run":       ["data_quality"],
        }

    analyses_run = ["data_quality", "descriptive"]
    sections: List[str] = []
    all_warnings: List[str] = list(quality["warnings"])

    # 3. Estatisticas descritivas (sempre)
    if numeric_cols:
        desc = descriptive_statistics_tool(rows, numeric_cols)
        sections.append(_format_descriptive(desc["stats"]))

    # 4. Serie principal
    main_col = numeric_cols[0] if numeric_cols else None
    main_series = _extract_series(rows, main_col) if main_col else []
    labels = _extract_labels(rows, columns, numeric_cols, date_cols)

    # 5. Tendencia
    if stat_intent_result["needs_trend"] and len(main_series) >= 3:
        trend = trend_analysis_tool(main_series, labels)
        sections.append(_format_trend(trend, main_col))
        analyses_run.append("trend")

        # 6. Sazonalidade
        if stat_intent_result["needs_seasonality"] and len(main_series) >= 6:
            seas = seasonality_detection_tool(main_series, labels)
            if seas["has_seasonality"]:
                sections.append(_format_seasonality(seas))
                analyses_run.append("seasonality")

        # 7. Previsao
        if stat_intent_result["needs_forecast"] and len(main_series) >= 5:
            fc = forecast_tool(main_series, steps=3, labels=labels)
            sections.append(_format_forecast(fc, main_col))
            analyses_run.append("forecast")

    # 8. Anomalias
    if stat_intent_result["needs_anomaly"] and len(main_series) >= 4:
        anomaly = anomaly_detection_tool(main_series, labels)
        if anomaly["has_anomalies"]:
            sections.append(_format_anomaly(anomaly))
            all_warnings.extend(
                ["Anomalia: " + a["label"] + "=" + str(a["value"]) for a in anomaly["anomalies_zscore"][:2]]
            )
        analyses_run.append("anomaly")

    # 9. Correlacao
    if stat_intent_result["needs_correlation"] and len(numeric_cols) >= 2:
        corr = correlation_analysis_tool(rows, numeric_cols)
        if corr["strongest_pair"]:
            sections.append(_format_correlation(corr))
        analyses_run.append("correlation")

    # 10. KPIs operacionais
    if stat_intent_result["needs_kpi"] or agent_intent in ("analise_por_berco", "analise_por_carga", "analise_por_operador"):
        kpis = operational_kpi_tool(rows, columns, agent_intent)
        if kpis["kpis"]:
            sections.append(_format_kpis(kpis))
        analyses_run.append("operational_kpi")

    # Score final
    confidence_score = round(
        quality["quality_score"] * 0.4 + stat_intent_result["confidence"] * 0.6, 2
    )
    if n < 10:
        confidence_score = round(confidence_score * 0.7, 2)

    stat_context_text = _build_context_block(sections, quality, confidence_score, all_warnings)

    logger.info(
        "[Stats] Concluido. analyses=%s confidence=%.2f warnings=%d",
        analyses_run, confidence_score, len(all_warnings),
    )

    return {
        "stat_context_text":  stat_context_text,
        "confidence_score":   confidence_score,
        "data_quality_score": quality["quality_score"],
        "sample_size":        n,
        "warnings":           all_warnings,
        "stat_intent":        stat_intent,
        "analyses_run":       analyses_run,
    }


# Formatadores

def _format_quality_only(q: Dict) -> str:
    lines = ["QUALIDADE DOS DADOS: score=" + str(q["quality_score"]) + " | n=" + str(q["sample_size"])]
    for w in q["warnings"]:
        lines.append("  AVISO: " + w)
    return "\n".join(lines)


def _format_descriptive(stats: Dict) -> str:
    lines = ["ESTATISTICAS DESCRITIVAS:"]
    for col, s in stats.items():
        lines.append(
            "  " + col + ": media=" + str(s["mean"]) + " | mediana=" + str(s["median"]) +
            " | min=" + str(s["min"]) + " | max=" + str(s["max"]) + " | dp=" + str(s["std"]) +
            " | q1=" + str(s["q1"]) + " | q3=" + str(s["q3"]) + " | " + s["skewness_label"]
        )
        lines.append("    -> Usar " + s["preferred_avg"] + " como medida central.")
    return "\n".join(lines)


def _format_trend(t: Dict, col: str) -> str:
    return (
        "TENDENCIA (" + str(col) + "): " + t["description"] +
        " Inclinacao: " + str(t["slope_pct_per_step"]) + "%/passo." +
        " Crescimento recente: " + str(t["growth_last_pct"]) + "%."
    )


def _format_seasonality(s: Dict) -> str:
    return "SAZONALIDADE: " + s["description"] + " Padrao trimestral: " + str(s["quarterly_pattern"]) + "."


def _format_forecast(f: Dict, col: str) -> str:
    ci_str = " | ".join("[" + str(lo) + "," + str(hi) + "]" for lo, hi in f["confidence_interval"])
    return (
        "PREVISAO (" + str(col) + "): " + f["description"] +
        " Intervalos de confianca: " + ci_str +
        ". Confiabilidade: " + f["reliability"] + "."
    )


def _format_anomaly(a: Dict) -> str:
    top = [
        x["label"] + "=" + str(x["value"]) + "(z=" + str(x.get("z_score", "?")) + ")"
        for x in a["anomalies_zscore"][:3]
    ]
    return "ANOMALIAS: " + a["description"] + " Valores extremos: " + ", ".join(top) + "."


def _format_correlation(c: Dict) -> str:
    return "CORRELACAO: " + c["description"]


def _format_kpis(k: Dict) -> str:
    lines = ["KPIs OPERACIONAIS:"]
    for name, kpi in k["kpis"].items():
        note = " [" + kpi["benchmark_note"] + "]" if kpi.get("benchmark_note") else ""
        lines.append("  " + kpi["label"] + ": " + str(kpi["value"]) + " " + str(kpi["unit"]) + note)
    return "\n".join(lines)


def _build_context_block(sections: list, quality: Dict, confidence: float, warnings: list) -> str:
    if not sections:
        return ""
    header = (
        "=== ANALISE ESTATISTICA ===\n"
        "Qualidade dos dados: " + str(round(quality["quality_score"] * 100)) + "% | "
        "Amostra: " + str(quality["sample_size"]) + " registros | "
        "Confianca: " + str(round(confidence * 100)) + "%\n"
    )
    body = "\n\n".join(sections)
    warn_block = ""
    if warnings:
        warn_block = "\n\nAVISOS ESTATISTICOS:\n" + "\n".join("  AVISO: " + w for w in warnings[:5])
    footer = (
        "\n\nLIMITACOES: Use estes indicadores como referencia analitica. "
        "Resultados com amostra < 30 tem menor representatividade estatistica."
    )
    return header + body + warn_block + footer


def _extract_series(rows: List[Dict], col: str) -> List[float]:
    result = []
    for r in rows:
        v = r.get(col)
        if v is None:
            continue
        try:
            result.append(float(v))
        except (ValueError, TypeError):
            pass
    return result


def _extract_labels(rows, columns, numeric_cols, date_cols) -> List[str]:
    label_col = None
    if date_cols:
        label_col = date_cols[0]
    else:
        text_cols = [c for c in columns if c not in numeric_cols and c not in date_cols]
        if text_cols:
            label_col = text_cols[0]
    if label_col:
        return [str(r.get(label_col, i)) for i, r in enumerate(rows)]
    return [str(i + 1) for i in range(len(rows))]


def _empty() -> Dict:
    return {
        "stat_context_text": "", "confidence_score": 0.0,
        "data_quality_score": 0.0, "sample_size": 0,
        "warnings": [], "stat_intent": "descriptive", "analyses_run": [],
    }

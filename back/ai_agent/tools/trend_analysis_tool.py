"""
Trend Analysis Tool

Detecta tendências em séries temporais ou sequenciais.
Métodos: regressão linear, média móvel, suavização exponencial.
Puro Python — sem dependências externas.
"""
import math
from typing import Any, Dict, List, Optional


def trend_analysis_tool(values: List[float], labels: Optional[List[str]] = None) -> Dict:
    """
    Detecta tendência em uma série de valores.

    Args:
        values: Série numérica ordenada cronologicamente.
        labels: Rótulos (ex: meses, anos) correspondentes aos valores.

    Returns:
        {
            "trend_direction": "crescimento" | "queda" | "estavel" | "aceleracao" | "desaceleracao",
            "slope": float,
            "slope_pct_per_step": float,
            "r_squared": float,
            "confidence": float,
            "moving_avg_3": [float],
            "moving_avg_6": [float],
            "growth_total_pct": float,
            "growth_last_pct": float,
            "description": str,
        }
    """
    n = len(values)
    if n < 2:
        return _empty("Dados insuficientes para análise de tendência.")

    vals = [float(v) for v in values]

    # ── Regressão linear (mínimos quadrados) ────────────────────────────
    x = list(range(n))
    mean_x = sum(x) / n
    mean_y = sum(vals) / n
    ss_xy = sum((x[i] - mean_x) * (vals[i] - mean_y) for i in range(n))
    ss_xx = sum((x[i] - mean_x) ** 2 for i in range(n))
    slope = ss_xy / ss_xx if ss_xx != 0 else 0.0

    # R²
    y_pred = [mean_y + slope * (xi - mean_x) for xi in x]
    ss_res = sum((vals[i] - y_pred[i]) ** 2 for i in range(n))
    ss_tot = sum((vals[i] - mean_y) ** 2 for i in range(n))
    r_squared = round(1 - ss_res / ss_tot if ss_tot > 0 else 0.0, 4)

    # ── Percentual de inclinação ─────────────────────────────────────────
    base = abs(mean_y) if mean_y != 0 else 1
    slope_pct = round((slope / base) * 100, 2)

    # ── Crescimento total e recente ──────────────────────────────────────
    growth_total = round(((vals[-1] - vals[0]) / abs(vals[0])) * 100, 2) if vals[0] != 0 else 0.0
    mid = max(n // 2, n - 4)
    growth_last = round(((vals[-1] - vals[mid]) / abs(vals[mid])) * 100, 2) if vals[mid] != 0 else 0.0

    # ── Direção ──────────────────────────────────────────────────────────
    threshold = 1.0  # 1% por passo = significativo
    if abs(slope_pct) < threshold:
        direction = "estavel"
    elif slope_pct > 0:
        direction = "crescimento"
        if growth_last > growth_total * 1.5 and n >= 6:
            direction = "aceleracao"
    else:
        direction = "queda"
        if growth_last < growth_total * 1.5 and n >= 6:
            direction = "desaceleracao"

    # ── Médias móveis ────────────────────────────────────────────────────
    def moving_avg(v, w):
        return [round(sum(v[max(0, i-w+1):i+1]) / min(i+1, w), 4) for i in range(len(v))]

    # ── Confiança: R² ajustado ───────────────────────────────────────────
    confidence = round(min(abs(r_squared) + 0.1, 0.99), 2) if n >= 5 else 0.5

    # ── Descrição textual ────────────────────────────────────────────────
    label_info = ""
    if labels and len(labels) >= 2:
        label_info = f" de {labels[0]} a {labels[-1]}"
    direction_pt = {
        "crescimento": "crescimento", "queda": "queda",
        "estavel": "estabilidade", "aceleracao": "aceleração",
        "desaceleracao": "desaceleração"
    }.get(direction, direction)
    description = (
        f"Tendência de {direction_pt}{label_info}. "
        f"Variação total: {'+' if growth_total >= 0 else ''}{growth_total:.1f}%. "
        f"Ajuste linear R²={r_squared:.2f}."
    )

    return {
        "trend_direction":      direction,
        "slope":                round(slope, 4),
        "slope_pct_per_step":   slope_pct,
        "r_squared":            r_squared,
        "confidence":           confidence,
        "moving_avg_3":         moving_avg(vals, 3),
        "moving_avg_6":         moving_avg(vals, 6),
        "growth_total_pct":     growth_total,
        "growth_last_pct":      growth_last,
        "description":          description,
    }


def _empty(msg: str) -> Dict:
    return {
        "trend_direction": "desconhecido", "slope": 0.0,
        "slope_pct_per_step": 0.0, "r_squared": 0.0, "confidence": 0.0,
        "moving_avg_3": [], "moving_avg_6": [], "growth_total_pct": 0.0,
        "growth_last_pct": 0.0, "description": msg,
    }

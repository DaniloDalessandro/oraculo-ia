"""
Forecast Tool

Realiza previsões simples usando regressão linear e suavização exponencial.
Puro Python — sem dependências externas.
"""
import math
from typing import Dict, List, Optional


def forecast_tool(
    values: List[float],
    steps: int = 3,
    labels: Optional[List[str]] = None,
    alpha: float = 0.3,
) -> Dict:
    """
    Gera previsões para os próximos N períodos.

    Args:
        values:  Série histórica ordenada.
        steps:   Número de períodos a prever (padrão 3).
        labels:  Rótulos históricos (ex: meses).
        alpha:   Fator de suavização exponencial (0 < alpha < 1).

    Returns:
        {
            "method": str,
            "forecast_linear": [float],
            "forecast_exp": [float],
            "forecast_combined": [float],
            "confidence_interval": [(lo, hi)],
            "reliability": "alta"|"moderada"|"baixa",
            "description": str,
        }
    """
    n = len(values)
    if n < 3:
        return _empty("Série muito curta para previsão (mínimo 3 pontos).")

    vals = [float(v) for v in values]

    # ── Regressão linear ─────────────────────────────────────────────────
    x = list(range(n))
    mean_x = sum(x) / n
    mean_y = sum(vals) / n
    ss_xy = sum((x[i] - mean_x) * (vals[i] - mean_y) for i in range(n))
    ss_xx = sum((x[i] - mean_x) ** 2 for i in range(n))
    slope = ss_xy / ss_xx if ss_xx != 0 else 0.0
    intercept = mean_y - slope * mean_x

    forecast_linear = [round(intercept + slope * (n + i), 4) for i in range(steps)]

    # ── Suavização exponencial simples ───────────────────────────────────
    s = vals[0]
    for v in vals[1:]:
        s = alpha * v + (1 - alpha) * s
    forecast_exp = [round(s, 4)] * steps  # nível constante

    # ── Combinado (média ponderada) ──────────────────────────────────────
    forecast_combined = [
        round(0.6 * forecast_linear[i] + 0.4 * forecast_exp[i], 4)
        for i in range(steps)
    ]

    # ── Intervalo de confiança (±1.5 std do erro de previsão) ────────────
    residuals = [vals[i] - (intercept + slope * i) for i in range(n)]
    std_err = math.sqrt(sum(r ** 2 for r in residuals) / max(n - 2, 1))
    margin = 1.5 * std_err
    ci = [(round(v - margin, 4), round(v + margin, 4)) for v in forecast_combined]

    # ── Confiabilidade por R² ────────────────────────────────────────────
    ss_tot = sum((v - mean_y) ** 2 for v in vals)
    ss_res = sum(residuals[i] ** 2 for i in range(n))
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
    if r2 >= 0.7 and n >= 10:
        reliability = "alta"
    elif r2 >= 0.4 and n >= 5:
        reliability = "moderada"
    else:
        reliability = "baixa"

    # ── Descrição ────────────────────────────────────────────────────────
    trend_word = "crescimento" if slope > 0 else ("queda" if slope < 0 else "estabilidade")
    description = (
        f"Previsão baseada em tendência de {trend_word} (R²={r2:.2f}, confiabilidade {reliability}). "
        f"Próximos {steps} períodos: {', '.join(str(v) for v in forecast_combined)}."
    )

    return {
        "method":              "linear + exponential_smoothing",
        "forecast_linear":     forecast_linear,
        "forecast_exp":        forecast_exp,
        "forecast_combined":   forecast_combined,
        "confidence_interval": ci,
        "r_squared":           round(r2, 4),
        "reliability":         reliability,
        "description":         description,
    }


def _empty(msg: str) -> Dict:
    return {
        "method": "N/A", "forecast_linear": [], "forecast_exp": [],
        "forecast_combined": [], "confidence_interval": [],
        "r_squared": 0.0, "reliability": "baixa", "description": msg,
    }

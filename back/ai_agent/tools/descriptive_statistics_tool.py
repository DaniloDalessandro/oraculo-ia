"""
Descriptive Statistics Tool

Calcula estatísticas descritivas completas sobre colunas numéricas
dos dados retornados pela consulta SQL.
Puro Python — sem dependências externas.
"""
import math
from typing import Any, Dict, List, Optional


def descriptive_statistics_tool(rows: List[Dict], numeric_columns: List[str]) -> Dict:
    """
    Calcula estatísticas descritivas para cada coluna numérica.

    Returns:
        {
            "stats": {
                "<col>": {
                    "count": int, "mean": float, "median": float,
                    "min": float, "max": float, "range": float,
                    "std": float, "variance": float,
                    "q1": float, "q3": float, "iqr": float,
                    "p10": float, "p90": float,
                    "skewness_label": str,
                    "preferred_avg": str,
                }
            }
        }
    """
    stats = {}
    for col in numeric_columns:
        vals = [_to_float(r[col]) for r in rows if r.get(col) is not None]
        if not vals:
            continue
        stats[col] = _calc(vals)
    return {"stats": stats}


def _calc(vals: List[float]) -> Dict:
    n = len(vals)
    sorted_vals = sorted(vals)
    mean = sum(vals) / n
    median = _percentile(sorted_vals, 50)
    variance = sum((v - mean) ** 2 for v in vals) / max(n - 1, 1)
    std = math.sqrt(variance)
    q1 = _percentile(sorted_vals, 25)
    q3 = _percentile(sorted_vals, 75)
    iqr = q3 - q1
    p10 = _percentile(sorted_vals, 10)
    p90 = _percentile(sorted_vals, 90)

    # Skewness label
    if n >= 5 and std > 0:
        skew = sum((v - mean) ** 3 for v in vals) / (n * std ** 3)
        if skew > 1:
            skewness_label = "assimetria positiva forte (cauda à direita)"
        elif skew > 0.5:
            skewness_label = "assimetria positiva moderada"
        elif skew < -1:
            skewness_label = "assimetria negativa forte (cauda à esquerda)"
        elif skew < -0.5:
            skewness_label = "assimetria negativa moderada"
        else:
            skewness_label = "distribuição aproximadamente simétrica"
    else:
        skewness_label = "amostra insuficiente para avaliar assimetria"

    # Média vs mediana recomendação
    if abs(mean - median) > 0.2 * abs(mean) and std > 0:
        preferred_avg = "mediana (distribuição assimétrica detectada)"
    else:
        preferred_avg = "média (distribuição aproximadamente simétrica)"

    return {
        "count":           n,
        "mean":            round(mean, 4),
        "median":          round(median, 4),
        "min":             round(sorted_vals[0], 4),
        "max":             round(sorted_vals[-1], 4),
        "range":           round(sorted_vals[-1] - sorted_vals[0], 4),
        "std":             round(std, 4),
        "variance":        round(variance, 4),
        "q1":              round(q1, 4),
        "q3":              round(q3, 4),
        "iqr":             round(iqr, 4),
        "p10":             round(p10, 4),
        "p90":             round(p90, 4),
        "skewness_label":  skewness_label,
        "preferred_avg":   preferred_avg,
    }


def _percentile(sorted_vals: List[float], p: float) -> float:
    n = len(sorted_vals)
    if n == 0:
        return 0.0
    if n == 1:
        return sorted_vals[0]
    idx = (p / 100) * (n - 1)
    lo = int(idx)
    hi = min(lo + 1, n - 1)
    frac = idx - lo
    return sorted_vals[lo] + frac * (sorted_vals[hi] - sorted_vals[lo])


def _to_float(val: Any) -> float:
    if isinstance(val, (int, float)):
        return float(val)
    try:
        return float(str(val).replace(",", "."))
    except (ValueError, TypeError):
        return 0.0

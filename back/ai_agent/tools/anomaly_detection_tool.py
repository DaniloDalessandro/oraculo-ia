"""
Anomaly Detection Tool

Detecta anomalias em séries de valores usando Z-Score e IQR.
Puro Python — sem dependências externas.
"""
import math
from typing import Any, Dict, List, Optional


def anomaly_detection_tool(
    values: List[float],
    labels: Optional[List[str]] = None,
    z_threshold: float = 2.5,
) -> Dict:
    """
    Detecta anomalias via Z-Score e IQR.

    Args:
        values: Série numérica.
        labels: Rótulos correspondentes (ex: nomes de berços, meses).
        z_threshold: Limiar z-score (padrão 2.5).

    Returns:
        {
            "has_anomalies": bool,
            "anomalies_zscore": [{label, value, z_score}],
            "anomalies_iqr": [{label, value, type}],
            "outlier_count": int,
            "outlier_pct": float,
            "description": str,
        }
    """
    n = len(values)
    if n < 4:
        return _empty("Dados insuficientes para detecção de anomalias (mínimo 4 pontos).")

    vals = [float(v) for v in values]
    lbls = labels if labels and len(labels) == n else [str(i + 1) for i in range(n)]

    mean = sum(vals) / n
    std = _std(vals)
    sorted_vals = sorted(vals)

    q1 = _percentile(sorted_vals, 25)
    q3 = _percentile(sorted_vals, 75)
    iqr = q3 - q1
    iqr_lo = q1 - 1.5 * iqr
    iqr_hi = q3 + 1.5 * iqr

    # ── Z-Score ──────────────────────────────────────────────────────────
    anomalies_z = []
    if std > 0:
        for i, v in enumerate(vals):
            z = (v - mean) / std
            if abs(z) > z_threshold:
                anomalies_z.append({
                    "label":   lbls[i],
                    "value":   round(v, 4),
                    "z_score": round(z, 2),
                    "type":    "pico" if v > mean else "queda",
                })
        anomalies_z.sort(key=lambda x: abs(x["z_score"]), reverse=True)

    # ── IQR ──────────────────────────────────────────────────────────────
    anomalies_iqr = []
    for i, v in enumerate(vals):
        if v > iqr_hi:
            anomalies_iqr.append({"label": lbls[i], "value": round(v, 4), "type": "outlier_alto"})
        elif v < iqr_lo:
            anomalies_iqr.append({"label": lbls[i], "value": round(v, 4), "type": "outlier_baixo"})

    all_outlier_labels = {a["label"] for a in anomalies_z} | {a["label"] for a in anomalies_iqr}
    outlier_count = len(all_outlier_labels)
    outlier_pct = round(outlier_count / n * 100, 1)
    has_anomalies = outlier_count > 0

    # ── Descrição ────────────────────────────────────────────────────────
    if has_anomalies:
        top = anomalies_z[0] if anomalies_z else anomalies_iqr[0]
        description = (
            f"{outlier_count} anomalia(s) detectada(s) ({outlier_pct}% dos dados). "
            f"Valor mais extremo: '{top['label']}' = {top['value']} "
            f"({'z=' + str(top.get('z_score','')) if 'z_score' in top else top.get('type','')})."
        )
    else:
        description = "Nenhuma anomalia significativa detectada nos dados."

    return {
        "has_anomalies":    has_anomalies,
        "anomalies_zscore": anomalies_z[:5],
        "anomalies_iqr":    anomalies_iqr[:5],
        "outlier_count":    outlier_count,
        "outlier_pct":      outlier_pct,
        "description":      description,
        "bounds": {
            "z_lower": round(mean - z_threshold * std, 4),
            "z_upper": round(mean + z_threshold * std, 4),
            "iqr_lower": round(iqr_lo, 4),
            "iqr_upper": round(iqr_hi, 4),
        },
    }


def _std(vals: List[float]) -> float:
    n = len(vals)
    if n < 2:
        return 0.0
    mean = sum(vals) / n
    return math.sqrt(sum((v - mean) ** 2 for v in vals) / (n - 1))


def _percentile(sorted_vals: List[float], p: float) -> float:
    n = len(sorted_vals)
    if n == 0:
        return 0.0
    idx = (p / 100) * (n - 1)
    lo = int(idx)
    hi = min(lo + 1, n - 1)
    return sorted_vals[lo] + (idx - lo) * (sorted_vals[hi] - sorted_vals[lo])


def _empty(msg: str) -> Dict:
    return {
        "has_anomalies": False, "anomalies_zscore": [], "anomalies_iqr": [],
        "outlier_count": 0, "outlier_pct": 0.0, "description": msg, "bounds": {},
    }

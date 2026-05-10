"""
Correlation Analysis Tool

Calcula correlação entre pares de colunas numéricas.
Métodos: Pearson e Spearman.
Puro Python — sem dependências externas.
"""
import math
from typing import Any, Dict, List, Tuple


def correlation_analysis_tool(rows: List[Dict], numeric_columns: List[str]) -> Dict:
    """
    Calcula correlação entre todos os pares de colunas numéricas.

    Returns:
        {
            "pairs": [
                {
                    "col_a": str, "col_b": str,
                    "pearson": float, "spearman": float,
                    "strength": str, "direction": str, "description": str,
                }
            ],
            "strongest_pair": dict | None,
            "description": str,
        }
    """
    if len(numeric_columns) < 2 or len(rows) < 5:
        return {"pairs": [], "strongest_pair": None,
                "description": "Dados insuficientes para análise de correlação."}

    pairs = []
    for i, col_a in enumerate(numeric_columns):
        for col_b in numeric_columns[i + 1:]:
            vals_a, vals_b = _extract_pair(rows, col_a, col_b)
            if len(vals_a) < 5:
                continue
            pearson = _pearson(vals_a, vals_b)
            spearman = _spearman(vals_a, vals_b)
            strength, direction = _classify(pearson)
            pairs.append({
                "col_a":      col_a,
                "col_b":      col_b,
                "pearson":    round(pearson, 4),
                "spearman":   round(spearman, 4),
                "strength":   strength,
                "direction":  direction,
                "description": (
                    f"'{col_a}' e '{col_b}': correlação {strength} {direction} "
                    f"(Pearson={pearson:.2f}, Spearman={spearman:.2f})."
                ),
            })

    pairs.sort(key=lambda p: abs(p["pearson"]), reverse=True)
    strongest = pairs[0] if pairs else None

    summary = (
        f"{len(pairs)} par(es) analisado(s). "
        + (f"Correlação mais forte: {strongest['description']}" if strongest else "Nenhuma correlação significativa.")
    )

    return {"pairs": pairs[:10], "strongest_pair": strongest, "description": summary}


# ── Helpers ──────────────────────────────────────────────────────────────── #

def _extract_pair(rows, col_a, col_b) -> Tuple[List[float], List[float]]:
    va, vb = [], []
    for r in rows:
        a, b = r.get(col_a), r.get(col_b)
        if a is not None and b is not None:
            try:
                va.append(float(a))
                vb.append(float(b))
            except (ValueError, TypeError):
                pass
    return va, vb


def _pearson(x: List[float], y: List[float]) -> float:
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    num = sum((x[i] - mx) * (y[i] - my) for i in range(n))
    dx = math.sqrt(sum((v - mx) ** 2 for v in x))
    dy = math.sqrt(sum((v - my) ** 2 for v in y))
    return num / (dx * dy) if dx * dy > 0 else 0.0


def _spearman(x: List[float], y: List[float]) -> float:
    def ranks(lst):
        sorted_lst = sorted(enumerate(lst), key=lambda t: t[1])
        r = [0.0] * len(lst)
        for rank, (idx, _) in enumerate(sorted_lst):
            r[idx] = rank + 1
        return r
    rx, ry = ranks(x), ranks(y)
    return _pearson(rx, ry)


def _classify(r: float) -> Tuple[str, str]:
    direction = "positiva" if r >= 0 else "negativa"
    ar = abs(r)
    if ar >= 0.8:
        strength = "muito forte"
    elif ar >= 0.6:
        strength = "forte"
    elif ar >= 0.4:
        strength = "moderada"
    elif ar >= 0.2:
        strength = "fraca"
    else:
        strength = "desprezível"
    return strength, direction

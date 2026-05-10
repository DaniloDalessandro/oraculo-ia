"""
Data Quality Tool

Valida qualidade dos dados retornados pela consulta SQL
antes de aplicar análise estatística.
"""
import math
from typing import Any, Dict, List


def data_quality_tool(rows: List[Dict], columns: List[str]) -> Dict:
    """
    Avalia qualidade dos dados para análise estatística.

    Returns:
        {
            "quality_score": float (0-1),
            "sample_size": int,
            "numeric_columns": [str],
            "date_columns": [str],
            "text_columns": [str],
            "null_rates": {col: float},
            "warnings": [str],
            "is_sufficient": bool,
        }
    """
    warnings = []
    n = len(rows)

    if n == 0:
        return {
            "quality_score": 0.0, "sample_size": 0,
            "numeric_columns": [], "date_columns": [], "text_columns": [],
            "null_rates": {}, "warnings": ["Nenhum dado retornado."], "is_sufficient": False,
        }

    # ── Classificar colunas ──────────────────────────────────────────────
    numeric_cols, date_cols, text_cols = [], [], []
    for col in columns:
        vals = [r[col] for r in rows if r.get(col) is not None]
        if not vals:
            continue
        sample = vals[0]
        if _is_numeric(sample):
            numeric_cols.append(col)
        elif _is_date(sample):
            date_cols.append(col)
        else:
            text_cols.append(col)

    # ── Taxa de nulos ────────────────────────────────────────────────────
    null_rates = {}
    penalties = 0.0
    for col in columns:
        nulls = sum(1 for r in rows if r.get(col) is None)
        rate = nulls / n
        null_rates[col] = round(rate, 3)
        if rate > 0.3:
            warnings.append(f"Coluna '{col}' tem {rate*100:.0f}% de valores nulos.")
            penalties += 0.1
        elif rate > 0.1:
            penalties += 0.05

    # ── Amostragem ───────────────────────────────────────────────────────
    if n < 5:
        warnings.append(f"Amostra muito pequena ({n} registros). Análise estatística com baixa confiabilidade.")
        penalties += 0.4
    elif n < 20:
        warnings.append(f"Amostra reduzida ({n} registros). Resultados podem não ser representativos.")
        penalties += 0.2
    elif n < 50:
        penalties += 0.05

    # ── Duplicatas ───────────────────────────────────────────────────────
    if len(columns) > 0:
        first_col = columns[0]
        vals = [r.get(first_col) for r in rows]
        if len(vals) != len(set(str(v) for v in vals)) and len(columns) == 1:
            warnings.append("Possíveis valores duplicados detectados.")
            penalties += 0.1

    # ── Outliers brutos por coluna numérica ──────────────────────────────
    for col in numeric_cols:
        vals = [_to_float(r[col]) for r in rows if r.get(col) is not None]
        if len(vals) < 4:
            continue
        mean = sum(vals) / len(vals)
        std = _std(vals)
        if std > 0:
            extremes = sum(1 for v in vals if abs(v - mean) > 3 * std)
            if extremes:
                warnings.append(f"Coluna '{col}': {extremes} valor(es) extremo(s) detectado(s) (z-score > 3).")
                penalties += 0.05

    quality_score = round(max(0.0, 1.0 - min(penalties, 0.8)), 2)
    is_sufficient = n >= 3 and quality_score >= 0.4

    return {
        "quality_score":    quality_score,
        "sample_size":      n,
        "numeric_columns":  numeric_cols,
        "date_columns":     date_cols,
        "text_columns":     text_cols,
        "null_rates":       null_rates,
        "warnings":         warnings,
        "is_sufficient":    is_sufficient,
    }


# ── Helpers ──────────────────────────────────────────────────────────────── #

def _is_numeric(val: Any) -> bool:
    if isinstance(val, (int, float)):
        return True
    if isinstance(val, str):
        try:
            float(val.replace(",", "."))
            return True
        except ValueError:
            return False
    return False


def _is_date(val: Any) -> bool:
    if not isinstance(val, str):
        return False
    import re
    return bool(re.match(r'\d{4}-\d{2}', val))


def _to_float(val: Any) -> float:
    if isinstance(val, (int, float)):
        return float(val)
    try:
        return float(str(val).replace(",", "."))
    except (ValueError, TypeError):
        return 0.0


def _std(vals: List[float]) -> float:
    n = len(vals)
    if n < 2:
        return 0.0
    mean = sum(vals) / n
    variance = sum((v - mean) ** 2 for v in vals) / (n - 1)
    return math.sqrt(variance)

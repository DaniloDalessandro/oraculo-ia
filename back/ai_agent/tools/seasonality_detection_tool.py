"""
Seasonality Detection Tool

Detecta padrões sazonais em séries temporais.
Agrupa valores por posição no ciclo (mês, trimestre) e identifica picos/vales.
Puro Python — sem dependências externas.
"""
from typing import Dict, List, Optional

_MONTHS_PT = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
}

_QUARTER_PT = {1: "T1 (Jan-Mar)", 2: "T2 (Abr-Jun)", 3: "T3 (Jul-Set)", 4: "T4 (Out-Dez)"}


def seasonality_detection_tool(
    values: List[float],
    labels: Optional[List[str]] = None,
) -> Dict:
    """
    Detecta sazonalidade em série de valores.

    Args:
        values: Série numérica. Se labels fornecidos com 'YYYY-MM', agrupa por mês.
        labels: Rótulos de período (ex: ['2023-01', '2023-02', ...]).

    Returns:
        {
            "has_seasonality": bool,
            "seasonal_strength": float (0-1),
            "peak_periods": [str],
            "valley_periods": [str],
            "monthly_pattern": {month_num: avg},
            "quarterly_pattern": {quarter: avg},
            "description": str,
        }
    """
    n = len(values)
    if n < 6:
        return _empty("Dados insuficientes para detecção de sazonalidade (mínimo 6 pontos).")

    vals = [float(v) for v in values]
    monthly_sums: dict[int, list] = {}
    quarterly_sums: dict[int, list] = {}

    # Extrair mês/trimestre dos labels se disponíveis
    if labels and len(labels) == n:
        for i, lbl in enumerate(labels):
            month = _extract_month(lbl)
            if month:
                monthly_sums.setdefault(month, []).append(vals[i])
                quarterly_sums.setdefault((month - 1) // 3 + 1, []).append(vals[i])
    else:
        # Sem labels: assume ciclo de 12 pontos (posição como mês)
        for i, v in enumerate(vals):
            m = (i % 12) + 1
            monthly_sums.setdefault(m, []).append(v)
            quarterly_sums.setdefault((m - 1) // 3 + 1, []).append(v)

    if len(monthly_sums) < 3:
        return _empty("Poucos períodos distintos para análise de sazonalidade.")

    monthly_avg = {m: sum(v) / len(v) for m, v in monthly_sums.items()}
    quarterly_avg = {q: round(sum(v) / len(v), 4) for q, v in quarterly_sums.items()}

    overall_mean = sum(vals) / len(vals)
    if overall_mean == 0:
        return _empty("Média geral zero — impossível calcular sazonalidade relativa.")

    # Força sazonal = amplitude relativa dos médias mensais
    sorted_avgs = sorted(monthly_avg.values())
    amplitude = (sorted_avgs[-1] - sorted_avgs[0]) / abs(overall_mean)
    seasonal_strength = round(min(amplitude, 1.0), 3)
    has_seasonality = seasonal_strength > 0.15

    # Picos e vales (top 3 meses)
    sorted_months = sorted(monthly_avg.items(), key=lambda x: x[1], reverse=True)
    peak_months = [_MONTHS_PT.get(m, str(m)) for m, _ in sorted_months[:3]]
    valley_months = [_MONTHS_PT.get(m, str(m)) for m, _ in sorted_months[-3:]]

    # Descrição
    if has_seasonality:
        description = (
            f"Sazonalidade detectada (intensidade {seasonal_strength:.0%}). "
            f"Picos: {', '.join(peak_months[:2])}. "
            f"Baixa atividade: {', '.join(valley_months[:2])}."
        )
    else:
        description = "Sem sazonalidade significativa detectada no período analisado."

    return {
        "has_seasonality":   has_seasonality,
        "seasonal_strength": seasonal_strength,
        "peak_periods":      peak_months,
        "valley_periods":    valley_months,
        "monthly_pattern":   {_MONTHS_PT.get(m, str(m)): round(v, 4) for m, v in monthly_avg.items()},
        "quarterly_pattern": {_QUARTER_PT.get(q, str(q)): v for q, v in quarterly_avg.items()},
        "description":       description,
    }


def _extract_month(label: str) -> Optional[int]:
    import re
    m = re.search(r'\d{4}-(\d{2})', label)
    if m:
        return int(m.group(1))
    m = re.search(r'^(\d{1,2})$', label.strip())
    if m:
        v = int(m.group(1))
        return v if 1 <= v <= 12 else None
    return None


def _empty(msg: str) -> Dict:
    return {
        "has_seasonality": False, "seasonal_strength": 0.0,
        "peak_periods": [], "valley_periods": [],
        "monthly_pattern": {}, "quarterly_pattern": {},
        "description": msg,
    }

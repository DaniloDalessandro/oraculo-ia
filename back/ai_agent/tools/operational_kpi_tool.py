"""
Operational KPI Tool

Gera KPIs portuários automaticamente a partir dos dados retornados.
Detecta colunas relevantes e calcula indicadores operacionais.
"""
from typing import Any, Dict, List, Optional
import math


# Palavras-chave por tipo de KPI
_KPI_COLUMNS = {
    "throughput":    ["toneladas", "quantidade_toneladas", "movimentacao", "movimentação", "carga"],
    "time_op":       ["horas_operacao", "tempo_operacao", "duracao", "duração", "horas_efetivas"],
    "productivity":  ["produtividade", "plr", "prancha"],
    "permanence":    ["permanencia", "permanência", "tempo_permanencia", "horas_total"],
    "queue":         ["fila", "tempo_fila", "espera"],
    "occupancy":     ["ocupacao", "ocupação", "utilizacao", "utilização"],
}


def operational_kpi_tool(rows: List[Dict], columns: List[str], intent: str = "") -> Dict:
    """
    Calcula KPIs portuários automaticamente.

    Returns:
        {
            "kpis": {kpi_name: {value, unit, label, benchmark_note}},
            "description": str,
        }
    """
    if not rows or not columns:
        return {"kpis": {}, "description": "Sem dados para calcular KPIs."}

    cols_lower = {c.lower(): c for c in columns}
    kpis = {}

    # ── Throughput (toneladas) ────────────────────────────────────────────
    tp_col = _find_col(cols_lower, _KPI_COLUMNS["throughput"])
    if tp_col:
        vals = _num_vals(rows, tp_col)
        if vals:
            kpis["throughput_total"] = {
                "value": round(sum(vals), 2), "unit": "t",
                "label": "Throughput Total",
                "benchmark_note": _benchmark(sum(vals), "throughput_total"),
            }
            kpis["throughput_medio"] = {
                "value": round(sum(vals) / len(vals), 2), "unit": "t/atracação",
                "label": "Throughput Médio por Atracação",
                "benchmark_note": "",
            }

    # ── Produtividade ─────────────────────────────────────────────────────
    prod_col = _find_col(cols_lower, _KPI_COLUMNS["productivity"])
    if prod_col and "produtividade" in prod_col.lower():
        vals = _num_vals(rows, prod_col)
        if vals:
            kpis["produtividade_media"] = {
                "value": round(sum(vals) / len(vals), 4), "unit": "",
                "label": "Produtividade Média",
                "benchmark_note": "",
            }

    # ── Tempo operacional ─────────────────────────────────────────────────
    time_col = _find_col(cols_lower, _KPI_COLUMNS["time_op"])
    if time_col:
        vals = _num_vals(rows, time_col)
        if vals:
            kpis["tempo_operacional_medio"] = {
                "value": round(sum(vals) / len(vals), 2), "unit": "h",
                "label": "Tempo Operacional Médio",
                "benchmark_note": _benchmark(sum(vals) / len(vals), "tempo_op"),
            }

    # ── Taxa de utilização (se houver colunas de ocupação) ───────────────
    occ_col = _find_col(cols_lower, _KPI_COLUMNS["occupancy"])
    if occ_col:
        vals = _num_vals(rows, occ_col)
        if vals:
            kpis["taxa_utilizacao_media"] = {
                "value": round(sum(vals) / len(vals), 2), "unit": "%",
                "label": "Taxa de Utilização Média",
                "benchmark_note": _benchmark(sum(vals) / len(vals), "utilizacao"),
            }

    # ── KPI genérico: contagem e variação ────────────────────────────────
    # Sempre: contar registros
    kpis["total_registros"] = {
        "value": len(rows), "unit": "registros",
        "label": "Total de Registros Analisados",
        "benchmark_note": "",
    }

    # Coluna numérica principal: variação máx-mín
    num_cols = [c for c in columns if _num_vals(rows, c)]
    if num_cols:
        main = num_cols[0]
        vals = _num_vals(rows, main)
        if len(vals) > 1:
            variation = ((max(vals) - min(vals)) / abs(sum(vals) / len(vals)) * 100) if sum(vals) != 0 else 0
            kpis["variacao_relativa"] = {
                "value": round(variation, 1), "unit": "%",
                "label": f"Variação Relativa ({main})",
                "benchmark_note": "Alta variação (>50%) pode indicar instabilidade operacional." if variation > 50 else "",
            }

    description = (
        f"{len(kpis)} KPI(s) calculado(s): "
        + ", ".join(f"{k['label']}={k['value']}{k['unit']}" for k in list(kpis.values())[:4])
        + ("..." if len(kpis) > 4 else ".")
    )

    return {"kpis": kpis, "description": description}


# ── Helpers ──────────────────────────────────────────────────────────────── #

def _find_col(cols_lower: dict, keywords: list) -> Optional[str]:
    for kw in keywords:
        for col_l, col_orig in cols_lower.items():
            if kw in col_l:
                return col_orig
    return None


def _num_vals(rows: List[Dict], col: str) -> List[float]:
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


def _benchmark(value: float, kpi_type: str) -> str:
    benchmarks = {
        "throughput_total": [
            (1_000_000, "Throughput elevado — porto de grande porte."),
            (100_000, "Throughput médio — porto de porte médio."),
            (0, "Throughput baixo — porto de pequeno porte ou período curto."),
        ],
        "tempo_op": [
            (72, "Tempo de operação alto — verificar eficiência."),
            (24, "Tempo de operação dentro do padrão."),
            (0, "Tempo de operação baixo — operação rápida."),
        ],
        "utilizacao": [
            (85, "Utilização muito alta — risco de congestionamento."),
            (60, "Utilização dentro do padrão ideal."),
            (0, "Utilização baixa — capacidade ociosa."),
        ],
    }
    thresholds = benchmarks.get(kpi_type, [])
    for threshold, note in thresholds:
        if value >= threshold:
            return note
    return ""

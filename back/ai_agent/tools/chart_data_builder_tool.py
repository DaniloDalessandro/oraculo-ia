"""
Chart Data Builder Tool

Converte resultado SQL para formato JSON compatível com Recharts.
Garante nomes simples, valores válidos, ordenação correta e limite de categorias.
"""
import re
import logging
from typing import Any, Dict, List

logger = logging.getLogger("ai_agent")

MAX_CATEGORIES = 15
TOP_N_CATEGORIES = 10

MONTH_PT = {
    1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
    7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez",
}


def chart_data_builder_tool(
    result: Dict[str, Any],
    plan: Dict,
) -> List[Dict]:
    """
    Transforma o resultado SQL em lista de dicts prontos para Recharts.

    Returns:
        Lista de pontos de dados com x_key e y_keys formatados.
    """
    dict_rows = result.get("dict_rows", [])
    if not dict_rows:
        return []

    x_key = plan.get("x_key", "")
    y_keys = plan.get("y_keys", [])
    chart_type = plan.get("type", "bar")

    is_temporal = _is_temporal_key(x_key)
    processed: List[Dict] = []

    for row in dict_rows:
        point: Dict[str, Any] = {}

        # Eixo X
        raw_x = row.get(x_key)
        if raw_x is not None:
            point[x_key] = _format_x(raw_x, x_key, is_temporal)

        # Eixos Y — garantir numérico
        for y_key in y_keys:
            point[y_key] = _to_float(row.get(y_key))

        if point:
            processed.append(point)

    # Ordenar
    processed = _sort_data(processed, x_key, y_keys, is_temporal, chart_type)

    # Limitar categorias (não temporal)
    if not is_temporal and chart_type in ("bar", "pie") and len(processed) > MAX_CATEGORIES:
        processed = _group_others(processed, x_key, y_keys, TOP_N_CATEGORIES)

    logger.info("Chart data built: %d pontos, tipo=%s", len(processed), chart_type)
    return processed


# ─── Helpers ─────────────────────────────────────────────────────────────── #


def _is_temporal_key(key: str) -> bool:
    kw = ("data", "date", "mes", "mês", "ano", "year", "month", "dt_", "_dt", "periodo", "período")
    return any(k in key.lower() for k in kw)


def _format_x(val: Any, key: str, is_temporal: bool) -> str:
    """Formata valor do eixo X para exibição amigável."""
    if val is None:
        return "N/A"

    s = str(val).strip()

    if not is_temporal:
        return s[:60]

    return _format_date_str(s)


def _format_date_str(s: str) -> str:
    """Converte string de data para formato legível (ex: 'Jan/25')."""
    # Somente ano: "2025"
    if re.match(r"^\d{4}$", s):
        return s

    # YYYY-MM-DD ou YYYY-MM-DD HH:MM
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        year, month = int(m.group(1)), int(m.group(2))
        return f"{MONTH_PT.get(month, f'M{month}')}/{str(year)[2:]}"

    # YYYY-MM (DATE_TRUNC result como string)
    m = re.match(r"^(\d{4})-(\d{2})$", s)
    if m:
        year, month = int(m.group(1)), int(m.group(2))
        return f"{MONTH_PT.get(month, f'M{month}')}/{str(year)[2:]}"

    # Número decimal como timestamp (inesperado — retorna como está)
    return s[:20]


def _to_float(val: Any) -> float:
    """Converte valor para float, retorna 0.0 em caso de falha."""
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return round(float(val), 4)
    try:
        return round(float(str(val).replace(",", ".")), 4)
    except (TypeError, ValueError):
        return 0.0


def _sort_data(
    data: List[Dict],
    x_key: str,
    y_keys: List[str],
    is_temporal: bool,
    chart_type: str,
) -> List[Dict]:
    """Ordena os dados por data (temporal) ou por valor desc (ranking)."""
    if not data:
        return data

    if is_temporal:
        try:
            return sorted(data, key=lambda r: _temporal_sort_key(str(r.get(x_key, ""))))
        except Exception:
            return data

    if chart_type in ("bar", "pie") and y_keys:
        try:
            return sorted(data, key=lambda r: _to_float(r.get(y_keys[0], 0)), reverse=True)
        except Exception:
            return data

    return data


def _temporal_sort_key(label: str) -> str:
    """
    Converte labels como 'Jan/25', 'Fev/25', '2025' em chave sortável.
    """
    month_order = {v: i for i, v in enumerate(MONTH_PT.values(), 1)}

    # 'Jan/25' → '2025-01'
    m = re.match(r"^([A-Za-záéíóú]+)/(\d{2})$", label)
    if m:
        month_name, year_short = m.group(1).capitalize(), m.group(2)
        month_num = month_order.get(month_name[:3], 0)
        full_year = f"20{year_short}" if int(year_short) < 50 else f"19{year_short}"
        return f"{full_year}-{month_num:02d}"

    # Somente ano
    if re.match(r"^\d{4}$", label):
        return f"{label}-00"

    return label


def _group_others(
    data: List[Dict],
    x_key: str,
    y_keys: List[str],
    top_n: int,
) -> List[Dict]:
    """Mantém top N e agrupa restante como 'Outros'."""
    top = data[:top_n]
    rest = data[top_n:]

    if not rest or not y_keys:
        return top

    outros: Dict[str, Any] = {x_key: "Outros"}
    for y_key in y_keys:
        outros[y_key] = round(sum(_to_float(r.get(y_key, 0)) for r in rest), 4)

    top.append(outros)
    return top

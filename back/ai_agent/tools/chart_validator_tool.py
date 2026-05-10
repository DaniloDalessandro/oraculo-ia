"""
Chart Validator Tool

Verifica se os dados estão prontos para renderização no Recharts.
"""
import logging
from typing import Any, Dict, List

logger = logging.getLogger("ai_agent")

MIN_POINTS_LINE = 2
MIN_POINTS_PIE = 2
MIN_POINTS_DEFAULT = 1


def chart_validator_tool(
    plan: Dict,
    data: List[Dict],
) -> Dict:
    """
    Valida se os dados e o plano são suficientes para renderizar o gráfico.

    Returns:
        {
            "can_render": bool,
            "reason": str,
            "warnings": list[str],
        }
    """
    if not plan.get("should_render", False):
        return _fail("Plano indica que gráfico não deve ser renderizado.")

    if not data:
        return _fail("Nenhum dado disponível para o gráfico.")

    x_key = plan.get("x_key", "")
    y_keys = plan.get("y_keys", [])
    chart_type = plan.get("type", "bar")

    warnings: List[str] = []

    # Verificar x_key
    if not x_key:
        return _fail("Eixo X não definido no plano do gráfico.")

    present_x = sum(1 for row in data[:10] if x_key in row)
    if present_x == 0:
        return _fail(f"Coluna de eixo X '{x_key}' não encontrada nos dados.")

    # Verificar y_keys
    if not y_keys:
        return _fail("Nenhuma métrica definida para o eixo Y.")

    for y_key in y_keys:
        present_y = sum(1 for row in data[:10] if y_key in row)
        if present_y == 0:
            return _fail(f"Coluna de eixo Y '{y_key}' não encontrada nos dados.")

    # Verificar pontos mínimos por tipo
    min_pts = _min_points(chart_type)
    if len(data) < min_pts:
        return _fail(
            f"Dados insuficientes: {len(data)} ponto(s). "
            f"Mínimo para {chart_type}: {min_pts}."
        )

    # Verificar valores numéricos nos y_keys
    for y_key in y_keys:
        numeric_count = sum(
            1 for row in data[:20]
            if isinstance(row.get(y_key), (int, float)) and row.get(y_key) is not None
        )
        if numeric_count == 0:
            warnings.append(
                f"Coluna '{y_key}' não possui valores numéricos válidos. "
                "O gráfico pode ficar em branco."
            )

    # Aviso sobre gráfico de linha com poucos pontos
    if chart_type == "line" and len(data) < 3:
        warnings.append("Gráfico de linha com menos de 3 pontos — considere tipo 'bar'.")

    # Aviso sobre muitos pontos
    if len(data) > 100:
        warnings.append(
            f"Gráfico com {len(data)} pontos pode ficar pesado — "
            "considere agregar mais os dados."
        )

    logger.info(
        "Chart validated: can_render=True type=%s points=%d warnings=%d",
        chart_type,
        len(data),
        len(warnings),
    )
    return {"can_render": True, "reason": "", "warnings": warnings}


def _min_points(chart_type: str) -> int:
    if chart_type == "line":
        return MIN_POINTS_LINE
    if chart_type == "pie":
        return MIN_POINTS_PIE
    return MIN_POINTS_DEFAULT


def _fail(reason: str) -> Dict:
    logger.info("Chart validation failed: %s", reason)
    return {"can_render": False, "reason": reason, "warnings": []}

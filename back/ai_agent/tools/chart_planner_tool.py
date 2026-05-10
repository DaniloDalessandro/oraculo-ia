"""
Chart Planner Tool — Especialista em Escolha de Gráficos

Decide o tipo de gráfico ideal usando regras determinísticas + LLM para
título e descrição. As regras sempre prevalecem sobre o LLM para type.
"""
import json
import logging
import re
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage

from ai_agent.services.gemini_service import invoke_llm

logger = logging.getLogger("ai_agent")

# ─── Prompt especialista ──────────────────────────────────────────────────── #

CHART_PLANNER_PROMPT = """
Você é um especialista em visualização de dados analíticos para sistemas portuários.

PERGUNTA DO USUÁRIO: {question}
INTENÇÃO CLASSIFICADA: {intent}
COLUNAS DO RESULTADO: {columns}
TIPOS DAS COLUNAS: {column_types}
QUANTIDADE DE LINHAS: {row_count}
QUANTIDADE DE CATEGORIAS DISTINTAS NO EIXO X: {category_count}
NOMES LONGOS NO EIXO X (>20 chars): {has_long_names}
CONTÉM COLUNAS TEMPORAIS: {has_dates}
CONTÉM COLUNAS NUMÉRICAS: {has_numerics}
AMOSTRA DOS DADOS (primeiros 5 registros):
{data_sample}

TIPO DE GRÁFICO DETERMINADO PELAS REGRAS: {rule_based_type}

REGRAS DE DECISÃO (respeite o tipo determinado pelas regras):
1. "line" → x_key é data/mês/ano, pergunta pede evolução, tendência ou histórico
2. "bar" → comparação entre categorias com métrica agregada
3. "horizontal_bar" → ranking ("top", "maiores", "menores"), ou nomes longos no eixo
4. "pie" → participação/percentual/distribuição com ≤6 categorias
5. "area" → evolução acumulada no tempo
6. "composed" → duas métricas diferentes no mesmo eixo temporal
7. "kpi" → resultado é um único número (1 linha, 1 ou 2 colunas numéricas)
8. "scatter" → correlação entre duas variáveis numéricas
9. "table" → muitas colunas textuais, estrutura complexa, ou dados não-visuais

Responda em JSON exatamente neste formato:
{{
  "should_render": true ou false,
  "type": "{rule_based_type}",
  "title": "título descritivo e conciso do gráfico",
  "description": "frase curta explicando o que o gráfico mostra",
  "x_key": "nome EXATO de uma das colunas listadas acima para eixo X",
  "y_keys": ["nome EXATO de coluna numérica para eixo Y"],
  "category_key": null,
  "reason": "justificativa clara da escolha",
  "fallback": "table"
}}

OBRIGATÓRIO:
- x_key e y_keys DEVEM ser nomes EXATOS das colunas listadas
- y_keys só aceita colunas numéricas
- Para "kpi", x_key pode ser null e y_keys deve ter 1 elemento
- Para "pie", y_keys deve ter exatamente 1 elemento
- should_render = false se: 0 dados, apenas 1 coluna, tipo="table"

Responda APENAS com o JSON, sem texto adicional.
"""


# ─── Lógica de regras determinísticas ─────────────────────────────────────── #

_TEMPORAL_KEYWORDS = frozenset([
    "data", "date", "mes", "mês", "ano", "year", "month", "dt_", "_dt",
    "periodo", "período", "trimestre", "quarter", "semana", "week",
])

_RANKING_KEYWORDS = frozenset([
    "top", "maior", "maiores", "menor", "menores", "ranking",
    "melhor", "melhores", "pior", "piores", "mais", "menos",
])

_PARTICIPATION_KEYWORDS = frozenset([
    "percentual", "participação", "participacao", "distribuição", "distribuicao",
    "composição", "composicao", "proporção", "proporcao", "parcela", "fatia",
])

_CUMULATIVE_KEYWORDS = frozenset([
    "acumulado", "acumulada", "progressivo", "progressiva", "soma acumulada",
])


def _is_temporal(key: str) -> bool:
    return any(k in key.lower() for k in _TEMPORAL_KEYWORDS)


def _detect_column_types(columns: List[str], sample_rows: List[Dict]) -> Dict[str, str]:
    """Infere tipo de cada coluna a partir da amostra."""
    types = {}
    for col in columns:
        values = [r.get(col) for r in sample_rows if r.get(col) is not None]
        if not values:
            types[col] = "unknown"
            continue
        val = values[0]
        if isinstance(val, bool):
            types[col] = "bool"
        elif isinstance(val, (int, float)):
            types[col] = "numeric"
        else:
            s = str(val).strip()
            if re.match(r"^\d{4}-\d{2}", s) or re.match(r"^\d{4}$", s):
                types[col] = "temporal"
            else:
                try:
                    float(s.replace(",", "."))
                    types[col] = "numeric"
                except ValueError:
                    types[col] = "text"
    return types


def _has_long_names(data: List[Dict], x_key: str, threshold: int = 20) -> bool:
    """Verifica se algum label do eixo X é longo."""
    return any(len(str(r.get(x_key, ""))) > threshold for r in data[:20])


def _rule_based_decision(
    question: str,
    intent: str,
    columns: List[str],
    col_types: Dict[str, str],
    row_count: int,
    data: List[Dict],
) -> Dict:
    """
    Decide o tipo de gráfico usando regras determinísticas.
    Retorna um dict com type, x_key, y_keys sugeridos.
    """
    q_lower = question.lower()

    numeric_cols = [c for c in columns if col_types.get(c) == "numeric"]
    temporal_cols = [c for c in columns if col_types.get(c) in ("temporal",) or _is_temporal(c)]
    text_cols = [c for c in columns if col_types.get(c) == "text"]

    # ── KPI: resultado é um único número ──────────────────────────────────
    if row_count == 1 and len(numeric_cols) >= 1 and len(columns) <= 2:
        x_key = text_cols[0] if text_cols else (columns[0] if columns else "")
        y_keys = numeric_cols[:1]
        return {"type": "kpi", "x_key": x_key, "y_keys": y_keys}

    # Determinar x_key candidato
    if temporal_cols:
        x_key = temporal_cols[0]
    elif text_cols:
        x_key = text_cols[0]
    else:
        x_key = columns[0] if columns else ""

    y_keys = [c for c in numeric_cols if c != x_key]
    if not y_keys and numeric_cols:
        y_keys = numeric_cols[:1]

    category_count = len({str(r.get(x_key)) for r in data})

    # ── Table: muitas colunas ou sem numérico ──────────────────────────────
    if not y_keys or len(columns) > 6:
        return {"type": "table", "x_key": x_key, "y_keys": y_keys}

    # ── Evolução acumulada no tempo ────────────────────────────────────────
    if temporal_cols and any(kw in q_lower for kw in _CUMULATIVE_KEYWORDS):
        return {"type": "area", "x_key": x_key, "y_keys": y_keys}

    # ── Evolução temporal ──────────────────────────────────────────────────
    if temporal_cols or intent == "evolucao_temporal":
        chart_type = "composed" if len(y_keys) >= 2 else "line"
        return {"type": chart_type, "x_key": x_key, "y_keys": y_keys[:2]}

    # ── Participação percentual (pie só com ≤6 categorias) ─────────────────
    is_participation = any(kw in q_lower for kw in _PARTICIPATION_KEYWORDS)
    if is_participation and category_count <= 6 and len(y_keys) == 1:
        return {"type": "pie", "x_key": x_key, "y_keys": y_keys}

    # ── Ranking / nomes longos → horizontal bar ────────────────────────────
    is_ranking = intent == "ranking" or any(kw in q_lower for kw in _RANKING_KEYWORDS)
    long_names = _has_long_names(data, x_key)
    if is_ranking or long_names:
        return {"type": "horizontal_bar", "x_key": x_key, "y_keys": y_keys[:1]}

    # ── Comparação entre categorias → bar ─────────────────────────────────
    return {"type": "bar", "x_key": x_key, "y_keys": y_keys[:2]}


# ─── Tool principal ────────────────────────────────────────────────────────── #

def chart_planner_tool(
    question: str,
    intent: str,
    result: Dict[str, Any],
) -> Dict:
    """
    Planeja o gráfico ideal para os dados retornados.

    Returns dict com: should_render, type, title, description,
                      x_key, y_keys, reason, fallback
    """
    if not result.get("success") or result.get("row_count", 0) == 0:
        return _no_chart("Sem dados para gerar gráfico.")

    columns = result.get("columns", [])
    dict_rows = result.get("dict_rows", [])
    row_count = result.get("row_count", 0)

    if len(columns) < 1:
        return _no_chart("Resultado sem colunas.")

    # ── 1. Inferir tipos das colunas ──────────────────────────────────────
    col_types = _detect_column_types(columns, dict_rows[:10])

    # ── 2. Decisão por regras ─────────────────────────────────────────────
    rules = _rule_based_decision(question, intent, columns, col_types, row_count, dict_rows)
    rule_type = rules["type"]
    rule_x = rules.get("x_key", "")
    rule_y = rules.get("y_keys", [])

    if rule_type == "table":
        return _no_chart("Dados tabulares — gráfico não aplicável.")

    # ── 3. LLM para título, descrição e validação de chaves ───────────────
    has_dates = any(t in ("temporal",) or _is_temporal(c) for c, t in col_types.items())
    has_numerics = any(t == "numeric" for t in col_types.values())
    category_count = len({str(r.get(rule_x)) for r in dict_rows}) if rule_x else 0
    col_type_str = ", ".join(f"{c}:{t}" for c, t in col_types.items())
    data_sample = json.dumps(dict_rows[:5], ensure_ascii=False, default=str)

    prompt = CHART_PLANNER_PROMPT.format(
        question=question,
        intent=intent,
        columns=", ".join(columns),
        column_types=col_type_str,
        row_count=row_count,
        category_count=category_count,
        has_long_names=_has_long_names(dict_rows, rule_x) if rule_x else False,
        has_dates=has_dates,
        has_numerics=has_numerics,
        data_sample=data_sample,
        rule_based_type=rule_type,
    )

    try:
        raw = invoke_llm([HumanMessage(content=prompt)])
        json_match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not json_match:
            raise ValueError("Sem JSON na resposta do chart planner.")

        plan = json.loads(json_match.group())

        # ── 4. Validar e corrigir com as regras ───────────────────────────
        # O tipo SEMPRE vem das regras
        plan["type"] = rule_type

        # x_key deve existir nas colunas reais
        x_key = plan.get("x_key") or rule_x
        if x_key not in columns:
            x_key = rule_x if rule_x in columns else (columns[0] if columns else "")
        plan["x_key"] = x_key

        # y_keys devem existir e ser numéricos
        llm_y = [k for k in plan.get("y_keys", []) if k in columns]
        y_keys = llm_y if llm_y else rule_y
        y_keys = [k for k in y_keys if k in columns and k != x_key]
        if not y_keys:
            y_keys = [c for c in columns if c != x_key and col_types.get(c) == "numeric"][:2]
        if not y_keys:
            return _no_chart("Nenhuma coluna numérica encontrada para o eixo Y.")
        plan["y_keys"] = y_keys

        # KPI: máx 1 y_key
        if rule_type == "kpi":
            plan["y_keys"] = y_keys[:1]

        # Pie: máx 1 y_key, máx 6 categorias
        if rule_type == "pie":
            plan["y_keys"] = y_keys[:1]
            if category_count > 6:
                plan["type"] = "bar"

        plan.setdefault("fallback", "table")
        plan.setdefault("should_render", True)
        plan["should_render"] = rule_type not in ("table",)

        logger.info(
            "Chart plan: type=%s x=%s y=%s (regra=%s)",
            plan["type"], plan.get("x_key"), plan.get("y_keys"), rule_type,
        )
        return plan

    except Exception as exc:
        logger.warning("Chart planner LLM falhou: %s. Usando regras puras.", exc)
        return {
            "should_render": True,
            "type": rule_type,
            "title": _infer_title(question, rule_type),
            "description": "",
            "x_key": rule_x,
            "y_keys": rule_y,
            "category_key": None,
            "reason": f"Decisão por regras determinísticas (LLM indisponível): {rule_type}",
            "fallback": "table",
        }


# ─── Helpers ──────────────────────────────────────────────────────────────── #

def _infer_title(question: str, chart_type: str) -> str:
    """Título de fallback baseado na pergunta truncada."""
    q = question[:60].rstrip("?").strip()
    suffixes = {
        "line": " (evolução)",
        "horizontal_bar": " (ranking)",
        "pie": " (distribuição)",
        "area": " (acumulado)",
        "kpi": "",
    }
    return q + suffixes.get(chart_type, "")


def _no_chart(reason: str) -> Dict:
    return {
        "should_render": False,
        "type": "table",
        "title": "",
        "description": reason,
        "x_key": "",
        "y_keys": [],
        "category_key": None,
        "reason": reason,
        "fallback": "table",
    }

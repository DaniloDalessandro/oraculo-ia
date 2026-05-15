"""
Question Classifier Tool

Classifica a pergunta do usuário em uma intenção analítica.
Usa o LLM para classificação semântica.
"""
import json
import logging
import re
from typing import Dict

from langchain_core.messages import HumanMessage, SystemMessage

from ai_agent.services.gemini_service import invoke_llm

logger = logging.getLogger("ai_agent")

VALID_INTENTS = {
    "totalizacao",
    "comparacao",
    "ranking",
    "listagem",
    "media",
    "evolucao_temporal",
    "analise_por_navio",
    "analise_por_carga",
    "analise_por_berco",
    "analise_por_cliente",
    "analise_por_operador",
    "ambigua",
}

CHART_KEYWORDS = frozenset([
    "gráfico", "grafico", "chart", "plot", "plotar", "visualizar",
    "visualização", "visualizacao", "mostre em gráfico", "gere um gráfico",
    "compare em gráfico", "dashboard",
    "faça um gráfico", "crie um gráfico", "mostrar gráfico", "ver gráfico",
])

def detect_chart_request(question: str, intent: str = "") -> bool:
    """Retorna True APENAS se o usuário pedir gráfico explicitamente."""
    q = question.lower()
    return any(kw in q for kw in CHART_KEYWORDS)


# ── Detector de nível de detalhe ─────────────────────────────────────────── #

_CONCISE_KW = frozenset([
    "resumo", "resumo rapido", "breve", "rapido", "so o numero", "so o valor",
    "quanto", "quantos", "quantas", "qual o total", "qual a media",
])
_ANALYTICAL_KW = frozenset([
    "analise", "analisa", "analise detalhada", "detalhe", "detalhes",
    "explique", "explica", "por que", "porque", "como", "tendencia", "tendência",
    "sazonalidade", "correlacao", "correlação", "evolucao", "evolução",
    "insights", "insight", "aprofunde",
])
_TECHNICAL_KW = frozenset([
    "sql", "query", "consulta sql", "codigo", "código", "tecnico", "técnico",
    "metodologia", "como foi calculado", "mostre o sql", "mostre a query",
])


def detect_detail_level(question: str) -> str:
    """
    Detecta o nível de detalhe esperado pelo usuário.

    Returns:
        "concise" | "normal" | "analytical" | "technical"
    """
    q = question.lower()
    if any(kw in q for kw in _TECHNICAL_KW):
        return "technical"
    if any(kw in q for kw in _ANALYTICAL_KW):
        return "analytical"
    if any(kw in q for kw in _CONCISE_KW):
        return "concise"
    return "normal"


# ── Heuristic keyword map ────────────────────────────────────────────────── #
# Priority order matters: more specific intents first.
_HEURISTIC_MAP: list = [
    ("ranking", [
        "top ", "top5", "top10", "maior", "menor", "melhor", "pior",
        "ranking", "primeiros", "últimos", "ultimo", "primeiro",
        "record", "recorde", "destaque", "líder", "lider",
        "mais alto", "mais baixo", "mais movimentado",
    ]),
    ("comparacao", [
        "compare", "comparar", "comparação", "comparacao", "versus", " vs ",
        "diferença", "diferenca", "cresceu", "caiu", "aumentou", "diminuiu",
        "em relação", "relação a", "ante ", "contra ",
    ]),
    ("evolucao_temporal", [
        "por mês", "por mes", "mensal", "mensalmente",
        "por ano", "anual", "anualmente",
        "evolução", "evolucao", "histórico", "historico",
        "tendência", "tendencia", "ao longo", "mês a mês", "mes a mes",
        "ano a ano", "trimestre", "semestre", "série histórica",
        "progressão", "progressao",
    ]),
    ("media", [
        "média", "media", "médio", "medio", "médias",
        "plr médio", "plr medio", "tempo médio", "tempo medio",
        "produtividade média", "produtividade media",
        "valor médio", "valor medio", "average",
    ]),
    ("totalizacao", [
        "total", "soma", "quanto ", "quantas ", "quantos ",
        "somatório", "somatoria", "acumulado", "no total", "ao todo",
        "contagem", "count(", "sum(",
    ]),
    ("listagem", [
        "liste", "listar", "listar ", "quais são", "quais sao",
        "quais foram", "mostre", "me mostre", "me liste",
        "quero ver", "apresente", "exibir", "mostrar",
    ]),
    ("analise_por_berco", [
        "berço", "berco", "berços", "bercos", "cais", "pier",
    ]),
    ("analise_por_operador", [
        "operador", "operadores", "operadora",
        "transpetro", "tegram", "copi", " vli ", "granel química",
        "granel quimica", "ultracargo", "ziran", "eneva", "copisi", " g5 ",
    ]),
    ("analise_por_navio", [
        "navio", "navios", "embarcação", "embarcacao",
        "embarcações", "vessel", " imo ", "mmsi",
    ]),
    ("analise_por_carga", [
        "carga", "mercadoria", "produto", "soja", "diesel", "milho",
        "gasolina", "fertilizante", "celulose", "contêiner", "container",
        "glp", "cobre", "álcool", "alcool", "etanol", "carvão", "carvao",
        "ferro gusa", "graneleiro",
    ]),
    ("analise_por_cliente", [
        "cliente", "clientes",
    ]),
]

# Questions shorter than this (chars) without keyword matches use LLM
_MIN_LEN_FOR_HEURISTIC = 15


def _heuristic_classify(question: str) -> Dict | None:
    """
    Fast keyword-based classification. Returns a full result dict on confident
    match, or None to signal LLM fallback is required.
    """
    q = " " + question.lower() + " "

    scores: dict[str, int] = {}
    for intent, keywords in _HEURISTIC_MAP:
        count = sum(1 for kw in keywords if kw in q)
        if count:
            scores[intent] = count

    if not scores:
        # No keywords matched — only use LLM if question has enough content
        if len(question.strip()) < _MIN_LEN_FOR_HEURISTIC:
            return None
        # Longer question with no keywords → default to listagem
        return _make_result("listagem", "low", False)

    best = max(scores, key=scores.get)
    confidence = "high" if scores[best] >= 2 else "medium"

    # needs_cross_check: True for aggregation intents, or when totalization
    # keywords appear alongside any entity intent
    is_aggregation = best in ("totalizacao", "media")
    has_total_kw = any(kw in q for kw in ("total", "soma", "quanto ", "quantas ", "quantos ", "média", "media"))
    needs_cross = is_aggregation or (has_total_kw and best not in ("evolucao_temporal", "ranking"))

    return _make_result(best, confidence, needs_cross)


def _make_result(intent: str, confidence: str, needs_cross_check: bool) -> Dict:
    return {
        "intent": intent,
        "confidence": confidence,
        "needs_cross_check": needs_cross_check,
        "reasoning": "heuristic",
        "is_ambiguous": False,
        "ambiguity_confidence": 0.95,
        "follow_up_questions": [],
        "interpretation_note": "",
    }


CLASSIFICATION_SYSTEM = """
Você é um classificador de intenção de perguntas analíticas sobre dados portuários.
Faça as duas tarefas abaixo em uma única resposta JSON.

TAREFA 1 — Classifique a intenção:
- totalizacao: soma, total, quantidade total, quanto no geral
- comparacao: comparar dois períodos, dois itens, versus, diferença entre
- ranking: top N, maior, menor, mais, menos, melhor, pior
- listagem: listar, mostrar, quais são, elencar
- media: média, médio, tempo médio, valor médio
- evolucao_temporal: por mês, por ano, evolução, histórico, tendência
- analise_por_navio: sobre um ou mais navios específicos
- analise_por_carga: sobre tipos de carga ou cargas específicas
- analise_por_berco: sobre berços ou posições específicas
- analise_por_cliente: sobre clientes ou armadores
- analise_por_operador: sobre operadores portuários
- ambigua: pergunta vaga, incompleta ou com múltiplas interpretações

TAREFA 2 — Detecte ambiguidade:
Uma pergunta é ambígua APENAS quando é impossível gerar SQL sem informação faltante.
REGRAS IMPORTANTES:
- Ausência de período de tempo NÃO é ambiguidade — use todo o histórico disponível.
- Ausência de limite (top N) NÃO é ambiguidade — use LIMIT 10 por padrão.
- Só marque is_ambiguous=true se faltar a ENTIDADE principal (ex: "qual a produtividade?" sem dizer de quê).
- Perguntas como "qual a carga mais movimentada no berço X" são CLARAS — não peça clarificação.

Responda APENAS com este JSON:
{
  "intent": "nome_da_intencao",
  "confidence": "high|medium|low",
  "needs_cross_check": true ou false,
  "is_ambiguous": true ou false,
  "ambiguity_confidence": 0.0 a 1.0,
  "follow_up_questions": [],
  "interpretation_note": ""
}

needs_cross_check = true APENAS para: totalizacao, media (somas e médias precisam validação)
needs_cross_check = false para: ranking, listagem, evolucao_temporal e demais (não precisam)
is_ambiguous = true apenas se faltar informação essencial para gerar SQL
ambiguity_confidence = 0.95 se claramente não-ambígua, < 0.60 se ambígua
"""


def question_classifier_tool(question: str) -> Dict:
    """
    Classifica a pergunta do usuário.
    Tenta heurística rápida primeiro; usa LLM apenas para casos ambíguos.
    """
    # Fast path: heuristic covers ~90% of real queries without LLM
    heuristic = _heuristic_classify(question)
    if heuristic and heuristic["confidence"] in ("high", "medium"):
        logger.debug("Classificador: heurística '%s' (conf=%s)", heuristic["intent"], heuristic["confidence"])
        return heuristic

    # Slow path: LLM for low-confidence or very short ambiguous questions
    logger.debug("Classificador: usando LLM (heurística insuficiente)")
    messages = [
        SystemMessage(content=CLASSIFICATION_SYSTEM),
        HumanMessage(content=f"Classifique esta pergunta: {question}"),
    ]

    try:
        raw = invoke_llm(messages)
        json_match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not json_match:
            raise ValueError("Nenhum JSON na resposta do classificador.")

        result = json.loads(json_match.group())

        intent = result.get("intent", "ambigua")
        if intent not in VALID_INTENTS:
            intent = "ambigua"

        return {
            "intent": intent,
            "confidence": result.get("confidence", "medium"),
            "needs_cross_check": bool(result.get("needs_cross_check", False)),
            "reasoning": result.get("reasoning", ""),
            "is_ambiguous": bool(result.get("is_ambiguous", False)),
            "ambiguity_confidence": float(result.get("ambiguity_confidence", 0.95)),
            "follow_up_questions": result.get("follow_up_questions", []),
            "interpretation_note": result.get("interpretation_note", ""),
        }

    except Exception as exc:
        logger.warning("Classificador LLM falhou: %s. Usando heurística de emergência.", exc)
        fallback_intent = _fallback_classify(question)
        return _make_result(fallback_intent, "low", fallback_intent in ("totalizacao", "media"))


def _fallback_classify(question: str) -> str:
    """Classificação mínima por palavras-chave — último recurso."""
    q = question.lower()
    if any(w in q for w in ("top", "maior", "menor", "mais", "ranking", "melhor")):
        return "ranking"
    if any(w in q for w in ("compare", "comparar", "versus", "vs", "diferença")):
        return "comparacao"
    if any(w in q for w in ("média", "médio", "tempo médio", "average")):
        return "media"
    if any(w in q for w in ("por mês", "por ano", "mensal", "anual", "evolução", "histórico")):
        return "evolucao_temporal"
    if any(w in q for w in ("total", "soma", "quanto", "quantas", "quantos")):
        return "totalizacao"
    if any(w in q for w in ("berço", "berco", "pier", "cais")):
        return "analise_por_berco"
    if any(w in q for w in ("operador", "operadora", "transpetro", "tegram", "copi")):
        return "analise_por_operador"
    if any(w in q for w in ("navio", "embarcação", "vessel")):
        return "analise_por_navio"
    if any(w in q for w in ("carga", "produto", "mercadoria", "soja", "diesel")):
        return "analise_por_carga"
    if any(w in q for w in ("cliente", "armador")):
        return "analise_por_cliente"
    if any(w in q for w in ("liste", "listar", "quais", "mostre")):
        return "listagem"
    return "listagem"

"""
Ambiguity Detector Tool

Analisa se uma pergunta tem contexto suficiente para gerar SQL preciso.
Usa pré-check por heurísticas (sem LLM) para perguntas obviamente claras,
e LLM apenas quando a heurística detecta possível ambiguidade.

Níveis de confiança:
  > 0.85  → executa automaticamente
  0.60–0.85 → executa, mas confirma a interpretação
  < 0.60  → pede esclarecimento antes de executar
"""
import json
import logging
import re
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage
from ai_agent.services.gemini_service import invoke_llm

logger = logging.getLogger("ai_agent")

# ─── Vocabulário de ambiguidade / especificidade ──────────────────────────── #

# Palavras vagas que, sozinhas, tornam a pergunta ambígua
_VAGUE_WORDS = frozenset([
    "total", "totais", "dados", "informação", "informações", "resultado",
    "mostre", "mostra", "exiba", "liste",
    "compare", "comparar", "comparação",
    "gráfico", "chart", "visualização",
    "maiores", "menores",
    "análise", "analise", "relatório", "relatorio",
    "o que", "o quanto",
])

# Padrões que indicam contexto suficiente na pergunta
_SPECIFIC_PATTERNS = [
    r"\b(19|20)\d{2}\b",                           # ano (ex: 2025)
    r"\b(jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)\w*\b",  # mês
    r"\bplr\b",
    r"\btonelagem\b",
    r"\batracac\w+\b",
    r"\bdesatracac\w+\b",
    r"\bdwt\b",
    r"\bcomprimento\b",
    r"\bberc[oa]\b",
    r"\bnavio[s]?\b",
    r"\bcarg[oa][s]?\b",
    r"\boperador[es]?\b",
    r"\barmador[es]?\b",
    r"\bpraticagem\b",
    r"\btempo médio\b|\btma\b",
]

# ─── Prompt de detecção ────────────────────────────────────────────────────── #

_AMBIGUITY_PROMPT = """
Você é um analista sênior de dados portuários. Analise se a pergunta abaixo tem contexto suficiente para gerar uma consulta SQL precisa.

SCHEMA DO BANCO (tabelas e colunas):
{schema_summary}

HISTÓRICO DA CONVERSA (últimas mensagens):
{history_summary}

PERGUNTA ATUAL: {question}
INTENÇÃO CLASSIFICADA: {intent}

GATILHOS QUE REDUZEM A CONFIANÇA:
- Falta período de tempo quando a intenção exige (ranking, evolução, total, comparação)
- Múltiplas métricas possíveis sem especificação (PLR? tonelagem? número de atracações?)
- Comparação sem referência ("compare os dados" — comparar o quê com o quê?)
- Ranking sem métrica ("maiores navios" — maior em DWT? comprimento? tonelagem?)
- "Faça um gráfico" sem métrica ou eixo definido
- Pergunta genérica com menos de 4 palavras sem histórico de contexto

NÃO MARQUE COMO AMBÍGUA quando:
- O histórico da conversa já fornece o contexto necessário
- O usuário está claramente respondendo uma pergunta anterior do agente
- A pergunta tem apenas uma interpretação razoável no domínio portuário
- A pergunta contém filtros claros (ano, berço, carga, métrica nomeada)

SOBRE AS PERGUNTAS DE ESCLARECIMENTO:
- Tom: natural, direto, como um analista conversando — NÃO robótico
- Máximo 2 perguntas, as mais críticas
- Curtas e objetivas
- Em português

Responda APENAS com JSON válido (sem markdown):
{{
  "is_ambiguous": true ou false,
  "confidence": 0.0 a 1.0,
  "missing_information": ["período", "métrica"] ou [],
  "possible_interpretations": ["total de PLR", "total de tonelagem"] ou [],
  "follow_up_questions": ["Você quer analisar qual período?", "PLR ou tonelagem?"] ou [],
  "confirmed_interpretation": "o que o agente entende que foi pedido",
  "interpretation_note": "frase curta para confirmar com usuário (se 0.60 <= confidence <= 0.85, senão vazio)"
}}
"""


# ─── Heurística rápida (sem LLM) ─────────────────────────────────────────── #

def _has_specific_context(question: str) -> bool:
    """Verifica se a pergunta contém algum qualificador específico."""
    q = question.lower()
    return any(re.search(p, q, re.IGNORECASE) for p in _SPECIFIC_PATTERNS)


def _has_vague_words(question: str) -> bool:
    """Verifica se a pergunta contém palavras tipicamente vagas."""
    words = set(question.lower().split())
    return bool(words & _VAGUE_WORDS)


def _is_ambiguous_plr_total(question: str) -> bool:
    q = question.lower()
    if "plr" not in q:
        return False
    total_terms = ("total", "totais", "soma", "somar", "somado", "acumulado")
    return any(term in q for term in total_terms)


def should_check_ambiguity(
    question: str,
    intent: str,
    has_history: bool,
    was_answering_clarification: bool,
) -> bool:
    """
    Heurística rápida: decide se vale rodar o detector LLM completo.
    Retorna False para perguntas claramente específicas → pula LLM.
    """
    # Se o usuário está respondendo uma clarificação → não checar (evita loop)
    if was_answering_clarification:
        return False

    # Já marcado como ambíguo pelo classificador
    if intent in ("ambigua", "desconhecida"):
        return True

    # Pergunta muito curta sem contexto conversacional
    word_count = len(question.split())
    if word_count <= 3 and not has_history:
        return True

    # Tem palavras vagas MAS também tem contexto específico → provavelmente OK
    if _has_vague_words(question) and not _has_specific_context(question):
        return True

    return False


# ─── Tool principal ───────────────────────────────────────────────────────── #

def ambiguity_detector_tool(
    question: str,
    intent: str,
    schema_text: str,
    history: List[Dict],
    was_answering_clarification: bool = False,
) -> Dict[str, Any]:
    """
    Detecta ambiguidade e informações ausentes na pergunta.

    Returns:
        {
            "is_ambiguous": bool,
            "confidence": float,
            "missing_information": list[str],
            "possible_interpretations": list[str],
            "follow_up_questions": list[str],
            "confirmed_interpretation": str,
            "interpretation_note": str,
            "checked_by_llm": bool,
        }
    """
    has_history = len(history) > 0

    if _is_ambiguous_plr_total(question) and not was_answering_clarification:
        return {
            "is_ambiguous": True,
            "confidence": 0.45,
            "missing_information": ["metrica de PLR"],
            "possible_interpretations": [
                "media mensal de PLR",
                "PLR ponderado por mes",
                "tonelagem total mensal",
            ],
            "follow_up_questions": [
                "PLR e uma taxa. Voce quer media mensal, PLR ponderado por mes ou tonelagem total?"
            ],
            "confirmed_interpretation": question,
            "interpretation_note": "",
            "checked_by_llm": False,
        }

    # ── Pré-check: pular LLM para perguntas claramente específicas ────────
    if not should_check_ambiguity(question, intent, has_history, was_answering_clarification):
        logger.debug("Ambiguity: pré-check passou, LLM dispensado.")
        return _clear_result(question)

    # ── Preparar contexto para o LLM ─────────────────────────────────────
    history_summary = _format_history(history[-6:])

    # Schema compacto: só tabelas e colunas principais
    schema_lines = schema_text.split("\n")
    schema_summary = "\n".join(
        line for line in schema_lines
        if line.startswith("TABELA") or (line.strip().startswith("-") and len(line) < 80)
    )[:1000]

    prompt = _AMBIGUITY_PROMPT.format(
        schema_summary=schema_summary or "Schema não disponível.",
        history_summary=history_summary,
        question=question,
        intent=intent,
    )

    try:
        raw = invoke_llm([HumanMessage(content=prompt)])
        json_match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not json_match:
            raise ValueError("Sem JSON na resposta do detector.")

        data = json.loads(json_match.group())
        confidence = float(data.get("confidence", 0.9))
        is_ambiguous = bool(data.get("is_ambiguous", False))

        logger.info(
            "Ambiguity LLM: is_ambiguous=%s confidence=%.2f missing=%s",
            is_ambiguous, confidence, data.get("missing_information", []),
        )

        return {
            "is_ambiguous": is_ambiguous,
            "confidence": confidence,
            "missing_information": data.get("missing_information", []),
            "possible_interpretations": data.get("possible_interpretations", []),
            "follow_up_questions": data.get("follow_up_questions", []),
            "confirmed_interpretation": data.get("confirmed_interpretation", question),
            "interpretation_note": data.get("interpretation_note", ""),
            "checked_by_llm": True,
        }

    except Exception as exc:
        logger.warning("Ambiguity detector falhou (%s) — assumindo não ambíguo.", exc)
        return _clear_result(question)


def _clear_result(question: str) -> Dict[str, Any]:
    return {
        "is_ambiguous": False,
        "confidence": 0.92,
        "missing_information": [],
        "possible_interpretations": [],
        "follow_up_questions": [],
        "confirmed_interpretation": question,
        "interpretation_note": "",
        "checked_by_llm": False,
    }


def _format_history(history: List[Dict]) -> str:
    if not history:
        return "Sem histórico."
    lines = []
    for msg in history:
        role = "Usuário" if msg.get("role") == "user" else "Agente"
        text = str(msg.get("text", ""))[:200]
        lines.append(f"{role}: {text}")
    return "\n".join(lines)

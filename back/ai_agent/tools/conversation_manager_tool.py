"""
Conversation Manager Tool

Gerencia o fluxo conversacional do agente:
- Detecta se o agente estava aguardando uma resposta do usuário
- Determina o estado atual da conversa
- Formata respostas de esclarecimento de forma natural
- Previne loops de clarificação

Estados conversacionais:
  ready_to_query          → pode gerar SQL
  waiting_for_period      → aguardando período/ano/mês
  waiting_for_metric      → aguardando qual métrica (PLR, tonelagem, etc.)
  waiting_for_grouping    → aguardando agrupamento (berço, carga, navio)
  waiting_for_confirmation → aguardando confirmação da interpretação
  clarifying              → aguardando esclarecimento genérico
"""
import logging
from typing import Dict, List, Optional

logger = logging.getLogger("ai_agent")

# ─── Estados ──────────────────────────────────────────────────────────────── #

STATE_READY = "ready_to_query"
STATE_WAITING_PERIOD = "waiting_for_period"
STATE_WAITING_METRIC = "waiting_for_metric"
STATE_WAITING_GROUPING = "waiting_for_grouping"
STATE_WAITING_CONFIRMATION = "waiting_for_confirmation"
STATE_CLARIFYING = "clarifying"

# Indicadores de que o agente fez uma pergunta de esclarecimento
_CLARIFICATION_INDICATORS = [
    "qual período", "que período", "deseja analisar", "qual ano", "que ano",
    "qual mês", "que mês", "de qual", "para qual",
    "qual métrica", "que métrica", "plr ou", "ou tonelagem",
    "qual berço", "que berço", "qual navio", "que navio",
    "deseja comparar", "o que deseja", "quer comparar",
    "poderia especificar", "pode especificar", "poderia informar",
    "certo?", "correto?", "confirma?", "isso está certo",
    "você se refere", "vou considerar",
    "preciso de mais", "preciso saber", "me diga",
    "qual seria", "você quer",
]

_PERIOD_INDICATORS = ["período", "ano", "mês", "data", "quando", "trimestre", "semana"]
_METRIC_INDICATORS = ["métrica", "plr", "tonelagem", "atracação", "o que", "qual dado", "operação"]
_GROUPING_INDICATORS = ["berço", "navio", "carga", "agrupar", "agrupamento", "detalhar", "por qual"]
_CONFIRMATION_INDICATORS = ["certo?", "correto?", "confirma?", "isso está", "vou considerar"]


def detect_conversation_state(history: List[Dict]) -> Dict:
    """
    Analisa o histórico para determinar o estado atual da conversa.

    Returns:
        {
            "state": str,
            "was_clarifying": bool,   — True se o agente fez uma pergunta de esclarecimento
            "pending_user_question": str | None,  — pergunta original do usuário pendente
        }
    """
    if not history:
        return {"state": STATE_READY, "was_clarifying": False, "pending_user_question": None}

    # Última mensagem do agente
    last_agent = next(
        (m for m in reversed(history) if m.get("role") == "assistant"), None
    )
    if not last_agent:
        return {"state": STATE_READY, "was_clarifying": False, "pending_user_question": None}

    last_text = str(last_agent.get("text", "")).lower()
    was_clarifying = any(ind in last_text for ind in _CLARIFICATION_INDICATORS)

    if not was_clarifying:
        return {"state": STATE_READY, "was_clarifying": False, "pending_user_question": None}

    # Determinar o tipo de esclarecimento
    if any(kw in last_text for kw in _PERIOD_INDICATORS):
        state = STATE_WAITING_PERIOD
    elif any(kw in last_text for kw in _METRIC_INDICATORS):
        state = STATE_WAITING_METRIC
    elif any(kw in last_text for kw in _GROUPING_INDICATORS):
        state = STATE_WAITING_GROUPING
    elif any(kw in last_text for kw in _CONFIRMATION_INDICATORS):
        state = STATE_WAITING_CONFIRMATION
    else:
        state = STATE_CLARIFYING

    # Pergunta original do usuário que ficou pendente (penúltima msg do usuário)
    user_msgs = [m for m in history if m.get("role") == "user"]
    pending = user_msgs[-2].get("text", "") if len(user_msgs) >= 2 else None

    return {
        "state": state,
        "was_clarifying": True,
        "pending_user_question": pending,
    }


def build_clarification_response(
    follow_up_questions: List[str],
    possible_interpretations: List[str] = None,
) -> str:
    """
    Formata uma resposta de esclarecimento natural e profissional.
    Evita linguagem robótica.
    """
    if not follow_up_questions:
        return "Poderia dar mais detalhes? Quero garantir que a análise seja precisa."

    if len(follow_up_questions) == 1:
        return follow_up_questions[0]

    # Duas perguntas: apresenta de forma natural
    q1, q2 = follow_up_questions[0], follow_up_questions[1]
    return f"{q1}\n\nTambém: {q2}"


def build_interpretation_prefix(interpretation_note: str) -> str:
    """
    Retorna prefixo para a resposta quando confidence está em 0.60-0.85.
    O agente confirma sua interpretação antes de apresentar os dados.
    """
    if not interpretation_note:
        return ""
    return f"*{interpretation_note}*\n\n"

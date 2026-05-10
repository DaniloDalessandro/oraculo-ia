"""
Memory Service — Memória Conversacional

Resolve perguntas de acompanhamento ("follow-up") usando o histórico
da conversa para que o usuário não precise repetir o contexto.

Exemplo:
  Histórico: "Qual foi o PLR do berço 105 em 2025?"
  Nova pergunta: "E em 2024?"
  Resolvida: "Qual foi o PLR do berço 105 em 2024?"
"""
import logging
import re
from typing import Dict, List, Optional

logger = logging.getLogger("ai_agent")

# Palavras que indicam pergunta de acompanhamento
_FOLLOWUP_STARTERS = (
    "e ", "e em", "e no", "e na", "e o", "e a",
    "mas ", "porém", "agora ", "também",
    "esse ", "essa ", "esses ", "essas ",
    "mesmo ", "mesma ", "esse mesmo", "essa mesma",
    "qual era", "e qual", "e quanto",
    "compare ", "compara ",
)

_SHORT_THRESHOLD = 45  # caracteres — perguntas curtas provavelmente são follow-ups


def is_followup(question: str) -> bool:
    """Heurística rápida: determina se a pergunta é provavelmente um follow-up."""
    q = question.strip().lower()
    if len(q) < _SHORT_THRESHOLD:
        return True
    return any(q.startswith(s) for s in _FOLLOWUP_STARTERS)


def resolve_with_context(
    question: str,
    history: List[Dict],
) -> str:
    """
    Se a pergunta for um follow-up, usa o LLM para reescrevê-la de forma
    completa e autocontida com base no histórico.

    Args:
        question: Pergunta atual do usuário.
        history: Lista de {role: "user"|"assistant", text: str}.

    Returns:
        Pergunta resolvida (ou a original se não for follow-up / LLM falhar).
    """
    if not history or not is_followup(question):
        return question

    # Usa apenas as últimas 3 trocas (6 mensagens) para manter custo baixo
    recent = history[-6:]
    history_text = "\n".join(
        f"{'Usuário' if h['role'] == 'user' else 'Assistente'}: {h['text']}"
        for h in recent
    )

    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        from ai_agent.services.gemini_service import invoke_llm

        messages = [
            SystemMessage(content=(
                "Você recebe o histórico de uma conversa analítica sobre dados portuários "
                "e uma nova pergunta que pode ser um acompanhamento.\n"
                "Sua tarefa: reescrever a nova pergunta de forma COMPLETA e AUTOCONTIDA, "
                "incorporando o contexto do histórico (berço, navio, carga, período, métrica).\n"
                "Responda SOMENTE com a pergunta reescrita. Sem explicações."
            )),
            HumanMessage(content=(
                f"Histórico da conversa:\n{history_text}\n\n"
                f"Nova pergunta: {question}\n\n"
                f"Pergunta reescrita de forma completa:"
            )),
        ]

        resolved = invoke_llm(messages).strip()
        if resolved and len(resolved) > 5:
            logger.info(
                "Memory: follow-up resolvido: '%s' → '%s'",
                question[:60], resolved[:80],
            )
            return resolved
    except Exception as exc:
        logger.warning("Memory: falha ao resolver follow-up: %s", exc)

    return question


def extract_context_entities(history: List[Dict]) -> Dict:
    """
    Extrai entidades mencionadas no histórico para injetar no contexto do LLM.
    Usa regex simples — sem LLM.

    Returns:
        {"bercos": [...], "navios": [...], "periodos": [...], "metricas": [...]}
    """
    all_text = " ".join(h.get("text", "") for h in history).lower()

    # Berços (números de 1 a 3 dígitos após "berço")
    bercos = re.findall(r"ber[çc]o\s+(\d{1,3})", all_text)

    # Anos mencionados
    periodos = re.findall(r"\b(20\d{2})\b", all_text)

    # Métricas comuns
    metricas = []
    for m in ("plr", "tonelagem", "dwt", "operação", "atracação", "desatracação"):
        if m in all_text:
            metricas.append(m)

    return {
        "bercos": list(set(bercos)),
        "periodos": list(set(periodos)),
        "metricas": list(set(metricas)),
    }


def build_context_hint(history: List[Dict]) -> str:
    """
    Monta um resumo do contexto conversacional para incluir no prompt do LLM.
    """
    if not history:
        return ""

    entities = extract_context_entities(history)
    lines = []

    if entities["bercos"]:
        lines.append(f"Berços mencionados na conversa: {', '.join(entities['bercos'])}")
    if entities["periodos"]:
        lines.append(f"Períodos mencionados: {', '.join(sorted(set(entities['periodos'])))}")
    if entities["metricas"]:
        lines.append(f"Métricas discutidas: {', '.join(entities['metricas'])}")

    if not lines:
        return ""

    return "CONTEXTO DA CONVERSA ATUAL:\n" + "\n".join(lines)

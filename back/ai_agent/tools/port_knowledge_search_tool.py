"""
Port Knowledge Search Tool

Busca conhecimento portuário relevante nas três tabelas:
- PortKnowledgeBase  → regras, procedimentos, conceitos
- PortGlossary       → termos técnicos
- PortBusinessRule   → regras de negócio operacionais

Usa scoring por sobreposição de palavras-chave (sem LLM, sem vetor).
Rápido e determinístico.
"""
import logging
import re
from typing import Any, Dict, List

logger = logging.getLogger("ai_agent")

# Stopwords em português a ignorar no scoring
_STOPWORDS = frozenset([
    "de", "da", "do", "das", "dos", "em", "no", "na", "nos", "nas",
    "por", "para", "com", "que", "qual", "quais", "como", "quando",
    "um", "uma", "uns", "umas", "o", "a", "os", "as", "e", "ou",
    "se", "já", "foi", "são", "está", "ser", "ter", "teve",
    "mais", "menos", "muito", "pouco", "todo", "toda",
])

MAX_KB_RESULTS = 4
MAX_GLOSSARY_RESULTS = 5
MAX_RULE_RESULTS = 3


def _keywords(text: str) -> set:
    words = re.findall(r'\b[a-záéíóúâêîôûãõçàü]{3,}\b', text.lower())
    return {w for w in words if w not in _STOPWORDS}


def _score(entry_text: str, question_kw: set) -> int:
    entry_kw = _keywords(entry_text)
    return len(question_kw & entry_kw)


# ─── Busca na PortKnowledgeBase ──────────────────────────────────────────── #

def search_knowledge_base(question: str, max_results: int = MAX_KB_RESULTS) -> List[Dict]:
    """
    Retorna entradas relevantes da base de conhecimento portuário.
    """
    try:
        from ai_agent.models import PortKnowledgeBase

        entries = list(PortKnowledgeBase.objects.filter(is_active=True).order_by("priority"))
        if not entries:
            return []

        q_kw = _keywords(question)
        scored = [
            (e, _score(f"{e.title} {e.content}", q_kw))
            for e in entries
        ]
        scored.sort(key=lambda x: (-x[1], x[0].priority))

        return [
            {
                "id": e.id,
                "title": e.title,
                "category": e.get_category_display(),
                "content": e.content,
                "source_type": e.source_type,
                "priority": e.priority,
                "score": score,
            }
            for e, score in scored[:max_results]
            if score > 0
        ]
    except Exception as exc:
        logger.warning("port_knowledge_search: KB falhou: %s", exc)
        return []


# ─── Busca no PortGlossary ────────────────────────────────────────────────── #

def search_glossary(question: str, max_results: int = MAX_GLOSSARY_RESULTS) -> List[Dict]:
    """
    Retorna termos do glossário mencionados na pergunta.
    """
    try:
        from ai_agent.models import PortGlossary

        terms = list(PortGlossary.objects.filter(is_active=True))
        if not terms:
            return []

        q_lower = question.lower()
        matched = []
        for t in terms:
            # Considera match se o termo aparece diretamente na pergunta
            if t.term.lower() in q_lower or t.term.lower().replace("-", " ") in q_lower:
                matched.append(t)
                continue
            # Ou se há sobreposição de keywords
            if _score(f"{t.term} {t.definition}", _keywords(question)) >= 2:
                matched.append(t)

        return [
            {
                "term": t.term,
                "definition": t.definition,
                "example": t.example,
            }
            for t in matched[:max_results]
        ]
    except Exception as exc:
        logger.warning("port_knowledge_search: Glossary falhou: %s", exc)
        return []


# ─── Busca em PortBusinessRule ────────────────────────────────────────────── #

def search_business_rules(question: str, max_results: int = MAX_RULE_RESULTS) -> List[Dict]:
    """
    Retorna regras de negócio relevantes para a pergunta.
    """
    try:
        from ai_agent.models import PortBusinessRule

        rules = list(PortBusinessRule.objects.filter(is_active=True).order_by("priority"))
        if not rules:
            return []

        q_kw = _keywords(question)
        scored = [
            (r, _score(f"{r.rule_name} {r.condition} {r.action} {r.explanation}", q_kw))
            for r in rules
        ]
        scored.sort(key=lambda x: (-x[1], x[0].priority))

        return [
            {
                "rule_name": r.rule_name,
                "rule_type": r.get_rule_type_display(),
                "condition": r.condition,
                "action": r.action,
                "explanation": r.explanation,
                "score": score,
            }
            for r, score in scored[:max_results]
            if score > 0
        ]
    except Exception as exc:
        logger.warning("port_knowledge_search: Rules falhou: %s", exc)
        return []


# ─── Unified search ──────────────────────────────────────────────────────── #

def port_knowledge_search_tool(question: str) -> Dict[str, Any]:
    """
    Busca unificada nas três fontes de conhecimento portuário.

    Returns:
        {
            "knowledge": [...],
            "glossary": [...],
            "rules": [...],
            "has_context": bool,
        }
    """
    knowledge = search_knowledge_base(question)
    glossary = search_glossary(question)
    rules = search_business_rules(question)

    has_context = bool(knowledge or glossary or rules)
    logger.info(
        "Port knowledge: %d KB | %d glossary | %d rules para '%s'",
        len(knowledge), len(glossary), len(rules), question[:60],
    )

    return {
        "knowledge": knowledge,
        "glossary": glossary,
        "rules": rules,
        "has_context": has_context,
    }

"""
Port Learning Tool

Detecta quando o usuário quer ensinar uma nova regra ao agente e
a salva na PortKnowledgeBase com source_type='conversa'.

Gatilhos de salvamento (palavras-chave):
  "lembre que", "salve essa regra", "cadastre essa regra",
  "isso é uma regra", "essa é uma regra", "salvar:", "regra:",
  "aprenda que", "anote que"

O LLM extrai título, categoria e conteúdo da instrução do usuário.
"""
import json
import logging
import re
from typing import Dict, Optional

from langchain_core.messages import HumanMessage
from ai_agent.services.gemini_service import invoke_llm

logger = logging.getLogger("ai_agent")

# Gatilhos que indicam intenção de salvar conhecimento
_SAVE_TRIGGERS = [
    r"\blembre(?:\s+que)?\b",
    r"\bsalve(?:\s+essa?\s+regra)?\b",
    r"\bcadastre(?:\s+essa?\s+regra)?\b",
    r"\bessa?\s+[eé]\s+uma\s+regra\b",
    r"\baprenda(?:\s+que)?\b",
    r"\banote(?:\s+que)?\b",
    r"\bsalvar\s*:",
    r"\bregra\s*:",
]

_EXTRACT_PROMPT = """
Você recebe uma instrução do usuário para salvar uma regra ou conhecimento portuário.
Extraia as informações e retorne APENAS JSON válido.

Instrução do usuário: {instruction}

Categorias disponíveis:
- regra_de_atracacao: regras sobre atracação e desatracação
- conceito_operacional: conceitos e definições operacionais
- regra_de_berco: preferências e restrições de berço
- regra_de_carga: regras sobre tipos de carga
- prioridade: prioridades operacionais
- excecao: exceções a regras gerais
- procedimento: procedimentos e processos
- indicador: métricas, KPIs, fórmulas
- aprendido: conhecimento geral aprendido em conversa

Responda APENAS com JSON:
{{
  "title": "título curto (máx 80 chars)",
  "category": "categoria da lista acima",
  "content": "conteúdo completo da regra/conhecimento, como uma instrução clara",
  "priority": 3
}}
"""


def is_save_intent(question: str) -> bool:
    """
    Retorna True se a mensagem do usuário contém intenção de salvar conhecimento.
    Verificação por regex, sem LLM.
    """
    q = question.lower()
    return any(re.search(pattern, q, re.IGNORECASE) for pattern in _SAVE_TRIGGERS)


def port_learning_tool(instruction: str, user=None) -> Dict:
    """
    Extrai e salva uma regra/conhecimento ensinado pelo usuário.

    Args:
        instruction: Texto completo da instrução do usuário.
        user: Usuário Django (opcional, para log).

    Returns:
        {"saved": bool, "title": str, "category": str, "message": str}
    """
    prompt = _EXTRACT_PROMPT.format(instruction=instruction)

    try:
        raw = invoke_llm([HumanMessage(content=prompt)])
        json_match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not json_match:
            raise ValueError("Sem JSON na extração.")

        data = json.loads(json_match.group())
        title = str(data.get("title", ""))[:200]
        category = str(data.get("category", "aprendido"))
        content = str(data.get("content", instruction))
        priority = int(data.get("priority", 3))

        if not title or not content:
            raise ValueError("Título ou conteúdo vazios.")

        from ai_agent.models import PortKnowledgeBase
        entry = PortKnowledgeBase.objects.create(
            title=title,
            category=category,
            content=content,
            source_type="conversa",
            source_name=f"usuário: {user}" if user else "conversa",
            priority=max(1, min(10, priority)),
        )

        logger.info(
            "Port learning: regra salva #%d — '%s' [%s]",
            entry.id, title, category,
        )

        return {
            "saved": True,
            "title": title,
            "category": entry.get_category_display(),
            "message": (
                f"Regra salva na base de conhecimento como **{entry.get_category_display()}**.\n"
                f"Título: _{title}_\n\n"
                "Vou consultar esse conhecimento em consultas futuras relacionadas."
            ),
        }

    except Exception as exc:
        logger.warning("port_learning_tool falhou: %s", exc)

        # Fallback: salva o texto bruto sem estruturação
        try:
            from ai_agent.models import PortKnowledgeBase
            cleaned = re.sub(
                r"(lembre(?:\s+que)?|salve|cadastre|aprenda(?:\s+que)?|anote(?:\s+que)?)",
                "", instruction, flags=re.IGNORECASE
            ).strip(" :.,")

            PortKnowledgeBase.objects.create(
                title=cleaned[:80],
                category="aprendido",
                content=cleaned,
                source_type="conversa",
                source_name="conversa (fallback)",
                priority=3,
            )
            return {
                "saved": True,
                "title": cleaned[:60],
                "category": "Aprendido em Conversa",
                "message": "Conhecimento salvo na base. Vou usar esse contexto em consultas futuras.",
            }
        except Exception:
            return {
                "saved": False,
                "title": "",
                "category": "",
                "message": "Não foi possível salvar o conhecimento. Tente novamente.",
            }

"""
Port Context Builder Tool

Constrói o bloco de contexto portuário para injetar no prompt do LLM.
Combina base de conhecimento + glossário + regras de negócio num texto
compacto, estruturado e acionável.

Formato da saída (injetado no prompt SQL e na resposta):

  === CONTEXTO PORTUÁRIO ===
  REGRAS E PROCEDIMENTOS:
  [prioridade] Preferência TEGRAM: ...
  GLOSSÁRIO RELEVANTE:
  PLR — Prancha Líquida Real: ...
  REGRAS DE NEGÓCIO:
  [preferencia] Regra LOA: SE ... ENTÃO ...
"""
import logging
from typing import Any, Dict

from ai_agent.tools.port_knowledge_search_tool import port_knowledge_search_tool

logger = logging.getLogger("ai_agent")


def port_context_builder_tool(question: str) -> str:
    """
    Busca e formata o contexto portuário relevante para a pergunta.

    Returns:
        String formatada para inserção no prompt, ou string vazia se não houver contexto.
    """
    try:
        result = port_knowledge_search_tool(question)

        if not result["has_context"]:
            return ""

        lines = ["=== CONTEXTO PORTUÁRIO RELEVANTE ===\n"]

        # ── Base de conhecimento ────────────────────────────────────────
        if result["knowledge"]:
            lines.append("REGRAS E PROCEDIMENTOS OPERACIONAIS:")
            for entry in result["knowledge"]:
                source_tag = " [aprendido em conversa]" if entry["source_type"] == "conversa" else ""
                lines.append(f"  [{entry['category']}] {entry['title']}{source_tag}:")
                lines.append(f"  {entry['content']}")
            lines.append("")

        # ── Regras de negócio ────────────────────────────────────────────
        if result["rules"]:
            lines.append("REGRAS DE NEGÓCIO:")
            for rule in result["rules"]:
                lines.append(f"  [{rule['rule_type']}] {rule['rule_name']}:")
                lines.append(f"  SE: {rule['condition']}")
                lines.append(f"  ENTÃO: {rule['action']}")
                if rule["explanation"]:
                    lines.append(f"  OBS: {rule['explanation']}")
            lines.append("")

        # ── Glossário ────────────────────────────────────────────────────
        if result["glossary"]:
            lines.append("GLOSSÁRIO:")
            for term in result["glossary"]:
                ex = f" (ex: {term['example']})" if term["example"] else ""
                lines.append(f"  {term['term']}: {term['definition']}{ex}")
            lines.append("")

        lines.append(
            "IMPORTANTE: Use as regras acima ao gerar SQL e ao formular a resposta. "
            "Cite a fonte quando aplicar uma regra cadastrada."
        )

        return "\n".join(lines)

    except Exception as exc:
        logger.warning("port_context_builder falhou: %s", exc)
        return ""

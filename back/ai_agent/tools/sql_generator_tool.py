"""
SQL Generator Tool

Gera SQL PostgreSQL a partir da pergunta e do schema do banco.
"""
import logging
import re

from langchain_core.messages import HumanMessage, SystemMessage

from ai_agent.services.gemini_service import invoke_llm
from ai_agent.prompts.sql_prompt import SQL_GENERATION_PROMPT, SQL_CROSS_CHECK_PROMPT

logger = logging.getLogger("ai_agent")


def _clean_sql_output(raw: str) -> str:
    """
    Extrai o SQL puro da resposta do modelo.
    Lida com: blocos markdown, tags <think>, texto de raciocínio antes do SELECT.
    """
    # Remover tags de thinking (Qwen3 e similares)
    raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL | re.IGNORECASE)

    # Extrair SQL de dentro de blocos ```sql ... ``` ou ``` ... ```
    block = re.search(r"```(?:sql)?\s*(.*?)```", raw, flags=re.DOTALL | re.IGNORECASE)
    if block:
        raw = block.group(1)
    else:
        # Sem bloco markdown — encontrar o primeiro SELECT ou WITH e pegar dali em diante
        match = re.search(r"\b(SELECT|WITH)\b", raw, flags=re.IGNORECASE)
        if match:
            raw = raw[match.start():]

    # Remover linhas em branco do início/fim
    lines = [line for line in raw.strip().splitlines() if line.strip()]
    return "\n".join(lines)


def sql_generator_tool(
    question: str,
    schema_text: str,
    intent: str,
    samples_text: str = "",
    context_hint: str = "",
    learning_hint: str = "",
    preferred_date_field: str = "desatracacao",
    preferred_limit: int = 50,
    port_context: str = "",
) -> str:
    """
    Gera uma consulta SQL SELECT para responder a pergunta.

    Args:
        question: Pergunta do usuário.
        schema_text: Resumo textual do schema.
        intent: Intenção classificada.
        samples_text: Amostras de valores reais (opcional).

    Returns:
        String com o SQL gerado.
    """
    prompt = SQL_GENERATION_PROMPT.format(
        schema=schema_text,
        samples=samples_text or "Amostras não disponíveis.",
        port_context=port_context or "",
        intent=intent,
        question=question,
        context_hint=context_hint,
        learning_hint=learning_hint,
        preferred_date_field=preferred_date_field,
        preferred_limit=preferred_limit,
    )

    messages = [
        HumanMessage(content=prompt),
    ]

    try:
        raw = invoke_llm(messages)
        sql = _clean_sql_output(raw)

        if not sql.strip().upper().startswith(("SELECT", "WITH")):
            logger.warning(
                "SQL gerado não começa com SELECT/WITH: %s", sql[:100]
            )
            raise ValueError(f"SQL gerado inválido: não começa com SELECT ou WITH.")

        logger.info("SQL gerado com sucesso: %d chars.", len(sql))
        return sql

    except Exception as exc:
        logger.error("Falha na geração de SQL: %s", exc, exc_info=True)
        raise RuntimeError(f"Não foi possível gerar o SQL para a pergunta: {exc}") from exc


def sql_cross_check_generator_tool(
    question: str,
    schema_text: str,
    main_sql: str,
    main_result: str,
) -> str:
    """
    Gera uma segunda consulta SQL para validação cruzada do resultado principal.

    Returns:
        String com o SQL de verificação.
    """
    prompt = SQL_CROSS_CHECK_PROMPT.format(
        schema=schema_text,
        question=question,
        main_sql=main_sql,
        main_result=main_result[:1000],
    )

    messages = [HumanMessage(content=prompt)]

    try:
        raw = invoke_llm(messages)
        sql = _clean_sql_output(raw)

        if not sql.strip().upper().startswith(("SELECT", "WITH")):
            raise ValueError("SQL de verificação não começa com SELECT.")

        logger.info("SQL de verificação gerado: %d chars.", len(sql))
        return sql

    except Exception as exc:
        logger.warning("Falha ao gerar SQL de verificação: %s", exc)
        return ""

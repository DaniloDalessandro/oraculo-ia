"""Agente de IA usando Groq + Tool Use."""

import json
from groq import AsyncGroq
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.services.sql_executor import (
    SQLExecutionError,
    execute_safe,
    format_result_for_prompt,
    get_schema_and_tables,
)
from app.services.sql_validator import SQLValidationError, validate_and_prepare

_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "executar_sql",
            "description": (
                "Executa uma consulta SQL SELECT no banco de dados PostgreSQL da empresa. "
                "Use para buscar dados de qualquer tabela disponível. "
                "Só aceita SELECT — nunca DELETE, UPDATE, INSERT ou DROP."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": (
                            "Query SQL SELECT válida para PostgreSQL. "
                            f"Limite padrão de {settings.AI_SQL_ROW_LIMIT} linhas. "
                            "Use funções nativas do PostgreSQL para datas (CURRENT_DATE, DATE_TRUNC, etc)."
                        ),
                    }
                },
                "required": ["sql"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "obter_schema",
            "description": (
                "Retorna a estrutura completa e atualizada de todas as tabelas disponíveis "
                "no banco de dados, incluindo colunas, tipos, PKs e FKs. "
                "Use sempre que precisar confirmar nomes de colunas ou tabelas antes de gerar SQL."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
]

async def run_agent(
    db: AsyncSession,
    question: str,
    history: list[dict],
    nome_assistente: str = "Assistente",
    nivel_detalhe: str = "normal",
) -> tuple[str, str | None]:
    """
    Executa o loop do agente Groq com tool use.

    Returns:
        (resposta_final, ultimo_sql_executado_ou_None)
    """
    client = AsyncGroq(api_key=settings.GROQ_API_KEY)

    try:
        schema_str, allowed_tables = await get_schema_and_tables(db)
    except Exception:
        schema_str = "(schema indisponível — use a tool obter_schema para tentar novamente)"
        allowed_tables = None

    system_prompt = f"""Você é {nome_assistente}, um assistente corporativo inteligente acessado via WhatsApp.

Você tem acesso a ferramentas para consultar o banco de dados PostgreSQL da empresa.
Use as ferramentas sempre que a pergunta envolver dados.

Nível de detalhe das respostas: {nivel_detalhe}
  - resumido:  máximo 2 linhas, só o essencial
  - normal:    resposta completa e objetiva com os dados relevantes
  - detalhado: resposta completa com análise e insights adicionais

Schema atual do banco:
{schema_str}

Regras obrigatórias:
- Responda SEMPRE em português brasileiro
- Use formatação WhatsApp: *negrito*, _itálico_, listas com •
- Seja preciso com números, porcentagens e datas
- Nunca invente dados além do que as ferramentas retornaram
- Para saudações ou perguntas gerais sobre o sistema, responda diretamente sem usar ferramentas
- Se uma consulta retornar erro, tente reformular o SQL antes de desistir
- Use obter_schema se precisar confirmar colunas exatas de uma tabela"""

    messages: list[dict] = [{"role": "system", "content": system_prompt}]
    messages.extend(history)
    messages.append({"role": "user", "content": question})

    last_sql: str | None = None
    max_iterations = 8  # evita loop infinito

    for _ in range(max_iterations):
        response = await client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=messages,
            tools=_TOOLS,
            tool_choice="auto",
            max_tokens=settings.AI_MAX_TOKENS,
            temperature=settings.AI_TEMPERATURE,
        )

        choice = response.choices[0]
        msg = choice.message

        msg_dict: dict = {"role": "assistant", "content": msg.content or ""}
        if msg.tool_calls:
            msg_dict["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in msg.tool_calls
            ]
        messages.append(msg_dict)

        if not msg.tool_calls or choice.finish_reason == "stop":
            return (msg.content or "Não consegui processar sua pergunta."), last_sql

        for tc in msg.tool_calls:
            tool_result = await _executar_ferramenta(
                tc.function.name, tc.function.arguments, db, schema_str, allowed_tables
            )

            if tc.function.name == "executar_sql":
                try:
                    last_sql = json.loads(tc.function.arguments).get("sql")
                except Exception:
                    pass

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": tool_result,
            })

    return "Não consegui processar sua pergunta após várias tentativas.", last_sql


async def _executar_ferramenta(
    nome: str,
    arguments_json: str,
    db: AsyncSession,
    schema_str: str,
    allowed_tables: set[str] | None,
) -> str:
    """Despacha a chamada de ferramenta e retorna o resultado como string."""
    try:
        args = json.loads(arguments_json)
    except Exception:
        args = {}

    if nome == "obter_schema":
        try:
            fresh_schema, _ = await get_schema_and_tables(db)
            return fresh_schema
        except Exception:
            return schema_str

    if nome == "executar_sql":
        sql = args.get("sql", "").strip()
        if not sql:
            return "Erro: SQL vazio."
        try:
            validated = validate_and_prepare(sql, allowed_tables)
            result = await execute_safe(db, validated)
            return format_result_for_prompt(result)
        except SQLValidationError as e:
            return f"Erro de validação: {e}. Reescreva a query usando apenas SELECT e as tabelas do schema."
        except SQLExecutionError as e:
            return f"Erro ao executar: {e}. Verifique a sintaxe e tente novamente."

    return f"Ferramenta desconhecida: {nome}"

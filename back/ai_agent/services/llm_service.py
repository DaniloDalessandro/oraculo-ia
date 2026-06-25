"""
LLM Service — Centraliza todo acesso ao modelo com suporte a structured output.

Substitui gemini_service.py como ponto central de acesso ao LLM.
Suporta:
  - Invocação simples com retorno de string
  - Structured output via Pydantic (with_structured_output)
  - LCEL chains
"""
import os
import re
import logging
from functools import lru_cache
from typing import Type, TypeVar

from langchain_core.messages import BaseMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

logger = logging.getLogger("ai_agent")

T = TypeVar("T", bound=BaseModel)

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


@lru_cache(maxsize=1)
def get_llm() -> ChatOpenAI:
    """Singleton LLM — DeepSeek via API OpenAI-compatível."""
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "DEEPSEEK_API_KEY não configurada. "
            "Defina a variável de ambiente DEEPSEEK_API_KEY."
        )

    model = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
    temperature = float(os.environ.get("DEEPSEEK_TEMPERATURE", "0.1"))

    return ChatOpenAI(
        api_key=api_key,
        model=model,
        temperature=temperature,
        base_url="https://api.deepseek.com",
    )


def get_structured_llm(schema: Type[T]):
    """
    Retorna LLM configurado para retornar uma schema Pydantic específica.

    Usa with_structured_output() do LangChain — evita parsing manual de JSON.
    """
    return get_llm().with_structured_output(schema)


def invoke_llm(messages: list) -> str:
    """
    Invoca o LLM com lista de mensagens e retorna string.
    Remove automaticamente tags <think>...</think> (DeepSeek reasoning).
    """
    response = get_llm().invoke(messages)
    content = response.content if hasattr(response, "content") else str(response)
    content = _THINK_RE.sub("", content)
    return content.strip()


def make_chain(system_message: str | None = None):
    """
    Cria uma LCEL chain simples: LLM | StrOutputParser.

    Se system_message for fornecido, cria uma chain com prompt fixo de sistema.
    """
    from langchain_core.prompts import ChatPromptTemplate

    if system_message:
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_message),
            ("human", "{input}"),
        ])
        return prompt | get_llm() | StrOutputParser()

    return get_llm() | StrOutputParser()

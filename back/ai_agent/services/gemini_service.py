"""
LLM Service

Inicializa e fornece o modelo via LangChain (DeepSeek).
"""
import os
import re
from functools import lru_cache
from langchain_openai import ChatOpenAI


@lru_cache(maxsize=1)
def get_llm() -> ChatOpenAI:
    """
    Retorna instância do LLM DeepSeek (singleton via lru_cache).
    Lê configurações do ambiente.
    """
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "DEEPSEEK_API_KEY não configurada. "
            "Defina a variável de ambiente DEEPSEEK_API_KEY."
        )

    model = os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-flash")
    temperature = float(os.environ.get("DEEPSEEK_TEMPERATURE", "0.1"))

    return ChatOpenAI(
        api_key=api_key,
        model=model,
        temperature=temperature,
        base_url="https://api.deepseek.com",
    )


def invoke_llm(messages: list) -> str:
    """
    Invoca o LLM com uma lista de mensagens e retorna o conteúdo textual.

    Args:
        messages: Lista de HumanMessage/SystemMessage/AIMessage do LangChain.

    Returns:
        Texto da resposta do modelo.
    """
    llm = get_llm()
    response = llm.invoke(messages)
    content = response.content.strip()
    # Remover tags <think>...</think> geradas por modelos com raciocínio interno (ex: Qwen3)
    content = re.sub(r"<think>.*?</think>\s*", "", content, flags=re.DOTALL | re.IGNORECASE)
    return content.strip()

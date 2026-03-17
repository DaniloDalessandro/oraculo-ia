"""
Serviço de IA usando LangChain + OpenAI.

Duas chains principais:
  1. text_to_sql_chain  — pergunta + schema + histórico → SQL
  2. format_response_chain — pergunta + dados SQL → resposta em PT-BR
"""

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import settings
from app.services.sql_validator import ALLOWED_TABLES

# ── Descrição do schema para o prompt de Text-to-SQL ────────────────────────

SCHEMA_DESCRIPTION = """
Tabela: messages
  - id (UUID): identificador único da mensagem
  - telefone (VARCHAR): número WhatsApp do usuário (ex: 5511999887766)
  - user_id (UUID): id do usuário autenticado (pode ser NULL)
  - mensagem_usuario (TEXT): texto enviado pelo usuário
  - resposta_sistema (TEXT): resposta gerada pelo sistema
  - created_at (TIMESTAMPTZ): data e hora da mensagem

Tabela: sessions
  - id (UUID): identificador único da sessão
  - telefone (VARCHAR): número WhatsApp
  - status (VARCHAR): 'nao_autenticado' | 'aguardando_login' | 'autenticado'
  - user_id (UUID): id do usuário vinculado (NULL se não autenticado)
  - authenticated_at (TIMESTAMPTZ): data/hora da autenticação
  - last_activity (TIMESTAMPTZ): última atividade registrada

Tabela: users
  - id (UUID): identificador único
  - email (VARCHAR): e-mail do usuário
  - nome (VARCHAR): nome do usuário
  - perfil (VARCHAR): 'admin' | 'operador' | 'cliente'
  - status_conta (VARCHAR): 'ativo' | 'inativo'
  - created_at (TIMESTAMPTZ): data de criação

Tabela: user_configs
  - id (UUID): identificador único
  - user_id (UUID): id do usuário (1:1)
  - bot_ativo (BOOLEAN): se o bot está habilitado
  - limite_diario (INTEGER): máximo de mensagens por dia
  - ia_ativa (BOOLEAN): se a IA está habilitada
  - nome_assistente (VARCHAR): nome do assistente configurado

Tabela: ai_query_logs
  - id (UUID): identificador único
  - user_id (UUID): id do usuário que fez a pergunta
  - telefone (VARCHAR): número WhatsApp
  - pergunta_original (TEXT): pergunta em linguagem natural
  - sql_gerado (TEXT): SQL gerado pela IA
  - tempo_execucao_ms (INTEGER): tempo de execução em milissegundos
  - erro (TEXT): mensagem de erro (NULL se sucesso)
  - created_at (TIMESTAMPTZ): data e hora

Funções PostgreSQL úteis:
  - NOW() → timestamp atual com timezone
  - CURRENT_DATE → data atual
  - DATE_TRUNC('day', campo) → trunca para o dia
  - EXTRACT(hour FROM campo) → extrai hora
  - AGE(timestamp) → diferença de datas
  - TO_CHAR(campo, 'DD/MM/YYYY HH24:MI') → formata data
""".strip()


# ── Inicialização do LLM ─────────────────────────────────────────────────────

def _build_llm(temperature: float | None = None) -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.OPENAI_MODEL,
        api_key=settings.OPENAI_API_KEY,
        temperature=temperature if temperature is not None else settings.AI_TEMPERATURE,
        max_tokens=settings.AI_MAX_TOKENS,
    )


# ── Chain 1: Text-to-SQL ─────────────────────────────────────────────────────

_SQL_SYSTEM = """Você é um especialista em SQL PostgreSQL.
Converta perguntas em linguagem natural para queries SQL de SOMENTE LEITURA.

Schema disponível:
{schema}

Regras OBRIGATÓRIAS:
- Use APENAS SELECT — nunca DELETE, UPDATE, INSERT, DROP ou ALTER
- Use APENAS as tabelas descritas no schema acima
- Adicione LIMIT se não houver (padrão: {row_limit})
- Use funções nativas do PostgreSQL para datas
- Retorne SOMENTE o SQL puro, sem explicações, sem markdown, sem ```
- Se a pergunta for ambígua, gere o SQL mais seguro e útil possível
- Para contagens simples, use COUNT(*)
- Para "hoje", use CURRENT_DATE ou DATE_TRUNC('day', NOW())
- Para "esta semana", use DATE_TRUNC('week', NOW())

Histórico da conversa (use para resolver referências como "esse mesmo", "ontem", "aquele"):
{history}"""

_sql_prompt = ChatPromptTemplate.from_messages([
    ("system", _SQL_SYSTEM),
    ("human", "{question}"),
])


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
async def generate_sql(question: str, history: str) -> str:
    """Gera SQL a partir de pergunta em linguagem natural."""
    llm = _build_llm()
    chain = _sql_prompt | llm | StrOutputParser()
    result = await chain.ainvoke({
        "schema": SCHEMA_DESCRIPTION,
        "row_limit": settings.AI_SQL_ROW_LIMIT,
        "history": history,
        "question": question,
    })
    return result.strip()


# ── Chain 2: Formatador de resposta ─────────────────────────────────────────

_RESPONSE_SYSTEM = """Você é {nome_assistente}, um assistente corporativo inteligente acessado via WhatsApp.

Seu papel é transformar dados brutos de banco de dados em respostas claras e naturais em português brasileiro.

Nível de detalhe: {nivel_detalhe}
- resumido: máximo 2 linhas, só o essencial
- normal: resposta completa e objetiva, com os dados mais relevantes
- detalhado: resposta completa com contexto, análise e insights adicionais

Regras:
- Responda sempre em português brasileiro
- Use formatação WhatsApp: *negrito*, _itálico_, listas com •
- Se não houver dados, diga claramente: "Não encontrei dados para essa consulta."
- Seja preciso com números e datas
- Não invente dados além do que foi retornado
- Mantenha o tom profissional mas acessível"""

_response_prompt = ChatPromptTemplate.from_messages([
    ("system", _RESPONSE_SYSTEM),
    ("human", "Pergunta do usuário: {question}\n\nDados retornados pelo banco:\n{data}\n\nResponda a pergunta acima de forma clara e útil."),
])


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
async def format_response(
    question: str,
    data: str,
    nome_assistente: str = "Assistente",
    nivel_detalhe: str = "normal",
) -> str:
    """Formata dados SQL em resposta amigável em português."""
    llm = _build_llm(temperature=0.3)
    chain = _response_prompt | llm | StrOutputParser()
    result = await chain.ainvoke({
        "nome_assistente": nome_assistente,
        "nivel_detalhe": nivel_detalhe,
        "question": question,
        "data": data,
    })
    return result.strip()


# ── Chain 3: Fallback para perguntas sem SQL ─────────────────────────────────

_GENERAL_SYSTEM = """Você é {nome_assistente}, um assistente corporativo via WhatsApp.

Responda perguntas gerais sobre o sistema de forma útil e clara em português brasileiro.
Você tem acesso a dados de mensagens, sessões e usuários do sistema.
Use formatação WhatsApp: *negrito*, _itálico_.

Histórico:
{history}"""

_general_prompt = ChatPromptTemplate.from_messages([
    ("system", _GENERAL_SYSTEM),
    ("human", "{question}"),
])


async def general_response(
    question: str,
    history: str,
    nome_assistente: str = "Assistente",
) -> str:
    """Resposta geral para perguntas que não precisam de SQL."""
    llm = _build_llm(temperature=0.5)
    chain = _general_prompt | llm | StrOutputParser()
    result = await chain.ainvoke({
        "nome_assistente": nome_assistente,
        "history": history,
        "question": question,
    })
    return result.strip()

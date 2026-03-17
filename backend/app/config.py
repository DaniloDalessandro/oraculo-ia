from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@db:5432/oraculo"
    # URL síncrona usada pelos workers Celery (psycopg2 via asyncpg não funciona em workers sync)
    DATABASE_URL_SYNC: str = "postgresql+psycopg2://postgres:postgres@db:5432/oraculo"
    REDIS_URL: str = "redis://redis:6379/0"
    SECRET_KEY: str = "dev-secret-key-change-in-production-32chars!!"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    LOGIN_TOKEN_EXPIRE_MINUTES: int = 10
    EVOLUTION_API_URL: str = "http://localhost:8080"
    EVOLUTION_API_KEY: str = "changeme"
    EVOLUTION_INSTANCE_NAME: str = "oraculo"
    APP_URL: str = "http://localhost:3000"

    # Sprint 3 — OpenAI / LangChain
    OPENAI_API_KEY: str = "sk-changeme"
    OPENAI_MODEL: str = "gpt-4o-mini"
    AI_MAX_TOKENS: int = 1500
    AI_TEMPERATURE: float = 0.1
    AI_CONTEXT_SIZE: int = 5
    AI_SQL_ROW_LIMIT: int = 50
    AI_TIMEOUT_SECONDS: int = 30

    # Sprint 4 — Celery
    CELERY_BROKER_URL: str = "redis://redis:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/2"
    CELERY_TASK_SOFT_TIME_LIMIT: int = 60   # aviso após 60s
    CELERY_TASK_TIME_LIMIT: int = 120        # kill após 120s

    # Sprint 4 — Cache de respostas IA
    AI_CACHE_TTL_SECONDS: int = 600          # 10 minutos
    AI_CACHE_ENABLED: bool = True

    # Sprint 4 — Rate Limit
    RATE_LIMIT_PER_MINUTE: int = 5           # msgs/min por usuário
    RATE_LIMIT_BURST: int = 3                # tolerância extra



settings = Settings()

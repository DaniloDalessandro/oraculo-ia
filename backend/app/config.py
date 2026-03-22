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
    # WhatsApp Cloud API (Meta)
    WHATSAPP_TOKEN: str = "changeme"
    WHATSAPP_PHONE_NUMBER_ID: str = "changeme"
    WHATSAPP_VERIFY_TOKEN: str = "changeme"
    WHATSAPP_API_VERSION: str = "v18.0"
    WHATSAPP_APP_SECRET: str = ""  # App Secret do painel Meta (opcional mas recomendado)
    APP_URL: str = "http://localhost:3001"

    # Sprint 3 — IA (provedor: "groq", "gemini" ou "openai")
    AI_PROVIDER: str = "groq"
    GROQ_API_KEY: str = "changeme"
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GEMINI_API_KEY: str = "changeme"
    GEMINI_MODEL: str = "gemini-2.0-flash"
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
    CELERY_TASK_SOFT_TIME_LIMIT: int = 55   # aviso após 55s (AI_TIMEOUT=30s + margem)
    CELERY_TASK_TIME_LIMIT: int = 60        # kill após 60s

    # Sprint 4 — Cache de respostas IA
    AI_CACHE_TTL_SECONDS: int = 600          # 10 minutos
    AI_CACHE_ENABLED: bool = True

    # Sprint 4 — Rate Limit
    RATE_LIMIT_PER_MINUTE: int = 5           # msgs/min por usuário
    RATE_LIMIT_BURST: int = 3                # tolerância extra

    # E-mail / Recuperação de senha
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "noreply@oraculoia.com"
    PASSWORD_RESET_EXPIRE_MINUTES: int = 30

    # Segurança — brute-force e sessões
    LOGIN_MAX_ATTEMPTS: int = 5
    LOGIN_LOCKOUT_SECONDS: int = 900          # 15 minutos
    WHATSAPP_SESSION_EXPIRE_HOURS: int = 24   # sessões inativas expiram em 24h



settings = Settings()

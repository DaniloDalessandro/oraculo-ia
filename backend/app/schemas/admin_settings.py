from pydantic import BaseModel, Field


class SystemSettingsOut(BaseModel):
    # IA — comportamento
    ai_provider: str
    ai_max_tokens: int
    ai_temperature: float
    ai_context_size: int
    ai_sql_row_limit: int
    ai_timeout_seconds: int
    ai_cache_enabled: bool
    ai_cache_ttl_seconds: int
    # Modelos
    groq_model: str
    gemini_model: str
    openai_model: str
    # Rate limiting
    rate_limit_per_minute: int
    rate_limit_burst: int
    # Sessão / WhatsApp
    whatsapp_session_expire_hours: int
    # Segurança de login
    login_max_attempts: int
    login_lockout_seconds: int


class SystemSettingsUpdate(BaseModel):
    ai_provider: str | None = Field(None, pattern="^(groq|gemini|openai)$")
    ai_max_tokens: int | None = Field(None, ge=100, le=32000)
    ai_temperature: float | None = Field(None, ge=0.0, le=2.0)
    ai_context_size: int | None = Field(None, ge=1, le=50)
    ai_sql_row_limit: int | None = Field(None, ge=1, le=1000)
    ai_timeout_seconds: int | None = Field(None, ge=5, le=120)
    ai_cache_enabled: bool | None = None
    ai_cache_ttl_seconds: int | None = Field(None, ge=60, le=86400)
    groq_model: str | None = Field(None, max_length=100)
    gemini_model: str | None = Field(None, max_length=100)
    openai_model: str | None = Field(None, max_length=100)
    rate_limit_per_minute: int | None = Field(None, ge=1, le=100)
    rate_limit_burst: int | None = Field(None, ge=0, le=50)
    whatsapp_session_expire_hours: int | None = Field(None, ge=1, le=168)
    login_max_attempts: int | None = Field(None, ge=1, le=20)
    login_lockout_seconds: int | None = Field(None, ge=60, le=86400)

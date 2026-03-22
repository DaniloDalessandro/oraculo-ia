"""
Serviço de configurações de sistema (admin-only).

As configurações ficam na tabela admin_settings como pares key/value (texto).
Ao carregar, os valores sobrescrevem o objeto `settings` em memória —
o restante do código continua lendo de `settings` normalmente.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.admin_setting import AdminSetting
from app.config import settings

# Mapeamento: nome_campo -> (atributo em Settings, tipo)
SETTINGS_MAP: dict[str, tuple[str, type]] = {
    "ai_provider":                  ("AI_PROVIDER",                 str),
    "ai_max_tokens":                ("AI_MAX_TOKENS",               int),
    "ai_temperature":               ("AI_TEMPERATURE",              float),
    "ai_context_size":              ("AI_CONTEXT_SIZE",             int),
    "ai_sql_row_limit":             ("AI_SQL_ROW_LIMIT",            int),
    "ai_timeout_seconds":           ("AI_TIMEOUT_SECONDS",          int),
    "ai_cache_enabled":             ("AI_CACHE_ENABLED",            bool),
    "ai_cache_ttl_seconds":         ("AI_CACHE_TTL_SECONDS",        int),
    "groq_model":                   ("GROQ_MODEL",                  str),
    "gemini_model":                 ("GEMINI_MODEL",                str),
    "openai_model":                 ("OPENAI_MODEL",                str),
    "rate_limit_per_minute":        ("RATE_LIMIT_PER_MINUTE",       int),
    "rate_limit_burst":             ("RATE_LIMIT_BURST",            int),
    "whatsapp_session_expire_hours": ("WHATSAPP_SESSION_EXPIRE_HOURS", int),
    "login_max_attempts":           ("LOGIN_MAX_ATTEMPTS",          int),
    "login_lockout_seconds":        ("LOGIN_LOCKOUT_SECONDS",       int),
}


def _cast(value: str, cast_fn: type):
    if cast_fn is bool:
        return value.lower() in ("true", "1", "yes")
    return cast_fn(value)


def _to_str(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


async def load_from_db(db: AsyncSession) -> dict[str, str]:
    """Retorna todos os overrides salvos no banco."""
    result = await db.execute(select(AdminSetting))
    return {row.key: row.value for row in result.scalars().all()}


def apply_to_runtime(db_overrides: dict[str, str]) -> None:
    """Aplica overrides do banco ao singleton `settings` em memória."""
    for field_name, (attr, cast_fn) in SETTINGS_MAP.items():
        if field_name in db_overrides:
            try:
                setattr(settings, attr, _cast(db_overrides[field_name], cast_fn))
            except (ValueError, TypeError):
                pass


def build_out() -> dict:
    """Lê os valores atuais do singleton `settings` e retorna como dict."""
    return {
        field: getattr(settings, attr)
        for field, (attr, _) in SETTINGS_MAP.items()
    }


async def update_settings(
    db: AsyncSession,
    updates: dict,
    user_id: uuid.UUID,
) -> None:
    """Persiste atualizações no banco e aplica em memória."""
    for field_name, value in updates.items():
        if value is None or field_name not in SETTINGS_MAP:
            continue

        attr, cast_fn = SETTINGS_MAP[field_name]
        str_value = _to_str(value)

        # Upsert na tabela admin_settings
        result = await db.execute(
            select(AdminSetting).where(AdminSetting.key == field_name)
        )
        row = result.scalar_one_or_none()
        if row:
            row.value = str_value
            row.updated_by_id = user_id
        else:
            db.add(AdminSetting(
                key=field_name,
                value=str_value,
                updated_by_id=user_id,
            ))

        # Aplica imediatamente em memória
        setattr(settings, attr, _cast(str_value, cast_fn))

    await db.commit()

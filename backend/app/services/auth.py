import secrets
from datetime import datetime, timedelta, timezone

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.config import settings
from app.core.security import decode_token, hash_password, verify_password
from app.models.audit_log import AuditLog
from app.models.login_token import LoginToken
from app.models.session import Session, SessionStatus
from app.models.user import User

_RESET_KEY_PREFIX = "pwd_reset:"


async def get_or_create_session(db: AsyncSession, telefone: str) -> Session:
    result = await db.execute(select(Session).where(Session.telefone == telefone))
    session = result.scalar_one_or_none()
    if not session:
        session = Session(telefone=telefone, status=SessionStatus.nao_autenticado)
        db.add(session)
        await db.commit()
        await db.refresh(session)
    return session


async def create_login_token(db: AsyncSession, telefone: str) -> LoginToken:
    # Invalida tokens anteriores não utilizados
    await db.execute(
        update(LoginToken)
        .where(LoginToken.telefone == telefone, LoginToken.usado == False)
        .values(usado=True)
    )
    token = LoginToken(
        token=secrets.token_hex(32),
        telefone=telefone,
        expiracao=datetime.now(timezone.utc)
        + timedelta(minutes=settings.LOGIN_TOKEN_EXPIRE_MINUTES),
    )
    db.add(token)
    await db.commit()
    await db.refresh(token)
    return token


async def get_valid_token(db: AsyncSession, token_str: str) -> LoginToken | None:
    result = await db.execute(
        select(LoginToken).where(
            LoginToken.token == token_str,
            LoginToken.usado == False,
            LoginToken.expiracao > datetime.now(timezone.utc),
        )
    )
    return result.scalar_one_or_none()


async def authenticate_user(
    db: AsyncSession, email: str, senha: str
) -> User | None:
    result = await db.execute(
        select(User).where(User.email == email, User.is_active == True)
    )
    user = result.scalar_one_or_none()
    if not user or not verify_password(senha, user.senha_hash):
        return None
    return user


async def create_user(db: AsyncSession, email: str, senha: str) -> User:
    user = User(email=email, senha_hash=hash_password(senha))
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def create_password_reset_token(redis: aioredis.Redis, email: str) -> str:
    token = secrets.token_urlsafe(32)
    ttl = settings.PASSWORD_RESET_EXPIRE_MINUTES * 60
    await redis.setex(f"{_RESET_KEY_PREFIX}{token}", ttl, email)
    return token


async def get_email_from_reset_token(
    redis: aioredis.Redis, token: str
) -> str | None:
    return await redis.get(f"{_RESET_KEY_PREFIX}{token}")


async def reset_password_with_token(
    db: AsyncSession, redis: aioredis.Redis, token: str, nova_senha: str
) -> bool:
    email = await get_email_from_reset_token(redis, token)
    if not email:
        return False
    result = await db.execute(
        select(User).where(User.email == email, User.is_active == True)
    )
    user = result.scalar_one_or_none()
    if not user:
        return False
    await db.execute(
        update(User).where(User.id == user.id).values(senha_hash=hash_password(nova_senha))
    )
    await db.commit()
    await redis.delete(f"{_RESET_KEY_PREFIX}{token}")
    return True


async def logout_user(redis: aioredis.Redis, token_str: str) -> None:
    """Adiciona o JTI do token na blocklist do Redis até ele expirar."""
    try:
        payload = decode_token(token_str)
        jti: str | None = payload.get("jti")
        exp: int | None = payload.get("exp")
        if jti and exp:
            ttl = int(exp - datetime.now(timezone.utc).timestamp())
            if ttl > 0:
                await redis.setex(f"token_blocklist:{jti}", ttl, "1")
    except Exception:
        pass  # token inválido — ignorar silenciosamente


async def change_password(
    db: AsyncSession, user: User, senha_atual: str, nova_senha: str
) -> bool:
    if not verify_password(senha_atual, user.senha_hash):
        return False
    await db.execute(
        update(User).where(User.id == user.id).values(senha_hash=hash_password(nova_senha))
    )
    await db.commit()
    return True


async def record_audit(
    db: AsyncSession,
    acao: str,
    user_id=None,
    detalhes: str | None = None,
    ip: str | None = None,
) -> None:
    log = AuditLog(user_id=user_id, acao=acao, detalhes=detalhes, ip=ip)
    db.add(log)
    await db.commit()


async def expire_whatsapp_sessions(db: AsyncSession) -> int:
    """Marca como nao_autenticado sessões inativas há mais de WHATSAPP_SESSION_EXPIRE_HOURS horas."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=settings.WHATSAPP_SESSION_EXPIRE_HOURS)
    result = await db.execute(
        update(Session)
        .where(
            Session.status == SessionStatus.autenticado,
            Session.last_activity < cutoff,
        )
        .values(status=SessionStatus.nao_autenticado)
        .returning(Session.id)
    )
    await db.commit()
    return len(result.fetchall())


async def link_user_to_session(
    db: AsyncSession, telefone: str, user_id
) -> None:
    await db.execute(
        update(Session)
        .where(Session.telefone == telefone)
        .values(
            user_id=user_id,
            status=SessionStatus.autenticado,
            authenticated_at=datetime.now(timezone.utc),
        )
    )
    await db.commit()

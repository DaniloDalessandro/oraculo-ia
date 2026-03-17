import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.models.login_token import LoginToken
from app.models.session import Session, SessionStatus
from app.models.user import User


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

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import redis.asyncio as aioredis

from app.core.security import decode_token
from app.database import get_db
from app.models.user import User
from app.redis_client import get_redis

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        user_id: str = payload.get("sub")
        jti: str | None = payload.get("jti")
        if not user_id:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # Verifica blocklist (logout revogou este token)
    if jti and await redis.exists(f"token_blocklist:{jti}"):
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise credentials_exception

    # Verifica se usuário foi desativado após emissão do token
    if await redis.exists(f"user_blocked:{user_id}"):
        raise credentials_exception

    return user


async def get_current_administrador(
    current_user: User = Depends(get_current_user),
) -> User:
    """Restringe acesso ao painel somente a administradores."""
    if current_user.perfil != "administrador":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a administradores",
        )
    return current_user

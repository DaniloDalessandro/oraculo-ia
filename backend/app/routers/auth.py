from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
import redis.asyncio as aioredis

from app.config import settings
from app.core.security import create_access_token, verify_password
from app.database import get_db
from app.redis_client import get_redis
from app.models.user import User
from app.models.login_token import LoginToken
from app.schemas.user import (
    LoginRequest,
    TokenResponse,
    VerifyLoginTokenRequest,
    VerifyLoginTokenResponse,
)
from app.services import auth as auth_service
from app.services import session as session_service
from app.services import config as config_service
from app.services.whatsapp import send_whatsapp_message

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    user = await auth_service.authenticate_user(db, body.email, body.senha)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha invalidos",
        )
    access_token = create_access_token(
        {"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return TokenResponse(access_token=access_token)


@router.post("/verify-token", response_model=VerifyLoginTokenResponse)
async def verify_login_token(
    body: VerifyLoginTokenRequest,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    login_token = await auth_service.get_valid_token(db, body.token)
    if not login_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token invalido ou expirado",
        )

    # Busca usuário existente ou cria novo
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas ou usuário não cadastrado. Solicite acesso ao administrador.",
        )
    if not verify_password(body.senha, user.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas ou usuário não cadastrado. Solicite acesso ao administrador.",
        )
    if user.status_conta == "pendente":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cadastro pendente de aprovação. Aguarde o administrador aprovar seu acesso.",
        )
    if user.status_conta == "inativo" or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Conta desativada. Entre em contato com o administrador.",
        )

    telefone = login_token.telefone

    # Vincula telefone ao usuário e marca como autenticado
    await auth_service.link_user_to_session(db, telefone, user.id)

    # Invalida o token
    await db.execute(
        update(LoginToken).where(LoginToken.id == login_token.id).values(usado=True)
    )
    await db.commit()

    # Atualiza Redis
    await session_service.set_session_status(redis, telefone, "autenticado")
    await session_service.set_session_user(redis, telefone, str(user.id))

    # Envia mensagem de boas-vindas no WhatsApp
    config = await config_service.get_or_create_config(db, user.id)
    nome_assistente = config.nome_assistente if config else "Assistente"
    nome_usuario = user.nome or user.email
    await send_whatsapp_message(
        telefone,
        f"✅ *Login realizado com sucesso!*\n\n"
        f"Olá, *{nome_usuario}*! Sou o *{nome_assistente}* e estou pronto para responder suas perguntas.\n\n"
        f"_Digite *menu* para ver os comandos disponíveis._",
    )

    access_token = create_access_token({"sub": str(user.id)})
    return VerifyLoginTokenResponse(
        access_token=access_token,
        message="Login realizado com sucesso!",
    )

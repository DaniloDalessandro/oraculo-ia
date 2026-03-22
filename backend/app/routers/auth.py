import logging
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
import redis.asyncio as aioredis

from app.config import settings
from app.core.dependencies import get_current_user
from app.core.security import create_access_token, verify_password
from app.database import get_db
from app.redis_client import get_redis
from app.models.user import User
from app.models.login_token import LoginToken
from app.schemas.user import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    ResetPasswordRequest,
    TokenResponse,
    VerifyLoginTokenRequest,
    VerifyLoginTokenResponse,
)
from app.services import auth as auth_service
from app.services import session as session_service
from app.services import config as config_service
from app.services.whatsapp import send_whatsapp_message
from app.services.email import send_password_reset_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Auth"])

_ATTEMPTS_KEY = "login_attempts:"


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    ip = request.client.host if request.client else "unknown"
    attempts_key = f"{_ATTEMPTS_KEY}{body.email}"

    attempts = await redis.get(attempts_key)
    if attempts and int(attempts) >= settings.LOGIN_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Conta temporariamente bloqueada por excesso de tentativas. Tente novamente em {settings.LOGIN_LOCKOUT_SECONDS // 60} minutos.",
        )

    user = await auth_service.authenticate_user(db, body.email, body.senha)
    if not user:
        await redis.incr(attempts_key)
        await redis.expire(attempts_key, settings.LOGIN_LOCKOUT_SECONDS)
        await auth_service.record_audit(db, "login_falhou", detalhes=body.email, ip=ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha invalidos",
        )

    await redis.delete(attempts_key)

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

    await auth_service.record_audit(db, "login", user_id=user.id, ip=ip)
    access_token = create_access_token(
        {"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return TokenResponse(access_token=access_token)


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
    current_user: User = Depends(get_current_user),
):
    auth_header = request.headers.get("Authorization", "")
    token_str = auth_header.removeprefix("Bearer ").strip()
    await auth_service.logout_user(redis, token_str)
    ip = request.client.host if request.client else "unknown"
    await auth_service.record_audit(db, "logout", user_id=current_user.id, ip=ip)
    return {"message": "Logout realizado com sucesso."}


@router.post("/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    request: Request,
    body: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
    current_user: User = Depends(get_current_user),
):
    if len(body.nova_senha) < 6:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A nova senha deve ter pelo menos 6 caracteres.",
        )

    ok = await auth_service.change_password(db, current_user, body.senha_atual, body.nova_senha)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Senha atual incorreta.",
        )

    ip = request.client.host if request.client else "unknown"
    await auth_service.record_audit(db, "troca_senha", user_id=current_user.id, ip=ip)
    return {"message": "Senha alterada com sucesso."}


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
    await auth_service.link_user_to_session(db, telefone, user.id)

    await db.execute(
        update(LoginToken).where(LoginToken.id == login_token.id).values(usado=True)
    )
    await db.commit()

    await session_service.set_session_status(redis, telefone, "autenticado")
    await session_service.set_session_user(redis, telefone, str(user.id))

    config = await config_service.get_or_create_config(db, user.id)
    nome_assistente = config.nome_assistente if config else "Assistente"
    nome_usuario = user.nome or user.email
    await send_whatsapp_message(
        telefone,
        f"✅ *Login realizado com sucesso!*\n\n"
        f"Olá, *{nome_usuario}*! Sou o *{nome_assistente}* e estou pronto para responder suas perguntas.\n\n"
        f"_Digite *menu* para ver os comandos disponíveis._",
    )

    await auth_service.record_audit(db, "login_whatsapp", user_id=user.id, detalhes=telefone)
    access_token = create_access_token({"sub": str(user.id)})
    return VerifyLoginTokenResponse(
        access_token=access_token,
        message="Login realizado com sucesso!",
    )


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
async def forgot_password(
    body: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    result = await db.execute(
        select(User).where(User.email == body.email, User.is_active == True)
    )
    user = result.scalar_one_or_none()

    if user and user.status_conta == "ativo":
        token = await auth_service.create_password_reset_token(redis, body.email)
        reset_url = f"{settings.APP_URL}/reset-senha?token={token}"
        try:
            await send_password_reset_email(body.email, reset_url)
        except Exception:
            logger.exception("Falha ao enviar e-mail de recuperacao para %s", body.email)
        await auth_service.record_audit(db, "reset_senha_solicitado", user_id=user.id, detalhes=body.email)

    return {"message": "Se o e-mail estiver cadastrado, voce recebera as instrucoes em breve."}


@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    if len(body.nova_senha) < 6:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A nova senha deve ter pelo menos 6 caracteres.",
        )

    ok = await auth_service.reset_password_with_token(db, redis, body.token, body.nova_senha)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token invalido ou expirado.",
        )

    return {"message": "Senha redefinida com sucesso."}

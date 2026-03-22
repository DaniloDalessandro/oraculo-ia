import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import redis.asyncio as aioredis

from app.database import get_db
from app.redis_client import get_redis
from app.core.dependencies import get_current_user
from app.core.security import hash_password
from app.models.audit_log import AuditLog
from app.models.user import User
from app.schemas.user import AdminUserCreate, AdminUserOut, AdminUserUpdate, AuditLogOut
from app.services import auth as auth_service
from app.services.email import send_welcome_email, send_account_approved_email
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.perfil != "administrador":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a administradores",
        )
    return current_user


@router.get("/usuarios", response_model=list[AdminUserOut])
async def listar_usuarios(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    return result.scalars().all()


@router.post("/usuarios", response_model=AdminUserOut, status_code=201)
async def criar_usuario(
    request: Request,
    body: AdminUserCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email já cadastrado")

    user = User(
        email=body.email,
        senha_hash=hash_password(body.senha),
        nome=body.nome,
        setor=body.setor,
        perfil=body.perfil,
        status_conta="pendente",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    ip = request.client.host if request.client else "unknown"
    await auth_service.record_audit(
        db, "usuario_criado",
        user_id=admin.id,
        detalhes=f"criou {body.email}",
        ip=ip,
    )

    try:
        await send_welcome_email(body.email, body.nome, settings.APP_URL + "/login")
    except Exception:
        logger.warning("Falha ao enviar e-mail de boas-vindas para %s", body.email)

    return user


@router.patch("/usuarios/{user_id}", response_model=AdminUserOut)
async def atualizar_usuario(
    user_id: str,
    request: Request,
    body: AdminUserUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
    redis: aioredis.Redis = Depends(get_redis),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    status_anterior = user.status_conta
    updates = body.model_dump(exclude_none=True)
    for field, value in updates.items():
        setattr(user, field, value)

    if "status_conta" in updates:
        user.is_active = updates["status_conta"] == "ativo"
    if "is_active" in updates:
        user.status_conta = "ativo" if updates["is_active"] else "inativo"

    await db.commit()
    await db.refresh(user)

    # Revoga tokens ativos se usuário foi desativado (issue #6 e #14)
    is_now_inactive = not user.is_active or user.status_conta != "ativo"
    if is_now_inactive:
        await redis.setex(f"user_blocked:{user_id}", settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60, "1")

    ip = request.client.host if request.client else "unknown"
    await auth_service.record_audit(
        db, "usuario_atualizado",
        user_id=admin.id,
        detalhes=f"atualizou {user.email}: {body.model_dump(exclude_none=True)}",
        ip=ip,
    )

    if status_anterior == "pendente" and user.status_conta == "ativo":
        try:
            await send_account_approved_email(
                user.email,
                user.nome or user.email,
                settings.APP_URL + "/login",
            )
        except Exception:
            logger.warning("Falha ao enviar e-mail de aprovacao para %s", user.email)

    return user


@router.delete("/usuarios/{user_id}", status_code=204)
async def deletar_usuario(
    user_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    if str(user.id) == str(current_user.id):
        raise HTTPException(
            status_code=400,
            detail="Não é possível excluir o próprio usuário",
        )

    email_deletado = user.email
    user.is_active = False
    user.status_conta = "inativo"
    user.email = f"deleted_{user.id}@deleted.invalid"
    await db.commit()
    await redis.setex(f"user_blocked:{user_id}", settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60, "1")

    ip = request.client.host if request.client else "unknown"
    await auth_service.record_audit(
        db, "usuario_deletado",
        user_id=current_user.id,
        detalhes=f"deletou {email_deletado}",
        ip=ip,
    )


@router.get("/audit-logs", response_model=list[AuditLogOut])
async def listar_audit_logs(
    limit: int = 100,
    offset: int = 0,
    acao: str | None = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    query = select(AuditLog).order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)
    if acao:
        query = query.where(AuditLog.acao == acao)
    result = await db.execute(query)
    return result.scalars().all()

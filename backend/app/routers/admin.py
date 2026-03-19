from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.core.dependencies import get_current_user
from app.core.security import hash_password
from app.models.user import User
from app.schemas.user import AdminUserCreate, AdminUserOut, AdminUserUpdate

router = APIRouter(prefix="/admin", tags=["Admin"])


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Dependency that enforces administrador-only access."""
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
    """Return all users ordered by creation date descending."""
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    return result.scalars().all()


@router.post("/usuarios", response_model=AdminUserOut, status_code=201)
async def criar_usuario(
    body: AdminUserCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Create a new user. Rejects duplicate emails."""
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
    return user


@router.patch("/usuarios/{user_id}", response_model=AdminUserOut)
async def atualizar_usuario(
    user_id: str,
    body: AdminUserUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Partially update a user's fields."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(user, field, value)

    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/usuarios/{user_id}", status_code=204)
async def deletar_usuario(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Delete a user. Admins cannot delete their own account."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    if str(user.id) == str(current_user.id):
        raise HTTPException(
            status_code=400,
            detail="Não é possível excluir o próprio usuário",
        )
    await db.delete(user)
    await db.commit()

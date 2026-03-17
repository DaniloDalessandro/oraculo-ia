from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.models.session import Session, SessionStatus
from app.schemas.settings import (
    UserConfigOut,
    UserConfigUpdate,
    UserProfileOut,
    UserProfileUpdate,
)
from app.services import config as config_service

router = APIRouter(prefix="/settings", tags=["Settings"])


async def _get_linked_phone(db: AsyncSession, user_id) -> str | None:
    result = await db.execute(
        select(Session.telefone).where(
            Session.user_id == user_id,
            Session.status == SessionStatus.autenticado,
        )
    )
    row = result.first()
    return row[0] if row else None


@router.get("/me", response_model=UserProfileOut)
async def get_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    config = await config_service.get_or_create_config(db, current_user.id)
    telefone = await _get_linked_phone(db, current_user.id)

    config_out = UserConfigOut.model_validate(config) if config else None

    return UserProfileOut(
        id=str(current_user.id),
        email=current_user.email,
        nome=current_user.nome,
        perfil=current_user.perfil,
        status_conta=current_user.status_conta,
        telefone_vinculado=telefone,
        config=config_out,
    )


@router.put("/me", response_model=UserProfileOut)
async def update_profile(
    body: UserProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if body.nome is not None:
        current_user.nome = body.nome
        await db.commit()
        await db.refresh(current_user)

    config = await config_service.get_or_create_config(db, current_user.id)
    telefone = await _get_linked_phone(db, current_user.id)

    return UserProfileOut(
        id=str(current_user.id),
        email=current_user.email,
        nome=current_user.nome,
        perfil=current_user.perfil,
        status_conta=current_user.status_conta,
        telefone_vinculado=telefone,
        config=UserConfigOut.model_validate(config),
    )


@router.get("/config", response_model=UserConfigOut)
async def get_config(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    config = await config_service.get_or_create_config(db, current_user.id)
    return UserConfigOut.model_validate(config)


@router.put("/config", response_model=UserConfigOut)
async def update_config(
    body: UserConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    config = await config_service.get_or_create_config(db, current_user.id)
    updated = await config_service.update_config(
        db,
        config,
        bot_ativo=body.bot_ativo,
        limite_diario=body.limite_diario,
        idioma=body.idioma,
        nome_assistente=body.nome_assistente,
    )
    return UserConfigOut.model_validate(updated)

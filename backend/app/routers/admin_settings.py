from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.routers.admin import require_admin
from app.schemas.admin_settings import SystemSettingsOut, SystemSettingsUpdate
from app.services import admin_settings as svc

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/system-settings", response_model=SystemSettingsOut)
async def get_system_settings(
    _: User = Depends(require_admin),
):
    return SystemSettingsOut(**svc.build_out())


@router.put("/system-settings", response_model=SystemSettingsOut)
async def update_system_settings(
    body: SystemSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    updates = body.model_dump(exclude_none=True)
    await svc.update_settings(db, updates, admin.id)
    return SystemSettingsOut(**svc.build_out())

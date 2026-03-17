from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.message import MessageListResponse, MessageOut
from app.services import message as message_service

router = APIRouter(prefix="/messages", tags=["Messages"])


@router.get("", response_model=MessageListResponse)
async def list_messages(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user_id: str | None = Query(None),
    q: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items, total = await message_service.list_messages(
        db, page=page, limit=limit, user_id=user_id, q=q
    )
    return MessageListResponse(
        items=[MessageOut.model_validate(m) for m in items],
        total=total,
        page=page,
        limit=limit,
    )

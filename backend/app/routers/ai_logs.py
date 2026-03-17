from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from datetime import datetime

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.ai_query_log import AIQueryLog
from app.models.user import User

router = APIRouter(prefix="/ai-logs", tags=["AI Logs"])


class AILogOut(BaseModel):
    id: str
    user_id: str | None
    telefone: str
    pergunta_original: str
    sql_gerado: str | None
    resposta_final: str | None
    tempo_execucao_ms: int | None
    modelo_usado: str
    erro: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AILogListResponse(BaseModel):
    items: list[AILogOut]
    total: int
    page: int
    limit: int


@router.get("", response_model=AILogListResponse)
async def list_ai_logs(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    com_erro: bool | None = Query(None, description="Filtrar apenas logs com erro"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(AIQueryLog)
    count_q = select(func.count(AIQueryLog.id))

    if com_erro is True:
        query = query.where(AIQueryLog.erro.isnot(None))
        count_q = count_q.where(AIQueryLog.erro.isnot(None))
    elif com_erro is False:
        query = query.where(AIQueryLog.erro.is_(None))
        count_q = count_q.where(AIQueryLog.erro.is_(None))

    total = (await db.execute(count_q)).scalar_one() or 0

    offset = (page - 1) * limit
    query = query.order_by(AIQueryLog.created_at.desc()).offset(offset).limit(limit)
    items = list((await db.execute(query)).scalars().all())

    return AILogListResponse(
        items=[AILogOut.model_validate(i) for i in items],
        total=total,
        page=page,
        limit=limit,
    )

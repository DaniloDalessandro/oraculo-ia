import uuid
from datetime import datetime, date, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_

from app.models.message import Message
from app.models.user import User


async def log_message(
    db: AsyncSession,
    telefone: str,
    user_id: uuid.UUID | None,
    mensagem_usuario: str,
    resposta_sistema: str,
) -> Message:
    msg = Message(
        telefone=telefone,
        user_id=user_id,
        mensagem_usuario=mensagem_usuario,
        resposta_sistema=resposta_sistema,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return msg


async def count_today(db: AsyncSession, user_id: uuid.UUID) -> int:
    today_start = datetime.combine(date.today(), datetime.min.time()).replace(
        tzinfo=timezone.utc
    )
    result = await db.execute(
        select(func.count(Message.id)).where(
            Message.user_id == user_id,
            Message.created_at >= today_start,
        )
    )
    return result.scalar_one() or 0


async def get_total(db: AsyncSession) -> int:
    result = await db.execute(select(func.count(Message.id)))
    return result.scalar_one() or 0


async def get_today_total(db: AsyncSession) -> int:
    today_start = datetime.combine(date.today(), datetime.min.time()).replace(
        tzinfo=timezone.utc
    )
    result = await db.execute(
        select(func.count(Message.id)).where(Message.created_at >= today_start)
    )
    return result.scalar_one() or 0


async def get_recent(db: AsyncSession, limit: int = 5) -> list[Message]:
    result = await db.execute(
        select(Message).order_by(Message.created_at.desc()).limit(limit)
    )
    return list(result.scalars().all())


async def list_messages(
    db: AsyncSession,
    page: int = 1,
    limit: int = 20,
    user_id: str | None = None,
    q: str | None = None,
) -> tuple[list[Message], int]:
    query = select(Message)
    count_query = select(func.count(Message.id))

    if user_id:
        try:
            uid = uuid.UUID(user_id)
            query = query.where(Message.user_id == uid)
            count_query = count_query.where(Message.user_id == uid)
        except ValueError:
            pass

    if q:
        search = f"%{q}%"
        query = query.where(
            or_(
                Message.mensagem_usuario.ilike(search),
                Message.resposta_sistema.ilike(search),
                Message.telefone.ilike(search),
            )
        )
        count_query = count_query.where(
            or_(
                Message.mensagem_usuario.ilike(search),
                Message.resposta_sistema.ilike(search),
                Message.telefone.ilike(search),
            )
        )

    total_result = await db.execute(count_query)
    total = total_result.scalar_one() or 0

    offset = (page - 1) * limit
    query = query.order_by(Message.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    items = list(result.scalars().all())

    return items, total

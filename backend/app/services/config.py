import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user_config import UserConfig


async def get_or_create_config(db: AsyncSession, user_id: uuid.UUID) -> UserConfig:
    result = await db.execute(
        select(UserConfig).where(UserConfig.user_id == user_id)
    )
    config = result.scalar_one_or_none()
    if not config:
        config = UserConfig(user_id=user_id)
        db.add(config)
        await db.commit()
        await db.refresh(config)
    return config


async def update_config(
    db: AsyncSession,
    config: UserConfig,
    **fields,
) -> UserConfig:
    for key, value in fields.items():
        if value is not None and hasattr(config, key):
            setattr(config, key, value)
    await db.commit()
    await db.refresh(config)
    return config

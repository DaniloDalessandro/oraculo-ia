import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserConfig(Base):
    __tablename__ = "user_configs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False
    )
    bot_ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    limite_diario: Mapped[int] = mapped_column(Integer, default=100)
    idioma: Mapped[str] = mapped_column(String(10), default="pt-BR")
    nome_assistente: Mapped[str] = mapped_column(String(100), default="Assistente")

    ia_ativa: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    limite_ia_diario: Mapped[int] = mapped_column(Integer, default=50, server_default="50")
    nivel_detalhe: Mapped[str] = mapped_column(  # resumido | normal | detalhado
        String(20), default="normal", server_default="normal"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user: Mapped["User"] = relationship("User", back_populates="config")

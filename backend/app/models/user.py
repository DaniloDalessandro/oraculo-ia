import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    senha_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    nome: Mapped[str | None] = mapped_column(String(100), nullable=True)
    setor: Mapped[str | None] = mapped_column(String(100), nullable=True)
    perfil: Mapped[str] = mapped_column(
        String(20), nullable=False, default="colaborador", server_default="colaborador"
    )
    status_conta: Mapped[str] = mapped_column(
        String(20), nullable=False, default="ativo", server_default="ativo"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    sessions: Mapped[list["Session"]] = relationship("Session", back_populates="user")
    login_tokens: Mapped[list["LoginToken"]] = relationship(
        "LoginToken", back_populates="user"
    )
    config: Mapped["UserConfig | None"] = relationship(
        "UserConfig", back_populates="user", uselist=False
    )
    messages: Mapped[list["Message"]] = relationship("Message", back_populates="user")
    ai_query_logs: Mapped[list["AIQueryLog"]] = relationship(
        "AIQueryLog", back_populates="user"
    )

import secrets
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class LoginToken(Base):
    __tablename__ = "login_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    token: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
        default=lambda: secrets.token_hex(32),
    )
    telefone: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    expiracao: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    usado: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    user: Mapped["User | None"] = relationship("User", back_populates="login_tokens")

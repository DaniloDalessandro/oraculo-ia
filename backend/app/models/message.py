import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Text, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    telefone: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True
    )
    mensagem_usuario: Mapped[str] = mapped_column(Text, nullable=False)
    resposta_sistema: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    user: Mapped["User | None"] = relationship("User", back_populates="messages")

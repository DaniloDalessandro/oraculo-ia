import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AIQueryLog(Base):
    __tablename__ = "ai_query_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True
    )
    telefone: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    pergunta_original: Mapped[str] = mapped_column(Text, nullable=False)
    sql_gerado: Mapped[str | None] = mapped_column(Text, nullable=True)
    resultado_bruto: Mapped[str | None] = mapped_column(Text, nullable=True)
    resposta_final: Mapped[str | None] = mapped_column(Text, nullable=True)
    tempo_execucao_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    modelo_usado: Mapped[str] = mapped_column(String(50), nullable=False)
    erro: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    user: Mapped["User | None"] = relationship("User")

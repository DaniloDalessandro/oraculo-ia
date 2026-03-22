import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Venda(Base):
    __tablename__ = "vendas"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    data_venda: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    produto: Mapped[str] = mapped_column(String(100), nullable=False)
    categoria: Mapped[str] = mapped_column(String(50), nullable=False)
    quantidade: Mapped[int] = mapped_column(Integer, nullable=False)
    valor_unitario: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    valor_total: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    cliente: Mapped[str] = mapped_column(String(100), nullable=False)
    vendedor: Mapped[str] = mapped_column(String(100), nullable=False)
    vendedor_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("vendedores.id", ondelete="SET NULL"), nullable=True, index=True
    )
    regiao: Mapped[str] = mapped_column(String(50), nullable=False)
    status_pagamento: Mapped[str] = mapped_column(String(20), nullable=False)
    forma_pagamento: Mapped[str] = mapped_column(String(30), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

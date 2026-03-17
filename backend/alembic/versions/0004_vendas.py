"""Cria tabela vendas

Revision ID: 0004_vendas
Revises: 0003_sprint3
Create Date: 2026-03-17
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004_vendas"
down_revision = "0003_sprint3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "vendas",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("data_venda", sa.DateTime(timezone=True), nullable=False),
        sa.Column("produto", sa.String(100), nullable=False),
        sa.Column("categoria", sa.String(50), nullable=False),
        sa.Column("quantidade", sa.Integer, nullable=False),
        sa.Column("valor_unitario", sa.Numeric(10, 2), nullable=False),
        sa.Column("valor_total", sa.Numeric(10, 2), nullable=False),
        sa.Column("cliente", sa.String(100), nullable=False),
        sa.Column("vendedor", sa.String(100), nullable=False),
        sa.Column("regiao", sa.String(50), nullable=False),
        sa.Column("status_pagamento", sa.String(20), nullable=False),
        sa.Column("forma_pagamento", sa.String(30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_vendas_data_venda", "vendas", ["data_venda"])
    op.create_index("ix_vendas_categoria", "vendas", ["categoria"])
    op.create_index("ix_vendas_vendedor", "vendas", ["vendedor"])
    op.create_index("ix_vendas_regiao", "vendas", ["regiao"])


def downgrade() -> None:
    op.drop_table("vendas")

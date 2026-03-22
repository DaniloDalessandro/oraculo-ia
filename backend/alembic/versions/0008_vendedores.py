"""Cria tabela vendedores e vincula com vendas

Revision ID: 0008
Revises: 0007
Create Date: 2026-03-22
"""

from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "vendedores",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("nome", sa.String(100), nullable=False),
        sa.Column("email", sa.String(100), nullable=False, unique=True),
        sa.Column("regiao", sa.String(50), nullable=False),
        sa.Column("meta_mensal", sa.Numeric(12, 2), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.add_column(
        "vendas",
        sa.Column(
            "vendedor_id",
            sa.Integer,
            sa.ForeignKey("vendedores.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_vendas_vendedor_id", "vendas", ["vendedor_id"])


def downgrade() -> None:
    op.drop_index("ix_vendas_vendedor_id", "vendas")
    op.drop_column("vendas", "vendedor_id")
    op.drop_table("vendedores")

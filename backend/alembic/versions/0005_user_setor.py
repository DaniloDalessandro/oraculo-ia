"""Adiciona campo setor ao usuario

Revision ID: 0005_user_setor
Revises: 0004_vendas
Create Date: 2026-03-17
"""
from alembic import op
import sqlalchemy as sa

revision = "0005_user_setor"
down_revision = "0004_vendas"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("setor", sa.String(100), nullable=True))


def downgrade():
    op.drop_column("users", "setor")

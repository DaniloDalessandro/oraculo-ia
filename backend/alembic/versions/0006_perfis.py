"""Migra perfis para administrador/colaborador

Revision ID: 0006
Revises: 0005
Create Date: 2026-03-19
"""
from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005_user_setor"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Migra valores existentes
    op.execute("UPDATE users SET perfil = 'administrador' WHERE perfil = 'admin'")
    op.execute("UPDATE users SET perfil = 'colaborador' WHERE perfil IN ('operador', 'cliente')")

    # Atualiza o default da coluna
    op.alter_column(
        "users",
        "perfil",
        existing_type=sa.String(20),
        server_default="colaborador",
    )


def downgrade() -> None:
    op.execute("UPDATE users SET perfil = 'admin' WHERE perfil = 'administrador'")
    op.execute("UPDATE users SET perfil = 'cliente' WHERE perfil = 'colaborador'")
    op.alter_column(
        "users",
        "perfil",
        existing_type=sa.String(20),
        server_default="cliente",
    )

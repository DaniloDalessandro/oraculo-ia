"""Sprint 2: expand users/sessions, add messages and user_configs

Revision ID: 0002_sprint2
Revises: None
Create Date: 2026-03-17
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_sprint2"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # --- users: add new columns if not exist ---
    for col, definition in [
        ("nome", "VARCHAR(100)"),
        ("perfil", "VARCHAR(20) NOT NULL DEFAULT 'cliente'"),
        ("status_conta", "VARCHAR(20) NOT NULL DEFAULT 'ativo'"),
    ]:
        result = conn.execute(
            sa.text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='users' AND column_name=:col"
            ),
            {"col": col},
        )
        if not result.fetchone():
            op.add_column("users", sa.Column(col, sa.String(20 if col != "nome" else 100), nullable=True))
            if col != "nome":
                op.execute(f"UPDATE users SET {col} = '{('cliente' if col == 'perfil' else 'ativo')}'")
                op.alter_column("users", col, nullable=False)

    # --- sessions: add last_activity if not exist ---
    result = conn.execute(
        sa.text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='sessions' AND column_name='last_activity'"
        )
    )
    if not result.fetchone():
        op.add_column(
            "sessions",
            sa.Column("last_activity", sa.DateTime(timezone=True), nullable=True),
        )

    # --- messages table ---
    op.create_table(
        "messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("telefone", sa.String(30), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("mensagem_usuario", sa.Text, nullable=False),
        sa.Column("resposta_sistema", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_messages_telefone", "messages", ["telefone"])
    op.create_index("ix_messages_user_id", "messages", ["user_id"])
    op.create_index("ix_messages_created_at", "messages", ["created_at"])

    # --- user_configs table ---
    op.create_table(
        "user_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, unique=True),
        sa.Column("bot_ativo", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("limite_diario", sa.Integer, nullable=False, server_default="100"),
        sa.Column("idioma", sa.String(10), nullable=False, server_default="pt-BR"),
        sa.Column("nome_assistente", sa.String(100), nullable=False, server_default="Assistente"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("user_configs")
    op.drop_table("messages")
    op.drop_column("sessions", "last_activity")
    op.drop_column("users", "status_conta")
    op.drop_column("users", "perfil")
    op.drop_column("users", "nome")

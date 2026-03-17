"""Sprint 3: add AI fields to user_configs, create ai_query_logs

Revision ID: 0003_sprint3
Revises: 0002_sprint2
Create Date: 2026-03-17
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003_sprint3"
down_revision = "0002_sprint2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # user_configs: add IA columns if not exist
    for col, col_type, default in [
        ("ia_ativa", "BOOLEAN NOT NULL DEFAULT true", None),
        ("limite_ia_diario", "INTEGER NOT NULL DEFAULT 50", None),
        ("nivel_detalhe", "VARCHAR(20) NOT NULL DEFAULT 'normal'", None),
    ]:
        result = conn.execute(
            sa.text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='user_configs' AND column_name=:col"
            ),
            {"col": col},
        )
        if not result.fetchone():
            op.add_column("user_configs", sa.Column(col, sa.Text, nullable=True))
            op.execute(f"UPDATE user_configs SET {col} = '{col_type.split('DEFAULT ')[1]}'")

    # ai_query_logs table
    op.create_table(
        "ai_query_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("telefone", sa.String(30), nullable=False),
        sa.Column("pergunta_original", sa.Text, nullable=False),
        sa.Column("sql_gerado", sa.Text, nullable=True),
        sa.Column("resultado_bruto", sa.Text, nullable=True),
        sa.Column("resposta_final", sa.Text, nullable=True),
        sa.Column("tempo_execucao_ms", sa.Integer, nullable=True),
        sa.Column("modelo_usado", sa.String(50), nullable=False, server_default="gpt-4o-mini"),
        sa.Column("erro", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_ai_query_logs_user_id", "ai_query_logs", ["user_id"])
    op.create_index("ix_ai_query_logs_telefone", "ai_query_logs", ["telefone"])
    op.create_index("ix_ai_query_logs_created_at", "ai_query_logs", ["created_at"])


def downgrade() -> None:
    op.drop_table("ai_query_logs")
    op.drop_column("user_configs", "nivel_detalhe")
    op.drop_column("user_configs", "limite_ia_diario")
    op.drop_column("user_configs", "ia_ativa")

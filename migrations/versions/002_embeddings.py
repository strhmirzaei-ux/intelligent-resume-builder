"""Add JSONB-stored embeddings used by the FAISS search adapter.

The historical revision id contains ``pgvector`` for compatibility with
databases created by an older project version. This migration does not enable
the PostgreSQL pgvector extension or create vector columns; embeddings are
stored as JSONB and searched through the FAISS adapter.

Revision ID: 002_pgvector_embeddings
Revises: 001_initial_resume_graph
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "002_pgvector_embeddings"
down_revision = "001_initial_resume_graph"
branch_labels = None
depends_on = None


def upgrade() -> None:
    embedding_type = postgresql.JSONB()
    op.add_column(
        "resume_sessions",
        sa.Column("asked_deficiency_codes", postgresql.JSONB(), nullable=False, server_default="[]"),
    )
    op.add_column("chat_messages", sa.Column("embedding", embedding_type, nullable=True))
    op.create_table(
        "resume_questions",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("resume_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("question_code", sa.String(length=200)),
        sa.Column("embedding", embedding_type, nullable=True),
        sa.Column("answered", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "resume_entities",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("resume_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("entity_key", sa.String(length=255), nullable=False),
        sa.Column("entity_data", postgresql.JSONB(), nullable=False),
        sa.Column("embedding", embedding_type, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("resume_entities")
    op.drop_table("resume_questions")
    op.drop_column("chat_messages", "embedding")
    op.drop_column("resume_sessions", "asked_deficiency_codes")

"""Add pgvector embeddings for messages, questions, and resume entities.

Revision ID: 002_pgvector_embeddings
Revises: 001_initial_resume_graph
"""

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision = "002_pgvector_embeddings"
down_revision = "001_initial_resume_graph"
branch_labels = None
depends_on = None

EMBEDDING_DIMENSION = 384


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.add_column(
        "resume_sessions",
        sa.Column("asked_deficiency_codes", postgresql.JSONB(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "chat_messages",
        sa.Column("embedding", Vector(EMBEDDING_DIMENSION), nullable=True),
    )
    op.create_table(
        "resume_questions",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("resume_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("question_code", sa.String(length=200)),
        sa.Column("embedding", Vector(EMBEDDING_DIMENSION), nullable=True),
        sa.Column("answered", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "resume_entities",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("resume_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("entity_key", sa.String(length=255), nullable=False),
        sa.Column("entity_data", postgresql.JSONB(), nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIMENSION), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "ix_resume_questions_embedding_cosine",
        "resume_questions",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )
    op.create_index(
        "ix_resume_entities_embedding_cosine",
        "resume_entities",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )
    op.create_index(
        "ix_chat_messages_embedding_cosine",
        "chat_messages",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )


def downgrade() -> None:
    op.drop_index("ix_chat_messages_embedding_cosine", table_name="chat_messages")
    op.drop_index("ix_resume_entities_embedding_cosine", table_name="resume_entities")
    op.drop_index("ix_resume_questions_embedding_cosine", table_name="resume_questions")
    op.drop_table("resume_entities")
    op.drop_table("resume_questions")
    op.drop_column("chat_messages", "embedding")
    op.drop_column("resume_sessions", "asked_deficiency_codes")

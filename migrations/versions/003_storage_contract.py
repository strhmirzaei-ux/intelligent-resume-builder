"""Persist question targets for backend parity.

Revision ID: 003_storage_contract
Revises: 002_pgvector_embeddings
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "003_storage_contract"
down_revision = "002_pgvector_embeddings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "resume_questions",
        sa.Column("target_entity", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("resume_questions", "target_entity")

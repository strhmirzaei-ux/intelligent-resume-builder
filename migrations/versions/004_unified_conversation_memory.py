"""Add compact conversation memory for the unified resume agent.

Revision ID: 004_unified_conversation_memory
Revises: 003_storage_contract
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "004_unified_conversation_memory"
down_revision = "003_storage_contract"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "resume_sessions",
        sa.Column("conversation_summary", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "resume_sessions",
        sa.Column("suppressed_facts", postgresql.JSONB(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "resume_sessions",
        sa.Column("operation_history", postgresql.JSONB(), nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("resume_sessions", "operation_history")
    op.drop_column("resume_sessions", "suppressed_facts")
    op.drop_column("resume_sessions", "conversation_summary")

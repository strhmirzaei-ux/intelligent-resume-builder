"""create resume graph persistence tables

Revision ID: 001_initial_resume_graph
Revises:
Create Date: 2026-08-26
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001_initial_resume_graph"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    uuid_type = postgresql.UUID(as_uuid=False)
    json_type = postgresql.JSONB()
    op.create_table(
        "users",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("external_id", sa.String(length=255), unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "resume_sessions",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("user_id", uuid_type, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("raw_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("normalized_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("asked_deficiencies", json_type, nullable=False, server_default="[]"),
        sa.Column("next_question", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "chat_messages",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("session_id", uuid_type, sa.ForeignKey("resume_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(length=30), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "resume_versions",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("session_id", uuid_type, sa.ForeignKey("resume_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("resume_data", json_type, nullable=False),
        sa.Column("analysis_data", json_type, nullable=False),
        sa.Column("coverage_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("session_id", "version_number", name="uq_resume_version_number"),
    )
    op.create_table(
        "resume_graph_nodes",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("version_id", uuid_type, sa.ForeignKey("resume_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("node_key", sa.String(length=50), nullable=False),
        sa.Column("label", sa.String(length=100), nullable=False),
        sa.Column("weight", sa.Integer(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("filled_fields", sa.Integer(), nullable=False),
        sa.Column("total_fields", sa.Integer(), nullable=False),
        sa.Column("missing_fields", json_type, nullable=False, server_default="[]"),
        sa.Column("node_data", json_type, nullable=False, server_default="{}"),
        sa.UniqueConstraint("version_id", "node_key", name="uq_graph_node_version"),
    )


def downgrade() -> None:
    op.drop_table("resume_graph_nodes")
    op.drop_table("resume_versions")
    op.drop_table("chat_messages")
    op.drop_table("resume_sessions")
    op.drop_table("users")

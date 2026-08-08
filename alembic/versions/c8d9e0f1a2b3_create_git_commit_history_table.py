"""Create deployment-synced Git commit history.

Revision ID: c8d9e0f1a2b3
Revises: b7c8d9e0f1a2
Create Date: 2026-08-08 16:45:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c8d9e0f1a2b3"
down_revision: str | None = "b7c8d9e0f1a2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "git_commit_history" in inspector.get_table_names():
        return
    op.create_table(
        "git_commit_history",
        sa.Column("commit_hash", sa.Text(), nullable=False),
        sa.Column("author", sa.Text(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("committed_at", sa.BigInteger(), nullable=False),
        sa.Column("member_keys", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.PrimaryKeyConstraint("commit_hash"),
    )
    op.create_index(
        op.f("ix_git_commit_history_committed_at"),
        "git_commit_history",
        ["committed_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_git_commit_history_committed_at"),
        table_name="git_commit_history",
    )
    op.drop_table("git_commit_history")

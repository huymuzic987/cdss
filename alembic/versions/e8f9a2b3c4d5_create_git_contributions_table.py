"""create git contributions table

Revision ID: e8f9a2b3c4d5
Revises: c7a41e92d830
Create Date: 2026-08-02 12:54:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e8f9a2b3c4d5"
down_revision: str | None = "c7a41e92d830"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "git_contributions" not in inspector.get_table_names():
        op.create_table(
            "git_contributions",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("member_key", sa.Text(), nullable=False),
            sa.Column("display_name", sa.Text(), nullable=False),
            sa.Column("canonical_email", sa.Text(), nullable=False),
            sa.Column("commit_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
            sa.Column("lines_added", sa.Integer(), server_default=sa.text("0"), nullable=False),
            sa.Column("lines_deleted", sa.Integer(), server_default=sa.text("0"), nullable=False),
            sa.Column("total_loc_changes", sa.Integer(), server_default=sa.text("0"), nullable=False),
            sa.Column("last_commit_hash", sa.Text(), nullable=True),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_git_contributions_member_key"),
            "git_contributions",
            ["member_key"],
            unique=True,
        )


def downgrade() -> None:
    op.drop_index(op.f("ix_git_contributions_member_key"), table_name="git_contributions")
    op.drop_table("git_contributions")

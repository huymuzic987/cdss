"""Merge the Git history and regimen decision migration branches.

Revision ID: f2a3b4c5d6e7
Revises: c8d9e0f1a2b3, d4e5f6a7b8c9
"""

from collections.abc import Sequence

revision: str = "f2a3b4c5d6e7"
down_revision: str | Sequence[str] | None = ("c8d9e0f1a2b3", "d4e5f6a7b8c9")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Join both migration branches without changing the database."""


def downgrade() -> None:
    """Allow Alembic to return to either branch head."""

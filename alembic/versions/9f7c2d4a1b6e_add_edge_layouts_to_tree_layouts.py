"""add edge layouts to tree layouts

Revision ID: 9f7c2d4a1b6e
Revises: b79e1f82c031
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "9f7c2d4a1b6e"
down_revision: str | None = "b79e1f82c031"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "tree_layouts",
        sa.Column(
            "edge_layouts",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("tree_layouts", "edge_layouts")

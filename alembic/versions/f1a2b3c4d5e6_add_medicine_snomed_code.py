"""add medicine SNOMED CT code

Revision ID: f1a2b3c4d5e6
Revises: e8f9a2b3c4d5
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f1a2b3c4d5e6"
down_revision: str | None = "e8f9a2b3c4d5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col["name"] for col in inspector.get_columns("medicines")]
    if "snomed_code" not in columns:
        op.add_column("medicines", sa.Column("snomed_code", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("medicines", "snomed_code")

"""create tree layouts table

Revision ID: 4da35a974155
Revises: 68b4b4838af0
Create Date: 2026-07-25 22:43:51.644749

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '4da35a974155'
down_revision: str | None = '68b4b4838af0'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'tree_layouts',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tree_id', sa.UUID(), nullable=False),
        sa.Column('arrow_kind', sa.Text(), server_default=sa.text("'elbow'"), nullable=False),
        sa.Column(
            'node_positions',
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("arrow_kind IN ('straight', 'elbow')", name='ck_tree_layouts_arrow_kind'),
        sa.ForeignKeyConstraint(['tree_id'], ['decision_trees.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tree_id', name='uq_tree_layouts_tree_id'),
    )


def downgrade() -> None:
    op.drop_table('tree_layouts')

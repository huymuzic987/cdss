"""create medicines table

Revision ID: 8cd7e7adc1fb
Revises: 5c43058f54be
Create Date: 2026-07-19 00:00:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '8cd7e7adc1fb'
down_revision: str | None = '5c43058f54be'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('medicines',
    sa.Column('drug_id', sa.Text(), nullable=False),
    sa.Column('name', sa.Text(), nullable=False),
    sa.Column('drug_class', sa.Text(), nullable=True),
    sa.Column('subgroup', sa.Text(), nullable=True),
    sa.Column('route', sa.Text(), nullable=True),
    sa.Column('dose_low', sa.Text(), nullable=True),
    sa.Column('dose_usual', sa.Text(), nullable=True),
    sa.Column('dose_max', sa.Text(), nullable=True),
    sa.Column('source', sa.Text(), nullable=True),
    sa.Column('link', sa.Text(), nullable=True),
    sa.Column('available', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.PrimaryKeyConstraint('drug_id')
    )
    op.create_index('ix_medicines_drug_class', 'medicines', ['drug_class'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_medicines_drug_class', table_name='medicines')
    op.drop_table('medicines')

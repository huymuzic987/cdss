"""create symptoms table

Revision ID: b79e1f82c031
Revises: 425debaec093
Create Date: 2026-07-26 23:20:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b79e1f82c031'
down_revision: str | None = '425debaec093'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'symptoms',
        sa.Column('symptom_id', sa.Text(), nullable=False),
        sa.Column('type', sa.Text(), nullable=True),
        sa.Column('subgroup', sa.Text(), nullable=True),
        sa.Column('name_vn', sa.Text(), nullable=False),
        sa.Column('name_en', sa.Text(), nullable=True),
        sa.Column('description_vn', sa.Text(), nullable=True),
        sa.Column('description_en', sa.Text(), nullable=True),
        sa.Column('source', sa.Text(), nullable=True),
        sa.Column('icd10_code', sa.Text(), nullable=True),
        sa.Column('snomed_code', sa.Text(), nullable=True),
        sa.Column('loinc_code', sa.Text(), nullable=True),
        sa.Column('loinc_common_name', sa.Text(), nullable=True),
        sa.Column('decision_tree_vn', sa.Text(), nullable=True),
        sa.Column('decision_tree_en', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('symptom_id'),
    )
    op.create_index('ix_symptoms_type', 'symptoms', ['type'], unique=False)
    op.create_index('ix_symptoms_subgroup', 'symptoms', ['subgroup'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_symptoms_subgroup', table_name='symptoms')
    op.drop_index('ix_symptoms_type', table_name='symptoms')
    op.drop_table('symptoms')

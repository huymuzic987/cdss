"""create drug contraindication reference table

Revision ID: a6b7c8d9e0f1
Revises: f1a2b3c4d5e6
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "a6b7c8d9e0f1"
down_revision: str | None = "f1a2b3c4d5e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "contraindication_drugs",
        sa.Column("contraindication_id", sa.Text(), nullable=False),
        sa.Column("disease_finding_vn", sa.Text(), nullable=False),
        sa.Column("disease_finding_eng", sa.Text(), nullable=False),
        sa.Column("contraindication_type", sa.Text(), nullable=False),
        sa.Column("drug_group", sa.Text(), nullable=False),
        sa.Column("drugs", sa.Text(), nullable=True),
        sa.Column("icd10_vn_1_decimal", sa.Text(), nullable=True),
        sa.Column("snomedct_2026_06_01", sa.Text(), nullable=True),
        sa.Column("target", sa.Text(), nullable=False),
        sa.Column("finding_key", sa.Text(), nullable=False),
        sa.Column("fact_key", sa.Text(), nullable=True),
        sa.Column("operator", sa.Text(), nullable=True),
        sa.Column("threshold", sa.Float(), nullable=True),
        sa.CheckConstraint(
            "contraindication_type IN ('absolute', 'relative')",
            name="ck_contraindication_drugs_type",
        ),
        sa.PrimaryKeyConstraint("contraindication_id"),
    )
    op.create_index(
        "ix_contraindication_drugs_target",
        "contraindication_drugs",
        ["target"],
        unique=False,
    )
    op.create_index(
        "ix_contraindication_drugs_icd10",
        "contraindication_drugs",
        ["icd10_vn_1_decimal"],
        unique=False,
    )
    op.create_index(
        "ix_contraindication_drugs_snomed",
        "contraindication_drugs",
        ["snomedct_2026_06_01"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_contraindication_drugs_snomed", table_name="contraindication_drugs")
    op.drop_index("ix_contraindication_drugs_icd10", table_name="contraindication_drugs")
    op.drop_index("ix_contraindication_drugs_target", table_name="contraindication_drugs")
    op.drop_table("contraindication_drugs")

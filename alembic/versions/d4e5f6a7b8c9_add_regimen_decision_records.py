"""Add auditable clinician regimen decisions.

Revision ID: d4e5f6a7b8c9
Revises: b7c8d9e0f1a2
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "d4e5f6a7b8c9"
down_revision: str | None = "b7c8d9e0f1a2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "regimen_decisions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("patient_fhir_id", sa.Text(), nullable=False),
        sa.Column("encounter_fhir_id", sa.Text(), nullable=True),
        sa.Column("patient_id", sa.UUID(), nullable=True),
        sa.Column("visit_id", sa.UUID(), nullable=True),
        sa.Column("outcome", sa.Text(), nullable=False),
        sa.Column("evaluation_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("baseline_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("final_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "outcome IN ('accepted', 'rejected')",
            name="ck_regimen_decisions_outcome",
        ),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["visit_id"], ["visits.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_regimen_decisions_patient_fhir_id", "regimen_decisions", ["patient_fhir_id"]
    )
    op.create_index(
        "ix_regimen_decisions_encounter_fhir_id", "regimen_decisions", ["encounter_fhir_id"]
    )
    op.create_index("ix_regimen_decisions_created_at", "regimen_decisions", ["created_at"])

    op.create_table(
        "regimen_clinical_plan_items",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("decision_id", sa.UUID(), nullable=False),
        sa.Column("item_order", sa.Integer(), nullable=False),
        sa.Column("item_type", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.CheckConstraint(
            "item_type IN ('NEXT_FOLLOW_UP', 'TARGET_BP', 'ELSE')",
            name="ck_regimen_clinical_plan_items_type",
        ),
        sa.ForeignKeyConstraint(["decision_id"], ["regimen_decisions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("decision_id", "item_order", name="uq_regimen_clinical_plan_items_order"),
    )
    op.create_index(
        "ix_regimen_clinical_plan_items_decision_id",
        "regimen_clinical_plan_items",
        ["decision_id"],
    )

    op.create_table(
        "regimen_options",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("decision_id", sa.UUID(), nullable=False),
        sa.Column("item_order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["decision_id"], ["regimen_decisions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("decision_id", "item_order", name="uq_regimen_options_order"),
    )
    op.create_index("ix_regimen_options_decision_id", "regimen_options", ["decision_id"])

    op.create_table(
        "regimen_option_components",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("option_id", sa.UUID(), nullable=False),
        sa.Column("item_order", sa.Integer(), nullable=False),
        sa.Column("selector_kind", sa.Text(), nullable=False),
        sa.Column("group_code", sa.Text(), nullable=False),
        sa.Column("subgroup", sa.Text(), nullable=True),
        sa.Column("medicine_id", sa.Text(), nullable=True),
        sa.Column("dose_strategy", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "selector_kind IN ('group', 'subgroup', 'medicine')",
            name="ck_regimen_option_components_selector_kind",
        ),
        sa.CheckConstraint(
            "dose_strategy IN ('LOW_DOSE', 'USUAL_DOSE', 'MAX_DOSE')",
            name="ck_regimen_option_components_dose_strategy",
        ),
        sa.ForeignKeyConstraint(["medicine_id"], ["medicines.drug_id"]),
        sa.ForeignKeyConstraint(["option_id"], ["regimen_options.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("option_id", "item_order", name="uq_regimen_option_components_order"),
    )
    op.create_index(
        "ix_regimen_option_components_option_id",
        "regimen_option_components",
        ["option_id"],
    )
    op.create_index(
        "ix_regimen_option_components_medicine_id",
        "regimen_option_components",
        ["medicine_id"],
    )

    op.create_table(
        "regimen_rejection_reasons",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("decision_id", sa.UUID(), nullable=False),
        sa.Column("item_order", sa.Integer(), nullable=False),
        sa.Column("reason_code", sa.Text(), nullable=False),
        sa.Column("other_text", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["decision_id"], ["regimen_decisions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("decision_id", "reason_code", name="uq_regimen_rejection_reasons_code"),
    )
    op.create_index(
        "ix_regimen_rejection_reasons_decision_id",
        "regimen_rejection_reasons",
        ["decision_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_regimen_rejection_reasons_decision_id", table_name="regimen_rejection_reasons")
    op.drop_table("regimen_rejection_reasons")
    op.drop_index("ix_regimen_option_components_medicine_id", table_name="regimen_option_components")
    op.drop_index("ix_regimen_option_components_option_id", table_name="regimen_option_components")
    op.drop_table("regimen_option_components")
    op.drop_index("ix_regimen_options_decision_id", table_name="regimen_options")
    op.drop_table("regimen_options")
    op.drop_index(
        "ix_regimen_clinical_plan_items_decision_id",
        table_name="regimen_clinical_plan_items",
    )
    op.drop_table("regimen_clinical_plan_items")
    op.drop_index("ix_regimen_decisions_created_at", table_name="regimen_decisions")
    op.drop_index("ix_regimen_decisions_encounter_fhir_id", table_name="regimen_decisions")
    op.drop_index("ix_regimen_decisions_patient_fhir_id", table_name="regimen_decisions")
    op.drop_table("regimen_decisions")

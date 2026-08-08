"""SQLAlchemy models for clinician-authored regimen decisions."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cdss.infrastructure.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class RegimenDecision(Base):
    __tablename__ = "regimen_decisions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    patient_fhir_id: Mapped[str] = mapped_column(Text, nullable=False)
    encounter_fhir_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    patient_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id", ondelete="SET NULL"), nullable=True
    )
    visit_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("visits.id", ondelete="SET NULL"), nullable=True
    )
    outcome: Mapped[str] = mapped_column(Text, nullable=False)
    evaluation_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    baseline_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    final_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    __table_args__ = (
        CheckConstraint(
            "outcome IN ('accepted', 'rejected')",
            name="ck_regimen_decisions_outcome",
        ),
    )

    clinical_plan_items: Mapped[list[RegimenClinicalPlanItem]] = relationship(
        back_populates="decision",
        cascade="all, delete-orphan",
        order_by="RegimenClinicalPlanItem.item_order",
    )
    options: Mapped[list[RegimenOption]] = relationship(
        back_populates="decision", cascade="all, delete-orphan", order_by="RegimenOption.item_order"
    )
    rejection_reasons: Mapped[list[RegimenRejectionReason]] = relationship(
        back_populates="decision",
        cascade="all, delete-orphan",
        order_by="RegimenRejectionReason.item_order",
    )


class RegimenClinicalPlanItem(Base):
    __tablename__ = "regimen_clinical_plan_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    decision_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("regimen_decisions.id", ondelete="CASCADE"), nullable=False
    )
    item_order: Mapped[int] = mapped_column(Integer, nullable=False)
    item_type: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "item_type IN ('NEXT_FOLLOW_UP', 'TARGET_BP', 'ELSE')",
            name="ck_regimen_clinical_plan_items_type",
        ),
        UniqueConstraint("decision_id", "item_order", name="uq_regimen_clinical_plan_items_order"),
        Index("ix_regimen_clinical_plan_items_decision_id", "decision_id"),
    )

    decision: Mapped[RegimenDecision] = relationship(back_populates="clinical_plan_items")


class RegimenOption(Base):
    __tablename__ = "regimen_options"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    decision_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("regimen_decisions.id", ondelete="CASCADE"), nullable=False
    )
    item_order: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint("decision_id", "item_order", name="uq_regimen_options_order"),
        Index("ix_regimen_options_decision_id", "decision_id"),
    )

    decision: Mapped[RegimenDecision] = relationship(back_populates="options")
    components: Mapped[list[RegimenOptionComponent]] = relationship(
        back_populates="option",
        cascade="all, delete-orphan",
        order_by="RegimenOptionComponent.item_order",
    )


class RegimenOptionComponent(Base):
    __tablename__ = "regimen_option_components"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    option_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("regimen_options.id", ondelete="CASCADE"), nullable=False
    )
    item_order: Mapped[int] = mapped_column(Integer, nullable=False)
    selector_kind: Mapped[str] = mapped_column(Text, nullable=False)
    group_code: Mapped[str] = mapped_column(Text, nullable=False)
    subgroup: Mapped[str | None] = mapped_column(Text, nullable=True)
    medicine_id: Mapped[str | None] = mapped_column(
        Text, ForeignKey("medicines.drug_id"), nullable=True
    )
    dose_strategy: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "selector_kind IN ('group', 'subgroup', 'medicine')",
            name="ck_regimen_option_components_selector_kind",
        ),
        CheckConstraint(
            "dose_strategy IN ('LOW_DOSE', 'USUAL_DOSE', 'MAX_DOSE')",
            name="ck_regimen_option_components_dose_strategy",
        ),
        UniqueConstraint("option_id", "item_order", name="uq_regimen_option_components_order"),
        Index("ix_regimen_option_components_option_id", "option_id"),
        Index("ix_regimen_option_components_medicine_id", "medicine_id"),
    )

    option: Mapped[RegimenOption] = relationship(back_populates="components")


class RegimenRejectionReason(Base):
    __tablename__ = "regimen_rejection_reasons"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    decision_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("regimen_decisions.id", ondelete="CASCADE"), nullable=False
    )
    item_order: Mapped[int] = mapped_column(Integer, nullable=False)
    reason_code: Mapped[str] = mapped_column(Text, nullable=False)
    other_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("decision_id", "reason_code", name="uq_regimen_rejection_reasons_code"),
        Index("ix_regimen_rejection_reasons_decision_id", "decision_id"),
    )

    decision: Mapped[RegimenDecision] = relationship(back_populates="rejection_reasons")

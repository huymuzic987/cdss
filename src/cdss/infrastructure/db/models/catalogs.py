"""SQLAlchemy models for runtime logs, medicine, symptom, and contraindication catalogs."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    Index,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from cdss.infrastructure.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class DevelopmentRuntimeLog(Base):
    __tablename__ = "development_runtime_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    environment: Mapped[str] = mapped_column(Text, nullable=False)
    input_payload: Mapped[Any] = mapped_column(JSONB, nullable=False)
    inference_context: Mapped[Any] = mapped_column(JSONB, nullable=False)
    journey: Mapped[Any] = mapped_column(JSONB, nullable=False)
    output_payload: Mapped[Any | None] = mapped_column(JSONB, nullable=True)
    error_payload: Mapped[Any | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    __table_args__ = (
        CheckConstraint(
            "environment IN ('development', 'test')",
            name="ck_development_runtime_logs_environment",
        ),
        Index("ix_development_runtime_logs_request_id", "request_id"),
        Index("ix_development_runtime_logs_created_at", "created_at"),
    )


class Medicine(Base):
    __tablename__ = "medicines"

    drug_id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    drug_class: Mapped[str | None] = mapped_column(Text, nullable=True)
    subgroup: Mapped[str | None] = mapped_column(Text, nullable=True)
    route: Mapped[str | None] = mapped_column(Text, nullable=True)
    dose_low: Mapped[str | None] = mapped_column(Text, nullable=True)
    dose_usual: Mapped[str | None] = mapped_column(Text, nullable=True)
    dose_max: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str | None] = mapped_column(Text, nullable=True)
    link: Mapped[str | None] = mapped_column(Text, nullable=True)
    available: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    atc_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    snomed_code: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (Index("ix_medicines_drug_class", "drug_class"),)


class Symptom(Base):
    __tablename__ = "symptoms"

    symptom_id: Mapped[str] = mapped_column(Text, primary_key=True)
    type: Mapped[str | None] = mapped_column(Text, nullable=True)
    subgroup: Mapped[str | None] = mapped_column(Text, nullable=True)
    name_vn: Mapped[str] = mapped_column(Text, nullable=False)
    name_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    description_vn: Mapped[str | None] = mapped_column(Text, nullable=True)
    description_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str | None] = mapped_column(Text, nullable=True)
    icd10_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    snomed_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    loinc_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    loinc_common_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    decision_tree_vn: Mapped[str | None] = mapped_column(Text, nullable=True)
    decision_tree_en: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_symptoms_type", "type"),
        Index("ix_symptoms_subgroup", "subgroup"),
    )


class ContraindicationDrug(Base):
    __tablename__ = "contraindication_drugs"

    contraindication_id: Mapped[str] = mapped_column(Text, primary_key=True)
    disease_finding_vn: Mapped[str] = mapped_column(Text, nullable=False)
    disease_finding_eng: Mapped[str] = mapped_column(Text, nullable=False)
    contraindication_type: Mapped[str] = mapped_column(Text, nullable=False)
    drug_group: Mapped[str] = mapped_column(Text, nullable=False)
    drugs: Mapped[str | None] = mapped_column(Text, nullable=True)
    icd10_vn_1_decimal: Mapped[str | None] = mapped_column(Text, nullable=True)
    snomedct_2026_06_01: Mapped[str | None] = mapped_column(Text, nullable=True)
    target: Mapped[str] = mapped_column(Text, nullable=False)
    finding_key: Mapped[str] = mapped_column(Text, nullable=False)
    fact_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    operator: Mapped[str | None] = mapped_column(Text, nullable=True)
    threshold: Mapped[float | None] = mapped_column(Float, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "contraindication_type IN ('absolute', 'relative')",
            name="ck_contraindication_drugs_type",
        ),
        Index("ix_contraindication_drugs_target", "target"),
        Index("ix_contraindication_drugs_icd10", "icd10_vn_1_decimal"),
        Index("ix_contraindication_drugs_snomed", "snomedct_2026_06_01"),
    )

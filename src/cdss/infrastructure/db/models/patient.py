"""SQLAlchemy models for Patient, Condition, Visit, Observation, and Medication records."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cdss.infrastructure.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fhir_id: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    gender: Mapped[str | None] = mapped_column(Text, nullable=True)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    risk_factor_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    department: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    visits: Mapped[list[Visit]] = relationship(
        back_populates="patient", order_by="Visit.visit_number"
    )
    conditions: Mapped[list[PatientCondition]] = relationship(back_populates="patient")


class PatientCondition(Base):
    __tablename__ = "patient_conditions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False
    )
    fhir_condition_id: Mapped[str] = mapped_column(Text, nullable=False)
    icd10_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    snomed_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    condition_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    __table_args__ = (
        UniqueConstraint(
            "patient_id", "fhir_condition_id", name="uq_patient_conditions_patient_id_fhir_id"
        ),
        Index("ix_patient_conditions_patient_id", "patient_id"),
        Index("ix_patient_conditions_icd10_code", "icd10_code"),
    )

    patient: Mapped[Patient] = relationship(back_populates="conditions")


class Visit(Base):
    __tablename__ = "visits"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False
    )
    fhir_encounter_id: Mapped[str] = mapped_column(Text, nullable=False, unique=True)

    visit_number: Mapped[int] = mapped_column(Integer, nullable=False)
    visit_date: Mapped[date] = mapped_column(Date, nullable=False)
    facility_capability: Mapped[str | None] = mapped_column(Text, nullable=True)

    is_early_revisit: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    early_revisit_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    scheduled_next_visit_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    clinic_sbp: Mapped[int | None] = mapped_column(Integer, nullable=True)
    clinic_dbp: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bp_target_sbp: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bp_target_dbp: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bp_controlled: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    hypertension_class: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_level: Mapped[str | None] = mapped_column(Text, nullable=True)

    cdss_recommended_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    adherent_to_cdss: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    __table_args__ = (
        UniqueConstraint("patient_id", "visit_number", name="uq_visits_patient_id_visit_number"),
        Index("ix_visits_patient_id", "patient_id"),
        Index("ix_visits_visit_date", "visit_date"),
    )

    patient: Mapped[Patient] = relationship(back_populates="visits")
    observations: Mapped[list[VisitObservation]] = relationship(back_populates="visit")
    medications: Mapped[list[VisitMedication]] = relationship(back_populates="visit")


class VisitObservation(Base):
    __tablename__ = "visit_observations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    visit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("visits.id"), nullable=False
    )
    loinc_code: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    __table_args__ = (
        Index("ix_visit_observations_visit_id", "visit_id"),
        Index("ix_visit_observations_loinc_code", "loinc_code"),
    )

    visit: Mapped[Visit] = relationship(back_populates="observations")


class VisitMedication(Base):
    __tablename__ = "visit_medications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    visit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("visits.id"), nullable=False
    )
    drug_id: Mapped[str | None] = mapped_column(
        Text, ForeignKey("medicines.drug_id"), nullable=True
    )
    drug_name: Mapped[str] = mapped_column(Text, nullable=False)
    drug_class_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    dose_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    dose_unit: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    __table_args__ = (
        Index("ix_visit_medications_visit_id", "visit_id"),
        Index("ix_visit_medications_drug_id", "drug_id"),
    )

    visit: Mapped[Visit] = relationship(back_populates="medications")


class FhirImportBatch(Base):
    __tablename__ = "fhir_import_batches"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_label: Mapped[str] = mapped_column(Text, nullable=False)
    patient_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    visit_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    errors: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )


class GitContribution(Base):
    __tablename__ = "git_contributions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    member_key: Mapped[str] = mapped_column(Text, nullable=False, unique=True, index=True)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_email: Mapped[str] = mapped_column(Text, nullable=False)
    commit_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    lines_added: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    lines_deleted: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    total_loc_changes: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    last_commit_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )


class GitCommitHistory(Base):
    __tablename__ = "git_commit_history"

    commit_hash: Mapped[str] = mapped_column(Text, primary_key=True)
    author: Mapped[str] = mapped_column(Text, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    committed_at: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    member_keys: Mapped[list[str]] = mapped_column(JSONB, nullable=False)

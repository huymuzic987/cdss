"""SQLAlchemy ORM models for the decision-tree schema.

Twenty-one tables: decision_trees, decision_nodes, decision_edges,
node_source_references, tree_layouts, development_runtime_logs, medicines,
contraindication_drugs,
patients, patient_conditions, visits, visit_observations, visit_medications,
fhir_import_batches, regimen decision records and their child rows.
medicines is a static drug reference catalog (with an
ATC code column for the future drugs-table integration). patients/
patient_conditions/visits/visit_observations/visit_medications/
fhir_import_batches hold clinical data imported from FHIR R4 bundles for the
statistics dashboard. Condition/Observation coded identifiers (ICD-10,
SNOMED CT, LOINC) are stored as plain string columns rather than foreign
keys, since the planned `diseases`/findings reference table doesn't exist
yet -- joining on those codes once it does is additive, not a migration.
``contraindication_drugs`` is a static drug-disease/finding safety catalog.
"""

from __future__ import annotations

import enum
import uuid
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, ENUM, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cdss.infrastructure.db.base import Base


class NodeType(enum.Enum):
    START = "START"
    CONDITION = "CONDITION"
    INFERENCE = "INFERENCE"
    ACTION = "ACTION"
    END = "END"
    LINK = "LINK"
    GLOBAL = "GLOBAL"


def _utcnow() -> datetime:
    return datetime.now(UTC)


class DecisionTree(Base):
    __tablename__ = "decision_trees"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tree_key: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    name_en: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    name_vi: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    nodes: Mapped[list[DecisionNode]] = relationship(back_populates="tree")


class DecisionNode(Base):
    __tablename__ = "decision_nodes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tree_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("decision_trees.id"), nullable=False
    )
    node_key: Mapped[str] = mapped_column(Text, nullable=False)
    node_type: Mapped[NodeType] = mapped_column(ENUM(NodeType, name="node_type"), nullable=False)

    text_en: Mapped[str] = mapped_column(Text, nullable=False)
    text_vi: Mapped[str] = mapped_column(Text, nullable=False)

    condition_definition: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    context_patch: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    action_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    global_config: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    link_target_tree_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    link_target_node_key: Mapped[str | None] = mapped_column(Text, nullable=True)

    display_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    __table_args__ = (
        UniqueConstraint("tree_id", "node_key", name="uq_decision_nodes_tree_id_node_key"),
    )

    tree: Mapped[DecisionTree] = relationship(back_populates="nodes")
    outgoing_edges: Mapped[list[DecisionEdge]] = relationship(
        back_populates="from_node", foreign_keys="DecisionEdge.from_node_id"
    )
    incoming_edges: Mapped[list[DecisionEdge]] = relationship(
        back_populates="to_node", foreign_keys="DecisionEdge.to_node_id"
    )
    source_references: Mapped[list[NodeSourceReference]] = relationship(
        back_populates="decision_node"
    )


class DecisionEdge(Base):
    __tablename__ = "decision_edges"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    from_node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("decision_nodes.id"), nullable=False
    )
    to_node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("decision_nodes.id"), nullable=False
    )
    traversal_order: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint("from_node_id", "to_node_id", name="uq_decision_edges_from_to"),
        UniqueConstraint(
            "from_node_id", "traversal_order", name="uq_decision_edges_from_traversal_order"
        ),
        Index("ix_decision_edges_from_node_id", "from_node_id"),
        Index("ix_decision_edges_to_node_id", "to_node_id"),
    )

    from_node: Mapped[DecisionNode] = relationship(
        back_populates="outgoing_edges", foreign_keys=[from_node_id]
    )
    to_node: Mapped[DecisionNode] = relationship(
        back_populates="incoming_edges", foreign_keys=[to_node_id]
    )


class NodeSourceReference(Base):
    __tablename__ = "node_source_references"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("decision_nodes.id"), nullable=False
    )

    source_title: Mapped[str] = mapped_column(Text, nullable=False)
    section_path: Mapped[Any] = mapped_column(JSONB, nullable=False)

    locator: Mapped[str | None] = mapped_column(Text, nullable=True)
    locator_detail: Mapped[str | None] = mapped_column(Text, nullable=True)

    printed_page_numbers: Mapped[list[int] | None] = mapped_column(
        ARRAY(SmallInteger), nullable=True
    )
    pdf_page_numbers: Mapped[list[int] | None] = mapped_column(ARRAY(SmallInteger), nullable=True)

    reference_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    reference_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))

    __table_args__ = (
        UniqueConstraint(
            "node_id", "reference_order", name="uq_node_source_references_node_id_reference_order"
        ),
        Index("ix_node_source_references_node_id", "node_id"),
    )

    decision_node: Mapped[DecisionNode] = relationship(back_populates="source_references")


class TreeLayout(Base):
    """Editor-canvas layout for a tree: per-node (x, y) position plus the
    connector style, keyed one-to-one with ``decision_trees``. Replaces the
    browser-localStorage persistence the tldraw canvas used previously, so
    layouts are shared across users/machines instead of per-browser.

    ``node_positions`` stays a JSONB blob keyed by ``node_key`` (not a
    normalized per-node table) because it is always read and written as one
    whole object by the canvas -- never queried per node -- and this way a
    node renamed/removed from ``decision_nodes`` leaves a harmless stale key
    rather than an orphaned row; the frontend already tolerates missing/extra
    keys when merging against the auto-computed layout.
    """

    __tablename__ = "tree_layouts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tree_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("decision_trees.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    arrow_kind: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'elbow'"))
    node_positions: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    edge_layouts: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    __table_args__ = (
        CheckConstraint("arrow_kind IN ('straight', 'elbow')", name="ck_tree_layouts_arrow_kind"),
    )


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
    """Static drug reference catalog (name, dose, source), seeded from
    backups/medicines.sql. Not patient data -- no encounter, patient, or
    prescription rows exist anywhere in this schema."""

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
    # ATC (Anatomical Therapeutic Chemical) classification code -- nullable until
    # the catalog is backfilled. Plain string column, not a FK: there is no ATC
    # reference table in this schema, just the code itself for future lookups.
    atc_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    snomed_code: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (Index("ix_medicines_drug_class", "drug_class"),)


class Symptom(Base):
    """Static symptoms reference catalog, seeded from backups/seed.sql."""

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
    """Static drug contraindication catalog, seeded from the VNHA CSV.

    The first seven fields mirror the source CSV. ``target`` and the optional
    fact/comparison fields are normalized execution metadata so the runtime
    does not have to interpret Vietnamese drug-group labels or hard-code every
    catalog row.
    """

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


class Patient(Base):
    """A patient imported from a FHIR R4 Patient resource.

    ``fhir_id`` is the Patient.id from the source bundle and is how re-imports
    upsert rather than duplicate. ``department`` mirrors the source data's
    ai4life department extension (e.g. "Nội tim mạch").
    """

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
    """A diagnosis imported from a FHIR Condition resource.

    Stores the coded identifiers (ICD-10, SNOMED CT) as plain string columns
    rather than a foreign key, since the future ``diseases`` reference table
    (name/description/ICD-10/SNOMED/LOINC catalog) doesn't exist yet. Once it
    does, joining on ``icd10_code`` (or adding a ``disease_id`` FK backfilled
    from it) is a one-column addition, not a data migration.
    """

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
    """One encounter (initial diagnosis or follow-up) imported from a FHIR
    Encounter + its linked Observation/MedicationRequest resources. A source
    bundle with no Encounter at all (a single-snapshot record, as produced by
    real-world exports) is imported as an implicit visit_number=1.

    ``cdss_recommended_action`` is the treatment strategy the CDSS engine
    would recommend at this visit; the actual medications given are in
    ``VisitMedication``. ``adherent_to_cdss`` flags whether the clinician
    followed the recommendation, which is what the efficacy dashboard
    compares outcomes against.
    """

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
    """A lab/vital reading imported from a FHIR Observation resource, keyed
    by LOINC code. Blood pressure (SBP/DBP) is special-cased onto dedicated
    ``Visit`` columns since almost every dashboard stat needs it; everything
    else (eGFR, potassium, future labs) lands here generically so new
    observation types never require a schema migration. ``loinc_code`` is a
    plain string column for the same forward-compatibility reason as
    ``PatientCondition.icd10_code`` -- joins to the future diseases/findings
    catalog by code, not by FK.
    """

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
    """An actual medication given at a visit, imported from a FHIR
    MedicationRequest resource. ``drug_id`` links to the existing
    ``medicines`` catalog when the name matches; ``drug_name`` is kept
    denormalized so an unmatched drug (not yet in the catalog) isn't lost.
    """

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
    """Audit record of one FHIR bundle import (preset or synthetic seed)."""

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
    """Pre-calculated contribution statistics per team member."""

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


class RegimenDecision(Base):
    """An auditable clinician decision made from one stateless evaluation."""

    __tablename__ = "regimen_decisions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
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
        Index("ix_regimen_decisions_patient_fhir_id", "patient_fhir_id"),
        Index("ix_regimen_decisions_encounter_fhir_id", "encounter_fhir_id"),
        Index("ix_regimen_decisions_created_at", "created_at"),
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

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
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

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
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

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
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

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
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

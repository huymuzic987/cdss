"""Persistence boundary for clinician-authored regimen decisions."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from cdss.api.schemas.regimen_decisions import RegimenDecisionCreateRequest
from cdss.domain.decision_tree.medicine_catalog import Medicine
from cdss.infrastructure.db.models import (
    Patient,
    RegimenClinicalPlanItem,
    RegimenDecision,
    RegimenOption,
    RegimenOptionComponent,
    RegimenRejectionReason,
    Visit,
)
from cdss.infrastructure.db.regimen_decision_validation import (
    RegimenDecisionValidationError,
    parse_evaluation_snapshot,
    validate_rejection_reasons,
    validate_snapshot,
)


def create_regimen_decision(
    session: Session, request: RegimenDecisionCreateRequest, catalog: Sequence[Medicine]
) -> RegimenDecision:
    parsed = parse_evaluation_snapshot(request.evaluation_snapshot)
    validate_snapshot(request.baseline, catalog, label="baseline")
    if request.outcome == "accepted":
        if request.final is not None:
            raise RegimenDecisionValidationError(
                "Accepted decisions must not include a custom final."
            )
        final = request.baseline
        if request.rejection_reasons or request.other_rejection_reason:
            raise RegimenDecisionValidationError(
                "Accepted decisions cannot include rejection reasons."
            )
    else:
        if request.final is None:
            raise RegimenDecisionValidationError(
                "Rejected decisions require a custom final regimen."
            )
        final = request.final
        validate_snapshot(final, catalog, label="final")
        validate_rejection_reasons(request)

    patient = session.execute(
        select(Patient).where(Patient.fhir_id == parsed.patient_id)
    ).scalar_one_or_none()
    encounter_id = parsed.encounter_ids[-1] if parsed.encounter_ids else None
    visit = (
        session.execute(
            select(Visit).where(Visit.fhir_encounter_id == encounter_id)
        ).scalar_one_or_none()
        if encounter_id
        else None
    )
    decision = RegimenDecision(
        id=uuid.uuid4(),
        patient_fhir_id=parsed.patient_id,
        encounter_fhir_id=encounter_id,
        patient_id=patient.id if patient else None,
        visit_id=visit.id if visit else None,
        outcome=request.outcome,
        evaluation_snapshot=dict(request.evaluation_snapshot),
        baseline_snapshot=request.baseline.model_dump(mode="json"),
        final_snapshot=final.model_dump(mode="json"),
    )
    session.add(decision)
    _add_plan_rows(session, decision, final)
    _add_option_rows(session, decision, final)
    _add_reason_rows(session, decision, request)
    session.commit()
    return decision


def _add_plan_rows(session: Session, decision: RegimenDecision, final) -> None:
    for index, item in enumerate(final.clinical_plan):
        session.add(
            RegimenClinicalPlanItem(
                id=uuid.uuid4(),
                decision=decision,
                item_order=index,
                item_type=item.type,
                payload=item.model_dump(mode="json"),
            )
        )


def _add_option_rows(session: Session, decision: RegimenDecision, final) -> None:
    for option_index, option in enumerate(final.regimen_options):
        option_row = RegimenOption(id=uuid.uuid4(), decision=decision, item_order=option_index)
        session.add(option_row)
        for component_index, component in enumerate(option.components):
            session.add(
                RegimenOptionComponent(
                    id=uuid.uuid4(),
                    option=option_row,
                    item_order=component_index,
                    selector_kind=component.selector_kind,
                    group_code=component.group_code,
                    subgroup=component.subgroup,
                    medicine_id=component.medicine_id,
                    dose_strategy=component.dose_strategy,
                )
            )


def _add_reason_rows(
    session: Session, decision: RegimenDecision, request: RegimenDecisionCreateRequest
) -> None:
    if request.outcome != "rejected":
        return
    for index, reason in enumerate(request.rejection_reasons):
        session.add(
            RegimenRejectionReason(
                id=uuid.uuid4(),
                decision=decision,
                item_order=index,
                reason_code=reason,
                other_text=request.other_rejection_reason.strip()
                if reason == "OTHER" and request.other_rejection_reason
                else None,
            )
        )

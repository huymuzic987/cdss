"""Unit coverage for clinician-authored regimen decision validation."""

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from cdss.api.schemas.regimen_decisions import (
    ClinicalPlanItemInput,
    RegimenComponentSelection,
    RegimenDecisionCreateRequest,
    RegimenOptionInput,
    RegimenSnapshotInput,
)
from cdss.domain.decision_tree.medicine_catalog import Medicine
from cdss.infrastructure.db.regimen_decision_service import (
    RegimenDecisionValidationError,
    create_regimen_decision,
)


def _evaluation_snapshot() -> dict:
    bundle = json.loads(Path("data/fhir/test_case/PT0001.json").read_text(encoding="utf-8"))
    return {"input_snapshot": bundle}


def _catalog() -> list[Medicine]:
    return [
        Medicine(
            drug_id="DRUG0003",
            name="Amlodipine",
            drug_class="C",
            subgroup="CKCa DHP",
            route="oral",
            dose_low="2.5 mg",
            dose_usual="5 mg",
            dose_max="10 mg",
            source="seed",
            link=None,
            available=True,
        )
    ]


def _session() -> Mock:
    session = Mock()
    session.execute.return_value.scalar_one_or_none.return_value = None
    return session


def test_accepted_decision_persists_baseline_and_fhir_identifier() -> None:
    baseline = RegimenSnapshotInput(
        clinical_plan=[ClinicalPlanItemInput(type="ELSE", text="Continue monitoring.")],
        regimen_options=[
            RegimenOptionInput(
                components=[
                    RegimenComponentSelection(
                        selector_kind="medicine",
                        group_code="C",
                        subgroup="CKCa DHP",
                        medicine_id="DRUG0003",
                    )
                ]
            )
        ],
    )
    request = RegimenDecisionCreateRequest(
        outcome="accepted",
        evaluation_snapshot=_evaluation_snapshot(),
        baseline=baseline,
    )

    decision = create_regimen_decision(_session(), request, _catalog())

    assert decision.outcome == "accepted"
    assert decision.patient_fhir_id == "PT0001"
    assert decision.final_snapshot == baseline.model_dump(mode="json")


def test_rejected_other_reason_requires_fifty_words() -> None:
    request = RegimenDecisionCreateRequest(
        outcome="rejected",
        evaluation_snapshot=_evaluation_snapshot(),
        baseline=RegimenSnapshotInput(),
        final=RegimenSnapshotInput(),
        rejection_reasons=["OTHER"],
        other_rejection_reason="Too short.",
    )

    with pytest.raises(RegimenDecisionValidationError, match="50 words"):
        create_regimen_decision(_session(), request, _catalog())


def test_medicine_selection_must_match_catalog_subgroup() -> None:
    request = RegimenDecisionCreateRequest(
        outcome="accepted",
        evaluation_snapshot=_evaluation_snapshot(),
        baseline=RegimenSnapshotInput(
            regimen_options=[
                RegimenOptionInput(
                    components=[
                        RegimenComponentSelection(
                            selector_kind="medicine",
                            group_code="C",
                            subgroup="wrong subgroup",
                            medicine_id="DRUG0003",
                        )
                    ]
                )
            ]
        ),
    )

    with pytest.raises(RegimenDecisionValidationError, match="subgroup"):
        create_regimen_decision(_session(), request, _catalog())

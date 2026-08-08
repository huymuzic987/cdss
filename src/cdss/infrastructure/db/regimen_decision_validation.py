"""Validation rules for clinician-authored regimen decisions."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from cdss.api.schemas.clinical_evaluation import parse_clinical_bundle
from cdss.api.schemas.regimen_decisions import (
    ClinicalPlanItemInput,
    RegimenComponentSelection,
    RegimenDecisionCreateRequest,
    RegimenSnapshotInput,
)
from cdss.domain.decision_tree.medication_regimen_subgroups import subgroup_matches
from cdss.domain.decision_tree.medicine_catalog import Medicine

ALLOWED_GROUPS = frozenset({"A", "B", "C", "D", "MRA", "SGLT2i", "GLP1RA", "Others"})
REASON_CODES = frozenset(
    {
        "DRUGS_NOT_CORRECT",
        "DOSE_OR_FREQUENCY_NOT_CORRECT",
        "SAFETY_OR_CONTRAINDICATION",
        "PATIENT_PREFERENCE_OR_ADHERENCE",
        "AVAILABILITY_OR_COST",
        "OTHER",
    }
)


class RegimenDecisionValidationError(ValueError):
    """A clinician decision cannot be safely or structurally persisted."""


def parse_evaluation_snapshot(snapshot: dict[str, Any]):
    raw_bundle = snapshot.get("input_snapshot")
    if not isinstance(raw_bundle, dict):
        raise RegimenDecisionValidationError(
            "evaluation_snapshot.input_snapshot must be the original FHIR Bundle."
        )
    try:
        return parse_clinical_bundle(raw_bundle)
    except Exception as exc:
        raise RegimenDecisionValidationError(
            "The saved evaluation does not contain a valid FHIR Bundle."
        ) from exc


def validate_snapshot(
    snapshot: RegimenSnapshotInput, catalog: Sequence[Medicine], *, label: str
) -> None:
    validate_plan_items(snapshot.clinical_plan, label=label)
    catalog_by_id = {medicine.drug_id: medicine for medicine in catalog}
    for option_index, option in enumerate(snapshot.regimen_options):
        for component_index, component in enumerate(option.components):
            validate_component(
                component,
                catalog_by_id,
                label=f"{label}.regimen_options[{option_index}].components[{component_index}]",
            )


def validate_component(
    component: RegimenComponentSelection, catalog_by_id: dict[str, Medicine], *, label: str
) -> None:
    if component.group_code not in ALLOWED_GROUPS:
        raise RegimenDecisionValidationError(
            f"{label}.group_code is not a supported medicine group."
        )
    if component.selector_kind == "group":
        if component.subgroup or component.medicine_id:
            raise RegimenDecisionValidationError(
                f"{label} group selections cannot include subgroup or medicine_id."
            )
        return
    if component.selector_kind == "subgroup":
        if not component.subgroup or component.medicine_id:
            raise RegimenDecisionValidationError(
                f"{label} subgroup selections require only a known subgroup."
            )
        if not any(
            _medicine_group(medicine) == component.group_code
            and subgroup_matches(medicine.subgroup, component.subgroup)
            for medicine in catalog_by_id.values()
            if medicine.available
        ):
            raise RegimenDecisionValidationError(
                f"{label}.subgroup is not in the medicine catalog."
            )
        return
    if not component.medicine_id or component.subgroup is None:
        raise RegimenDecisionValidationError(
            f"{label} medicine selections require medicine_id and subgroup."
        )
    medicine = catalog_by_id.get(component.medicine_id)
    if medicine is None or not medicine.available:
        raise RegimenDecisionValidationError(
            f"{label}.medicine_id is not an available catalog medicine."
        )
    if _medicine_group(medicine) != component.group_code:
        raise RegimenDecisionValidationError(f"{label}.medicine_id does not belong to group_code.")
    if not subgroup_matches(medicine.subgroup, component.subgroup):
        raise RegimenDecisionValidationError(f"{label}.subgroup does not match medicine_id.")


def validate_plan_items(items: Sequence[ClinicalPlanItemInput], *, label: str) -> None:
    for index, item in enumerate(items):
        prefix = f"{label}.clinical_plan[{index}]"
        if item.type == "NEXT_FOLLOW_UP":
            if item.scheduled_at is None:
                raise RegimenDecisionValidationError(f"{prefix} requires scheduled_at.")
            if (item.duration_value is None) != (item.duration_unit is None):
                raise RegimenDecisionValidationError(
                    f"{prefix} duration_value and duration_unit must be supplied together."
                )
            fields = (
                item.target_mode,
                item.target_sbp,
                item.target_dbp,
                item.map_reduction_percent,
                item.timeframe_value,
                item.timeframe_unit,
                item.text,
            )
            if any(value is not None for value in fields):
                raise RegimenDecisionValidationError(
                    f"{prefix} contains fields from another plan tab."
                )
        elif item.type == "TARGET_BP":
            if item.target_mode is None:
                raise RegimenDecisionValidationError(f"{prefix} requires target_mode.")
            if item.target_mode == "SBP_DBP":
                if (
                    item.target_sbp is None
                    or item.target_dbp is None
                    or item.map_reduction_percent is not None
                ):
                    raise RegimenDecisionValidationError(f"{prefix} requires SBP and DBP only.")
            elif (
                item.map_reduction_percent is None
                or item.target_sbp is not None
                or item.target_dbp is not None
            ):
                raise RegimenDecisionValidationError(
                    f"{prefix} requires MAP reduction percentage only."
                )
            if (item.timeframe_value is None) != (item.timeframe_unit is None):
                raise RegimenDecisionValidationError(
                    f"{prefix} timeframe_value and timeframe_unit must be supplied together."
                )
            fields = (item.scheduled_at, item.duration_value, item.duration_unit, item.text)
            if any(value is not None for value in fields):
                raise RegimenDecisionValidationError(
                    f"{prefix} contains fields from another plan tab."
                )
        elif item.type == "ELSE":
            if not item.text or not item.text.strip():
                raise RegimenDecisionValidationError(f"{prefix} requires text.")
            fields = (
                item.scheduled_at,
                item.duration_value,
                item.duration_unit,
                item.target_mode,
                item.target_sbp,
                item.target_dbp,
                item.map_reduction_percent,
                item.timeframe_value,
                item.timeframe_unit,
            )
            if any(value is not None for value in fields):
                raise RegimenDecisionValidationError(
                    f"{prefix} contains fields from another plan tab."
                )


def validate_rejection_reasons(request: RegimenDecisionCreateRequest) -> None:
    reasons = list(request.rejection_reasons)
    if not reasons:
        raise RegimenDecisionValidationError(
            "Select at least one reason for rejecting the regimen."
        )
    if len(reasons) != len(set(reasons)) or any(reason not in REASON_CODES for reason in reasons):
        raise RegimenDecisionValidationError(
            "Rejection reasons contain an invalid or duplicate code."
        )
    other_text = request.other_rejection_reason.strip() if request.other_rejection_reason else ""
    if "OTHER" in reasons and not other_text:
        raise RegimenDecisionValidationError("The Other rejection reason must include details.")
    if "OTHER" not in reasons and other_text:
        raise RegimenDecisionValidationError(
            "other_rejection_reason is allowed only when OTHER is selected."
        )


def _medicine_group(medicine: Medicine) -> str:
    drug_class = (medicine.drug_class or "").casefold()
    subgroup = (medicine.subgroup or "").casefold()
    name = medicine.name.casefold()
    if drug_class == "mra" or "mra" in subgroup or name in {"spironolactone", "eplerenone"}:
        return "MRA"
    if drug_class == "sglt2i":
        return "SGLT2i"
    if drug_class == "glp1ra":
        return "GLP1RA"
    if drug_class in {"a", "b", "c", "d"}:
        return drug_class.upper()
    return "Others"

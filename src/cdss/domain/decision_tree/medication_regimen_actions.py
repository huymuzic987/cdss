"""Legacy action-payload normalization for medication regimens."""

from collections.abc import Mapping, Sequence
from typing import Any, TypeGuard

from cdss.domain.decision_tree.medication_regimen_contracts import (
    DEFAULT_REGIMEN_DOSE_STRATEGY,
    RegimenAlternative,
    RegimenComponent,
)
from cdss.domain.decision_tree.medication_regimen_values import class_component

_ACTION_TYPE_CLASSES: dict[str, tuple[str, ...]] = {
    "COMBINE_D_SGLT2I_ALDO": ("D", "SGLT2i", "MRA"),
    "COMBINE_ABD_ALDO_SGLT2I": ("A", "B", "D", "SGLT2i", "MRA"),
    "ADD_A_ARNI_CTTA_UCMC": ("A",),
    "ADD_A_ARNI_CTTA": ("A",),
    "ADD_A_ARNI_ARB_OR_ACE_INHIBITOR_FOR_HFMREF": ("A",),
    "ADD_DIHYDROPYRIDINE_CCB": ("C",),
    "COMBINE_ACD_MRA": ("A", "C", "D", "MRA"),
}


def components_from_action_payload(
    payload: Mapping[str, Any] | None,
) -> tuple[list[RegimenComponent], list[RegimenAlternative]]:
    if not isinstance(payload, Mapping):
        return [], []
    dose = _string(payload.get("dose_strategy")) or DEFAULT_REGIMEN_DOSE_STRATEGY
    alternatives = [
        RegimenAlternative(
            components=[class_component(code, dose) for code in raw if _string(code)]
        )
        for raw in _lists(payload.get("combination_options"))
    ]
    options = payload.get("drug_options")
    if _sequence(options):
        for raw in options:
            code = _string(raw.get("class")) if isinstance(raw, Mapping) else None
            if code:
                alternatives.append(RegimenAlternative(components=[class_component(code, dose)]))
    classes = payload.get("classes")
    components = (
        [class_component(code, dose) for code in classes if isinstance(code, str) and code]
        if _sequence(classes)
        else []
    )
    preferred = payload.get("preferred_combination")
    preferred_classes = preferred.get("classes") if isinstance(preferred, Mapping) else None
    if _sequence(preferred_classes):
        components.extend(
            class_component(code, dose)
            for code in preferred_classes
            if isinstance(code, str) and code
        )
    action_type = payload.get("action_type")
    if isinstance(action_type, str):
        components.extend(
            class_component(code, dose) for code in _ACTION_TYPE_CLASSES.get(action_type, ())
        )
    return components, [option for option in alternatives if option.components]


def _lists(value: object) -> list[list[Any]]:
    return [list(item) for item in value if _sequence(item)] if _sequence(value) else []


def _sequence(value: object) -> TypeGuard[Sequence[Any]]:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes))


def _string(value: object) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None

"""Drug-reference resolution for END nodes that start medication therapy.

Two independent mechanisms, both driven by the full medicine catalog in
medicines.py (generated from backups/medicines.sql):

1. Class-letter combinations. Tree 6 ("drug-combination") is the only tree
   whose INFERENCE nodes set ``context.treatment_preferences.combination_options``
   (e.g. ``[["A","C"],["A","D"]]``) or ``.escalation_options`` (the 3-drug
   escalation shape) and ``.additional_drug_classes`` (e.g. ``["B"]`` for a
   mandated beta-blocker add-on) immediately before one of its own END nodes
   -- see the "A/B/C/D class-letter shape" convention documented in
   backups/cdss_merged.sql (A = RAS inhibitor [ACEI/ARB/ARNI], B =
   beta-blocker, C = calcium-channel blocker, D = diuretic).
   build_medicine_options() resolves these into medicine lists, restricted to
   oral + available drugs (chronic combination therapy shouldn't suggest an
   IV-only or currently-unavailable drug).

2. Direct single-drug references, e.g. Tree 12's aspirin-prophylaxis END
   node, which names one specific drug rather than a drug class. These are
   looked up by drug_id via SINGLE_DRUG_ACTION_TYPES and are NOT filtered by
   route/availability -- the drug is always shown, with its `available` flag
   intact, so the caller can decide how to present an unavailable drug.

Callers are expected to invoke these only when collecting an END node whose
action_type is in START_COMBINATION_ACTION_TYPES or SINGLE_DRUG_ACTION_TYPES
(see actions.py) -- this module is not meaningful for any other node.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

from cdss.domain.decision_tree.contracts import JsonObject, JsonValue
from cdss.domain.decision_tree.medicines import MEDICINES_BY_CLASS, MEDICINES_BY_ID

# action_type values (Tree 6 END nodes only) that represent starting or
# escalating a class-letter drug combination, as opposed to e.g. maintaining
# the current regimen (MAINTAIN_CURRENT_REGIMEN) or trees unrelated to the
# A/B/C/D combination scheme.
START_COMBINATION_ACTION_TYPES: frozenset[str] = frozenset(
    {
        "CONSIDER_MONOTHERAPY",
        "INITIAL_TWO_DRUG_COMBINATION",
        "INCREASE_DOSE_OR_THREE_DRUG_COMBINATION",
    }
)

# action_type -> drug_id(s) for END nodes that name one specific drug rather
# than a class-letter combination.
SINGLE_DRUG_ACTION_TYPES: Mapping[str, tuple[str, ...]] = {
    # T12_END_ASPIRIN_PROPHYLAXIS (Tree 12: hypertension-in-pregnancy).
    "ASPIRIN_PROPHYLAXIS": ("DRUG0065",),
}


def _is_oral(medicine: JsonObject) -> bool:
    route = medicine.get("route")
    return isinstance(route, str) and "Uống" in route


def _is_available(medicine: JsonObject) -> bool:
    return medicine.get("available") is True


def _oral_available_medicines(class_letter: str) -> list[JsonObject]:
    return [
        medicine
        for medicine in MEDICINES_BY_CLASS.get(class_letter, ())
        if _is_oral(medicine) and _is_available(medicine)
    ]


def _string_list(value: Any) -> list[str] | None:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        return None
    return list(value)


def _base_combinations(treatment_preferences: Mapping[str, Any]) -> list[list[str]]:
    """Class-letter combos from combination_options and/or escalation_options."""

    combos: list[list[str]] = []

    combination_options = treatment_preferences.get("combination_options")
    if isinstance(combination_options, list):
        for option in combination_options:
            classes = _string_list(option)
            if classes is not None:
                combos.append(classes)

    escalation_options = treatment_preferences.get("escalation_options")
    if isinstance(escalation_options, list):
        for strategy in escalation_options:
            if isinstance(strategy, Mapping):
                classes = _string_list(strategy.get("classes"))
                if classes is not None:
                    combos.append(classes)

    return combos


def _mandated_additional_classes(treatment_preferences: Mapping[str, Any]) -> list[str]:
    """Class letters (e.g. a mandated beta-blocker) added on top of every combo."""

    additional = _string_list(treatment_preferences.get("additional_drug_classes"))
    if additional is None:
        return []
    return [class_letter for class_letter in additional if class_letter in MEDICINES_BY_CLASS]


def build_medicine_options(context: Mapping[str, Any]) -> list[JsonObject] | None:
    """Resolve the active class-letter combination(s) in ``context`` into medicines.

    Returns None if no combination/escalation classes are present in
    ``context.treatment_preferences``.
    """

    treatment_preferences = context.get("treatment_preferences")
    if not isinstance(treatment_preferences, Mapping):
        return None

    combos = _base_combinations(treatment_preferences)
    if not combos:
        return None
    mandated = _mandated_additional_classes(treatment_preferences)

    medicine_options: list[JsonObject] = []
    for combo in combos:
        classes = list(dict.fromkeys([*combo, *mandated]))
        medicine_options.append(
            {
                "classes": cast(JsonValue, classes),
                "medicines": {
                    class_letter: cast(JsonValue, _oral_available_medicines(class_letter))
                    for class_letter in classes
                },
            }
        )
    return medicine_options


def resolve_single_drug_medicines(action_type: str) -> list[JsonObject] | None:
    """Look up the specific drug(s) named by a single-drug action_type.

    Returns None if action_type isn't in SINGLE_DRUG_ACTION_TYPES. Unlike
    build_medicine_options, results are not filtered by route/availability --
    the drug is always returned, with its `available` flag intact.
    """

    drug_ids = SINGLE_DRUG_ACTION_TYPES.get(action_type)
    if drug_ids is None:
        return None
    return [MEDICINES_BY_ID[drug_id] for drug_id in drug_ids if drug_id in MEDICINES_BY_ID]

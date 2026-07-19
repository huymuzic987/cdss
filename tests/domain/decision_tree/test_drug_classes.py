"""Pure unit tests for drug-reference resolution (combinations and single drugs)."""

from typing import Any, cast

from cdss.domain.decision_tree.drug_classes import (
    build_medicine_options,
    resolve_single_drug_medicines,
)


def _medicine_names(option: dict[str, Any], class_letter: str) -> set[str]:
    medicines = cast(dict[str, Any], option["medicines"])
    return {cast(str, m["name"]) for m in cast(list[dict[str, Any]], medicines[class_letter])}


def test_build_medicine_options_returns_none_without_treatment_preferences() -> None:
    assert build_medicine_options({}) is None
    assert build_medicine_options({"treatment_preferences": {}}) is None


def test_build_medicine_options_expands_combination_options() -> None:
    context = {"treatment_preferences": {"combination_options": [["A", "C"], ["A", "D"]]}}

    options = build_medicine_options(context)

    assert options is not None
    assert [o["classes"] for o in options] == [["A", "C"], ["A", "D"]]
    assert "Losartan" in _medicine_names(options[0], "A")
    assert "Amlodipine" in _medicine_names(options[0], "C")


def test_build_medicine_options_excludes_iv_only_and_unavailable_drugs() -> None:
    context = {"treatment_preferences": {"combination_options": [["C"]]}}

    options = build_medicine_options(context)

    assert options is not None
    names = _medicine_names(options[0], "C")
    assert "Amlodipine" in names
    assert "Nicardipine" not in names
    assert "Clevidipine" not in names


def test_build_medicine_options_expands_escalation_options_classes() -> None:
    context = {
        "treatment_preferences": {
            "escalation_options": [
                {"strategy": "INCREASE_DOSE_TWO_DRUG"},
                {"strategy": "THREE_DRUG_COMBINATION", "classes": ["A", "C", "D"]},
            ]
        }
    }

    options = build_medicine_options(context)

    assert options is not None
    assert [o["classes"] for o in options] == [["A", "C", "D"]]


def test_build_medicine_options_merges_mandated_additional_classes() -> None:
    context = {
        "treatment_preferences": {
            "combination_options": [["A", "C"], ["A", "D"]],
            "additional_drug_classes": ["B"],
        }
    }

    options = build_medicine_options(context)

    assert options is not None
    assert [o["classes"] for o in options] == [["A", "C", "B"], ["A", "D", "B"]]
    assert "Bisoprolol" in _medicine_names(options[0], "B")


def test_build_medicine_options_ignores_unknown_additional_classes() -> None:
    context = {
        "treatment_preferences": {
            "combination_options": [["B"]],
            "additional_drug_classes": ["SGLT2_INHIBITOR", "GLP1_RECEPTOR_AGONIST"],
        }
    }

    options = build_medicine_options(context)

    assert options is not None
    assert options[0]["classes"] == ["B"]


def test_resolve_single_drug_medicines_returns_none_for_unknown_action_type() -> None:
    assert resolve_single_drug_medicines("MAINTAIN_CURRENT_REGIMEN") is None


def test_resolve_single_drug_medicines_returns_aspirin_with_dose_and_availability() -> None:
    medicines = resolve_single_drug_medicines("ASPIRIN_PROPHYLAXIS")

    assert medicines is not None
    assert len(medicines) == 1
    aspirin = medicines[0]
    assert aspirin["name"] == "Aspirin"
    assert aspirin["dose_low"] == "75 - 81 mg/ngày"
    assert aspirin["available"] is True

"""Exhaustive unit tests for the condition-DSL -> FHIRPath translator.

Each test asserts the exact FHIRPath string produced for one grammar form,
per the clinical-safety concern behind translating (rather than merely
preserving) the condition dialect.
"""

from __future__ import annotations

from cdss.api.schemas.fhir import condition_to_fhirpath


def test_static_comparison_gte() -> None:
    condition = {"path": "input.current_clinic_sbp", "op": "gte", "value": 140}
    assert condition_to_fhirpath(condition) == "(%input.current_clinic_sbp >= 140)"


def test_static_comparison_all_operators() -> None:
    assert condition_to_fhirpath({"path": "input.a", "op": "eq", "value": 1}) == "(%input.a = 1)"
    assert condition_to_fhirpath({"path": "input.a", "op": "lt", "value": 1}) == "(%input.a < 1)"
    assert condition_to_fhirpath({"path": "input.a", "op": "lte", "value": 1}) == "(%input.a <= 1)"
    assert condition_to_fhirpath({"path": "input.a", "op": "gt", "value": 1}) == "(%input.a > 1)"
    assert condition_to_fhirpath({"path": "input.a", "op": "gte", "value": 1}) == "(%input.a >= 1)"


def test_comparison_with_context_path() -> None:
    condition = {"path": "context.risk.level", "op": "eq", "value": "HIGH"}
    assert condition_to_fhirpath(condition) == "(%context.risk.level = 'HIGH')"


def test_comparison_boolean_literal() -> None:
    condition = {"path": "input.is_medication_follow_up", "op": "eq", "value": True}
    assert condition_to_fhirpath(condition) == "(%input.is_medication_follow_up = true)"

    condition_false = {"path": "input.is_medication_follow_up", "op": "eq", "value": False}
    assert condition_to_fhirpath(condition_false) == "(%input.is_medication_follow_up = false)"


def test_comparison_string_literal_is_escaped() -> None:
    condition = {"path": "input.facility_capability", "op": "eq", "value": "it's a 'test'"}
    assert condition_to_fhirpath(condition) == r"(%input.facility_capability = 'it\'s a \'test\'')"


def test_dynamic_value_from_path() -> None:
    condition = {
        "path": "input.current_clinic_sbp",
        "op": "lt",
        "value_from_path": "context.treatment.bp_target.sbp.upper_exclusive_mmhg",
    }
    assert condition_to_fhirpath(condition) == (
        "(%input.current_clinic_sbp < %context.treatment.bp_target.sbp.upper_exclusive_mmhg)"
    )


def test_subtract_left_expression() -> None:
    condition = {
        "left": {
            "expression": "subtract",
            "left_path": "input.previous_clinic_sbp",
            "right_path": "input.current_clinic_sbp",
        },
        "op": "gte",
        "value": 10,
    }
    assert condition_to_fhirpath(condition) == (
        "((%input.previous_clinic_sbp - %input.current_clinic_sbp) >= 10)"
    )


def test_exists_operator() -> None:
    condition = {"op": "exists", "path": "input.home_sbp"}
    assert condition_to_fhirpath(condition) == "(%input.home_sbp.exists())"


def test_in_operator_literal_membership() -> None:
    condition = {"op": "in", "path": "input.risk_factor_count", "value": [1, 2]}
    assert condition_to_fhirpath(condition) == "(%input.risk_factor_count in (1 | 2))"


def test_all_group() -> None:
    condition = {
        "all": [
            {"path": "input.current_clinic_sbp", "op": "gte", "value": 140},
            {"path": "input.current_clinic_dbp", "op": "gte", "value": 90},
        ]
    }
    assert condition_to_fhirpath(condition) == (
        "((%input.current_clinic_sbp >= 140) and (%input.current_clinic_dbp >= 90))"
    )


def test_any_group() -> None:
    condition = {
        "any": [
            {"path": "input.current_clinic_sbp", "op": "gte", "value": 180},
            {"path": "input.current_clinic_dbp", "op": "gte", "value": 120},
        ]
    }
    assert condition_to_fhirpath(condition) == (
        "((%input.current_clinic_sbp >= 180) or (%input.current_clinic_dbp >= 120))"
    )


def test_not_group() -> None:
    condition = {"not": {"path": "input.is_medication_follow_up", "op": "eq", "value": True}}
    assert condition_to_fhirpath(condition) == ("(((%input.is_medication_follow_up = true)).not())")


def test_nested_all_not_any() -> None:
    condition = {
        "all": [
            {"path": "input.is_medication_follow_up", "op": "eq", "value": True},
            {
                "not": {
                    "any": [
                        {"path": "input.current_clinic_sbp", "op": "lt", "value": 90},
                        {"path": "input.current_clinic_dbp", "op": "lt", "value": 60},
                    ]
                }
            },
        ]
    }
    assert condition_to_fhirpath(condition) == (
        "((%input.is_medication_follow_up = true) and "
        "((((%input.current_clinic_sbp < 90) or (%input.current_clinic_dbp < 60))).not()))"
    )

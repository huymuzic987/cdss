"""Pure unit tests for drug-reference resolution (combinations and single drugs)."""

from typing import Any, cast

from cdss.domain.decision_tree.drug_classes import (
    build_medicine_options,
    resolve_single_drug_medicines,
)
from cdss.domain.decision_tree.medicine_catalog import Medicine

_CATALOG = (
    Medicine(
        drug_id="DRUG0023",
        name="Losartan",
        drug_class="A",
        subgroup="ARB",
        route="Thuốc Uống",
        dose_low="25 mg",
        dose_usual="50 - 100 mg",
        dose_max="100 mg",
        source="Bảng 10",
        link=None,
        available=True,
    ),
    Medicine(
        drug_id="DRUG0003",
        name="Amlodipine",
        drug_class="C",
        subgroup="CKCa DHP",
        route="Thuốc Uống",
        dose_low="2.5 mg",
        dose_usual="5 - 10 mg",
        dose_max="10 mg",
        source="Bảng 10",
        link=None,
        available=True,
    ),
    Medicine(
        drug_id="DRUG0057",
        name="Nicardipine",
        drug_class="C",
        subgroup="CKCa DHP",
        route="Thuốc Truyền Tĩnh Mạch",
        dose_low="3 mg/giờ",
        dose_usual="5 mg/giờ",
        dose_max="15 mg/giờ",
        source="Mục 3.7.5",
        link="https://drugs.com/dosage/nicardipine.html",
        available=True,
    ),
    Medicine(
        drug_id="DRUG0058",
        name="Clevidipine",
        drug_class="C",
        subgroup="CKCa DHP",
        route="Thuốc Truyền Tĩnh Mạch",
        dose_low="1 - 2 mg/giờ",
        dose_usual="4 - 6 mg/giờ",
        dose_max="16-32 mg/giờ",
        source="Mục 3.7.5",
        link="https://drugs.com/dosage/clevidipine.html",
        available=False,
    ),
    Medicine(
        drug_id="DRUG0036",
        name="Spironolactone",
        drug_class="D",
        subgroup="Lợi tiểu giữ Kali",
        route="Thuốc Uống",
        dose_low="12.5 mg",
        dose_usual="25 - 50 mg",
        dose_max="100 mg",
        source="Bảng 10",
        link=None,
        available=True,
    ),
    Medicine(
        drug_id="DRUG0040",
        name="Bisoprolol",
        drug_class="B",
        subgroup="CB chọn lọc Beta-1",
        route="Thuốc Uống",
        dose_low="2.5 mg",
        dose_usual="5 - 10 mg",
        dose_max="20 mg",
        source="Bảng 10",
        link=None,
        available=True,
    ),
    Medicine(
        drug_id="DRUG0065",
        name="Aspirin",
        drug_class=None,
        subgroup=None,
        route=None,
        dose_low="75 - 81 mg/ngày",
        dose_usual=None,
        dose_max="150 - 162 mg/ngày",
        source=None,
        link="https://www.drugs.com/dosage/aspirin.html",
        available=True,
    ),
)


class _FakeMedicineRepository:
    def get_by_id(self, drug_id: str) -> Medicine | None:
        return next((m for m in _CATALOG if m.drug_id == drug_id), None)

    def list_by_class(self, drug_class: str) -> tuple[Medicine, ...]:
        return tuple(m for m in _CATALOG if m.drug_class == drug_class)

    def list_all(self) -> tuple[Medicine, ...]:
        return _CATALOG


def _medicine_names(option: dict[str, Any], class_letter: str) -> set[str]:
    medicines = cast(dict[str, Any], option["medicines"])
    return {cast(str, m["name"]) for m in cast(list[dict[str, Any]], medicines[class_letter])}


def test_build_medicine_options_returns_none_without_treatment_preferences() -> None:
    repository = _FakeMedicineRepository()
    assert build_medicine_options({}, repository) is None
    assert build_medicine_options({"treatment_preferences": {}}, repository) is None


def test_build_medicine_options_expands_combination_options() -> None:
    context = {"treatment_preferences": {"combination_options": [["A", "C"], ["A", "D"]]}}

    options = build_medicine_options(context, _FakeMedicineRepository())

    assert options is not None
    assert [o["classes"] for o in options] == [["A", "C"], ["A", "D"]]
    assert "Losartan" in _medicine_names(options[0], "A")
    assert "Amlodipine" in _medicine_names(options[0], "C")


def test_build_medicine_options_excludes_iv_only_and_unavailable_drugs() -> None:
    context = {"treatment_preferences": {"combination_options": [["C"]]}}

    options = build_medicine_options(context, _FakeMedicineRepository())

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

    options = build_medicine_options(context, _FakeMedicineRepository())

    assert options is not None
    assert [o["classes"] for o in options] == [["A", "C", "D"]]


def test_build_medicine_options_merges_mandated_additional_classes() -> None:
    context = {
        "treatment_preferences": {
            "combination_options": [["A", "C"], ["A", "D"]],
            "additional_drug_classes": ["B"],
        }
    }

    options = build_medicine_options(context, _FakeMedicineRepository())

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

    options = build_medicine_options(context, _FakeMedicineRepository())

    assert options is not None
    assert options[0]["classes"] == ["B"]


def test_resolve_single_drug_medicines_returns_none_for_unknown_action_type() -> None:
    result = resolve_single_drug_medicines("MAINTAIN_CURRENT_REGIMEN", _FakeMedicineRepository())
    assert result is None


def test_resolve_single_drug_medicines_returns_aspirin_with_dose_and_availability() -> None:
    medicines = resolve_single_drug_medicines("ASPIRIN_PROPHYLAXIS", _FakeMedicineRepository())

    assert medicines is not None
    assert len(medicines) == 1
    aspirin = medicines[0]
    assert aspirin["name"] == "Aspirin"
    assert aspirin["dose_low"] == "75 - 81 mg/ngày"
    assert aspirin["available"] is True

"""Pure unit tests for the generated medicine catalog (medicines.py)."""

from typing import cast

from cdss.domain.decision_tree.medicines import (
    MEDICINES,
    MEDICINES_BY_CLASS,
    MEDICINES_BY_ID,
)


def test_catalog_covers_all_65_drugs_from_medicine_csv() -> None:
    assert len(MEDICINES) == 65
    assert len(MEDICINES_BY_ID) == 65


def test_catalog_includes_drugs_outside_the_abcd_scheme() -> None:
    # These were excluded from the earlier, feature-scoped lookup table but
    # belong in the full catalog: IV-only drugs, "Other" class drugs, SGLT2i,
    # and aspirin.
    assert MEDICINES_BY_ID["DRUG0057"]["name"] == "Nicardipine"
    assert MEDICINES_BY_ID["DRUG0048"]["name"] == "Aliskiren"
    assert MEDICINES_BY_ID["DRUG0062"]["name"] == "Dapagliflozin"
    assert MEDICINES_BY_ID["DRUG0065"]["name"] == "Aspirin"


def test_every_drug_defaults_to_available() -> None:
    assert all(medicine["available"] is True for medicine in MEDICINES)


def test_drug_class_assigned_only_for_abcd_scheme_drugs() -> None:
    assert MEDICINES_BY_ID["DRUG0023"]["drug_class"] == "A"  # Losartan
    assert MEDICINES_BY_ID["DRUG0040"]["drug_class"] == "B"  # Bisoprolol
    assert MEDICINES_BY_ID["DRUG0003"]["drug_class"] == "C"  # Amlodipine
    assert MEDICINES_BY_ID["DRUG0036"]["drug_class"] == "D"  # Spironolactone
    # Outside the A/B/C/D scheme.
    assert MEDICINES_BY_ID["DRUG0048"]["drug_class"] is None  # Aliskiren
    assert MEDICINES_BY_ID["DRUG0065"]["drug_class"] is None  # Aspirin
    assert MEDICINES_BY_ID["DRUG0062"]["drug_class"] == "SGLT2i"  # Dapagliflozin


def test_medicines_by_class_includes_iv_only_drugs_unfiltered() -> None:
    # medicines.py is a raw catalog -- route/availability filtering is the
    # caller's responsibility (see drug_classes._oral_available_medicines).
    names = {cast(str, m["name"]) for m in MEDICINES_BY_CLASS["C"]}
    assert "Nicardipine" in names
    assert "Clevidipine" in names


def test_aspirin_entry_carries_dose_and_link_without_a_source_row() -> None:
    aspirin = MEDICINES_BY_ID["DRUG0065"]
    assert aspirin["dose_low"] == "75 - 81 mg/ngày"
    assert aspirin["dose_max"] == "150 - 162 mg/ngày"
    assert aspirin["source"] is None
    assert "drugs.com" in str(aspirin["link"])

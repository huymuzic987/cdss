from cdss.api.routes.evaluation_medication_collection import (
    collect_action_type_ids,
    collect_inference_group_ids,
)
from cdss.domain.decision_tree.medicine_catalog import Medicine


def _medicine(drug_id: str, drug_class: str, subgroup: str) -> Medicine:
    return Medicine(
        drug_id=drug_id,
        name=drug_id,
        drug_class=drug_class,
        subgroup=subgroup,
        route="Oral",
        dose_low="1 mg",
        dose_usual="2 mg",
        dose_max="4 mg",
        source="test",
        link=None,
        available=True,
    )


def test_action_type_collection_keeps_only_the_named_subgroups() -> None:
    catalog = [
        _medicine("ACEI", "A", "ƯCMC"),
        _medicine("ARB", "A", "CTTA"),
        _medicine("DHP", "C", "CKCa DHP"),
        _medicine("NON_DHP", "C", "CKCa Non-DHP"),
    ]
    selected: set[str] = set()

    collect_action_type_ids({"action_type": "ADD_A_ARNI_CTTA"}, catalog, selected)
    assert selected == {"ARB"}

    selected.clear()
    collect_inference_group_ids(
        "Add A (ARNI and CTTA)",
        catalog,
        selected,
        node_key="T10_INFERENCE_ADD_A_ARNI_OR_ARB_FOR_HFPEF",
    )
    assert selected == {"ARB"}

    selected.clear()
    collect_action_type_ids({"action_type": "ADD_DIHYDROPYRIDINE_CCB"}, catalog, selected)
    assert selected == {"DHP"}


def test_action_type_collection_uses_group_words_instead_of_action_type_mappings() -> None:
    catalog = [
        _medicine("THIAZIDE", "D", "LT Thiazide-like"),
        _medicine("LOOP", "D", "LT quai"),
        _medicine("DHP", "C", "CKCa DHP"),
        _medicine("BETA", "B", "CB"),
    ]
    selected: set[str] = set()

    collect_action_type_ids(
        {"action_type": "PRESCRIBE_D_C_THIAZIDE_PRIORITY"},
        catalog,
        selected,
        text="Prescribe D + C combination, prioritize thiazide-like D",
    )
    assert selected == {"THIAZIDE", "DHP"}

    selected.clear()
    collect_action_type_ids(
        {"action_type": "BETA_BLOCKER_3_YEARS"},
        catalog,
        selected,
    )
    assert selected == {"BETA"}


def test_inference_group_collection_ignores_non_treatment_and_negative_nodes() -> None:
    catalog = [_medicine("DHP", "C", "CKCa DHP")]
    selected: set[str] = set()

    collect_inference_group_ids(
        "Determine contraindications for the calcium-channel blocker",
        catalog,
        selected,
        node_key="T10_INFERENCE_DETERMINE_CONTRAINDICATIONS",
    )
    collect_inference_group_ids(
        "Absolute contraindication: calcium-channel blocker",
        catalog,
        selected,
        node_key="T12_INFERENCE_AVOID_CALCIUM_CHANNEL_BLOCKER",
    )

    assert selected == set()


def test_group_collection_keeps_all_group_medicines_when_only_groups_are_named() -> None:
    catalog = [
        _medicine("MRA_AS_D", "D", "MRA (LT giữ Kali)"),
        _medicine("THIAZIDE", "D", "LT Thiazide"),
        _medicine("MRA", "MRA", "MRA (LT giữ Kali)"),
    ]
    selected: set[str] = set()

    collect_inference_group_ids(
        "Combine D and MRA",
        catalog,
        selected,
        node_key="T10_INFERENCE_COMBINE_D_PLUS_MRA",
    )

    assert selected == {"MRA_AS_D", "THIAZIDE", "MRA"}


def test_catalog_independent_arni_subgroup_does_not_fall_back_to_class_a() -> None:
    catalog = [_medicine("ACEI", "A", "ƯCMC"), _medicine("ARB", "A", "CTTA")]
    selected: set[str] = set()

    collect_inference_group_ids(
        "Add A (ARNI)",
        catalog,
        selected,
        node_key="T10_INFERENCE_ADD_A_ARNI_FOR_HFPEF",
    )

    assert selected == set()

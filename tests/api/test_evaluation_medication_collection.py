from cdss.api.routes.evaluation_medication_collection import collect_action_type_ids
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
    collect_action_type_ids({"action_type": "ADD_DIHYDROPYRIDINE_CCB"}, catalog, selected)
    assert selected == {"DHP"}

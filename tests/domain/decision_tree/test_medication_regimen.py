from collections.abc import Mapping
from types import SimpleNamespace
from typing import Any, cast
from uuid import uuid4

import pytest

from cdss.domain.decision_tree import (
    NodeDefinition,
    NodeType,
    RegimenKeyword,
    TraceEvent,
    TraversalResult,
    TreeGraphRepository,
    build_traversed_medication_regimen,
)
from cdss.domain.decision_tree.contracts import FrozenJsonObject
from cdss.domain.decision_tree.medicine_catalog import Medicine


class _Medicines:
    def list_all(self) -> tuple[Medicine, ...]:
        return ()

    def list_by_class(self, drug_class: str) -> tuple[Medicine, ...]:
        del drug_class
        return ()

    def get_by_id(self, drug_id: str) -> Medicine | None:
        del drug_id
        return None


def _node(
    key: str,
    text: str,
    *,
    node_type: NodeType = NodeType.INFERENCE,
    text_vi: str | None = None,
    context_patch: Mapping[str, Any] | None = None,
    action_payload: Mapping[str, Any] | None = None,
) -> NodeDefinition:
    return NodeDefinition(
        id=uuid4(),
        tree_id=uuid4(),
        node_key=key,
        node_type=node_type,
        text_en=text,
        text_vi=text_vi or text,
        context_patch=context_patch,
        action_payload=action_payload,
    )


def _plan(*nodes: NodeDefinition):
    graph = SimpleNamespace(nodes_by_key={node.node_key: node for node in nodes})
    repository = SimpleNamespace(get_tree=lambda _key: graph)
    result = cast(
        TraversalResult,
        SimpleNamespace(
            trace=[
                SimpleNamespace(
                    step=index,
                    event=TraceEvent.NODE_ENTERED,
                    tree_key="drug-combination",
                    node_key=node.node_key,
                    node_type=NodeType.INFERENCE,
                )
                for index, node in enumerate(nodes, start=1)
            ]
        ),
    )
    return build_traversed_medication_regimen(
        result,
        cast(TreeGraphRepository, repository),
        _Medicines(),
    )


def test_start_stays_first_and_add_keeps_its_own_default_low_dose() -> None:
    add = _node(
        "T6_INFERENCE_ADD_LOW_DOSE_B_BETA_BLOCKER",
        "Add beta blocker",
        context_patch={"treatment_preferences": {"additional_drug_classes": ["B"]}},
    )
    start = _node(
        "T6_INFERENCE_START_LOW_DOSE_A_PLUS_C_OR_A_PLUS_D",
        "Start A with C or D",
        context_patch={
            "treatment_preferences": {
                "dose_strategy": "LOW_DOSE",
                "combination_options": [["A", "C"], ["A", "D"]],
            }
        },
    )

    plan = _plan(add, start)

    assert [step.keyword for step in plan.steps] == [RegimenKeyword.START, RegimenKeyword.ADD]
    assert plan.steps[0].trace_step == 2
    assert plan.steps[1].trace_step == 1
    assert plan.steps[1].components[0].code == "B"
    assert plan.steps[1].components[0].dose_strategy == "LOW_DOSE"
    base_codes = [
        [item.code for item in option.components] for option in plan.effective_regimen.base_options
    ]
    assert base_codes == [
        ["A", "C"],
        ["A", "D"],
    ]
    assert [item.code for item in plan.effective_regimen.additions] == ["B"]


def test_structured_select_keeps_each_medicine_as_an_or_alternative() -> None:
    select = _node(
        "T12_INFERENCE_SELECT_METHYLDOPA_OR_LABETALOL_OR_NIFEDIPINE_OR_NICARDIPINE",
        "Select Methyldopa or Labetalol or Nifedipine or Nicardipine",
        action_payload={
            "regimen_update": {
                "operation": "SELECT",
                "alternatives": [
                    {"components": [{"selector_kind": "medicine", "name": name}]}
                    for name in ("Methyldopa", "Labetalol (oral)", "Nifedipine", "Nicardipine")
                ]
            }
        },
    )

    plan = _plan(select)

    assert plan.effective_regimen.status == "choice_required"
    assert [
        [component.name for component in option.components]
        for option in plan.effective_regimen.base_options
    ] == [["Methyldopa"], ["Labetalol (oral)"], ["Nifedipine"], ["Nicardipine"]]


def test_canonical_inference_select_nodes_are_collected_as_alternatives() -> None:
    select = _node(
        "T14_INFERENCE_SELECT_LABETALOL_NICARDIPINE_OR_URAPIDIL",
        "Select Labetalol or Nicardipine or Urapidil",
        action_payload={"action_type": "ACUTE_THERAPY"},
    )
    catalog = [
        Medicine(
            drug_id=name.lower(),
            name=name,
            drug_class=None,
            subgroup=None,
            route=None,
            dose_low=None,
            dose_usual=None,
            dose_max=None,
            source=None,
            link=None,
            available=True,
        )
        for name in ("Labetalol", "Nicardipine", "Urapidil")
    ]
    graph = SimpleNamespace(nodes_by_key={select.node_key: select})
    repository = SimpleNamespace(get_tree=lambda _key: graph)
    result = cast(
        TraversalResult,
        SimpleNamespace(
            trace=[
                SimpleNamespace(
                    step=1,
                    event=TraceEvent.NODE_ENTERED,
                    tree_key="hypertensive-emergency",
                    node_key=select.node_key,
                    node_type=NodeType.INFERENCE,
                )
            ]
        ),
    )
    medicines = SimpleNamespace(list_all=lambda: tuple(catalog))

    plan = build_traversed_medication_regimen(
        result,
        cast(TreeGraphRepository, repository),
        cast(Any, medicines),
    )

    assert plan.steps[0].keyword is RegimenKeyword.SELECT
    assert [
        [component.name for component in option.components]
        for option in plan.effective_regimen.base_options
    ] == [["Labetalol"], ["Nicardipine"], ["Urapidil"]]


def test_canonical_fixed_dose_select_uses_payload_combination_options() -> None:
    action = _node(
        "T5_INFERENCE_SELECT_FIXED_DOSE_A_PLUS_C_OR_A_PLUS_D",
        "Fixed-dose two-drug combination: A + C or A + D",
        action_payload={
            "action_type": "FIXED_DOSE_TWO_DRUG_COMBINATION",
            "combination_options": [["A", "C"], ["A", "D"]],
        },
    )

    plan = _plan(action)

    assert plan.steps[0].keyword is RegimenKeyword.SELECT
    assert [
        [component.code for component in option.components]
        for option in plan.effective_regimen.base_options
    ] == [["A", "C"], ["A", "D"]]


def test_explicit_add_dose_does_not_inherit_start_dose() -> None:
    start = _node(
        "T6_INFERENCE_START_LOW_DOSE_A_WITH_C",
        "Start A and C",
        context_patch={
            "treatment_preferences": {
                "dose_strategy": "LOW_DOSE",
                "combination_options": [["A", "C"]],
            }
        },
    )
    add = _node(
        "T6_INFERENCE_ADD_LOW_DOSE_B_BETA_BLOCKER",
        "Add B",
        action_payload={
            "regimen_update": {
                "components": [
                    {
                        "selector_kind": "class",
                        "code": "B",
                        "dose_strategy": "USUAL_DOSE",
                    }
                ]
            }
        },
    )

    plan = _plan(start, add)

    assert plan.steps[0].alternatives[0].components[0].dose_strategy == "LOW_DOSE"
    assert plan.steps[1].components[0].dose_strategy == "USUAL_DOSE"


def test_persisted_frozen_json_preserves_start_alternatives() -> None:
    start = _node(
        "T6_INFERENCE_START_LOW_DOSE_A_PLUS_C_OR_A_PLUS_D",
        "Start one low-dose regimen: A + C or A + D",
        action_payload=FrozenJsonObject(
            {
                "regimen_update": {
                    "operation": "START",
                    "alternatives": [
                        {
                            "components": [
                                {"selector_kind": "class", "code": "A"},
                                {"selector_kind": "class", "code": "C"},
                            ]
                        },
                        {
                            "components": [
                                {"selector_kind": "class", "code": "A"},
                                {"selector_kind": "class", "code": "D"},
                            ]
                        },
                    ],
                }
            }
        ),
    )

    plan = _plan(start)

    assert [
        [component.code for component in alternative.components]
        for alternative in plan.effective_regimen.base_options
    ] == [["A", "C"], ["A", "D"]]


def test_select_preserves_alternatives_and_requires_a_choice() -> None:
    select = _node(
        "T6_INFERENCE_SELECT_A_WITH_C_OR_D",
        "Select A with C or D",
        action_payload={
            "regimen_update": {
                "alternatives": [
                    {"components": [{"selector_kind": "class", "code": "A"}]},
                    {"components": [{"selector_kind": "class", "code": "C"}]},
                ]
            }
        },
    )

    plan = _plan(select)

    assert len(plan.steps[0].alternatives) == 2
    assert plan.effective_regimen.status == "choice_required"


def test_legacy_heart_failure_action_type_keeps_every_regimen_class() -> None:
    combine = _node(
        "T10_INFERENCE_COMBINE_LOW_DOSE_D_PLUS_SGLT2I_PLUS_MRA_FOR_HFMREF",
        "Combine D and SGLT2i and Aldosterone antagonist",
        action_payload={"action_type": "COMBINE_D_SGLT2I_ALDO"},
    )

    plan = _plan(combine)

    assert [item.code for item in plan.steps[0].components] == ["D", "SGLT2i", "MRA"]
    assert all(item.dose_strategy == "LOW_DOSE" for item in plan.steps[0].components)


def test_complete_regimen_sequence_preserves_alternatives_and_no_op_maintain() -> None:
    start = _node(
        "T6_INFERENCE_START_LOW_DOSE_A_PLUS_C_OR_A_PLUS_D",
        "Drug therapy: start with 2 low-dose drugs (A combined with C or D)",
        context_patch={
            "treatment_preferences": {
                "dose_strategy": "LOW_DOSE",
                "combination_options": [["A", "C"], ["A", "D"]],
            }
        },
    )
    combine = _node(
        "T10_INFERENCE_COMBINE_LOW_DOSE_D_PLUS_SGLT2I_PLUS_MRA_FOR_HFMREF",
        "Combine D and SGLT2i and Aldosterone antagonist",
        action_payload={"action_type": "COMBINE_D_SGLT2I_ALDO"},
    )
    add_a = _node(
        "T10_INFERENCE_ADD_A_ARNI_CTTA_UCMC",
        "Add A (ARNI or CTTA or UCMC)",
        action_payload={"action_type": "ADD_A_ARNI_CTTA_UCMC"},
    )
    maintain = _node(
        "T6_INFERENCE_MAINTAIN_CURRENT_REGIMEN_NO_CHANGE_AFTER_NO_ADJUSTMENT",
        "Maintain regimen",
        text_vi="Duy trì phác đồ",
    )
    add_b = _node(
        "T6_INFERENCE_ADD_LOW_DOSE_B_BETA_BLOCKER",
        "Add beta-blocker",
        context_patch={"treatment_preferences": {"additional_drug_classes": ["B"]}},
    )

    plan = _plan(start, combine, add_a, maintain, add_b)

    assert [
        [component.code for component in alternative.components]
        for alternative in plan.effective_regimen.base_options
    ] == [["A", "C"], ["A", "D"]]
    assert [component.code for component in plan.effective_regimen.additions] == [
        "D",
        "SGLT2i",
        "MRA",
        "A",
        "B",
    ]
    maintain_step = next(step for step in plan.steps if step.keyword is RegimenKeyword.MAINTAIN)
    assert maintain_step.components == []
    assert maintain_step.alternatives == []
    assert plan.effective_regimen.adjustments == []


def test_legacy_diabetes_class_names_are_normalized_to_regimen_groups() -> None:
    select = _node(
        "T8_INFERENCE_SELECT_SGLT2I_OR_GLP1RA",
        "Select SGLT2i or GLP1RA",
        context_patch={
            "treatment_preferences": {
                "combination_options": [
                    ["SGLT2_INHIBITOR"],
                    ["GLP1_RECEPTOR_AGONIST"],
                ]
            }
        },
    )

    plan = _plan(select)

    assert [
        [component.code for component in alternative.components]
        for alternative in plan.steps[0].alternatives
    ] == [
        ["SGLT2i"],
        ["GLP1RA"],
    ]
    assert [
        [component.code for component in alternative.components]
        for alternative in plan.effective_regimen.base_options
    ] == [["SGLT2i"], ["GLP1RA"]]
    assert plan.effective_regimen.status == "choice_required"


def test_independent_select_survives_later_base_selection_and_repeated_start() -> None:
    glucose_lowering = _node(
        "T8_INFERENCE_SELECT_SGLT2I_OR_GLP1RA",
        "Select SGLT2i or GLP1RA",
        context_patch={
            "treatment_preferences": {
                "combination_options": [["SGLT2i"], ["GLP1RA"]]
            }
        },
    )
    base_selection = _node(
        "T4_INFERENCE_SELECT_FIXED_DOSE_A_C_OR_A_D_ONE_PILL",
        "Select A + C or A + D",
        context_patch={
            "treatment_preferences": {
                "dose_strategy": "USUAL_DOSE",
                "combination_options": [["A", "C"], ["A", "D"]]
            }
        },
    )
    repeated_start = _node(
        "T6_INFERENCE_START_LOW_DOSE_A_PLUS_C_OR_A_PLUS_D",
        "Start A + C or A + D",
        context_patch={
            "treatment_preferences": {
                "dose_strategy": "LOW_DOSE",
                "combination_options": [["A", "C"], ["A", "D"]]
            }
        },
    )

    plan = _plan(glucose_lowering, base_selection, repeated_start)

    assert [
        [component.code for component in alternative.components]
        for alternative in plan.effective_regimen.base_options
    ] == [
        ["SGLT2i", "A", "C"],
        ["SGLT2i", "A", "D"],
        ["GLP1RA", "A", "C"],
        ["GLP1RA", "A", "D"],
    ]


def test_vietnamese_word_endings_are_not_parsed_as_abcd_classes() -> None:
    maintain = _node(
        "T6_INFERENCE_MAINTAIN_CURRENT_REGIMEN_NO_CHANGE_AFTER_NO_ADJUSTMENT",
        "Maintain regimen",
        text_vi="Duy trì phác đồ",
    )
    add_b = _node(
        "T6_INFERENCE_ADD_LOW_DOSE_B_BETA_BLOCKER",
        "Add beta-blocker",
        text_vi="Thêm thuốc chẹn Beta",
    )

    plan = _plan(maintain, add_b)

    assert [step.keyword for step in plan.steps] == [RegimenKeyword.MAINTAIN]
    assert plan.steps[0].components == []
    assert plan.effective_regimen.additions == []


@pytest.mark.parametrize(
    ("keyword", "bucket"),
    [
        ("COMBINE", "additions"),
        ("ADJUST", "adjustments"),
        ("CHANGE", "adjustments"),
        ("ESCALATE", "adjustments"),
        ("REDUCE", "adjustments"),
        ("KEEP", "adjustments"),
        ("MONITOR", "adjustments"),
        ("STOP", "stopped_components"),
        ("AVOID", "constraints"),
    ],
)
def test_treatment_keywords_keep_structured_components(keyword: str, bucket: str) -> None:
    node = _node(
        f"T6_INFERENCE_{keyword}_BETA_BLOCKER",
        f"{keyword} beta blocker",
        action_payload={
            "regimen_update": {"components": [{"selector_kind": "class", "code": "B"}]}
        },
    )

    plan = _plan(node)

    assert plan.steps[0].components[0].dose_strategy == "LOW_DOSE"
    assert getattr(plan.effective_regimen, bucket)


def test_maintain_ignores_even_accidental_structured_components() -> None:
    maintain = _node(
        "T6_INFERENCE_MAINTAIN_REGIMEN",
        "Maintain regimen",
        action_payload={
            "regimen_update": {"components": [{"selector_kind": "class", "code": "C"}]}
        },
    )

    plan = _plan(maintain)

    assert plan.steps[0].components == []
    assert plan.effective_regimen.additions == []
    assert plan.effective_regimen.adjustments == []

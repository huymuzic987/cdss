"""Read-only LINK/evidence checks discovered from the declared seeded trees."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import pytest
from sqlalchemy.orm import Session

from cdss.domain.decision_tree import (
    DecisionTreeError,
    EdgeDefinition,
    MissingRuntimePath,
    NodeDefinition,
    NodeType,
    RunState,
    TraversalResult,
    TreeDefinition,
    TreeGraph,
    walk_tree,
)
from cdss.domain.decision_tree.contracts import copy_json_value
from cdss.infrastructure.db.decision_tree_repository import SqlAlchemyTreeGraphRepository

pytestmark = pytest.mark.database

TREE_KEYS = [
    "hypertension-diagnosis",
    "risk-classification",
    "treatment-threshold-and-bp-target",
    "essential-treatment-strategy",
    "optimal-treatment-strategy",
    "hypertension-coronary-artery-disease",
]


@dataclass(frozen=True)
class SeededTrees:
    repository: SqlAlchemyTreeGraphRepository
    graphs: dict[str, TreeGraph]


@pytest.fixture(scope="module")
def seeded_trees(seeded_session: Session) -> SeededTrees:
    repository = SqlAlchemyTreeGraphRepository(seeded_session)
    return SeededTrees(
        repository=repository,
        graphs={tree_key: repository.get_tree(tree_key) for tree_key in TREE_KEYS},
    )


def test_tree_1_normal_bp_definition_applies_expected_context(seeded_trees: SeededTrees) -> None:
    graph = seeded_trees.graphs["hypertension-diagnosis"]
    node = _find_node(
        graph,
        lambda candidate: (
            _nested_value(
                candidate.context_patch,
                ("diagnosis", "hypertension_class"),
            )
            == "NORMAL_BP"
        ),
        "NORMAL_BP context patch",
    )

    state = _walk_from_exact_node(seeded_trees, graph, node, {})

    assert _nested_value(state.context, ("diagnosis", "hypertension_class")) == "NORMAL_BP"


def test_tree_1_emergency_link_resolves_into_seeded_tree(
    seeded_trees: SeededTrees,
) -> None:
    """hypertensive-emergency is now seeded (backups/cdss_merged.sql), so the LINK
    resolves and traversal continues into it instead of raising LinkTargetNotFound.
    The bridged walk carries no upstream input, so it fails on the tree's own first
    required field rather than reaching a terminal node.
    """
    graph = seeded_trees.graphs["hypertension-diagnosis"]
    node = _find_node(
        graph,
        lambda candidate: (
            candidate.node_type is NodeType.LINK
            and candidate.link_target_tree_key == "hypertensive-emergency"
        ),
        "hypertensive-emergency LINK",
    )

    with pytest.raises(MissingRuntimePath) as exc_info:
        walk_tree(
            _bridge_to(graph, node),
            {},
            repository=seeded_trees.repository,
        )

    partial = exc_info.value.partial_run_state
    assert partial is not None
    assert any(
        entry.tree_key == graph.tree.tree_key and entry.node_key == node.node_key
        for entry in partial.trace
    )
    assert any(entry.tree_key == "hypertensive-emergency" for entry in partial.trace)


def test_tree_9_generic_cad_uses_fallback_link_without_subtype_flags(
    seeded_trees: SeededTrees,
) -> None:
    graph = seeded_trees.graphs["hypertension-coronary-artery-disease"]
    node = graph.nodes_by_key["T9_C_BP1"]

    state = _walk_from_exact_node(
        seeded_trees,
        graph,
        node,
        {
            "age": 55,
            "current_clinic_sbp": 135,
            "current_clinic_dbp": 88,
            "facility_capability": "FULL_RESOURCES",
            "has_mi_acs": False,
            "has_ccs_angina": False,
            "has_ccs_revasc": False,
            "has_cabg": False,
        },
    )

    assert any(
        entry.tree_key == graph.tree.tree_key and entry.node_key == "T9_LINK_ESSENTIAL"
        for entry in state.trace
    )


def test_tree_3_restore_operation_copies_active_target_before_transfer(
    seeded_trees: SeededTrees,
) -> None:
    graph = seeded_trees.graphs["treatment-threshold-and-bp-target"]
    node = _find_node(
        graph,
        lambda candidate: _has_copy_operation(
            candidate,
            from_path="input.active_bp_target",
            to_path="context.treatment.bp_target",
        ),
        "active BP target COPY_PATH",
    )
    active_target = {"test_marker": "restored-target"}

    state = _walk_from_exact_node(
        seeded_trees,
        graph,
        node,
        {"active_bp_target": active_target},
    )

    assert _nested_value(state.context, ("treatment", "bp_target")) == active_target


def test_tree_4_or_5_target_reached_emits_seeded_vietnamese_text(
    seeded_trees: SeededTrees,
) -> None:
    expected_text = "Tiếp tục theo dõi và duy trì phác đồ"
    candidates = [
        (graph, node)
        for graph in (
            seeded_trees.graphs["essential-treatment-strategy"],
            seeded_trees.graphs["optimal-treatment-strategy"],
        )
        for node in graph.nodes_by_id.values()
        if node.node_type in {NodeType.ACTION, NodeType.END}
        and node.text_vi == expected_text
        and node.action_payload is not None
    ]
    if not candidates:
        pytest.fail("seeded target-reached ACTION/END with payload was not found")
    graph, node = candidates[0]

    state = _walk_from_exact_node(seeded_trees, graph, node, {})

    assert any(action.text_vi == expected_text for action in state.actions)


def test_drug_combination_link_resolves_and_retains_prior_execution_state(
    seeded_trees: SeededTrees,
) -> None:
    """drug-combination is now seeded (backups/cdss_merged.sql), so the LINK resolves
    and traversal continues into it instead of raising LinkTargetNotFound. The bridged
    walk carries no upstream input, so it fails on drug-combination's own first
    required field rather than reaching a terminal node, but the ACTION executed
    before the LINK is still retained in the partial state.
    """
    graphs = [
        seeded_trees.graphs["essential-treatment-strategy"],
        seeded_trees.graphs["optimal-treatment-strategy"],
    ]
    selected: tuple[TreeGraph, NodeDefinition, NodeDefinition] | None = None
    for graph in graphs:
        link = next(
            (
                node
                for node in graph.nodes_by_id.values()
                if node.node_type is NodeType.LINK
                and node.link_target_tree_key == "drug-combination"
            ),
            None,
        )
        if link is None:
            continue
        predecessors = [
            graph.nodes_by_id[edge.from_node_id]
            for edges in graph.outgoing_edges_by_node_id.values()
            for edge in edges
            if edge.to_node_id == link.id
        ]
        predecessor = next(
            (node for node in predecessors if node.action_payload is not None),
            None,
        )
        if predecessor is not None:
            selected = (graph, predecessor, link)
            break
    if selected is None:
        pytest.fail("seeded actionable node leading to drug-combination LINK was not found")
    graph, predecessor, link = selected

    with pytest.raises(MissingRuntimePath) as exc_info:
        walk_tree(
            _bridge_to(graph, predecessor),
            {},
            repository=seeded_trees.repository,
        )

    partial = exc_info.value.partial_run_state
    assert partial is not None
    if predecessor.node_type is NodeType.INFERENCE:
        assert partial.actions == []
    else:
        assert partial.actions
    assert partial.trace
    assert any(
        entry.tree_key == graph.tree.tree_key and entry.node_key == link.node_key
        for entry in partial.trace
    )
    assert any(entry.tree_key == "drug-combination" for entry in partial.trace)
    if predecessor.context_patch is not None:
        assert partial.context


def _walk_from_exact_node(
    seeded_trees: SeededTrees,
    graph: TreeGraph,
    node: NodeDefinition,
    runtime_input: dict[str, Any],
) -> RunState | TraversalResult:
    try:
        return walk_tree(
            _bridge_to(graph, node),
            runtime_input,
            repository=seeded_trees.repository,
        )
    except DecisionTreeError as exc:
        if exc.partial_run_state is None:
            raise
        return exc.partial_run_state


def _bridge_to(target_graph: TreeGraph, target_node: NodeDefinition) -> TreeGraph:
    tree = TreeDefinition(
        id=UUID(int=9000),
        tree_key=f"test-bridge-{target_graph.tree.tree_key}",
        name_en="Test bridge",
        name_vi="Test bridge",
    )
    start = NodeDefinition(
        id=UUID(int=9001),
        tree_id=tree.id,
        node_key="start",
        node_type=NodeType.START,
        text_en="start",
        text_vi="start",
    )
    link = NodeDefinition(
        id=UUID(int=9002),
        tree_id=tree.id,
        node_key="link",
        node_type=NodeType.LINK,
        text_en="link",
        text_vi="link",
        link_target_tree_key=target_graph.tree.tree_key,
        link_target_node_key=target_node.node_key,
    )
    edge = EdgeDefinition(
        id=UUID(int=9003),
        from_node_id=start.id,
        to_node_id=link.id,
        traversal_order=1,
        from_tree_id=tree.id,
        to_tree_id=tree.id,
    )
    return TreeGraph.build(tree=tree, nodes=[start, link], edges=[edge], references=[])


def _find_node(
    graph: TreeGraph,
    predicate: Any,
    description: str,
) -> NodeDefinition:
    node = next(
        (candidate for candidate in graph.nodes_by_id.values() if predicate(candidate)),
        None,
    )
    if node is None:
        pytest.fail(f"seeded definition not found: {description}")
    return node


def _nested_value(value: Any, path: tuple[str, ...]) -> Any:
    current = value
    for segment in path:
        if not isinstance(current, Mapping) or segment not in current:
            return None
        current = current[segment]
    return copy_json_value(current)


def _has_copy_operation(
    node: NodeDefinition,
    *,
    from_path: str,
    to_path: str,
) -> bool:
    patch = node.context_patch
    if not isinstance(patch, Mapping):
        return False
    operations = patch.get("operations")
    if not isinstance(operations, (list, tuple)):
        return False
    return any(
        isinstance(operation, Mapping)
        and operation.get("op") == "COPY_PATH"
        and operation.get("from_path") == from_path
        and operation.get("to_path") == to_path
        for operation in operations
    )

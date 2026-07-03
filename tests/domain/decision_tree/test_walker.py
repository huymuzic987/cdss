"""Synthetic tests for the internal-tree traversal loop."""

from collections.abc import Sequence
from typing import Any
from uuid import UUID

import pytest

from cdss.domain.decision_tree import (
    DEFAULT_MAX_STEPS,
    EdgeDefinition,
    InvalidRuntimeValueType,
    InvalidTreeStructure,
    LinkNotEnabled,
    NodeDefinition,
    NodeType,
    NoMatchingTransition,
    TraceEvent,
    TraversalLimitExceeded,
    TraversalTraceEntry,
    TreeDefinition,
    TreeGraph,
    walk_tree,
)

TREE_ID = UUID(int=500)
TREE = TreeDefinition(
    id=TREE_ID,
    tree_key="walker-test-tree",
    name_en="Walker test tree",
    name_vi="Cay thu nghiem walker",
)


def test_default_maximum_step_limit_is_300() -> None:
    assert DEFAULT_MAX_STEPS == 300


def _node(
    serial: int,
    node_key: str,
    node_type: NodeType,
    **values: Any,
) -> NodeDefinition:
    return NodeDefinition(
        id=UUID(int=serial),
        tree_id=TREE_ID,
        node_key=node_key,
        node_type=node_type,
        text_en=node_key,
        text_vi=node_key,
        display_order=serial,
        **values,
    )


def _edge(
    serial: int,
    source: NodeDefinition,
    target: NodeDefinition,
    traversal_order: int = 1,
) -> EdgeDefinition:
    return EdgeDefinition(
        id=UUID(int=serial),
        from_node_id=source.id,
        to_node_id=target.id,
        traversal_order=traversal_order,
        from_tree_id=TREE_ID,
        to_tree_id=TREE_ID,
    )


def _graph(nodes: list[NodeDefinition], edges: list[EdgeDefinition]) -> TreeGraph:
    return TreeGraph.build(tree=TREE, nodes=nodes, edges=edges, references=[])


def _entered_node_keys(trace: Sequence[TraversalTraceEntry]) -> list[str]:
    return [entry.node_key for entry in trace if entry.event is TraceEvent.NODE_ENTERED]


def test_first_matching_condition_wins() -> None:
    start = _node(1, "start", NodeType.START)
    first = _node(
        2,
        "first-condition",
        NodeType.CONDITION,
        condition_definition={"path": "input.value", "op": "gte", "value": 1},
    )
    second = _node(
        3,
        "second-condition",
        NodeType.CONDITION,
        condition_definition={"path": "input.value", "op": "gte", "value": 1},
    )
    first_action = _node(4, "first-action", NodeType.ACTION)
    second_action = _node(5, "second-action", NodeType.ACTION)
    graph = _graph(
        [start, first, second, first_action, second_action],
        [
            _edge(11, start, second, 2),
            _edge(10, start, first, 1),
            _edge(12, first, first_action),
            _edge(13, second, second_action),
        ],
    )

    result = walk_tree(graph, {"value": 5})

    assert _entered_node_keys(result.trace) == ["start", "first-condition", "first-action"]
    start_attempts = [
        entry
        for entry in result.trace
        if entry.event is TraceEvent.CANDIDATE_EVALUATED and entry.node_key == "start"
    ]
    assert [(entry.candidate_node_key, entry.condition_result) for entry in start_attempts] == [
        ("first-condition", True)
    ]


def test_failed_first_condition_then_successful_second_condition() -> None:
    start = _node(1, "start", NodeType.START)
    first = _node(
        2,
        "first-condition",
        NodeType.CONDITION,
        condition_definition={"path": "input.value", "op": "lt", "value": 0},
    )
    second = _node(
        3,
        "second-condition",
        NodeType.CONDITION,
        condition_definition={"path": "input.value", "op": "gte", "value": 0},
    )
    first_action = _node(4, "first-action", NodeType.ACTION)
    second_action = _node(5, "second-action", NodeType.ACTION)
    graph = _graph(
        [start, first, second, first_action, second_action],
        [
            _edge(10, start, first, 1),
            _edge(11, start, second, 2),
            _edge(12, first, first_action),
            _edge(13, second, second_action),
        ],
    )

    result = walk_tree(graph, {"value": 5})

    assert _entered_node_keys(result.trace) == ["start", "second-condition", "second-action"]
    start_attempts = [
        entry
        for entry in result.trace
        if entry.event is TraceEvent.CANDIDATE_EVALUATED and entry.node_key == "start"
    ]
    assert [(entry.candidate_node_key, entry.condition_result) for entry in start_attempts] == [
        ("first-condition", False),
        ("second-condition", True),
    ]


def test_unconditional_branch_is_selected_and_logged() -> None:
    start = _node(1, "start", NodeType.START)
    action = _node(2, "action", NodeType.ACTION)

    result = walk_tree(_graph([start, action], [_edge(10, start, action)]), {})

    candidate_entry = result.trace[1]
    assert candidate_entry.event is TraceEvent.CANDIDATE_EVALUATED
    assert candidate_entry.candidate_node_key == "action"
    assert candidate_entry.condition_definition is None
    assert candidate_entry.condition_result is True
    assert candidate_entry.evaluation_details == {
        "kind": "unconditional",
        "result": True,
    }


def test_terminal_action_finishes_successfully_and_collects_payload() -> None:
    start = _node(1, "start", NodeType.START)
    action = _node(
        2,
        "action",
        NodeType.ACTION,
        action_payload={"recommendation": "monitor"},
    )

    result = walk_tree(_graph([start, action], [_edge(10, start, action)]), {"value": 1})

    assert result.status == "success"
    assert _entered_node_keys(result.trace) == ["start", "action"]
    assert [item.payload for item in result.actions] == [{"recommendation": "monitor"}]
    assert result.input_snapshot.to_dict() == {"value": 1}


def test_terminal_end_applies_context_patch() -> None:
    start = _node(1, "start", NodeType.START)
    end = _node(
        2,
        "end",
        NodeType.END,
        context_patch={"diagnosis": {"status": "complete"}},
    )

    result = walk_tree(_graph([start, end], [_edge(10, start, end)]), {})

    assert result.context == {"diagnosis": {"status": "complete"}}
    end_entry = result.trace[-1]
    assert end_entry.node_key == "end"
    assert end_entry.changed_context_paths == ["context.diagnosis.status"]


def test_action_with_outgoing_edge_continues() -> None:
    start = _node(1, "start", NodeType.START)
    action = _node(
        2,
        "action",
        NodeType.ACTION,
        action_payload={"recommendation": "adjust"},
        context_patch={"treatment": {"adjusted": True}},
    )
    end = _node(3, "end", NodeType.END)
    graph = _graph(
        [start, action, end],
        [_edge(10, start, action), _edge(11, action, end)],
    )

    result = walk_tree(graph, {})

    assert _entered_node_keys(result.trace) == ["start", "action", "end"]
    assert result.context == {"treatment": {"adjusted": True}}
    assert [item.payload for item in result.actions] == [{"recommendation": "adjust"}]


def test_no_matching_transition_preserves_rejected_candidate_trace() -> None:
    start = _node(1, "start", NodeType.START)
    condition = _node(
        2,
        "condition",
        NodeType.CONDITION,
        condition_definition={"path": "input.value", "op": "gt", "value": 10},
    )
    action = _node(3, "action", NodeType.ACTION)
    graph = _graph(
        [start, condition, action],
        [_edge(10, start, condition), _edge(11, condition, action)],
    )

    with pytest.raises(NoMatchingTransition) as exc_info:
        walk_tree(graph, {"value": 5})

    partial = exc_info.value.partial_run_state
    assert partial is not None
    assert [(entry.event, entry.condition_result) for entry in partial.trace] == [
        (TraceEvent.NODE_ENTERED, None),
        (TraceEvent.CANDIDATE_EVALUATED, False),
    ]
    assert partial.trace[-1].candidate_node_key == "condition"


def test_internal_cycle_is_rejected_before_traversal() -> None:
    start = _node(1, "start", NodeType.START)
    first = _node(2, "first", NodeType.ACTION)
    second = _node(3, "second", NodeType.ACTION)
    graph = _graph(
        [start, first, second],
        [
            _edge(10, start, first),
            _edge(11, first, second),
            _edge(12, second, first),
        ],
    )

    with pytest.raises(InvalidTreeStructure) as exc_info:
        walk_tree(graph, {})

    assert exc_info.value.details["reason"] == "internal_graph_cycle"
    assert exc_info.value.partial_run_state is None


def test_traversal_step_limit_is_enforced_before_next_side_effect() -> None:
    start = _node(1, "start", NodeType.START)
    action = _node(
        2,
        "action",
        NodeType.ACTION,
        action_payload={"should_not_run": True},
    )

    with pytest.raises(TraversalLimitExceeded) as exc_info:
        walk_tree(
            _graph([start, action], [_edge(10, start, action)]),
            {},
            max_steps=1,
        )

    partial = exc_info.value.partial_run_state
    assert partial is not None
    assert _entered_node_keys(partial.trace) == ["start"]
    assert partial.actions == []
    assert exc_info.value.details == {"max_steps": 1}


def test_link_not_enabled_preserves_prior_state_and_link_entry() -> None:
    start = _node(1, "start", NodeType.START)
    action = _node(
        2,
        "action",
        NodeType.ACTION,
        action_payload={"recommendation": "prepare"},
        context_patch={"prepared": True},
    )
    link = _node(
        3,
        "link",
        NodeType.LINK,
        link_target_tree_key="external-tree",
    )
    graph = _graph(
        [start, action, link],
        [_edge(10, start, action), _edge(11, action, link)],
    )

    with pytest.raises(LinkNotEnabled) as exc_info:
        walk_tree(graph, {"request": "test"})

    partial = exc_info.value.partial_run_state
    assert partial is not None
    assert partial.input_snapshot.to_dict() == {"request": "test"}
    assert partial.context == {"prepared": True}
    assert [item.payload for item in partial.actions] == [{"recommendation": "prepare"}]
    assert _entered_node_keys(partial.trace) == ["start", "action", "link"]
    assert partial.trace[-1].event is TraceEvent.NODE_ENTERED
    assert exc_info.value.details["link_target_tree_key"] == "external-tree"


@pytest.mark.parametrize("bad_value", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_input_raises_typed_error_not_untyped_crash(bad_value: float) -> None:
    start = _node(1, "start", NodeType.START)
    action = _node(2, "action", NodeType.ACTION)
    graph = _graph([start, action], [_edge(10, start, action)])

    with pytest.raises(InvalidRuntimeValueType) as exc_info:
        walk_tree(graph, {"measurement": bad_value})

    assert exc_info.value.details["reason"] == "invalid_runtime_input"
    assert exc_info.value.tree_key == "walker-test-tree"
    # The fault precedes run-state creation, so there is no partial state.
    assert exc_info.value.partial_run_state is None


def test_candidate_evaluations_do_not_consume_the_step_budget() -> None:
    start = _node(1, "start", NodeType.START)
    cond_a = _node(
        2, "cond-a", NodeType.CONDITION,
        condition_definition={"op": "exists", "path": "input.absent"},
    )
    cond_b = _node(
        3, "cond-b", NodeType.CONDITION,
        condition_definition={"op": "exists", "path": "input.missing"},
    )
    end = _node(4, "end", NodeType.END)
    graph = _graph(
        [start, cond_a, cond_b, end],
        [
            _edge(10, start, cond_a, traversal_order=1),
            _edge(11, start, cond_b, traversal_order=2),
            _edge(12, start, end, traversal_order=3),
            _edge(13, cond_a, end),
            _edge(14, cond_b, end),
        ],
    )

    # Only two nodes are entered (start, end); the three candidate evaluations at
    # the start node are traced but must not count against the two-step budget.
    result = walk_tree(graph, {}, max_steps=2)

    assert result.status == "success"
    assert _entered_node_keys(result.trace) == ["start", "end"]
    assert len(result.trace) == 5


def test_trace_step_numbers_are_stable_and_monotonic() -> None:
    start = _node(1, "start", NodeType.START)
    action = _node(2, "action", NodeType.ACTION)

    result = walk_tree(_graph([start, action], [_edge(10, start, action)]), {})

    assert [entry.step for entry in result.trace] == [1, 2, 3]

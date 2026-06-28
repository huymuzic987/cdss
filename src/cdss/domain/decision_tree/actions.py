"""Action collection for entered decision-tree nodes."""

from __future__ import annotations

from cdss.domain.decision_tree.contracts import (
    ExecutedAction,
    NodeType,
    RunState,
    copy_json_value,
)
from cdss.domain.decision_tree.errors import InvalidTreeStructure
from cdss.domain.decision_tree.graph import NodeDefinition


def collect_action(
    node: NodeDefinition,
    run_state: RunState,
    *,
    tree_key: str,
) -> ExecutedAction | None:
    """Append a detached action payload for an ACTION or END node."""

    if node.action_payload is None:
        return None
    if node.node_type not in {NodeType.ACTION, NodeType.END}:
        raise InvalidTreeStructure(
            tree_key=tree_key,
            node_key=node.node_key,
            details={"reason": "action_payload_on_unsupported_node_type"},
            partial_run_state=run_state,
        )

    try:
        payload = copy_json_value(node.action_payload)
    except TypeError as exc:
        raise InvalidTreeStructure(
            tree_key=tree_key,
            node_key=node.node_key,
            details={"reason": "action_payload_is_not_json_object"},
            partial_run_state=run_state,
        ) from exc
    if not isinstance(payload, dict):
        raise InvalidTreeStructure(
            tree_key=tree_key,
            node_key=node.node_key,
            details={"reason": "action_payload_is_not_json_object"},
            partial_run_state=run_state,
        )

    action = ExecutedAction(
        tree_key=tree_key,
        node_key=node.node_key,
        node_type=node.node_type,
        text_en=node.text_en,
        text_vi=node.text_vi,
        payload=payload,
    )
    run_state.actions.append(action)
    return action

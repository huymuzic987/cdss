"""Cycle, reachability, and external-link validation."""

from collections.abc import Set
from uuid import UUID

from cdss.domain.decision_tree.contracts import JsonObject, NodeType
from cdss.domain.decision_tree.graph import NodeDefinition, TreeGraph
from cdss.domain.decision_tree.validation_errors import structure_error
from cdss.domain.decision_tree.validation_types import TreeValidationWarning


def validate_no_cycles(
    graph: TreeGraph,
    nodes: list[NodeDefinition],
    adjacency: dict[UUID, tuple[UUID, ...]],
) -> None:
    color: dict[UUID, int] = {}
    executable_nodes = [node for node in nodes if node.node_type is not NodeType.GLOBAL]
    for root in executable_nodes:
        if color.get(root.id, 0) != 0:
            continue
        color[root.id] = 1
        stack: list[tuple[UUID, int]] = [(root.id, 0)]
        while stack:
            node_id, next_index = stack[-1]
            targets = adjacency[node_id]
            if next_index >= len(targets):
                color[node_id] = 2
                stack.pop()
                continue
            target_id = targets[next_index]
            stack[-1] = (node_id, next_index + 1)
            target_color = color.get(target_id, 0)
            if target_color == 1:
                raise structure_error(
                    graph,
                    node=graph.nodes_by_id[node_id],
                    reason="internal_graph_cycle",
                    target_node_key=graph.nodes_by_id[target_id].node_key,
                )
            if target_color == 0:
                color[target_id] = 1
                stack.append((target_id, 0))


def validate_reachability(
    graph: TreeGraph,
    nodes: list[NodeDefinition],
    adjacency: dict[UUID, tuple[UUID, ...]],
    start_node_id: UUID,
) -> None:
    reachable: set[UUID] = set()
    pending = [start_node_id]
    while pending:
        node_id = pending.pop()
        if node_id in reachable:
            continue
        reachable.add(node_id)
        pending.extend(adjacency[node_id])

    unreachable = [
        node.node_key
        for node in nodes
        if node.node_type is not NodeType.GLOBAL and node.id not in reachable
    ]
    if unreachable:
        raise structure_error(
            graph,
            reason="unreachable_executable_nodes",
            unreachable_node_keys=unreachable,
        )


def validate_link_targets(
    graph: TreeGraph,
    nodes: list[NodeDefinition],
    *,
    available_tree_keys: Set[str] | None,
    strict_link_targets: bool,
) -> list[TreeValidationWarning]:
    if available_tree_keys is None:
        return []

    warnings: list[TreeValidationWarning] = []
    for node in nodes:
        if node.node_type is not NodeType.LINK:
            continue
        target_tree_key = node.link_target_tree_key
        if target_tree_key is None or target_tree_key in available_tree_keys:
            continue
        details: JsonObject = {"target_tree_key": target_tree_key}
        if strict_link_targets:
            raise structure_error(
                graph,
                node=node,
                reason="unseeded_link_target",
                target_tree_key=target_tree_key,
            )
        warnings.append(
            TreeValidationWarning(
                code="unseeded_link_target",
                message="Linked target tree is not currently available.",
                tree_key=graph.tree.tree_key,
                node_key=node.node_key,
                details=details,
            )
        )
    return warnings

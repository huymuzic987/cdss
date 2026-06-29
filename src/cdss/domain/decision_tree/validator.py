"""Reusable structural validation for loaded decision-tree graphs."""

from __future__ import annotations

from collections.abc import Mapping, Set
from typing import Any
from uuid import UUID

from pydantic import Field

from cdss.domain.decision_tree.conditions import validate_condition_definition
from cdss.domain.decision_tree.contracts import (
    JsonObject,
    NodeType,
    RuntimeModel,
    copy_json_value,
)
from cdss.domain.decision_tree.errors import (
    ContextPatchError,
    InvalidStartNode,
    InvalidTreeStructure,
)
from cdss.domain.decision_tree.graph import EdgeDefinition, NodeDefinition, TreeGraph


class TreeValidationWarning(RuntimeModel):
    code: str
    message: str
    tree_key: str
    node_key: str | None = None
    details: JsonObject = Field(default_factory=dict)


class TreeValidationResult(RuntimeModel):
    tree_key: str
    warnings: list[TreeValidationWarning] = Field(default_factory=list)


def validate_tree_graph(
    graph: TreeGraph,
    *,
    available_tree_keys: Set[str] | None = None,
    strict_link_targets: bool = False,
) -> TreeValidationResult:
    """Validate one graph and report unavailable external links as warnings."""

    tree = graph.tree
    nodes = sorted(
        graph.nodes_by_id.values(),
        key=lambda node: (node.display_order, node.node_key, str(node.id)),
    )
    for node in nodes:
        if node.tree_id != tree.id:
            raise _structure_error(
                graph,
                node=node,
                reason="node_belongs_to_another_tree",
                node_id=str(node.id),
            )

    start_nodes = [node for node in nodes if node.node_type is NodeType.START]
    if len(start_nodes) != 1 or graph.start_node.id != start_nodes[0].id:
        raise InvalidStartNode(
            tree_key=tree.tree_key,
            details={"start_node_count": len(start_nodes)},
        )

    adjacency, outgoing_counts = _validate_edges(graph)
    _validate_node_semantics(graph, nodes, outgoing_counts)
    _validate_no_cycles(graph, nodes, adjacency)
    _validate_reachability(graph, nodes, adjacency, start_nodes[0].id)

    warnings = _validate_link_targets(
        graph,
        nodes,
        available_tree_keys=available_tree_keys,
        strict_link_targets=strict_link_targets,
    )
    return TreeValidationResult(tree_key=tree.tree_key, warnings=warnings)


def _validate_edges(
    graph: TreeGraph,
) -> tuple[dict[UUID, tuple[UUID, ...]], dict[UUID, int]]:
    nodes_by_id = graph.nodes_by_id
    adjacency_lists: dict[UUID, list[UUID]] = {node_id: [] for node_id in nodes_by_id}
    outgoing_counts: dict[UUID, int] = {node_id: 0 for node_id in nodes_by_id}
    edge_ids: set[UUID] = set()
    edge_targets: set[tuple[UUID, UUID]] = set()
    traversal_orders: set[tuple[UUID, int]] = set()

    for bucket_node_id, bucket in graph.outgoing_edges_by_node_id.items():
        if bucket_node_id not in nodes_by_id:
            raise _structure_error(
                graph,
                reason="outgoing_edge_bucket_has_missing_source",
                node_id=str(bucket_node_id),
            )
        for edge in bucket:
            from_node = nodes_by_id.get(edge.from_node_id)
            to_node = nodes_by_id.get(edge.to_node_id)
            if edge.from_node_id != bucket_node_id:
                raise _structure_error(
                    graph,
                    node=from_node,
                    reason="edge_stored_under_wrong_source",
                    edge_id=str(edge.id),
                )
            if _edge_crosses_tree(graph, edge) or from_node is None or to_node is None:
                raise _structure_error(
                    graph,
                    node=from_node,
                    reason="cross_tree_or_missing_edge_endpoint",
                    edge_id=str(edge.id),
                    from_node_id=str(edge.from_node_id),
                    to_node_id=str(edge.to_node_id),
                )
            if from_node.node_type is NodeType.GLOBAL or to_node.node_type is NodeType.GLOBAL:
                raise _structure_error(
                    graph,
                    node=from_node,
                    reason="global_node_has_internal_edge",
                    edge_id=str(edge.id),
                )
            if edge.id in edge_ids:
                raise _structure_error(
                    graph,
                    node=from_node,
                    reason="duplicate_edge_id",
                    edge_id=str(edge.id),
                )
            edge_target = (edge.from_node_id, edge.to_node_id)
            if edge_target in edge_targets:
                raise _structure_error(
                    graph,
                    node=from_node,
                    reason="duplicate_edge_target",
                    edge_id=str(edge.id),
                )
            traversal_order = (edge.from_node_id, edge.traversal_order)
            if traversal_order in traversal_orders:
                raise _structure_error(
                    graph,
                    node=from_node,
                    reason="duplicate_outgoing_traversal_order",
                    traversal_order=edge.traversal_order,
                )

            edge_ids.add(edge.id)
            edge_targets.add(edge_target)
            traversal_orders.add(traversal_order)
            adjacency_lists[edge.from_node_id].append(edge.to_node_id)
            outgoing_counts[edge.from_node_id] += 1

    adjacency = {node_id: tuple(targets) for node_id, targets in adjacency_lists.items()}
    return adjacency, outgoing_counts


def _edge_crosses_tree(graph: TreeGraph, edge: EdgeDefinition) -> bool:
    tree_id = graph.tree.id
    endpoint_tree_ids = (edge.from_tree_id, edge.to_tree_id)
    if any(value is not None and value != tree_id for value in endpoint_tree_ids):
        return True
    from_node = graph.nodes_by_id.get(edge.from_node_id)
    to_node = graph.nodes_by_id.get(edge.to_node_id)
    return any(node is not None and node.tree_id != tree_id for node in (from_node, to_node))


def _validate_node_semantics(
    graph: TreeGraph,
    nodes: list[NodeDefinition],
    outgoing_counts: dict[UUID, int],
) -> None:
    for node in nodes:
        outgoing_count = outgoing_counts[node.id]
        if node.node_type in {NodeType.START, NodeType.CONDITION, NodeType.INFERENCE}:
            if outgoing_count == 0:
                raise _structure_error(
                    graph,
                    node=node,
                    reason="node_requires_outgoing_edge",
                    node_type=node.node_type.value,
                )
        elif node.node_type in {NodeType.END, NodeType.LINK} and outgoing_count != 0:
            raise _structure_error(
                graph,
                node=node,
                reason="terminal_node_has_internal_edge",
                node_type=node.node_type.value,
            )

        if node.node_type is NodeType.LINK and not (
            isinstance(node.link_target_tree_key, str) and node.link_target_tree_key.strip()
        ):
            raise _structure_error(
                graph,
                node=node,
                reason="link_target_tree_key_required",
            )

        if node.condition_definition is not None:
            validate_condition_definition(
                node.condition_definition,
                tree_key=graph.tree.tree_key,
                node_key=node.node_key,
            )
        elif node.node_type is NodeType.CONDITION:
            validate_condition_definition(
                None,
                tree_key=graph.tree.tree_key,
                node_key=node.node_key,
            )

        _validate_context_patch(graph, node)


def _validate_context_patch(graph: TreeGraph, node: NodeDefinition) -> None:
    patch = node.context_patch
    if patch is None:
        return
    if not isinstance(patch, Mapping):
        raise _context_patch_error(graph, node, "context_patch_must_be_object")

    for key, value in patch.items():
        if not isinstance(key, str):
            raise _context_patch_error(graph, node, "context_patch_keys_must_be_strings")
        if key != "operations":
            try:
                copy_json_value(value)
            except TypeError as exc:
                raise _context_patch_error(graph, node, "context_patch_value_is_not_json") from exc

    if "operations" not in patch:
        return
    operations = patch["operations"]
    if not isinstance(operations, (list, tuple)):
        raise _context_patch_error(graph, node, "operations_must_be_array")

    for operation_index, operation in enumerate(operations):
        _validate_context_operation(graph, node, operation, operation_index)


def _validate_context_operation(
    graph: TreeGraph,
    node: NodeDefinition,
    operation: Any,
    operation_index: int,
) -> None:
    if not isinstance(operation, Mapping):
        raise _context_patch_error(
            graph, node, "operation_must_be_object", operation_index=operation_index
        )
    allowed_keys = {"op", "from_path", "to_path", "required"}
    if not set(operation).issubset(allowed_keys):
        raise _context_patch_error(
            graph,
            node,
            "operation_contains_unknown_keys",
            operation_index=operation_index,
        )
    if operation.get("op") != "COPY_PATH":
        raise _context_patch_error(
            graph,
            node,
            "unsupported_context_operation",
            operation_index=operation_index,
        )
    if "from_path" not in operation or "to_path" not in operation:
        raise _context_patch_error(
            graph,
            node,
            "copy_path_requires_source_and_target",
            operation_index=operation_index,
        )
    if not isinstance(operation.get("required", False), bool):
        raise _context_patch_error(
            graph,
            node,
            "copy_path_required_must_be_boolean",
            operation_index=operation_index,
        )
    _validate_patch_path(
        graph,
        node,
        operation["from_path"],
        roots={"input", "context"},
        role="source",
        operation_index=operation_index,
    )
    _validate_patch_path(
        graph,
        node,
        operation["to_path"],
        roots={"context"},
        role="target",
        operation_index=operation_index,
    )


def _validate_patch_path(
    graph: TreeGraph,
    node: NodeDefinition,
    path: Any,
    *,
    roots: set[str],
    role: str,
    operation_index: int,
) -> None:
    if not isinstance(path, str):
        raise _context_patch_error(
            graph,
            node,
            f"copy_{role}_path_must_be_string",
            operation_index=operation_index,
        )
    parts = path.split(".")
    if len(parts) < 2 or parts[0] not in roots or any(not part for part in parts):
        raise _context_patch_error(
            graph,
            node,
            f"invalid_copy_{role}_path",
            operation_index=operation_index,
            path=path,
        )


def _validate_no_cycles(
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
                raise _structure_error(
                    graph,
                    node=graph.nodes_by_id[node_id],
                    reason="internal_graph_cycle",
                    target_node_key=graph.nodes_by_id[target_id].node_key,
                )
            if target_color == 0:
                color[target_id] = 1
                stack.append((target_id, 0))


def _validate_reachability(
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
        raise _structure_error(
            graph,
            reason="unreachable_executable_nodes",
            unreachable_node_keys=unreachable,
        )


def _validate_link_targets(
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
            raise _structure_error(
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


def _structure_error(
    graph: TreeGraph,
    *,
    reason: str,
    node: NodeDefinition | None = None,
    **details: Any,
) -> InvalidTreeStructure:
    return InvalidTreeStructure(
        tree_key=graph.tree.tree_key,
        node_key=node.node_key if node is not None else None,
        details={"reason": reason, **details},
    )


def _context_patch_error(
    graph: TreeGraph,
    node: NodeDefinition,
    reason: str,
    **details: Any,
) -> ContextPatchError:
    return ContextPatchError(
        tree_key=graph.tree.tree_key,
        node_key=node.node_key,
        details={"reason": reason, **details},
    )

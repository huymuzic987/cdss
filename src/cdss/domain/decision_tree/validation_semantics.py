"""Node semantics and context-patch definition validation."""

from collections.abc import Mapping
from typing import Any
from uuid import UUID

from cdss.domain.decision_tree.conditions import validate_condition_definition
from cdss.domain.decision_tree.contracts import NodeType, copy_json_value
from cdss.domain.decision_tree.graph import NodeDefinition, TreeGraph
from cdss.domain.decision_tree.validation_errors import context_patch_error, structure_error
from cdss.domain.decision_tree.validation_regimen import validate_regimen_update


def validate_node_semantics(
    graph: TreeGraph,
    nodes: list[NodeDefinition],
    outgoing_counts: dict[UUID, int],
) -> None:
    for node in nodes:
        outgoing_count = outgoing_counts[node.id]
        if node.node_type in {NodeType.START, NodeType.CONDITION, NodeType.INFERENCE}:
            if outgoing_count == 0:
                raise structure_error(
                    graph,
                    node=node,
                    reason="node_requires_outgoing_edge",
                    node_type=node.node_type.value,
                )
        elif node.node_type in {NodeType.END, NodeType.LINK} and outgoing_count != 0:
            raise structure_error(
                graph,
                node=node,
                reason="terminal_node_has_internal_edge",
                node_type=node.node_type.value,
            )

        if node.node_type is NodeType.LINK and not (
            isinstance(node.link_target_tree_key, str) and node.link_target_tree_key.strip()
        ):
            raise structure_error(
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

        validate_context_patch(graph, node)
        validate_regimen_update(graph, node)


def validate_context_patch(graph: TreeGraph, node: NodeDefinition) -> None:
    patch = node.context_patch
    if patch is None:
        return
    if not isinstance(patch, Mapping):
        raise context_patch_error(graph, node, "context_patch_must_be_object")

    for key, value in patch.items():
        if not isinstance(key, str):
            raise context_patch_error(graph, node, "context_patch_keys_must_be_strings")
        if key != "operations":
            try:
                copy_json_value(value)
            except TypeError as exc:
                raise context_patch_error(graph, node, "context_patch_value_is_not_json") from exc

    if "operations" not in patch:
        return
    operations = patch["operations"]
    if not isinstance(operations, (list, tuple)):
        raise context_patch_error(graph, node, "operations_must_be_array")

    for operation_index, operation in enumerate(operations):
        validate_context_operation(graph, node, operation, operation_index)


def validate_context_operation(
    graph: TreeGraph,
    node: NodeDefinition,
    operation: Any,
    operation_index: int,
) -> None:
    if not isinstance(operation, Mapping):
        raise context_patch_error(
            graph, node, "operation_must_be_object", operation_index=operation_index
        )
    allowed_keys = {"op", "from_path", "to_path", "required"}
    if not set(operation).issubset(allowed_keys):
        raise context_patch_error(
            graph,
            node,
            "operation_contains_unknown_keys",
            operation_index=operation_index,
        )
    if operation.get("op") != "COPY_PATH":
        raise context_patch_error(
            graph,
            node,
            "unsupported_context_operation",
            operation_index=operation_index,
        )
    if "from_path" not in operation or "to_path" not in operation:
        raise context_patch_error(
            graph,
            node,
            "copy_path_requires_source_and_target",
            operation_index=operation_index,
        )
    if not isinstance(operation.get("required", False), bool):
        raise context_patch_error(
            graph,
            node,
            "copy_path_required_must_be_boolean",
            operation_index=operation_index,
        )
    validate_patch_path(
        graph,
        node,
        operation["from_path"],
        roots={"input", "context"},
        role="source",
        operation_index=operation_index,
    )
    validate_patch_path(
        graph,
        node,
        operation["to_path"],
        roots={"context"},
        role="target",
        operation_index=operation_index,
    )


def validate_patch_path(
    graph: TreeGraph,
    node: NodeDefinition,
    path: Any,
    *,
    roots: set[str],
    role: str,
    operation_index: int,
) -> None:
    if not isinstance(path, str):
        raise context_patch_error(
            graph,
            node,
            f"copy_{role}_path_must_be_string",
            operation_index=operation_index,
        )
    parts = path.split(".")
    if len(parts) < 2 or parts[0] not in roots or any(not part for part in parts):
        raise context_patch_error(
            graph,
            node,
            f"invalid_copy_{role}_path",
            operation_index=operation_index,
            path=path,
        )

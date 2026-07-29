"""Immutable copying and structural errors used during graph construction."""

from collections.abc import Mapping
from dataclasses import replace
from typing import Any

from cdss.domain.decision_tree.contracts import FrozenJsonObject
from cdss.domain.decision_tree.errors import InvalidTreeStructure
from cdss.domain.decision_tree.graph import (
    EdgeDefinition,
    NodeDefinition,
    SourceReferenceDefinition,
    TreeDefinition,
)


def freeze_node(tree: TreeDefinition, node: NodeDefinition) -> NodeDefinition:
    frozen_values: dict[str, FrozenJsonObject | None] = {}
    for field_name in (
        "condition_definition",
        "context_patch",
        "action_payload",
        "global_config",
    ):
        value = getattr(node, field_name)
        if value is None or isinstance(value, FrozenJsonObject):
            frozen_values[field_name] = value
        elif isinstance(value, Mapping):
            try:
                frozen_values[field_name] = FrozenJsonObject(value)
            except TypeError as exc:
                raise invalid_structure(
                    tree,
                    node_key=node.node_key,
                    reason="invalid_node_json",
                    field=field_name,
                ) from exc
        else:
            raise invalid_structure(
                tree,
                node_key=node.node_key,
                reason="invalid_node_json",
                field=field_name,
            )
    return replace(node, **frozen_values)


def freeze_reference(reference: SourceReferenceDefinition) -> SourceReferenceDefinition:
    return replace(
        reference,
        section_path=freeze_json_value(reference.section_path),
        printed_page_numbers=(
            tuple(reference.printed_page_numbers)
            if reference.printed_page_numbers is not None
            else None
        ),
        pdf_page_numbers=(
            tuple(reference.pdf_page_numbers) if reference.pdf_page_numbers is not None else None
        ),
    )


def freeze_json_value(value: Any) -> Any:
    return FrozenJsonObject({"value": value})["value"]


def validate_edge_tree_ownership(tree: TreeDefinition, edge: EdgeDefinition) -> None:
    endpoint_tree_ids = (edge.from_tree_id, edge.to_tree_id)
    if any(tree_id is not None and tree_id != tree.id for tree_id in endpoint_tree_ids):
        raise invalid_structure(
            tree,
            reason="cross_tree_edge",
            edge_id=str(edge.id),
            from_tree_id=str(edge.from_tree_id) if edge.from_tree_id is not None else None,
            to_tree_id=str(edge.to_tree_id) if edge.to_tree_id is not None else None,
        )


def invalid_structure(
    tree: TreeDefinition,
    *,
    reason: str,
    node_key: str | None = None,
    **details: Any,
) -> InvalidTreeStructure:
    return InvalidTreeStructure(
        tree_key=tree.tree_key,
        node_key=node_key,
        details={"reason": reason, **details},
    )

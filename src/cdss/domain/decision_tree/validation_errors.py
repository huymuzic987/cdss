"""Domain error factories for tree validation."""

from typing import Any

from cdss.domain.decision_tree.errors import ContextPatchError, InvalidTreeStructure
from cdss.domain.decision_tree.graph import NodeDefinition, TreeGraph


def structure_error(
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


def context_patch_error(
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

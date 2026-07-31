"""Bulk SQLAlchemy loader for immutable decision-tree graphs."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session, aliased

from cdss.domain.decision_tree.contracts import NodeType
from cdss.domain.decision_tree.errors import InvalidTreeStructure, TreeNotFound
from cdss.domain.decision_tree.graph import (
    EdgeDefinition,
    NodeDefinition,
    SourceReferenceDefinition,
    TreeDefinition,
    TreeGraph,
    TreeGraphRepository,
)
from cdss.infrastructure.db.models import (
    DecisionEdge,
    DecisionNode,
    DecisionTree,
    NodeSourceReference,
)
from cdss.infrastructure.db.runtime_graph_overrides import apply_runtime_graph_overrides


def _coerce_node_type(node: DecisionNode, tree_key: str) -> NodeType:
    """Map a stored node type to the domain enum, failing typed on divergence."""

    try:
        return NodeType(node.node_type.value)
    except ValueError as exc:
        raise InvalidTreeStructure(
            tree_key=tree_key,
            node_key=node.node_key,
            details={"reason": "unknown_node_type", "node_type": str(node.node_type.value)},
        ) from exc


class SqlAlchemyTreeGraphRepository(TreeGraphRepository):
    """Load a tree in four bounded queries without ORM relationship access."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_trees(self) -> Sequence[TreeDefinition]:
        tree_rows = (
            self._session.execute(select(DecisionTree).order_by(DecisionTree.name_en))
            .scalars()
            .all()
        )
        return [
            TreeDefinition(
                id=tree_row.id,
                tree_key=tree_row.tree_key,
                name_en=tree_row.name_en,
                name_vi=tree_row.name_vi,
            )
            for tree_row in tree_rows
        ]

    def get_tree(self, tree_key: str) -> TreeGraph:
        tree_row = self._session.execute(
            select(DecisionTree).where(DecisionTree.tree_key == tree_key)
        ).scalar_one_or_none()
        if tree_row is None:
            raise TreeNotFound(tree_key=tree_key)

        node_rows = (
            self._session.execute(select(DecisionNode).where(DecisionNode.tree_id == tree_row.id))
            .scalars()
            .all()
        )

        source_node = aliased(DecisionNode, name="source_node")
        target_node = aliased(DecisionNode, name="target_node")
        edge_rows = self._session.execute(
            select(DecisionEdge, source_node.tree_id, target_node.tree_id)
            .join(source_node, DecisionEdge.from_node_id == source_node.id)
            .join(target_node, DecisionEdge.to_node_id == target_node.id)
            .where(source_node.tree_id == tree_row.id)
        ).all()

        reference_rows = (
            self._session.execute(
                select(NodeSourceReference)
                .join(DecisionNode, NodeSourceReference.node_id == DecisionNode.id)
                .where(DecisionNode.tree_id == tree_row.id)
            )
            .scalars()
            .all()
        )

        tree = TreeDefinition(
            id=tree_row.id,
            tree_key=tree_row.tree_key,
            name_en=tree_row.name_en,
            name_vi=tree_row.name_vi,
        )
        nodes = [
            NodeDefinition(
                id=node.id,
                tree_id=node.tree_id,
                node_key=node.node_key,
                node_type=_coerce_node_type(node, tree_row.tree_key),
                text_en=node.text_en,
                text_vi=node.text_vi,
                condition_definition=node.condition_definition,
                context_patch=node.context_patch,
                action_payload=node.action_payload,
                global_config=node.global_config,
                link_target_tree_key=node.link_target_tree_key,
                link_target_node_key=node.link_target_node_key,
                display_order=node.display_order,
            )
            for node in node_rows
        ]
        edges = [
            EdgeDefinition(
                id=edge.id,
                from_node_id=edge.from_node_id,
                to_node_id=edge.to_node_id,
                traversal_order=edge.traversal_order,
                from_tree_id=from_tree_id,
                to_tree_id=to_tree_id,
            )
            for edge, from_tree_id, to_tree_id in edge_rows
        ]
        references = [
            SourceReferenceDefinition(
                id=reference.id,
                node_id=reference.node_id,
                source_title=reference.source_title,
                section_path=reference.section_path,
                reference_order=reference.reference_order,
                locator=reference.locator,
                locator_detail=reference.locator_detail,
                printed_page_numbers=(
                    tuple(reference.printed_page_numbers)
                    if reference.printed_page_numbers is not None
                    else None
                ),
                pdf_page_numbers=(
                    tuple(reference.pdf_page_numbers)
                    if reference.pdf_page_numbers is not None
                    else None
                ),
                reference_note=reference.reference_note,
            )
            for reference in reference_rows
        ]
        nodes, edges = apply_runtime_graph_overrides(tree, nodes, edges)

        return TreeGraph.build(
            tree=tree,
            nodes=nodes,
            edges=edges,
            references=references,
        )

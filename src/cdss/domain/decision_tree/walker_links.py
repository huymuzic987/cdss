"""Cross-tree link resolution during traversal."""

from typing import Any

from cdss.domain.decision_tree.contracts import NodeType, RunState
from cdss.domain.decision_tree.errors import (
    DecisionTreeError,
    InvalidTreeStructure,
    LinkNotEnabled,
    LinkTargetNodeNotFound,
    LinkTargetNotFound,
    TreeNotFound,
)
from cdss.domain.decision_tree.graph import NodeDefinition, TreeGraph, TreeGraphRepository


class LinkTraversalMixin:
    graph: TreeGraph
    run_state: RunState
    repository: TreeGraphRepository | None
    links_enabled: bool
    validated_graph_ids: set[tuple[str, Any]]
    _record_tree_metadata: Any
    validate_graph: Any

    def _follow_link(self, link_node: NodeDefinition) -> tuple[TreeGraph, NodeDefinition]:
        target_tree_key = link_node.link_target_tree_key
        if not self.links_enabled or self.repository is None:
            raise LinkNotEnabled(
                tree_key=self.graph.tree.tree_key,
                node_key=link_node.node_key,
                details={
                    "link_target_tree_key": target_tree_key,
                    "link_target_node_key": link_node.link_target_node_key,
                },
                partial_run_state=self.run_state,
            )
        if not isinstance(target_tree_key, str) or not target_tree_key.strip():
            raise InvalidTreeStructure(
                tree_key=self.graph.tree.tree_key,
                node_key=link_node.node_key,
                details={"reason": "link_target_tree_key_required"},
                partial_run_state=self.run_state,
            )

        try:
            target_graph = self.repository.get_tree(target_tree_key)
        except TreeNotFound as exc:
            raise LinkTargetNotFound(
                tree_key=self.graph.tree.tree_key,
                node_key=link_node.node_key,
                details={"link_target_tree_key": target_tree_key},
                partial_run_state=self.run_state,
            ) from exc
        except DecisionTreeError as exc:
            self._attach_partial_state(exc)
            raise

        try:
            self._validate_graph_once(target_graph)
            self._record_tree_metadata(target_graph)
        except DecisionTreeError as exc:
            self._attach_partial_state(exc)
            raise

        target_node_key = link_node.link_target_node_key
        if target_node_key is None:
            target_node = target_graph.start_node
        else:
            target_node = target_graph.nodes_by_key.get(target_node_key)
            if target_node is None or target_node.node_type is NodeType.GLOBAL:
                raise LinkTargetNodeNotFound(
                    tree_key=target_tree_key,
                    node_key=target_node_key,
                    details={
                        "source_tree_key": self.graph.tree.tree_key,
                        "source_node_key": link_node.node_key,
                    },
                    partial_run_state=self.run_state,
                )

        return target_graph, target_node

    def _validate_graph_once(self, graph: TreeGraph) -> None:
        identity = (graph.tree.tree_key, graph.tree.id)
        if identity in self.validated_graph_ids:
            return
        self.validate_graph(graph)
        self.validated_graph_ids.add(identity)

    def _attach_partial_state(self, error: DecisionTreeError) -> None:
        if error.partial_run_state is None:
            error.partial_run_state = self.run_state.snapshot()

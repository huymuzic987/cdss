"""Candidate transition selection during traversal."""

from collections.abc import Mapping
from typing import Any, cast

from cdss.domain.decision_tree.conditions import evaluate_candidate_condition
from cdss.domain.decision_tree.contracts import (
    JsonObject,
    NodeType,
    RunState,
    TraceEvent,
    copy_json_value,
)
from cdss.domain.decision_tree.errors import InvalidTreeStructure, NoMatchingTransition
from cdss.domain.decision_tree.graph import EdgeDefinition, NodeDefinition, TreeGraph


class TransitionTraversalMixin:
    graph: TreeGraph
    run_state: RunState
    _append_trace: Any

    def _select_next_node(
        self,
        current: NodeDefinition,
        outgoing_edges: tuple[EdgeDefinition, ...],
    ) -> NodeDefinition:
        for edge in sorted(outgoing_edges, key=lambda item: item.traversal_order):
            candidate = self.graph.nodes_by_id.get(edge.to_node_id)
            if candidate is None:
                raise InvalidTreeStructure(
                    tree_key=self.graph.tree.tree_key,
                    node_key=current.node_key,
                    details={
                        "reason": "edge_target_missing_from_graph",
                        "edge_id": str(edge.id),
                        "target_node_id": str(edge.to_node_id),
                    },
                    partial_run_state=self.run_state,
                )
            if candidate.node_type is NodeType.GLOBAL:
                raise InvalidTreeStructure(
                    tree_key=self.graph.tree.tree_key,
                    node_key=current.node_key,
                    details={
                        "reason": "global_node_selected_as_candidate",
                        "candidate_node_key": candidate.node_key,
                    },
                    partial_run_state=self.run_state,
                )

            evaluation = evaluate_candidate_condition(
                candidate.node_type,
                candidate.condition_definition,
                self.run_state,
                tree_key=self.graph.tree.tree_key,
                node_key=candidate.node_key,
            )
            condition_definition = optional_json_object(candidate.condition_definition)
            self._append_trace(
                event=TraceEvent.CANDIDATE_EVALUATED,
                node=current,
                candidate_node_key=candidate.node_key,
                condition_definition=condition_definition,
                condition_result=evaluation.result,
                evaluation_details=evaluation.details,
            )
            if evaluation.result:
                return candidate

        raise NoMatchingTransition(
            tree_key=self.graph.tree.tree_key,
            node_key=current.node_key,
            details={"outgoing_candidate_count": len(outgoing_edges)},
            partial_run_state=self.run_state,
        )


def optional_json_object(value: Mapping[str, Any] | None) -> JsonObject | None:
    if value is None:
        return None
    copied = copy_json_value(value)
    return cast(JsonObject, copied)

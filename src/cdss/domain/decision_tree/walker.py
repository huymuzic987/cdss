"""Decision-tree traversal with cross-tree tail-link execution."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

from cdss.domain.decision_tree.actions import collect_action
from cdss.domain.decision_tree.conditions import evaluate_candidate_condition
from cdss.domain.decision_tree.contracts import (
    ExecutedReference,
    JsonObject,
    NodeType,
    RunState,
    TraceEvent,
    TraversalResult,
    TraversalTraceEntry,
    TreeMetadata,
    copy_json_value,
)
from cdss.domain.decision_tree.errors import (
    DecisionTreeError,
    InvalidRuntimeValueType,
    InvalidTreeStructure,
    LinkNotEnabled,
    LinkTargetNodeNotFound,
    LinkTargetNotFound,
    NoMatchingTransition,
    TraversalCycleDetected,
    TraversalLimitExceeded,
    TreeNotFound,
)
from cdss.domain.decision_tree.graph import (
    EdgeDefinition,
    NodeDefinition,
    SourceReferenceDefinition,
    TreeGraph,
    TreeGraphRepository,
)
from cdss.domain.decision_tree.patches import apply_context_patch
from cdss.domain.decision_tree.validator import validate_tree_graph

DEFAULT_MAX_STEPS = 300


def walk_tree(
    graph: TreeGraph,
    runtime_input: Mapping[str, Any],
    *,
    max_steps: int = DEFAULT_MAX_STEPS,
    repository: TreeGraphRepository | None = None,
    links_enabled: bool = True,
) -> TraversalResult:
    """Traverse a graph and tail-transfer through enabled LINK nodes."""

    started_at = datetime.now(UTC)
    validate_tree_graph(graph)
    try:
        run_state = RunState.initialize(runtime_input)
    except TypeError as exc:
        # Non-finite floats (NaN/Infinity) and non-JSON value types survive the
        # API schema but are rejected when the input snapshot is frozen. Surface
        # them as a typed 422 instead of an untyped 500.
        raise InvalidRuntimeValueType(
            message="Runtime input is not a valid JSON object.",
            tree_key=graph.tree.tree_key,
            details={"reason": "invalid_runtime_input"},
        ) from exc
    session = _InternalTraversal(
        graph=graph,
        run_state=run_state,
        max_steps=max_steps,
        repository=repository,
        links_enabled=links_enabled,
    )
    session.run()
    return TraversalResult.from_run_state(
        run_state,
        tree_metadata=session.tree_metadata,
        started_at=started_at,
        completed_at=datetime.now(UTC),
    )


class _InternalTraversal:
    def __init__(
        self,
        *,
        graph: TreeGraph,
        run_state: RunState,
        max_steps: int,
        repository: TreeGraphRepository | None,
        links_enabled: bool,
    ) -> None:
        self.graph = graph
        self.run_state = run_state
        self.max_steps = max_steps
        self.repository = repository
        self.links_enabled = links_enabled
        # Monotonic trace sequence number (increments on every trace entry) is
        # kept separate from the traversal budget, which counts only actual node
        # entries across all linked trees. Candidate evaluations are traced but
        # do not consume the budget.
        self.trace_step = 0
        self.node_step_count = 0
        self.visited_node_ids: set[tuple[str, UUID]] = set()
        self.executed_reference_ids: set[tuple[str, UUID, UUID]] = set()
        self.recorded_tree_ids: set[tuple[str, UUID]] = set()
        self.validated_graph_ids: set[tuple[str, UUID]] = {(graph.tree.tree_key, graph.tree.id)}
        self.tree_metadata: list[TreeMetadata] = []
        self._record_tree_metadata(graph)

    def run(self) -> None:
        if self.max_steps <= 0:
            raise TraversalLimitExceeded(
                tree_key=self.graph.tree.tree_key,
                details={"max_steps": self.max_steps},
                partial_run_state=self.run_state,
            )

        current = self.graph.start_node
        while True:
            self._check_repeated_visit(current)
            self._enter_node_budget(current)
            self.visited_node_ids.add(self._node_identity(current))
            self._collect_references(current)

            changed_paths: list[str] = []
            if current.node_type is NodeType.INFERENCE:
                changed_paths = self._apply_patch(current)
            elif current.node_type is NodeType.ACTION:
                collect_action(current, self.run_state, tree_key=self.graph.tree.tree_key)
                changed_paths = self._apply_patch(current)
            elif current.node_type is NodeType.END:
                changed_paths = self._apply_patch(current)
                collect_action(current, self.run_state, tree_key=self.graph.tree.tree_key)
            elif current.node_type is NodeType.GLOBAL:
                raise InvalidTreeStructure(
                    tree_key=self.graph.tree.tree_key,
                    node_key=current.node_key,
                    details={"reason": "global_node_entered_during_traversal"},
                    partial_run_state=self.run_state,
                )

            self._append_trace(
                event=TraceEvent.NODE_ENTERED,
                node=current,
                changed_context_paths=changed_paths,
            )

            outgoing_edges = self.graph.outgoing_edges_by_node_id.get(current.id, ())
            if current.node_type is NodeType.END:
                return
            if current.node_type is NodeType.LINK:
                self.graph, current = self._follow_link(current)
                continue
            if current.node_type is NodeType.ACTION and not outgoing_edges:
                return

            current = self._select_next_node(current, outgoing_edges)

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
            condition_definition = _optional_json_object(candidate.condition_definition)
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

    def _apply_patch(self, node: NodeDefinition) -> list[str]:
        result = apply_context_patch(
            node.context_patch,
            self.run_state,
            tree_key=self.graph.tree.tree_key,
            node_key=node.node_key,
        )
        return result.changed_context_paths

    def _check_repeated_visit(self, node: NodeDefinition) -> None:
        if self._node_identity(node) in self.visited_node_ids:
            raise TraversalCycleDetected(
                tree_key=self.graph.tree.tree_key,
                node_key=node.node_key,
                details={"node_id": str(node.id)},
                partial_run_state=self.run_state,
            )

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
        validate_tree_graph(graph)
        self.validated_graph_ids.add(identity)

    def _attach_partial_state(self, error: DecisionTreeError) -> None:
        if error.partial_run_state is None:
            error.partial_run_state = self.run_state.snapshot()

    def _collect_references(self, node: NodeDefinition) -> None:
        references = self.graph.references_by_node_id.get(node.id, ())
        for reference in references:
            identity = (self.graph.tree.tree_key, node.id, reference.id)
            if identity in self.executed_reference_ids:
                continue
            self.executed_reference_ids.add(identity)
            self.run_state.references.append(
                _executed_reference(self.graph, node, reference, self.run_state)
            )

    def _record_tree_metadata(self, graph: TreeGraph) -> None:
        identity = (graph.tree.tree_key, graph.tree.id)
        if identity in self.recorded_tree_ids:
            return
        self.recorded_tree_ids.add(identity)
        self.tree_metadata.append(_tree_metadata(graph))

    def _node_identity(self, node: NodeDefinition) -> tuple[str, UUID]:
        return (self.graph.tree.tree_key, node.id)

    def _append_trace(
        self,
        *,
        event: TraceEvent,
        node: NodeDefinition,
        candidate_node_key: str | None = None,
        condition_definition: JsonObject | None = None,
        condition_result: bool | None = None,
        evaluation_details: JsonObject | None = None,
        changed_context_paths: list[str] | None = None,
    ) -> None:
        self.trace_step += 1
        self.run_state.trace.append(
            TraversalTraceEntry(
                step=self.trace_step,
                event=event,
                tree_key=self.graph.tree.tree_key,
                node_key=node.node_key,
                node_type=node.node_type,
                candidate_node_key=candidate_node_key,
                condition_definition=condition_definition,
                condition_result=condition_result,
                evaluation_details=evaluation_details,
                changed_context_paths=changed_context_paths or [],
            )
        )

    def _enter_node_budget(self, node: NodeDefinition) -> None:
        # The budget bounds actual node entries across all linked trees and is
        # never reset on transfer. Candidate evaluations do not consume it;
        # cycle detection guarantees termination regardless of the budget.
        if self.node_step_count >= self.max_steps:
            raise TraversalLimitExceeded(
                tree_key=self.graph.tree.tree_key,
                node_key=node.node_key,
                details={"max_steps": self.max_steps},
                partial_run_state=self.run_state,
            )
        self.node_step_count += 1


def _optional_json_object(value: Mapping[str, Any] | None) -> JsonObject | None:
    if value is None:
        return None
    copied = copy_json_value(value)
    return cast(JsonObject, copied)


def _tree_metadata(graph: TreeGraph) -> TreeMetadata:
    global_config: list[JsonObject] = []
    for node in graph.global_nodes:
        if node.global_config is None:
            continue
        copied = copy_json_value(node.global_config)
        if not isinstance(copied, dict):
            raise InvalidTreeStructure(
                tree_key=graph.tree.tree_key,
                node_key=node.node_key,
                details={"reason": "global_config_must_be_object"},
            )
        global_config.append(copied)
    return TreeMetadata(
        tree_id=graph.tree.id,
        tree_key=graph.tree.tree_key,
        name_en=graph.tree.name_en,
        name_vi=graph.tree.name_vi,
        global_config=global_config,
    )


def _executed_reference(
    graph: TreeGraph,
    node: NodeDefinition,
    reference: SourceReferenceDefinition,
    run_state: RunState,
) -> ExecutedReference:
    try:
        section_path = copy_json_value(reference.section_path)
    except TypeError as exc:
        raise InvalidTreeStructure(
            tree_key=graph.tree.tree_key,
            node_key=node.node_key,
            details={
                "reason": "reference_section_path_is_not_json",
                "reference_id": str(reference.id),
            },
            partial_run_state=run_state,
        ) from exc
    return ExecutedReference(
        tree_key=graph.tree.tree_key,
        node_key=node.node_key,
        reference_order=reference.reference_order,
        source_title=reference.source_title,
        section_path=section_path,
        locator=reference.locator,
        locator_detail=reference.locator_detail,
        printed_page_numbers=(
            list(reference.printed_page_numbers)
            if reference.printed_page_numbers is not None
            else None
        ),
        pdf_page_numbers=(
            list(reference.pdf_page_numbers) if reference.pdf_page_numbers is not None else None
        ),
        reference_note=reference.reference_note,
    )

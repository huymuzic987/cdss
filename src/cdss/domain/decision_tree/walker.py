"""Decision-tree traversal with cross-tree tail-link execution."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from cdss.domain.decision_tree.actions import collect_action
from cdss.domain.decision_tree.contracts import (
    NodeType,
    RunState,
    TraceEvent,
    TraversalResult,
    TreeMetadata,
)
from cdss.domain.decision_tree.errors import (
    InvalidRuntimeValueType,
    InvalidTreeStructure,
    TraversalCycleDetected,
    TraversalLimitExceeded,
)
from cdss.domain.decision_tree.graph import (
    NodeDefinition,
    TreeGraph,
    TreeGraphRepository,
)
from cdss.domain.decision_tree.medicine_catalog import MedicineRepository
from cdss.domain.decision_tree.patches import apply_context_patch
from cdss.domain.decision_tree.validator import validate_tree_graph
from cdss.domain.decision_tree.walker_links import LinkTraversalMixin
from cdss.domain.decision_tree.walker_start import resolve_start_node
from cdss.domain.decision_tree.walker_trace import TraceTraversalMixin
from cdss.domain.decision_tree.walker_transitions import TransitionTraversalMixin

DEFAULT_MAX_STEPS = 300

_ACTION_CONTINUATION_TREE_KEYS = frozenset(
    {"essential-treatment-strategy", "optimal-treatment-strategy"}
)
_ACTION_CONTINUATION_NODES = frozenset(
    {
        (
            "hypertension-in-pregnancy",
            "T12_ACTION_MONITOR_PREGNANCY_POSTPARTUM",
        ),
        (
            "hypertension-in-pregnancy",
            "T12_C_IMMEDIATE_TARGET",
        ),
        (
            "resistant-hypertension",
            "T13_A_CHECK_MRA",
        ),
        (
            "resistant-hypertension",
            "T13_A_CHECK_SPIRONOLACTONE",
        ),
        (
            "hypertensive-emergency",
            "T14_ACTION_ADMIT_AND_DETERMINE_TARGET_ORGAN",
        ),
    }
)


def walk_tree(
    graph: TreeGraph,
    runtime_input: Mapping[str, Any],
    *,
    start_node_key: str | None = None,
    max_steps: int = DEFAULT_MAX_STEPS,
    repository: TreeGraphRepository | None = None,
    medicine_repository: MedicineRepository | None = None,
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
    start_node = resolve_start_node(graph, start_node_key, run_state)
    session = _InternalTraversal(
        graph=graph,
        start_node=start_node,
        run_state=run_state,
        max_steps=max_steps,
        repository=repository,
        medicine_repository=medicine_repository,
        links_enabled=links_enabled,
    )
    session.run()
    return TraversalResult.from_run_state(
        run_state,
        tree_metadata=session.tree_metadata,
        started_at=started_at,
        completed_at=datetime.now(UTC),
    )


class _InternalTraversal(TransitionTraversalMixin, LinkTraversalMixin, TraceTraversalMixin):
    def __init__(
        self,
        *,
        graph: TreeGraph,
        start_node: NodeDefinition,
        run_state: RunState,
        max_steps: int,
        repository: TreeGraphRepository | None,
        medicine_repository: MedicineRepository | None,
        links_enabled: bool,
    ) -> None:
        self.graph = graph
        self.start_node = start_node
        self.run_state = run_state
        self.max_steps = max_steps
        self.repository = repository
        self.medicine_repository = medicine_repository
        self.links_enabled = links_enabled
        self.validate_graph = validate_tree_graph
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

        current = self.start_node
        while True:
            self._check_repeated_visit(current)
            self._enter_node_budget(current)
            self.visited_node_ids.add(self._node_identity(current))
            self._collect_references(current)

            changed_paths: list[str] = []
            if current.node_type is NodeType.INFERENCE:
                changed_paths = self._apply_patch(current)
            elif current.node_type is NodeType.ACTION:
                collect_action(
                    current,
                    self.run_state,
                    tree_key=self.graph.tree.tree_key,
                    medicine_repository=self.medicine_repository,
                )
                changed_paths = self._apply_patch(current)
            elif current.node_type is NodeType.END:
                changed_paths = self._apply_patch(current)
                collect_action(
                    current,
                    self.run_state,
                    tree_key=self.graph.tree.tree_key,
                    medicine_repository=self.medicine_repository,
                )
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
            if current.node_type is NodeType.ACTION:
                may_continue = bool(outgoing_edges) and (
                    (
                        self.graph.tree.tree_key in _ACTION_CONTINUATION_TREE_KEYS
                        and all(
                            self.graph.nodes_by_id[edge.to_node_id].node_type is NodeType.LINK
                            for edge in outgoing_edges
                        )
                    )
                    or (
                        self.graph.tree.tree_key,
                        current.node_key,
                    )
                    in _ACTION_CONTINUATION_NODES
                )
                if not may_continue:
                    return

            current = self._select_next_node(current, outgoing_edges)

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

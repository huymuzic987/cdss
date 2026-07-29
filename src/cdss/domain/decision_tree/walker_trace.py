"""Traversal trace, reference, metadata, and budget recording."""

from uuid import UUID

from cdss.domain.decision_tree.contracts import (
    ExecutedReference,
    JsonObject,
    RunState,
    TraceEvent,
    TraversalTraceEntry,
    TreeMetadata,
    copy_json_value,
)
from cdss.domain.decision_tree.errors import InvalidTreeStructure, TraversalLimitExceeded
from cdss.domain.decision_tree.graph import NodeDefinition, SourceReferenceDefinition, TreeGraph


class TraceTraversalMixin:
    graph: TreeGraph
    run_state: RunState
    max_steps: int
    trace_step: int
    node_step_count: int
    executed_reference_ids: set[tuple[str, UUID, UUID]]
    recorded_tree_ids: set[tuple[str, UUID]]
    tree_metadata: list[TreeMetadata]

    def _collect_references(self, node: NodeDefinition) -> None:
        references = self.graph.references_by_node_id.get(node.id, ())
        for reference in references:
            identity = (self.graph.tree.tree_key, node.id, reference.id)
            if identity in self.executed_reference_ids:
                continue
            self.executed_reference_ids.add(identity)
            self.run_state.references.append(
                executed_reference(self.graph, node, reference, self.run_state)
            )

    def _record_tree_metadata(self, graph: TreeGraph) -> None:
        identity = (graph.tree.tree_key, graph.tree.id)
        if identity in self.recorded_tree_ids:
            return
        self.recorded_tree_ids.add(identity)
        self.tree_metadata.append(tree_metadata_from_graph(graph))

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


def tree_metadata_from_graph(graph: TreeGraph) -> TreeMetadata:
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


def executed_reference(
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

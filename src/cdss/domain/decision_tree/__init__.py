"""Decision tree execution engine, node types, conditions, actions, and graph validation."""

from typing import Any

from cdss.domain.decision_tree.actions import (
    collect_action,
    select_output_actions,
)
from cdss.domain.decision_tree.conditions import (
    ConditionEvaluation,
    evaluate_candidate_condition,
    evaluate_condition,
    validate_condition_definition,
)
from cdss.domain.decision_tree.contracts import (
    ExecutedAction,
    ExecutedReference,
    FrozenJsonObject,
    JsonObject,
    JsonValue,
    NodeType,
    TraceEvent,
    TraversalResult,
    TraversalTraceEntry,
    TreeMetadata,
)
from cdss.domain.decision_tree.errors import (
    ContextPatchError,
    DecisionTreeError,
    InvalidConditionDefinition,
    InvalidFhirInput,
    InvalidRuntimeValueType,
    InvalidStartNode,
    InvalidTreeStructure,
    LinkNotEnabled,
    LinkTargetNodeNotFound,
    LinkTargetNotFound,
    MissingRuntimePath,
    NoMatchingTransition,
    RunState,
    TraversalCycleDetected,
    TraversalLimitExceeded,
    TreeNotFound,
    UnsupportedOperator,
)
from cdss.domain.decision_tree.graph import (
    EdgeDefinition,
    NodeDefinition,
    SourceReferenceDefinition,
    TreeDefinition,
    TreeGraph,
    TreeGraphRepository,
)
from cdss.domain.decision_tree.medication_regimen import (
    DEFAULT_REGIMEN_DOSE_STRATEGY,
    EffectiveMedicationRegimen,
    MedicationRegimenPlan,
    RegimenAlternative,
    RegimenComponent,
    RegimenKeyword,
    RegimenUpdateStep,
    build_traversed_medication_regimen,
)
from cdss.domain.decision_tree.medicine_catalog import Medicine, MedicineRepository
from cdss.domain.decision_tree.patches import ContextPatchResult, apply_context_patch
from cdss.domain.decision_tree.paths import resolve_runtime_path
from cdss.domain.decision_tree.validator import (
    TreeValidationResult,
    TreeValidationWarning,
    validate_tree_graph,
)
from cdss.domain.decision_tree.walker import DEFAULT_MAX_STEPS, walk_tree


def __getattr__(name: str) -> Any:
    if name == "filter_medication_regimen_plan":
        from cdss.domain.medication_safety.medication_safety_regimen import (
            filter_medication_regimen_plan,
        )

        return filter_medication_regimen_plan
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "ContextPatchError",
    "ContextPatchResult",
    "ConditionEvaluation",
    "collect_action",
    "DecisionTreeError",
    "DEFAULT_MAX_STEPS",
    "EdgeDefinition",
    "ExecutedAction",
    "ExecutedReference",
    "evaluate_candidate_condition",
    "evaluate_condition",
    "FrozenJsonObject",
    "InvalidConditionDefinition",
    "InvalidFhirInput",
    "InvalidRuntimeValueType",
    "InvalidStartNode",
    "InvalidTreeStructure",
    "JsonObject",
    "JsonValue",
    "LinkNotEnabled",
    "LinkTargetNodeNotFound",
    "LinkTargetNotFound",
    "Medicine",
    "MedicineRepository",
    "MedicationRegimenPlan",
    "MissingRuntimePath",
    "NoMatchingTransition",
    "NodeDefinition",
    "NodeType",
    "RegimenAlternative",
    "RegimenComponent",
    "RegimenKeyword",
    "RegimenUpdateStep",
    "RunState",
    "resolve_runtime_path",
    "select_output_actions",
    "SourceReferenceDefinition",
    "TraceEvent",
    "TraversalCycleDetected",
    "TraversalLimitExceeded",
    "TraversalResult",
    "TraversalTraceEntry",
    "TreeDefinition",
    "TreeGraph",
    "TreeGraphRepository",
    "TreeMetadata",
    "TreeNotFound",
    "TreeValidationResult",
    "TreeValidationWarning",
    "UnsupportedOperator",
    "DEFAULT_REGIMEN_DOSE_STRATEGY",
    "EffectiveMedicationRegimen",
    "apply_context_patch",
    "build_traversed_medication_regimen",
    "validate_condition_definition",
    "validate_tree_graph",
    "walk_tree",
]

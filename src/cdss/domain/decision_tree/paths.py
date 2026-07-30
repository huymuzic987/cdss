"""Strict runtime path resolution for decision-tree evaluation."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from cdss.domain.decision_tree.contracts import RunState
from cdss.domain.decision_tree.errors import MissingRuntimePath


def resolve_runtime_path(
    run_state: RunState,
    path: str,
    *,
    tree_key: str | None = None,
    node_key: str | None = None,
) -> Any:
    """Resolve an exact object path rooted at input or context."""

    if not isinstance(path, str) or not path:
        raise _path_error(
            run_state,
            path,
            tree_key=tree_key,
            node_key=node_key,
            reason="path_must_be_non_empty_string",
        )

    parts = path.split(".")
    if len(parts) < 2 or any(not part for part in parts):
        raise _path_error(
            run_state,
            path,
            tree_key=tree_key,
            node_key=node_key,
            reason="invalid_path_syntax",
        )

    root, *segments = parts
    if root == "input":
        current: Any = run_state.input_snapshot
        # Fallback to context.diagnosis for current_clinic_sbp and current_clinic_dbp if missing from input
        if len(segments) == 1 and segments[0] in ("current_clinic_sbp", "current_clinic_dbp"):
            if segments[0] not in current:
                diagnosis = run_state.context.get("diagnosis")
                if isinstance(diagnosis, dict) and segments[0] in diagnosis:
                    return diagnosis[segments[0]]
    elif root == "context":
        current = run_state.context
    else:
        raise _path_error(
            run_state,
            path,
            tree_key=tree_key,
            node_key=node_key,
            reason="invalid_path_root",
        )

    traversed = root
    for segment in segments:
        if not isinstance(current, Mapping):
            raise _path_error(
                run_state,
                path,
                tree_key=tree_key,
                node_key=node_key,
                reason="non_object_path_segment",
                resolved_prefix=traversed,
            )
        if segment not in current:
            raise _path_error(
                run_state,
                path,
                tree_key=tree_key,
                node_key=node_key,
                reason="missing_path_segment",
                resolved_prefix=traversed,
                missing_segment=segment,
            )
        current = current[segment]
        traversed = f"{traversed}.{segment}"

    return current


def _path_error(
    run_state: RunState,
    path: Any,
    *,
    tree_key: str | None,
    node_key: str | None,
    reason: str,
    **details: Any,
) -> MissingRuntimePath:
    return MissingRuntimePath(
        tree_key=tree_key,
        node_key=node_key,
        details={"path": path, "reason": reason, **details},
        partial_run_state=run_state,
    )

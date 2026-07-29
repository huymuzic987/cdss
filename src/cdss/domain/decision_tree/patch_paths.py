"""Validation and assignment of context-patch paths."""

from typing import Any

from cdss.domain.decision_tree.contracts import JsonObject, JsonValue, RunState
from cdss.domain.decision_tree.patch_errors import patch_error


def validate_patch_path(
    path: Any,
    *,
    roots: set[str],
    path_role: str,
    operation_index: int,
    run_state: RunState,
    tree_key: str | None,
    node_key: str | None,
) -> list[str]:
    if not isinstance(path, str):
        raise patch_error(
            run_state,
            tree_key=tree_key,
            node_key=node_key,
            reason=f"copy_{path_role}_path_must_be_string",
            operation_index=operation_index,
        )
    parts = path.split(".")
    if len(parts) < 2 or parts[0] not in roots or any(not part for part in parts):
        raise patch_error(
            run_state,
            tree_key=tree_key,
            node_key=node_key,
            reason=f"invalid_copy_{path_role}_path",
            operation_index=operation_index,
            path=path,
        )
    return parts[1:]


def assign_context_path(
    context: JsonObject,
    segments: list[str],
    value: JsonValue,
    *,
    full_path: str,
    changed_paths: list[str],
) -> None:
    target = context
    traversed = "context"
    for segment in segments[:-1]:
        traversed = f"{traversed}.{segment}"
        existing = target.get(segment)
        if isinstance(existing, dict):
            target = existing
        else:
            if segment in target:
                changed_paths.append(traversed)
            child: JsonObject = {}
            target[segment] = child
            target = child
    target[segments[-1]] = value
    changed_paths.append(full_path)

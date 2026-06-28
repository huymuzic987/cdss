"""Pure context-patch execution for decision-tree runtime state."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import Field

from cdss.domain.decision_tree.contracts import (
    JsonObject,
    JsonValue,
    RunState,
    RuntimeModel,
    copy_json_value,
)
from cdss.domain.decision_tree.errors import ContextPatchError, MissingRuntimePath
from cdss.domain.decision_tree.paths import resolve_runtime_path


class ContextPatchResult(RuntimeModel):
    changed_context_paths: list[str] = Field(default_factory=list)


def apply_context_patch(
    context_patch: Mapping[str, Any] | None,
    run_state: RunState,
    *,
    tree_key: str | None = None,
    node_key: str | None = None,
) -> ContextPatchResult:
    """Apply static values, then ordered operations, to runtime context."""

    if context_patch is None:
        return ContextPatchResult()
    if not isinstance(context_patch, Mapping):
        raise _patch_error(
            run_state,
            tree_key=tree_key,
            node_key=node_key,
            reason="context_patch_must_be_object",
        )

    changed_paths: list[str] = []
    for key, value in context_patch.items():
        if not isinstance(key, str):
            raise _patch_error(
                run_state,
                tree_key=tree_key,
                node_key=node_key,
                reason="context_patch_keys_must_be_strings",
            )
        if key != "operations":
            _merge_context_value(
                run_state.context,
                key,
                value,
                parent_path="context",
                changed_paths=changed_paths,
                run_state=run_state,
                tree_key=tree_key,
                node_key=node_key,
            )

    if "operations" in context_patch:
        operations = context_patch["operations"]
        if not isinstance(operations, (list, tuple)):
            raise _patch_error(
                run_state,
                tree_key=tree_key,
                node_key=node_key,
                reason="operations_must_be_array",
            )
        for operation_index, operation in enumerate(operations):
            _execute_operation(
                operation,
                operation_index=operation_index,
                run_state=run_state,
                changed_paths=changed_paths,
                tree_key=tree_key,
                node_key=node_key,
            )

    return ContextPatchResult(changed_context_paths=changed_paths)


def _merge_context_value(
    target: dict[str, JsonValue],
    key: str,
    patch_value: Any,
    *,
    parent_path: str,
    changed_paths: list[str],
    run_state: RunState,
    tree_key: str | None,
    node_key: str | None,
) -> None:
    path = f"{parent_path}.{key}"
    if isinstance(patch_value, Mapping):
        existing = target.get(key)
        if isinstance(existing, dict):
            child_target = existing
        else:
            existed = key in target
            child_target = {}
            target[key] = child_target
            if existed or not patch_value:
                changed_paths.append(path)

        for child_key, child_value in patch_value.items():
            if not isinstance(child_key, str):
                raise _patch_error(
                    run_state,
                    tree_key=tree_key,
                    node_key=node_key,
                    reason="context_patch_keys_must_be_strings",
                    path=path,
                )
            _merge_context_value(
                child_target,
                child_key,
                child_value,
                parent_path=path,
                changed_paths=changed_paths,
                run_state=run_state,
                tree_key=tree_key,
                node_key=node_key,
            )
        return

    try:
        target[key] = copy_json_value(patch_value)
    except TypeError as exc:
        raise _patch_error(
            run_state,
            tree_key=tree_key,
            node_key=node_key,
            reason="context_patch_value_is_not_json",
            path=path,
        ) from exc
    changed_paths.append(path)


def _execute_operation(
    operation: Any,
    *,
    operation_index: int,
    run_state: RunState,
    changed_paths: list[str],
    tree_key: str | None,
    node_key: str | None,
) -> None:
    if not isinstance(operation, Mapping):
        raise _patch_error(
            run_state,
            tree_key=tree_key,
            node_key=node_key,
            reason="operation_must_be_object",
            operation_index=operation_index,
        )

    allowed_keys = {"op", "from_path", "to_path", "required"}
    if not set(operation).issubset(allowed_keys):
        raise _patch_error(
            run_state,
            tree_key=tree_key,
            node_key=node_key,
            reason="operation_contains_unknown_keys",
            operation_index=operation_index,
        )

    operation_name = operation.get("op")
    if not isinstance(operation_name, str):
        raise _patch_error(
            run_state,
            tree_key=tree_key,
            node_key=node_key,
            reason="operation_name_must_be_string",
            operation_index=operation_index,
        )
    if operation_name != "COPY_PATH":
        raise _patch_error(
            run_state,
            tree_key=tree_key,
            node_key=node_key,
            reason="unsupported_context_operation",
            operation_index=operation_index,
            operation=operation_name,
        )
    if "from_path" not in operation or "to_path" not in operation:
        raise _patch_error(
            run_state,
            tree_key=tree_key,
            node_key=node_key,
            reason="copy_path_requires_source_and_target",
            operation_index=operation_index,
        )

    required = operation.get("required", False)
    if not isinstance(required, bool):
        raise _patch_error(
            run_state,
            tree_key=tree_key,
            node_key=node_key,
            reason="copy_path_required_must_be_boolean",
            operation_index=operation_index,
        )

    from_path = operation["from_path"]
    to_path = operation["to_path"]
    _validate_patch_path(
        from_path,
        roots={"input", "context"},
        path_role="source",
        operation_index=operation_index,
        run_state=run_state,
        tree_key=tree_key,
        node_key=node_key,
    )
    target_segments = _validate_patch_path(
        to_path,
        roots={"context"},
        path_role="target",
        operation_index=operation_index,
        run_state=run_state,
        tree_key=tree_key,
        node_key=node_key,
    )

    try:
        source_value = resolve_runtime_path(
            run_state,
            from_path,
            tree_key=tree_key,
            node_key=node_key,
        )
    except MissingRuntimePath as exc:
        if not required:
            return
        raise _patch_error(
            run_state,
            tree_key=tree_key,
            node_key=node_key,
            reason="required_copy_source_missing",
            operation_index=operation_index,
            from_path=from_path,
            source_error=exc.details,
        ) from exc

    try:
        copied_value = copy_json_value(source_value)
    except TypeError as exc:
        raise _patch_error(
            run_state,
            tree_key=tree_key,
            node_key=node_key,
            reason="copy_source_is_not_json",
            operation_index=operation_index,
            from_path=from_path,
        ) from exc

    _assign_context_path(
        run_state.context,
        target_segments,
        copied_value,
        full_path=to_path,
        changed_paths=changed_paths,
    )


def _validate_patch_path(
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
        raise _patch_error(
            run_state,
            tree_key=tree_key,
            node_key=node_key,
            reason=f"copy_{path_role}_path_must_be_string",
            operation_index=operation_index,
        )
    parts = path.split(".")
    if len(parts) < 2 or parts[0] not in roots or any(not part for part in parts):
        raise _patch_error(
            run_state,
            tree_key=tree_key,
            node_key=node_key,
            reason=f"invalid_copy_{path_role}_path",
            operation_index=operation_index,
            path=path,
        )
    return parts[1:]


def _assign_context_path(
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


def _patch_error(
    run_state: RunState,
    *,
    tree_key: str | None,
    node_key: str | None,
    reason: str,
    **details: Any,
) -> ContextPatchError:
    return ContextPatchError(
        tree_key=tree_key,
        node_key=node_key,
        details={"reason": reason, **details},
        partial_run_state=run_state,
    )

"""Execution of ordered context-patch operations."""

from collections.abc import Mapping
from typing import Any

from cdss.domain.decision_tree.contracts import RunState, copy_json_value
from cdss.domain.decision_tree.errors import MissingRuntimePath
from cdss.domain.decision_tree.patch_errors import patch_error
from cdss.domain.decision_tree.patch_paths import assign_context_path, validate_patch_path
from cdss.domain.decision_tree.paths import resolve_runtime_path


def execute_operation(
    operation: Any,
    *,
    operation_index: int,
    run_state: RunState,
    changed_paths: list[str],
    tree_key: str | None,
    node_key: str | None,
) -> None:
    if not isinstance(operation, Mapping):
        raise patch_error(
            run_state,
            tree_key=tree_key,
            node_key=node_key,
            reason="operation_must_be_object",
            operation_index=operation_index,
        )

    allowed_keys = {"op", "from_path", "to_path", "required"}
    if not set(operation).issubset(allowed_keys):
        raise patch_error(
            run_state,
            tree_key=tree_key,
            node_key=node_key,
            reason="operation_contains_unknown_keys",
            operation_index=operation_index,
        )

    operation_name = operation.get("op")
    if not isinstance(operation_name, str):
        raise patch_error(
            run_state,
            tree_key=tree_key,
            node_key=node_key,
            reason="operation_name_must_be_string",
            operation_index=operation_index,
        )
    if operation_name != "COPY_PATH":
        raise patch_error(
            run_state,
            tree_key=tree_key,
            node_key=node_key,
            reason="unsupported_context_operation",
            operation_index=operation_index,
            operation=operation_name,
        )
    if "from_path" not in operation or "to_path" not in operation:
        raise patch_error(
            run_state,
            tree_key=tree_key,
            node_key=node_key,
            reason="copy_path_requires_source_and_target",
            operation_index=operation_index,
        )

    required = operation.get("required", False)
    if not isinstance(required, bool):
        raise patch_error(
            run_state,
            tree_key=tree_key,
            node_key=node_key,
            reason="copy_path_required_must_be_boolean",
            operation_index=operation_index,
        )

    from_path = operation["from_path"]
    to_path = operation["to_path"]
    validate_patch_path(
        from_path,
        roots={"input", "context"},
        path_role="source",
        operation_index=operation_index,
        run_state=run_state,
        tree_key=tree_key,
        node_key=node_key,
    )
    target_segments = validate_patch_path(
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
        raise patch_error(
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
        raise patch_error(
            run_state,
            tree_key=tree_key,
            node_key=node_key,
            reason="copy_source_is_not_json",
            operation_index=operation_index,
            from_path=from_path,
        ) from exc

    assign_context_path(
        run_state.context,
        target_segments,
        copied_value,
        full_path=to_path,
        changed_paths=changed_paths,
    )

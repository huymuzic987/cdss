"""Public context-patch orchestration for decision-tree runtime state."""

from collections.abc import Mapping
from typing import Any

from pydantic import Field

from cdss.domain.decision_tree.contracts import (
    JsonValue,
    RunState,
    RuntimeModel,
    copy_json_value,
)
from cdss.domain.decision_tree.patch_errors import patch_error
from cdss.domain.decision_tree.patch_operations import execute_operation


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
        raise patch_error(
            run_state,
            tree_key=tree_key,
            node_key=node_key,
            reason="context_patch_must_be_object",
        )

    changed_paths: list[str] = []
    for key, value in context_patch.items():
        if not isinstance(key, str):
            raise patch_error(
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
            raise patch_error(
                run_state,
                tree_key=tree_key,
                node_key=node_key,
                reason="operations_must_be_array",
            )
        for operation_index, operation in enumerate(operations):
            execute_operation(
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
                raise patch_error(
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
        raise patch_error(
            run_state,
            tree_key=tree_key,
            node_key=node_key,
            reason="context_patch_value_is_not_json",
            path=path,
        ) from exc
    changed_paths.append(path)

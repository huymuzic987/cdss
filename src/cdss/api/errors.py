"""Safe HTTP serialization for API and decision-tree errors."""

from __future__ import annotations

import logging
from typing import cast

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.types import ExceptionHandler

from cdss.api.schemas import EvaluationErrorResponse, PartialRunStateResponse
from cdss.domain.decision_tree import (
    ContextPatchError,
    DecisionTreeError,
    InvalidFhirInput,
    InvalidRuntimeValueType,
    LinkNotEnabled,
    LinkTargetNodeNotFound,
    LinkTargetNotFound,
    MissingRuntimePath,
    NoMatchingTransition,
    TraversalLimitExceeded,
    TreeNotFound,
)
from cdss.domain.decision_tree.contracts import JsonValue

logger = logging.getLogger("cdss.api")


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(
        DecisionTreeError,
        cast(ExceptionHandler, decision_tree_error_handler),
    )
    app.add_exception_handler(
        RequestValidationError,
        cast(ExceptionHandler, request_validation_error_handler),
    )


def _verbose_error_message(error: DecisionTreeError) -> str:
    message = error.message
    if isinstance(error, MissingRuntimePath):
        path = error.details.get("path")
        reason = error.details.get("reason")
        if reason == "missing_path_segment":
            resolved_prefix = error.details.get("resolved_prefix")
            missing_segment = error.details.get("missing_segment")
            message = (
                f"A required runtime path is missing: '{path}'. "
                f"Specifically, the segment '{missing_segment}' was not found "
                f"under '{resolved_prefix}'."
            )
        elif reason == "non_object_path_segment":
            resolved_prefix = error.details.get("resolved_prefix")
            message = (
                f"A required runtime path is missing: '{path}'. "
                f"Specifically, '{resolved_prefix}' is not an object/mapping, "
                "so it cannot be traversed further."
            )
        elif reason == "invalid_path_root":
            message = (
                f"A required runtime path is missing: '{path}'. "
                f"The path root is invalid. Paths must start with 'input' or 'context'."
            )
        elif path:
            message = f"A required runtime path is missing: '{path}'. Reason: {reason}."
    elif isinstance(error, InvalidRuntimeValueType):
        operator = error.details.get("operator")
        operand = error.details.get("operand")
        actual_type = error.details.get("actual_type")
        reason = error.details.get("reason")
        if reason == "invalid_runtime_input":
            message = "Runtime input is not a valid JSON object."
        elif operator == "in":
            message = (
                "A runtime value has an invalid type. Operator 'in' requires "
                f"the right operand to be a list, but got '{actual_type}'."
            )
        elif operator and operand:
            message = (
                f"A runtime value has an invalid type. Operator '{operator}' "
                f"requires numeric operands, but the {operand} operand was "
                f"of type '{actual_type}'."
            )
    elif isinstance(error, NoMatchingTransition):
        candidate_count = error.details.get("outgoing_candidate_count")
        message = (
            f"No outgoing transition matched from node '{error.node_key}' "
            f"in tree '{error.tree_key}'. "
            f"Tested {candidate_count} candidate transitions, but none evaluated to true."
        )
    elif isinstance(error, LinkTargetNotFound):
        target_tree_key = error.details.get("link_target_tree_key")
        message = f"Linked decision tree '{target_tree_key}' was not found in the repository."
    elif isinstance(error, LinkTargetNodeNotFound):
        source_tree = error.details.get("source_tree_key")
        source_node = error.details.get("source_node_key")
        message = (
            f"Linked target node '{error.node_key}' was not found in tree '{error.tree_key}'. "
            f"Linked from tree '{source_tree}' node '{source_node}'."
        )
    elif isinstance(error, TreeNotFound):
        message = f"Decision tree '{error.tree_key}' was not found."
    elif isinstance(error, LinkNotEnabled):
        target_tree = error.details.get("link_target_tree_key")
        target_node = error.details.get("link_target_node_key")
        message = f"Cross-tree link to tree '{target_tree}' node '{target_node}' is not enabled."
    elif isinstance(error, TraversalLimitExceeded):
        max_steps = error.details.get("max_steps", 0)
        message = f"Decision-tree traversal exceeded its safety limit of {max_steps} steps."
    elif isinstance(error, InvalidFhirInput):
        reason = error.details.get("reason")
        message = f"{error.message} Reason: {reason}." if reason else error.message
    return message


async def decision_tree_error_handler(
    _request: Request,
    error: DecisionTreeError,
) -> JSONResponse:
    message = _verbose_error_message(error)
    logger.error(
        "DecisionTreeError [%s]: %s (tree: %s, node: %s) - Details: %s",
        error.code,
        message,
        error.tree_key,
        error.node_key,
        error.details,
        exc_info=True,
    )
    response = EvaluationErrorResponse(
        code=error.code,
        message=message,
        tree_key=error.tree_key,
        node_key=error.node_key,
        details=error.details,
        partial_run_state=(
            PartialRunStateResponse.from_run_state(error.partial_run_state)
            if error.partial_run_state is not None
            else None
        ),
    )
    return JSONResponse(
        status_code=_status_for_domain_error(error),
        content=response.model_dump(mode="json"),
    )


async def request_validation_error_handler(
    _request: Request,
    error: RequestValidationError,
) -> JSONResponse:
    errors = error.errors()
    safe_errors: list[JsonValue] = [
        {
            "type": item["type"],
            "location": list(item["loc"]),
            "message": item["msg"],
        }
        for item in errors
    ]
    errors_summary = []
    for item in errors:
        loc_str = " -> ".join(str(loc) for loc in item["loc"])
        errors_summary.append(f"{loc_str}: {item['msg']}")

    message = "Request validation failed."
    if errors_summary:
        message = f"Request validation failed. Errors: {', '.join(errors_summary)}"

    logger.warning(
        "RequestValidationError: %s (Errors: %s)",
        message,
        safe_errors,
    )
    response = EvaluationErrorResponse(
        code="invalid_request",
        message=message,
        details={"errors": safe_errors},
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=response.model_dump(mode="json"),
    )


def _status_for_domain_error(error: DecisionTreeError) -> int:
    if isinstance(error, TreeNotFound):
        return status.HTTP_404_NOT_FOUND
    if isinstance(error, (LinkTargetNotFound, LinkTargetNodeNotFound)):
        return status.HTTP_424_FAILED_DEPENDENCY
    if isinstance(
        error,
        (MissingRuntimePath, InvalidRuntimeValueType, NoMatchingTransition, InvalidFhirInput),
    ):
        return status.HTTP_422_UNPROCESSABLE_CONTENT
    if isinstance(error, ContextPatchError) and error.details.get("reason") == (
        "required_copy_source_missing"
    ):
        return status.HTTP_422_UNPROCESSABLE_CONTENT
    return status.HTTP_500_INTERNAL_SERVER_ERROR

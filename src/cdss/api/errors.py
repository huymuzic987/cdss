"""Safe HTTP serialization for API and decision-tree errors."""

from __future__ import annotations

from typing import cast

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.types import ExceptionHandler

from cdss.api.schemas import EvaluationErrorResponse, PartialRunStateResponse
from cdss.domain.decision_tree import (
    ContextPatchError,
    DecisionTreeError,
    InvalidRuntimeValueType,
    LinkTargetNodeNotFound,
    LinkTargetNotFound,
    MissingRuntimePath,
    NoMatchingTransition,
    TreeNotFound,
)
from cdss.domain.decision_tree.contracts import JsonValue


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(
        DecisionTreeError,
        cast(ExceptionHandler, decision_tree_error_handler),
    )
    app.add_exception_handler(
        RequestValidationError,
        cast(ExceptionHandler, request_validation_error_handler),
    )


async def decision_tree_error_handler(
    _request: Request,
    error: DecisionTreeError,
) -> JSONResponse:
    response = EvaluationErrorResponse(
        code=error.code,
        message=error.message,
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
    safe_errors: list[JsonValue] = [
        {
            "type": item["type"],
            "location": list(item["loc"]),
            "message": item["msg"],
        }
        for item in error.errors()
    ]
    response = EvaluationErrorResponse(
        code="invalid_request",
        message="Request validation failed.",
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
    if isinstance(error, (MissingRuntimePath, InvalidRuntimeValueType, NoMatchingTransition)):
        return status.HTTP_422_UNPROCESSABLE_CONTENT
    if isinstance(error, ContextPatchError) and error.details.get("reason") == (
        "required_copy_source_missing"
    ):
        return status.HTTP_422_UNPROCESSABLE_CONTENT
    return status.HTTP_500_INTERNAL_SERVER_ERROR

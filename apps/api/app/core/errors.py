"""Domain-specific error types and FastAPI exception handlers."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.core.logging import get_logger

log = get_logger(__name__)


class OpenDispatchError(Exception):
    """Base class for all OpenDispatch domain errors."""

    code: str = "INTERNAL_ERROR"
    http_status: int = 500
    message: str = "An internal error occurred."

    def __init__(self, message: str | None = None, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message or self.message)
        self.message = message or self.message
        self.details = details or {}

    def to_payload(self) -> dict[str, Any]:
        return {"error": {"code": self.code, "message": self.message, "details": self.details}}


class NotFoundError(OpenDispatchError):
    code = "NOT_FOUND"
    http_status = 404
    message = "Resource not found."


class ValidationFailed(OpenDispatchError):
    code = "VALIDATION_FAILED"
    http_status = 422
    message = "Validation failed."


class ConflictError(OpenDispatchError):
    code = "CONFLICT"
    http_status = 409
    message = "Resource conflict."


class UnauthorizedError(OpenDispatchError):
    code = "UNAUTHORIZED"
    http_status = 401
    message = "Authentication required."


class ForbiddenError(OpenDispatchError):
    code = "FORBIDDEN"
    http_status = 403
    message = "Permission denied."


class BusinessRuleViolation(OpenDispatchError):
    code = "BUSINESS_RULE_VIOLATION"
    http_status = 422
    message = "Business rule violated."


class PlanningError(OpenDispatchError):
    code = "PLANNING_ERROR"
    http_status = 422

    def __init__(
        self,
        code: str,
        message: str,
        *,
        details: dict[str, Any] | None = None,
        http_status: int = 422,
    ) -> None:
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(message, details=details)


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(OpenDispatchError)
    async def _domain(_request: Request, exc: OpenDispatchError) -> JSONResponse:
        return JSONResponse(status_code=exc.http_status, content=exc.to_payload())

    @app.exception_handler(ValidationError)
    async def _pydantic(_request: Request, exc: ValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "VALIDATION_FAILED",
                    "message": "Request validation failed.",
                    "details": {"errors": exc.errors()},
                }
            },
        )

    @app.exception_handler(SQLAlchemyError)
    async def _sqla(_request: Request, exc: SQLAlchemyError) -> JSONResponse:
        log.error("sqlalchemy_error", error=str(exc))
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "DATABASE_ERROR",
                    "message": "A database error occurred.",
                    "details": {},
                }
            },
        )

    @app.exception_handler(Exception)
    async def _unhandled(_request: Request, exc: Exception) -> JSONResponse:
        log.error("unhandled_exception", error=str(exc), type=type(exc).__name__)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An internal error occurred.",
                    "details": {},
                }
            },
        )

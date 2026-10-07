"""Every error leaves the API as {"error": {"code": "...", "message": "..."}}."""

from http import HTTPStatus

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from redis.exceptions import RedisError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = structlog.get_logger(__name__)


class AppError(Exception):
    """Raised by services for expected failures; carries the HTTP status and a stable code."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.headers = headers


def error_response(
    status_code: int, code: str, message: str, headers: dict[str, str] | None = None
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
        headers=headers,
    )


def _status_to_code(status_code: int) -> str:
    try:
        return HTTPStatus(status_code).phrase.lower().replace(" ", "_")
    except ValueError:
        return "error"


async def _app_error_handler(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppError)  # noqa: S101
    return error_response(exc.status_code, exc.code, exc.message, exc.headers)


async def _http_error_handler(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)  # noqa: S101
    message = exc.detail if isinstance(exc.detail, str) else HTTPStatus(exc.status_code).phrase
    return error_response(exc.status_code, _status_to_code(exc.status_code), message, exc.headers)


async def _validation_error_handler(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)  # noqa: S101
    parts = []
    for err in exc.errors():
        location = ".".join(str(p) for p in err["loc"] if p != "body")
        parts.append(f"{location}: {err['msg']}" if location else err["msg"])
    return error_response(422, "validation_error", "; ".join(parts))


async def _redis_error_handler(request: Request, exc: Exception) -> JSONResponse:
    # Features that need Redis to be correct (holds, login limits) fail closed with a 503, which
    # tells clients the problem is temporary, rather than a generic 500.
    logger.error("redis_unavailable", path=request.url.path, error=str(exc))
    return error_response(
        503, "service_unavailable", "A required service is temporarily unavailable"
    )


async def _unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled_error", path=request.url.path)
    return error_response(500, "internal_error", "An unexpected error occurred")


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _app_error_handler)
    app.add_exception_handler(StarletteHTTPException, _http_error_handler)
    app.add_exception_handler(RequestValidationError, _validation_error_handler)
    app.add_exception_handler(RedisError, _redis_error_handler)
    app.add_exception_handler(Exception, _unhandled_error_handler)

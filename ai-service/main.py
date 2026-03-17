"""Production-ready FastAPI entry point for the AI service.

Features
--------
* POST /ai/reply-suggestion  – main AI endpoint
* Pydantic request/response models with field validation
* Per-IP rate limiting: 10 requests / minute (slowapi)
* Structured logging with unique request IDs
* Global exception handlers (validation, rate-limit, generic)
* Async endpoint with non-blocking generate_reply call
* Input sanitization and payload size limit (32 KB)
"""

import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware

from ai_service import generate_reply
from utils import sanitize_input

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s %(message)s",
)
logger = logging.getLogger(__name__)

# ── Rate limiter ──────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=["10/minute"])

# ── App lifecycle ─────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    logger.info("event=startup service=ai-service")
    yield
    logger.info("event=shutdown service=ai-service")


# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="AI Service",
    version="2.0.0",
    lifespan=lifespan,
)
app.state.limiter = limiter


# ── Request ID + timing middleware ────────────────────────────────────────────
class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        start = time.perf_counter()

        logger.info(
            "request_received request_id=%s method=%s path=%s",
            request_id,
            request.method,
            request.url.path,
        )

        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000

        logger.info(
            "request_completed request_id=%s status=%d duration_ms=%.2f",
            request_id,
            response.status_code,
            elapsed_ms,
        )
        response.headers["X-Request-ID"] = request_id
        return response


app.add_middleware(RequestLoggingMiddleware)

# ── Payload size limit (32 KB) ────────────────────────────────────────────────
MAX_BODY_SIZE = 32_768  # bytes


@app.middleware("http")
async def limit_body_size(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_BODY_SIZE:
        request_id = getattr(request.state, "request_id", "unknown")
        logger.warning("payload_too_large request_id=%s", request_id)
        return JSONResponse(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            content={
                "success": False,
                "data": None,
                "error": {
                    "code": "PAYLOAD_TOO_LARGE",
                    "message": "Request body exceeds the 32 KB limit.",
                },
            },
        )
    return await call_next(request)


# ── Pydantic models ───────────────────────────────────────────────────────────
class ReplySuggestionRequest(BaseModel):
    message: str
    context: Optional[str] = None

    @field_validator("message")
    @classmethod
    def message_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("message must not be empty")
        if len(v) > 2_000:
            raise ValueError("message must not exceed 2000 characters")
        return v

    @field_validator("context")
    @classmethod
    def context_max_length(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v) > 5_000:
            raise ValueError("context must not exceed 5000 characters")
        return v


class ErrorDetail(BaseModel):
    code: str
    message: str


class ReplySuggestionData(BaseModel):
    suggestions: list[str]


class ReplySuggestionResponse(BaseModel):
    success: bool
    data: Optional[ReplySuggestionData] = None
    error: Optional[ErrorDetail] = None


# ── Exception handlers ────────────────────────────────────────────────────────
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):  # noqa: ARG001
    request_id = getattr(request.state, "request_id", "unknown")
    logger.warning(
        "rate_limit_exceeded request_id=%s ip=%s",
        request_id,
        get_remote_address(request),
    )
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "success": False,
            "data": None,
            "error": {
                "code": "RATE_LIMIT_EXCEEDED",
                "message": "Too many requests. Limit is 10 per minute.",
            },
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    request_id = getattr(request.state, "request_id", "unknown")
    messages = "; ".join(
        f"{'.'.join(str(loc) for loc in err['loc'])}: {err['msg']}"
        for err in exc.errors()
    )
    logger.warning("validation_error request_id=%s errors=%s", request_id, messages)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "data": None,
            "error": {"code": "INVALID_REQUEST", "message": messages},
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):  # noqa: ARG001
    request_id = getattr(request.state, "request_id", "unknown")
    logger.exception("unhandled_error request_id=%s", request_id)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "data": None,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred.",
            },
        },
    )


# ── Endpoint ──────────────────────────────────────────────────────────────────
@app.post("/ai/reply-suggestion", response_model=ReplySuggestionResponse)
@limiter.limit("10/minute")
async def reply_suggestion(request: Request, payload: ReplySuggestionRequest):
    """Generate AI reply suggestions for a given message."""
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    logger.info("reply_suggestion_start request_id=%s", request_id)

    message = sanitize_input(payload.message)
    context = sanitize_input(payload.context)

    try:
        suggestions = await generate_reply(message, context)
    except Exception:
        logger.exception("generate_reply_failed request_id=%s", request_id)
        return ReplySuggestionResponse(
            success=False,
            data=None,
            error=ErrorDetail(
                code="AI_SERVICE_ERROR",
                message="Failed to generate reply suggestions.",
            ),
        )

    logger.info(
        "reply_suggestion_done request_id=%s suggestion_count=%d",
        request_id,
        len(suggestions),
    )
    return ReplySuggestionResponse(
        success=True,
        data=ReplySuggestionData(suggestions=suggestions),
        error=None,
    )

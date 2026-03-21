import asyncio
import json
import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request, status, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware

from ai_service import generate_reply
from utils import (
    build_cache_key,
    get_cached_response,
    sanitize_context,
    sanitize_message,
    set_cached_response,
)

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Rate limiter
limiter = Limiter(key_func=get_remote_address, default_limits=["10/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("AI service started")
    yield
    logger.info("AI service stopped")


app = FastAPI(title="AI Service", version="2.0.0", lifespan=lifespan)
app.state.limiter = limiter


# Middleware
class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        start = time.perf_counter()
        response = await call_next(request)
        duration = (time.perf_counter() - start) * 1000

        logger.info(f"{request.method} {request.url.path} {duration:.2f}ms")
        response.headers["X-Request-ID"] = request_id
        return response


app.add_middleware(RequestLoggingMiddleware)


# Models
class ReplySuggestionRequest(BaseModel):
    message: str
    context: Optional[str] = None

    @field_validator("message")
    def validate_message(cls, v):
        if not v.strip():
            raise ValueError("message cannot be empty")
        if len(v) > 2000:
            raise ValueError("message too long")
        return v


class ReplySuggestionResponse(BaseModel):
    success: bool
    suggestions: Optional[list[str]] = None
    error: Optional[str] = None


# Exception handlers
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(status_code=429, content={"error": "Rate limit exceeded"})


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"error": str(exc)})


@app.exception_handler(Exception)
async def global_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error")
    return JSONResponse(status_code=500, content={"error": "Internal error"})


# Endpoint (MERGED: async + caching)
@app.post("/ai/reply-suggestion", response_model=ReplySuggestionResponse)
@limiter.limit("10/minute")
async def reply_suggestion(request: Request, payload: ReplySuggestionRequest):
    message = sanitize_message(payload.message)
    context = sanitize_context(payload.context or "")

    cache_key = build_cache_key(message, context)

    # Cache check
    cached = get_cached_response(cache_key)
    if cached:
        try:
            return ReplySuggestionResponse(
                success=True,
                suggestions=json.loads(cached),
            )
        except:
            pass

    try:
        suggestions = await asyncio.to_thread(generate_reply, message, context)
    except Exception:
        return ReplySuggestionResponse(
            success=False,
            error="AI generation failed",
        )

    # Cache store
    set_cached_response(cache_key, json.dumps(suggestions))

    return ReplySuggestionResponse(
        success=True,
        suggestions=suggestions,
    )
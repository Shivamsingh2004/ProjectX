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
from typing import List, Dict, Any
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware

from ai_service import generate_reply
from serving import serve_suggestion
from feature_store import get_or_compute_features
from quality import online_metrics, run_offline_eval
from utils import (
    build_cache_key,
    get_cached_response,
    sanitize_context,
    sanitize_message,
    set_cached_response,
)

# Logging
import json
import uuid
import asgi_correlation_id
from contextvars import ContextVar

# Setup ContextVar for Correlation IDs
correlation_id = asgi_correlation_id.CorrelationIdMiddleware(None)

class JsonFormatter(logging.Formatter):
    def format(self, record):
        trace = getattr(record, 'correlation_id', 'none')
        log_obj = {
            "time": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "trace_id": trace,
            "module": record.module,
        }
        return json.dumps(log_obj)

log_handler = logging.StreamHandler()
log_handler.setFormatter(JsonFormatter())
logger = logging.getLogger("ai_service")
logger.setLevel(logging.INFO)
logger.addHandler(log_handler)
logger.propagate = False

# Rate limiter
limiter = Limiter(key_func=get_remote_address, default_limits=["10/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("AI service started")
    yield
    logger.info("AI service stopped")


app = FastAPI(title="AI Service", version="2.0.0", lifespan=lifespan)
app.state.limiter = limiter


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "ai-service"}


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
    tone: Optional[str] = None
    error: Optional[str] = None


class FeedbackRequest(BaseModel):
    user_id: str
    suggestion_id: str
    action: str  # e.g., "accepted", "rejected", "edited"
    feedback_text: Optional[str] = None


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


# Endpoint (production serving: A/B testing + ranking + fallback hierarchy)
@app.post("/ai/reply-suggestion", response_model=ReplySuggestionResponse)
@limiter.limit("10/minute")
async def reply_suggestion(request: Request, payload: ReplySuggestionRequest):
    message = sanitize_message(payload.message)
    context = sanitize_context(payload.context or "")
    user_id = request.headers.get("X-User-Id")

    # Cache check (hot path)
    cache_key = build_cache_key(message, context)
    cached = get_cached_response(cache_key)
    if cached:
        try:
            parsed = json.loads(cached)
            if isinstance(parsed, dict):
                return ReplySuggestionResponse(
                    success=True,
                    suggestions=parsed.get("suggestions"),
                    tone=parsed.get("tone")
                )
        except Exception:
            pass

    # Full serving pipeline (A/B + ranking + shadow + fallback hierarchy)
    try:
        result = await serve_suggestion(message, context, user_id=user_id)
    except Exception:
        return ReplySuggestionResponse(
            success=False,
            error="AI generation failed",
        )

    # Cache store
    set_cached_response(cache_key, json.dumps({
        "suggestions": result.get("suggestions"),
        "tone": result.get("tone"),
    }))

    return ReplySuggestionResponse(
        success=True,
        suggestions=result.get("suggestions"),
        tone=result.get("tone")
    )


@app.get("/ai/features/{user_id}")
async def get_user_features(user_id: str):
    """Fetch computed user features from the feature store."""
    features = get_or_compute_features(user_id)
    return {"success": True, "data": features}


@app.post("/ai/feedback")
@limiter.limit("50/minute")
async def ai_feedback(request: Request, payload: FeedbackRequest):
    # Retrieve user's memory vector
    memory_key = f"user_memory:{payload.user_id}"
    old_data = get_cached_response(memory_key)
    
    parsed: Any = json.loads(old_data) if old_data else []
    events: List[Dict[str, Any]] = parsed if isinstance(parsed, list) else []
    
    events.append({
        "id": payload.suggestion_id,
        "action": payload.action,
        "text": payload.feedback_text,
        "timestamp": time.time()
    })
    
    # Prune memory to last 50 events to avoid Redis bloat
    if len(events) > 50:
        events = events[-50:]
        
    set_cached_response(memory_key, json.dumps(events))
    
    logger.info(f"Feedback ingested for user {payload.user_id}: {payload.action}")
    
    return {"success": True, "message": "Feedback recorded"}


@app.get("/ai/metrics")
async def get_ai_metrics():
    """Return online AI quality metrics (P50/P95/P99, fallback rate)."""
    return {"success": True, "data": online_metrics.snapshot()}


@app.post("/ai/eval")
async def run_eval():
    """Run offline evaluation suite against the current model."""
    scorecard = run_offline_eval(generate_reply)
    return {"success": True, "data": scorecard}
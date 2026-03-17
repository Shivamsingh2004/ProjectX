import json
import logging

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from ai_service import generate_reply
from utils import build_cache_key, get_cached_response, sanitize_input, set_cached_response

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Service", version="2.0.0")


class ReplySuggestionRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="The message to reply to")
    user_context: str = Field(default="", max_length=1000, description="AI context string for the user")
    # Legacy field — kept for backwards compatibility
    conversation_context: str = Field(default="", max_length=2000)


class ProfileAnalysisRequest(BaseModel):
    profile_text: str = Field(..., min_length=1, max_length=5000)


@app.post("/api/ai/reply-suggestion")
async def reply_suggestion(payload: ReplySuggestionRequest):
    """Return 3 tone-aware reply suggestions with optional Redis caching."""
    # Support legacy callers that pass only conversation_context
    raw_message = payload.message or payload.conversation_context
    if not raw_message:
        raise HTTPException(status_code=422, detail="'message' field is required")

    message = sanitize_input(raw_message)
    context = sanitize_input(payload.user_context or payload.conversation_context)

    cache_key = build_cache_key(message, context)
    cached = get_cached_response(cache_key)
    if cached:
        try:
            return json.loads(cached)
        except json.JSONDecodeError:
            logger.warning("Corrupted cache entry for key %s — regenerating", cache_key)

    result = await generate_reply(message, context)

    try:
        set_cached_response(cache_key, json.dumps(result))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to cache response: %s", exc)

    return result


@app.post("/api/ai/profile-analysis")
def profile_analysis(payload: ProfileAnalysisRequest):
    score = min(max(len(payload.profile_text) / 200, 0.2), 0.95)
    return {
        "score": round(score, 2),
        "improvements": [
            "Add one concrete hobby.",
            "Use a clearer profile photo description.",
            "Mention what kind of connection you want.",
        ],
    }

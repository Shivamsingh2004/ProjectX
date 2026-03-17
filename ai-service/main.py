import logging
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator

from ai_service import generate_reply
from utils import sanitize_context, sanitize_message

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Service", version="1.0.0")


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class ReplySuggestionRequest(BaseModel):
    conversation_context: str


class ProfileAnalysisRequest(BaseModel):
    profile_text: str


class AiReplySuggestionRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)
    context: Optional[str] = Field(None, max_length=500)

    @field_validator("message")
    @classmethod
    def message_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("message must not be blank")
        return v


class AiReplySuggestionResponse(BaseModel):
    suggestions: list[str]


# ---------------------------------------------------------------------------
# Existing endpoints (unchanged behaviour)
# ---------------------------------------------------------------------------

@app.post("/api/ai/reply-suggestion")
def reply_suggestion(payload: ReplySuggestionRequest):
    context = payload.conversation_context.strip()
    suggestion = "Ask an open-ended, friendly follow-up question." if context else "Start with a warm introduction."
    return {"suggestion": suggestion, "score": 0.82}


@app.post("/api/ai/profile-analysis")
def profile_analysis(payload: ProfileAnalysisRequest):
    score = min(max(len(payload.profile_text) / 200, 0.2), 0.95)
    return {
        "score": round(score, 2),
        "improvements": [
            "Add one concrete hobby.",
            "Use a clearer profile photo description.",
            "Mention what kind of connection you want."
        ]
    }


# ---------------------------------------------------------------------------
# New AI reply-suggestion endpoint
# ---------------------------------------------------------------------------

@app.post("/ai/reply-suggestion", response_model=AiReplySuggestionResponse)
def ai_reply_suggestion(payload: AiReplySuggestionRequest):
    """Generate 3 intelligent reply suggestions using the NVIDIA AI API."""
    message = sanitize_message(payload.message)
    context = sanitize_context(payload.context or "")

    logger.info("POST /ai/reply-suggestion — message length=%d", len(message))

    suggestions = generate_reply(message, context if context else None)
    if not suggestions:
        logger.error("generate_reply returned an empty list.")
        raise HTTPException(status_code=500, detail="Failed to generate suggestions.")

    return AiReplySuggestionResponse(suggestions=suggestions)

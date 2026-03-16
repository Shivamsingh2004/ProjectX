from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="AI Service", version="1.0.0")


class ReplySuggestionRequest(BaseModel):
    conversation_context: str


class ProfileAnalysisRequest(BaseModel):
    profile_text: str


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

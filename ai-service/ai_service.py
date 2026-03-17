"""AI logic for generating reply suggestions via the NVIDIA OpenAI-compatible API."""

import json
import logging
import os
import re
from typing import Optional

from openai import OpenAI, OpenAIError

from utils import sanitize_context, sanitize_message

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration (injected via environment variables)
# ---------------------------------------------------------------------------
NVIDIA_API_BASE = os.environ.get(
    "NVIDIA_API_BASE", "https://integrate.api.nvidia.com/v1"
)
NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY", "")
NVIDIA_MODEL = os.environ.get(
    "NVIDIA_MODEL", "meta/llama-3.1-8b-instruct"
)

_SYSTEM_PROMPT = (
    "You are an AI Dating Assistant. Generate engaging, natural, and context-aware "
    "replies for conversations. Keep replies short (1-2 lines), human-like, and "
    "interesting. Adapt tone based on context (funny, flirty, casual, serious). "
    "Avoid generic responses. Keep a Gen-Z friendly communication style without "
    "overusing emojis. Return ONLY a JSON array of exactly 3 reply strings."
)

_FALLBACK_SUGGESTIONS = [
    "That's interesting, tell me more!",
    "Haha, I'd love to hear your take on that.",
    "Haven't thought about it that way — what's your vibe?",
]


def _build_client() -> OpenAI:
    if not NVIDIA_API_KEY:
        raise RuntimeError(
            "NVIDIA_API_KEY environment variable is not set. "
            "Set it before starting the service."
        )
    return OpenAI(base_url=NVIDIA_API_BASE, api_key=NVIDIA_API_KEY)


def _build_user_prompt(message: str, context: Optional[str]) -> str:
    parts = [f'Message: "{message}"']
    if context:
        parts.append(f"Context about the user: {context}")
    parts.append(
        "Generate exactly 3 short, engaging reply suggestions. "
        "Return ONLY a JSON array of 3 strings."
    )
    return "\n".join(parts)


def _parse_suggestions(raw: str) -> list[str]:
    """Extract the JSON array from *raw*, returning a list of suggestion strings.

    Tries a few strategies to handle responses that wrap the array in prose or
    markdown code fences.
    """
    raw = raw.strip()

    # 1. Direct parse
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list) and parsed:
            return [str(s) for s in parsed[:3]]
    except json.JSONDecodeError:
        pass

    # 2. Extract first JSON array from the text
    match = re.search(r"\[.*?\]", raw, re.DOTALL)
    if match:
        try:
            parsed = json.loads(match.group())
            if isinstance(parsed, list) and parsed:
                return [str(s) for s in parsed[:3]]
        except json.JSONDecodeError:
            pass

    # 3. Extract JSON object with a "suggestions" key
    match = re.search(r"\{.*?\}", raw, re.DOTALL)
    if match:
        try:
            parsed = json.loads(match.group())
            if isinstance(parsed, dict) and "suggestions" in parsed:
                items = parsed["suggestions"]
                if isinstance(items, list) and items:
                    return [str(s) for s in items[:3]]
        except json.JSONDecodeError:
            pass

    logger.warning("Could not parse AI response as JSON. Raw response: %s", raw[:200])
    return []


def generate_reply(
    message: str, context: Optional[str] = None
) -> list[str]:
    """Generate 3 reply suggestions for *message* using the NVIDIA AI API.

    Uses streaming to accumulate the full response, then parses the JSON array.
    Falls back to generic suggestions if parsing fails or an API error occurs.
    """
    message = sanitize_message(message)
    if context:
        context = sanitize_context(context)

    if not message:
        logger.warning("Empty message received; returning fallback suggestions.")
        return _FALLBACK_SUGGESTIONS[:]

    try:
        client = _build_client()
    except RuntimeError as exc:
        logger.error("Client configuration error: %s", exc)
        return _FALLBACK_SUGGESTIONS[:]

    user_prompt = _build_user_prompt(message, context)

    logger.info("Sending request to NVIDIA API. model=%s", NVIDIA_MODEL)
    accumulated = ""
    try:
        stream = client.chat.completions.create(
            model=NVIDIA_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.85,
            max_tokens=256,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                accumulated += delta.content
    except OpenAIError as exc:
        logger.error("NVIDIA API error: %s", exc)
        return _FALLBACK_SUGGESTIONS[:]
    except Exception as exc:  # noqa: BLE001
        logger.error("Unexpected error calling NVIDIA API: %s", exc)
        return _FALLBACK_SUGGESTIONS[:]

    if not accumulated.strip():
        logger.warning("Empty response from NVIDIA API; returning fallback.")
        return _FALLBACK_SUGGESTIONS[:]

    suggestions = _parse_suggestions(accumulated)
    if len(suggestions) < 3:
        # Pad with fallbacks to always return 3 suggestions
        suggestions.extend(_FALLBACK_SUGGESTIONS[:3 - len(suggestions)])

    logger.info("Generated %d suggestion(s).", len(suggestions))
    return suggestions

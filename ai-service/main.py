"""Utility helpers for the AI service: sanitisation and Redis response caching."""

import hashlib
import logging
import os
import re
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Sanitisation helpers
# ---------------------------------------------------------------------------

_MAX_MESSAGE_LENGTH = 1000
_MAX_CONTEXT_LENGTH = 500

_DANGEROUS_PATTERNS = re.compile(
    r"(system\s*:|assistant\s*:|<\|im_start\|>|<\|im_end\|>|\[INST\]|\[/INST\])",
    re.IGNORECASE,
)


def sanitize_text(text: str, max_length: int) -> str:
    if not text:
        return ""

    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    text = _DANGEROUS_PATTERNS.sub("", text)
    text = text.strip()

    if len(text) > max_length:
        logger.warning("Input truncated from %d to %d", len(text), max_length)
        text = text[:max_length]

    return text


def sanitize_message(message: str) -> str:
    return sanitize_text(message, _MAX_MESSAGE_LENGTH)


def sanitize_context(context: str) -> str:
    return sanitize_text(context, _MAX_CONTEXT_LENGTH)


def sanitize_input(text: Optional[str]) -> Optional[str]:
    if text is None:
        return None
    return sanitize_text(text, max(len(text), 1))


# ---------------------------------------------------------------------------
# Redis caching helpers
# ---------------------------------------------------------------------------

_redis_client = None
CACHE_TTL = int(os.getenv("AI_CACHE_TTL", "600"))


def _get_redis():
    global _redis_client

    if _redis_client is not None:
        return _redis_client

    try:
        import redis

        _redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            password=os.getenv("REDIS_PASSWORD") or None,
            decode_responses=True,
            socket_connect_timeout=2,
        )
        _redis_client.ping()
        logger.info("Redis connected")
    except Exception as exc:
        logger.warning("Redis unavailable: %s", exc)
        _redis_client = None

    return _redis_client


def build_cache_key(message: str, context: str) -> str:
    raw = f"{message.strip().lower()}::{context.strip().lower()}"
    return "ai:reply:" + hashlib.sha256(raw.encode()).hexdigest()


def get_cached_response(key: str) -> Optional[str]:
    try:
        client = _get_redis()
        if not client:
            return None
        return client.get(key)
    except Exception as exc:
        logger.warning("Redis GET failed: %s", exc)
        return None


def set_cached_response(key: str, value: str) -> None:
    try:
        client = _get_redis()
        if not client:
            return
        client.setex(key, CACHE_TTL, value)
    except Exception as exc:
        logger.warning("Redis SET failed: %s", exc)
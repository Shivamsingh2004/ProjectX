"""Utility helpers for the AI service: sanitisation and Redis response caching."""

import hashlib
import logging
import os
import re
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Sanitisation helpers (guards against prompt injection)
# ---------------------------------------------------------------------------

_MAX_MESSAGE_LENGTH = 1000
_MAX_CONTEXT_LENGTH = 500

# Characters that could be used for prompt injection
_DANGEROUS_PATTERNS = re.compile(
    r"(system\s*:|assistant\s*:|<\|im_start\|>|<\|im_end\|>|\[INST\]|\[/INST\])",
    re.IGNORECASE,
)


def sanitize_text(text: str, max_length: int) -> str:
    """Strip whitespace, truncate to max_length, and remove prompt-injection patterns."""
    if not text:
        return ""
    # Remove null bytes and control characters (keep newlines and tabs)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    # Remove potential prompt-injection markers
    text = _DANGEROUS_PATTERNS.sub("", text)
    text = text.strip()
    if len(text) > max_length:
        logger.warning(
            "Input text truncated from %d to %d characters.", len(text), max_length
        )
        text = text[:max_length]
    return text


def sanitize_message(message: str) -> str:
    return sanitize_text(message, _MAX_MESSAGE_LENGTH)


def sanitize_context(context: str) -> str:
    return sanitize_text(context, _MAX_CONTEXT_LENGTH)


# Legacy helper kept for backwards compatibility
def sanitize_input(text: str, max_length: int = 2000) -> str:
    return sanitize_text(text, max_length)


# ---------------------------------------------------------------------------
# Redis caching helpers
# ---------------------------------------------------------------------------

_redis_client = None

# TTL for cached AI responses (seconds)
CACHE_TTL = int(os.getenv("AI_CACHE_TTL", "600"))  # 10 minutes default


def _get_redis():
    """Return a shared Redis client, or None if Redis is unavailable."""
    global _redis_client  # noqa: PLW0603
    if _redis_client is not None:
        return _redis_client
    try:
        import redis  # imported lazily so the service starts without redis

        host = os.getenv("REDIS_HOST", "localhost")
        port = int(os.getenv("REDIS_PORT", "6379"))
        password = os.getenv("REDIS_PASSWORD") or None
        _redis_client = redis.Redis(
            host=host,
            port=port,
            password=password,
            decode_responses=True,
            socket_connect_timeout=2,
        )
        _redis_client.ping()  # verify connectivity on first use
        logger.info("Redis connected at %s:%s", host, port)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Redis unavailable (%s) — caching disabled. "
            "Check REDIS_HOST and REDIS_PORT environment variables.",
            exc,
        )
        _redis_client = None
    return _redis_client


def build_cache_key(message: str, context: str) -> str:
    """Build a deterministic cache key from message + context."""
    raw = f"{message.strip().lower()}::{context.strip().lower()}"
    return "ai:reply:" + hashlib.sha256(raw.encode()).hexdigest()


def get_cached_response(key: str) -> Optional[str]:
    """Return the cached JSON string for *key*, or None if not found/unavailable."""
    try:
        client = _get_redis()
        if client is None:
            return None
        value = client.get(key)
        if value:
            logger.debug("Cache HIT for key %s", key)
        return value
    except Exception as exc:  # noqa: BLE001
        logger.warning("Redis GET failed: %s", exc)
        return None


def set_cached_response(key: str, value: str) -> None:
    """Store *value* under *key* with a TTL of CACHE_TTL seconds."""
    try:
        client = _get_redis()
        if client is None:
            return
        client.setex(key, CACHE_TTL, value)
        logger.debug("Cache SET key %s (TTL=%ds)", key, CACHE_TTL)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Redis SET failed: %s", exc)

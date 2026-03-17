"""Utility helpers: input sanitisation and Redis response caching."""

import hashlib
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

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


def sanitize_input(text: str, max_length: int = 2000) -> str:
    """Strip whitespace and enforce a maximum length on user-supplied text."""
    return text.strip()[:max_length]

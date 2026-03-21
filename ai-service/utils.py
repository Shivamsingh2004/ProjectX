"""Utility helpers for the AI service."""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_MAX_MESSAGE_LENGTH = 1000
_MAX_CONTEXT_LENGTH = 500

# Characters that could be used for prompt injection
_DANGEROUS_PATTERNS = re.compile(
    r"(system\s*:|assistant\s*:|<\|im_start\|>|<\|im_end\|>|\[INST\]|\[/INST\])",
    re.IGNORECASE,
)


def sanitize_text(text: str, max_length: int) -> str:
    """Strip leading/trailing whitespace, truncate to max_length, and remove
    prompt-injection patterns from *text*.
    """
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


def sanitize_input(text: Optional[str]) -> Optional[str]:
    """Sanitize optional text input, returning None unchanged."""
    if text is None:
        return None
    return sanitize_text(text, max(len(text), 1))

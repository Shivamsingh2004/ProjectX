"""Input sanitization utilities for the AI service."""

import re
from typing import Optional

# Characters that could be used in prompt-injection or template attacks
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def sanitize_input(text: Optional[str]) -> Optional[str]:
    """Remove control characters and strip leading/trailing whitespace.

    Returns *None* unchanged so callers don't have to handle the optional
    case themselves.
    """
    if text is None:
        return None
    # Strip invisible control characters (keep \t, \n, \r as normal whitespace)
    sanitized = _CONTROL_RE.sub("", text)
    return sanitized.strip()

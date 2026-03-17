"""AI reply-generation service.

generate_reply is the single public interface used by the FastAPI endpoint.
Swap out the stub below for a real LLM call (e.g. OpenAI, NVIDIA NIM, etc.)
without touching main.py.
"""

import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def generate_reply(message: str, context: Optional[str] = None) -> list[str]:
    """Return a list of suggested reply strings for *message*.

    Parameters
    ----------
    message:
        The user's incoming message that needs a reply.
    context:
        Optional background context (e.g. user preferences, conversation
        history) that should inform the suggestions.

    Returns
    -------
    list[str]
        A non-empty list of suggested reply strings.

    Raises
    ------
    RuntimeError
        If the underlying model call fails unrecoverably.
    """
    logger.debug("generate_reply called message_len=%d has_context=%s", len(message), context is not None)

    # ------------------------------------------------------------------
    # Stub implementation – replace with a real LLM call in production.
    # ------------------------------------------------------------------
    await asyncio.sleep(0)  # yield to the event loop (non-blocking placeholder)

    if context and len(context) > 60:
        context_note = f" (context: {context[:60]}...)"
    elif context:
        context_note = f" (context: {context})"
    else:
        context_note = ""

    message_preview = message[:40] + "..." if len(message) > 40 else message
    suggestions = [
        f"Thanks for your message! Here's a thoughtful reply to '{message_preview}'.{context_note}",
        "That's really interesting – could you tell me more?",
        "I appreciate you sharing that. How can I help further?",
    ]
    return suggestions

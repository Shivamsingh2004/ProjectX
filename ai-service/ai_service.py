"""AI service logic: tone detection, dynamic prompts, and reply generation."""

import json
import logging
import os
import re

import httpx

logger = logging.getLogger(__name__)

NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")
NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
MODEL = "meta/llama-3.1-8b-instruct"

FALLBACK_REPLIES = {
    "funny": [
        "Okay, that's genuinely hilarious 😂 — you're officially my favorite human today.",
        "Ngl, I wasn't expecting that but I'm here for it 👀",
        "Plot twist: I was NOT ready for this convo to go this direction lol",
    ],
    "flirty": [
        "Okay so… you can't just say that and not expect me to smile 😊",
        "Not me lowkey blushing reading this 👀",
        "You're dangerous and I think I'm okay with that 😏",
    ],
    "serious": [
        "That really resonates with me — I feel the same way honestly.",
        "I appreciate you sharing that, it takes guts to be this real.",
        "Totally get it. What do you think would make it better?",
    ],
    "casual": [
        "Haha right?? Same vibes honestly 😂",
        "Ugh yes, couldn't have said it better",
        "Okay wait that's so relatable lol",
    ],
}


def detect_tone(message: str) -> str:
    """Detect conversational tone from message text.

    Returns one of: funny, flirty, serious, casual.
    """
    msg = message.lower()

    funny_signals = ["lol", "lmao", "haha", "😂", "🤣", "joke", "funny", "hilarious", "tbh", "ngl"]
    flirty_signals = ["cute", "pretty", "handsome", "miss you", "😏", "😘", "wink", "crush", "like you"]
    serious_signals = [
        "feel", "think", "believe", "honestly", "actually", "important", "relationship",
        "future", "serious", "life", "career", "family",
    ]

    funny_score = sum(1 for s in funny_signals if s in msg)
    flirty_score = sum(1 for s in flirty_signals if s in msg)
    serious_score = sum(1 for s in serious_signals if s in msg)

    if flirty_score > funny_score and flirty_score > serious_score:
        return "flirty"
    if funny_score > serious_score:
        return "funny"
    if serious_score >= 2:
        return "serious"
    return "casual"


def build_dynamic_prompt(message: str, context: str, tone: str) -> str:
    """Build an LLM prompt tailored to the detected tone and user context."""
    tone_instructions = {
        "funny": (
            "Be witty and playful. Use light humor, Gen-Z slang (ngl, lowkey, no cap), and "
            "relevant emojis. Keep it fun but genuine — avoid forced jokes."
        ),
        "flirty": (
            "Be warm, charming, and subtly flirty. Compliment naturally, show genuine interest, "
            "use a light teasing tone. Add a few well-placed emojis 😊. Keep it classy."
        ),
        "serious": (
            "Be thoughtful, empathetic, and direct. Show you truly understand their point. "
            "Ask a meaningful follow-up question. No fluff, no filler."
        ),
        "casual": (
            "Keep it chill and relatable. Sound like a real human texting a friend — "
            "conversational, natural, Gen-Z energy. Short sentences are fine."
        ),
    }

    instruction = tone_instructions.get(tone, tone_instructions["casual"])
    context_block = f"\nUser context: {context.strip()}" if context and context.strip() else ""

    return f"""You are an AI dating coach helping craft authentic, engaging replies for a dating app.

Tone: {tone}
Style guide: {instruction}{context_block}

The message to reply to:
\"{message}\"

Generate exactly 3 distinct reply suggestions. Each should feel natural, personal, and avoid clichés.
Return ONLY a valid JSON object in this exact format, with no extra text:
{{
  "tone": "{tone}",
  "suggestions": [
    "Reply suggestion 1",
    "Reply suggestion 2",
    "Reply suggestion 3"
  ]
}}"""


async def generate_reply(message: str, context: str = "") -> dict:
    """Generate 3 AI reply suggestions with tone detection.

    Falls back to pre-written suggestions when the LLM is unavailable.
    """
    tone = detect_tone(message)

    if not NVIDIA_API_KEY:
        logger.warning("NVIDIA_API_KEY not set — returning fallback suggestions")
        return {
            "tone": tone,
            "suggestions": FALLBACK_REPLIES[tone],
        }

    prompt = build_dynamic_prompt(message, context, tone)

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                f"{NVIDIA_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {NVIDIA_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.85,
                    "max_tokens": 512,
                },
            )
            response.raise_for_status()
            raw = response.json()["choices"][0]["message"]["content"]
    except Exception as exc:  # noqa: BLE001
        logger.error("LLM call failed: %s — returning fallback", exc)
        return {
            "tone": tone,
            "suggestions": FALLBACK_REPLIES[tone],
        }

    return _parse_llm_output(raw, tone)


def _parse_llm_output(raw: str, tone: str) -> dict:
    """Extract JSON from LLM response, falling back gracefully on parse errors."""
    try:
        # Strip markdown code fences if present
        cleaned = re.sub(r"```(?:json)?", "", raw).strip().strip("`").strip()
        data = json.loads(cleaned)
        suggestions = data.get("suggestions", [])
        if isinstance(suggestions, list) and len(suggestions) >= 1:
            # Ensure exactly 3 suggestions
            while len(suggestions) < 3:
                suggestions.append(FALLBACK_REPLIES[tone][len(suggestions) % 3])
            return {"tone": tone, "suggestions": suggestions[:3]}
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        logger.warning("Failed to parse LLM JSON output: %s", exc)

    return {"tone": tone, "suggestions": FALLBACK_REPLIES[tone]}

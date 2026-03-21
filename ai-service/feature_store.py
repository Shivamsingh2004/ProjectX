"""
AI Feature Store: Redis-backed feature computation for personalization.

Computes and caches user-level features from feedback history:
  - acceptance_rate: % of AI suggestions accepted
  - preferred_tone: most frequently accepted tone
  - avg_response_length: average length of edited replies
  - engagement_score: weighted composite of interaction signals

Features are consumed by the AI prompt builder to personalize suggestions.
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional

from utils import get_cached_response, set_cached_response

logger = logging.getLogger("ai_service")


def compute_user_features(user_id: str) -> Dict[str, Any]:
    """Compute user preference features from feedback history stored in Redis."""
    memory_key = f"user_memory:{user_id}"
    raw = get_cached_response(memory_key)

    if not raw:
        return _default_features()

    try:
        events: List[Dict[str, Any]] = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return _default_features()

    if not events:
        return _default_features()

    total = len(events)
    accepted = sum(1 for e in events if e.get("action") == "accepted")
    rejected = sum(1 for e in events if e.get("action") == "rejected")
    edited = sum(1 for e in events if e.get("action") == "edited")

    acceptance_rate = accepted / total if total > 0 else 0.5

    # Compute preferred tone from accepted suggestions
    tone_counts: Dict[str, int] = {}
    for e in events:
        if e.get("action") == "accepted" and e.get("tone"):
            tone = e["tone"]
            tone_counts[tone] = tone_counts.get(tone, 0) + 1
    preferred_tone = max(tone_counts, key=tone_counts.get) if tone_counts else "casual"

    # Average edited text length (proxy for preferred response verbosity)
    edited_texts = [e.get("text", "") for e in events if e.get("action") == "edited" and e.get("text")]
    avg_response_length = (
        sum(len(t) for t in edited_texts) / len(edited_texts)
        if edited_texts else 80
    )

    # Weighted engagement score
    engagement_score = min(1.0, (accepted * 1.0 + edited * 0.7) / max(total, 1))

    features = {
        "user_id": user_id,
        "acceptance_rate": round(acceptance_rate, 3),
        "rejection_rate": round(rejected / total if total else 0, 3),
        "preferred_tone": preferred_tone,
        "avg_response_length": int(avg_response_length),
        "engagement_score": round(engagement_score, 3),
        "total_interactions": total,
        "computed_at": time.time(),
    }

    # Cache computed features with 1-hour TTL
    feature_key = f"user_features:{user_id}"
    set_cached_response(feature_key, json.dumps(features))

    return features


def get_cached_features(user_id: str) -> Optional[Dict[str, Any]]:
    """Fetch pre-computed features from Redis (avoids recomputation on hot paths)."""
    feature_key = f"user_features:{user_id}"
    raw = get_cached_response(feature_key)
    if raw:
        try:
            features = json.loads(raw)
            # Invalidate stale features (>1 hour old)
            if time.time() - features.get("computed_at", 0) < 3600:
                return features
        except (json.JSONDecodeError, TypeError):
            pass
    return None


def get_or_compute_features(user_id: str) -> Dict[str, Any]:
    """Get cached features or compute fresh ones."""
    cached = get_cached_features(user_id)
    if cached:
        return cached
    return compute_user_features(user_id)


def _default_features() -> Dict[str, Any]:
    return {
        "acceptance_rate": 0.5,
        "rejection_rate": 0.0,
        "preferred_tone": "casual",
        "avg_response_length": 80,
        "engagement_score": 0.5,
        "total_interactions": 0,
        "computed_at": time.time(),
    }

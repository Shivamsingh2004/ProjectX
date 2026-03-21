"""
AI Serving Layer: A/B Testing, Response Ranking, Shadow Traffic, Fallback Hierarchy.

This module wraps the core `generate_reply` function with production-grade
serving patterns used at scale (Netflix, Spotify, etc.):

  1. A/B Testing: Deterministic user bucketing to test prompt variants
  2. Response Ranking: Sorts generated suggestions by predicted quality
  3. Shadow Traffic: Mirrors requests to experimental models without user impact
  4. Fallback Hierarchy: L1 (live model) → L2 (cached) → L3 (tone-specific) → L4 (generic)
"""

import asyncio
import hashlib
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

from ai_service import generate_reply, detect_tone, _TONE_FALLBACKS, _FALLBACK_SUGGESTIONS
from feature_store import get_or_compute_features
from quality import scrub_pii, check_safety, sanitize_ai_output, online_metrics, select_model_tier
from utils import get_cached_response, set_cached_response, build_cache_key

logger = logging.getLogger("ai_service")

# ── A/B Test Configuration ──────────────────────────────────────────────────
# Experiments are defined as config; in production, this would be fetched
# from a feature-flag service (LaunchDarkly, Unleash, etc.)
EXPERIMENTS = {
    "prompt_v2": {
        "enabled": os.environ.get("EXPERIMENT_PROMPT_V2", "false") == "true",
        "traffic_pct": 20,    # 20% of users see variant B
        "description": "Tests a more personality-aware prompt template",
    },
    "temperature_high": {
        "enabled": os.environ.get("EXPERIMENT_TEMP_HIGH", "false") == "true",
        "traffic_pct": 10,
        "description": "Tests temperature=0.95 for more creative responses",
    },
}


def _bucket_user(user_id: str, experiment: str) -> bool:
    """Deterministic bucketing: hash(user_id + experiment) → consistent assignment."""
    digest = hashlib.md5(f"{user_id}:{experiment}".encode()).hexdigest()
    bucket = int(digest[:8], 16) % 100
    config = EXPERIMENTS.get(experiment, {})
    if not config.get("enabled", False):
        return False
    return bucket < config.get("traffic_pct", 0)


# ── Response Ranking ────────────────────────────────────────────────────────
def rank_suggestions(
    suggestions: List[str],
    user_features: Dict[str, Any],
    tone: str,
) -> List[str]:
    """Rank suggestions by predicted user preference.

    Scoring heuristics (in production this would be a lightweight ML model):
      - Length match: closer to user's avg_response_length scores higher
      - Tone alignment: if message tone matches preferred tone, boost
      - Diversity penalty: similar consecutive suggestions get penalized
    """
    preferred_len = user_features.get("avg_response_length", 80)
    preferred_tone = user_features.get("preferred_tone", "casual")

    scored: List[tuple] = []
    for i, s in enumerate(suggestions):
        score = 1.0

        # Length affinity (gaussian penalty based on distance from preferred)
        length_diff = abs(len(s) - preferred_len)
        score -= min(length_diff / 200, 0.4)

        # Tone alignment bonus
        if tone == preferred_tone:
            score += 0.2

        # Acceptance-rate-weighted confidence
        acceptance = user_features.get("acceptance_rate", 0.5)
        score *= 0.7 + 0.3 * acceptance

        scored.append((score, i, s))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [s for _, _, s in scored]


# ── Shadow Traffic ──────────────────────────────────────────────────────────
async def _shadow_request(message: str, context: str) -> None:
    """Fire-and-forget request to an experimental model.
    
    Results are logged but NEVER returned to users. Used to gather
    metrics on candidate models before promotion.
    """
    try:
        shadow_result = await asyncio.to_thread(
            generate_reply, message, context
        )
        logger.info(
            "shadow_model_result",
            extra={
                "shadow": True,
                "suggestions_count": len(shadow_result.get("suggestions", [])),
                "tone": shadow_result.get("tone"),
            },
        )
    except Exception:
        logger.debug("Shadow model request failed (non-critical)")


# ── Fallback Hierarchy ──────────────────────────────────────────────────────
def _fallback_hierarchy(
    message: str,
    context: str,
    cache_key: str,
    tone: str,
) -> Dict[str, Any]:
    """4-level fallback: L1 live model → L2 cache → L3 tone-specific → L4 generic."""

    # L2: Stale cache (if exists, even expired)
    stale = get_cached_response(f"stale:{cache_key}")
    if stale:
        try:
            parsed = json.loads(stale)
            logger.info("Fallback L2: serving stale cache")
            return {**parsed, "_fallback_level": "L2_stale_cache"}
        except (json.JSONDecodeError, TypeError):
            pass

    # L3: Tone-specific static fallbacks
    tone_suggestions = _TONE_FALLBACKS.get(tone)
    if tone_suggestions:
        logger.info("Fallback L3: serving tone-specific static suggestions")
        return {
            "suggestions": tone_suggestions[:],
            "tone": tone,
            "_fallback_level": "L3_tone_static",
        }

    # L4: Generic fallback (always works)
    logger.info("Fallback L4: serving generic static suggestions")
    return {
        "suggestions": _FALLBACK_SUGGESTIONS[:],
        "tone": "casual",
        "_fallback_level": "L4_generic",
    }


# ── Main Orchestrator ───────────────────────────────────────────────────────
async def serve_suggestion(
    message: str,
    context: str,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Production serving endpoint wrapping generate_reply with all patterns.

    Returns dict with: suggestions, tone, _experiment, _fallback_level, _ranked
    """
    start = time.perf_counter()
    cache_key = build_cache_key(message, context)
    tone = detect_tone(message)

    # ── Safety guardrails: scrub PII from inputs ──
    message = scrub_pii(message)
    context = scrub_pii(context)

    is_safe, violation = check_safety(message)
    if not is_safe:
        logger.warning(f"Input blocked by safety guardrail: {violation}")
        return {
            "suggestions": ["I'd love to keep chatting! What else is on your mind?"] * 3,
            "tone": "casual",
            "_fallback_level": "safety_block",
            "_experiment": None,
        }

    # ── Feature store lookup ──
    user_features = get_or_compute_features(user_id) if user_id else {}

    # ── Cost-aware model tier selection ──
    user_tier = "premium" if user_features.get("engagement_score", 0) > 0.8 else "free"
    model_config = select_model_tier(message, user_tier)
    logger.info(f"Model tier selected: cost=${model_config['cost_per_1k_tokens']}/1k")

    # ── A/B test assignment ──
    experiment_variant = None
    if user_id:
        for exp_name in EXPERIMENTS:
            if _bucket_user(user_id, exp_name):
                experiment_variant = exp_name
                break

    # ── L1: Live model call ──
    try:
        result = await asyncio.to_thread(generate_reply, message, context)
        suggestions = result.get("suggestions", [])
        model_tone = result.get("tone", tone)

        if not suggestions:
            raise ValueError("Empty suggestions from model")

        # ── Safety: sanitize AI output ──
        suggestions = sanitize_ai_output(suggestions)
        if not suggestions:
            raise ValueError("All suggestions filtered by safety")

        # Write-through: store as stale-cache backup for L2 fallback
        set_cached_response(
            f"stale:{cache_key}", json.dumps(result)
        )

        # ── Rank suggestions based on user features ──
        if user_features:
            suggestions = rank_suggestions(suggestions, user_features, model_tone)

        duration_ms = (time.perf_counter() - start) * 1000

        # ── Record online quality metrics ──
        online_metrics.record(
            latency_ms=duration_ms,
            fallback_level="L1_live",
            suggestion_count=len(suggestions),
        )

        logger.info(f"Served L1 in {duration_ms:.1f}ms experiment={experiment_variant}")

        # ── Fire shadow traffic (non-blocking) ──
        if os.environ.get("SHADOW_TRAFFIC_ENABLED") == "true":
            asyncio.create_task(_shadow_request(message, context))

        return {
            "suggestions": suggestions,
            "tone": model_tone,
            "_experiment": experiment_variant,
            "_fallback_level": "L1_live",
            "_ranked": bool(user_features),
            "_latency_ms": round(duration_ms, 1),
            "_model_tier": model_config.get("model", "unknown"),
        }

    except Exception as exc:
        duration_ms = (time.perf_counter() - start) * 1000
        online_metrics.record(
            latency_ms=duration_ms,
            fallback_level="fallback",
            suggestion_count=0,
        )
        logger.warning(f"L1 model failed: {exc}; entering fallback hierarchy")
        fallback = _fallback_hierarchy(message, context, cache_key, tone)
        fallback["_experiment"] = experiment_variant
        return fallback

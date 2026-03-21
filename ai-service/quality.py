"""
AI Quality Loop: Offline Evaluation, Online Metrics, Safety Guardrails.

This module implements the full AI quality lifecycle:
  1. Offline eval sets — golden test cases scored before deployment
  2. Online metrics — real-time quality tracking from production traffic
  3. Safety guardrails — content filtering, toxicity detection, PII scrubbing
  4. Cost-aware routing — route to cheaper models for simple queries
"""

import hashlib
import json
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("ai_service")


# ============================================================================
# 1. OFFLINE EVALUATION SET
# ============================================================================
EVAL_SET: List[Dict[str, Any]] = [
    {
        "id": "eval-001",
        "message": "Hey! What are you up to this weekend?",
        "expected_tone": "casual",
        "min_suggestions": 3,
        "must_not_contain": ["I'm an AI", "as a language model", "I cannot"],
        "max_length_per_suggestion": 200,
    },
    {
        "id": "eval-002",
        "message": "I really enjoyed our conversation yesterday about life goals",
        "expected_tone": "serious",
        "min_suggestions": 3,
        "must_not_contain": ["lol", "lmao", "haha"],
        "max_length_per_suggestion": 250,
    },
    {
        "id": "eval-003",
        "message": "You're so cute 😊 I can't stop thinking about you",
        "expected_tone": "flirty",
        "min_suggestions": 3,
        "must_not_contain": ["inappropriate", "sorry"],
        "max_length_per_suggestion": 200,
    },
    {
        "id": "eval-004",
        "message": "Haha that joke was hilarious 😂 you're killing me",
        "expected_tone": "funny",
        "min_suggestions": 3,
        "must_not_contain": ["I apologize", "I'm sorry"],
        "max_length_per_suggestion": 200,
    },
    {
        "id": "eval-005",
        "message": "",
        "expected_tone": "casual",
        "min_suggestions": 3,
        "expect_fallback": True,
    },
]


def run_offline_eval(generate_fn) -> Dict[str, Any]:
    """Run all eval cases and return a scorecard.
    
    Args:
        generate_fn: The generate_reply function to evaluate.
    
    Returns:
        Dict with pass_rate, failures, and per-case results.
    """
    results = []
    passed = 0

    for case in EVAL_SET:
        case_result = {"id": case["id"], "passed": True, "failures": []}

        try:
            result = generate_fn(case["message"], None)
            suggestions = result.get("suggestions", [])
            tone = result.get("tone", "")

            # Check minimum suggestions
            if len(suggestions) < case.get("min_suggestions", 0):
                case_result["failures"].append(
                    f"Expected ≥{case['min_suggestions']} suggestions, got {len(suggestions)}"
                )

            # Check tone detection
            if case.get("expected_tone") and tone != case["expected_tone"]:
                # Tone mismatch is a soft failure (warning, not fail)
                case_result["warnings"] = [
                    f"Expected tone '{case['expected_tone']}', got '{tone}'"
                ]

            # Check forbidden content
            for forbidden in case.get("must_not_contain", []):
                for s in suggestions:
                    if forbidden.lower() in s.lower():
                        case_result["failures"].append(
                            f"Suggestion contains forbidden phrase: '{forbidden}'"
                        )

            # Check length limits
            max_len = case.get("max_length_per_suggestion", 500)
            for s in suggestions:
                if len(s) > max_len:
                    case_result["failures"].append(
                        f"Suggestion exceeds {max_len} chars: {len(s)}"
                    )

        except Exception as e:
            if not case.get("expect_fallback"):
                case_result["failures"].append(f"Exception: {str(e)}")

        case_result["passed"] = len(case_result.get("failures", [])) == 0
        if case_result["passed"]:
            passed += 1
        results.append(case_result)

    total = len(EVAL_SET)
    return {
        "pass_rate": round(passed / total, 3) if total else 0,
        "passed": passed,
        "total": total,
        "results": results,
        "timestamp": time.time(),
    }


# ============================================================================
# 2. ONLINE QUALITY METRICS
# ============================================================================
class OnlineMetricsCollector:
    """Tracks real-time AI quality signals from production traffic."""

    def __init__(self):
        self._latencies: List[float] = []
        self._fallback_count = 0
        self._total_count = 0
        self._empty_count = 0

    def record(
        self,
        latency_ms: float,
        fallback_level: str,
        suggestion_count: int,
    ) -> None:
        self._total_count += 1
        self._latencies.append(latency_ms)
        if fallback_level != "L1_live":
            self._fallback_count += 1
        if suggestion_count == 0:
            self._empty_count += 1

        # Keep sliding window of last 1000 measurements
        if len(self._latencies) > 1000:
            self._latencies = self._latencies[-1000:]

    def snapshot(self) -> Dict[str, Any]:
        n = len(self._latencies)
        if n == 0:
            return {"total": 0}

        sorted_l = sorted(self._latencies)
        return {
            "total_requests": self._total_count,
            "p50_ms": sorted_l[n // 2],
            "p95_ms": sorted_l[int(n * 0.95)],
            "p99_ms": sorted_l[int(n * 0.99)],
            "fallback_rate": round(self._fallback_count / max(self._total_count, 1), 4),
            "empty_rate": round(self._empty_count / max(self._total_count, 1), 4),
        }


online_metrics = OnlineMetricsCollector()


# ============================================================================
# 3. SAFETY GUARDRAILS
# ============================================================================
# PII patterns for scrubbing
_PII_PATTERNS = [
    (re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b"), "[PHONE]"),           # Phone numbers
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"), "[EMAIL]"),  # Emails
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[SSN]"),                       # SSN
    (re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"), "[CARD]"), # Credit cards
    (re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"), "[IP]"),      # IP addresses
]

# Toxicity/safety blocklist (in production, use a model like Perspective API)
_BLOCKED_PATTERNS = [
    re.compile(r"\b(kill|murder|suicide|self.?harm)\b", re.IGNORECASE),
    re.compile(r"\b(nude|explicit|nsfw)\b", re.IGNORECASE),
    re.compile(r"\b(password|credit.?card|social.?security)\b", re.IGNORECASE),
]


def scrub_pii(text: str) -> str:
    """Remove PII from text before sending to LLM or storing."""
    for pattern, replacement in _PII_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def check_safety(text: str) -> Tuple[bool, Optional[str]]:
    """Check if text passes safety guardrails.
    
    Returns:
        (is_safe, violation_reason)
    """
    for pattern in _BLOCKED_PATTERNS:
        match = pattern.search(text)
        if match:
            return False, f"Blocked content detected: '{match.group()}'"
    return True, None


def sanitize_ai_output(suggestions: List[str]) -> List[str]:
    """Post-process AI outputs through safety pipeline."""
    safe_suggestions = []
    for s in suggestions:
        # Scrub any PII the model may have leaked
        s = scrub_pii(s)
        # Check safety
        is_safe, reason = check_safety(s)
        if is_safe:
            safe_suggestions.append(s)
        else:
            logger.warning(f"Filtered unsafe suggestion: {reason}")
    return safe_suggestions


# ============================================================================
# 4. COST-AWARE ROUTING
# ============================================================================
# Model tiers: route simple queries to cheaper/faster models
_MODEL_TIERS = {
    "premium": {
        "model": os.environ.get("NVIDIA_MODEL", "meta/llama-3.1-8b-instruct"),
        "max_tokens": 256,
        "temperature": 0.85,
        "cost_per_1k_tokens": 0.012,
    },
    "standard": {
        "model": os.environ.get("NVIDIA_MODEL_STANDARD", "meta/llama-3.1-8b-instruct"),
        "max_tokens": 128,
        "temperature": 0.7,
        "cost_per_1k_tokens": 0.004,
    },
    "economy": {
        "model": os.environ.get("NVIDIA_MODEL_ECONOMY", "meta/llama-3.1-8b-instruct"),
        "max_tokens": 64,
        "temperature": 0.6,
        "cost_per_1k_tokens": 0.001,
    },
}


def select_model_tier(message: str, user_tier: str = "free") -> Dict[str, Any]:
    """Route to appropriate model tier based on query complexity and user subscription.
    
    Routing rules:
      - Premium users always get premium model
      - Short/simple messages → economy tier
      - Complex/multi-turn messages → standard tier
      - Messages requiring high creativity → premium tier
    """
    if user_tier == "premium":
        return _MODEL_TIERS["premium"]

    msg_len = len(message)
    word_count = len(message.split())

    # Simple messages (< 20 words, no questions): economy
    if word_count < 20 and "?" not in message:
        return _MODEL_TIERS["economy"]

    # Medium complexity: standard
    if word_count < 50:
        return _MODEL_TIERS["standard"]

    # Complex messages: premium (even for free users)
    return _MODEL_TIERS["premium"]


def estimate_cost(
    model_tier: Dict[str, Any],
    input_tokens: int,
    output_tokens: int,
) -> float:
    """Estimate API call cost for tracking/attribution."""
    total_tokens = input_tokens + output_tokens
    return (total_tokens / 1000) * model_tier["cost_per_1k_tokens"]

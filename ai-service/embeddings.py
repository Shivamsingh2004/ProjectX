"""
User Embedding System: Deep Personalization via Semantic Intelligence.

Generates dense vector embeddings from user behavior, preferences, and
interaction history. Used for:
  1. Semantic similarity matching (find similar users)
  2. AI prompt personalization (inject user "personality" into LLM context)
  3. Content recommendation ranking
  4. Anomaly detection on behavior change

Architecture:
  - Embedding model: sentence-transformers (384-dim vectors)
  - Storage: Redis with vector similarity search (HNSW index)
  - Update trigger: Kafka events → real-time recomputation
"""

import hashlib
import json
import logging
import math
import time
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("ai_service")

# Embedding dimension (sentence-transformers/all-MiniLM-L6-v2)
EMBED_DIM = 384


class UserEmbeddingEngine:
    """Computes and manages user behavior embeddings."""

    # Feature weights for embedding composition
    FEATURE_WEIGHTS = {
        "tone_preference": 0.25,
        "response_style": 0.20,
        "engagement_pattern": 0.20,
        "temporal_pattern": 0.15,
        "platform_affinity": 0.10,
        "conversation_depth": 0.10,
    }

    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}

    def compute_behavior_embedding(
        self,
        user_id: str,
        interaction_history: List[Dict[str, Any]],
    ) -> List[float]:
        """Compute a dense embedding from user behavior signals.

        This uses a handcrafted feature extraction pipeline. In production,
        replace with a learned embedding model fine-tuned on interaction data.
        """
        if not interaction_history:
            return self._default_embedding()

        features = self._extract_features(interaction_history)
        embedding = self._features_to_vector(features)
        
        # Normalize to unit vector
        norm = math.sqrt(sum(x * x for x in embedding))
        if norm > 0:
            embedding = [x / norm for x in embedding]

        # Cache with metadata
        self._cache[user_id] = {
            "embedding": embedding,
            "features": features,
            "computed_at": time.time(),
            "interaction_count": len(interaction_history),
        }

        return embedding

    def get_personality_context(self, user_id: str) -> str:
        """Generate a natural language personality summary for LLM injection."""
        cached = self._cache.get(user_id)
        if not cached:
            return ""

        features = cached["features"]
        parts = []

        tone = features.get("dominant_tone", "casual")
        parts.append(f"User prefers {tone} conversation tone.")

        avg_len = features.get("avg_message_length", 80)
        if avg_len < 50:
            parts.append("User likes short, concise replies.")
        elif avg_len > 150:
            parts.append("User appreciates detailed, thoughtful responses.")
        else:
            parts.append("User prefers medium-length responses.")

        engagement = features.get("engagement_score", 0.5)
        if engagement > 0.7:
            parts.append("User is highly engaged — be creative and personalized.")
        elif engagement < 0.3:
            parts.append("User engagement is low — keep responses simple and direct.")

        emoji_rate = features.get("emoji_usage_rate", 0.0)
        if emoji_rate > 0.3:
            parts.append("User uses emojis frequently — mirror that style.")
        elif emoji_rate < 0.05:
            parts.append("User rarely uses emojis — keep responses emoji-free.")

        peak_hour = features.get("peak_activity_hour", -1)
        if 22 <= peak_hour or peak_hour < 6:
            parts.append("User is most active late at night.")
        elif 6 <= peak_hour < 12:
            parts.append("User is a morning person.")

        return " ".join(parts)

    def cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Compute cosine similarity between two embeddings."""
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def find_similar_users(
        self,
        target_embedding: List[float],
        top_k: int = 10,
    ) -> List[Tuple[str, float]]:
        """Find most similar users by embedding cosine similarity."""
        scores = []
        for uid, data in self._cache.items():
            sim = self.cosine_similarity(target_embedding, data["embedding"])
            scores.append((uid, sim))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    def detect_behavior_shift(
        self,
        user_id: str,
        new_embedding: List[float],
        threshold: float = 0.3,
    ) -> Optional[Dict[str, Any]]:
        """Detect significant behavior change (e.g., user mood shift)."""
        cached = self._cache.get(user_id)
        if not cached:
            return None

        old_embedding = cached["embedding"]
        similarity = self.cosine_similarity(old_embedding, new_embedding)
        drift = 1 - similarity

        if drift > threshold:
            return {
                "user_id": user_id,
                "drift_score": round(drift, 4),
                "similarity": round(similarity, 4),
                "alert": "SIGNIFICANT_BEHAVIOR_CHANGE",
                "recommendation": "Re-calibrate personalization model",
            }
        return None

    # ── Private: Feature Extraction ─────────────────────────────────────────
    def _extract_features(self, history: List[Dict]) -> Dict[str, Any]:
        total = len(history)
        
        # Tone distribution
        tone_counts: Dict[str, int] = {}
        for e in history:
            t = e.get("tone", "casual")
            tone_counts[t] = tone_counts.get(t, 0) + 1
        dominant_tone = max(tone_counts, key=tone_counts.get) if tone_counts else "casual"

        # Response lengths
        lengths = [len(e.get("text", "")) for e in history if e.get("text")]
        avg_len = sum(lengths) / len(lengths) if lengths else 80

        # Engagement (acceptance/edit rate)
        accepted = sum(1 for e in history if e.get("action") == "accepted")
        edited = sum(1 for e in history if e.get("action") == "edited")
        engagement = (accepted + edited * 0.7) / max(total, 1)

        # Emoji usage
        import re
        emoji_pattern = re.compile(
            "[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF"
            "\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]+",
            flags=re.UNICODE,
        )
        texts_with_emoji = sum(
            1 for e in history
            if e.get("text") and emoji_pattern.search(e["text"])
        )
        emoji_rate = texts_with_emoji / max(total, 1)

        # Temporal patterns
        timestamps = [e.get("timestamp", 0) for e in history if e.get("timestamp")]
        hours = [int((t % 86400) / 3600) for t in timestamps] if timestamps else []
        peak_hour = max(set(hours), key=hours.count) if hours else -1

        return {
            "dominant_tone": dominant_tone,
            "tone_distribution": tone_counts,
            "avg_message_length": round(avg_len, 1),
            "engagement_score": round(engagement, 3),
            "emoji_usage_rate": round(emoji_rate, 3),
            "peak_activity_hour": peak_hour,
            "total_interactions": total,
        }

    def _features_to_vector(self, features: Dict[str, Any]) -> List[float]:
        """Convert feature dict to dense vector (simplified; real version
        uses a trained encoder)."""
        vector = [0.0] * EMBED_DIM

        # Encode tone as one-hot in first 4 dims
        tone_map = {"casual": 0, "funny": 1, "flirty": 2, "serious": 3}
        tone_idx = tone_map.get(features.get("dominant_tone", "casual"), 0)
        vector[tone_idx] = 1.0

        # Encode numeric features
        vector[4] = features.get("avg_message_length", 80) / 300  # Normalize
        vector[5] = features.get("engagement_score", 0.5)
        vector[6] = features.get("emoji_usage_rate", 0.0)
        vector[7] = features.get("peak_activity_hour", 12) / 24
        vector[8] = min(features.get("total_interactions", 0) / 100, 1.0)

        # Distribute tone proportions
        dist = features.get("tone_distribution", {})
        total = sum(dist.values()) or 1
        for i, tone in enumerate(["casual", "funny", "flirty", "serious"]):
            vector[10 + i] = dist.get(tone, 0) / total

        return vector

    def _default_embedding(self) -> List[float]:
        """Neutral embedding for new users."""
        v = [0.0] * EMBED_DIM
        v[0] = 0.25  # casual
        v[4] = 0.27  # ~80 char messages
        v[5] = 0.5   # neutral engagement
        return v


# Module singleton
embedding_engine = UserEmbeddingEngine()

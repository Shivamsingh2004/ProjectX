"""
Real-Time Stream Processing: Live Feature Updates via Kafka Streams.

Processes event streams in real-time to compute:
  1. Live user activity features (for AI personalization)
  2. Platform health signals (for autonomous scaling)
  3. Trending conversation topics (for content recommendations)
  4. Windowed aggregations (5min/1hr/24hr sliding windows)

Architecture:
  Kafka Topics → Stream Processor → Feature Store (Redis) → AI Service
"""

import json
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("platform")


@dataclass
class WindowedCounter:
    """Sliding window counter with configurable granularity."""
    window_seconds: int
    _buckets: Dict[int, float] = field(default_factory=dict)
    
    def add(self, value: float = 1.0) -> None:
        bucket = int(time.time())
        self._buckets[bucket] = self._buckets.get(bucket, 0) + value
        self._evict()
    
    def sum(self) -> float:
        self._evict()
        return sum(self._buckets.values())
    
    def count(self) -> int:
        self._evict()
        return len(self._buckets)
    
    def rate(self) -> float:
        """Events per second over the window."""
        total = self.sum()
        return total / self.window_seconds if self.window_seconds > 0 else 0
    
    def _evict(self) -> None:
        cutoff = int(time.time()) - self.window_seconds
        self._buckets = {k: v for k, v in self._buckets.items() if k > cutoff}


@dataclass
class UserActivityState:
    """Real-time state for a single user, updated by stream events."""
    user_id: str
    messages_5min: WindowedCounter = field(default_factory=lambda: WindowedCounter(300))
    messages_1hr: WindowedCounter = field(default_factory=lambda: WindowedCounter(3600))
    ai_requests_5min: WindowedCounter = field(default_factory=lambda: WindowedCounter(300))
    suggestions_accepted: WindowedCounter = field(default_factory=lambda: WindowedCounter(3600))
    suggestions_rejected: WindowedCounter = field(default_factory=lambda: WindowedCounter(3600))
    last_active_at: float = 0.0
    session_count_today: int = 0
    platforms_active: set = field(default_factory=set)
    
    def to_features(self) -> Dict[str, Any]:
        accepted = self.suggestions_accepted.sum()
        rejected = self.suggestions_rejected.sum()
        total = accepted + rejected
        
        return {
            "user_id": self.user_id,
            "messages_5min": self.messages_5min.sum(),
            "messages_1hr": self.messages_1hr.sum(),
            "message_rate_per_min": round(self.messages_5min.rate() * 60, 2),
            "ai_request_rate": round(self.ai_requests_5min.rate() * 60, 2),
            "live_acceptance_rate": round(accepted / total, 3) if total > 0 else 0.5,
            "is_active": (time.time() - self.last_active_at) < 300,
            "session_count_today": self.session_count_today,
            "platforms_active": list(self.platforms_active),
            "computed_at": time.time(),
        }


class StreamProcessor:
    """Processes Kafka events to compute real-time features."""
    
    def __init__(self):
        self._user_states: Dict[str, UserActivityState] = {}
        self._topic_counts: Dict[str, WindowedCounter] = defaultdict(
            lambda: WindowedCounter(3600)
        )
        self._global_metrics = {
            "events_processed": 0,
            "events_per_second": WindowedCounter(60),
            "errors": WindowedCounter(300),
        }
    
    def get_user_state(self, user_id: str) -> UserActivityState:
        if user_id not in self._user_states:
            self._user_states[user_id] = UserActivityState(user_id=user_id)
        return self._user_states[user_id]
    
    def process_event(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process a single event from Kafka.
        
        Returns updated user features (for writing to feature store).
        """
        try:
            event_type = event.get("event_type", "")
            user_id = event.get("user_id", "")
            
            if not user_id:
                return None
            
            state = self.get_user_state(user_id)
            state.last_active_at = time.time()
            
            # Route by event type
            if event_type == "MESSAGE_SENT":
                state.messages_5min.add()
                state.messages_1hr.add()
                platform = event.get("platform")
                if platform:
                    state.platforms_active.add(platform)
            
            elif event_type == "MESSAGE_RECEIVED":
                state.messages_5min.add()
                state.messages_1hr.add()
            
            elif event_type == "AI_SUGGESTION_SHOWN":
                state.ai_requests_5min.add()
            
            elif event_type == "AI_SUGGESTION_ACCEPTED":
                state.suggestions_accepted.add()
            
            elif event_type == "AI_SUGGESTION_REJECTED":
                state.suggestions_rejected.add()
            
            elif event_type == "PLATFORM_CONNECTED":
                platform = event.get("platform")
                if platform:
                    state.platforms_active.add(platform)
            
            # Track topic trends
            metadata = event.get("metadata", {})
            if isinstance(metadata, dict):
                topic = metadata.get("topic")
                if topic:
                    self._topic_counts[topic].add()
            
            # Update global metrics
            self._global_metrics["events_processed"] += 1
            self._global_metrics["events_per_second"].add()
            
            return state.to_features()
        
        except Exception as e:
            self._global_metrics["errors"].add()
            logger.error(f"Stream processing error: {e}")
            return None
    
    def get_trending_topics(self, top_k: int = 10) -> List[Dict[str, Any]]:
        """Get trending conversation topics from the last hour."""
        topics = [
            {"topic": name, "count": int(counter.sum()), "rate_per_min": round(counter.rate() * 60, 2)}
            for name, counter in self._topic_counts.items()
        ]
        topics.sort(key=lambda x: x["count"], reverse=True)
        return topics[:top_k]
    
    def get_active_users(self, since_seconds: int = 300) -> List[str]:
        """Get users active in the last N seconds."""
        cutoff = time.time() - since_seconds
        return [
            uid for uid, state in self._user_states.items()
            if state.last_active_at > cutoff
        ]
    
    def get_processing_stats(self) -> Dict[str, Any]:
        return {
            "total_events_processed": self._global_metrics["events_processed"],
            "events_per_second": round(self._global_metrics["events_per_second"].rate(), 2),
            "error_rate_5min": round(self._global_metrics["errors"].rate() * 60, 2),
            "active_users": len(self.get_active_users()),
            "total_user_states": len(self._user_states),
        }


# Module singleton
stream_processor = StreamProcessor()

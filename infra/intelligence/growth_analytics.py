"""
Business Intelligence: Product Growth Analytics System.

Computes growth metrics, cohort analysis, and funnel tracking for
product teams. Powers data-driven decisions without manual SQL.

Key metrics:
  1. DAU/WAU/MAU and stickiness ratios
  2. Funnel: Signup → Connect Platform → First Message → AI Usage → Match
  3. Cohort retention curves
  4. Feature adoption rates
  5. Revenue attribution (which features drive conversions)
"""

import json
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("platform")


@dataclass
class UserCohort:
    """Users grouped by signup week."""
    cohort_week: str  # e.g., "2026-W12"
    user_ids: Set[str] = field(default_factory=set)
    
    def size(self) -> int:
        return len(self.user_ids)


class GrowthAnalytics:
    """Real-time product growth analytics engine."""
    
    def __init__(self):
        # Active user tracking (sliding windows)
        self._daily_active: Dict[str, Set[str]] = defaultdict(set)  # date → user_ids
        self._weekly_active: Dict[str, Set[str]] = defaultdict(set)  # iso_week → user_ids
        self._monthly_active: Dict[str, Set[str]] = defaultdict(set)  # month → user_ids
        
        # Funnel tracking
        self._funnel_stages: Dict[str, Dict[str, float]] = {}  # user_id → {stage: timestamp}
        
        # Cohort tracking
        self._cohorts: Dict[str, UserCohort] = {}  # week → cohort
        
        # Feature adoption
        self._feature_usage: Dict[str, Set[str]] = defaultdict(set)  # feature → user_ids
        
        # Event log for analytics
        self._events: List[Dict[str, Any]] = []
    
    def track_event(self, user_id: str, event_type: str, properties: Optional[Dict] = None) -> None:
        """Track a user event for analytics."""
        now = time.time()
        dt = datetime.utcfromtimestamp(now)
        
        # Update active user sets
        day_key = dt.strftime("%Y-%m-%d")
        week_key = dt.strftime("%Y-W%W")
        month_key = dt.strftime("%Y-%m")
        
        self._daily_active[day_key].add(user_id)
        self._weekly_active[week_key].add(user_id)
        self._monthly_active[month_key].add(user_id)
        
        # Track funnel progression
        funnel_map = {
            "USER_SIGNED_UP": "signup",
            "PLATFORM_CONNECTED": "connect_platform",
            "MESSAGE_SENT": "first_message",
            "AI_SUGGESTION_SHOWN": "ai_usage",
            "MATCH_CREATED": "match",
        }
        stage = funnel_map.get(event_type)
        if stage:
            if user_id not in self._funnel_stages:
                self._funnel_stages[user_id] = {}
            if stage not in self._funnel_stages[user_id]:
                self._funnel_stages[user_id][stage] = now
        
        # Track feature adoption
        feature_map = {
            "AI_SUGGESTION_SHOWN": "ai_replies",
            "AI_SUGGESTION_ACCEPTED": "ai_replies",
            "PLATFORM_CONNECTED": "multi_platform",
        }
        feature = feature_map.get(event_type)
        if feature:
            self._feature_usage[feature].add(user_id)
        
        # Store event
        self._events.append({
            "user_id": user_id,
            "event_type": event_type,
            "timestamp": now,
            "properties": properties or {},
        })
        
        # Prune old events (keep last 100K)
        if len(self._events) > 100_000:
            self._events = self._events[-100_000:]
    
    def register_user(self, user_id: str) -> None:
        """Register user in their signup cohort."""
        dt = datetime.utcnow()
        week_key = dt.strftime("%Y-W%W")
        if week_key not in self._cohorts:
            self._cohorts[week_key] = UserCohort(cohort_week=week_key)
        self._cohorts[week_key].user_ids.add(user_id)
        
        self.track_event(user_id, "USER_SIGNED_UP")
    
    # ── Core Metrics ────────────────────────────────────────────────────────
    def get_active_users(self) -> Dict[str, Any]:
        dt = datetime.utcnow()
        day_key = dt.strftime("%Y-%m-%d")
        week_key = dt.strftime("%Y-W%W")
        month_key = dt.strftime("%Y-%m")
        
        dau = len(self._daily_active.get(day_key, set()))
        wau = len(self._weekly_active.get(week_key, set()))
        mau = len(self._monthly_active.get(month_key, set()))
        
        return {
            "dau": dau,
            "wau": wau,
            "mau": mau,
            "dau_wau_ratio": round(dau / max(wau, 1), 3),  # Stickiness
            "dau_mau_ratio": round(dau / max(mau, 1), 3),
            "date": day_key,
        }
    
    def get_funnel(self) -> Dict[str, Any]:
        """Get conversion funnel metrics."""
        stages = ["signup", "connect_platform", "first_message", "ai_usage", "match"]
        counts = {}
        
        for stage in stages:
            counts[stage] = sum(
                1 for user_stages in self._funnel_stages.values()
                if stage in user_stages
            )
        
        total_signups = max(counts.get("signup", 0), 1)
        funnel = []
        for i, stage in enumerate(stages):
            count = counts.get(stage, 0)
            funnel.append({
                "stage": stage,
                "users": count,
                "conversion_from_signup": round(count / total_signups, 3),
                "conversion_from_previous": round(
                    count / max(counts.get(stages[i-1], 0), 1), 3
                ) if i > 0 else 1.0,
            })
        
        return {"stages": funnel, "total_users": total_signups}
    
    def get_cohort_retention(self, weeks_back: int = 8) -> List[Dict[str, Any]]:
        """Compute weekly cohort retention curves."""
        retention = []
        
        sorted_cohorts = sorted(self._cohorts.keys())[-weeks_back:]
        
        for cohort_week in sorted_cohorts:
            cohort = self._cohorts[cohort_week]
            cohort_size = cohort.size()
            if cohort_size == 0:
                continue
            
            week_retention = {"cohort": cohort_week, "size": cohort_size, "weeks": {}}
            
            # Check retention for each subsequent week
            for offset in range(8):
                # Parse the week and add offset
                try:
                    base_year = int(cohort_week.split("-W")[0])
                    base_week = int(cohort_week.split("-W")[1])
                    target_week_num = base_week + offset
                    target_key = f"{base_year}-W{target_week_num:02d}"
                except (ValueError, IndexError):
                    continue
                
                active_in_week = self._weekly_active.get(target_key, set())
                retained = cohort.user_ids & active_in_week
                rate = len(retained) / cohort_size
                
                week_retention["weeks"][f"week_{offset}"] = round(rate, 3)
            
            retention.append(week_retention)
        
        return retention
    
    def get_feature_adoption(self) -> List[Dict[str, Any]]:
        """Get feature adoption rates."""
        total_users = len(self._funnel_stages)
        
        return [
            {
                "feature": feature,
                "users": len(user_ids),
                "adoption_rate": round(len(user_ids) / max(total_users, 1), 3),
            }
            for feature, user_ids in sorted(
                self._feature_usage.items(),
                key=lambda x: len(x[1]),
                reverse=True,
            )
        ]
    
    def get_dashboard(self) -> Dict[str, Any]:
        """Full BI dashboard snapshot."""
        return {
            "active_users": self.get_active_users(),
            "funnel": self.get_funnel(),
            "feature_adoption": self.get_feature_adoption(),
            "total_events_tracked": len(self._events),
            "total_cohorts": len(self._cohorts),
            "generated_at": time.time(),
        }


# Module singleton
growth_analytics = GrowthAnalytics()

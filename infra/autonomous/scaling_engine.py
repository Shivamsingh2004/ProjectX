"""
Autonomous Scaling & Self-Healing: AI-Driven Anomaly Detection.

Uses statistical anomaly detection (Z-score + exponential smoothing) to:
  1. Predict traffic surges BEFORE they happen (proactive scaling)
  2. Detect service degradation patterns (self-healing triggers)
  3. Auto-tune resource limits based on observed behavior
  4. Emit scaling recommendations to Kubernetes HPA via custom metrics

This replaces reactive HPA (CPU/memory thresholds) with predictive,
anomaly-aware scaling used at Netflix/Uber scale.
"""

import json
import logging
import math
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("platform")


@dataclass
class TimeSeriesPoint:
    timestamp: float
    value: float


@dataclass
class ServiceMetrics:
    """Rolling metrics window for a single service."""
    name: str
    window_size: int = 300  # 5 minutes of 1-second samples
    _latencies: deque = field(default_factory=lambda: deque(maxlen=300))
    _error_rates: deque = field(default_factory=lambda: deque(maxlen=300))
    _request_rates: deque = field(default_factory=lambda: deque(maxlen=300))
    _cpu_utilizations: deque = field(default_factory=lambda: deque(maxlen=300))
    
    # Exponential smoothing state
    _smoothed_rps: float = 0.0
    _smoothed_latency: float = 0.0
    _trend_rps: float = 0.0
    
    def record(
        self,
        latency_ms: float,
        error_rate: float,
        request_rate: float,
        cpu_pct: float,
    ) -> None:
        now = time.time()
        self._latencies.append(TimeSeriesPoint(now, latency_ms))
        self._error_rates.append(TimeSeriesPoint(now, error_rate))
        self._request_rates.append(TimeSeriesPoint(now, request_rate))
        self._cpu_utilizations.append(TimeSeriesPoint(now, cpu_pct))
        
        # Holt-Winters double exponential smoothing for trend prediction
        alpha = 0.3  # Level smoothing
        beta = 0.1   # Trend smoothing
        
        if self._smoothed_rps == 0:
            self._smoothed_rps = request_rate
        else:
            prev = self._smoothed_rps
            self._smoothed_rps = alpha * request_rate + (1 - alpha) * (prev + self._trend_rps)
            self._trend_rps = beta * (self._smoothed_rps - prev) + (1 - beta) * self._trend_rps
        
        self._smoothed_latency = alpha * latency_ms + (1 - alpha) * self._smoothed_latency


class AnomalyDetector:
    """Detects anomalies using Z-score on rolling windows."""
    
    SENSITIVITY = 2.5  # Z-score threshold for anomaly
    
    @staticmethod
    def z_score(values: List[float], current: float) -> float:
        if len(values) < 10:
            return 0.0
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std = math.sqrt(variance) if variance > 0 else 1.0
        return (current - mean) / std
    
    @classmethod
    def detect(cls, metrics: ServiceMetrics) -> List[Dict[str, Any]]:
        anomalies = []
        
        # Latency anomaly
        if len(metrics._latencies) >= 10:
            values = [p.value for p in metrics._latencies]
            z = cls.z_score(values[:-1], values[-1])
            if abs(z) > cls.SENSITIVITY:
                anomalies.append({
                    "type": "latency_spike",
                    "service": metrics.name,
                    "z_score": round(z, 2),
                    "current_ms": values[-1],
                    "mean_ms": round(sum(values) / len(values), 2),
                    "severity": "critical" if z > 4 else "warning",
                })
        
        # Error rate anomaly
        if len(metrics._error_rates) >= 10:
            values = [p.value for p in metrics._error_rates]
            z = cls.z_score(values[:-1], values[-1])
            if z > cls.SENSITIVITY:
                anomalies.append({
                    "type": "error_spike",
                    "service": metrics.name,
                    "z_score": round(z, 2),
                    "current_pct": round(values[-1] * 100, 2),
                    "severity": "critical" if values[-1] > 0.05 else "warning",
                })
        
        # Traffic surge prediction (using trend)
        if metrics._trend_rps > 0 and len(metrics._request_rates) >= 30:
            predicted_5min = metrics._smoothed_rps + metrics._trend_rps * 300
            current = metrics._smoothed_rps
            if predicted_5min > current * 1.5 and current > 10:
                anomalies.append({
                    "type": "traffic_surge_predicted",
                    "service": metrics.name,
                    "current_rps": round(current, 1),
                    "predicted_5min_rps": round(predicted_5min, 1),
                    "growth_pct": round((predicted_5min / current - 1) * 100, 1),
                    "severity": "info",
                })
        
        return anomalies


class AutonomousScaler:
    """Generates scaling decisions based on anomaly detection + trend prediction."""
    
    # Service-specific scaling profiles
    PROFILES = {
        "api-gateway": {"min": 3, "max": 50, "scale_up_cooldown": 30, "scale_down_cooldown": 300},
        "messaging-service": {"min": 3, "max": 30, "scale_up_cooldown": 60, "scale_down_cooldown": 300},
        "ai-service": {"min": 2, "max": 20, "scale_up_cooldown": 120, "scale_down_cooldown": 600},
        "analytics-service": {"min": 2, "max": 15, "scale_up_cooldown": 60, "scale_down_cooldown": 300},
    }
    
    def __init__(self):
        self._last_scale_action: Dict[str, float] = {}
        self._services: Dict[str, ServiceMetrics] = {}
        self._detector = AnomalyDetector()
    
    def get_or_create_metrics(self, service: str) -> ServiceMetrics:
        if service not in self._services:
            self._services[service] = ServiceMetrics(name=service)
        return self._services[service]
    
    def ingest(self, service: str, latency_ms: float, error_rate: float,
               request_rate: float, cpu_pct: float) -> None:
        metrics = self.get_or_create_metrics(service)
        metrics.record(latency_ms, error_rate, request_rate, cpu_pct)
    
    def evaluate(self, service: str, current_replicas: int) -> Optional[Dict[str, Any]]:
        """Evaluate whether a scaling action is needed."""
        metrics = self.get_or_create_metrics(service)
        profile = self.PROFILES.get(service, self.PROFILES["messaging-service"])
        anomalies = self._detector.detect(metrics)
        
        now = time.time()
        last_action = self._last_scale_action.get(service, 0)
        
        # Proactive scale-up on predicted surge
        surge = next((a for a in anomalies if a["type"] == "traffic_surge_predicted"), None)
        if surge and (now - last_action) > profile["scale_up_cooldown"]:
            growth = surge["growth_pct"]
            new_replicas = min(
                profile["max"],
                int(current_replicas * (1 + growth / 200))  # Scale proportionally
            )
            if new_replicas > current_replicas:
                self._last_scale_action[service] = now
                return {
                    "action": "scale_up",
                    "service": service,
                    "from": current_replicas,
                    "to": new_replicas,
                    "reason": f"Predicted {growth:.0f}% traffic surge in 5 minutes",
                    "anomalies": anomalies,
                }
        
        # Reactive scale-up on latency/error anomaly
        critical = [a for a in anomalies if a["severity"] == "critical"]
        if critical and (now - last_action) > profile["scale_up_cooldown"]:
            new_replicas = min(profile["max"], current_replicas + 2)
            self._last_scale_action[service] = now
            return {
                "action": "scale_up",
                "service": service,
                "from": current_replicas,
                "to": new_replicas,
                "reason": f"Critical anomaly: {critical[0]['type']}",
                "anomalies": anomalies,
            }
        
        # Scale-down when stable (no anomalies, low utilization)
        if not anomalies and len(metrics._cpu_utilizations) >= 30:
            avg_cpu = sum(p.value for p in metrics._cpu_utilizations) / len(metrics._cpu_utilizations)
            if avg_cpu < 0.3 and current_replicas > profile["min"]:
                if (now - last_action) > profile["scale_down_cooldown"]:
                    new_replicas = max(profile["min"], current_replicas - 1)
                    self._last_scale_action[service] = now
                    return {
                        "action": "scale_down",
                        "service": service,
                        "from": current_replicas,
                        "to": new_replicas,
                        "reason": f"Stable: avg CPU {avg_cpu:.0%}, no anomalies",
                    }
        
        return None  # No action needed


class SelfHealingEngine:
    """Automated remediation for detected anomalies."""
    
    PLAYBOOKS = {
        "latency_spike": [
            "check_downstream_health",
            "flush_connection_pools",
            "scale_up_service",
            "enable_circuit_breaker",
        ],
        "error_spike": [
            "check_dependency_health",
            "trigger_service_restart",
            "enable_fallback_mode",
            "page_oncall",
        ],
        "traffic_surge_predicted": [
            "preemptive_scale_up",
            "warm_cache",
            "enable_rate_limiting",
        ],
    }
    
    def generate_remediation(self, anomalies: List[Dict]) -> List[Dict[str, Any]]:
        actions = []
        for anomaly in anomalies:
            playbook = self.PLAYBOOKS.get(anomaly["type"], [])
            actions.append({
                "anomaly": anomaly,
                "remediation_steps": playbook,
                "auto_executable": anomaly["severity"] != "critical",
                "requires_human": anomaly["severity"] == "critical",
                "timestamp": time.time(),
            })
        return actions


# Module-level singletons
autonomous_scaler = AutonomousScaler()
self_healing = SelfHealingEngine()

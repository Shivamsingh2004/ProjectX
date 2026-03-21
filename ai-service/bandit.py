"""
Multi-Armed Bandit: Continuous Experimentation Engine.

Replaces static A/B testing with adaptive, reward-optimizing experimentation
using Thompson Sampling (Bayesian bandit). Key advantages:
  - Automatically allocates MORE traffic to winning variants
  - Minimizes regret (opportunity cost of showing bad variants)
  - Converges faster than A/B tests with fixed traffic splits
  - Handles multiple concurrent experiments with isolation

Used for: prompt templates, model selection, tone strategies, UI variants.
"""

import json
import logging
import math
import random
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ai_service")


@dataclass
class Arm:
    """A single variant in a bandit experiment."""
    name: str
    alpha: float = 1.0   # Beta distribution: successes + 1
    beta_param: float = 1.0    # Beta distribution: failures + 1
    total_pulls: int = 0
    total_reward: float = 0.0
    
    @property
    def mean_reward(self) -> float:
        if self.total_pulls == 0:
            return 0.0
        return self.total_reward / self.total_pulls
    
    @property
    def confidence_interval(self) -> tuple:
        """95% credible interval from Beta posterior."""
        # Approximate using normal for large counts
        n = self.total_pulls
        if n < 2:
            return (0.0, 1.0)
        p = self.mean_reward
        se = math.sqrt(p * (1 - p) / n)
        return (max(0, p - 1.96 * se), min(1, p + 1.96 * se))


@dataclass
class Experiment:
    """A bandit experiment with multiple arms."""
    name: str
    arms: List[Arm] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    min_samples_per_arm: int = 100
    
    @property
    def is_mature(self) -> bool:
        """Has enough data for statistical significance."""
        return all(a.total_pulls >= self.min_samples_per_arm for a in self.arms)
    
    @property
    def winner(self) -> Optional[Arm]:
        """Declare winner if one arm's lower CI bound exceeds others' upper bounds."""
        if not self.is_mature:
            return None
        for arm in self.arms:
            lower = arm.confidence_interval[0]
            if all(
                lower > other.confidence_interval[1]
                for other in self.arms if other.name != arm.name
            ):
                return arm
        return None


class BanditEngine:
    """Thompson Sampling bandit engine for continuous experimentation."""
    
    def __init__(self):
        self._experiments: Dict[str, Experiment] = {}
        self._setup_default_experiments()
    
    def _setup_default_experiments(self):
        """Pre-configure the standard experiments."""
        # Prompt template experiment
        self.create_experiment("prompt_strategy", [
            "baseline_v1",
            "personality_aware_v2",
            "context_heavy_v3",
            "concise_v4",
        ])
        
        # Temperature experiment
        self.create_experiment("temperature", [
            "temp_0.7_conservative",
            "temp_0.85_balanced",
            "temp_0.95_creative",
        ])
        
        # Response length experiment
        self.create_experiment("response_length", [
            "short_50_chars",
            "medium_100_chars",
            "long_200_chars",
        ])
    
    def create_experiment(self, name: str, arm_names: List[str]) -> Experiment:
        exp = Experiment(
            name=name,
            arms=[Arm(name=n) for n in arm_names],
        )
        self._experiments[name] = exp
        return exp
    
    def select_arm(self, experiment_name: str, user_id: Optional[str] = None) -> str:
        """Thompson Sampling: sample from each arm's Beta posterior, pick highest."""
        exp = self._experiments.get(experiment_name)
        if not exp:
            return "default"
        
        # Sample from Beta(alpha, beta) for each arm
        samples = []
        for arm in exp.arms:
            sample = random.betavariate(arm.alpha, arm.beta_param)
            samples.append((sample, arm))
        
        # Select arm with highest sample
        samples.sort(key=lambda x: x[0], reverse=True)
        selected = samples[0][1]
        
        logger.debug(
            f"Bandit selected '{selected.name}' for experiment '{experiment_name}' "
            f"(mean={selected.mean_reward:.3f}, pulls={selected.total_pulls})"
        )
        return selected.name
    
    def record_reward(self, experiment_name: str, arm_name: str, reward: float) -> None:
        """Record outcome (reward ∈ [0, 1]) for selected arm.
        
        For AI suggestions:
          - reward=1.0 if user accepted suggestion
          - reward=0.7 if user edited suggestion
          - reward=0.0 if user rejected suggestion
        """
        exp = self._experiments.get(experiment_name)
        if not exp:
            return
        
        arm = next((a for a in exp.arms if a.name == arm_name), None)
        if not arm:
            return
        
        arm.total_pulls += 1
        arm.total_reward += reward
        
        # Update Beta posterior
        if reward > 0.5:
            arm.alpha += 1
        else:
            arm.beta_param += 1
    
    def get_experiment_status(self, experiment_name: str) -> Dict[str, Any]:
        exp = self._experiments.get(experiment_name)
        if not exp:
            return {"error": "Experiment not found"}
        
        winner = exp.winner
        return {
            "name": exp.name,
            "is_mature": exp.is_mature,
            "winner": winner.name if winner else None,
            "arms": [
                {
                    "name": a.name,
                    "pulls": a.total_pulls,
                    "mean_reward": round(a.mean_reward, 4),
                    "ci_lower": round(a.confidence_interval[0], 4),
                    "ci_upper": round(a.confidence_interval[1], 4),
                    "traffic_share": round(a.total_pulls / max(sum(x.total_pulls for x in exp.arms), 1), 3),
                }
                for a in exp.arms
            ],
        }
    
    def get_all_experiments(self) -> List[Dict[str, Any]]:
        return [self.get_experiment_status(name) for name in self._experiments]


# Module singleton
bandit_engine = BanditEngine()

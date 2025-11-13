"""
Configuration for FSA-0.1 MLA Task Deconstructor

This module contains configuration constants and weights for the MLA framework.
"""

from typing import Dict


class MLAConfig:
    """Configuration for MLA framework calculations"""

    # Cost component weights (must sum to 1.0)
    COST_WEIGHTS: Dict[str, float] = {
        "time": 0.5,           # Weight for time cost
        "cognitive": 0.3,      # Weight for cognitive load
        "resources": 0.2,      # Weight for resource cost
    }

    # Impact component weights (must sum to 1.0)
    IMPACT_WEIGHTS: Dict[str, float] = {
        "progress": 0.6,       # Weight for immediate progress toward goal
        "efficiency": 0.4,     # Weight for future efficiency gains (compound effect)
    }

    # Cognitive load levels (normalized 0-100)
    COGNITIVE_LOAD_LEVELS: Dict[str, float] = {
        "trivial": 10.0,
        "low": 25.0,
        "medium": 50.0,
        "high": 75.0,
        "very_high": 90.0,
    }

    # LQ_MLA normalization parameters
    LQ_NORMALIZATION_MAX: float = 100.0  # Maximum normalized score
    LQ_NORMALIZATION_MIN: float = 0.0    # Minimum normalized score

    # Goal confidence thresholds
    GOAL_CONFIDENCE_HIGH: float = 0.85
    GOAL_CONFIDENCE_MEDIUM: float = 0.60
    GOAL_CONFIDENCE_LOW: float = 0.40

    # Task decomposition parameters
    MAX_DECOMPOSITION_DEPTH: int = 5     # Maximum recursive depth for task breakdown
    MIN_TASK_GRANULARITY: int = 5        # Minimum time (minutes) for atomic task

    # Context elicitation
    MAX_CLARIFYING_QUESTIONS: int = 5

    # Default values for missing parameters
    DEFAULT_TIME_ESTIMATE: float = 30.0  # minutes
    DEFAULT_COGNITIVE_LOAD: str = "medium"
    DEFAULT_RESOURCE_COST: float = 20.0  # normalized 0-100


# Global configuration instance
config = MLAConfig()

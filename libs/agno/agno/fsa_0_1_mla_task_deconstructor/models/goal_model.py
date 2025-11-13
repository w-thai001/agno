"""
Goal Model for MLA Framework

Represents the target objective G and success criteria O_G.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Goal:
    """
    Represents a goal in the MLA framework.

    Attributes:
        G: Primary objective description
        O_G: Success outcome criteria (what does achievement look like?)
        confidence: Confidence level in goal inference (0.0-1.0)
        explicit: Whether goal was explicitly stated or inferred
        context: Additional context about the goal
        constraints: Known constraints on achieving the goal
        success_metrics: Measurable success indicators
    """

    G: str
    O_G: str
    confidence: float = 1.0
    explicit: bool = True
    context: Optional[str] = None
    constraints: List[str] = field(default_factory=list)
    success_metrics: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Validate goal attributes"""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")

        if not self.G:
            raise ValueError("Goal G cannot be empty")

        if not self.O_G:
            raise ValueError("Outcome criteria O_G cannot be empty")

    def to_dict(self) -> dict:
        """Convert goal to dictionary format"""
        return {
            "G": self.G,
            "O_G": self.O_G,
            "confidence": self.confidence,
            "explicit": self.explicit,
            "context": self.context,
            "constraints": self.constraints,
            "success_metrics": self.success_metrics,
        }

    def __str__(self) -> str:
        """Human-readable representation"""
        confidence_pct = int(self.confidence * 100)
        source = "explicit" if self.explicit else "inferred"
        return f"Goal({source}, {confidence_pct}%): {self.G}"

    @classmethod
    def from_dict(cls, data: dict) -> "Goal":
        """Create Goal from dictionary"""
        return cls(
            G=data["G"],
            O_G=data["O_G"],
            confidence=data.get("confidence", 1.0),
            explicit=data.get("explicit", True),
            context=data.get("context"),
            constraints=data.get("constraints", []),
            success_metrics=data.get("success_metrics", []),
        )

    def needs_clarification(self, threshold: float = 0.7) -> bool:
        """
        Determine if goal needs clarification based on confidence.

        Args:
            threshold: Confidence threshold below which clarification is needed

        Returns:
            True if confidence is below threshold
        """
        return self.confidence < threshold

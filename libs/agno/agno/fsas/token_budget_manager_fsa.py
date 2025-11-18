"""
Token Budget Manager FSA - Comprehensive token budget management system.

This module provides a finite state automaton for managing and optimizing token budgets
across AI operations. It includes tracking, prediction, enforcement, and allocation capabilities.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class BudgetState(str, Enum):
    """FSA states for budget management."""

    IDLE = "idle"
    VALIDATING = "validating"
    TRACKING = "tracking"
    PREDICTING = "predicting"
    ALLOCATING = "allocating"
    ENFORCING = "enforcing"
    ANALYZING = "analyzing"
    ERROR = "error"


class AllocationStrategy(str, Enum):
    """Strategies for budget allocation across agents."""

    PROPORTIONAL = "proportional"  # Based on historical usage
    PRIORITY_BASED = "priority_based"  # Based on agent priority levels
    DYNAMIC = "dynamic"  # Adaptive based on current needs
    EQUAL = "equal"  # Equal distribution
    WEIGHTED = "weighted"  # Custom weights per agent


class EnforcementLevel(str, Enum):
    """Budget enforcement levels."""

    SOFT = "soft"  # Warning only
    HARD = "hard"  # Strict blocking
    ADAPTIVE = "adaptive"  # Context-dependent


class Agent(BaseModel):
    """Represents an agent for budget allocation."""

    agent_id: str
    name: str
    priority: int = Field(default=1, ge=1, le=10)
    weight: float = Field(default=1.0, ge=0.0)
    historical_usage: int = Field(default=0, ge=0)
    current_budget: int = Field(default=0, ge=0)


class BudgetRequest(BaseModel):
    """Request for budget validation."""

    operation_id: str = Field(default_factory=lambda: str(uuid4()))
    operation_type: str
    requested_tokens: int = Field(ge=0)
    priority: int = Field(default=5, ge=1, le=10)
    agent_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ValidationResult(BaseModel):
    """Result of budget request validation."""

    is_valid: bool
    approved_tokens: int = Field(ge=0)
    reason: Optional[str] = None
    suggestions: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class BudgetDecision(BaseModel):
    """Decision from the budget management pipeline."""

    operation_id: str
    approved: bool
    allocated_tokens: int = Field(ge=0)
    remaining_budget: int = Field(ge=0)
    predicted_usage: Optional[int] = None
    warnings: List[str] = Field(default_factory=list)
    enforcement_action: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class TokenPrediction(BaseModel):
    """Predicted token usage for an operation."""

    operation_type: str
    predicted_tokens: int = Field(ge=0)
    confidence: float = Field(ge=0.0, le=1.0)
    historical_average: float = Field(ge=0.0)
    variance: float = Field(ge=0.0)
    sample_size: int = Field(ge=0)


class EnforcementAction(BaseModel):
    """Action taken by budget enforcement."""

    action_type: str  # "allow", "warn", "block", "throttle"
    message: str
    current_usage: int = Field(ge=0)
    limit: int = Field(ge=0)
    usage_percentage: float = Field(ge=0.0, le=100.0)
    recommended_action: Optional[str] = None


class UsageAnalytics(BaseModel):
    """Analytics for token usage patterns."""

    time_window: str
    total_tokens_used: int = Field(ge=0)
    num_operations: int = Field(ge=0)
    average_tokens_per_operation: float = Field(ge=0.0)
    peak_usage: int = Field(ge=0)
    peak_timestamp: Optional[datetime] = None
    operation_type_breakdown: Dict[str, int] = Field(default_factory=dict)
    trend: str  # "increasing", "decreasing", "stable"
    efficiency_score: float = Field(ge=0.0, le=100.0)


@dataclass
class OperationRecord:
    """Record of a token consumption operation."""

    operation_id: str
    operation_type: str
    tokens_used: int
    timestamp: datetime
    agent_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class TokenBudgetManagerFSA:
    """
    Finite State Automaton for comprehensive token budget management.

    This FSA manages token budgets across AI operations by tracking consumption,
    predicting usage, enforcing limits, and providing real-time budget allocation
    recommendations.

    Attributes:
        total_budget: Total token budget available
        current_usage: Current token consumption
        soft_limit_percentage: Percentage threshold for soft warnings (0-100)
        hard_limit_percentage: Percentage threshold for hard blocks (0-100)
        enable_prediction: Whether to enable usage prediction
        enable_analytics: Whether to enable historical analytics
    """

    def __init__(
        self,
        total_budget: int = 100000,
        soft_limit_percentage: float = 80.0,
        hard_limit_percentage: float = 95.0,
        enable_prediction: bool = True,
        enable_analytics: bool = True,
        history_window_hours: int = 24,
    ):
        """
        Initialize the Token Budget Manager FSA.

        Args:
            total_budget: Total token budget available
            soft_limit_percentage: Percentage for soft limit warnings
            hard_limit_percentage: Percentage for hard limit enforcement
            enable_prediction: Enable predictive analytics
            enable_analytics: Enable historical analytics
            history_window_hours: Hours to retain in history window
        """
        if total_budget < 0:
            raise ValueError("Total budget must be non-negative")
        if not 0 <= soft_limit_percentage <= 100:
            raise ValueError("Soft limit percentage must be between 0 and 100")
        if not 0 <= hard_limit_percentage <= 100:
            raise ValueError("Hard limit percentage must be between 0 and 100")
        if soft_limit_percentage > hard_limit_percentage:
            raise ValueError("Soft limit must be less than or equal to hard limit")

        self.total_budget = total_budget
        self.current_usage = 0
        self.soft_limit_percentage = soft_limit_percentage
        self.hard_limit_percentage = hard_limit_percentage
        self.enable_prediction = enable_prediction
        self.enable_analytics = enable_analytics
        self.history_window_hours = history_window_hours

        # FSA state
        self.current_state = BudgetState.IDLE
        self.state_history: deque = deque(maxlen=100)

        # Operation tracking
        self.operation_history: deque[OperationRecord] = deque(maxlen=1000)
        self.operation_type_stats: Dict[str, List[int]] = defaultdict(list)
        self.agent_budgets: Dict[str, int] = {}
        self.agent_usage: Dict[str, int] = defaultdict(int)

        # Prediction cache
        self.prediction_cache: Dict[str, TokenPrediction] = {}
        self.cache_ttl_seconds = 300  # 5 minutes
        self.cache_timestamps: Dict[str, datetime] = {}

        # Budget reservations (for pending operations)
        self.reservations: Dict[str, int] = {}

        # Error tracking
        self.error_count = 0
        self.last_error: Optional[str] = None

    def _transition_state(self, new_state: BudgetState) -> None:
        """Transition to a new FSA state."""
        self.state_history.append((self.current_state, datetime.now()))
        self.current_state = new_state

    def _get_available_budget(self) -> int:
        """Get available budget accounting for reservations."""
        reserved_total = sum(self.reservations.values())
        return max(0, self.total_budget - self.current_usage - reserved_total)

    def _cleanup_old_history(self) -> None:
        """Remove operation records older than the history window."""
        if not self.enable_analytics:
            return

        cutoff_time = datetime.now() - timedelta(hours=self.history_window_hours)

        # Remove old operation records
        while self.operation_history and self.operation_history[0].timestamp < cutoff_time:
            old_record = self.operation_history.popleft()

            # Update operation type stats
            if old_record.operation_type in self.operation_type_stats:
                stats = self.operation_type_stats[old_record.operation_type]
                if old_record.tokens_used in stats:
                    stats.remove(old_record.tokens_used)
                if not stats:
                    del self.operation_type_stats[old_record.operation_type]

    def _invalidate_cache(self, operation_type: Optional[str] = None) -> None:
        """Invalidate prediction cache."""
        if operation_type:
            if operation_type in self.prediction_cache:
                del self.prediction_cache[operation_type]
            if operation_type in self.cache_timestamps:
                del self.cache_timestamps[operation_type]
        else:
            self.prediction_cache.clear()
            self.cache_timestamps.clear()

    def _is_cache_valid(self, operation_type: str) -> bool:
        """Check if cached prediction is still valid."""
        if operation_type not in self.cache_timestamps:
            return False

        age = (datetime.now() - self.cache_timestamps[operation_type]).total_seconds()
        return age < self.cache_ttl_seconds

    def execute(self, operation: str, estimated_tokens: int) -> BudgetDecision:
        """
        Main budget management pipeline execution.

        This is the primary method that coordinates all FSA operations including
        validation, prediction, enforcement, and allocation.

        Args:
            operation: Type of operation being requested
            estimated_tokens: Estimated token requirement

        Returns:
            BudgetDecision with approval status and details
        """
        operation_id = str(uuid4())

        try:
            # Create budget request
            request = BudgetRequest(
                operation_id=operation_id,
                operation_type=operation,
                requested_tokens=estimated_tokens,
            )

            # Validate request
            self._transition_state(BudgetState.VALIDATING)
            validation = self.validate(request)

            if not validation.is_valid:
                return BudgetDecision(
                    operation_id=operation_id,
                    approved=False,
                    allocated_tokens=0,
                    remaining_budget=self._get_available_budget(),
                    warnings=validation.warnings + [validation.reason or "Validation failed"],
                )

            # Get prediction if enabled
            predicted_usage = None
            if self.enable_prediction:
                self._transition_state(BudgetState.PREDICTING)
                prediction = self.predict_usage(operation)
                predicted_usage = prediction.predicted_tokens

                # Use prediction if available and higher than estimate
                tokens_to_allocate = max(estimated_tokens, predicted_usage)
            else:
                tokens_to_allocate = estimated_tokens

            # Enforce limits
            self._transition_state(BudgetState.ENFORCING)
            enforcement = self.enforce_limits(
                self.current_usage + tokens_to_allocate,
                self.total_budget
            )

            # Determine approval
            approved = enforcement.action_type in ["allow", "warn"]
            allocated = tokens_to_allocate if approved else 0

            # Reserve budget if approved
            if approved:
                self.reservations[operation_id] = allocated

            self._transition_state(BudgetState.IDLE)

            return BudgetDecision(
                operation_id=operation_id,
                approved=approved,
                allocated_tokens=allocated,
                remaining_budget=self._get_available_budget(),
                predicted_usage=predicted_usage,
                warnings=validation.warnings + ([enforcement.message] if enforcement.action_type == "warn" else []),
                enforcement_action=enforcement.action_type,
            )

        except Exception as e:
            self._transition_state(BudgetState.ERROR)
            self.error_count += 1
            self.last_error = str(e)

            return BudgetDecision(
                operation_id=operation_id,
                approved=False,
                allocated_tokens=0,
                remaining_budget=self._get_available_budget(),
                warnings=[f"Error in budget execution: {str(e)}"],
            )

    def validate(self, budget_request: BudgetRequest) -> ValidationResult:
        """
        Validate a budget request.

        Args:
            budget_request: The budget request to validate

        Returns:
            ValidationResult with validation status and details
        """
        warnings = []
        suggestions = []

        # Check for negative or zero tokens
        if budget_request.requested_tokens <= 0:
            return ValidationResult(
                is_valid=False,
                approved_tokens=0,
                reason="Requested tokens must be positive",
            )

        # Check if request exceeds total budget
        if budget_request.requested_tokens > self.total_budget:
            return ValidationResult(
                is_valid=False,
                approved_tokens=0,
                reason=f"Requested tokens ({budget_request.requested_tokens}) exceed total budget ({self.total_budget})",
                suggestions=["Consider reducing operation scope", "Increase total budget"],
            )

        # Check available budget
        available = self._get_available_budget()
        if budget_request.requested_tokens > available:
            return ValidationResult(
                is_valid=False,
                approved_tokens=available,
                reason=f"Insufficient budget. Available: {available}, Requested: {budget_request.requested_tokens}",
                suggestions=[
                    f"Reduce request to {available} tokens",
                    "Wait for budget to free up",
                    "Release unused reservations",
                ],
            )

        # Soft limit warning
        projected_usage = self.current_usage + budget_request.requested_tokens
        soft_threshold = self.total_budget * (self.soft_limit_percentage / 100)

        if projected_usage > soft_threshold:
            warnings.append(
                f"Approaching budget limit ({self.soft_limit_percentage}% threshold)"
            )
            suggestions.append("Monitor usage closely")

        return ValidationResult(
            is_valid=True,
            approved_tokens=budget_request.requested_tokens,
            warnings=warnings,
            suggestions=suggestions,
        )

    def track_consumption(self, tokens_used: int, operation_id: str, operation_type: str = "unknown") -> None:
        """
        Track actual token consumption.

        Args:
            tokens_used: Number of tokens consumed
            operation_id: Unique identifier for the operation
            operation_type: Type of operation performed
        """
        if tokens_used < 0:
            raise ValueError("Tokens used cannot be negative")

        self._transition_state(BudgetState.TRACKING)

        # Update current usage
        self.current_usage += tokens_used

        # Release reservation if exists
        if operation_id in self.reservations:
            del self.reservations[operation_id]

        # Record operation
        record = OperationRecord(
            operation_id=operation_id,
            operation_type=operation_type,
            tokens_used=tokens_used,
            timestamp=datetime.now(),
        )
        self.operation_history.append(record)

        # Update operation type statistics
        self.operation_type_stats[operation_type].append(tokens_used)

        # Invalidate prediction cache for this operation type
        self._invalidate_cache(operation_type)

        # Cleanup old history
        self._cleanup_old_history()

        self._transition_state(BudgetState.IDLE)

    def predict_usage(self, operation_type: str) -> TokenPrediction:
        """
        Predict token usage for an operation type.

        Uses historical data to forecast token requirements with confidence metrics.

        Args:
            operation_type: Type of operation to predict

        Returns:
            TokenPrediction with forecasted usage and confidence
        """
        # Check cache first
        if self._is_cache_valid(operation_type):
            return self.prediction_cache[operation_type]

        # Get historical data
        if operation_type not in self.operation_type_stats:
            # No historical data - return conservative estimate
            prediction = TokenPrediction(
                operation_type=operation_type,
                predicted_tokens=1000,  # Default conservative estimate
                confidence=0.0,
                historical_average=0.0,
                variance=0.0,
                sample_size=0,
            )
            return prediction

        stats = self.operation_type_stats[operation_type]
        sample_size = len(stats)

        if sample_size == 0:
            prediction = TokenPrediction(
                operation_type=operation_type,
                predicted_tokens=1000,
                confidence=0.0,
                historical_average=0.0,
                variance=0.0,
                sample_size=0,
            )
            return prediction

        # Calculate statistics
        average = sum(stats) / sample_size
        variance = sum((x - average) ** 2 for x in stats) / sample_size
        std_dev = variance ** 0.5

        # Predict with safety margin (average + 1 std dev)
        predicted = int(average + std_dev)

        # Confidence based on sample size and variance
        # Higher sample size and lower variance = higher confidence
        confidence = min(1.0, (sample_size / 100) * (1.0 / (1.0 + variance / (average + 1))))

        prediction = TokenPrediction(
            operation_type=operation_type,
            predicted_tokens=predicted,
            confidence=confidence,
            historical_average=average,
            variance=variance,
            sample_size=sample_size,
        )

        # Cache the prediction
        self.prediction_cache[operation_type] = prediction
        self.cache_timestamps[operation_type] = datetime.now()

        return prediction

    def allocate_budget(
        self,
        agents: List[Agent],
        total_budget: int,
        strategy: AllocationStrategy = AllocationStrategy.PROPORTIONAL,
    ) -> Dict[str, int]:
        """
        Distribute budget across multiple agents.

        Args:
            agents: List of agents to allocate budget to
            total_budget: Total budget to distribute
            strategy: Allocation strategy to use

        Returns:
            Dictionary mapping agent_id to allocated budget
        """
        self._transition_state(BudgetState.ALLOCATING)

        if not agents:
            self._transition_state(BudgetState.IDLE)
            return {}

        if total_budget < 0:
            raise ValueError("Total budget must be non-negative")

        allocations: Dict[str, int] = {}

        try:
            if strategy == AllocationStrategy.EQUAL:
                # Equal distribution
                per_agent = total_budget // len(agents)
                remainder = total_budget % len(agents)

                for i, agent in enumerate(agents):
                    allocation = per_agent + (1 if i < remainder else 0)
                    allocations[agent.agent_id] = allocation

            elif strategy == AllocationStrategy.PRIORITY_BASED:
                # Allocate based on priority levels
                total_priority = sum(agent.priority for agent in agents)

                for agent in agents:
                    allocation = int((agent.priority / total_priority) * total_budget)
                    allocations[agent.agent_id] = allocation

            elif strategy == AllocationStrategy.WEIGHTED:
                # Allocate based on custom weights
                total_weight = sum(agent.weight for agent in agents)

                if total_weight == 0:
                    # Fall back to equal distribution
                    return self.allocate_budget(agents, total_budget, AllocationStrategy.EQUAL)

                for agent in agents:
                    allocation = int((agent.weight / total_weight) * total_budget)
                    allocations[agent.agent_id] = allocation

            elif strategy == AllocationStrategy.PROPORTIONAL:
                # Allocate based on historical usage
                total_usage = sum(agent.historical_usage for agent in agents)

                if total_usage == 0:
                    # No history - fall back to equal distribution
                    return self.allocate_budget(agents, total_budget, AllocationStrategy.EQUAL)

                for agent in agents:
                    allocation = int((agent.historical_usage / total_usage) * total_budget)
                    allocations[agent.agent_id] = allocation

            elif strategy == AllocationStrategy.DYNAMIC:
                # Dynamic allocation considering both priority and historical usage
                # Formula: weight = (priority * 0.6) + (normalized_usage * 0.4)
                total_usage = sum(agent.historical_usage for agent in agents)

                if total_usage == 0:
                    # No history - use priority-based
                    return self.allocate_budget(agents, total_budget, AllocationStrategy.PRIORITY_BASED)

                weights = []
                for agent in agents:
                    normalized_usage = agent.historical_usage / total_usage
                    normalized_priority = agent.priority / 10.0  # Priority is 1-10
                    dynamic_weight = (normalized_priority * 0.6) + (normalized_usage * 0.4)
                    weights.append(dynamic_weight)

                total_weight = sum(weights)

                for agent, weight in zip(agents, weights):
                    allocation = int((weight / total_weight) * total_budget)
                    allocations[agent.agent_id] = allocation

            # Store allocations
            self.agent_budgets.update(allocations)

            self._transition_state(BudgetState.IDLE)
            return allocations

        except Exception as e:
            self._transition_state(BudgetState.ERROR)
            self.error_count += 1
            self.last_error = f"Budget allocation error: {str(e)}"
            raise

    def enforce_limits(self, current_usage: int, limit: int) -> EnforcementAction:
        """
        Enforce budget constraints with soft/hard thresholds.

        Args:
            current_usage: Current token usage level
            limit: Budget limit to enforce

        Returns:
            EnforcementAction with enforcement decision
        """
        if current_usage < 0:
            raise ValueError("Current usage cannot be negative")
        if limit < 0:
            raise ValueError("Limit cannot be negative")

        usage_percentage = (current_usage / limit * 100) if limit > 0 else 100.0

        soft_threshold = limit * (self.soft_limit_percentage / 100)
        hard_threshold = limit * (self.hard_limit_percentage / 100)

        if current_usage >= hard_threshold:
            return EnforcementAction(
                action_type="block",
                message=f"Hard limit reached ({self.hard_limit_percentage}%). Operation blocked.",
                current_usage=current_usage,
                limit=limit,
                usage_percentage=usage_percentage,
                recommended_action="Wait for budget reset or increase limit",
            )
        elif current_usage >= soft_threshold:
            return EnforcementAction(
                action_type="warn",
                message=f"Soft limit exceeded ({self.soft_limit_percentage}%). Approaching hard limit.",
                current_usage=current_usage,
                limit=limit,
                usage_percentage=usage_percentage,
                recommended_action="Monitor usage closely and optimize operations",
            )
        else:
            return EnforcementAction(
                action_type="allow",
                message="Within budget limits",
                current_usage=current_usage,
                limit=limit,
                usage_percentage=usage_percentage,
            )

    def analyze_trends(self, time_window: str = "24h") -> UsageAnalytics:
        """
        Analyze historical usage patterns and trends.

        Args:
            time_window: Time window for analysis (e.g., "1h", "24h", "7d")

        Returns:
            UsageAnalytics with comprehensive usage metrics
        """
        self._transition_state(BudgetState.ANALYZING)

        try:
            # Parse time window
            window_hours = self._parse_time_window(time_window)
            cutoff_time = datetime.now() - timedelta(hours=window_hours)

            # Filter operations in time window
            recent_ops = [
                op for op in self.operation_history
                if op.timestamp >= cutoff_time
            ]

            if not recent_ops:
                self._transition_state(BudgetState.IDLE)
                return UsageAnalytics(
                    time_window=time_window,
                    total_tokens_used=0,
                    num_operations=0,
                    average_tokens_per_operation=0.0,
                    peak_usage=0,
                    trend="stable",
                    efficiency_score=100.0,
                )

            # Calculate metrics
            total_tokens = sum(op.tokens_used for op in recent_ops)
            num_operations = len(recent_ops)
            avg_tokens = total_tokens / num_operations

            # Find peak usage
            peak_op = max(recent_ops, key=lambda op: op.tokens_used)
            peak_usage = peak_op.tokens_used
            peak_timestamp = peak_op.timestamp

            # Operation type breakdown
            type_breakdown: Dict[str, int] = defaultdict(int)
            for op in recent_ops:
                type_breakdown[op.operation_type] += op.tokens_used

            # Analyze trend
            trend = self._calculate_trend(recent_ops)

            # Calculate efficiency score (100 - waste percentage)
            # Efficiency based on how close actual usage is to predictions
            efficiency_score = self._calculate_efficiency(recent_ops)

            self._transition_state(BudgetState.IDLE)

            return UsageAnalytics(
                time_window=time_window,
                total_tokens_used=total_tokens,
                num_operations=num_operations,
                average_tokens_per_operation=avg_tokens,
                peak_usage=peak_usage,
                peak_timestamp=peak_timestamp,
                operation_type_breakdown=dict(type_breakdown),
                trend=trend,
                efficiency_score=efficiency_score,
            )

        except Exception as e:
            self._transition_state(BudgetState.ERROR)
            self.error_count += 1
            self.last_error = f"Analytics error: {str(e)}"
            raise

    def _parse_time_window(self, time_window: str) -> float:
        """Parse time window string to hours."""
        if time_window.endswith("h"):
            return float(time_window[:-1])
        elif time_window.endswith("d"):
            return float(time_window[:-1]) * 24
        elif time_window.endswith("m"):
            return float(time_window[:-1]) / 60
        else:
            return 24.0  # Default to 24 hours

    def _calculate_trend(self, operations: List[OperationRecord]) -> str:
        """Calculate usage trend from operations."""
        if len(operations) < 2:
            return "stable"

        # Split into two halves and compare
        mid = len(operations) // 2
        first_half = operations[:mid]
        second_half = operations[mid:]

        first_avg = sum(op.tokens_used for op in first_half) / len(first_half)
        second_avg = sum(op.tokens_used for op in second_half) / len(second_half)

        # 10% threshold for trend detection
        threshold = first_avg * 0.1

        if second_avg > first_avg + threshold:
            return "increasing"
        elif second_avg < first_avg - threshold:
            return "decreasing"
        else:
            return "stable"

    def _calculate_efficiency(self, operations: List[OperationRecord]) -> float:
        """Calculate efficiency score based on budget utilization."""
        if not operations:
            return 100.0

        # Efficiency based on variance from average
        avg_tokens = sum(op.tokens_used for op in operations) / len(operations)

        if avg_tokens == 0:
            return 100.0

        variance = sum((op.tokens_used - avg_tokens) ** 2 for op in operations) / len(operations)
        coefficient_of_variation = (variance ** 0.5) / avg_tokens

        # Lower variance = higher efficiency
        efficiency = max(0.0, min(100.0, 100.0 - (coefficient_of_variation * 100)))

        return round(efficiency, 2)

    def reset_budget(self, new_budget: Optional[int] = None) -> None:
        """
        Reset budget tracking.

        Args:
            new_budget: Optional new budget amount. If None, keeps existing budget.
        """
        if new_budget is not None:
            if new_budget < 0:
                raise ValueError("Budget must be non-negative")
            self.total_budget = new_budget

        self.current_usage = 0
        self.reservations.clear()
        self._invalidate_cache()

    def get_status(self) -> Dict[str, Any]:
        """Get current status of the budget manager."""
        return {
            "state": self.current_state.value,
            "total_budget": self.total_budget,
            "current_usage": self.current_usage,
            "available_budget": self._get_available_budget(),
            "reserved_budget": sum(self.reservations.values()),
            "usage_percentage": (self.current_usage / self.total_budget * 100) if self.total_budget > 0 else 0,
            "num_operations": len(self.operation_history),
            "num_reservations": len(self.reservations),
            "error_count": self.error_count,
            "last_error": self.last_error,
        }

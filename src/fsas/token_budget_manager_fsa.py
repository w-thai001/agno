"""Token Budget Manager FSA for managing token allocation and budgeting across FSA cascade."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4


class AllocationStrategy(Enum):
    """Budget allocation strategies."""

    EQUAL = "equal"
    WEIGHTED = "weighted"
    PRIORITY = "priority"


class BudgetStatus(Enum):
    """Budget status indicators."""

    OK = "ok"
    WARNING = "warning"
    EXCEEDED = "exceeded"


@dataclass
class FSAConfig:
    """Configuration for an FSA's token budget."""

    fsa_id: str
    weight: float = 1.0
    priority: int = 1
    soft_limit_ratio: float = 0.8  # Warning at 80% usage
    hard_limit: Optional[int] = None  # Override allocated budget


@dataclass
class UsageRecord:
    """Record of token usage for a single FSA call."""

    timestamp: datetime
    fsa_id: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    remaining_budget: int


@dataclass
class BudgetAllocation:
    """Allocated budget for an FSA."""

    fsa_id: str
    allocated_tokens: int
    used_tokens: int = 0
    soft_limit: int = 0
    hard_limit: int = 0

    def __post_init__(self):
        """Initialize limits based on allocation."""
        if self.soft_limit == 0:
            self.soft_limit = int(self.allocated_tokens * 0.8)
        if self.hard_limit == 0:
            self.hard_limit = self.allocated_tokens

    @property
    def remaining_tokens(self) -> int:
        """Calculate remaining tokens in budget."""
        return max(0, self.hard_limit - self.used_tokens)

    @property
    def usage_ratio(self) -> float:
        """Calculate usage ratio (0.0 to 1.0+)."""
        if self.hard_limit == 0:
            return 0.0
        return self.used_tokens / self.hard_limit

    @property
    def status(self) -> BudgetStatus:
        """Determine current budget status."""
        if self.used_tokens >= self.hard_limit:
            return BudgetStatus.EXCEEDED
        elif self.used_tokens >= self.soft_limit:
            return BudgetStatus.WARNING
        return BudgetStatus.OK


@dataclass
class OptimizationRecommendation:
    """Recommendation for budget optimization."""

    fsa_id: str
    current_allocation: int
    recommended_allocation: int
    reason: str
    priority: int = 1


@dataclass
class UsageStatistics:
    """Statistical summary of token usage."""

    total_tokens_allocated: int
    total_tokens_used: int
    total_calls: int
    fsa_stats: Dict[str, Dict[str, Any]]
    efficiency_score: float
    warnings: List[str]
    recommendations: List[OptimizationRecommendation]


class TokenBudgetManagerFSA:
    """
    Manages token allocation and budgeting across FSA cascade.

    Provides token tracking, budget enforcement, allocation strategies,
    optimization suggestions, and historical usage analytics.
    """

    def __init__(
        self,
        total_budget: int = 0,
        default_strategy: AllocationStrategy = AllocationStrategy.EQUAL,
        enable_tracking: bool = True,
    ):
        """
        Initialize the Token Budget Manager.

        Args:
            total_budget: Total token budget available
            default_strategy: Default allocation strategy to use
            enable_tracking: Enable detailed usage tracking
        """
        self.total_budget = total_budget
        self.default_strategy = default_strategy
        self.enable_tracking = enable_tracking

        self.allocations: Dict[str, BudgetAllocation] = {}
        self.usage_history: List[UsageRecord] = []
        self.fsa_configs: Dict[str, FSAConfig] = {}

        # Performance tracking
        self._call_count: Dict[str, int] = defaultdict(int)
        self._total_input_tokens: Dict[str, int] = defaultdict(int)
        self._total_output_tokens: Dict[str, int] = defaultdict(int)

    def allocate_budget(
        self,
        total_tokens: int,
        fsas_config: List[FSAConfig] | Dict[str, Any],
        strategy: Optional[AllocationStrategy] = None,
    ) -> Dict[str, BudgetAllocation]:
        """
        Allocate token budget across FSAs based on strategy.

        Args:
            total_tokens: Total tokens to allocate
            fsas_config: List of FSAConfig or dict with fsa_id -> config
            strategy: Allocation strategy (uses default if None)

        Returns:
            Dictionary mapping fsa_id to BudgetAllocation
        """
        strategy = strategy or self.default_strategy
        self.total_budget = total_tokens

        # Normalize config input
        configs = self._normalize_fsas_config(fsas_config)
        self.fsa_configs = {cfg.fsa_id: cfg for cfg in configs}

        # Apply allocation strategy
        if strategy == AllocationStrategy.EQUAL:
            allocations = self._allocate_equal(total_tokens, configs)
        elif strategy == AllocationStrategy.WEIGHTED:
            allocations = self._allocate_weighted(total_tokens, configs)
        elif strategy == AllocationStrategy.PRIORITY:
            allocations = self._allocate_priority(total_tokens, configs)
        else:
            raise ValueError(f"Unknown allocation strategy: {strategy}")

        self.allocations = allocations
        return allocations

    def track_usage(
        self,
        fsa_id: str,
        input_tokens: int,
        output_tokens: int,
    ) -> Tuple[int, BudgetStatus]:
        """
        Track token usage for an FSA call.

        Args:
            fsa_id: Identifier for the FSA
            input_tokens: Number of input tokens used
            output_tokens: Number of output tokens used

        Returns:
            Tuple of (remaining_tokens, budget_status)
        """
        total_tokens = input_tokens + output_tokens

        # Initialize allocation if not exists
        if fsa_id not in self.allocations:
            self._init_default_allocation(fsa_id)

        # Update allocation
        allocation = self.allocations[fsa_id]
        allocation.used_tokens += total_tokens

        # Update performance tracking
        self._call_count[fsa_id] += 1
        self._total_input_tokens[fsa_id] += input_tokens
        self._total_output_tokens[fsa_id] += output_tokens

        # Record usage history
        if self.enable_tracking:
            record = UsageRecord(
                timestamp=datetime.now(),
                fsa_id=fsa_id,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                remaining_budget=allocation.remaining_tokens,
            )
            self.usage_history.append(record)

        return allocation.remaining_tokens, allocation.status

    def check_budget(self, fsa_id: str) -> int:
        """
        Check remaining budget for an FSA.

        Args:
            fsa_id: Identifier for the FSA

        Returns:
            Number of remaining tokens
        """
        if fsa_id not in self.allocations:
            self._init_default_allocation(fsa_id)

        return self.allocations[fsa_id].remaining_tokens

    def get_budget_status(self, fsa_id: str) -> BudgetStatus:
        """
        Get budget status for an FSA.

        Args:
            fsa_id: Identifier for the FSA

        Returns:
            Current budget status
        """
        if fsa_id not in self.allocations:
            return BudgetStatus.OK

        return self.allocations[fsa_id].status

    def optimize_allocation(self) -> List[OptimizationRecommendation]:
        """
        Generate optimization recommendations based on usage patterns.

        Returns:
            List of optimization recommendations
        """
        recommendations = []

        if not self.usage_history:
            return recommendations

        # Analyze usage patterns
        for fsa_id, allocation in self.allocations.items():
            call_count = self._call_count.get(fsa_id, 0)

            if call_count == 0:
                continue

            avg_tokens_per_call = allocation.used_tokens / call_count
            usage_ratio = allocation.usage_ratio

            # Under-utilized FSA
            if usage_ratio < 0.3 and call_count > 5:
                recommended = int(allocation.hard_limit * 0.6)
                recommendations.append(
                    OptimizationRecommendation(
                        fsa_id=fsa_id,
                        current_allocation=allocation.hard_limit,
                        recommended_allocation=recommended,
                        reason=f"Low utilization ({usage_ratio:.1%}). Consider reducing allocation.",
                        priority=2,
                    )
                )

            # Over-utilized FSA
            elif usage_ratio > 0.9:
                recommended = int(allocation.hard_limit * 1.5)
                recommendations.append(
                    OptimizationRecommendation(
                        fsa_id=fsa_id,
                        current_allocation=allocation.hard_limit,
                        recommended_allocation=recommended,
                        reason=f"High utilization ({usage_ratio:.1%}). Consider increasing allocation.",
                        priority=1,
                    )
                )

            # Inefficient token usage (high output/input ratio)
            input_ratio = self._total_input_tokens[fsa_id] / allocation.used_tokens if allocation.used_tokens > 0 else 0
            if input_ratio < 0.2 and call_count > 3:
                recommendations.append(
                    OptimizationRecommendation(
                        fsa_id=fsa_id,
                        current_allocation=allocation.hard_limit,
                        recommended_allocation=allocation.hard_limit,
                        reason=f"High output token ratio. Consider prompt optimization to reduce output.",
                        priority=3,
                    )
                )

        # Sort by priority
        recommendations.sort(key=lambda r: r.priority)
        return recommendations

    def get_usage_report(self) -> UsageStatistics:
        """
        Generate comprehensive usage statistics report.

        Returns:
            UsageStatistics with detailed metrics
        """
        total_allocated = sum(alloc.hard_limit for alloc in self.allocations.values())
        total_used = sum(alloc.used_tokens for alloc in self.allocations.values())
        total_calls = sum(self._call_count.values())

        # Per-FSA statistics
        fsa_stats = {}
        for fsa_id, allocation in self.allocations.items():
            calls = self._call_count.get(fsa_id, 0)
            input_tokens = self._total_input_tokens.get(fsa_id, 0)
            output_tokens = self._total_output_tokens.get(fsa_id, 0)

            fsa_stats[fsa_id] = {
                "allocated": allocation.hard_limit,
                "used": allocation.used_tokens,
                "remaining": allocation.remaining_tokens,
                "usage_ratio": allocation.usage_ratio,
                "status": allocation.status.value,
                "calls": calls,
                "avg_tokens_per_call": allocation.used_tokens / calls if calls > 0 else 0,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "input_output_ratio": input_tokens / output_tokens if output_tokens > 0 else 0,
            }

        # Calculate efficiency score
        efficiency_score = self._calculate_efficiency_score()

        # Generate warnings
        warnings = self._generate_warnings()

        # Get optimization recommendations
        recommendations = self.optimize_allocation()

        return UsageStatistics(
            total_tokens_allocated=total_allocated,
            total_tokens_used=total_used,
            total_calls=total_calls,
            fsa_stats=fsa_stats,
            efficiency_score=efficiency_score,
            warnings=warnings,
            recommendations=recommendations,
        )

    def reset_usage(self, fsa_id: Optional[str] = None):
        """
        Reset usage tracking for specific FSA or all FSAs.

        Args:
            fsa_id: Specific FSA to reset, or None to reset all
        """
        if fsa_id:
            if fsa_id in self.allocations:
                self.allocations[fsa_id].used_tokens = 0
            self._call_count[fsa_id] = 0
            self._total_input_tokens[fsa_id] = 0
            self._total_output_tokens[fsa_id] = 0
            self.usage_history = [r for r in self.usage_history if r.fsa_id != fsa_id]
        else:
            for allocation in self.allocations.values():
                allocation.used_tokens = 0
            self._call_count.clear()
            self._total_input_tokens.clear()
            self._total_output_tokens.clear()
            self.usage_history.clear()

    # Private helper methods

    def _normalize_fsas_config(
        self,
        fsas_config: List[FSAConfig] | Dict[str, Any],
    ) -> List[FSAConfig]:
        """Normalize FSA config input to list of FSAConfig."""
        if isinstance(fsas_config, list):
            return fsas_config

        # Convert dict to list of FSAConfig
        configs = []
        for fsa_id, config in fsas_config.items():
            if isinstance(config, FSAConfig):
                configs.append(config)
            elif isinstance(config, dict):
                configs.append(FSAConfig(fsa_id=fsa_id, **config))
            else:
                configs.append(FSAConfig(fsa_id=fsa_id))

        return configs

    def _allocate_equal(
        self,
        total_tokens: int,
        configs: List[FSAConfig],
    ) -> Dict[str, BudgetAllocation]:
        """Allocate tokens equally across FSAs."""
        if not configs:
            return {}

        tokens_per_fsa = total_tokens // len(configs)
        allocations = {}

        for cfg in configs:
            allocation = cfg.hard_limit if cfg.hard_limit else tokens_per_fsa
            allocations[cfg.fsa_id] = BudgetAllocation(
                fsa_id=cfg.fsa_id,
                allocated_tokens=allocation,
                soft_limit=int(allocation * cfg.soft_limit_ratio),
                hard_limit=allocation,
            )

        return allocations

    def _allocate_weighted(
        self,
        total_tokens: int,
        configs: List[FSAConfig],
    ) -> Dict[str, BudgetAllocation]:
        """Allocate tokens based on weights."""
        if not configs:
            return {}

        total_weight = sum(cfg.weight for cfg in configs)
        allocations = {}

        for cfg in configs:
            if cfg.hard_limit:
                allocation = cfg.hard_limit
            else:
                allocation = int(total_tokens * (cfg.weight / total_weight))

            allocations[cfg.fsa_id] = BudgetAllocation(
                fsa_id=cfg.fsa_id,
                allocated_tokens=allocation,
                soft_limit=int(allocation * cfg.soft_limit_ratio),
                hard_limit=allocation,
            )

        return allocations

    def _allocate_priority(
        self,
        total_tokens: int,
        configs: List[FSAConfig],
    ) -> Dict[str, BudgetAllocation]:
        """Allocate tokens based on priority (higher priority gets more)."""
        if not configs:
            return {}

        # Sort by priority (lower number = higher priority)
        sorted_configs = sorted(configs, key=lambda c: c.priority)
        allocations = {}
        remaining_tokens = total_tokens

        # Calculate priority-based weights (inverse of priority number)
        max_priority = max(cfg.priority for cfg in configs)
        priority_weights = {
            cfg.fsa_id: (max_priority - cfg.priority + 1) for cfg in configs
        }
        total_weight = sum(priority_weights.values())

        for cfg in sorted_configs:
            if cfg.hard_limit:
                allocation = min(cfg.hard_limit, remaining_tokens)
            else:
                allocation = int(total_tokens * (priority_weights[cfg.fsa_id] / total_weight))

            allocations[cfg.fsa_id] = BudgetAllocation(
                fsa_id=cfg.fsa_id,
                allocated_tokens=allocation,
                soft_limit=int(allocation * cfg.soft_limit_ratio),
                hard_limit=allocation,
            )
            remaining_tokens -= allocation

        return allocations

    def _init_default_allocation(self, fsa_id: str):
        """Initialize default allocation for untracked FSA."""
        default_allocation = self.total_budget // 10 if self.total_budget > 0 else 10000

        self.allocations[fsa_id] = BudgetAllocation(
            fsa_id=fsa_id,
            allocated_tokens=default_allocation,
            hard_limit=default_allocation,
        )

    def _calculate_efficiency_score(self) -> float:
        """
        Calculate overall efficiency score (0.0 to 1.0).

        Based on:
        - Token utilization (how well allocated tokens are used)
        - Distribution balance (how evenly tokens are distributed)
        - Waste factor (allocated but unused tokens)
        """
        if not self.allocations:
            return 1.0

        total_allocated = sum(alloc.hard_limit for alloc in self.allocations.values())
        if total_allocated == 0:
            return 1.0

        total_used = sum(alloc.used_tokens for alloc in self.allocations.values())

        # Utilization score (prefer 70-90% utilization)
        utilization = total_used / total_allocated
        utilization_score = 1.0 - abs(0.8 - utilization)
        utilization_score = max(0.0, min(1.0, utilization_score))

        # Balance score (check variance in usage ratios)
        usage_ratios = [alloc.usage_ratio for alloc in self.allocations.values()]
        if len(usage_ratios) > 1:
            avg_ratio = sum(usage_ratios) / len(usage_ratios)
            variance = sum((r - avg_ratio) ** 2 for r in usage_ratios) / len(usage_ratios)
            balance_score = 1.0 / (1.0 + variance)
        else:
            balance_score = 1.0

        # Weighted combination
        efficiency = (utilization_score * 0.7) + (balance_score * 0.3)
        return round(efficiency, 3)

    def _generate_warnings(self) -> List[str]:
        """Generate warnings for budget issues."""
        warnings = []

        for fsa_id, allocation in self.allocations.items():
            status = allocation.status

            if status == BudgetStatus.EXCEEDED:
                warnings.append(
                    f"FSA '{fsa_id}' has exceeded budget: "
                    f"{allocation.used_tokens}/{allocation.hard_limit} tokens "
                    f"({allocation.usage_ratio:.1%})"
                )
            elif status == BudgetStatus.WARNING:
                warnings.append(
                    f"FSA '{fsa_id}' approaching budget limit: "
                    f"{allocation.used_tokens}/{allocation.hard_limit} tokens "
                    f"({allocation.usage_ratio:.1%})"
                )

        # Check overall budget
        total_allocated = sum(alloc.hard_limit for alloc in self.allocations.values())
        total_used = sum(alloc.used_tokens for alloc in self.allocations.values())

        if self.total_budget > 0 and total_used > self.total_budget * 0.9:
            warnings.append(
                f"Overall budget approaching limit: "
                f"{total_used}/{self.total_budget} tokens "
                f"({total_used/self.total_budget:.1%})"
            )

        return warnings

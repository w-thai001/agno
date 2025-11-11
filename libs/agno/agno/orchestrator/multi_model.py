"""
Multi-Model Orchestrator for Claude Models (Opus, Sonnet, Haiku)

This module provides intelligent routing of tasks to optimal Claude models based on:
- Task complexity analysis
- Budget constraints and cost optimization
- Latency requirements
- Performance tracking and analytics
"""

import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from agno.models.anthropic import Claude
from agno.models.message import Message
from agno.utils.log import logger


class ModelTier(Enum):
    """Claude model tiers with their characteristics."""

    OPUS = "opus"
    SONNET = "sonnet"
    HAIKU = "haiku"


@dataclass
class ModelConfig:
    """Configuration for a specific Claude model tier."""

    tier: ModelTier
    model_id: str
    cost_per_1k_input: float  # USD per 1K input tokens
    cost_per_1k_output: float  # USD per 1K output tokens
    max_tokens: int
    complexity_score: int  # 1-10, higher = more capable
    speed_score: int  # 1-10, higher = faster


@dataclass
class TaskMetrics:
    """Metrics for a completed task."""

    task_id: str
    model_tier: ModelTier
    model_id: str
    complexity_score: float
    input_tokens: int
    output_tokens: int
    total_cost: float
    latency_ms: float
    timestamp: datetime
    success: bool
    error: Optional[str] = None


@dataclass
class BudgetConstraints:
    """Budget constraints for task routing."""

    max_cost_per_task: Optional[float] = None  # USD
    max_latency_ms: Optional[float] = None  # milliseconds
    prefer_speed: bool = False  # Prioritize speed over quality
    prefer_quality: bool = False  # Prioritize quality over cost


class MultiModelOrchestrator:
    """
    Intelligent orchestrator for routing tasks to optimal Claude models.

    Features:
    - Automatic task complexity analysis
    - Cost-optimized model selection
    - Performance tracking and analytics
    - Budget constraint enforcement
    - Adaptive routing based on historical performance
    """

    # Model configurations with current pricing (as of Jan 2025)
    MODEL_CONFIGS = {
        ModelTier.OPUS: ModelConfig(
            tier=ModelTier.OPUS,
            model_id="claude-opus-4-20250514",
            cost_per_1k_input=15.0,
            cost_per_1k_output=75.0,
            max_tokens=16384,
            complexity_score=10,
            speed_score=6,
        ),
        ModelTier.SONNET: ModelConfig(
            tier=ModelTier.SONNET,
            model_id="claude-sonnet-4-20250514",
            cost_per_1k_input=3.0,
            cost_per_1k_output=15.0,
            max_tokens=8192,
            complexity_score=8,
            speed_score=8,
        ),
        ModelTier.HAIKU: ModelConfig(
            tier=ModelTier.HAIKU,
            model_id="claude-3-5-haiku-20241022",
            cost_per_1k_input=0.8,
            cost_per_1k_output=4.0,
            max_tokens=8192,
            complexity_score=6,
            speed_score=10,
        ),
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        default_budget: Optional[BudgetConstraints] = None,
        enable_tracking: bool = True,
    ):
        """
        Initialize the Multi-Model Orchestrator.

        Args:
            api_key: Anthropic API key (uses ANTHROPIC_API_KEY env var if not provided)
            default_budget: Default budget constraints for all tasks
            enable_tracking: Enable performance tracking and analytics
        """
        self.api_key = api_key
        self.default_budget = default_budget or BudgetConstraints()
        self.enable_tracking = enable_tracking
        self.metrics_history: List[TaskMetrics] = []
        self._task_counter = 0

        logger.info("MultiModelOrchestrator initialized with tracking=%s", enable_tracking)

    def analyze_task_complexity(self, task: str, context: Optional[Dict[str, Any]] = None) -> float:
        """
        Analyze task complexity to determine appropriate model tier.

        Args:
            task: The task description or prompt
            context: Optional context including token estimates, domain, etc.

        Returns:
            Complexity score from 0-10 (higher = more complex)
        """
        complexity_score = 0.0

        # Base complexity on task length
        task_length = len(task)
        if task_length < 100:
            complexity_score += 1
        elif task_length < 500:
            complexity_score += 3
        elif task_length < 1500:
            complexity_score += 5
        else:
            complexity_score += 7

        # Check for complexity indicators
        complexity_indicators = [
            ("reasoning", 2.0),
            ("analysis", 2.0),
            ("complex", 1.5),
            ("detailed", 1.5),
            ("comprehensive", 1.5),
            ("explain", 1.0),
            ("compare", 1.5),
            ("evaluate", 2.0),
            ("design", 2.0),
            ("architect", 2.5),
            ("optimize", 2.0),
            ("strategy", 2.0),
            ("multi-step", 2.5),
            ("algorithm", 2.0),
            ("research", 2.0),
        ]

        task_lower = task.lower()
        for indicator, weight in complexity_indicators:
            if indicator in task_lower:
                complexity_score += weight

        # Simple task indicators (reduce complexity)
        simple_indicators = [
            ("simple", -1.5),
            ("quick", -1.0),
            ("summarize", -0.5),
            ("list", -1.0),
            ("what is", -1.0),
            ("define", -0.5),
        ]

        for indicator, weight in simple_indicators:
            if indicator in task_lower:
                complexity_score += weight

        # Adjust based on context
        if context:
            estimated_tokens = context.get("estimated_input_tokens", 0)
            if estimated_tokens > 10000:
                complexity_score += 2
            elif estimated_tokens > 5000:
                complexity_score += 1

            if context.get("requires_tools", False):
                complexity_score += 1.5

            if context.get("multi_turn", False):
                complexity_score += 1

        # Clamp to 0-10 range
        complexity_score = max(0, min(10, complexity_score))

        logger.debug(f"Task complexity score: {complexity_score:.2f}")
        return complexity_score

    def selectModel(
        self, complexity: float, latency: Optional[float] = None, budget: Optional[BudgetConstraints] = None
    ) -> ModelConfig:
        """
        Select optimal model based on complexity, latency requirements, and budget.

        Args:
            complexity: Task complexity score (0-10)
            latency: Maximum acceptable latency in milliseconds
            budget: Budget constraints for this task

        Returns:
            Selected ModelConfig
        """
        budget = budget or self.default_budget

        # Override for speed preference (highest priority)
        if budget.prefer_speed:
            selected_tier = ModelTier.HAIKU
            logger.info("Selecting Haiku for speed optimization")
        # Start with complexity-based selection
        elif complexity >= 8 and not budget.prefer_speed:
            selected_tier = ModelTier.OPUS
        elif complexity >= 4 or budget.prefer_quality:
            selected_tier = ModelTier.SONNET
        else:
            selected_tier = ModelTier.HAIKU

        # Override based on budget constraints
        if budget.max_cost_per_task is not None:
            # Estimate cost for 1K input/output tokens
            config = self.MODEL_CONFIGS[selected_tier]
            estimated_cost = (config.cost_per_1k_input + config.cost_per_1k_output) / 1000

            if estimated_cost > budget.max_cost_per_task:
                # Downgrade to cheaper model
                if selected_tier == ModelTier.OPUS:
                    selected_tier = ModelTier.SONNET
                    logger.info("Downgrading from Opus to Sonnet due to budget constraints")
                elif selected_tier == ModelTier.SONNET:
                    selected_tier = ModelTier.HAIKU
                    logger.info("Downgrading from Sonnet to Haiku due to budget constraints")

        # Override based on latency requirements
        if latency is not None and latency < 1000:
            selected_tier = ModelTier.HAIKU
            logger.info("Selecting Haiku for optimal latency")

        selected_config = self.MODEL_CONFIGS[selected_tier]
        logger.info(
            f"Selected model: {selected_config.model_id} "
            f"(complexity={complexity:.2f}, tier={selected_tier.value})"
        )

        return selected_config

    def routeTask(
        self,
        task: str,
        budget: Optional[BudgetConstraints] = None,
        context: Optional[Dict[str, Any]] = None,
        execute: bool = True,
    ) -> Dict[str, Any]:
        """
        Route a task to the optimal model and optionally execute it.

        Args:
            task: The task/prompt to execute
            budget: Budget constraints for this specific task
            context: Optional context for complexity analysis
            execute: Whether to actually execute the task or just return routing decision

        Returns:
            Dictionary containing routing decision and execution results (if execute=True)
        """
        self._task_counter += 1
        task_id = f"task_{self._task_counter}_{int(time.time())}"

        # Analyze complexity
        complexity = self.analyze_task_complexity(task, context)

        # Select model
        latency_req = budget.max_latency_ms if budget else None
        model_config = self.selectModel(complexity, latency_req, budget)

        routing_decision = {
            "task_id": task_id,
            "complexity_score": complexity,
            "selected_model": model_config.model_id,
            "model_tier": model_config.tier.value,
            "estimated_cost_per_1k_tokens": model_config.cost_per_1k_input + model_config.cost_per_1k_output,
        }

        if not execute:
            return routing_decision

        # Execute the task
        start_time = time.time()
        success = True
        error_msg = None
        response = None
        usage = None

        try:
            # Create Claude model instance
            model = Claude(id=model_config.model_id, api_key=self.api_key, max_tokens=model_config.max_tokens)

            # Execute the task
            messages = [Message(role="user", content=task)]
            response_obj = model.invoke(messages)
            response = response_obj

            # Extract usage information
            if hasattr(response_obj, "usage"):
                usage = response_obj.usage

        except Exception as e:
            success = False
            error_msg = str(e)
            logger.error(f"Task execution failed: {error_msg}")

        # Calculate metrics
        latency_ms = (time.time() - start_time) * 1000

        input_tokens = usage.input_tokens if usage else 0
        output_tokens = usage.output_tokens if usage else 0
        total_cost = (
            (input_tokens / 1000.0 * model_config.cost_per_1k_input)
            + (output_tokens / 1000.0 * model_config.cost_per_1k_output)
            if usage
            else 0.0
        )

        # Track performance
        if self.enable_tracking:
            metrics = TaskMetrics(
                task_id=task_id,
                model_tier=model_config.tier,
                model_id=model_config.model_id,
                complexity_score=complexity,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_cost=total_cost,
                latency_ms=latency_ms,
                timestamp=datetime.now(),
                success=success,
                error=error_msg,
            )
            self.metrics_history.append(metrics)

        # Build result
        result = {
            **routing_decision,
            "executed": True,
            "success": success,
            "latency_ms": latency_ms,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_cost_usd": total_cost,
            "response": response,
        }

        if error_msg:
            result["error"] = error_msg

        logger.info(
            f"Task {task_id} completed: {model_config.tier.value} "
            f"(latency={latency_ms:.0f}ms, cost=${total_cost:.4f})"
        )

        return result

    def trackPerformance(self) -> Dict[str, Any]:
        """
        Get performance analytics and statistics.

        Returns:
            Dictionary containing performance metrics and analytics
        """
        if not self.metrics_history:
            return {
                "total_tasks": 0,
                "message": "No tasks executed yet",
            }

        total_tasks = len(self.metrics_history)
        successful_tasks = sum(1 for m in self.metrics_history if m.success)
        total_cost = sum(m.total_cost for m in self.metrics_history)
        avg_latency = sum(m.latency_ms for m in self.metrics_history) / total_tasks

        # Per-model statistics
        model_stats = {}
        for tier in ModelTier:
            tier_metrics = [m for m in self.metrics_history if m.model_tier == tier]
            if tier_metrics:
                model_stats[tier.value] = {
                    "tasks": len(tier_metrics),
                    "avg_latency_ms": sum(m.latency_ms for m in tier_metrics) / len(tier_metrics),
                    "total_cost_usd": sum(m.total_cost for m in tier_metrics),
                    "avg_complexity": sum(m.complexity_score for m in tier_metrics) / len(tier_metrics),
                    "success_rate": sum(1 for m in tier_metrics if m.success) / len(tier_metrics),
                }

        analytics = {
            "total_tasks": total_tasks,
            "successful_tasks": successful_tasks,
            "success_rate": successful_tasks / total_tasks,
            "total_cost_usd": total_cost,
            "avg_cost_per_task_usd": total_cost / total_tasks,
            "avg_latency_ms": avg_latency,
            "model_distribution": {tier.value: len([m for m in self.metrics_history if m.model_tier == tier]) for tier in ModelTier},
            "model_stats": model_stats,
        }

        return analytics

    def get_cost_savings_report(self) -> Dict[str, Any]:
        """
        Calculate cost savings from intelligent routing vs. always using Opus.

        Returns:
            Dictionary containing cost savings analysis
        """
        if not self.metrics_history:
            return {"message": "No tasks executed yet"}

        actual_cost = sum(m.total_cost for m in self.metrics_history)

        # Calculate what it would have cost with Opus for all tasks
        opus_config = self.MODEL_CONFIGS[ModelTier.OPUS]
        opus_cost = 0.0
        for m in self.metrics_history:
            opus_cost += (m.input_tokens / 1000.0 * opus_config.cost_per_1k_input) + (
                m.output_tokens / 1000.0 * opus_config.cost_per_1k_output
            )

        savings = opus_cost - actual_cost
        savings_percent = (savings / opus_cost * 100) if opus_cost > 0 else 0

        return {
            "actual_cost_usd": actual_cost,
            "opus_only_cost_usd": opus_cost,
            "savings_usd": savings,
            "savings_percent": savings_percent,
            "total_tasks": len(self.metrics_history),
        }

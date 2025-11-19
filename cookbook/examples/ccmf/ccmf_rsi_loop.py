"""
CCMF RSI (Recursive Self-Improvement) Loop - SESSION 1
=======================================================

This module implements the Recursive Self-Improvement feedback loop
for the CCMF framework. It enables the system to learn from its
operations, adapt strategies, and improve performance over time.

Key components:
- Feedback collection and analysis
- Performance metrics tracking
- Strategy adaptation
- Continuous improvement mechanisms
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
from enum import Enum
import statistics


class FeedbackType(Enum):
    """Types of feedback in the RSI loop."""
    SUCCESS = "success"
    FAILURE = "failure"
    PERFORMANCE = "performance"
    QUALITY = "quality"
    EFFICIENCY = "efficiency"
    USER = "user"


class AdaptationStrategy(Enum):
    """Strategies for system adaptation."""
    OPTIMIZE_PARAMETERS = "optimize_parameters"
    CHANGE_PATTERN = "change_pattern"
    ADD_FALLBACK = "add_fallback"
    INCREASE_RESOURCES = "increase_resources"
    DECREASE_RESOURCES = "decrease_resources"
    NO_ACTION = "no_action"


@dataclass
class FeedbackEntry:
    """Represents a single feedback entry in the RSI loop."""
    timestamp: datetime
    feedback_type: FeedbackType
    source: str  # Which component generated the feedback
    metrics: Dict[str, Any]
    context: Dict[str, Any] = field(default_factory=dict)
    severity: float = 0.5  # 0.0 (low) to 1.0 (high)
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert feedback to dictionary."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'feedback_type': self.feedback_type.value,
            'source': self.source,
            'metrics': self.metrics,
            'context': self.context,
            'severity': self.severity,
            'message': self.message
        }


@dataclass
class PerformanceMetrics:
    """Performance metrics for RSI analysis."""
    execution_time: float = 0.0
    success_rate: float = 0.0
    resource_usage: Dict[str, Any] = field(default_factory=dict)
    quality_score: float = 0.0
    efficiency_score: float = 0.0
    error_count: int = 0
    total_operations: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            'execution_time': self.execution_time,
            'success_rate': self.success_rate,
            'resource_usage': self.resource_usage,
            'quality_score': self.quality_score,
            'efficiency_score': self.efficiency_score,
            'error_count': self.error_count,
            'total_operations': self.total_operations
        }


@dataclass
class AdaptationDecision:
    """Represents a decision made by the RSI loop."""
    timestamp: datetime
    strategy: AdaptationStrategy
    reason: str
    confidence: float  # 0.0 to 1.0
    parameters: Dict[str, Any] = field(default_factory=dict)
    expected_improvement: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert decision to dictionary."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'strategy': self.strategy.value,
            'reason': self.reason,
            'confidence': self.confidence,
            'parameters': self.parameters,
            'expected_improvement': self.expected_improvement
        }


class RSIFeedbackLoop:
    """
    Recursive Self-Improvement Feedback Loop.

    This class implements a continuous improvement mechanism that:
    1. Collects feedback from system operations
    2. Analyzes performance trends
    3. Makes adaptation decisions
    4. Applies improvements
    5. Validates improvements
    """

    def __init__(
        self,
        feedback_window: int = 100,
        adaptation_threshold: float = 0.3,
        min_feedback_for_adaptation: int = 10
    ):
        """
        Initialize the RSI feedback loop.

        Args:
            feedback_window: Number of recent feedback entries to consider
            adaptation_threshold: Threshold for triggering adaptation
            min_feedback_for_adaptation: Minimum feedback entries before adapting
        """
        self.feedback_window = feedback_window
        self.adaptation_threshold = adaptation_threshold
        self.min_feedback_for_adaptation = min_feedback_for_adaptation

        self.feedback_history: List[FeedbackEntry] = []
        self.adaptation_history: List[AdaptationDecision] = []
        self.performance_snapshots: List[PerformanceMetrics] = []

        self.current_metrics = PerformanceMetrics()
        self.improvement_rate = 0.0

    def collect_feedback(
        self,
        feedback_type: FeedbackType,
        source: str,
        metrics: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        severity: float = 0.5,
        message: str = ""
    ):
        """
        Collect feedback from system operations.

        Args:
            feedback_type: Type of feedback
            source: Source component
            metrics: Metrics data
            context: Optional context information
            severity: Severity level (0.0 to 1.0)
            message: Optional message
        """
        feedback = FeedbackEntry(
            timestamp=datetime.now(),
            feedback_type=feedback_type,
            source=source,
            metrics=metrics,
            context=context or {},
            severity=severity,
            message=message
        )

        self.feedback_history.append(feedback)

        # Keep only the most recent entries within the window
        if len(self.feedback_history) > self.feedback_window * 2:
            self.feedback_history = self.feedback_history[-self.feedback_window:]

        # Update current metrics
        self._update_metrics()

    def _update_metrics(self):
        """Update current performance metrics based on feedback."""
        if not self.feedback_history:
            return

        recent_feedback = self.feedback_history[-self.feedback_window:]

        # Calculate success rate
        success_count = sum(
            1 for f in recent_feedback
            if f.feedback_type == FeedbackType.SUCCESS
        )
        total_operations = len([
            f for f in recent_feedback
            if f.feedback_type in [FeedbackType.SUCCESS, FeedbackType.FAILURE]
        ])
        self.current_metrics.success_rate = (
            success_count / total_operations if total_operations > 0 else 0.0
        )

        # Calculate average execution time
        execution_times = [
            f.metrics.get('execution_time', 0.0)
            for f in recent_feedback
            if 'execution_time' in f.metrics
        ]
        self.current_metrics.execution_time = (
            statistics.mean(execution_times) if execution_times else 0.0
        )

        # Calculate quality score
        quality_scores = [
            f.metrics.get('quality', 0.0)
            for f in recent_feedback
            if 'quality' in f.metrics
        ]
        self.current_metrics.quality_score = (
            statistics.mean(quality_scores) if quality_scores else 0.0
        )

        # Count errors
        self.current_metrics.error_count = sum(
            1 for f in recent_feedback
            if f.feedback_type == FeedbackType.FAILURE
        )

        # Total operations
        self.current_metrics.total_operations = total_operations

        # Calculate efficiency score (inverse of execution time, normalized)
        if self.current_metrics.execution_time > 0:
            self.current_metrics.efficiency_score = min(
                1.0, 1.0 / self.current_metrics.execution_time
            )

    def analyze_performance(self) -> Dict[str, Any]:
        """
        Analyze current performance and identify improvement opportunities.

        Returns:
            Dictionary with analysis results
        """
        if len(self.feedback_history) < self.min_feedback_for_adaptation:
            return {
                'ready_for_adaptation': False,
                'reason': f'Insufficient feedback data (need {self.min_feedback_for_adaptation})',
                'current_metrics': self.current_metrics.to_dict()
            }

        recent_feedback = self.feedback_history[-self.feedback_window:]

        # Identify trends
        trends = {
            'success_rate_trend': self._calculate_trend('success_rate'),
            'execution_time_trend': self._calculate_trend('execution_time'),
            'quality_trend': self._calculate_trend('quality'),
            'error_rate_trend': self._calculate_trend('error_rate')
        }

        # Identify problems
        problems = []
        if self.current_metrics.success_rate < 0.7:
            problems.append({
                'type': 'low_success_rate',
                'severity': 1.0 - self.current_metrics.success_rate,
                'description': f'Success rate is low: {self.current_metrics.success_rate:.2%}'
            })

        if self.current_metrics.execution_time > 5.0:  # Threshold
            problems.append({
                'type': 'high_execution_time',
                'severity': min(1.0, self.current_metrics.execution_time / 10.0),
                'description': f'Execution time is high: {self.current_metrics.execution_time:.2f}s'
            })

        if self.current_metrics.error_count > len(recent_feedback) * 0.3:
            problems.append({
                'type': 'high_error_rate',
                'severity': self.current_metrics.error_count / len(recent_feedback),
                'description': f'Error rate is high: {self.current_metrics.error_count} errors'
            })

        # Calculate overall health score
        health_score = (
            self.current_metrics.success_rate * 0.4 +
            self.current_metrics.quality_score * 0.3 +
            self.current_metrics.efficiency_score * 0.3
        )

        needs_adaptation = (
            health_score < (1.0 - self.adaptation_threshold) or
            len(problems) > 0
        )

        return {
            'ready_for_adaptation': needs_adaptation,
            'health_score': health_score,
            'current_metrics': self.current_metrics.to_dict(),
            'trends': trends,
            'problems': problems,
            'feedback_count': len(recent_feedback)
        }

    def _calculate_trend(self, metric_name: str) -> str:
        """
        Calculate trend for a specific metric.

        Args:
            metric_name: Name of the metric

        Returns:
            Trend description ('improving', 'declining', 'stable')
        """
        if len(self.performance_snapshots) < 2:
            return 'stable'

        recent_snapshots = self.performance_snapshots[-5:]
        values = []

        for snapshot in recent_snapshots:
            if metric_name == 'success_rate':
                values.append(snapshot.success_rate)
            elif metric_name == 'execution_time':
                values.append(snapshot.execution_time)
            elif metric_name == 'quality':
                values.append(snapshot.quality_score)
            elif metric_name == 'error_rate':
                values.append(snapshot.error_count)

        if len(values) < 2:
            return 'stable'

        # Simple linear trend
        first_half = statistics.mean(values[:len(values)//2])
        second_half = statistics.mean(values[len(values)//2:])

        if metric_name == 'execution_time' or metric_name == 'error_rate':
            # Lower is better
            if second_half < first_half * 0.9:
                return 'improving'
            elif second_half > first_half * 1.1:
                return 'declining'
        else:
            # Higher is better
            if second_half > first_half * 1.1:
                return 'improving'
            elif second_half < first_half * 0.9:
                return 'declining'

        return 'stable'

    def make_adaptation_decision(self, analysis: Dict[str, Any]) -> Optional[AdaptationDecision]:
        """
        Make an adaptation decision based on performance analysis.

        Args:
            analysis: Performance analysis results

        Returns:
            AdaptationDecision or None if no action needed
        """
        if not analysis.get('ready_for_adaptation', False):
            return None

        problems = analysis.get('problems', [])
        health_score = analysis.get('health_score', 1.0)

        # Prioritize problems by severity
        if problems:
            problems.sort(key=lambda p: p['severity'], reverse=True)
            main_problem = problems[0]

            if main_problem['type'] == 'low_success_rate':
                return AdaptationDecision(
                    timestamp=datetime.now(),
                    strategy=AdaptationStrategy.ADD_FALLBACK,
                    reason=main_problem['description'],
                    confidence=main_problem['severity'],
                    parameters={'fallback_strategy': 'retry_with_backoff'},
                    expected_improvement=0.2
                )

            elif main_problem['type'] == 'high_execution_time':
                return AdaptationDecision(
                    timestamp=datetime.now(),
                    strategy=AdaptationStrategy.OPTIMIZE_PARAMETERS,
                    reason=main_problem['description'],
                    confidence=main_problem['severity'],
                    parameters={'target_metric': 'execution_time'},
                    expected_improvement=0.3
                )

            elif main_problem['type'] == 'high_error_rate':
                return AdaptationDecision(
                    timestamp=datetime.now(),
                    strategy=AdaptationStrategy.CHANGE_PATTERN,
                    reason=main_problem['description'],
                    confidence=main_problem['severity'],
                    parameters={'consider_alternative_patterns': True},
                    expected_improvement=0.25
                )

        # General low health score
        if health_score < 0.6:
            return AdaptationDecision(
                timestamp=datetime.now(),
                strategy=AdaptationStrategy.INCREASE_RESOURCES,
                reason=f'Overall health score low: {health_score:.2%}',
                confidence=0.6,
                parameters={'resource_type': 'compute'},
                expected_improvement=0.15
            )

        return None

    def apply_adaptation(self, decision: AdaptationDecision) -> bool:
        """
        Apply an adaptation decision.

        Args:
            decision: The adaptation decision to apply

        Returns:
            True if successful, False otherwise
        """
        # Record the decision
        self.adaptation_history.append(decision)

        # In a real implementation, this would apply actual changes
        # For now, we simulate the application
        print(f"Applying adaptation: {decision.strategy.value}")
        print(f"Reason: {decision.reason}")
        print(f"Confidence: {decision.confidence:.2%}")
        print(f"Expected improvement: {decision.expected_improvement:.2%}")

        return True

    def snapshot_performance(self):
        """Take a snapshot of current performance metrics."""
        snapshot = PerformanceMetrics(
            execution_time=self.current_metrics.execution_time,
            success_rate=self.current_metrics.success_rate,
            resource_usage=self.current_metrics.resource_usage.copy(),
            quality_score=self.current_metrics.quality_score,
            efficiency_score=self.current_metrics.efficiency_score,
            error_count=self.current_metrics.error_count,
            total_operations=self.current_metrics.total_operations
        )
        self.performance_snapshots.append(snapshot)

        # Keep last 50 snapshots
        if len(self.performance_snapshots) > 50:
            self.performance_snapshots = self.performance_snapshots[-50:]

    def get_improvement_report(self) -> Dict[str, Any]:
        """
        Generate a report on system improvements over time.

        Returns:
            Dictionary with improvement metrics
        """
        if len(self.performance_snapshots) < 2:
            return {
                'message': 'Insufficient data for improvement analysis',
                'adaptations_made': len(self.adaptation_history)
            }

        first_snapshot = self.performance_snapshots[0]
        latest_snapshot = self.performance_snapshots[-1]

        improvements = {
            'success_rate': {
                'initial': first_snapshot.success_rate,
                'current': latest_snapshot.success_rate,
                'improvement': latest_snapshot.success_rate - first_snapshot.success_rate
            },
            'execution_time': {
                'initial': first_snapshot.execution_time,
                'current': latest_snapshot.execution_time,
                'improvement': first_snapshot.execution_time - latest_snapshot.execution_time
            },
            'quality_score': {
                'initial': first_snapshot.quality_score,
                'current': latest_snapshot.quality_score,
                'improvement': latest_snapshot.quality_score - first_snapshot.quality_score
            },
            'efficiency_score': {
                'initial': first_snapshot.efficiency_score,
                'current': latest_snapshot.efficiency_score,
                'improvement': latest_snapshot.efficiency_score - first_snapshot.efficiency_score
            }
        }

        # Calculate overall improvement rate
        improvement_scores = [v['improvement'] for v in improvements.values()]
        overall_improvement = statistics.mean(improvement_scores)

        return {
            'snapshots_count': len(self.performance_snapshots),
            'adaptations_made': len(self.adaptation_history),
            'overall_improvement': overall_improvement,
            'improvements': improvements,
            'latest_health_score': (
                latest_snapshot.success_rate * 0.4 +
                latest_snapshot.quality_score * 0.3 +
                latest_snapshot.efficiency_score * 0.3
            )
        }

    def run_improvement_cycle(self) -> Dict[str, Any]:
        """
        Run a complete improvement cycle.

        Returns:
            Dictionary with cycle results
        """
        # Snapshot current performance
        self.snapshot_performance()

        # Analyze performance
        analysis = self.analyze_performance()

        # Make adaptation decision
        decision = self.make_adaptation_decision(analysis)

        # Apply adaptation if needed
        adapted = False
        if decision:
            adapted = self.apply_adaptation(decision)

        return {
            'timestamp': datetime.now().isoformat(),
            'analysis': analysis,
            'decision': decision.to_dict() if decision else None,
            'adapted': adapted,
            'current_health': analysis.get('health_score', 0.0)
        }


if __name__ == "__main__":
    # Example usage
    print("CCMF RSI Feedback Loop - Example Usage")
    print("=" * 60)

    # Create RSI loop
    rsi_loop = RSIFeedbackLoop()

    # Simulate some operations with feedback
    print("\nSimulating operations and collecting feedback...")
    import random
    import time

    for i in range(20):
        # Simulate operation
        success = random.random() > 0.2  # 80% success rate
        execution_time = random.uniform(0.1, 2.0)
        quality = random.uniform(0.6, 1.0) if success else random.uniform(0.3, 0.6)

        feedback_type = FeedbackType.SUCCESS if success else FeedbackType.FAILURE

        rsi_loop.collect_feedback(
            feedback_type=feedback_type,
            source="test_operation",
            metrics={
                'execution_time': execution_time,
                'quality': quality
            },
            severity=0.3 if success else 0.7,
            message=f"Operation {i+1} {'succeeded' if success else 'failed'}"
        )

        time.sleep(0.01)  # Small delay to simulate real operations

    # Run improvement cycle
    print("\nRunning improvement cycle...")
    cycle_result = rsi_loop.run_improvement_cycle()

    print(f"\nCycle Results:")
    print(f"  Health Score: {cycle_result['current_health']:.2%}")
    print(f"  Adapted: {cycle_result['adapted']}")

    if cycle_result['decision']:
        print(f"\n  Adaptation Decision:")
        print(f"    Strategy: {cycle_result['decision']['strategy']}")
        print(f"    Reason: {cycle_result['decision']['reason']}")
        print(f"    Confidence: {cycle_result['decision']['confidence']:.2%}")

    # Get improvement report
    print("\n" + "-" * 60)
    report = rsi_loop.get_improvement_report()
    print("\nImprovement Report:")
    print(f"  Snapshots: {report.get('snapshots_count', 0)}")
    print(f"  Adaptations: {report.get('adaptations_made', 0)}")
    print(f"  Overall Improvement: {report.get('overall_improvement', 0):.4f}")

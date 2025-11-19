"""
Claude Code Mastery Framework (CCMF) v1.0 - RSI Feedback Loop Module

This module implements recursive self-improvement through execution analysis and pattern optimization.

The RSI (Recursive Self-Improvement) feedback loop continuously analyzes pattern performance,
identifies optimization opportunities, and suggests improvements to maximize Leverage Quotient.

Components:
1. ExecutionAnalyzer - Analyzes pattern execution logs for performance trends
2. PatternOptimizer - Suggests and applies optimizations to patterns
3. RSIFeedbackLoop - Main orchestrator for continuous improvement

This enables Fellou agents to learn from execution history and improve over time.
"""

import json
import logging
import statistics
from collections import defaultdict
from datetime import datetime
from threading import Lock
from typing import Any, Dict, List, Optional, Tuple

from agno.ccmf_constitutional import BasePattern, ExecutionLog

# Configure logging
logger = logging.getLogger(__name__)


class ExecutionAnalyzer:
    """
    Analyzes pattern execution logs for performance trends and bottlenecks.

    This analyzer examines execution history to identify:
    - Success/failure rates
    - Average LQ scores and trends
    - Performance bottlenecks
    - Improvement opportunities

    The analysis feeds into the RSI loop for continuous optimization.
    """

    def __init__(self):
        """Initialize the execution analyzer."""
        self.analysis_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_lock = Lock()
        logger.info("ExecutionAnalyzer initialized")

    def analyze_pattern_performance(self, pattern: BasePattern) -> Dict[str, Any]:
        """
        Analyze comprehensive performance metrics for a pattern.

        Args:
            pattern: Pattern to analyze

        Returns:
            Dictionary containing:
                - pattern_id: Pattern identifier
                - total_executions: Total execution count
                - successful_executions: Successful execution count
                - failed_executions: Failed execution count
                - success_rate: Success rate percentage
                - avg_lq: Average Leverage Quotient
                - avg_duration: Average execution duration
                - min_duration: Minimum duration
                - max_duration: Maximum duration
                - lq_trend: LQ trend ("improving", "declining", "stable")
                - duration_trend: Duration trend
                - recent_failures: List of recent failure reasons
                - recommendations: List of improvement recommendations
        """
        logger.info("Analyzing performance for pattern: %s", pattern.pattern_id)

        executions = pattern.execution_logs
        if not executions:
            return {
                "pattern_id": pattern.pattern_id,
                "total_executions": 0,
                "analysis_status": "insufficient_data",
                "recommendations": ["Execute pattern to gather performance data"]
            }

        # Basic metrics
        total = len(executions)
        successful = [e for e in executions if e.success]
        failed = [e for e in executions if not e.success]

        success_rate = (len(successful) / total * 100) if total > 0 else 0.0

        # LQ metrics
        lq_scores = [e.lq_score for e in successful if e.lq_score > 0]
        avg_lq = statistics.mean(lq_scores) if lq_scores else 0.0

        # Duration metrics
        durations = [e.duration for e in executions]
        avg_duration = statistics.mean(durations) if durations else 0.0
        min_duration = min(durations) if durations else 0.0
        max_duration = max(durations) if durations else 0.0

        # Trend analysis
        lq_trend = self._analyze_trend([e.lq_score for e in successful[-10:]])
        duration_trend = self._analyze_trend(durations[-10:], inverse=True)

        # Recent failures
        recent_failures = [
            {
                "timestamp": e.timestamp.isoformat(),
                "error": e.error
            }
            for e in failed[-5:]
        ]

        # Generate recommendations
        recommendations = self._generate_recommendations(
            success_rate=success_rate,
            avg_lq=avg_lq,
            lq_trend=lq_trend,
            duration_trend=duration_trend,
            failed_count=len(failed)
        )

        analysis = {
            "pattern_id": pattern.pattern_id,
            "pattern_name": pattern.pattern_name,
            "total_executions": total,
            "successful_executions": len(successful),
            "failed_executions": len(failed),
            "success_rate": success_rate,
            "avg_lq": avg_lq,
            "avg_duration": avg_duration,
            "min_duration": min_duration,
            "max_duration": max_duration,
            "lq_trend": lq_trend,
            "duration_trend": duration_trend,
            "recent_failures": recent_failures,
            "recommendations": recommendations,
            "analysis_timestamp": datetime.now().isoformat()
        }

        # Cache analysis
        with self.cache_lock:
            self.analysis_cache[pattern.pattern_id] = analysis

        logger.debug("Analysis complete for %s: success_rate=%.2f%%, avg_lq=%.2f",
                    pattern.pattern_id, success_rate, avg_lq)

        return analysis

    def identify_bottlenecks(self, patterns: List[BasePattern]) -> List[Dict[str, Any]]:
        """
        Identify performance bottlenecks across multiple patterns.

        Bottlenecks are identified based on:
        - Low success rates (<80%)
        - Declining LQ trends
        - High average durations
        - Frequent failures

        Args:
            patterns: List of patterns to analyze

        Returns:
            List of bottleneck descriptions sorted by severity
        """
        logger.info("Identifying bottlenecks across %d patterns", len(patterns))

        bottlenecks = []

        for pattern in patterns:
            analysis = self.analyze_pattern_performance(pattern)

            if analysis.get("total_executions", 0) == 0:
                continue

            # Check for various bottleneck conditions
            severity_score = 0
            issues = []

            # Low success rate
            success_rate = analysis.get("success_rate", 100)
            if success_rate < 80:
                severity_score += (80 - success_rate) / 10
                issues.append(f"Low success rate: {success_rate:.1f}%")

            # Declining LQ
            if analysis.get("lq_trend") == "declining":
                severity_score += 3
                issues.append("Declining LQ trend")

            # High failure rate
            failed = analysis.get("failed_executions", 0)
            if failed > 5:
                severity_score += failed / 2
                issues.append(f"High failure count: {failed}")

            # Slow performance
            avg_duration = analysis.get("avg_duration", 0)
            if avg_duration > 5.0:  # >5 seconds
                severity_score += avg_duration / 5
                issues.append(f"Slow performance: {avg_duration:.2f}s avg")

            if severity_score > 0:
                bottlenecks.append({
                    "pattern_id": pattern.pattern_id,
                    "pattern_name": pattern.pattern_name,
                    "severity_score": severity_score,
                    "issues": issues,
                    "analysis": analysis
                })

        # Sort by severity
        bottlenecks.sort(key=lambda x: x["severity_score"], reverse=True)

        logger.info("Identified %d bottlenecks", len(bottlenecks))

        return bottlenecks

    def calculate_improvement_opportunities(self, pattern: BasePattern) -> float:
        """
        Calculate potential LQ gain from optimizing a pattern.

        This estimates how much the LQ could improve based on:
        - Current vs. theoretical maximum LQ
        - Success rate improvement potential
        - Duration optimization potential

        Args:
            pattern: Pattern to evaluate

        Returns:
            Potential LQ improvement score (0.0 to 10.0)
        """
        analysis = self.analyze_pattern_performance(pattern)

        if analysis.get("total_executions", 0) == 0:
            return 0.0

        current_lq = analysis.get("avg_lq", 0)
        success_rate = analysis.get("success_rate", 100) / 100

        # Theoretical maximum LQ (assuming pattern could achieve)
        theoretical_max = 10.0

        # Calculate improvement potential
        lq_gap = theoretical_max - current_lq
        success_gap = 1.0 - success_rate

        # Weight factors
        lq_improvement = lq_gap * 0.7  # 70% from LQ optimization
        success_improvement = success_gap * theoretical_max * 0.3  # 30% from success rate

        total_opportunity = lq_improvement + success_improvement

        logger.debug("Improvement opportunity for %s: %.2f (LQ gap: %.2f, success gap: %.2f%%)",
                    pattern.pattern_id, total_opportunity, lq_gap, success_gap * 100)

        return total_opportunity

    def _analyze_trend(self, values: List[float], inverse: bool = False) -> str:
        """
        Analyze trend in a series of values.

        Args:
            values: List of numeric values
            inverse: If True, decreasing is good (e.g., for durations)

        Returns:
            "improving", "declining", or "stable"
        """
        if len(values) < 3:
            return "stable"

        # Simple linear regression slope
        n = len(values)
        x = list(range(n))
        x_mean = statistics.mean(x)
        y_mean = statistics.mean(values)

        numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return "stable"

        slope = numerator / denominator

        # Determine trend
        threshold = 0.01
        if inverse:
            slope = -slope

        if slope > threshold:
            return "improving"
        elif slope < -threshold:
            return "declining"
        else:
            return "stable"

    def _generate_recommendations(
        self,
        success_rate: float,
        avg_lq: float,
        lq_trend: str,
        duration_trend: str,
        failed_count: int
    ) -> List[str]:
        """
        Generate optimization recommendations based on metrics.

        Args:
            success_rate: Current success rate percentage
            avg_lq: Average LQ score
            lq_trend: LQ trend direction
            duration_trend: Duration trend direction
            failed_count: Number of failures

        Returns:
            List of recommendation strings
        """
        recommendations = []

        # Success rate recommendations
        if success_rate < 80:
            recommendations.append("Critical: Improve error handling to increase success rate")
        elif success_rate < 95:
            recommendations.append("Optimize input validation to reduce failures")

        # LQ recommendations
        if avg_lq < 3.0:
            recommendations.append("Low LQ: Consider redesigning pattern for better efficiency")
        elif avg_lq < 6.0:
            recommendations.append("Moderate LQ: Optimize subprocess calls and timeout values")

        # Trend recommendations
        if lq_trend == "declining":
            recommendations.append("Warning: LQ trending downward - investigate recent changes")

        if duration_trend == "declining":
            recommendations.append("Warning: Execution time increasing - profile for bottlenecks")

        # Failure recommendations
        if failed_count > 10:
            recommendations.append("High failure count: Review error logs and add fallback strategies")

        # Positive feedback
        if success_rate >= 95 and avg_lq >= 7.0:
            recommendations.append("Excellent performance: Pattern is well-optimized")

        return recommendations if recommendations else ["Pattern performance is acceptable"]


class PatternOptimizer:
    """
    Suggests and applies optimizations to patterns based on analysis.

    This optimizer uses execution history to:
    - Suggest concrete optimization strategies
    - Adjust timeout values dynamically
    - Reorder search paths by success frequency
    - Predict expected LQ improvements
    """

    def __init__(self, analyzer: Optional[ExecutionAnalyzer] = None):
        """
        Initialize the pattern optimizer.

        Args:
            analyzer: ExecutionAnalyzer instance (creates new if None)
        """
        self.analyzer = analyzer if analyzer else ExecutionAnalyzer()
        logger.info("PatternOptimizer initialized")

    def suggest_optimizations(
        self,
        pattern: BasePattern,
        analysis: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate concrete optimization suggestions for a pattern.

        Args:
            pattern: Pattern to optimize
            analysis: Pre-computed analysis (computes if None)

        Returns:
            List of optimization suggestions with:
                - optimization_type: Type of optimization
                - description: Human-readable description
                - expected_lq_improvement: Estimated LQ gain
                - implementation_complexity: "low", "medium", "high"
                - priority: Priority score (higher = more important)
        """
        if analysis is None:
            analysis = self.analyzer.analyze_pattern_performance(pattern)

        logger.info("Generating optimizations for pattern: %s", pattern.pattern_id)

        optimizations = []

        # Timeout optimization
        if analysis.get("avg_duration", 0) > 0:
            timeout_opt = {
                "optimization_type": "timeout_adjustment",
                "description": "Adjust timeout values based on historical execution times",
                "expected_lq_improvement": 0.5,
                "implementation_complexity": "low",
                "priority": 7,
                "details": self.optimize_timeout_values(pattern)
            }
            optimizations.append(timeout_opt)

        # Error handling improvement
        success_rate = analysis.get("success_rate", 100)
        if success_rate < 90:
            error_opt = {
                "optimization_type": "error_handling",
                "description": "Add retry logic and fallback strategies for common failures",
                "expected_lq_improvement": (100 - success_rate) / 10,
                "implementation_complexity": "medium",
                "priority": 10,
                "details": {
                    "current_success_rate": success_rate,
                    "target_success_rate": 95.0,
                    "recent_failures": analysis.get("recent_failures", [])
                }
            }
            optimizations.append(error_opt)

        # Performance optimization
        avg_duration = analysis.get("avg_duration", 0)
        if avg_duration > 2.0:
            perf_opt = {
                "optimization_type": "performance",
                "description": "Reduce execution time through subprocess optimization",
                "expected_lq_improvement": min(avg_duration / 2, 2.0),
                "implementation_complexity": "medium",
                "priority": 8,
                "details": {
                    "current_avg_duration": avg_duration,
                    "target_duration": avg_duration * 0.7,
                    "optimization_areas": ["subprocess_calls", "validation_overhead"]
                }
            }
            optimizations.append(perf_opt)

        # LQ improvement
        avg_lq = analysis.get("avg_lq", 0)
        if avg_lq < 7.0:
            lq_opt = {
                "optimization_type": "lq_enhancement",
                "description": "Improve Leverage Quotient through efficiency gains",
                "expected_lq_improvement": (7.0 - avg_lq) * 0.5,
                "implementation_complexity": "high",
                "priority": 6,
                "details": {
                    "current_avg_lq": avg_lq,
                    "target_lq": 7.0,
                    "focus_areas": ["reduce_cost", "increase_efficiency"]
                }
            }
            optimizations.append(lq_opt)

        # Sort by priority
        optimizations.sort(key=lambda x: x["priority"], reverse=True)

        logger.info("Generated %d optimization suggestions for %s",
                   len(optimizations), pattern.pattern_id)

        return optimizations

    def optimize_timeout_values(self, pattern: BasePattern) -> Dict[str, Any]:
        """
        Calculate optimal timeout values based on historical performance.

        Analyzes execution durations and suggests timeout values that:
        - Cover 95th percentile of execution times
        - Add safety margin for variance
        - Prevent unnecessary waiting

        Args:
            pattern: Pattern to optimize

        Returns:
            Dictionary with current and recommended timeout values
        """
        executions = pattern.execution_logs
        if len(executions) < 5:
            return {
                "status": "insufficient_data",
                "message": "Need at least 5 executions to optimize timeouts"
            }

        # Separate by success/failure
        successful = [e for e in executions if e.success]

        if not successful:
            return {
                "status": "no_successful_executions",
                "message": "Cannot optimize without successful executions"
            }

        durations = [e.duration for e in successful]

        # Calculate statistics
        avg_duration = statistics.mean(durations)
        median_duration = statistics.median(durations)

        # Calculate 95th percentile (for timeout)
        sorted_durations = sorted(durations)
        percentile_95_idx = int(len(sorted_durations) * 0.95)
        percentile_95 = sorted_durations[percentile_95_idx] if percentile_95_idx < len(sorted_durations) else sorted_durations[-1]

        # Recommended timeout: 95th percentile + 50% safety margin
        recommended_timeout = percentile_95 * 1.5

        logger.debug("Timeout optimization for %s: avg=%.2fs, p95=%.2fs, recommended=%.2fs",
                    pattern.pattern_id, avg_duration, percentile_95, recommended_timeout)

        return {
            "status": "success",
            "current_stats": {
                "avg_duration": avg_duration,
                "median_duration": median_duration,
                "95th_percentile": percentile_95,
                "max_duration": max(durations),
                "min_duration": min(durations)
            },
            "recommended_timeout": recommended_timeout,
            "safety_margin": 1.5,
            "expected_coverage": "95% of executions",
            "sample_size": len(successful)
        }

    def optimize_search_order(self, search_log: List[Dict[str, Any]]) -> List[str]:
        """
        Reorder search paths by success frequency to optimize search efficiency.

        Analyzes search history to identify which paths succeed most often,
        then reorders to check high-probability paths first.

        Args:
            search_log: List of search attempt dictionaries from KnownPathSearchPattern

        Returns:
            List of paths ordered by success probability (highest first)
        """
        if not search_log:
            return []

        # Count successes per path
        path_stats = defaultdict(lambda: {"attempts": 0, "successes": 0})

        for attempt in search_log:
            path = attempt.get("path")
            if not path:
                continue

            path_stats[path]["attempts"] += 1
            if attempt.get("exists", False):
                path_stats[path]["successes"] += 1

        # Calculate success rate for each path
        path_scores = []
        for path, stats in path_stats.items():
            success_rate = (stats["successes"] / stats["attempts"]) if stats["attempts"] > 0 else 0
            path_scores.append({
                "path": path,
                "success_rate": success_rate,
                "attempts": stats["attempts"],
                "successes": stats["successes"]
            })

        # Sort by success rate (descending), then by attempt count (descending)
        path_scores.sort(key=lambda x: (x["success_rate"], x["attempts"]), reverse=True)

        optimized_order = [p["path"] for p in path_scores]

        logger.info("Optimized search order for %d paths (top: %s with %.1f%% success)",
                   len(optimized_order),
                   optimized_order[0] if optimized_order else "none",
                   path_scores[0]["success_rate"] * 100 if path_scores else 0)

        return optimized_order


class RSIFeedbackLoop:
    """
    Main orchestrator for recursive self-improvement feedback loop.

    The RSI feedback loop continuously:
    1. Tracks pattern execution
    2. Analyzes performance trends
    3. Identifies optimization opportunities
    4. Suggests and logs improvements
    5. Exports comprehensive reports

    This enables autonomous improvement of the CCMF framework over time.
    """

    def __init__(self):
        """Initialize the RSI feedback loop."""
        self.patterns: Dict[str, BasePattern] = {}
        self.analyzer = ExecutionAnalyzer()
        self.optimizer = PatternOptimizer(self.analyzer)
        self.improvement_log: List[Dict[str, Any]] = []

        self.cycle_count = 0
        self.total_optimizations = 0

        self.lock = Lock()

        logger.info("RSIFeedbackLoop initialized")

    def register_pattern(self, pattern: BasePattern) -> None:
        """
        Register a pattern for tracking and optimization.

        Args:
            pattern: Pattern to register
        """
        with self.lock:
            self.patterns[pattern.pattern_id] = pattern
            logger.info("Registered pattern: %s (%s)",
                       pattern.pattern_id, pattern.pattern_name)

    def unregister_pattern(self, pattern_id: str) -> bool:
        """
        Unregister a pattern from tracking.

        Args:
            pattern_id: ID of pattern to unregister

        Returns:
            True if unregistered, False if not found
        """
        with self.lock:
            if pattern_id in self.patterns:
                del self.patterns[pattern_id]
                logger.info("Unregistered pattern: %s", pattern_id)
                return True
            return False

    def run_improvement_cycle(self) -> Dict[str, Any]:
        """
        Run a complete improvement cycle across all registered patterns.

        This cycle:
        1. Analyzes all pattern performance
        2. Identifies bottlenecks
        3. Generates optimization suggestions
        4. Logs improvement opportunities
        5. Returns comprehensive results

        Returns:
            Dictionary containing:
                - cycle_number: Current cycle number
                - timestamp: Cycle execution time
                - patterns_analyzed: Number of patterns analyzed
                - bottlenecks_identified: List of bottlenecks
                - total_optimizations_suggested: Total optimization count
                - optimizations_by_pattern: Optimizations per pattern
                - improvement_summary: Summary statistics
        """
        with self.lock:
            self.cycle_count += 1
            cycle_num = self.cycle_count

        logger.info("Starting RSI improvement cycle #%d", cycle_num)
        cycle_start = datetime.now()

        patterns_list = list(self.patterns.values())

        if not patterns_list:
            logger.warning("No patterns registered for improvement cycle")
            return {
                "cycle_number": cycle_num,
                "timestamp": cycle_start.isoformat(),
                "patterns_analyzed": 0,
                "status": "no_patterns_registered"
            }

        # Analyze all patterns
        analyses = {}
        for pattern in patterns_list:
            analyses[pattern.pattern_id] = self.analyzer.analyze_pattern_performance(pattern)

        # Identify bottlenecks
        bottlenecks = self.analyzer.identify_bottlenecks(patterns_list)

        # Generate optimizations for each pattern
        optimizations_by_pattern = {}
        total_optimizations = 0

        for pattern in patterns_list:
            analysis = analyses[pattern.pattern_id]
            opts = self.optimizer.suggest_optimizations(pattern, analysis)
            optimizations_by_pattern[pattern.pattern_id] = opts
            total_optimizations += len(opts)

        # Calculate improvement opportunities
        opportunities = {}
        for pattern in patterns_list:
            opp = self.analyzer.calculate_improvement_opportunities(pattern)
            opportunities[pattern.pattern_id] = opp

        # Create improvement summary
        improvement_summary = {
            "total_patterns": len(patterns_list),
            "patterns_with_data": sum(1 for a in analyses.values() if a.get("total_executions", 0) > 0),
            "average_success_rate": statistics.mean([a.get("success_rate", 0) for a in analyses.values()]) if analyses else 0,
            "average_lq": statistics.mean([a.get("avg_lq", 0) for a in analyses.values() if a.get("avg_lq", 0) > 0]) or 0,
            "total_bottlenecks": len(bottlenecks),
            "total_improvement_opportunity": sum(opportunities.values())
        }

        # Log improvement cycle
        cycle_result = {
            "cycle_number": cycle_num,
            "timestamp": cycle_start.isoformat(),
            "duration": (datetime.now() - cycle_start).total_seconds(),
            "patterns_analyzed": len(patterns_list),
            "bottlenecks_identified": bottlenecks,
            "total_optimizations_suggested": total_optimizations,
            "optimizations_by_pattern": optimizations_by_pattern,
            "improvement_opportunities": opportunities,
            "improvement_summary": improvement_summary,
            "analyses": analyses
        }

        with self.lock:
            self.improvement_log.append(cycle_result)
            self.total_optimizations += total_optimizations

        logger.info("Completed RSI cycle #%d: %d patterns, %d bottlenecks, %d optimizations",
                   cycle_num, len(patterns_list), len(bottlenecks), total_optimizations)

        return cycle_result

    def get_improvement_history(
        self,
        limit: Optional[int] = None,
        pattern_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get historical improvement cycle data.

        Args:
            limit: Maximum number of cycles to return (most recent first)
            pattern_id: Filter by specific pattern ID

        Returns:
            List of improvement cycle results
        """
        with self.lock:
            history = list(reversed(self.improvement_log))  # Most recent first

        if pattern_id:
            # Filter cycles that include this pattern
            history = [
                cycle for cycle in history
                if pattern_id in cycle.get("analyses", {})
            ]

        if limit:
            history = history[:limit]

        return history

    def export_rsi_report(self, include_full_logs: bool = False) -> str:
        """
        Generate comprehensive RSI report in JSON format.

        Args:
            include_full_logs: Include complete execution logs (can be large)

        Returns:
            JSON-formatted report string
        """
        logger.info("Generating RSI report (include_logs=%s)", include_full_logs)

        with self.lock:
            patterns_summary = {}
            for pattern_id, pattern in self.patterns.items():
                analysis = self.analyzer.analyze_pattern_performance(pattern)

                pattern_data = {
                    "pattern_id": pattern.pattern_id,
                    "pattern_name": pattern.pattern_name,
                    "version": pattern.version,
                    "constitutional_requirements": pattern.constitutional_requirements,
                    "performance": {
                        "total_executions": pattern.total_executions,
                        "successful_executions": pattern.successful_executions,
                        "failed_executions": pattern.failed_executions,
                        "success_rate": analysis.get("success_rate", 0),
                        "average_lq": pattern.average_lq,
                        "avg_duration": analysis.get("avg_duration", 0)
                    },
                    "trends": {
                        "lq_trend": analysis.get("lq_trend", "stable"),
                        "duration_trend": analysis.get("duration_trend", "stable")
                    },
                    "recommendations": analysis.get("recommendations", [])
                }

                if include_full_logs:
                    pattern_data["execution_logs"] = [
                        {
                            "timestamp": log.timestamp.isoformat(),
                            "success": log.success,
                            "duration": log.duration,
                            "lq_score": log.lq_score,
                            "error": log.error
                        }
                        for log in pattern.execution_logs[-100:]  # Last 100 logs
                    ]

                patterns_summary[pattern_id] = pattern_data

            report = {
                "report_type": "CCMF_RSI_Report",
                "report_version": "1.0.0",
                "generated_at": datetime.now().isoformat(),
                "rsi_loop_statistics": {
                    "total_cycles_run": self.cycle_count,
                    "total_patterns_registered": len(self.patterns),
                    "total_optimizations_suggested": self.total_optimizations
                },
                "patterns": patterns_summary,
                "improvement_history": self.get_improvement_history(limit=10),
                "overall_metrics": {
                    "total_executions": sum(p.total_executions for p in self.patterns.values()),
                    "total_successful": sum(p.successful_executions for p in self.patterns.values()),
                    "overall_success_rate": self._calculate_overall_success_rate(),
                    "average_lq_all_patterns": self._calculate_average_lq()
                }
            }

        return json.dumps(report, indent=2)

    def _calculate_overall_success_rate(self) -> float:
        """Calculate overall success rate across all patterns."""
        total_executions = sum(p.total_executions for p in self.patterns.values())
        total_successful = sum(p.successful_executions for p in self.patterns.values())

        if total_executions == 0:
            return 0.0

        return (total_successful / total_executions) * 100

    def _calculate_average_lq(self) -> float:
        """Calculate average LQ across all patterns."""
        lq_scores = [p.average_lq for p in self.patterns.values() if p.average_lq > 0]
        return statistics.mean(lq_scores) if lq_scores else 0.0

    def get_summary(self) -> Dict[str, Any]:
        """
        Get a quick summary of RSI loop status.

        Returns:
            Dictionary with current status
        """
        return {
            "cycles_run": self.cycle_count,
            "patterns_registered": len(self.patterns),
            "total_optimizations": self.total_optimizations,
            "overall_success_rate": self._calculate_overall_success_rate(),
            "average_lq": self._calculate_average_lq()
        }

    def __repr__(self) -> str:
        """String representation of RSI loop."""
        return (f"<RSIFeedbackLoop cycles={self.cycle_count} "
                f"patterns={len(self.patterns)} "
                f"optimizations={self.total_optimizations}>")


# Module-level convenience functions
def create_rsi_loop() -> RSIFeedbackLoop:
    """
    Factory function to create a new RSIFeedbackLoop instance.

    Returns:
        RSIFeedbackLoop instance
    """
    return RSIFeedbackLoop()


# Module metadata
__version__ = "1.0.0"
__author__ = "CCMF Contributors"
__description__ = "CCMF RSI Feedback Loop - Recursive self-improvement through execution analysis"

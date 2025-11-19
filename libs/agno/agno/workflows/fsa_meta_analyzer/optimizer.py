"""
FSA Optimizer - Generates optimization recommendations and automated improvements.

Analyzes FSA structure, validation issues, performance profiles, and quality metrics
to generate actionable optimization recommendations and automated code improvements.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from agno.workflows.fsa_meta_analyzer.dependency_analyzer import DependencyAnalysisReport
from agno.workflows.fsa_meta_analyzer.pattern_analyzer import PatternAnalysisReport
from agno.workflows.fsa_meta_analyzer.profiler import PerformanceAnalysis
from agno.workflows.fsa_meta_analyzer.quality_metrics import QualityMetrics
from agno.workflows.fsa_meta_analyzer.static_analyzer import FSAStructure
from agno.workflows.fsa_meta_analyzer.validator import ValidationReport


@dataclass
class OptimizationRecommendation:
    """Represents a single optimization recommendation."""

    category: str  # 'performance', 'structure', 'quality', 'security', 'maintainability'
    priority: str  # 'critical', 'high', 'medium', 'low'
    title: str
    description: str
    impact: str  # Expected impact of implementing the recommendation
    effort: str  # 'low', 'medium', 'high' - estimated effort to implement
    code_example: Optional[str] = None
    affected_states: List[str] = field(default_factory=list)


@dataclass
class OptimizationPlan:
    """Complete optimization plan for an FSA."""

    workflow_name: str
    overall_health: str  # 'excellent', 'good', 'fair', 'poor', 'critical'
    health_score: float  # 0-100
    recommendations: List[OptimizationRecommendation] = field(default_factory=list)
    quick_wins: List[OptimizationRecommendation] = field(default_factory=list)
    long_term_improvements: List[OptimizationRecommendation] = field(default_factory=list)
    automated_fixes: List[str] = field(default_factory=list)
    summary: str = ''


class FSAOptimizer:
    """Generates optimization recommendations for FSAs."""

    def __init__(self):
        self.recommendations: List[OptimizationRecommendation] = []

    def generate_optimization_plan(
        self,
        fsa: FSAStructure,
        validation_report: ValidationReport,
        quality_metrics: QualityMetrics,
        performance_analysis: Optional[PerformanceAnalysis] = None,
        pattern_report: Optional[PatternAnalysisReport] = None,
        dependency_report: Optional[DependencyAnalysisReport] = None,
    ) -> OptimizationPlan:
        """
        Generate comprehensive optimization plan.

        Args:
            fsa: The FSA structure
            validation_report: Validation results
            quality_metrics: Quality metrics
            performance_analysis: Optional performance analysis
            pattern_report: Optional pattern analysis
            dependency_report: Optional dependency analysis

        Returns:
            OptimizationPlan with prioritized recommendations
        """
        plan = OptimizationPlan(workflow_name=fsa.workflow_name)

        # Generate recommendations from different sources
        self._analyze_validation_issues(validation_report, plan)
        self._analyze_quality_metrics(quality_metrics, plan)
        self._analyze_performance(fsa, performance_analysis, plan)
        self._analyze_patterns(pattern_report, plan)
        self._analyze_dependencies(dependency_report, plan)
        self._analyze_structure(fsa, plan)
        self._analyze_security(fsa, plan)

        # Calculate overall health
        plan.health_score = self._calculate_health_score(
            validation_report, quality_metrics
        )
        plan.overall_health = self._get_health_status(plan.health_score)

        # Categorize recommendations
        self._categorize_recommendations(plan)

        # Generate summary
        plan.summary = self._generate_summary(plan)

        return plan

    def _analyze_validation_issues(
        self, validation_report: ValidationReport, plan: OptimizationPlan
    ):
        """Generate recommendations from validation issues."""
        # Critical issues
        for issue in validation_report.issues:
            if issue.severity.value == 'critical':
                rec = OptimizationRecommendation(
                    category='structure',
                    priority='critical',
                    title=f'Fix Critical Issue: {issue.category}',
                    description=issue.message,
                    impact='Required for workflow to function correctly',
                    effort='high' if 'refactor' in issue.message.lower() else 'medium',
                    affected_states=[issue.state] if issue.state else [],
                )
                if issue.recommendation:
                    rec.description += f'\n\nRecommendation: {issue.recommendation}'
                plan.recommendations.append(rec)

        # Error issues
        for issue in validation_report.issues:
            if issue.severity.value == 'error':
                rec = OptimizationRecommendation(
                    category='quality',
                    priority='high',
                    title=f'Fix Error: {issue.category}',
                    description=issue.message,
                    impact='Improves reliability and correctness',
                    effort='medium',
                    affected_states=[issue.state] if issue.state else [],
                )
                if issue.recommendation:
                    rec.description += f'\n\nRecommendation: {issue.recommendation}'
                plan.recommendations.append(rec)

    def _analyze_quality_metrics(
        self, quality_metrics: QualityMetrics, plan: OptimizationPlan
    ):
        """Generate recommendations from quality metrics."""
        # Low maintainability
        if quality_metrics.maintainability_index < 60:
            plan.recommendations.append(
                OptimizationRecommendation(
                    category='maintainability',
                    priority='high',
                    title='Improve Maintainability',
                    description=f'Maintainability index is {quality_metrics.maintainability_index:.0f}/100. '
                    f'Reduce complexity and improve code organization.',
                    impact='Easier to maintain and extend the workflow',
                    effort='high',
                )
            )

        # Low reliability
        if quality_metrics.reliability_score < 70:
            plan.recommendations.append(
                OptimizationRecommendation(
                    category='quality',
                    priority='high',
                    title='Improve Reliability',
                    description=f'Reliability score is {quality_metrics.reliability_score:.0f}/100. '
                    f'Add error handling and ensure all paths lead to proper exits.',
                    impact='Reduces failures and improves user experience',
                    effort='medium',
                    code_example="""
try:
    result = agent.run(input)
except Exception as e:
    logger.error(f"Agent failed: {e}")
    return RunResponse(content="Error occurred", error=str(e))
""",
                )
            )

        # Antipatterns
        if quality_metrics.antipatterns_detected:
            for antipattern in quality_metrics.antipatterns_detected:
                plan.recommendations.append(
                    OptimizationRecommendation(
                        category='structure',
                        priority='medium',
                        title='Fix Antipattern',
                        description=antipattern,
                        impact='Improves code quality and maintainability',
                        effort='medium',
                    )
                )

        # Low test coverage
        if quality_metrics.type_annotation_coverage < 80:
            plan.recommendations.append(
                OptimizationRecommendation(
                    category='quality',
                    priority='low',
                    title='Add Type Annotations',
                    description=f'Type annotation coverage is {quality_metrics.type_annotation_coverage:.0f}%. '
                    f'Add type hints to improve code clarity and catch errors early.',
                    impact='Better IDE support and early error detection',
                    effort='low',
                    code_example='def run(self, topic: str, max_results: int = 10) -> Iterator[RunResponse]:',
                )
            )

    def _analyze_performance(
        self,
        fsa: FSAStructure,
        performance_analysis: Optional[PerformanceAnalysis],
        plan: OptimizationPlan,
    ):
        """Generate performance optimization recommendations."""
        if not performance_analysis:
            return

        # Performance score
        if performance_analysis.performance_score < 70:
            plan.recommendations.append(
                OptimizationRecommendation(
                    category='performance',
                    priority='high',
                    title='Optimize Performance',
                    description=f'Performance score is {performance_analysis.performance_score:.0f}/100. '
                    f'Review bottlenecks and optimize critical paths.',
                    impact='Faster execution and better resource utilization',
                    effort='high',
                )
            )

        # Bottleneck states
        if performance_analysis.profile.bottleneck_states:
            for state in performance_analysis.profile.bottleneck_states[:3]:  # Top 3
                plan.recommendations.append(
                    OptimizationRecommendation(
                        category='performance',
                        priority='medium',
                        title=f'Optimize Bottleneck State: {state}',
                        description='State identified as performance bottleneck. '
                        'Consider caching, parallelization, or optimization.',
                        impact='Reduces overall execution time',
                        effort='medium',
                        affected_states=[state],
                        code_example="""
# Parallelize independent agent calls
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor() as executor:
    future1 = executor.submit(agent1.run, input1)
    future2 = executor.submit(agent2.run, input2)
    result1, result2 = future1.result(), future2.result()
""",
                    )
                )

    def _analyze_patterns(
        self, pattern_report: Optional[PatternAnalysisReport], plan: OptimizationPlan
    ):
        """Generate recommendations from pattern analysis."""
        if not pattern_report:
            return

        # Antipatterns
        for antipattern in pattern_report.antipatterns:
            plan.recommendations.append(
                OptimizationRecommendation(
                    category='structure',
                    priority='medium' if antipattern.confidence > 0.8 else 'low',
                    title=f'Fix {antipattern.pattern_type.value} Antipattern',
                    description=antipattern.description,
                    impact='Improves code structure and maintainability',
                    effort='medium',
                    affected_states=antipattern.states_involved,
                )
            )

        # Reusable patterns
        if pattern_report.reusable_patterns:
            plan.recommendations.append(
                OptimizationRecommendation(
                    category='maintainability',
                    priority='low',
                    title='Extract Reusable Patterns',
                    description=f'Found {len(pattern_report.reusable_patterns)} patterns that could be extracted '
                    f'into reusable components or sub-workflows.',
                    impact='Improved code reuse and consistency',
                    effort='high',
                )
            )

    def _analyze_dependencies(
        self, dependency_report: Optional[DependencyAnalysisReport], plan: OptimizationPlan
    ):
        """Generate recommendations from dependency analysis."""
        if not dependency_report:
            return

        # Circular dependencies
        if dependency_report.circular_dependencies > 0:
            plan.recommendations.append(
                OptimizationRecommendation(
                    category='structure',
                    priority='critical',
                    title='Break Circular Dependencies',
                    description=f'Found {dependency_report.circular_dependencies} circular dependencies. '
                    f'These can cause maintenance issues and unexpected behavior.',
                    impact='Prevents circular dependency issues',
                    effort='high',
                )
            )

        # High coupling
        if dependency_report.coupling_score < 60:
            plan.recommendations.append(
                OptimizationRecommendation(
                    category='structure',
                    priority='medium',
                    title='Reduce Coupling',
                    description=f'Coupling score is {dependency_report.coupling_score:.0f}/100. '
                    f'Reduce dependencies between components.',
                    impact='More modular and maintainable code',
                    effort='high',
                )
            )

    def _analyze_structure(self, fsa: FSAStructure, plan: OptimizationPlan):
        """Analyze structural aspects of the FSA."""
        # High complexity
        complexity = fsa.complexity_metrics.get('cyclomatic_complexity', 0)
        if complexity > 20:
            plan.recommendations.append(
                OptimizationRecommendation(
                    category='structure',
                    priority='high',
                    title='Reduce Cyclomatic Complexity',
                    description=f'Cyclomatic complexity is {complexity}. '
                    f'Break down complex logic into smaller functions or sub-workflows.',
                    impact='Easier to understand, test, and maintain',
                    effort='high',
                )
            )

        # Too many states
        state_count = fsa.complexity_metrics.get('total_states', 0)
        if state_count > 30:
            plan.recommendations.append(
                OptimizationRecommendation(
                    category='structure',
                    priority='medium',
                    title='Consider Workflow Decomposition',
                    description=f'Workflow has {state_count} states. '
                    f'Consider breaking into multiple smaller workflows.',
                    impact='Improved modularity and reusability',
                    effort='high',
                )
            )

    def _analyze_security(self, fsa: FSAStructure, plan: OptimizationPlan):
        """Analyze security aspects."""
        # Check for sensitive data handling
        sensitive_keywords = ['password', 'token', 'api_key', 'secret', 'credential']

        for state_name, state in fsa.states.items():
            for var in state.variables_written:
                if any(keyword in var.lower() for keyword in sensitive_keywords):
                    plan.recommendations.append(
                        OptimizationRecommendation(
                            category='security',
                            priority='high',
                            title='Secure Sensitive Data',
                            description=f'State "{state_name}" handles potentially sensitive data: {var}. '
                            f'Ensure proper encryption and access controls.',
                            impact='Prevents security vulnerabilities',
                            effort='low',
                            affected_states=[state_name],
                            code_example="""
# Use environment variables for secrets
import os
api_key = os.getenv('API_KEY')

# Don't log sensitive data
logger.info(f"Processing request")  # Good
logger.info(f"API key: {api_key}")  # Bad!
""",
                        )
                    )

    def _calculate_health_score(
        self, validation_report: ValidationReport, quality_metrics: QualityMetrics
    ) -> float:
        """Calculate overall health score."""
        score = quality_metrics.overall_quality_score

        # Penalize for validation issues
        score -= validation_report.critical_count * 10
        score -= validation_report.error_count * 5
        score -= validation_report.warning_count * 2

        return max(0.0, min(100.0, score))

    def _get_health_status(self, score: float) -> str:
        """Get health status from score."""
        if score >= 90:
            return 'excellent'
        elif score >= 75:
            return 'good'
        elif score >= 60:
            return 'fair'
        elif score >= 40:
            return 'poor'
        else:
            return 'critical'

    def _categorize_recommendations(self, plan: OptimizationPlan):
        """Categorize recommendations into quick wins and long-term improvements."""
        for rec in plan.recommendations:
            # Quick wins: high impact, low effort
            if rec.effort == 'low' and rec.priority in ['high', 'critical']:
                plan.quick_wins.append(rec)
            # Long-term: high effort, high impact
            elif rec.effort == 'high' and rec.priority in ['high', 'medium']:
                plan.long_term_improvements.append(rec)

    def _generate_summary(self, plan: OptimizationPlan) -> str:
        """Generate executive summary of the optimization plan."""
        summary_parts = [
            f'Workflow Health: {plan.overall_health.upper()} ({plan.health_score:.0f}/100)',
            f'\nTotal Recommendations: {len(plan.recommendations)}',
        ]

        # Count by priority
        priority_counts = {}
        for rec in plan.recommendations:
            priority_counts[rec.priority] = priority_counts.get(rec.priority, 0) + 1

        if priority_counts:
            summary_parts.append('\nBy Priority:')
            for priority in ['critical', 'high', 'medium', 'low']:
                if priority in priority_counts:
                    summary_parts.append(f'  - {priority.capitalize()}: {priority_counts[priority]}')

        # Quick wins
        if plan.quick_wins:
            summary_parts.append(f'\nQuick Wins: {len(plan.quick_wins)} opportunities for immediate improvement')

        # Long-term
        if plan.long_term_improvements:
            summary_parts.append(
                f'\nLong-term Improvements: {len(plan.long_term_improvements)} strategic enhancements'
            )

        return '\n'.join(summary_parts)

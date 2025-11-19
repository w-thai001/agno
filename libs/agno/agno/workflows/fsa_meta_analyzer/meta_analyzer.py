"""
FSA Meta-Analyzer Workflow - Main orchestration workflow for FSA analysis.

This workflow coordinates all analysis modules to provide comprehensive
FSA analysis, validation, and optimization recommendations.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Type

from agno.run.response import RunResponse
from agno.workflow.workflow import Workflow
from agno.workflows.fsa_meta_analyzer.dependency_analyzer import (
    DependencyAnalyzer,
    DependencyAnalysisReport,
)
from agno.workflows.fsa_meta_analyzer.optimizer import FSAOptimizer, OptimizationPlan
from agno.workflows.fsa_meta_analyzer.pattern_analyzer import (
    FSAPatternDetector,
    PatternAnalysisReport,
)
from agno.workflows.fsa_meta_analyzer.profiler import (
    FSAPerformanceProfiler,
    PerformanceAnalysis,
)
from agno.workflows.fsa_meta_analyzer.quality_metrics import QualityMetrics, QualityMetricsCalculator
from agno.workflows.fsa_meta_analyzer.static_analyzer import FSAStaticAnalyzer, FSAStructure
from agno.workflows.fsa_meta_analyzer.validator import FSAValidator, ValidationReport


@dataclass
class MetaAnalysisReport:
    """Complete meta-analysis report for one or more FSAs."""

    workflow_name: str
    fsa_structure: Optional[FSAStructure] = None
    validation_report: Optional[ValidationReport] = None
    quality_metrics: Optional[QualityMetrics] = None
    performance_analysis: Optional[PerformanceAnalysis] = None
    pattern_analysis: Optional[PatternAnalysisReport] = None
    dependency_analysis: Optional[DependencyAnalysisReport] = None
    optimization_plan: Optional[OptimizationPlan] = None
    analysis_summary: str = ''
    visualizations: Dict[str, str] = field(default_factory=dict)


class FSAMetaAnalyzer(Workflow):
    """
    FSA Meta-Analyzer Workflow.

    A specialized workflow that analyzes, validates, and improves other FSAs.
    Provides comprehensive analysis including structure validation, performance profiling,
    quality metrics, pattern detection, dependency analysis, and optimization recommendations.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.static_analyzer = FSAStaticAnalyzer()
        self.validator = FSAValidator()
        self.profiler = FSAPerformanceProfiler()
        self.quality_calculator = QualityMetricsCalculator()
        self.pattern_detector = FSAPatternDetector()
        self.dependency_analyzer = DependencyAnalyzer()
        self.optimizer = FSAOptimizer()

    def run(
        self,
        workflow_class: Optional[Type[Workflow]] = None,
        workflow_classes: Optional[List[Type[Workflow]]] = None,
        include_performance: bool = True,
        include_patterns: bool = True,
        include_dependencies: bool = True,
        include_optimization: bool = True,
        generate_visualizations: bool = True,
    ) -> Iterator[RunResponse]:
        """
        Analyze one or more workflow FSAs.

        Args:
            workflow_class: Single workflow class to analyze
            workflow_classes: Multiple workflow classes to analyze
            include_performance: Include performance analysis
            include_patterns: Include pattern detection
            include_dependencies: Include dependency analysis
            include_optimization: Include optimization recommendations
            generate_visualizations: Generate dependency graph visualizations

        Returns:
            Iterator of RunResponse with analysis results
        """
        # Determine workflows to analyze
        workflows_to_analyze = []
        if workflow_class:
            workflows_to_analyze.append(workflow_class)
        if workflow_classes:
            workflows_to_analyze.extend(workflow_classes)

        if not workflows_to_analyze:
            yield RunResponse(
                content='Error: No workflow classes provided for analysis',
                error='No workflows specified',
            )
            return

        yield RunResponse(
            content=f'Starting meta-analysis of {len(workflows_to_analyze)} workflow(s)...'
        )

        # Analyze each workflow
        reports = []
        for workflow_cls in workflows_to_analyze:
            yield RunResponse(content=f'\n{"=" * 80}\nAnalyzing: {workflow_cls.__name__}\n{"=" * 80}')

            report = self._analyze_single_workflow(
                workflow_cls,
                include_performance=include_performance,
                include_patterns=include_patterns,
                include_optimization=include_optimization,
            )
            reports.append(report)

            # Output individual report
            yield from self._format_report(report)

        # Cross-workflow analysis
        if len(reports) > 1:
            yield RunResponse(
                content=f'\n{"=" * 80}\nCross-Workflow Analysis\n{"=" * 80}'
            )

            if include_patterns:
                yield from self._perform_cross_workflow_pattern_analysis(
                    [r.fsa_structure for r in reports if r.fsa_structure]
                )

            if include_dependencies:
                yield from self._perform_cross_workflow_dependency_analysis(
                    [r.fsa_structure for r in reports if r.fsa_structure],
                    generate_visualizations,
                )

        # Summary
        yield RunResponse(
            content=f'\n{"=" * 80}\nAnalysis Complete\n{"=" * 80}\n'
            f'Analyzed {len(reports)} workflow(s)'
        )

        # Cache reports in session state
        self.session_state['analysis_reports'] = reports

    def _analyze_single_workflow(
        self,
        workflow_class: Type[Workflow],
        include_performance: bool = True,
        include_patterns: bool = True,
        include_optimization: bool = True,
    ) -> MetaAnalysisReport:
        """Analyze a single workflow."""
        report = MetaAnalysisReport(workflow_name=workflow_class.__name__)

        # 1. Static Analysis - Extract FSA structure
        report.fsa_structure = self.static_analyzer.analyze_workflow(workflow_class)

        # 2. Validation - Check for errors and best practices
        report.validation_report = self.validator.validate(report.fsa_structure)

        # 3. Quality Metrics - Calculate quality scores
        report.quality_metrics = self.quality_calculator.calculate_metrics(
            report.fsa_structure, report.validation_report
        )

        # 4. Performance Analysis (optional)
        if include_performance:
            report.performance_analysis = (
                self.profiler.analyze_performance_characteristics(report.fsa_structure)
            )

        # 5. Pattern Detection (optional)
        if include_patterns:
            report.pattern_analysis = self.pattern_detector.analyze_patterns(
                report.fsa_structure
            )

        # 6. Optimization Recommendations (optional)
        if include_optimization:
            report.optimization_plan = self.optimizer.generate_optimization_plan(
                fsa=report.fsa_structure,
                validation_report=report.validation_report,
                quality_metrics=report.quality_metrics,
                performance_analysis=report.performance_analysis,
                pattern_report=report.pattern_analysis,
            )

        # Generate summary
        report.analysis_summary = self._generate_summary(report)

        return report

    def _perform_cross_workflow_pattern_analysis(
        self, fsas: List[FSAStructure]
    ) -> Iterator[RunResponse]:
        """Perform pattern analysis across multiple workflows."""
        if not fsas:
            return

        yield RunResponse(content='\n## Cross-Workflow Pattern Analysis')

        aggregate_report = self.pattern_detector.analyze_multiple_fsas(fsas)

        yield RunResponse(
            content=f'\nCommon Patterns Detected: {len(aggregate_report.common_patterns)}'
        )

        if aggregate_report.common_patterns:
            for pattern_type in aggregate_report.common_patterns:
                count = aggregate_report.pattern_frequency.get(pattern_type, 0)
                yield RunResponse(
                    content=f'  - {pattern_type.value}: {count} occurrences'
                )

        if aggregate_report.antipatterns:
            yield RunResponse(
                content=f'\nAntipatterns Found: {len(aggregate_report.antipatterns)}'
            )

    def _perform_cross_workflow_dependency_analysis(
        self, fsas: List[FSAStructure], generate_visualizations: bool
    ) -> Iterator[RunResponse]:
        """Perform dependency analysis across multiple workflows."""
        if not fsas:
            return

        yield RunResponse(content='\n## Cross-Workflow Dependency Analysis')

        dependency_report = self.dependency_analyzer.analyze_multiple_fsas(fsas)

        yield RunResponse(
            content=f'\nTotal Dependencies: {dependency_report.total_dependencies}\n'
            f'Circular Dependencies: {dependency_report.circular_dependencies}\n'
            f'Dependency Depth: {dependency_report.max_dependency_depth} layers\n'
            f'Coupling Score: {dependency_report.coupling_score:.0f}/100'
        )

        if dependency_report.highly_coupled_components:
            yield RunResponse(
                content=f'\nHighly Coupled Components: {len(dependency_report.highly_coupled_components)}'
            )

        if generate_visualizations:
            # Generate Mermaid diagram
            mermaid = self.dependency_analyzer.generate_mermaid_diagram(
                dependency_report.graph
            )
            yield RunResponse(
                content=f'\n### Dependency Graph (Mermaid)\n\n```mermaid\n{mermaid}\n```'
            )

    def _format_report(self, report: MetaAnalysisReport) -> Iterator[RunResponse]:
        """Format and output a single workflow report."""
        # Overview
        yield RunResponse(content='\n## Overview')

        if report.fsa_structure:
            fsa = report.fsa_structure
            yield RunResponse(
                content=f'\n**Structure:**\n'
                f'  - States: {len(fsa.states)}\n'
                f'  - Transitions: {len(fsa.transitions)}\n'
                f'  - Agents: {len(fsa.agents)}\n'
                f'  - Cyclomatic Complexity: {fsa.complexity_metrics.get("cyclomatic_complexity", 0)}'
            )

        # Validation Results
        if report.validation_report:
            yield RunResponse(content='\n## Validation Results')
            val = report.validation_report
            yield RunResponse(
                content=f'\n**Status:** {"✓ VALID" if val.is_valid else "✗ INVALID"}\n'
                f'  - Critical Issues: {val.critical_count}\n'
                f'  - Errors: {val.error_count}\n'
                f'  - Warnings: {val.warning_count}\n'
                f'  - Info: {val.info_count}'
            )

            # Show critical/error issues
            critical_errors = [
                i for i in val.issues if i.severity.value in ['critical', 'error']
            ]
            if critical_errors:
                yield RunResponse(content='\n**Critical Issues:**')
                for issue in critical_errors[:5]:  # Show first 5
                    yield RunResponse(
                        content=f'  - [{issue.severity.value.upper()}] {issue.category}: {issue.message}'
                    )

        # Quality Metrics
        if report.quality_metrics:
            yield RunResponse(content='\n## Quality Metrics')
            qm = report.quality_metrics
            yield RunResponse(
                content=f'\n**Overall Quality:** Grade {qm.quality_grade} ({qm.overall_quality_score:.0f}/100)\n\n'
                f'**Breakdown:**\n'
                f'  - Maintainability: {qm.maintainability_index:.0f}/100\n'
                f'  - Reliability: {qm.reliability_score:.0f}/100\n'
                f'  - Efficiency: {qm.efficiency_score:.0f}/100\n'
                f'  - Testability: {qm.testability_score:.0f}/100\n'
                f'  - Best Practices: {qm.best_practices_score:.0f}/100'
            )

            if qm.antipatterns_detected:
                yield RunResponse(
                    content=f'\n**Antipatterns:** {len(qm.antipatterns_detected)} detected'
                )

        # Performance Analysis
        if report.performance_analysis:
            yield RunResponse(content='\n## Performance Analysis')
            perf = report.performance_analysis
            yield RunResponse(
                content=f'\n**Performance Score:** {perf.performance_score:.0f}/100'
            )

            if perf.slowest_states:
                yield RunResponse(content='\n**Slowest States (Predicted):')
                for state_name, complexity in perf.slowest_states[:3]:
                    yield RunResponse(
                        content=f'  - {state_name}: complexity score {complexity:.0f}'
                    )

        # Pattern Analysis
        if report.pattern_analysis:
            yield RunResponse(content='\n## Pattern Analysis')
            pa = report.pattern_analysis
            yield RunResponse(content=f'\n**Patterns Detected:** {len(pa.patterns)}')

            if pa.antipatterns:
                yield RunResponse(
                    content=f'\n**Antipatterns:** {len(pa.antipatterns)}'
                )
                for ap in pa.antipatterns[:3]:
                    yield RunResponse(
                        content=f'  - {ap.pattern_type.value}: {ap.description}'
                    )

        # Optimization Plan
        if report.optimization_plan:
            yield RunResponse(content='\n## Optimization Plan')
            opt = report.optimization_plan
            yield RunResponse(
                content=f'\n**Health Status:** {opt.overall_health.upper()} ({opt.health_score:.0f}/100)\n'
                f'**Total Recommendations:** {len(opt.recommendations)}'
            )

            if opt.quick_wins:
                yield RunResponse(
                    content=f'\n**Quick Wins ({len(opt.quick_wins)}):**'
                )
                for qw in opt.quick_wins[:3]:
                    yield RunResponse(
                        content=f'  - [{qw.priority.upper()}] {qw.title}\n'
                        f'    {qw.description[:100]}...'
                    )

            if opt.long_term_improvements:
                yield RunResponse(
                    content=f'\n**Long-term Improvements ({len(opt.long_term_improvements)}):**'
                )
                for lt in opt.long_term_improvements[:3]:
                    yield RunResponse(
                        content=f'  - [{lt.priority.upper()}] {lt.title}'
                    )

    def _generate_summary(self, report: MetaAnalysisReport) -> str:
        """Generate executive summary of the analysis."""
        parts = [f'Analysis Summary for {report.workflow_name}', '=' * 60, '']

        if report.fsa_structure:
            parts.append(
                f'Structure: {len(report.fsa_structure.states)} states, '
                f'{len(report.fsa_structure.transitions)} transitions'
            )

        if report.validation_report:
            status = 'VALID' if report.validation_report.is_valid else 'INVALID'
            parts.append(f'Validation: {status}')

        if report.quality_metrics:
            parts.append(
                f'Quality: Grade {report.quality_metrics.quality_grade} '
                f'({report.quality_metrics.overall_quality_score:.0f}/100)'
            )

        if report.optimization_plan:
            parts.append(
                f'Health: {report.optimization_plan.overall_health.upper()} '
                f'({report.optimization_plan.health_score:.0f}/100)'
            )
            parts.append(f'Recommendations: {len(report.optimization_plan.recommendations)}')

        return '\n'.join(parts)

    def get_cached_reports(self) -> List[MetaAnalysisReport]:
        """Get cached analysis reports from session state."""
        return self.session_state.get('analysis_reports', [])

    def export_report(self, report: MetaAnalysisReport, output_path: str) -> bool:
        """
        Export analysis report to file.

        Args:
            report: The report to export
            output_path: Path to save the report

        Returns:
            True if successful, False otherwise
        """
        try:
            import json
            from dataclasses import asdict

            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            # Convert report to dict (simplified version)
            report_dict = {
                'workflow_name': report.workflow_name,
                'analysis_summary': report.analysis_summary,
            }

            if report.validation_report:
                report_dict['validation'] = {
                    'is_valid': report.validation_report.is_valid,
                    'critical_count': report.validation_report.critical_count,
                    'error_count': report.validation_report.error_count,
                    'warning_count': report.validation_report.warning_count,
                }

            if report.quality_metrics:
                report_dict['quality'] = {
                    'grade': report.quality_metrics.quality_grade,
                    'score': report.quality_metrics.overall_quality_score,
                }

            with open(output_file, 'w') as f:
                json.dump(report_dict, f, indent=2)

            return True
        except Exception as e:
            print(f'Error exporting report: {e}')
            return False

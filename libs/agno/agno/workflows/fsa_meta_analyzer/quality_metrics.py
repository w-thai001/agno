"""
FSA Quality Metrics Calculator - Computes quality metrics for FSAs.

Calculates comprehensive quality metrics including:
- Maintainability index
- Cohesion and coupling scores
- Complexity metrics
- Test coverage estimations
- Documentation quality
- Best practices compliance
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set

from agno.workflows.fsa_meta_analyzer.static_analyzer import FSAStructure
from agno.workflows.fsa_meta_analyzer.validator import ValidationReport, ValidationSeverity


@dataclass
class QualityMetrics:
    """Comprehensive quality metrics for an FSA."""

    workflow_name: str

    # Overall scores (0-100)
    overall_quality_score: float = 0.0
    maintainability_index: float = 0.0
    reliability_score: float = 0.0
    efficiency_score: float = 0.0
    testability_score: float = 0.0

    # Structural metrics
    cohesion_score: float = 0.0
    coupling_score: float = 0.0
    modularity_score: float = 0.0

    # Complexity metrics
    cyclomatic_complexity: int = 0
    cognitive_complexity: int = 0
    state_complexity: float = 0.0
    transition_complexity: float = 0.0

    # Code quality metrics
    documentation_score: float = 0.0
    type_annotation_coverage: float = 0.0
    error_handling_coverage: float = 0.0

    # Best practices compliance
    best_practices_score: float = 0.0
    antipatterns_detected: List[str] = field(default_factory=list)

    # Recommendations
    quality_grade: str = 'F'  # A, B, C, D, F
    improvement_areas: List[str] = field(default_factory=list)


class QualityMetricsCalculator:
    """Calculates comprehensive quality metrics for FSAs."""

    def __init__(self):
        self.weights = {
            'maintainability': 0.25,
            'reliability': 0.25,
            'efficiency': 0.20,
            'testability': 0.15,
            'best_practices': 0.15,
        }

    def calculate_metrics(
        self, fsa: FSAStructure, validation_report: ValidationReport
    ) -> QualityMetrics:
        """
        Calculate comprehensive quality metrics for an FSA.

        Args:
            fsa: The FSA structure to analyze
            validation_report: Validation report from FSAValidator

        Returns:
            QualityMetrics with all calculated scores
        """
        metrics = QualityMetrics(workflow_name=fsa.workflow_name)

        # Calculate individual metric components
        self._calculate_maintainability(fsa, validation_report, metrics)
        self._calculate_reliability(fsa, validation_report, metrics)
        self._calculate_efficiency(fsa, metrics)
        self._calculate_testability(fsa, metrics)
        self._calculate_structural_metrics(fsa, metrics)
        self._calculate_complexity_metrics(fsa, metrics)
        self._calculate_code_quality(fsa, metrics)
        self._detect_antipatterns(fsa, metrics)
        self._calculate_best_practices(fsa, metrics)

        # Calculate overall quality score
        metrics.overall_quality_score = self._calculate_overall_score(metrics)

        # Assign quality grade
        metrics.quality_grade = self._assign_grade(metrics.overall_quality_score)

        # Generate improvement recommendations
        self._generate_improvement_areas(fsa, metrics)

        return metrics

    def _calculate_maintainability(
        self, fsa: FSAStructure, validation_report: ValidationReport, metrics: QualityMetrics
    ):
        """Calculate maintainability index."""
        # Start with perfect score
        score = 100.0

        # Penalize for complexity
        complexity = fsa.complexity_metrics.get('cyclomatic_complexity', 0)
        if complexity > 10:
            score -= (complexity - 10) * 2

        # Penalize for validation errors
        score -= validation_report.error_count * 5
        score -= validation_report.warning_count * 2

        # Penalize for large number of states
        state_count = fsa.complexity_metrics.get('total_states', 0)
        if state_count > 20:
            score -= (state_count - 20) * 1

        # Bonus for good documentation
        if any(s.description for s in fsa.states.values()):
            score += 5

        metrics.maintainability_index = max(0.0, min(100.0, score))

    def _calculate_reliability(
        self, fsa: FSAStructure, validation_report: ValidationReport, metrics: QualityMetrics
    ):
        """Calculate reliability score based on error handling and validation."""
        score = 100.0

        # Penalize for critical validation issues
        score -= validation_report.critical_count * 20
        score -= validation_report.error_count * 10

        # Reward error handling
        error_state_ratio = len(fsa.error_states) / max(len(fsa.states), 1)
        if error_state_ratio > 0:
            score += 10
        if error_state_ratio > 0.1:
            score += 5

        # Penalize for missing exit states
        if not fsa.exit_states:
            score -= 15

        # Check error handling coverage
        states_with_agents = sum(1 for s in fsa.states.values() if s.agent_calls)
        if states_with_agents > 0:
            coverage = len(fsa.error_states) / states_with_agents
            metrics.error_handling_coverage = min(100.0, coverage * 100)
            score += coverage * 10

        metrics.reliability_score = max(0.0, min(100.0, score))

    def _calculate_efficiency(self, fsa: FSAStructure, metrics: QualityMetrics):
        """Calculate efficiency score based on structure."""
        score = 100.0

        # Penalize for excessive transitions
        transition_count = fsa.complexity_metrics.get('total_transitions', 0)
        state_count = fsa.complexity_metrics.get('total_states', 1)

        # Ideal ratio is around 1.5 transitions per state
        ratio = transition_count / state_count
        if ratio > 3:
            score -= (ratio - 3) * 5

        # Penalize for deep nesting (approximated by decision points)
        decision_points = fsa.complexity_metrics.get('decision_points', 0)
        if decision_points > 10:
            score -= (decision_points - 10) * 3

        # Penalize for excessive loops
        loop_count = fsa.complexity_metrics.get('loop_states', 0)
        if loop_count > 5:
            score -= (loop_count - 5) * 5

        # Reward simple, linear workflows
        if decision_points < 5 and loop_count < 2:
            score += 10

        metrics.efficiency_score = max(0.0, min(100.0, score))

    def _calculate_testability(self, fsa: FSAStructure, metrics: QualityMetrics):
        """Calculate testability score."""
        score = 100.0

        # Penalize for high complexity (harder to test)
        complexity = fsa.complexity_metrics.get('cyclomatic_complexity', 0)
        score -= max(0, (complexity - 5) * 3)

        # Reward modular structure
        state_count = fsa.complexity_metrics.get('total_states', 1)
        if 5 <= state_count <= 15:
            score += 10

        # Reward type annotations (easier to test)
        annotated_params = sum(
            1 for p in fsa.parameters.values() if p.get('annotation') is not None
        )
        total_params = len(fsa.parameters)
        if total_params > 0:
            annotation_coverage = annotated_params / total_params
            metrics.type_annotation_coverage = annotation_coverage * 100
            score += annotation_coverage * 10

        # Reward clear entry and exit points
        if fsa.entry_state and fsa.exit_states:
            score += 10

        # Penalize for many agents (harder to mock/test)
        agent_count = len(fsa.agents)
        if agent_count > 5:
            score -= (agent_count - 5) * 3

        metrics.testability_score = max(0.0, min(100.0, score))

    def _calculate_structural_metrics(self, fsa: FSAStructure, metrics: QualityMetrics):
        """Calculate cohesion, coupling, and modularity."""
        state_count = len(fsa.states)
        if state_count == 0:
            return

        # Cohesion: how focused are states on a single purpose
        # Higher cohesion = states have fewer responsibilities
        avg_agent_calls = (
            sum(len(s.agent_calls) for s in fsa.states.values()) / state_count
        )
        cohesion = 100.0 / (1 + avg_agent_calls)  # Lower agent calls = higher cohesion
        metrics.cohesion_score = cohesion

        # Coupling: how interdependent are states
        # Lower coupling = better
        transition_count = len(fsa.transitions)
        coupling_ratio = transition_count / state_count
        coupling = max(0, 100 - (coupling_ratio * 20))
        metrics.coupling_score = coupling

        # Modularity: combination of cohesion and coupling
        metrics.modularity_score = (cohesion + coupling) / 2

    def _calculate_complexity_metrics(self, fsa: FSAStructure, metrics: QualityMetrics):
        """Calculate detailed complexity metrics."""
        metrics.cyclomatic_complexity = fsa.complexity_metrics.get(
            'cyclomatic_complexity', 0
        )

        # Cognitive complexity: how hard is it to understand the flow
        cognitive = 0
        cognitive += fsa.complexity_metrics.get('decision_points', 0) * 2  # If/else branches
        cognitive += fsa.complexity_metrics.get('loop_states', 0) * 3  # Loops are harder
        cognitive += len(fsa.error_states) * 1  # Exception handling
        metrics.cognitive_complexity = cognitive

        # State complexity: average complexity per state
        state_count = fsa.complexity_metrics.get('total_states', 1)
        state_complexity = sum(
            len(s.agent_calls) * 3 + len(s.tool_calls) * 2 + len(s.variables_written)
            for s in fsa.states.values()
        )
        metrics.state_complexity = state_complexity / state_count

        # Transition complexity
        metrics.transition_complexity = fsa.complexity_metrics.get('total_transitions', 0) / state_count

    def _calculate_code_quality(self, fsa: FSAStructure, metrics: QualityMetrics):
        """Calculate code quality indicators."""
        # Documentation score
        documented_states = sum(1 for s in fsa.states.values() if s.description)
        total_states = len(fsa.states)
        if total_states > 0:
            metrics.documentation_score = (documented_states / total_states) * 100

    def _detect_antipatterns(self, fsa: FSAStructure, metrics: QualityMetrics):
        """Detect common antipatterns in FSA design."""
        antipatterns = []

        # God State: state with too many responsibilities
        for state in fsa.states.values():
            if len(state.agent_calls) > 5:
                antipatterns.append(
                    f"God State: '{state.name}' has {len(state.agent_calls)} agent calls"
                )

        # Spaghetti Flow: too many transitions
        transition_count = fsa.complexity_metrics.get('total_transitions', 0)
        state_count = fsa.complexity_metrics.get('total_states', 1)
        if transition_count / state_count > 4:
            antipatterns.append(
                f"Spaghetti Flow: {transition_count} transitions for {state_count} states"
            )

        # Missing Error Handling
        if not fsa.error_states and fsa.agents:
            antipatterns.append("Missing Error Handling: No error states despite agent usage")

        # Dead End: state with no exit
        for state_name in fsa.states:
            has_exit = any(
                t.from_state == state_name for t in fsa.transitions
            ) or state_name in fsa.exit_states
            if not has_exit:
                antipatterns.append(f"Dead End: State '{state_name}' has no exit")

        # Unreachable States: already caught by validator but worth mentioning
        if fsa.entry_state:
            reachable = self._get_reachable_states(fsa, fsa.entry_state)
            unreachable = set(fsa.states.keys()) - reachable
            if unreachable:
                antipatterns.append(
                    f"Unreachable States: {len(unreachable)} states cannot be reached"
                )

        # Deep Nesting: too many decision points
        if fsa.complexity_metrics.get('decision_points', 0) > 15:
            antipatterns.append(
                f"Deep Nesting: {fsa.complexity_metrics['decision_points']} decision points"
            )

        metrics.antipatterns_detected = antipatterns

    def _get_reachable_states(self, fsa: FSAStructure, entry_state: str) -> Set[str]:
        """Get all reachable states from entry state."""
        reachable = set()
        stack = [entry_state]

        while stack:
            state = stack.pop()
            if state in reachable:
                continue
            reachable.add(state)

            # Find all states reachable from this state
            for transition in fsa.transitions:
                if transition.from_state == state and transition.to_state not in reachable:
                    stack.append(transition.to_state)

        return reachable

    def _calculate_best_practices(self, fsa: FSAStructure, metrics: QualityMetrics):
        """Calculate best practices compliance score."""
        score = 100.0

        # Type annotations
        if metrics.type_annotation_coverage < 80:
            score -= (80 - metrics.type_annotation_coverage) * 0.2

        # Error handling
        if metrics.error_handling_coverage < 50:
            score -= (50 - metrics.error_handling_coverage) * 0.3

        # Documentation
        if metrics.documentation_score < 50:
            score -= (50 - metrics.documentation_score) * 0.1

        # Return type annotation
        if not fsa.return_type:
            score -= 10

        # Entry and exit states
        if not fsa.entry_state:
            score -= 15
        if not fsa.exit_states:
            score -= 15

        # Reasonable complexity
        if metrics.cyclomatic_complexity > 20:
            score -= (metrics.cyclomatic_complexity - 20) * 2

        metrics.best_practices_score = max(0.0, min(100.0, score))

    def _calculate_overall_score(self, metrics: QualityMetrics) -> float:
        """Calculate weighted overall quality score."""
        score = (
            metrics.maintainability_index * self.weights['maintainability']
            + metrics.reliability_score * self.weights['reliability']
            + metrics.efficiency_score * self.weights['efficiency']
            + metrics.testability_score * self.weights['testability']
            + metrics.best_practices_score * self.weights['best_practices']
        )
        return round(score, 2)

    def _assign_grade(self, score: float) -> str:
        """Assign letter grade based on score."""
        if score >= 90:
            return 'A'
        elif score >= 80:
            return 'B'
        elif score >= 70:
            return 'C'
        elif score >= 60:
            return 'D'
        else:
            return 'F'

    def _generate_improvement_areas(self, fsa: FSAStructure, metrics: QualityMetrics):
        """Generate specific improvement recommendations."""
        areas = []

        # Maintainability improvements
        if metrics.maintainability_index < 70:
            areas.append(
                "Improve maintainability by reducing complexity and fixing validation issues"
            )

        # Reliability improvements
        if metrics.reliability_score < 70:
            areas.append("Add error handling and ensure all code paths lead to exit states")

        # Efficiency improvements
        if metrics.efficiency_score < 70:
            areas.append("Optimize control flow by reducing unnecessary transitions")

        # Testability improvements
        if metrics.testability_score < 70:
            areas.append("Improve testability by adding type annotations and reducing agent coupling")

        # Structural improvements
        if metrics.cohesion_score < 60:
            areas.append("Increase cohesion by giving each state a single, focused responsibility")

        if metrics.coupling_score < 60:
            areas.append("Reduce coupling by minimizing dependencies between states")

        # Complexity improvements
        if metrics.cyclomatic_complexity > 15:
            areas.append(
                "Reduce cyclomatic complexity by extracting complex logic into sub-workflows"
            )

        if metrics.cognitive_complexity > 20:
            areas.append("Simplify control flow to reduce cognitive complexity")

        # Code quality improvements
        if metrics.type_annotation_coverage < 80:
            areas.append("Add type annotations to improve code clarity and catch errors early")

        if metrics.documentation_score < 50:
            areas.append("Add documentation to states and complex logic")

        # Antipattern fixes
        if metrics.antipatterns_detected:
            areas.append(
                f"Address {len(metrics.antipatterns_detected)} antipatterns detected in the workflow"
            )

        metrics.improvement_areas = areas

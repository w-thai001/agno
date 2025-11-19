"""
FSA Pattern Detection - Detects common patterns across FSA collections.

Identifies design patterns, anti-patterns, and reusable patterns across
multiple FSA workflows for standardization and best practices.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Set, Tuple

from agno.workflows.fsa_meta_analyzer.static_analyzer import FSAStructure, FSAState, FSATransition


class PatternType(str, Enum):
    """Types of patterns that can be detected."""

    # Design patterns
    PIPELINE = 'pipeline'
    SCATTER_GATHER = 'scatter_gather'
    FAN_OUT_FAN_IN = 'fan_out_fan_in'
    STATE_MACHINE = 'state_machine'
    RETRY_LOOP = 'retry_loop'
    CACHE_ASIDE = 'cache_aside'
    CIRCUIT_BREAKER = 'circuit_breaker'

    # Anti-patterns
    GOD_STATE = 'god_state'
    SPAGHETTI_FLOW = 'spaghetti_flow'
    LAVA_FLOW = 'lava_flow'  # Dead code
    GOLDEN_HAMMER = 'golden_hammer'  # Overused pattern

    # Common patterns
    GUARD_CLAUSE = 'guard_clause'
    ERROR_HANDLER = 'error_handler'
    VALIDATOR = 'validator'
    TRANSFORMER = 'transformer'


@dataclass
class DetectedPattern:
    """Represents a detected pattern in an FSA."""

    pattern_type: PatternType
    confidence: float  # 0.0 - 1.0
    location: str  # State or transition where pattern is found
    description: str
    states_involved: List[str] = field(default_factory=list)
    is_antipattern: bool = False
    recommendation: str = ''


@dataclass
class PatternAnalysisReport:
    """Report of patterns detected across FSAs."""

    patterns: List[DetectedPattern] = field(default_factory=list)
    pattern_frequency: Dict[PatternType, int] = field(default_factory=dict)
    common_patterns: List[PatternType] = field(default_factory=list)
    antipatterns: List[DetectedPattern] = field(default_factory=list)
    reusable_patterns: List[str] = field(default_factory=list)


class FSAPatternDetector:
    """Detects patterns in FSA structures."""

    def __init__(self):
        self.detected_patterns: List[DetectedPattern] = []

    def analyze_patterns(self, fsa: FSAStructure) -> PatternAnalysisReport:
        """
        Analyze an FSA to detect design patterns and anti-patterns.

        Args:
            fsa: The FSA structure to analyze

        Returns:
            PatternAnalysisReport with detected patterns
        """
        report = PatternAnalysisReport()

        # Detect design patterns
        self._detect_pipeline_pattern(fsa, report)
        self._detect_scatter_gather_pattern(fsa, report)
        self._detect_retry_loop_pattern(fsa, report)
        self._detect_cache_aside_pattern(fsa, report)
        self._detect_guard_clause_pattern(fsa, report)
        self._detect_error_handler_pattern(fsa, report)

        # Detect anti-patterns
        self._detect_god_state_antipattern(fsa, report)
        self._detect_spaghetti_flow_antipattern(fsa, report)
        self._detect_lava_flow_antipattern(fsa, report)

        # Calculate pattern frequency
        self._calculate_pattern_frequency(report)

        # Identify reusable patterns
        self._identify_reusable_patterns(report)

        return report

    def analyze_multiple_fsas(self, fsas: List[FSAStructure]) -> PatternAnalysisReport:
        """
        Analyze multiple FSAs to find common patterns across workflows.

        Args:
            fsas: List of FSA structures to analyze

        Returns:
            Aggregated pattern analysis report
        """
        aggregate_report = PatternAnalysisReport()

        # Analyze each FSA
        for fsa in fsas:
            fsa_report = self.analyze_patterns(fsa)
            aggregate_report.patterns.extend(fsa_report.patterns)

        # Calculate aggregate statistics
        self._calculate_pattern_frequency(aggregate_report)
        self._identify_common_patterns(aggregate_report)
        self._identify_reusable_patterns(aggregate_report)

        # Separate antipatterns
        aggregate_report.antipatterns = [
            p for p in aggregate_report.patterns if p.is_antipattern
        ]

        return aggregate_report

    def _detect_pipeline_pattern(self, fsa: FSAStructure, report: PatternAnalysisReport):
        """Detect linear pipeline pattern (A -> B -> C -> D)."""
        # Build transition graph
        graph = self._build_transition_graph(fsa)

        # Find linear sequences
        for state in fsa.states:
            if state == fsa.entry_state:
                sequence = self._find_linear_sequence(state, graph, fsa.states)
                if len(sequence) >= 3:
                    pattern = DetectedPattern(
                        pattern_type=PatternType.PIPELINE,
                        confidence=0.9,
                        location=state,
                        description=f'Linear pipeline of {len(sequence)} states',
                        states_involved=sequence,
                        recommendation='Pipeline pattern detected - good for sequential processing',
                    )
                    report.patterns.append(pattern)

    def _detect_scatter_gather_pattern(self, fsa: FSAStructure, report: PatternAnalysisReport):
        """Detect scatter-gather pattern (fan-out then fan-in)."""
        graph = self._build_transition_graph(fsa)

        for state in fsa.states:
            # Check for fan-out (one state to many)
            outgoing = graph.get(state, [])
            if len(outgoing) >= 3:
                # Check if they converge to a single state (fan-in)
                converge_states = set()
                for out_state in outgoing:
                    next_states = graph.get(out_state, [])
                    converge_states.update(next_states)

                # If most paths converge to one or two states, it's scatter-gather
                if len(converge_states) <= 2:
                    pattern = DetectedPattern(
                        pattern_type=PatternType.SCATTER_GATHER,
                        confidence=0.85,
                        location=state,
                        description=f'Scatter to {len(outgoing)} states, gather to {len(converge_states)}',
                        states_involved=[state] + outgoing + list(converge_states),
                        recommendation='Scatter-gather pattern - consider parallel execution',
                    )
                    report.patterns.append(pattern)

    def _detect_retry_loop_pattern(self, fsa: FSAStructure, report: PatternAnalysisReport):
        """Detect retry/loop pattern with exit condition."""
        graph = self._build_transition_graph(fsa)

        for loop_state in fsa.loop_states:
            # Check if loop has error handling
            has_error_handler = any(
                t.from_state == loop_state and t.to_state in fsa.error_states
                for t in fsa.transitions
            )

            # Check if loop has exit condition
            has_exit = any(
                t.from_state == loop_state and t.to_state not in fsa.loop_states
                for t in fsa.transitions
            )

            if has_exit:
                confidence = 0.9 if has_error_handler else 0.7
                pattern = DetectedPattern(
                    pattern_type=PatternType.RETRY_LOOP,
                    confidence=confidence,
                    location=loop_state,
                    description='Retry loop with exit condition',
                    states_involved=[loop_state],
                    recommendation='Good retry pattern' if has_error_handler else 'Add error handling to retry loop',
                )
                report.patterns.append(pattern)

    def _detect_cache_aside_pattern(self, fsa: FSAStructure, report: PatternAnalysisReport):
        """Detect cache-aside pattern (check cache, fetch if miss, update cache)."""
        # Look for states that read from session_state (cache check)
        for state_name, state in fsa.states.items():
            if 'session_state' in state.variables_read or 'cache' in state_name.lower():
                # Look for conditional branch
                outgoing_transitions = [
                    t for t in fsa.transitions if t.from_state == state_name
                ]

                if len(outgoing_transitions) >= 2:  # Cache hit and miss branches
                    pattern = DetectedPattern(
                        pattern_type=PatternType.CACHE_ASIDE,
                        confidence=0.75,
                        location=state_name,
                        description='Cache-aside pattern detected',
                        states_involved=[state_name],
                        recommendation='Cache-aside pattern improves performance',
                    )
                    report.patterns.append(pattern)

    def _detect_guard_clause_pattern(self, fsa: FSAStructure, report: PatternAnalysisReport):
        """Detect guard clause pattern (early return/exit based on condition)."""
        # Look for early exit states near entry
        if not fsa.entry_state:
            return

        graph = self._build_transition_graph(fsa)
        entry_neighbors = graph.get(fsa.entry_state, [])

        for neighbor in entry_neighbors:
            if neighbor in fsa.exit_states:
                pattern = DetectedPattern(
                    pattern_type=PatternType.GUARD_CLAUSE,
                    confidence=0.85,
                    location=fsa.entry_state,
                    description='Guard clause - early exit on invalid input',
                    states_involved=[fsa.entry_state, neighbor],
                    recommendation='Guard clauses improve readability and reduce nesting',
                )
                report.patterns.append(pattern)

    def _detect_error_handler_pattern(self, fsa: FSAStructure, report: PatternAnalysisReport):
        """Detect error handling patterns."""
        if not fsa.error_states:
            return

        # Check coverage of error handling
        states_with_agents = [s for s in fsa.states.values() if s.agent_calls]
        states_with_error_transitions = set()

        for transition in fsa.transitions:
            if transition.to_state in fsa.error_states:
                states_with_error_transitions.add(transition.from_state)

        coverage = len(states_with_error_transitions) / max(len(states_with_agents), 1)

        pattern = DetectedPattern(
            pattern_type=PatternType.ERROR_HANDLER,
            confidence=coverage,
            location='global',
            description=f'Error handling coverage: {coverage:.0%}',
            states_involved=list(fsa.error_states),
            recommendation='High coverage' if coverage > 0.7 else 'Consider adding more error handling',
        )
        report.patterns.append(pattern)

    def _detect_god_state_antipattern(self, fsa: FSAStructure, report: PatternAnalysisReport):
        """Detect God State anti-pattern."""
        for state_name, state in fsa.states.items():
            responsibility_score = (
                len(state.agent_calls) * 3
                + len(state.tool_calls) * 2
                + len(state.variables_written)
            )

            if responsibility_score > 15:
                pattern = DetectedPattern(
                    pattern_type=PatternType.GOD_STATE,
                    confidence=min(1.0, responsibility_score / 20),
                    location=state_name,
                    description=f'State has too many responsibilities (score: {responsibility_score})',
                    states_involved=[state_name],
                    is_antipattern=True,
                    recommendation='Break down into smaller, focused states',
                )
                report.patterns.append(pattern)

    def _detect_spaghetti_flow_antipattern(
        self, fsa: FSAStructure, report: PatternAnalysisReport
    ):
        """Detect spaghetti flow anti-pattern."""
        state_count = len(fsa.states)
        transition_count = len(fsa.transitions)

        if state_count > 0:
            ratio = transition_count / state_count

            if ratio > 4:  # Too many transitions per state
                pattern = DetectedPattern(
                    pattern_type=PatternType.SPAGHETTI_FLOW,
                    confidence=min(1.0, ratio / 6),
                    location='global',
                    description=f'Complex control flow: {transition_count} transitions for {state_count} states',
                    is_antipattern=True,
                    recommendation='Simplify control flow, reduce branching',
                )
                report.patterns.append(pattern)

    def _detect_lava_flow_antipattern(self, fsa: FSAStructure, report: PatternAnalysisReport):
        """Detect lava flow (dead code) anti-pattern."""
        if not fsa.entry_state:
            return

        reachable = self._find_reachable_states(fsa, fsa.entry_state)
        unreachable = set(fsa.states.keys()) - reachable

        if unreachable:
            pattern = DetectedPattern(
                pattern_type=PatternType.LAVA_FLOW,
                confidence=1.0,
                location='global',
                description=f'{len(unreachable)} unreachable states (dead code)',
                states_involved=list(unreachable),
                is_antipattern=True,
                recommendation='Remove unreachable states',
            )
            report.patterns.append(pattern)

    def _build_transition_graph(self, fsa: FSAStructure) -> Dict[str, List[str]]:
        """Build adjacency list representation of state transitions."""
        graph: Dict[str, List[str]] = {state: [] for state in fsa.states}
        for transition in fsa.transitions:
            if transition.from_state in graph:
                graph[transition.from_state].append(transition.to_state)
        return graph

    def _find_linear_sequence(
        self, start_state: str, graph: Dict[str, List[str]], all_states: Dict[str, FSAState]
    ) -> List[str]:
        """Find linear sequence of states (no branching)."""
        sequence = [start_state]
        current = start_state

        while True:
            if current not in graph:
                break

            next_states = graph[current]

            # Linear sequence means exactly one outgoing transition
            if len(next_states) != 1:
                break

            next_state = next_states[0]

            # Avoid cycles
            if next_state in sequence:
                break

            sequence.append(next_state)
            current = next_state

        return sequence

    def _find_reachable_states(self, fsa: FSAStructure, start_state: str) -> Set[str]:
        """Find all states reachable from start state."""
        reachable = set()
        stack = [start_state]

        while stack:
            state = stack.pop()
            if state in reachable:
                continue
            reachable.add(state)

            for transition in fsa.transitions:
                if transition.from_state == state and transition.to_state not in reachable:
                    stack.append(transition.to_state)

        return reachable

    def _calculate_pattern_frequency(self, report: PatternAnalysisReport):
        """Calculate frequency of each pattern type."""
        frequency: Dict[PatternType, int] = {}

        for pattern in report.patterns:
            pattern_type = pattern.pattern_type
            frequency[pattern_type] = frequency.get(pattern_type, 0) + 1

        report.pattern_frequency = frequency

    def _identify_common_patterns(self, report: PatternAnalysisReport):
        """Identify most common patterns across multiple FSAs."""
        if not report.pattern_frequency:
            return

        # Sort by frequency
        sorted_patterns = sorted(
            report.pattern_frequency.items(), key=lambda x: x[1], reverse=True
        )

        # Top 5 most common patterns
        report.common_patterns = [pattern_type for pattern_type, _ in sorted_patterns[:5]]

    def _identify_reusable_patterns(self, report: PatternAnalysisReport):
        """Identify patterns that could be extracted as reusable components."""
        reusable = []

        for pattern in report.patterns:
            # High-confidence design patterns are good candidates
            if (
                not pattern.is_antipattern
                and pattern.confidence > 0.8
                and len(pattern.states_involved) >= 3
            ):
                reusable.append(
                    f'{pattern.pattern_type.value}: {pattern.description}'
                )

        report.reusable_patterns = reusable

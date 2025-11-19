"""
FSA Performance Profiler - Profiles workflow execution for performance analysis.

Tracks execution time, state transitions, agent calls, and resource usage
to identify performance bottlenecks and optimization opportunities.
"""

import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from agno.workflows.fsa_meta_analyzer.static_analyzer import FSAStructure


@dataclass
class StateExecutionMetrics:
    """Metrics for a single state execution."""

    state_name: str
    entry_time: float
    exit_time: float
    duration: float
    agent_calls: int = 0
    tool_calls: int = 0
    transitions: int = 0
    error_count: int = 0
    memory_delta: Optional[int] = None


@dataclass
class TransitionMetrics:
    """Metrics for state transitions."""

    from_state: str
    to_state: str
    timestamp: float
    duration: float
    condition_met: Optional[str] = None


@dataclass
class PerformanceProfile:
    """Complete performance profile for an FSA execution."""

    workflow_name: str
    session_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    total_duration: float = 0.0
    state_metrics: Dict[str, List[StateExecutionMetrics]] = field(default_factory=dict)
    transition_metrics: List[TransitionMetrics] = field(default_factory=list)
    total_states_visited: int = 0
    total_transitions: int = 0
    total_agent_calls: int = 0
    total_errors: int = 0
    bottleneck_states: List[str] = field(default_factory=list)
    hot_paths: List[List[str]] = field(default_factory=list)


@dataclass
class PerformanceAnalysis:
    """Analysis results from performance profiling."""

    profile: PerformanceProfile
    average_state_duration: float = 0.0
    slowest_states: List[tuple[str, float]] = field(default_factory=list)
    fastest_states: List[tuple[str, float]] = field(default_factory=list)
    most_visited_states: List[tuple[str, int]] = field(default_factory=list)
    transition_frequency: Dict[str, int] = field(default_factory=dict)
    performance_score: float = 0.0
    recommendations: List[str] = field(default_factory=list)


class FSAPerformanceProfiler:
    """
    Profiler for tracking FSA execution performance.

    Note: This is a static profiler that analyzes FSA structure.
    For runtime profiling, this would need to be integrated with workflow execution.
    """

    def __init__(self):
        self.current_profile: Optional[PerformanceProfile] = None

    def analyze_performance_characteristics(self, fsa: FSAStructure) -> PerformanceAnalysis:
        """
        Analyze performance characteristics of an FSA structure.

        This performs static analysis to predict performance characteristics.

        Args:
            fsa: The FSA structure to analyze

        Returns:
            PerformanceAnalysis with predictions and recommendations
        """
        # Create mock profile for analysis
        profile = PerformanceProfile(
            workflow_name=fsa.workflow_name,
            session_id='static_analysis',
            start_time=datetime.now(),
        )

        analysis = PerformanceAnalysis(profile=profile)

        # Analyze state complexity for performance prediction
        self._analyze_state_complexity(fsa, analysis)

        # Analyze transition patterns
        self._analyze_transition_patterns(fsa, analysis)

        # Identify potential bottlenecks
        self._identify_bottlenecks(fsa, analysis)

        # Generate performance recommendations
        self._generate_performance_recommendations(fsa, analysis)

        # Calculate overall performance score
        analysis.performance_score = self._calculate_performance_score(fsa, analysis)

        return analysis

    def _analyze_state_complexity(self, fsa: FSAStructure, analysis: PerformanceAnalysis):
        """Analyze complexity of individual states."""
        state_complexity = {}

        for state_name, state in fsa.states.items():
            # Calculate complexity score for each state
            complexity = 0

            # Agent calls add significant time
            complexity += len(state.agent_calls) * 10

            # Tool calls add moderate time
            complexity += len(state.tool_calls) * 5

            # Variable operations add minimal time
            complexity += len(state.variables_written) * 1
            complexity += len(state.variables_read) * 0.5

            state_complexity[state_name] = complexity

        # Sort by complexity
        sorted_states = sorted(state_complexity.items(), key=lambda x: x[1], reverse=True)

        # Identify slowest states (highest complexity)
        analysis.slowest_states = [(name, score) for name, score in sorted_states[:5]]

        # Identify fastest states (lowest complexity)
        analysis.fastest_states = [(name, score) for name, score in sorted_states[-5:]]

    def _analyze_transition_patterns(self, fsa: FSAStructure, analysis: PerformanceAnalysis):
        """Analyze transition patterns to identify hot paths."""
        # Count transitions by source state
        transition_counts: Dict[str, int] = {}

        for transition in fsa.transitions:
            from_state = transition.from_state
            transition_counts[from_state] = transition_counts.get(from_state, 0) + 1

        analysis.transition_frequency = transition_counts

        # Identify most frequently transitioned states
        sorted_transitions = sorted(
            transition_counts.items(), key=lambda x: x[1], reverse=True
        )
        analysis.most_visited_states = sorted_transitions[:5]

        # Identify hot paths (sequences of states in loops)
        self._identify_hot_paths(fsa, analysis)

    def _identify_hot_paths(self, fsa: FSAStructure, analysis: PerformanceAnalysis):
        """Identify frequently executed paths (hot paths)."""
        # Build transition graph
        graph: Dict[str, List[str]] = {}
        for transition in fsa.transitions:
            if transition.from_state not in graph:
                graph[transition.from_state] = []
            graph[transition.from_state].append(transition.to_state)

        # Find paths in loops
        for loop_state in fsa.loop_states:
            path = self._trace_loop_path(loop_state, graph, max_depth=10)
            if path:
                analysis.hot_paths.append(path)

    def _trace_loop_path(
        self, start_state: str, graph: Dict[str, List[str]], max_depth: int = 10
    ) -> List[str]:
        """Trace a path from a loop state."""
        path = [start_state]
        current = start_state
        visited = {start_state}

        for _ in range(max_depth):
            if current not in graph or not graph[current]:
                break

            next_state = graph[current][0]  # Take first transition
            if next_state in visited:
                break

            path.append(next_state)
            visited.add(next_state)
            current = next_state

        return path if len(path) > 1 else []

    def _identify_bottlenecks(self, fsa: FSAStructure, analysis: PerformanceAnalysis):
        """Identify potential performance bottlenecks."""
        bottlenecks = []

        for state_name, state in fsa.states.items():
            # States with multiple agent calls are bottlenecks
            if len(state.agent_calls) >= 2:
                bottlenecks.append(state_name)
                continue

            # Loop states with agent calls are bottlenecks
            if state_name in fsa.loop_states and state.agent_calls:
                bottlenecks.append(state_name)
                continue

            # Decision states with many outgoing transitions
            outgoing_transitions = [
                t for t in fsa.transitions if t.from_state == state_name
            ]
            if len(outgoing_transitions) > 3:
                bottlenecks.append(state_name)

        analysis.profile.bottleneck_states = bottlenecks

    def _generate_performance_recommendations(
        self, fsa: FSAStructure, analysis: PerformanceAnalysis
    ):
        """Generate performance optimization recommendations."""
        recommendations = []

        # Check for sequential agent calls that could be parallelized
        for state_name, state in fsa.states.items():
            if len(state.agent_calls) > 1:
                recommendations.append(
                    f"State '{state_name}' has {len(state.agent_calls)} sequential agent calls. "
                    f"Consider parallelizing independent agent calls for better performance."
                )

        # Check for loops with agent calls
        for loop_state in fsa.loop_states:
            if loop_state in fsa.states and fsa.states[loop_state].agent_calls:
                recommendations.append(
                    f"Loop state '{loop_state}' contains agent calls. "
                    f"Consider batching operations or implementing caching to reduce overhead."
                )

        # Check for excessive state transitions
        if fsa.complexity_metrics.get('total_transitions', 0) > 20:
            recommendations.append(
                f"Workflow has {fsa.complexity_metrics['total_transitions']} transitions. "
                f"Consider simplifying control flow to reduce overhead."
            )

        # Check for excessive decision points
        if fsa.complexity_metrics.get('decision_points', 0) > 10:
            recommendations.append(
                f"Workflow has {fsa.complexity_metrics['decision_points']} decision points. "
                f"Consider using lookup tables or strategy patterns to reduce branching."
            )

        # Check for missing error handling
        if not fsa.error_states and fsa.agents:
            recommendations.append(
                "Workflow lacks error handling states. "
                "Adding try/except blocks can improve resilience without significant performance impact."
            )

        # Check for complex entry points
        if fsa.entry_state and fsa.entry_state in fsa.states:
            entry_state = fsa.states[fsa.entry_state]
            if len(entry_state.agent_calls) > 0:
                recommendations.append(
                    "Entry state contains agent calls. "
                    "Consider deferring heavy operations to later states for faster startup."
                )

        # Hot path optimization
        if analysis.hot_paths:
            recommendations.append(
                f"Identified {len(analysis.hot_paths)} hot paths in the workflow. "
                f"Focus optimization efforts on these frequently executed code paths."
            )

        # State complexity recommendations
        complex_states = [
            name for name, score in analysis.slowest_states if score > 50
        ]
        if complex_states:
            recommendations.append(
                f"States {complex_states} have high complexity scores. "
                f"Consider breaking them into smaller, more focused states."
            )

        analysis.recommendations = recommendations

    def _calculate_performance_score(
        self, fsa: FSAStructure, analysis: PerformanceAnalysis
    ) -> float:
        """
        Calculate overall performance score (0-100).

        Higher score = better predicted performance.
        """
        score = 100.0

        # Penalize for high complexity
        cyclomatic = fsa.complexity_metrics.get('cyclomatic_complexity', 0)
        if cyclomatic > 20:
            score -= (cyclomatic - 20) * 2
        elif cyclomatic > 10:
            score -= (cyclomatic - 10) * 1

        # Penalize for bottlenecks
        bottleneck_count = len(analysis.profile.bottleneck_states)
        score -= bottleneck_count * 5

        # Penalize for excessive transitions
        transition_count = fsa.complexity_metrics.get('total_transitions', 0)
        if transition_count > 30:
            score -= (transition_count - 30) * 0.5

        # Penalize for missing error handling
        if not fsa.error_states and fsa.agents:
            score -= 10

        # Bonus for simple, well-structured workflows
        if cyclomatic < 5 and transition_count < 10:
            score += 10

        # Ensure score is in valid range
        return max(0.0, min(100.0, score))


class RuntimeProfiler:
    """
    Runtime profiler for tracking actual execution.

    This would be integrated with workflow execution to track real performance data.
    """

    def __init__(self):
        self.profiles: List[PerformanceProfile] = []
        self.current_profile: Optional[PerformanceProfile] = None
        self.current_state: Optional[str] = None
        self.state_entry_time: Optional[float] = None

    def start_profiling(self, workflow_name: str, session_id: str):
        """Start profiling a workflow execution."""
        self.current_profile = PerformanceProfile(
            workflow_name=workflow_name,
            session_id=session_id,
            start_time=datetime.now(),
        )

    def enter_state(self, state_name: str):
        """Record entering a state."""
        if not self.current_profile:
            return

        self.current_state = state_name
        self.state_entry_time = time.time()

    def exit_state(self, state_name: str, agent_calls: int = 0, tool_calls: int = 0):
        """Record exiting a state."""
        if not self.current_profile or not self.state_entry_time:
            return

        exit_time = time.time()
        duration = exit_time - self.state_entry_time

        metrics = StateExecutionMetrics(
            state_name=state_name,
            entry_time=self.state_entry_time,
            exit_time=exit_time,
            duration=duration,
            agent_calls=agent_calls,
            tool_calls=tool_calls,
        )

        if state_name not in self.current_profile.state_metrics:
            self.current_profile.state_metrics[state_name] = []

        self.current_profile.state_metrics[state_name].append(metrics)
        self.current_profile.total_states_visited += 1

        self.current_state = None
        self.state_entry_time = None

    def record_transition(self, from_state: str, to_state: str, condition: Optional[str] = None):
        """Record a state transition."""
        if not self.current_profile:
            return

        metrics = TransitionMetrics(
            from_state=from_state,
            to_state=to_state,
            timestamp=time.time(),
            duration=0.0,
            condition_met=condition,
        )

        self.current_profile.transition_metrics.append(metrics)
        self.current_profile.total_transitions += 1

    def end_profiling(self) -> Optional[PerformanceProfile]:
        """End profiling and return the profile."""
        if not self.current_profile:
            return None

        self.current_profile.end_time = datetime.now()
        self.current_profile.total_duration = (
            self.current_profile.end_time - self.current_profile.start_time
        ).total_seconds()

        profile = self.current_profile
        self.profiles.append(profile)
        self.current_profile = None

        return profile

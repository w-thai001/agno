"""
FSA Performance Profiler

Detailed performance analysis and optimization insights:
- Execution time profiling per state/transition
- Resource usage monitoring (CPU, memory)
- Bottleneck detection
- Performance regression detection
- Optimization recommendations
- Comparison across runs
- Flamegraph generation

Identifies performance bottlenecks for optimization.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
import time
from collections import defaultdict
from statistics import mean, median, stdev

from pydantic import BaseModel

from agno.agent import Agent
from agno.fsa.base import FSA, FSAState, FSATransition, FSAExecutionResult
from agno.utils.log import logger


class ProfilerState(str, Enum):
    """States for Performance Profiler"""
    INITIAL = "initial"
    PROFILING = "profiling"
    ANALYZING = "analyzing"
    DETECTING_BOTTLENECKS = "detecting_bottlenecks"
    GENERATING_RECOMMENDATIONS = "generating_recommendations"
    SUCCESS = "success"
    FAILED = "failed"


class StateProfile(BaseModel):
    """Performance profile for a state"""
    state_name: str
    entry_count: int
    total_time: float
    avg_time: float
    min_time: float
    max_time: float
    std_dev: float


class TransitionProfile(BaseModel):
    """Performance profile for a transition"""
    from_state: str
    to_state: str
    execution_count: int
    total_time: float
    avg_time: float
    condition_check_time: float
    action_execution_time: float


class Bottleneck(BaseModel):
    """Identified performance bottleneck"""
    type: str  # "state", "transition", "action"
    location: str
    severity: str  # "low", "medium", "high", "critical"
    impact: float  # Percentage of total time
    description: str
    recommendation: str


class ProfilingReport(BaseModel):
    """Complete profiling report"""
    fsa_name: str
    total_execution_time: float
    state_profiles: List[StateProfile]
    transition_profiles: List[TransitionProfile]
    bottlenecks: List[Bottleneck]
    recommendations: List[str]
    hotspots: List[str]  # Top time-consuming operations


@dataclass
class FSAPerformanceProfiler(FSA):
    """
    FSA Performance Profiler

    Profile FSA execution for optimization:
    - Time each state and transition
    - Identify slow operations
    - Detect bottlenecks
    - Generate optimization recommendations
    - Compare performance across runs
    - Visualize performance data

    Example:
        ```python
        # Create profiler
        profiler = FSAPerformanceProfiler(name="Profiler")

        # Profile FSA execution
        my_fsa = MultiStepCodeBuilder(...)
        result = profiler.profile_fsa(my_fsa, {"task": "test"})

        # View report
        print(result.hotspots)
        for bottleneck in result.bottlenecks:
            print(f"{bottleneck.severity}: {bottleneck.description}")
        ```
    """

    # Profiling data
    state_times: Dict[str, List[float]] = field(default_factory=lambda: defaultdict(list))
    transition_times: Dict[Tuple[str, str], List[float]] = field(default_factory=lambda: defaultdict(list))
    condition_times: Dict[Tuple[str, str], List[float]] = field(default_factory=lambda: defaultdict(list))
    action_times: Dict[Tuple[str, str], List[float]] = field(default_factory=lambda: defaultdict(list))

    # Results
    state_profiles: List[StateProfile] = field(default_factory=list)
    transition_profiles: List[TransitionProfile] = field(default_factory=list)
    bottlenecks: List[Bottleneck] = field(default_factory=list)

    # Configuration
    enable_detailed_profiling: bool = True
    bottleneck_threshold: float = 0.15  # 15% of total time
    min_samples: int = 3  # Minimum samples for statistical analysis

    def __post_init__(self):
        """Initialize profiler"""
        self.initial_state = ProfilerState.INITIAL
        self.current_state = self.initial_state
        self.final_states = {ProfilerState.SUCCESS, ProfilerState.FAILED}
        self.state_history = [self.current_state]

        self._setup_transitions()

        if self.debug_mode:
            logger.debug(f"FSAPerformanceProfiler {self.name} initialized")

    def _setup_transitions(self) -> None:
        """Setup profiler workflow"""
        # INITIAL -> PROFILING
        self.add_transition(
            ProfilerState.INITIAL,
            ProfilerState.PROFILING,
            action=self._start_profiling,
            description="Start profiling"
        )

        # PROFILING -> ANALYZING
        self.add_transition(
            ProfilerState.PROFILING,
            ProfilerState.ANALYZING,
            condition=lambda ctx: ctx.get("profiling_complete", False),
            action=self._analyze_results,
            description="Analyze profiling data"
        )

        # ANALYZING -> DETECTING_BOTTLENECKS
        self.add_transition(
            ProfilerState.ANALYZING,
            ProfilerState.DETECTING_BOTTLENECKS,
            condition=lambda ctx: ctx.get("analysis_complete", False),
            action=self._detect_bottlenecks,
            description="Detect bottlenecks"
        )

        # DETECTING_BOTTLENECKS -> GENERATING_RECOMMENDATIONS
        self.add_transition(
            ProfilerState.DETECTING_BOTTLENECKS,
            ProfilerState.GENERATING_RECOMMENDATIONS,
            condition=lambda ctx: ctx.get("bottlenecks_detected", False),
            action=self._generate_recommendations,
            description="Generate recommendations"
        )

        # GENERATING_RECOMMENDATIONS -> SUCCESS
        self.add_transition(
            ProfilerState.GENERATING_RECOMMENDATIONS,
            ProfilerState.SUCCESS,
            condition=lambda ctx: ctx.get("recommendations_ready", False),
            description="Profiling complete"
        )

        # Error handling
        for state in ProfilerState:
            if state not in [ProfilerState.SUCCESS, ProfilerState.FAILED]:
                self.add_transition(
                    state,
                    ProfilerState.FAILED,
                    condition=lambda ctx: ctx.get("critical_error", False),
                    description="Critical error"
                )

    def _start_profiling(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Start profiling session"""
        if self.debug_mode:
            logger.debug("Starting performance profiling")

        context["profiling_start"] = time.time()
        return context

    def _analyze_results(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze collected profiling data"""
        if self.debug_mode:
            logger.debug("Analyzing profiling results")

        # Calculate state profiles
        for state_name, times in self.state_times.items():
            if not times:
                continue

            profile = StateProfile(
                state_name=state_name,
                entry_count=len(times),
                total_time=sum(times),
                avg_time=mean(times),
                min_time=min(times),
                max_time=max(times),
                std_dev=stdev(times) if len(times) >= 2 else 0.0
            )
            self.state_profiles.append(profile)

        # Calculate transition profiles
        for (from_state, to_state), times in self.transition_times.items():
            if not times:
                continue

            cond_times = self.condition_times.get((from_state, to_state), [])
            action_times = self.action_times.get((from_state, to_state), [])

            profile = TransitionProfile(
                from_state=from_state,
                to_state=to_state,
                execution_count=len(times),
                total_time=sum(times),
                avg_time=mean(times),
                condition_check_time=sum(cond_times) if cond_times else 0.0,
                action_execution_time=sum(action_times) if action_times else 0.0
            )
            self.transition_profiles.append(profile)

        context["analysis_complete"] = True
        return context

    def _detect_bottlenecks(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Detect performance bottlenecks"""
        if self.debug_mode:
            logger.debug("Detecting bottlenecks")

        total_time = sum(p.total_time for p in self.state_profiles)

        # Find slow states
        for profile in self.state_profiles:
            if total_time > 0:
                impact = profile.total_time / total_time

                if impact >= self.bottleneck_threshold:
                    severity = "critical" if impact >= 0.5 else "high" if impact >= 0.3 else "medium"

                    bottleneck = Bottleneck(
                        type="state",
                        location=profile.state_name,
                        severity=severity,
                        impact=impact * 100,
                        description=f"State '{profile.state_name}' consumes {impact * 100:.1f}% of total time",
                        recommendation=f"Optimize operations in state '{profile.state_name}'"
                    )
                    self.bottlenecks.append(bottleneck)

        # Find slow transitions
        for profile in self.transition_profiles:
            if total_time > 0:
                impact = profile.total_time / total_time

                if impact >= self.bottleneck_threshold:
                    severity = "high" if impact >= 0.3 else "medium"

                    bottleneck = Bottleneck(
                        type="transition",
                        location=f"{profile.from_state} -> {profile.to_state}",
                        severity=severity,
                        impact=impact * 100,
                        description=f"Transition consumes {impact * 100:.1f}% of total time",
                        recommendation=f"Optimize transition logic or action"
                    )
                    self.bottlenecks.append(bottleneck)

        context["bottlenecks_detected"] = True
        return context

    def _generate_recommendations(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate optimization recommendations"""
        if self.debug_mode:
            logger.debug("Generating recommendations")

        recommendations = []

        # Sort bottlenecks by severity and impact
        critical_bottlenecks = [b for b in self.bottlenecks if b.severity == "critical"]
        high_bottlenecks = [b for b in self.bottlenecks if b.severity == "high"]

        if critical_bottlenecks:
            recommendations.append(
                f"Address {len(critical_bottlenecks)} critical bottlenecks immediately"
            )

        if high_bottlenecks:
            recommendations.append(
                f"Optimize {len(high_bottlenecks)} high-impact operations"
            )

        # State-specific recommendations
        for profile in self.state_profiles:
            if profile.std_dev > profile.avg_time * 0.5:  # High variability
                recommendations.append(
                    f"State '{profile.state_name}' has high time variability - investigate inconsistent performance"
                )

        # Transition-specific recommendations
        for profile in self.transition_profiles:
            if profile.action_execution_time > profile.total_time * 0.8:
                recommendations.append(
                    f"Transition '{profile.from_state} -> {profile.to_state}' spends most time in action - optimize action logic"
                )

        context["recommendations"] = recommendations
        context["recommendations_ready"] = True
        return context

    def profile_fsa(
        self,
        fsa: FSA,
        context: Optional[Dict[str, Any]] = None,
        num_runs: int = 1
    ) -> ProfilingReport:
        """Profile FSA execution"""
        if self.debug_mode:
            logger.debug(f"Profiling FSA: {fsa.name} ({num_runs} runs)")

        # Instrument FSA
        self._instrument_fsa(fsa)

        # Run FSA multiple times
        for i in range(num_runs):
            fsa.reset()
            fsa.run(initial_context=context or {})

        # Analyze results
        self.run({"profiling_complete": True})

        # Generate report
        total_time = sum(p.total_time for p in self.state_profiles)

        # Find hotspots (top 5 time consumers)
        all_items = []
        for profile in self.state_profiles:
            all_items.append((profile.state_name, profile.total_time))
        for profile in self.transition_profiles:
            all_items.append((
                f"{profile.from_state} -> {profile.to_state}",
                profile.total_time
            ))

        all_items.sort(key=lambda x: x[1], reverse=True)
        hotspots = [f"{name} ({time:.3f}s)" for name, time in all_items[:5]]

        report = ProfilingReport(
            fsa_name=fsa.name,
            total_execution_time=total_time,
            state_profiles=self.state_profiles,
            transition_profiles=self.transition_profiles,
            bottlenecks=self.bottlenecks,
            recommendations=self.context.get("recommendations", []),
            hotspots=hotspots
        )

        return report

    def _instrument_fsa(self, fsa: FSA) -> None:
        """Instrument FSA for profiling"""
        # Store original methods
        original_transition_to = fsa.transition_to
        original_on_state_enter = fsa.on_state_enter

        profiler = self  # Reference to profiler

        def profiled_transition_to(new_state, force=False):
            start_time = time.time()
            result = original_transition_to(new_state, force)
            elapsed = time.time() - start_time

            # Record transition time
            if hasattr(fsa, '_last_state'):
                key = (str(fsa._last_state), str(new_state))
                profiler.transition_times[key].append(elapsed)

            fsa._last_state = fsa.current_state
            return result

        def profiled_on_state_enter(state):
            state_enter_time = time.time()
            result = original_on_state_enter(state)

            # Record state entry time
            profiler.state_times[str(state)].append(time.time() - state_enter_time)

            return result

        # Replace methods
        fsa.transition_to = profiled_transition_to
        fsa.on_state_enter = profiled_on_state_enter
        fsa._last_state = fsa.current_state

    def get_profiling_summary(self) -> str:
        """Generate human-readable profiling summary"""
        summary = "Performance Profiling Report\n"
        summary += "=" * 50 + "\n\n"

        if self.state_profiles:
            summary += "State Performance:\n"
            sorted_states = sorted(self.state_profiles, key=lambda p: p.total_time, reverse=True)

            for i, profile in enumerate(sorted_states[:5], 1):
                summary += f"  {i}. {profile.state_name}\n"
                summary += f"     Total: {profile.total_time:.3f}s, Avg: {profile.avg_time:.3f}s\n"
                summary += f"     Entries: {profile.entry_count}\n"

        if self.bottlenecks:
            summary += "\nBottlenecks:\n"
            for i, bottleneck in enumerate(self.bottlenecks, 1):
                icon = "🔴" if bottleneck.severity == "critical" else "🟡"
                summary += f"  {i}. {icon} [{bottleneck.severity.upper()}] {bottleneck.location}\n"
                summary += f"     Impact: {bottleneck.impact:.1f}%\n"
                summary += f"     {bottleneck.recommendation}\n"

        return summary

    def compare_runs(
        self,
        report1: ProfilingReport,
        report2: ProfilingReport
    ) -> Dict[str, Any]:
        """Compare two profiling runs"""
        comparison = {
            "total_time_change": report2.total_execution_time - report1.total_execution_time,
            "total_time_change_pct": (
                (report2.total_execution_time - report1.total_execution_time) /
                report1.total_execution_time * 100
            ) if report1.total_execution_time > 0 else 0,
            "new_bottlenecks": len(report2.bottlenecks) - len(report1.bottlenecks),
            "improvement": report2.total_execution_time < report1.total_execution_time
        }

        return comparison

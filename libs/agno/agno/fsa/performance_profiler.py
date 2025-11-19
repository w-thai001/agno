"""Performance Profiler FSA for tracking execution time, memory usage, and bottlenecks."""

import time
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from collections import defaultdict
import logging

from agno.fsa.base import FSA, Transition

# Optional psutil import for memory tracking
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

logger = logging.getLogger(__name__)


class ProfilerState(str, Enum):
    """States for Performance Profiler FSA."""

    INITIAL = "initial"
    PROFILING = "profiling"
    ANALYZING = "analyzing"
    GENERATING_REPORT = "generating_report"
    COMPLETED = "completed"


@dataclass
class ProfileEntry:
    """Single profiling entry."""

    name: str
    start_time: float
    end_time: float = 0.0
    duration: float = 0.0
    memory_start: float = 0.0
    memory_end: float = 0.0
    memory_delta: float = 0.0
    call_count: int = 1


@dataclass
class PerformanceReport:
    """Performance analysis report."""

    total_duration: float = 0.0
    total_memory_delta: float = 0.0
    entry_count: int = 0
    bottlenecks: List[Dict[str, Any]] = field(default_factory=list)
    top_time_consumers: List[Dict[str, Any]] = field(default_factory=list)
    top_memory_consumers: List[Dict[str, Any]] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)


class PerformanceProfiler(FSA):
    """FSA for profiling code performance."""

    def __init__(self):
        super().__init__(name="PerformanceProfiler", initial_state=ProfilerState.INITIAL)

        # Initialize context
        self.context = {
            "entries": {},
            "active_profiles": {},
            "report": None,
            "profiling_active": False,
        }

        # Setup transitions
        self._setup_transitions()

        # Process reference for memory tracking
        if HAS_PSUTIL:
            self.process = psutil.Process(os.getpid())
        else:
            self.process = None
            logger.warning("psutil not available, memory tracking disabled")

    def _setup_transitions(self):
        """Setup FSA transitions."""
        transitions = [
            # INITIAL -> PROFILING
            Transition(
                from_state=ProfilerState.INITIAL,
                to_state=ProfilerState.PROFILING,
                condition=lambda ctx: True,
                action=self._start_profiling,
            ),
            # PROFILING -> ANALYZING
            Transition(
                from_state=ProfilerState.PROFILING,
                to_state=ProfilerState.ANALYZING,
                condition=lambda ctx: not ctx["profiling_active"],
                action=self._analyze_results,
            ),
            # ANALYZING -> GENERATING_REPORT
            Transition(
                from_state=ProfilerState.ANALYZING,
                to_state=ProfilerState.GENERATING_REPORT,
                condition=lambda ctx: len(ctx["entries"]) > 0,
                action=self._generate_report,
            ),
            # GENERATING_REPORT -> COMPLETED
            Transition(
                from_state=ProfilerState.GENERATING_REPORT,
                to_state=ProfilerState.COMPLETED,
                condition=lambda ctx: ctx["report"] is not None,
                action=lambda ctx: ctx,
            ),
        ]

        self.register_transitions(transitions)

    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        if self.process is None:
            return 0.0
        try:
            return self.process.memory_info().rss / 1024 / 1024
        except Exception:
            return 0.0

    def _start_profiling(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Start profiling session."""
        logger.info("Starting profiling session...")
        context["profiling_active"] = True
        context["entries"] = {}
        context["active_profiles"] = {}
        return context

    def start(self, name: str) -> None:
        """Start profiling a code block."""
        if self.current_state == ProfilerState.INITIAL:
            self.transition(ProfilerState.PROFILING)

        entry = ProfileEntry(
            name=name,
            start_time=time.time(),
            memory_start=self._get_memory_usage(),
        )

        self.context["active_profiles"][name] = entry
        logger.debug(f"Started profiling: {name}")

    def stop(self, name: str) -> Optional[ProfileEntry]:
        """Stop profiling a code block."""
        if name not in self.context["active_profiles"]:
            logger.warning(f"No active profile found for: {name}")
            return None

        entry = self.context["active_profiles"].pop(name)
        entry.end_time = time.time()
        entry.duration = entry.end_time - entry.start_time
        entry.memory_end = self._get_memory_usage()
        entry.memory_delta = entry.memory_end - entry.memory_start

        # Store or update entry
        if name in self.context["entries"]:
            # Aggregate multiple calls
            existing = self.context["entries"][name]
            existing.duration += entry.duration
            existing.memory_delta += entry.memory_delta
            existing.call_count += 1
        else:
            self.context["entries"][name] = entry

        logger.debug(f"Stopped profiling: {name} ({entry.duration:.4f}s)")
        return entry

    def profile(self, func: Callable, *args, **kwargs) -> Any:
        """Profile a function call."""
        name = func.__name__
        self.start(name)
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            self.stop(name)

    def end_profiling(self) -> PerformanceReport:
        """End profiling session and generate report."""
        # Stop any active profiles
        for name in list(self.context["active_profiles"].keys()):
            self.stop(name)

        self.context["profiling_active"] = False

        # Trigger FSA transitions to complete analysis
        self.transition(ProfilerState.ANALYZING)
        self.transition(ProfilerState.GENERATING_REPORT)
        self.transition(ProfilerState.COMPLETED)

        return self.context["report"]

    def _analyze_results(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze profiling results."""
        logger.info("Analyzing profiling results...")

        entries = context["entries"]
        if not entries:
            logger.warning("No profiling entries to analyze")
            return context

        # Calculate totals
        total_duration = sum(e.duration for e in entries.values())
        total_memory = sum(e.memory_delta for e in entries.values())

        # Identify bottlenecks (>20% of total time or >50MB memory)
        bottlenecks = []
        for name, entry in entries.items():
            time_percentage = (entry.duration / total_duration * 100) if total_duration > 0 else 0

            if time_percentage > 20 or abs(entry.memory_delta) > 50:
                bottlenecks.append({
                    "name": name,
                    "duration": entry.duration,
                    "time_percentage": time_percentage,
                    "memory_delta": entry.memory_delta,
                    "call_count": entry.call_count,
                    "reason": "High execution time" if time_percentage > 20 else "High memory usage",
                })

        context["bottlenecks"] = bottlenecks
        context["total_duration"] = total_duration
        context["total_memory"] = total_memory

        logger.info(f"Found {len(bottlenecks)} bottlenecks")
        return context

    def _generate_report(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate performance report."""
        logger.info("Generating performance report...")

        entries = context["entries"]

        # Top time consumers
        top_time = sorted(
            entries.items(),
            key=lambda x: x[1].duration,
            reverse=True,
        )[:5]

        top_time_consumers = [
            {
                "name": name,
                "duration": entry.duration,
                "avg_duration": entry.duration / entry.call_count,
                "call_count": entry.call_count,
                "percentage": (entry.duration / context["total_duration"] * 100)
                if context["total_duration"] > 0
                else 0,
            }
            for name, entry in top_time
        ]

        # Top memory consumers
        top_memory = sorted(
            entries.items(),
            key=lambda x: abs(x[1].memory_delta),
            reverse=True,
        )[:5]

        top_memory_consumers = [
            {
                "name": name,
                "memory_delta": entry.memory_delta,
                "avg_memory": entry.memory_delta / entry.call_count,
                "call_count": entry.call_count,
            }
            for name, entry in top_memory
        ]

        # Generate summary
        summary = {
            "total_entries": len(entries),
            "total_duration": context["total_duration"],
            "total_memory_delta": context["total_memory"],
            "avg_duration": context["total_duration"] / len(entries) if entries else 0,
            "bottleneck_count": len(context.get("bottlenecks", [])),
        }

        report = PerformanceReport(
            total_duration=context["total_duration"],
            total_memory_delta=context["total_memory"],
            entry_count=len(entries),
            bottlenecks=context.get("bottlenecks", []),
            top_time_consumers=top_time_consumers,
            top_memory_consumers=top_memory_consumers,
            summary=summary,
        )

        context["report"] = report
        logger.info("Performance report generated")
        return context


# Context manager for easy profiling
class ProfileBlock:
    """Context manager for profiling code blocks."""

    def __init__(self, profiler: PerformanceProfiler, name: str):
        self.profiler = profiler
        self.name = name

    def __enter__(self):
        self.profiler.start(self.name)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.profiler.stop(self.name)
        return False


def print_performance_report(report: PerformanceReport, detailed: bool = False):
    """Print a formatted performance report."""
    print("\n" + "=" * 80)
    print("PERFORMANCE PROFILING REPORT")
    print("=" * 80)

    # Summary
    print("\n📊 SUMMARY:")
    print("-" * 80)
    print(f"  Total Profiled Operations: {report.summary['total_entries']}")
    print(f"  Total Execution Time:      {report.total_duration:.4f}s")
    print(f"  Total Memory Delta:        {report.total_memory_delta:+.2f} MB")
    print(f"  Average Operation Time:    {report.summary['avg_duration']:.4f}s")
    print(f"  Bottlenecks Detected:      {report.summary['bottleneck_count']}")

    # Top time consumers
    if report.top_time_consumers:
        print("\n⏱️  TOP TIME CONSUMERS:")
        print("-" * 80)
        for i, item in enumerate(report.top_time_consumers, 1):
            print(f"  {i}. {item['name']}")
            print(f"     Duration:    {item['duration']:.4f}s ({item['percentage']:.1f}%)")
            print(f"     Calls:       {item['call_count']}")
            print(f"     Avg/Call:    {item['avg_duration']:.4f}s")

    # Top memory consumers
    if report.top_memory_consumers:
        print("\n💾 TOP MEMORY CONSUMERS:")
        print("-" * 80)
        for i, item in enumerate(report.top_memory_consumers, 1):
            print(f"  {i}. {item['name']}")
            print(f"     Memory Delta: {item['memory_delta']:+.2f} MB")
            print(f"     Calls:        {item['call_count']}")
            print(f"     Avg/Call:     {item['avg_memory']:+.2f} MB")

    # Bottlenecks
    if report.bottlenecks:
        print("\n🔴 BOTTLENECKS DETECTED:")
        print("-" * 80)
        for i, item in enumerate(report.bottlenecks, 1):
            print(f"  {i}. {item['name']} - {item['reason']}")
            print(f"     Duration:     {item['duration']:.4f}s ({item['time_percentage']:.1f}%)")
            print(f"     Memory Delta: {item['memory_delta']:+.2f} MB")
            print(f"     Calls:        {item['call_count']}")
    else:
        print("\n✅ No significant bottlenecks detected!")

    print("\n" + "=" * 80 + "\n")

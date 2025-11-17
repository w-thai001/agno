"""
Risk Assessor FSA (Finite State Automaton)

A comprehensive risk assessment system that evaluates failure modes and risks for task execution.
Uses FSA principles to systematically analyze technical, resource, dependency, and timing risks.

Author: Agno Team
"""

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set
from uuid import uuid4

from pydantic import BaseModel, Field

from agno.utils.log import logger

if TYPE_CHECKING:
    from rich.console import Console


# ============================================================================
# FSA States
# ============================================================================


class RiskAssessorState(str, Enum):
    """FSA states for risk assessment workflow"""

    INITIAL = "initial"  # Starting state
    COLLECTING = "collecting"  # Collecting task information
    ANALYZING = "analyzing"  # Analyzing failure modes
    SCORING = "scoring"  # Computing risk scores
    MITIGATING = "mitigating"  # Generating mitigation strategies
    FINAL = "final"  # Assessment complete


# ============================================================================
# Risk Categories and Levels
# ============================================================================


class FailureMode(str, Enum):
    """Types of failure modes to analyze"""

    TECHNICAL = "technical"  # Technical/implementation failures
    RESOURCE = "resource"  # Resource availability/capacity failures
    DEPENDENCY = "dependency"  # External dependency failures
    TIMING = "timing"  # Timing/scheduling failures


class RiskLevel(str, Enum):
    """Overall risk severity levels"""

    CRITICAL = "critical"  # Risk score >= 16 (requires immediate attention)
    HIGH = "high"  # Risk score 12-15 (significant concerns)
    MEDIUM = "medium"  # Risk score 6-11 (moderate concerns)
    LOW = "low"  # Risk score 1-5 (minimal concerns)
    NEGLIGIBLE = "negligible"  # Risk score 0 (no identified risks)


# ============================================================================
# Data Models
# ============================================================================


@dataclass
class TaskContext:
    """Context information for risk assessment"""

    task_description: str
    context: Optional[Dict[str, Any]] = None
    dependencies: Optional[List[str]] = None
    constraints: Optional[Dict[str, Any]] = None
    environment: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Initialize default values for optional fields"""
        if self.context is None:
            self.context = {}
        if self.dependencies is None:
            self.dependencies = []
        if self.constraints is None:
            self.constraints = {}
        if self.environment is None:
            self.environment = {}


@dataclass
class FailureModeAnalysis:
    """Analysis of a specific failure mode"""

    failure_mode: FailureMode
    description: str
    probability: int  # 1-5 scale (1=rare, 5=certain)
    impact: int  # 1-5 scale (1=negligible, 5=catastrophic)
    risk_score: int = field(init=False)  # probability × impact
    indicators: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Compute risk score after initialization"""
        self.risk_score = self.probability * self.impact

        # Validate probability and impact ranges
        if not 1 <= self.probability <= 5:
            raise ValueError(f"Probability must be 1-5, got {self.probability}")
        if not 1 <= self.impact <= 5:
            raise ValueError(f"Impact must be 1-5, got {self.impact}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "failure_mode": self.failure_mode.value,
            "description": self.description,
            "probability": self.probability,
            "impact": self.impact,
            "risk_score": self.risk_score,
            "indicators": self.indicators,
            "examples": self.examples,
        }


@dataclass
class MitigationStrategy:
    """Recommended strategy to mitigate a specific risk"""

    failure_mode: FailureMode
    strategy: str
    priority: str  # "critical", "high", "medium", "low"
    effort: str  # "low", "medium", "high"
    effectiveness: str  # "low", "medium", "high"
    actions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "failure_mode": self.failure_mode.value,
            "strategy": self.strategy,
            "priority": self.priority,
            "effort": self.effort,
            "effectiveness": self.effectiveness,
            "actions": self.actions,
        }


@dataclass
class RiskAssessment:
    """Complete risk assessment for a task"""

    assessment_id: str
    task_context: TaskContext
    current_state: RiskAssessorState
    failure_modes: List[FailureModeAnalysis] = field(default_factory=list)
    mitigation_strategies: List[MitigationStrategy] = field(default_factory=list)
    overall_risk_score: int = 0
    overall_risk_level: RiskLevel = RiskLevel.NEGLIGIBLE
    confidence: float = 0.0  # 0.0-1.0
    timestamp: Optional[str] = None

    def compute_overall_risk(self):
        """Compute overall risk score and level from failure modes"""
        if not self.failure_modes:
            self.overall_risk_score = 0
            self.overall_risk_level = RiskLevel.NEGLIGIBLE
            return

        # Overall risk is the maximum risk score among all failure modes
        # This represents the "worst case" scenario
        self.overall_risk_score = max(fm.risk_score for fm in self.failure_modes)

        # Determine risk level based on score
        if self.overall_risk_score >= 16:
            self.overall_risk_level = RiskLevel.CRITICAL
        elif self.overall_risk_score >= 12:
            self.overall_risk_level = RiskLevel.HIGH
        elif self.overall_risk_score >= 6:
            self.overall_risk_level = RiskLevel.MEDIUM
        elif self.overall_risk_score >= 1:
            self.overall_risk_level = RiskLevel.LOW
        else:
            self.overall_risk_level = RiskLevel.NEGLIGIBLE

    def get_critical_risks(self) -> List[FailureModeAnalysis]:
        """Get all failure modes with critical risk scores (>=16)"""
        return [fm for fm in self.failure_modes if fm.risk_score >= 16]

    def get_high_risks(self) -> List[FailureModeAnalysis]:
        """Get all failure modes with high risk scores (12-15)"""
        return [fm for fm in self.failure_modes if 12 <= fm.risk_score < 16]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "assessment_id": self.assessment_id,
            "task_description": self.task_context.task_description,
            "current_state": self.current_state.value,
            "failure_modes": [fm.to_dict() for fm in self.failure_modes],
            "mitigation_strategies": [ms.to_dict() for ms in self.mitigation_strategies],
            "overall_risk_score": self.overall_risk_score,
            "overall_risk_level": self.overall_risk_level.value,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
        }

    def print_assessment(self, console: Optional["Console"] = None):
        """Print formatted risk assessment using rich console"""
        try:
            from rich.console import Console
            from rich.panel import Panel
            from rich.table import Table
            from rich.text import Text
        except ImportError:
            # Fallback to basic printing if rich is not available
            print(f"\n{'='*60}")
            print(f"Risk Assessment: {self.assessment_id}")
            print(f"{'='*60}")
            print(f"Task: {self.task_context.task_description}")
            print(f"Overall Risk: {self.overall_risk_level.value.upper()} (Score: {self.overall_risk_score}/25)")
            print(f"Confidence: {self.confidence:.2%}")
            print(f"\nFailure Modes Analyzed: {len(self.failure_modes)}")
            for fm in self.failure_modes:
                print(f"  - {fm.failure_mode.value.title()}: Score {fm.risk_score}/25 "
                      f"(P={fm.probability}, I={fm.impact})")
            print(f"\nMitigation Strategies: {len(self.mitigation_strategies)}")
            for ms in self.mitigation_strategies:
                print(f"  - {ms.strategy} (Priority: {ms.priority})")
            return

        # Use rich for formatted output
        if console is None:
            console = Console()

        # Risk level color mapping
        risk_colors = {
            RiskLevel.CRITICAL: "red",
            RiskLevel.HIGH: "orange3",
            RiskLevel.MEDIUM: "yellow",
            RiskLevel.LOW: "green",
            RiskLevel.NEGLIGIBLE: "grey50",
        }

        # Header
        console.print(f"\n[bold]Risk Assessment: {self.assessment_id}[/bold]")
        console.print(f"Task: {self.task_context.task_description}\n")

        # Overall Risk Panel
        risk_color = risk_colors.get(self.overall_risk_level, "white")
        overall_text = Text()
        overall_text.append("Overall Risk Level: ", style="bold")
        overall_text.append(self.overall_risk_level.value.upper(), style=f"bold {risk_color}")
        overall_text.append(f" (Score: {self.overall_risk_score}/25)\n", style="bold")
        overall_text.append(f"Confidence: {self.confidence:.1%}")

        console.print(Panel(overall_text, border_style=risk_color))

        # Failure Modes Table
        if self.failure_modes:
            table = Table(title="Failure Mode Analysis", show_header=True, header_style="bold")
            table.add_column("Failure Mode", style="cyan", width=15)
            table.add_column("Description", width=30)
            table.add_column("Prob", justify="center", width=5)
            table.add_column("Impact", justify="center", width=6)
            table.add_column("Score", justify="center", width=6)
            table.add_column("Level", width=10)

            for fm in self.failure_modes:
                # Determine risk level for this failure mode
                if fm.risk_score >= 16:
                    level_color = "red"
                    level_text = "CRITICAL"
                elif fm.risk_score >= 12:
                    level_color = "orange3"
                    level_text = "HIGH"
                elif fm.risk_score >= 6:
                    level_color = "yellow"
                    level_text = "MEDIUM"
                else:
                    level_color = "green"
                    level_text = "LOW"

                table.add_row(
                    fm.failure_mode.value.title(),
                    fm.description[:50] + "..." if len(fm.description) > 50 else fm.description,
                    str(fm.probability),
                    str(fm.impact),
                    f"[bold]{fm.risk_score}[/bold]",
                    f"[{level_color}]{level_text}[/{level_color}]"
                )

            console.print("\n", table)

        # Mitigation Strategies
        if self.mitigation_strategies:
            console.print("\n[bold]Mitigation Strategies:[/bold]")
            for i, ms in enumerate(self.mitigation_strategies, 1):
                priority_color = {
                    "critical": "red",
                    "high": "orange3",
                    "medium": "yellow",
                    "low": "green"
                }.get(ms.priority.lower(), "white")

                console.print(f"\n{i}. [{priority_color}]{ms.strategy}[/{priority_color}]")
                console.print(f"   Priority: [{priority_color}]{ms.priority.upper()}[/{priority_color}] | "
                            f"Effort: {ms.effort} | Effectiveness: {ms.effectiveness}")
                if ms.actions:
                    console.print(f"   Actions:")
                    for action in ms.actions:
                        console.print(f"   • {action}")


# ============================================================================
# Risk Assessor FSA
# ============================================================================


@dataclass
class RiskAssessorFSA:
    """
    Finite State Automaton for comprehensive risk assessment.

    Evaluates failure modes and risks for task execution through systematic
    state transitions: INITIAL -> COLLECTING -> ANALYZING -> SCORING -> MITIGATING -> FINAL
    """

    name: Optional[str] = "RiskAssessorFSA"
    fsa_id: Optional[str] = None
    debug_mode: bool = False

    # FSA state tracking
    current_state: RiskAssessorState = RiskAssessorState.INITIAL
    state_history: List[RiskAssessorState] = field(default_factory=list)

    # Assessment storage
    current_assessment: Optional[RiskAssessment] = None
    assessments: List[RiskAssessment] = field(default_factory=list)

    def __post_init__(self):
        """Initialize FSA after dataclass construction"""
        if self.fsa_id is None:
            self.fsa_id = str(uuid4())

        # Record initial state
        self.state_history.append(self.current_state)

        if self.debug_mode:
            logger.info(f"RiskAssessorFSA initialized: {self.fsa_id}")

    def transition_to(self, new_state: RiskAssessorState):
        """
        Transition to a new FSA state with validation.

        Args:
            new_state: Target state to transition to

        Raises:
            ValueError: If transition is invalid
        """
        # Define valid state transitions
        valid_transitions = {
            RiskAssessorState.INITIAL: {RiskAssessorState.COLLECTING},
            RiskAssessorState.COLLECTING: {RiskAssessorState.ANALYZING},
            RiskAssessorState.ANALYZING: {RiskAssessorState.SCORING},
            RiskAssessorState.SCORING: {RiskAssessorState.MITIGATING},
            RiskAssessorState.MITIGATING: {RiskAssessorState.FINAL},
            RiskAssessorState.FINAL: set(),  # Terminal state
        }

        # Validate transition
        if new_state not in valid_transitions.get(self.current_state, set()):
            raise ValueError(
                f"Invalid state transition: {self.current_state.value} -> {new_state.value}"
            )

        if self.debug_mode:
            logger.info(f"State transition: {self.current_state.value} -> {new_state.value}")

        self.current_state = new_state
        self.state_history.append(new_state)

        # Update current assessment state if exists
        if self.current_assessment:
            self.current_assessment.current_state = new_state

    def assess_risk(
        self,
        task_description: str,
        context: Optional[Dict[str, Any]] = None,
        dependencies: Optional[List[str]] = None,
        constraints: Optional[Dict[str, Any]] = None,
        environment: Optional[Dict[str, Any]] = None,
    ) -> RiskAssessment:
        """
        Execute complete risk assessment FSA workflow.

        Args:
            task_description: Description of the task to assess
            context: Additional context information
            dependencies: List of external dependencies
            constraints: Constraint information (time, resources, etc.)
            environment: Environment information

        Returns:
            RiskAssessment: Complete risk assessment with scores and mitigation strategies
        """
        # Reset to initial state for new assessment
        self.current_state = RiskAssessorState.INITIAL
        self.state_history = [self.current_state]

        # STATE 1: COLLECTING - Gather task information
        self.transition_to(RiskAssessorState.COLLECTING)
        task_context = self._collect_task_context(
            task_description, context, dependencies, constraints, environment
        )

        # Create new assessment
        assessment_id = f"risk-{uuid4().hex[:8]}"
        self.current_assessment = RiskAssessment(
            assessment_id=assessment_id,
            task_context=task_context,
            current_state=self.current_state,
        )

        # STATE 2: ANALYZING - Analyze failure modes
        self.transition_to(RiskAssessorState.ANALYZING)
        self._analyze_failure_modes()

        # STATE 3: SCORING - Compute risk scores
        self.transition_to(RiskAssessorState.SCORING)
        self._compute_risk_scores()

        # STATE 4: MITIGATING - Generate mitigation strategies
        self.transition_to(RiskAssessorState.MITIGATING)
        self._generate_mitigation_strategies()

        # STATE 5: FINAL - Complete assessment
        self.transition_to(RiskAssessorState.FINAL)
        self._finalize_assessment()

        # Store completed assessment
        self.assessments.append(self.current_assessment)

        if self.debug_mode:
            logger.info(f"Assessment complete: {assessment_id}")

        return self.current_assessment

    def _collect_task_context(
        self,
        task_description: str,
        context: Optional[Dict[str, Any]],
        dependencies: Optional[List[str]],
        constraints: Optional[Dict[str, Any]],
        environment: Optional[Dict[str, Any]],
    ) -> TaskContext:
        """STATE: COLLECTING - Collect and validate task context"""
        if self.debug_mode:
            logger.info(f"Collecting task context: {task_description[:50]}...")

        # Edge case: Empty task description
        if not task_description or not task_description.strip():
            raise ValueError("Task description cannot be empty")

        return TaskContext(
            task_description=task_description.strip(),
            context=context or {},
            dependencies=dependencies or [],
            constraints=constraints or {},
            environment=environment or {},
        )

    def _analyze_failure_modes(self):
        """STATE: ANALYZING - Analyze all failure modes"""
        if not self.current_assessment:
            raise RuntimeError("No current assessment available")

        task_context = self.current_assessment.task_context

        if self.debug_mode:
            logger.info("Analyzing failure modes...")

        # Analyze each failure mode category
        self.current_assessment.failure_modes = [
            self._analyze_technical_risks(task_context),
            self._analyze_resource_risks(task_context),
            self._analyze_dependency_risks(task_context),
            self._analyze_timing_risks(task_context),
        ]

    def _analyze_technical_risks(self, task_context: TaskContext) -> FailureModeAnalysis:
        """Analyze technical implementation risks"""
        description = task_context.task_description.lower()
        context_data = task_context.context

        # Default values
        probability = 2  # Moderate probability
        impact = 2  # Moderate impact
        indicators = []
        examples = []

        # Risk indicators - keywords that suggest technical complexity
        high_risk_keywords = {
            "api", "integration", "database", "migration", "refactor", "architecture",
            "security", "authentication", "encryption", "distributed", "concurrent",
            "multi-threaded", "real-time", "streaming", "complex", "algorithm"
        }

        medium_risk_keywords = {
            "new", "implement", "create", "build", "develop", "modify", "update",
            "feature", "service", "module", "component"
        }

        # Analyze task description
        words = set(description.split())
        high_risk_matches = words.intersection(high_risk_keywords)
        medium_risk_matches = words.intersection(medium_risk_keywords)

        # Adjust probability based on complexity indicators
        if high_risk_matches:
            probability = min(5, probability + len(high_risk_matches))
            indicators.extend([f"High complexity: {kw}" for kw in list(high_risk_matches)[:3]])
        elif medium_risk_matches:
            probability = min(4, probability + 1)
            indicators.append("Moderate complexity task")

        # Adjust impact based on context
        if context_data.get("critical", False) or context_data.get("production", False):
            impact = min(5, impact + 2)
            indicators.append("Critical/production environment")

        if context_data.get("user_facing", True):
            impact = min(5, impact + 1)
            indicators.append("User-facing changes")

        # Generate examples
        if "api" in description or "integration" in description:
            examples.append("API version incompatibility")
            examples.append("Network communication errors")
        if "database" in description or "migration" in description:
            examples.append("Data corruption or loss")
            examples.append("Schema migration failures")
        if "security" in description or "authentication" in description:
            examples.append("Security vulnerabilities")
            examples.append("Authentication bypass")

        # Default examples if none specific
        if not examples:
            examples = [
                "Implementation bugs or logical errors",
                "Edge cases not handled properly",
                "Performance issues under load",
            ]

        return FailureModeAnalysis(
            failure_mode=FailureMode.TECHNICAL,
            description="Technical implementation failures, bugs, or logical errors",
            probability=min(5, probability),
            impact=min(5, impact),
            indicators=indicators or ["Standard implementation task"],
            examples=examples,
        )

    def _analyze_resource_risks(self, task_context: TaskContext) -> FailureModeAnalysis:
        """Analyze resource availability and capacity risks"""
        constraints = task_context.constraints
        environment = task_context.environment

        probability = 2
        impact = 2
        indicators = []
        examples = []

        # Analyze resource constraints
        if "deadline" in constraints or "time_limit" in constraints:
            probability = min(5, probability + 1)
            indicators.append("Time constraints present")

        if "budget" in constraints or "cost_limit" in constraints:
            probability = min(5, probability + 1)
            indicators.append("Budget constraints present")

        # Analyze environment requirements
        if environment.get("scalability_required", False):
            impact = min(5, impact + 2)
            indicators.append("Scalability requirements")
            examples.append("Insufficient compute resources under load")

        if environment.get("high_availability", False):
            impact = min(5, impact + 1)
            indicators.append("High availability requirements")
            examples.append("Resource exhaustion during peak usage")

        # Check for resource-intensive keywords
        description = task_context.task_description.lower()
        resource_keywords = ["scale", "performance", "optimization", "memory", "cpu", "storage"]
        if any(kw in description for kw in resource_keywords):
            probability = min(5, probability + 1)
            indicators.append("Resource-intensive operations")

        # Default examples
        if not examples:
            examples = [
                "Insufficient memory or CPU capacity",
                "Storage limitations or quota exceeded",
                "Network bandwidth constraints",
            ]

        return FailureModeAnalysis(
            failure_mode=FailureMode.RESOURCE,
            description="Resource availability, capacity, or allocation failures",
            probability=min(5, probability),
            impact=min(5, impact),
            indicators=indicators or ["Standard resource requirements"],
            examples=examples,
        )

    def _analyze_dependency_risks(self, task_context: TaskContext) -> FailureModeAnalysis:
        """Analyze external dependency risks"""
        dependencies = task_context.dependencies
        context_data = task_context.context

        probability = 1
        impact = 2
        indicators = []
        examples = []

        # Analyze dependency count and types
        if dependencies:
            dep_count = len(dependencies)
            if dep_count > 10:
                probability = 5
                indicators.append(f"High dependency count ({dep_count})")
            elif dep_count > 5:
                probability = 4
                indicators.append(f"Moderate dependency count ({dep_count})")
            elif dep_count > 0:
                probability = 3
                indicators.append(f"Low dependency count ({dep_count})")

            # Analyze dependency types
            external_apis = [d for d in dependencies if "api" in d.lower() or "http" in d.lower()]
            if external_apis:
                impact = min(5, impact + 2)
                indicators.append(f"External API dependencies ({len(external_apis)})")
                examples.append("External API downtime or rate limiting")

            databases = [d for d in dependencies if "db" in d.lower() or "database" in d.lower()]
            if databases:
                impact = min(5, impact + 1)
                indicators.append(f"Database dependencies ({len(databases)})")
                examples.append("Database connection failures")

            third_party = [d for d in dependencies if "library" in d.lower() or "package" in d.lower()]
            if third_party:
                probability = min(5, probability + 1)
                indicators.append(f"Third-party library dependencies ({len(third_party)})")
                examples.append("Library version conflicts or deprecation")

        # Check context for dependency indicators
        if context_data.get("external_services", False):
            probability = min(5, probability + 2)
            impact = min(5, impact + 1)
            indicators.append("External service dependencies")

        # Default examples if none specific
        if not examples:
            examples = [
                "Third-party service unavailability",
                "Dependency version incompatibilities",
                "Network connectivity issues",
            ]

        return FailureModeAnalysis(
            failure_mode=FailureMode.DEPENDENCY,
            description="External dependency or integration point failures",
            probability=min(5, probability),
            impact=min(5, impact),
            indicators=indicators or ["No significant dependencies identified"],
            examples=examples,
        )

    def _analyze_timing_risks(self, task_context: TaskContext) -> FailureModeAnalysis:
        """Analyze timing and scheduling risks"""
        constraints = task_context.constraints
        description = task_context.task_description.lower()

        probability = 2
        impact = 2
        indicators = []
        examples = []

        # Analyze timing constraints
        if "deadline" in constraints:
            deadline_str = str(constraints["deadline"]).lower()
            if any(urgent in deadline_str for urgent in ["urgent", "asap", "immediate"]):
                probability = 5
                impact = min(5, impact + 2)
                indicators.append("Urgent deadline")
            else:
                probability = 3
                indicators.append("Standard deadline")

        if "time_limit" in constraints or "duration" in constraints:
            probability = min(5, probability + 1)
            indicators.append("Time limit specified")

        # Check for timing-sensitive keywords
        timing_keywords = [
            "schedule", "deadline", "urgent", "critical", "time-sensitive",
            "real-time", "immediate", "asap", "rush"
        ]
        if any(kw in description for kw in timing_keywords):
            probability = min(5, probability + 1)
            impact = min(5, impact + 1)
            indicators.append("Time-sensitive task")

        # Check for blocking/sequential dependencies
        if task_context.dependencies:
            probability = min(5, probability + 1)
            indicators.append("Sequential dependencies may cause delays")
            examples.append("Dependency delays cascade to task completion")

        # Check for coordination requirements
        if any(kw in description for kw in ["coordinate", "synchronize", "schedule", "meeting"]):
            probability = min(5, probability + 1)
            indicators.append("Coordination requirements")
            examples.append("Coordination delays or scheduling conflicts")

        # Default examples
        if not examples:
            examples = [
                "Task duration exceeds available time",
                "Unexpected delays in prerequisite tasks",
                "Resource contention causing schedule slips",
            ]

        return FailureModeAnalysis(
            failure_mode=FailureMode.TIMING,
            description="Timing, scheduling, or deadline-related failures",
            probability=min(5, probability),
            impact=min(5, impact),
            indicators=indicators or ["No significant timing constraints"],
            examples=examples,
        )

    def _compute_risk_scores(self):
        """STATE: SCORING - Compute overall risk scores and confidence"""
        if not self.current_assessment:
            raise RuntimeError("No current assessment available")

        if self.debug_mode:
            logger.info("Computing risk scores...")

        # Compute overall risk from failure modes
        self.current_assessment.compute_overall_risk()

        # Compute confidence based on information completeness
        confidence_factors = []

        # Factor 1: Task description completeness (0.3 weight)
        desc_len = len(self.current_assessment.task_context.task_description)
        desc_confidence = min(1.0, desc_len / 100)  # 100+ chars = full confidence
        confidence_factors.append(desc_confidence * 0.3)

        # Factor 2: Context availability (0.25 weight)
        has_context = bool(self.current_assessment.task_context.context)
        confidence_factors.append((1.0 if has_context else 0.5) * 0.25)

        # Factor 3: Dependency information (0.25 weight)
        has_deps = bool(self.current_assessment.task_context.dependencies)
        confidence_factors.append((1.0 if has_deps else 0.6) * 0.25)

        # Factor 4: Constraints/environment info (0.2 weight)
        has_constraints = bool(self.current_assessment.task_context.constraints)
        has_environment = bool(self.current_assessment.task_context.environment)
        env_confidence = 0.5 if has_constraints else 0.4
        env_confidence += 0.5 if has_environment else 0.4
        confidence_factors.append(min(1.0, env_confidence) * 0.2)

        # Total confidence
        self.current_assessment.confidence = sum(confidence_factors)

        if self.debug_mode:
            logger.info(
                f"Overall risk: {self.current_assessment.overall_risk_level.value} "
                f"(score: {self.current_assessment.overall_risk_score}/25, "
                f"confidence: {self.current_assessment.confidence:.2%})"
            )

    def _generate_mitigation_strategies(self):
        """STATE: MITIGATING - Generate mitigation strategies for identified risks"""
        if not self.current_assessment:
            raise RuntimeError("No current assessment available")

        if self.debug_mode:
            logger.info("Generating mitigation strategies...")

        strategies = []

        # Generate strategies for each failure mode
        for fm in self.current_assessment.failure_modes:
            # Skip low-risk failure modes
            if fm.risk_score < 6:
                continue

            strategy = self._generate_strategy_for_failure_mode(fm)
            if strategy:
                strategies.append(strategy)

        # Sort strategies by priority
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        strategies.sort(key=lambda s: priority_order.get(s.priority.lower(), 4))

        self.current_assessment.mitigation_strategies = strategies

    def _generate_strategy_for_failure_mode(
        self, failure_mode: FailureModeAnalysis
    ) -> Optional[MitigationStrategy]:
        """Generate mitigation strategy for a specific failure mode"""

        # Determine priority based on risk score
        if failure_mode.risk_score >= 16:
            priority = "critical"
        elif failure_mode.risk_score >= 12:
            priority = "high"
        elif failure_mode.risk_score >= 6:
            priority = "medium"
        else:
            priority = "low"

        # Generate mode-specific strategies
        if failure_mode.failure_mode == FailureMode.TECHNICAL:
            return MitigationStrategy(
                failure_mode=failure_mode.failure_mode,
                strategy="Implement comprehensive testing and code review",
                priority=priority,
                effort="medium",
                effectiveness="high",
                actions=[
                    "Write unit tests for all new functionality",
                    "Perform peer code review before deployment",
                    "Implement integration tests for critical paths",
                    "Add error handling and input validation",
                    "Use static analysis tools to detect potential issues",
                ],
            )

        elif failure_mode.failure_mode == FailureMode.RESOURCE:
            return MitigationStrategy(
                failure_mode=failure_mode.failure_mode,
                strategy="Establish resource monitoring and capacity planning",
                priority=priority,
                effort="medium",
                effectiveness="medium",
                actions=[
                    "Set up resource monitoring and alerting",
                    "Conduct capacity planning analysis",
                    "Implement auto-scaling where applicable",
                    "Establish resource quotas and limits",
                    "Create resource usage documentation",
                ],
            )

        elif failure_mode.failure_mode == FailureMode.DEPENDENCY:
            return MitigationStrategy(
                failure_mode=failure_mode.failure_mode,
                strategy="Implement dependency isolation and fallback mechanisms",
                priority=priority,
                effort="high",
                effectiveness="high",
                actions=[
                    "Implement circuit breakers for external services",
                    "Add retry logic with exponential backoff",
                    "Create fallback/degraded mode functionality",
                    "Monitor dependency health and SLAs",
                    "Maintain dependency version compatibility matrix",
                    "Consider dependency alternatives or redundancy",
                ],
            )

        elif failure_mode.failure_mode == FailureMode.TIMING:
            return MitigationStrategy(
                failure_mode=failure_mode.failure_mode,
                strategy="Implement schedule buffering and milestone tracking",
                priority=priority,
                effort="low",
                effectiveness="medium",
                actions=[
                    "Add time buffers to critical path tasks",
                    "Establish clear milestones and checkpoints",
                    "Implement progress tracking and reporting",
                    "Identify and communicate schedule risks early",
                    "Prepare contingency plans for schedule slips",
                ],
            )

        return None

    def _finalize_assessment(self):
        """STATE: FINAL - Finalize assessment with timestamp"""
        if not self.current_assessment:
            raise RuntimeError("No current assessment available")

        from datetime import datetime, timezone

        self.current_assessment.timestamp = datetime.now(timezone.utc).isoformat()

        if self.debug_mode:
            logger.info(f"Assessment finalized: {self.current_assessment.assessment_id}")

    def get_assessment_by_id(self, assessment_id: str) -> Optional[RiskAssessment]:
        """Retrieve a specific assessment by ID"""
        for assessment in self.assessments:
            if assessment.assessment_id == assessment_id:
                return assessment
        return None

    def get_all_assessments(self) -> List[RiskAssessment]:
        """Get all completed assessments"""
        return self.assessments.copy()

    def reset(self):
        """Reset FSA to initial state"""
        self.current_state = RiskAssessorState.INITIAL
        self.state_history = [self.current_state]
        self.current_assessment = None

        if self.debug_mode:
            logger.info("FSA reset to initial state")


# ============================================================================
# Convenience Functions
# ============================================================================


def quick_risk_assessment(
    task_description: str,
    dependencies: Optional[List[str]] = None,
    critical: bool = False,
    print_result: bool = True,
) -> RiskAssessment:
    """
    Convenience function for quick risk assessment.

    Args:
        task_description: Task to assess
        dependencies: Optional list of dependencies
        critical: Whether this is a critical task
        print_result: Whether to print formatted results

    Returns:
        RiskAssessment: Complete risk assessment
    """
    fsa = RiskAssessorFSA()

    context = {"critical": critical} if critical else None

    assessment = fsa.assess_risk(
        task_description=task_description,
        dependencies=dependencies,
        context=context,
    )

    if print_result:
        assessment.print_assessment()

    return assessment

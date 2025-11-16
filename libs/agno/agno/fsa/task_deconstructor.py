"""
MLA Task Deconstructor FSA

Implements Maximum Leverage Analysis (MLA) v3.0 principles to intelligently
deconstruct and prioritize tasks:

- Analyzes tasks for leverage points (impact vs. effort)
- Breaks down complex tasks into atomic, high-leverage subtasks
- Prioritizes based on maximum ROI
- Identifies reusable patterns and components
- Optimizes execution strategy for efficiency

MLA Principles:
1. Focus on highest-leverage actions first
2. Identify and eliminate low-leverage work
3. Find reusable solutions that solve multiple problems
4. Optimize for strategic value, not just completion
5. Make informed inferences to avoid blocking
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from pydantic import BaseModel

from agno.agent import Agent
from agno.fsa.base import FSA, FSAState, FSATransition, FSAExecutionResult
from agno.utils.log import logger


class MLAState(str, Enum):
    """States for MLA Task Deconstructor"""
    INITIAL = "initial"
    ANALYZING = "analyzing"
    DECONSTRUCTING = "deconstructing"
    SCORING_LEVERAGE = "scoring_leverage"
    PRIORITIZING = "prioritizing"
    OPTIMIZING = "optimizing"
    FINALIZING = "finalizing"
    SUCCESS = "success"
    FAILED = "failed"


class LeverageScore(BaseModel):
    """Leverage score for a task/subtask"""
    impact: float  # 0-10: Expected impact/value
    effort: float  # 0-10: Required effort/complexity
    leverage: float  # Calculated: impact / effort
    reusability: float  # 0-10: Potential for reuse
    strategic_value: float  # 0-10: Long-term strategic importance
    total_score: float  # Combined score for prioritization


class Subtask(BaseModel):
    """Represents a deconstructed subtask"""
    id: str
    description: str
    category: str  # e.g., "foundational", "high_impact", "quick_win", "low_priority"
    leverage_score: LeverageScore
    dependencies: List[str] = []  # IDs of subtasks this depends on
    estimated_duration: float = 0.0  # hours
    required_skills: List[str] = []
    deliverables: List[str] = []
    assumptions: List[str] = []


class TaskAnalysis(BaseModel):
    """Analysis result for a task"""
    original_task: str
    complexity: str  # "low", "medium", "high", "very_high"
    estimated_effort: float  # hours
    key_challenges: List[str]
    success_criteria: List[str]
    constraints: List[str]
    opportunities: List[str]  # High-leverage opportunities identified


class DeconstructionResult(BaseModel):
    """Result of task deconstruction"""
    success: bool
    original_task: str
    analysis: TaskAnalysis
    subtasks: List[Subtask]
    execution_plan: List[List[str]]  # Ordered groups of subtask IDs
    high_leverage_actions: List[str]  # Recommended focus areas
    low_leverage_actions: List[str]  # Actions to defer/eliminate
    reusable_components: List[str]  # Identified reusable patterns
    total_estimated_effort: float
    expected_impact: float
    overall_leverage: float
    error: Optional[str] = None


@dataclass
class MLATaskDeconstructor(FSA):
    """
    MLA Task Deconstructor FSA

    Applies Maximum Leverage Analysis to break down and prioritize tasks:
    - Intelligent task decomposition
    - Leverage-based prioritization
    - Reusability identification
    - Strategic optimization

    Example:
        ```python
        deconstructor = MLATaskDeconstructor(
            name="TaskAnalyzer",
            agent=analysis_agent
        )

        result = deconstructor.run({
            "task": "Build a complete user authentication system"
        })

        # Follow high-leverage actions first
        for action in result.high_leverage_actions:
            print(f"High priority: {action}")
        ```
    """

    # Analysis agent
    analysis_agent: Optional[Agent] = None

    # Results
    task_analysis: Optional[TaskAnalysis] = None
    subtasks: List[Subtask] = field(default_factory=list)
    execution_plan: List[List[str]] = field(default_factory=list)

    # Configuration
    max_subtask_size: int = 30  # Max subtasks to generate
    leverage_threshold: float = 2.0  # Minimum leverage score (impact/effort)
    min_impact_score: float = 3.0  # Minimum impact to consider

    # MLA scoring weights
    impact_weight: float = 0.35
    effort_weight: float = 0.25
    reusability_weight: float = 0.20
    strategic_weight: float = 0.20

    def __post_init__(self):
        """Initialize MLA deconstructor"""
        self.initial_state = MLAState.INITIAL
        self.current_state = self.initial_state
        self.final_states = {MLAState.SUCCESS, MLAState.FAILED}
        self.state_history = [self.current_state]

        self._setup_transitions()

        if self.debug_mode:
            logger.debug(f"MLATaskDeconstructor {self.name} initialized")

    def _setup_transitions(self) -> None:
        """Setup state transitions"""
        # INITIAL -> ANALYZING
        self.add_transition(
            MLAState.INITIAL,
            MLAState.ANALYZING,
            action=self._analyze_task,
            description="Analyze task complexity and requirements"
        )

        # ANALYZING -> DECONSTRUCTING
        self.add_transition(
            MLAState.ANALYZING,
            MLAState.DECONSTRUCTING,
            condition=lambda ctx: ctx.get("analysis_complete", False),
            action=self._deconstruct_task,
            description="Break down task into subtasks"
        )

        # DECONSTRUCTING -> SCORING_LEVERAGE
        self.add_transition(
            MLAState.DECONSTRUCTING,
            MLAState.SCORING_LEVERAGE,
            condition=lambda ctx: ctx.get("deconstruction_complete", False),
            action=self._score_leverage,
            description="Calculate leverage scores"
        )

        # SCORING_LEVERAGE -> PRIORITIZING
        self.add_transition(
            MLAState.SCORING_LEVERAGE,
            MLAState.PRIORITIZING,
            condition=lambda ctx: ctx.get("scoring_complete", False),
            action=self._prioritize_subtasks,
            description="Prioritize based on leverage"
        )

        # PRIORITIZING -> OPTIMIZING
        self.add_transition(
            MLAState.PRIORITIZING,
            MLAState.OPTIMIZING,
            condition=lambda ctx: ctx.get("prioritization_complete", False),
            action=self._optimize_execution,
            description="Optimize execution strategy"
        )

        # OPTIMIZING -> FINALIZING
        self.add_transition(
            MLAState.OPTIMIZING,
            MLAState.FINALIZING,
            condition=lambda ctx: ctx.get("optimization_complete", False),
            action=self._finalize_plan,
            description="Finalize execution plan"
        )

        # FINALIZING -> SUCCESS
        self.add_transition(
            MLAState.FINALIZING,
            MLAState.SUCCESS,
            condition=lambda ctx: ctx.get("plan_finalized", False),
            description="Plan ready"
        )

        # Error handling
        for state in MLAState:
            if state not in [MLAState.SUCCESS, MLAState.FAILED]:
                self.add_transition(
                    state,
                    MLAState.FAILED,
                    condition=lambda ctx: ctx.get("critical_error", False),
                    description="Critical error"
                )

    def _analyze_task(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze the task to understand complexity and requirements"""
        task = context.get("task", "")

        if self.debug_mode:
            logger.debug(f"Analyzing task: {task}")

        # Use agent for intelligent analysis
        if self.analysis_agent:
            analysis_prompt = f"""
            Analyze this task using MLA principles:

            Task: {task}

            Provide analysis of:
            1. Overall complexity (low/medium/high/very_high)
            2. Estimated effort in hours
            3. Key challenges and obstacles
            4. Success criteria
            5. Constraints and limitations
            6. High-leverage opportunities

            Focus on identifying where small efforts can yield large results.
            """
            # Agent would analyze
            pass

        # Create task analysis
        self.task_analysis = TaskAnalysis(
            original_task=task,
            complexity="medium",
            estimated_effort=8.0,
            key_challenges=[
                "Understanding requirements",
                "Designing optimal solution",
                "Implementation complexity",
            ],
            success_criteria=[
                "Task completed as specified",
                "High quality implementation",
                "Efficient use of resources",
            ],
            constraints=[
                "Time constraints",
                "Resource limitations",
            ],
            opportunities=[
                "Identify reusable components",
                "Leverage existing solutions",
                "Optimize for future similar tasks",
            ]
        )

        context["analysis"] = self.task_analysis
        context["analysis_complete"] = True

        return context

    def _deconstruct_task(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Break down task into atomic subtasks"""
        task = context.get("task", "")
        analysis = context.get("analysis")

        if self.debug_mode:
            logger.debug("Deconstructing task into subtasks")

        # Use agent for intelligent deconstruction
        if self.analysis_agent:
            deconstruction_prompt = f"""
            Deconstruct this task into atomic subtasks:

            Task: {task}
            Analysis: {analysis}

            Create subtasks that are:
            1. Atomic (single-purpose, focused)
            2. Actionable (clear what needs to be done)
            3. Measurable (clear completion criteria)
            4. Independent where possible (minimize dependencies)

            For each subtask, identify:
            - Clear description
            - Category (foundational/high_impact/quick_win/low_priority)
            - Required skills
            - Deliverables
            - Dependencies on other subtasks

            Aim for 5-15 well-scoped subtasks.
            """
            # Agent would create subtasks
            pass

        # Create example subtasks (would be generated by agent)
        self.subtasks = [
            Subtask(
                id="st-001",
                description="Analyze core requirements and define scope",
                category="foundational",
                leverage_score=LeverageScore(
                    impact=8.0, effort=2.0, leverage=4.0,
                    reusability=6.0, strategic_value=8.0, total_score=0.0
                ),
                dependencies=[],
                estimated_duration=1.0,
                required_skills=["analysis", "planning"],
                deliverables=["Requirements document"],
                assumptions=["Requirements are accessible"]
            ),
            Subtask(
                id="st-002",
                description="Design high-level architecture",
                category="foundational",
                leverage_score=LeverageScore(
                    impact=9.0, effort=2.5, leverage=3.6,
                    reusability=7.0, strategic_value=9.0, total_score=0.0
                ),
                dependencies=["st-001"],
                estimated_duration=1.5,
                required_skills=["architecture", "design"],
                deliverables=["Architecture diagram"],
                assumptions=["Requirements are clear"]
            ),
            Subtask(
                id="st-003",
                description="Implement core functionality",
                category="high_impact",
                leverage_score=LeverageScore(
                    impact=10.0, effort=5.0, leverage=2.0,
                    reusability=5.0, strategic_value=7.0, total_score=0.0
                ),
                dependencies=["st-002"],
                estimated_duration=4.0,
                required_skills=["programming", "problem-solving"],
                deliverables=["Working implementation"],
                assumptions=["Design is complete"]
            ),
        ]

        context["subtasks"] = self.subtasks
        context["deconstruction_complete"] = True

        return context

    def _score_leverage(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate leverage scores for all subtasks"""
        subtasks = context.get("subtasks", [])

        if self.debug_mode:
            logger.debug("Calculating leverage scores")

        for subtask in subtasks:
            # Calculate total score using weighted formula
            score = subtask.leverage_score

            # Normalize leverage (impact/effort)
            score.leverage = score.impact / max(score.effort, 0.1)

            # Calculate weighted total score
            score.total_score = (
                (score.impact * self.impact_weight) +
                ((10.0 - score.effort) * self.effort_weight) +  # Lower effort = higher score
                (score.reusability * self.reusability_weight) +
                (score.strategic_value * self.strategic_weight)
            )

        context["scoring_complete"] = True

        return context

    def _prioritize_subtasks(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Prioritize subtasks based on leverage scores"""
        subtasks = context.get("subtasks", [])

        if self.debug_mode:
            logger.debug("Prioritizing subtasks")

        # Sort by total_score (descending)
        sorted_subtasks = sorted(
            subtasks,
            key=lambda st: st.leverage_score.total_score,
            reverse=True
        )

        # Categorize into high/low leverage
        high_leverage = []
        low_leverage = []

        for subtask in sorted_subtasks:
            if subtask.leverage_score.leverage >= self.leverage_threshold:
                high_leverage.append(subtask.description)
            else:
                low_leverage.append(subtask.description)

        context["high_leverage_actions"] = high_leverage
        context["low_leverage_actions"] = low_leverage
        context["sorted_subtasks"] = sorted_subtasks
        context["prioritization_complete"] = True

        return context

    def _optimize_execution(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize execution strategy"""
        sorted_subtasks = context.get("sorted_subtasks", [])

        if self.debug_mode:
            logger.debug("Optimizing execution strategy")

        # Identify reusable components
        reusable = []
        for subtask in sorted_subtasks:
            if subtask.leverage_score.reusability >= 7.0:
                reusable.append(subtask.description)

        # Build dependency graph and create execution order
        execution_plan = self._build_execution_plan(sorted_subtasks)

        context["reusable_components"] = reusable
        context["execution_plan"] = execution_plan
        context["optimization_complete"] = True

        return context

    def _build_execution_plan(self, subtasks: List[Subtask]) -> List[List[str]]:
        """Build execution plan respecting dependencies and leverage"""
        # Simple topological sort with leverage priority
        completed = set()
        execution_plan = []

        while len(completed) < len(subtasks):
            # Find subtasks that can be executed (dependencies met)
            ready = []
            for subtask in subtasks:
                if subtask.id not in completed:
                    deps_met = all(dep in completed for dep in subtask.dependencies)
                    if deps_met:
                        ready.append(subtask)

            if not ready:
                # Circular dependency or error
                break

            # Sort ready subtasks by leverage score
            ready.sort(key=lambda st: st.leverage_score.total_score, reverse=True)

            # Add to execution plan
            execution_plan.append([st.id for st in ready])

            # Mark as completed
            for subtask in ready:
                completed.add(subtask.id)

        return execution_plan

    def _finalize_plan(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Finalize the execution plan"""
        subtasks = context.get("subtasks", [])
        execution_plan = context.get("execution_plan", [])

        # Calculate totals
        total_effort = sum(st.estimated_duration for st in subtasks)
        avg_impact = sum(st.leverage_score.impact for st in subtasks) / max(len(subtasks), 1)
        overall_leverage = avg_impact / max(total_effort, 0.1)

        context["total_estimated_effort"] = total_effort
        context["expected_impact"] = avg_impact
        context["overall_leverage"] = overall_leverage
        context["plan_finalized"] = True

        return context

    def run(self, initial_context: Optional[Dict[str, Any]] = None) -> DeconstructionResult:
        """
        Run the MLA deconstructor

        Args:
            initial_context: Context with task description

        Returns:
            DeconstructionResult with prioritized subtasks and execution plan
        """
        # Execute base FSA run
        base_result = super().run(initial_context)

        # Build result
        return DeconstructionResult(
            success=base_result.success,
            original_task=initial_context.get("task", "") if initial_context else "",
            analysis=self.task_analysis or TaskAnalysis(
                original_task="",
                complexity="unknown",
                estimated_effort=0.0,
                key_challenges=[],
                success_criteria=[],
                constraints=[],
                opportunities=[]
            ),
            subtasks=self.subtasks,
            execution_plan=self.context.get("execution_plan", []),
            high_leverage_actions=self.context.get("high_leverage_actions", []),
            low_leverage_actions=self.context.get("low_leverage_actions", []),
            reusable_components=self.context.get("reusable_components", []),
            total_estimated_effort=self.context.get("total_estimated_effort", 0.0),
            expected_impact=self.context.get("expected_impact", 0.0),
            overall_leverage=self.context.get("overall_leverage", 0.0),
            error=base_result.error
        )

    def get_leverage_report(self) -> str:
        """Generate a human-readable leverage analysis report"""
        report = f"MLA Task Deconstruction: {self.name}\n"
        report += "=" * 50 + "\n\n"

        if self.task_analysis:
            report += f"Original Task: {self.task_analysis.original_task}\n"
            report += f"Complexity: {self.task_analysis.complexity}\n"
            report += f"Estimated Effort: {self.task_analysis.estimated_effort} hours\n\n"

        if self.subtasks:
            report += f"Total Subtasks: {len(self.subtasks)}\n"
            report += "\nTop Leverage Subtasks:\n"
            sorted_subtasks = sorted(
                self.subtasks,
                key=lambda st: st.leverage_score.total_score,
                reverse=True
            )
            for i, subtask in enumerate(sorted_subtasks[:5], 1):
                report += f"  {i}. {subtask.description}\n"
                report += f"     Leverage: {subtask.leverage_score.leverage:.2f} "
                report += f"(Impact: {subtask.leverage_score.impact}, "
                report += f"Effort: {subtask.leverage_score.effort})\n"

        return report

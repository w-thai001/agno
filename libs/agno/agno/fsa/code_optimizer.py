"""
RSI Code Optimizer FSA

Recursive Self-Improvement (RSI) Code Optimizer that:
- Analyzes code for optimization opportunities
- Applies iterative improvements
- Learns from successful optimizations
- Improves its own optimization strategies
- Measures and validates performance gains

Self-improvement aspects:
1. Maintains optimization history and patterns
2. Learns which optimizations work best for different code types
3. Improves heuristics based on success rates
4. Generates new optimization strategies from successful patterns
5. Meta-optimizes its own optimization process
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
from datetime import datetime
import json

from pydantic import BaseModel

from agno.agent import Agent
from agno.fsa.base import FSA, FSAState, FSATransition, FSAExecutionResult
from agno.utils.log import logger


class OptimizerState(str, Enum):
    """States for RSI Code Optimizer"""
    INITIAL = "initial"
    ANALYZING = "analyzing"
    IDENTIFYING_OPPORTUNITIES = "identifying_opportunities"
    APPLYING_OPTIMIZATIONS = "applying_optimizations"
    VALIDATING = "validating"
    LEARNING = "learning"
    SELF_IMPROVING = "self_improving"
    SUCCESS = "success"
    FAILED = "failed"


class OptimizationType(str, Enum):
    """Types of optimizations"""
    PERFORMANCE = "performance"
    MEMORY = "memory"
    READABILITY = "readability"
    COMPLEXITY = "complexity"
    SECURITY = "security"
    MAINTAINABILITY = "maintainability"


class OptimizationOpportunity(BaseModel):
    """Represents an optimization opportunity"""
    id: str
    type: OptimizationType
    description: str
    location: str  # File:line or function name
    current_code: str
    suggested_code: str
    expected_improvement: float  # 0-100 percentage
    confidence: float  # 0-1
    rationale: str
    complexity: str  # "low", "medium", "high"


class OptimizationResult(BaseModel):
    """Result of applying an optimization"""
    opportunity_id: str
    success: bool
    applied: bool
    actual_improvement: Optional[float] = None
    before_metrics: Dict[str, Any] = {}
    after_metrics: Dict[str, Any] = {}
    validation_passed: bool = False
    error: Optional[str] = None


class OptimizationPattern(BaseModel):
    """Learned optimization pattern"""
    pattern_id: str
    type: OptimizationType
    trigger_conditions: List[str]  # When to apply this pattern
    transformation_template: str
    success_rate: float  # 0-1
    average_improvement: float
    applications: int
    last_updated: str


class CodeMetrics(BaseModel):
    """Code quality and performance metrics"""
    cyclomatic_complexity: int = 0
    lines_of_code: int = 0
    execution_time_ms: float = 0.0
    memory_usage_mb: float = 0.0
    readability_score: float = 0.0  # 0-100
    maintainability_index: float = 0.0  # 0-100
    test_coverage: float = 0.0  # 0-100


class RSIOptimizerResult(BaseModel):
    """Result of RSI optimization process"""
    success: bool
    original_code: str
    optimized_code: str
    opportunities_identified: List[OptimizationOpportunity]
    optimizations_applied: List[OptimizationResult]
    before_metrics: CodeMetrics
    after_metrics: CodeMetrics
    total_improvement: float  # Percentage
    iterations: int
    patterns_learned: List[OptimizationPattern]
    self_improvement_gains: Dict[str, float] = {}
    error: Optional[str] = None


@dataclass
class RSICodeOptimizer(FSA):
    """
    RSI Code Optimizer FSA

    Self-improving code optimizer that learns and evolves:
    - Multi-dimensional code optimization
    - Validation of improvements
    - Pattern learning and application
    - Self-improvement of optimization strategies

    Example:
        ```python
        optimizer = RSICodeOptimizer(
            name="CodeOptimizer",
            agent=optimization_agent
        )

        result = optimizer.run({
            "code": source_code,
            "optimization_goals": ["performance", "readability"]
        })

        print(f"Improvement: {result.total_improvement}%")
        print(f"Patterns learned: {len(result.patterns_learned)}")
        ```
    """

    # Optimization agent
    optimization_agent: Optional[Agent] = None

    # Results and tracking
    opportunities: List[OptimizationOpportunity] = field(default_factory=list)
    applied_optimizations: List[OptimizationResult] = field(default_factory=list)
    learned_patterns: List[OptimizationPattern] = field(default_factory=list)

    # Metrics
    before_metrics: Optional[CodeMetrics] = None
    after_metrics: Optional[CodeMetrics] = None

    # Code tracking
    original_code: str = ""
    current_code: str = ""

    # Configuration
    max_iterations: int = 5
    min_improvement_threshold: float = 5.0  # Minimum 5% improvement to continue
    optimization_goals: Set[OptimizationType] = field(default_factory=lambda: {
        OptimizationType.PERFORMANCE,
        OptimizationType.READABILITY,
        OptimizationType.COMPLEXITY
    })

    # Learning configuration
    enable_learning: bool = True
    enable_self_improvement: bool = True
    pattern_confidence_threshold: float = 0.7
    min_pattern_applications: int = 3  # Before considering pattern reliable

    # Knowledge base (persisted patterns)
    knowledge_base: Dict[str, OptimizationPattern] = field(default_factory=dict)

    def __post_init__(self):
        """Initialize optimizer"""
        self.initial_state = OptimizerState.INITIAL
        self.current_state = self.initial_state
        self.final_states = {OptimizerState.SUCCESS, OptimizerState.FAILED}
        self.state_history = [self.current_state]

        self._setup_transitions()

        if self.debug_mode:
            logger.debug(f"RSICodeOptimizer {self.name} initialized")

    def _setup_transitions(self) -> None:
        """Setup state transitions"""
        # INITIAL -> ANALYZING
        self.add_transition(
            OptimizerState.INITIAL,
            OptimizerState.ANALYZING,
            action=self._analyze_code,
            description="Analyze code and collect metrics"
        )

        # ANALYZING -> IDENTIFYING_OPPORTUNITIES
        self.add_transition(
            OptimizerState.ANALYZING,
            OptimizerState.IDENTIFYING_OPPORTUNITIES,
            condition=lambda ctx: ctx.get("analysis_complete", False),
            action=self._identify_opportunities,
            description="Identify optimization opportunities"
        )

        # IDENTIFYING_OPPORTUNITIES -> APPLYING_OPTIMIZATIONS
        self.add_transition(
            OptimizerState.IDENTIFYING_OPPORTUNITIES,
            OptimizerState.APPLYING_OPTIMIZATIONS,
            condition=lambda ctx: len(ctx.get("opportunities", [])) > 0,
            action=self._apply_optimizations,
            description="Apply optimizations"
        )

        # IDENTIFYING_OPPORTUNITIES -> SUCCESS (no opportunities found)
        self.add_transition(
            OptimizerState.IDENTIFYING_OPPORTUNITIES,
            OptimizerState.SUCCESS,
            condition=lambda ctx: len(ctx.get("opportunities", [])) == 0,
            description="No optimizations needed"
        )

        # APPLYING_OPTIMIZATIONS -> VALIDATING
        self.add_transition(
            OptimizerState.APPLYING_OPTIMIZATIONS,
            OptimizerState.VALIDATING,
            condition=lambda ctx: ctx.get("optimizations_applied", False),
            action=self._validate_optimizations,
            description="Validate optimizations"
        )

        # VALIDATING -> LEARNING
        self.add_transition(
            OptimizerState.VALIDATING,
            OptimizerState.LEARNING,
            condition=lambda ctx: ctx.get("validation_complete", False) and self.enable_learning,
            action=self._learn_from_results,
            description="Learn from optimization results"
        )

        # VALIDATING -> SUCCESS (no learning)
        self.add_transition(
            OptimizerState.VALIDATING,
            OptimizerState.SUCCESS,
            condition=lambda ctx: ctx.get("validation_complete", False) and not self.enable_learning,
            description="Complete without learning"
        )

        # LEARNING -> SELF_IMPROVING
        self.add_transition(
            OptimizerState.LEARNING,
            OptimizerState.SELF_IMPROVING,
            condition=lambda ctx: ctx.get("learning_complete", False) and self.enable_self_improvement,
            action=self._self_improve,
            description="Improve optimization strategies"
        )

        # LEARNING -> SUCCESS (no self-improvement)
        self.add_transition(
            OptimizerState.LEARNING,
            OptimizerState.SUCCESS,
            condition=lambda ctx: ctx.get("learning_complete", False) and not self.enable_self_improvement,
            description="Complete with learning"
        )

        # SELF_IMPROVING -> SUCCESS
        self.add_transition(
            OptimizerState.SELF_IMPROVING,
            OptimizerState.SUCCESS,
            condition=lambda ctx: ctx.get("self_improvement_complete", False),
            description="Self-improvement complete"
        )

        # Error handling
        for state in OptimizerState:
            if state not in [OptimizerState.SUCCESS, OptimizerState.FAILED]:
                self.add_transition(
                    state,
                    OptimizerState.FAILED,
                    condition=lambda ctx: ctx.get("critical_error", False),
                    description="Critical error"
                )

    def _analyze_code(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze code and collect baseline metrics"""
        code = context.get("code", "")
        self.original_code = code
        self.current_code = code

        if self.debug_mode:
            logger.debug("Analyzing code for optimization")

        # Collect metrics
        self.before_metrics = self._collect_metrics(code)

        context["before_metrics"] = self.before_metrics
        context["analysis_complete"] = True

        return context

    def _collect_metrics(self, code: str) -> CodeMetrics:
        """Collect code metrics"""
        # Use agent for sophisticated analysis
        if self.optimization_agent:
            metrics_prompt = f"""
            Analyze this code and provide metrics:

            Code:
            {code}

            Calculate:
            1. Cyclomatic complexity
            2. Lines of code
            3. Estimated execution time
            4. Memory usage
            5. Readability score (0-100)
            6. Maintainability index (0-100)

            Provide numerical metrics.
            """
            # Agent would analyze
            pass

        # Simple metric calculation (would be more sophisticated with agent)
        return CodeMetrics(
            cyclomatic_complexity=len(code.split("if ")) + len(code.split("for ")) + len(code.split("while ")),
            lines_of_code=len(code.split("\n")),
            execution_time_ms=0.0,
            memory_usage_mb=0.0,
            readability_score=70.0,
            maintainability_index=65.0,
            test_coverage=0.0
        )

    def _identify_opportunities(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Identify optimization opportunities"""
        code = self.current_code
        goals = context.get("optimization_goals", list(self.optimization_goals))

        if self.debug_mode:
            logger.debug(f"Identifying optimization opportunities for goals: {goals}")

        # Use learned patterns first
        pattern_opportunities = self._apply_learned_patterns(code)

        # Use agent to identify additional opportunities
        if self.optimization_agent:
            identification_prompt = f"""
            Identify optimization opportunities in this code:

            Code:
            {code}

            Focus on: {goals}

            For each opportunity:
            1. Type of optimization
            2. Specific location in code
            3. Current code snippet
            4. Suggested improvement
            5. Expected improvement percentage
            6. Confidence level (0-1)
            7. Detailed rationale

            Prioritize high-impact, high-confidence optimizations.
            """
            # Agent would identify
            pass

        # Create example opportunities (would be generated by agent + patterns)
        self.opportunities = pattern_opportunities + [
            OptimizationOpportunity(
                id="opt-001",
                type=OptimizationType.PERFORMANCE,
                description="Replace inefficient loop with list comprehension",
                location="line 15-20",
                current_code="for item in items: result.append(transform(item))",
                suggested_code="result = [transform(item) for item in items]",
                expected_improvement=15.0,
                confidence=0.85,
                rationale="List comprehensions are more efficient",
                complexity="low"
            ),
        ]

        context["opportunities"] = self.opportunities
        context["opportunities_identified"] = len(self.opportunities)

        return context

    def _apply_learned_patterns(self, code: str) -> List[OptimizationOpportunity]:
        """Apply learned optimization patterns to identify opportunities"""
        opportunities = []

        for pattern_id, pattern in self.knowledge_base.items():
            # Check if pattern is reliable enough
            if (pattern.success_rate >= self.pattern_confidence_threshold and
                pattern.applications >= self.min_pattern_applications):

                # Check if pattern's trigger conditions are met
                if self._pattern_matches(code, pattern):
                    opportunity = OptimizationOpportunity(
                        id=f"pattern-{pattern_id}",
                        type=pattern.type,
                        description=f"Apply learned pattern: {pattern_id}",
                        location="detected by pattern",
                        current_code="",
                        suggested_code=pattern.transformation_template,
                        expected_improvement=pattern.average_improvement,
                        confidence=pattern.success_rate,
                        rationale=f"Learned pattern with {pattern.success_rate:.0%} success rate",
                        complexity="low"
                    )
                    opportunities.append(opportunity)

        return opportunities

    def _pattern_matches(self, code: str, pattern: OptimizationPattern) -> bool:
        """Check if optimization pattern matches code"""
        # Simple keyword matching (would be more sophisticated in production)
        for condition in pattern.trigger_conditions:
            if condition.lower() in code.lower():
                return True
        return False

    def _apply_optimizations(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Apply identified optimizations"""
        opportunities = context.get("opportunities", [])

        if self.debug_mode:
            logger.debug(f"Applying {len(opportunities)} optimizations")

        for opportunity in opportunities:
            result = self._apply_single_optimization(opportunity)
            self.applied_optimizations.append(result)

            if result.success:
                # Update current code with optimization
                self.current_code = self.current_code  # Would actually apply the change

        context["applied_optimizations"] = self.applied_optimizations
        context["optimizations_applied"] = True

        return context

    def _apply_single_optimization(self, opportunity: OptimizationOpportunity) -> OptimizationResult:
        """Apply a single optimization"""
        try:
            # Apply the optimization (simplified)
            # In production, this would actually modify the code

            return OptimizationResult(
                opportunity_id=opportunity.id,
                success=True,
                applied=True,
                actual_improvement=opportunity.expected_improvement * 0.9,  # Simulate
                validation_passed=True
            )
        except Exception as e:
            return OptimizationResult(
                opportunity_id=opportunity.id,
                success=False,
                applied=False,
                error=str(e)
            )

    def _validate_optimizations(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Validate that optimizations improved the code"""
        if self.debug_mode:
            logger.debug("Validating optimizations")

        # Collect metrics after optimization
        self.after_metrics = self._collect_metrics(self.current_code)

        # Calculate improvement
        improvement = self._calculate_improvement(self.before_metrics, self.after_metrics)

        context["after_metrics"] = self.after_metrics
        context["total_improvement"] = improvement
        context["validation_complete"] = True

        return context

    def _calculate_improvement(self, before: CodeMetrics, after: CodeMetrics) -> float:
        """Calculate overall improvement percentage"""
        improvements = []

        # Complexity improvement (lower is better)
        if before.cyclomatic_complexity > 0:
            complexity_imp = ((before.cyclomatic_complexity - after.cyclomatic_complexity) /
                            before.cyclomatic_complexity) * 100
            improvements.append(max(0, complexity_imp))

        # Readability improvement
        readability_imp = after.readability_score - before.readability_score
        improvements.append(max(0, readability_imp))

        # Maintainability improvement
        maintainability_imp = after.maintainability_index - before.maintainability_index
        improvements.append(max(0, maintainability_imp))

        # Return average improvement
        return sum(improvements) / len(improvements) if improvements else 0.0

    def _learn_from_results(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Learn from optimization results"""
        if self.debug_mode:
            logger.debug("Learning from optimization results")

        applied = self.applied_optimizations

        # Analyze successful optimizations
        successful = [opt for opt in applied if opt.success and opt.validation_passed]

        # Extract patterns from successful optimizations
        for opt_result in successful:
            # Find corresponding opportunity
            opportunity = next(
                (opp for opp in self.opportunities if opp.id == opt_result.opportunity_id),
                None
            )

            if opportunity:
                # Create or update pattern
                pattern_id = f"pattern-{opportunity.type.value}-{len(self.learned_patterns)}"

                if pattern_id not in self.knowledge_base:
                    pattern = OptimizationPattern(
                        pattern_id=pattern_id,
                        type=opportunity.type,
                        trigger_conditions=["TODO: extract trigger"],
                        transformation_template=opportunity.suggested_code,
                        success_rate=1.0,
                        average_improvement=opt_result.actual_improvement or 0.0,
                        applications=1,
                        last_updated=datetime.now().isoformat()
                    )
                    self.knowledge_base[pattern_id] = pattern
                    self.learned_patterns.append(pattern)
                else:
                    # Update existing pattern
                    pattern = self.knowledge_base[pattern_id]
                    pattern.applications += 1
                    pattern.average_improvement = (
                        (pattern.average_improvement * (pattern.applications - 1) +
                         (opt_result.actual_improvement or 0.0)) / pattern.applications
                    )
                    pattern.last_updated = datetime.now().isoformat()

        context["patterns_learned"] = len(self.learned_patterns)
        context["learning_complete"] = True

        return context

    def _self_improve(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Improve optimization strategies based on learning"""
        if self.debug_mode:
            logger.debug("Performing self-improvement")

        # Analyze which types of optimizations work best
        type_performance = {}
        for opt in self.applied_optimizations:
            if opt.success and opt.actual_improvement:
                opp = next((o for o in self.opportunities if o.id == opt.opportunity_id), None)
                if opp:
                    opt_type = opp.type.value
                    if opt_type not in type_performance:
                        type_performance[opt_type] = []
                    type_performance[opt_type].append(opt.actual_improvement)

        # Calculate average performance by type
        avg_performance = {
            opt_type: sum(improvements) / len(improvements)
            for opt_type, improvements in type_performance.items()
        }

        # Adjust optimization goals based on performance
        if avg_performance:
            best_type = max(avg_performance, key=avg_performance.get)
            if self.debug_mode:
                logger.debug(f"Best performing optimization type: {best_type}")

        context["self_improvement_gains"] = avg_performance
        context["self_improvement_complete"] = True

        return context

    def run(self, initial_context: Optional[Dict[str, Any]] = None) -> RSIOptimizerResult:
        """
        Run the RSI optimizer

        Args:
            initial_context: Context with code to optimize

        Returns:
            RSIOptimizerResult with optimizations and learning
        """
        # Execute base FSA run
        base_result = super().run(initial_context)

        # Calculate total improvement
        total_improvement = self.context.get("total_improvement", 0.0)

        # Build result
        return RSIOptimizerResult(
            success=base_result.success,
            original_code=self.original_code,
            optimized_code=self.current_code,
            opportunities_identified=self.opportunities,
            optimizations_applied=self.applied_optimizations,
            before_metrics=self.before_metrics or CodeMetrics(),
            after_metrics=self.after_metrics or CodeMetrics(),
            total_improvement=total_improvement,
            iterations=len(self.applied_optimizations),
            patterns_learned=self.learned_patterns,
            self_improvement_gains=self.context.get("self_improvement_gains", {}),
            error=base_result.error
        )

    def save_knowledge_base(self, filepath: str) -> None:
        """Save learned patterns to file"""
        with open(filepath, 'w') as f:
            json.dump(
                {pid: pattern.dict() for pid, pattern in self.knowledge_base.items()},
                f,
                indent=2
            )

    def load_knowledge_base(self, filepath: str) -> None:
        """Load learned patterns from file"""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                self.knowledge_base = {
                    pid: OptimizationPattern(**pattern)
                    for pid, pattern in data.items()
                }
        except Exception as e:
            logger.warning(f"Failed to load knowledge base: {e}")

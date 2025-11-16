"""
FSA Pattern Library

Reusable FSA patterns and templates:
- Common workflow patterns (sequential, parallel, retry)
- Design patterns (pipeline, chain of responsibility, state machine)
- Best practice templates
- Composable FSA components
- Pattern catalog with examples

Accelerates FSA development through reusable components.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from copy import deepcopy

from pydantic import BaseModel

from agno.agent import Agent
from agno.fsa.base import FSA, FSAState, FSATransition, FSAExecutionResult
from agno.utils.log import logger


class PatternCategory(str, Enum):
    """Categories of FSA patterns"""
    WORKFLOW = "workflow"
    CONTROL_FLOW = "control_flow"
    ERROR_HANDLING = "error_handling"
    OPTIMIZATION = "optimization"
    INTEGRATION = "integration"


class FSAPattern(BaseModel):
    """A reusable FSA pattern"""
    name: str
    category: PatternCategory
    description: str
    use_cases: List[str]
    states: List[str]
    transitions: List[Dict[str, str]]
    example_code: str
    best_practices: List[str]


class PatternLibraryState(str, Enum):
    """States for Pattern Library"""
    INITIAL = "initial"
    LOADING = "loading"
    BROWSING = "browsing"
    APPLYING = "applying"
    VALIDATING = "validating"
    SUCCESS = "success"
    FAILED = "failed"


@dataclass
class FSAPatternLibrary(FSA):
    """
    FSA Pattern Library

    Provides reusable FSA patterns and templates:
    - Pre-built workflow patterns
    - Common control flow structures
    - Error handling patterns
    - Optimization patterns
    - Integration patterns

    Example:
        ```python
        # Access pattern library
        library = FSAPatternLibrary(name="PatternLib")

        # Get a pattern
        retry_pattern = library.get_pattern("retry_with_backoff")

        # Apply pattern to create FSA
        my_fsa = library.apply_pattern(retry_pattern, {
            "max_retries": 3,
            "backoff_multiplier": 2.0
        })
        ```
    """

    # Pattern catalog
    patterns: Dict[str, FSAPattern] = field(default_factory=dict)

    # Configuration
    include_builtin_patterns: bool = True

    def __post_init__(self):
        """Initialize pattern library"""
        self.initial_state = PatternLibraryState.INITIAL
        self.current_state = self.initial_state
        self.final_states = {PatternLibraryState.SUCCESS, PatternLibraryState.FAILED}
        self.state_history = [self.current_state]

        if self.include_builtin_patterns:
            self._load_builtin_patterns()

        self._setup_transitions()

        if self.debug_mode:
            logger.debug(f"FSAPatternLibrary {self.name} initialized with {len(self.patterns)} patterns")

    def _setup_transitions(self) -> None:
        """Setup pattern library workflow"""
        # INITIAL -> LOADING
        self.add_transition(
            PatternLibraryState.INITIAL,
            PatternLibraryState.LOADING,
            action=self._load_patterns,
            description="Load pattern catalog"
        )

        # LOADING -> BROWSING
        self.add_transition(
            PatternLibraryState.LOADING,
            PatternLibraryState.BROWSING,
            condition=lambda ctx: ctx.get("loading_complete", False),
            action=self._browse_patterns,
            description="Browse available patterns"
        )

        # BROWSING -> APPLYING
        self.add_transition(
            PatternLibraryState.BROWSING,
            PatternLibraryState.APPLYING,
            condition=lambda ctx: ctx.get("pattern_selected", False),
            action=self._apply_pattern,
            description="Apply selected pattern"
        )

        # APPLYING -> VALIDATING
        self.add_transition(
            PatternLibraryState.APPLYING,
            PatternLibraryState.VALIDATING,
            condition=lambda ctx: ctx.get("pattern_applied", False),
            action=self._validate_pattern,
            description="Validate applied pattern"
        )

        # VALIDATING -> SUCCESS
        self.add_transition(
            PatternLibraryState.VALIDATING,
            PatternLibraryState.SUCCESS,
            condition=lambda ctx: ctx.get("validation_passed", False),
            description="Pattern ready"
        )

        # Error handling
        for state in PatternLibraryState:
            if state not in [PatternLibraryState.SUCCESS, PatternLibraryState.FAILED]:
                self.add_transition(
                    state,
                    PatternLibraryState.FAILED,
                    condition=lambda ctx: ctx.get("critical_error", False),
                    description="Critical error"
                )

    def _load_builtin_patterns(self) -> None:
        """Load built-in FSA patterns"""

        # Pattern 1: Sequential Workflow
        self.patterns["sequential_workflow"] = FSAPattern(
            name="Sequential Workflow",
            category=PatternCategory.WORKFLOW,
            description="Execute tasks in strict sequential order",
            use_cases=[
                "Multi-step processes",
                "Pipeline operations",
                "Data transformation chains"
            ],
            states=["initial", "step_1", "step_2", "step_3", "success"],
            transitions=[
                {"from": "initial", "to": "step_1"},
                {"from": "step_1", "to": "step_2"},
                {"from": "step_2", "to": "step_3"},
                {"from": "step_3", "to": "success"}
            ],
            example_code='''
fsa = FSA(name="Sequential", initial_state="initial")
fsa.add_transition("initial", "step_1", action=step1_action)
fsa.add_transition("step_1", "step_2", action=step2_action)
fsa.add_transition("step_2", "step_3", action=step3_action)
fsa.add_transition("step_3", "success")
''',
            best_practices=[
                "Keep each step focused and single-purpose",
                "Add validation between steps",
                "Include error handling for each step"
            ]
        )

        # Pattern 2: Retry with Exponential Backoff
        self.patterns["retry_with_backoff"] = FSAPattern(
            name="Retry with Exponential Backoff",
            category=PatternCategory.ERROR_HANDLING,
            description="Retry failed operations with increasing delays",
            use_cases=[
                "API calls with rate limiting",
                "Network operations",
                "External service integration"
            ],
            states=["initial", "attempting", "success", "retrying", "failed"],
            transitions=[
                {"from": "initial", "to": "attempting"},
                {"from": "attempting", "to": "success"},
                {"from": "attempting", "to": "retrying"},
                {"from": "retrying", "to": "attempting"},
                {"from": "retrying", "to": "failed"}
            ],
            example_code='''
fsa = FSA(name="Retry")
fsa.add_transition("initial", "attempting", action=attempt_operation)
fsa.add_transition("attempting", "success", condition=lambda ctx: ctx["success"])
fsa.add_transition("attempting", "retrying", condition=lambda ctx: not ctx["success"] and ctx["retries"] < 3)
fsa.add_transition("retrying", "attempting", action=lambda ctx: {**ctx, "retries": ctx["retries"] + 1, "delay": ctx["delay"] * 2})
fsa.add_transition("retrying", "failed", condition=lambda ctx: ctx["retries"] >= 3)
''',
            best_practices=[
                "Set maximum retry limit",
                "Use exponential backoff to avoid overwhelming services",
                "Log retry attempts for debugging"
            ]
        )

        # Pattern 3: Parallel Execution
        self.patterns["parallel_execution"] = FSAPattern(
            name="Parallel Execution",
            category=PatternCategory.WORKFLOW,
            description="Execute multiple independent tasks in parallel",
            use_cases=[
                "Independent API calls",
                "Batch processing",
                "Data aggregation from multiple sources"
            ],
            states=["initial", "executing", "aggregating", "success"],
            transitions=[
                {"from": "initial", "to": "executing"},
                {"from": "executing", "to": "aggregating"},
                {"from": "aggregating", "to": "success"}
            ],
            example_code='''
# Use Meta-FSA Orchestrator for parallel execution
orchestrator = MetaFSAOrchestrator(parallel_execution=True)
orchestrator.register_fsa(task1_fsa)  # No dependencies
orchestrator.register_fsa(task2_fsa)  # No dependencies
orchestrator.register_fsa(aggregator_fsa, depends_on=[task1_fsa.fsa_id, task2_fsa.fsa_id])
''',
            best_practices=[
                "Ensure tasks are truly independent",
                "Handle partial failures gracefully",
                "Aggregate results carefully"
            ]
        )

        # Pattern 4: Validation Pipeline
        self.patterns["validation_pipeline"] = FSAPattern(
            name="Validation Pipeline",
            category=PatternCategory.WORKFLOW,
            description="Multi-stage validation with progressive checks",
            use_cases=[
                "Data validation",
                "Input sanitization",
                "Quality assurance"
            ],
            states=["initial", "syntax_check", "semantic_check", "business_rules", "success", "failed"],
            transitions=[
                {"from": "initial", "to": "syntax_check"},
                {"from": "syntax_check", "to": "semantic_check"},
                {"from": "semantic_check", "to": "business_rules"},
                {"from": "business_rules", "to": "success"},
                {"from": "syntax_check", "to": "failed"},
                {"from": "semantic_check", "to": "failed"},
                {"from": "business_rules", "to": "failed"}
            ],
            example_code='''
validator = FSA(name="Validator")
validator.add_transition("initial", "syntax_check", action=check_syntax)
validator.add_transition("syntax_check", "semantic_check", condition=lambda ctx: ctx["syntax_valid"], action=check_semantics)
validator.add_transition("syntax_check", "failed", condition=lambda ctx: not ctx["syntax_valid"])
validator.add_transition("semantic_check", "business_rules", condition=lambda ctx: ctx["semantics_valid"], action=check_business_rules)
validator.add_transition("business_rules", "success", condition=lambda ctx: ctx["rules_satisfied"])
''',
            best_practices=[
                "Fail fast - check syntax before semantics",
                "Provide detailed error messages",
                "Make validations reusable"
            ]
        )

        # Pattern 5: State Machine with Rollback
        self.patterns["rollback_pattern"] = FSAPattern(
            name="State Machine with Rollback",
            category=PatternCategory.ERROR_HANDLING,
            description="Support rollback/undo operations",
            use_cases=[
                "Transaction processing",
                "Multi-step operations with failure recovery",
                "Database migrations"
            ],
            states=["initial", "step_1", "step_2", "committed", "rolling_back", "rolled_back", "failed"],
            transitions=[
                {"from": "initial", "to": "step_1"},
                {"from": "step_1", "to": "step_2"},
                {"from": "step_2", "to": "committed"},
                {"from": "step_1", "to": "rolling_back"},
                {"from": "step_2", "to": "rolling_back"},
                {"from": "rolling_back", "to": "rolled_back"}
            ],
            example_code='''
fsa = FSA(name="Transaction")
# Forward transitions
fsa.add_transition("initial", "step_1", action=lambda ctx: {**ctx, "undo_stack": [undo_initial]})
fsa.add_transition("step_1", "step_2", action=lambda ctx: {**ctx, "undo_stack": ctx["undo_stack"] + [undo_step1]})
fsa.add_transition("step_2", "committed")
# Rollback transitions
fsa.add_transition("step_1", "rolling_back", condition=lambda ctx: ctx.get("error"))
fsa.add_transition("rolling_back", "rolled_back", action=lambda ctx: execute_undo_stack(ctx["undo_stack"]))
''',
            best_practices=[
                "Track all operations for rollback",
                "Test rollback procedures regularly",
                "Ensure rollback is idempotent"
            ]
        )

    def _load_patterns(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Load pattern catalog"""
        if self.debug_mode:
            logger.debug(f"Loading {len(self.patterns)} patterns")

        context["patterns_loaded"] = len(self.patterns)
        context["loading_complete"] = True

        return context

    def _browse_patterns(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Browse available patterns"""
        pattern_name = context.get("pattern_name")

        if pattern_name:
            context["pattern_selected"] = True
            context["selected_pattern"] = self.patterns.get(pattern_name)
        else:
            context["pattern_selected"] = False
            context["available_patterns"] = list(self.patterns.keys())

        return context

    def _apply_pattern(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Apply selected pattern"""
        pattern = context.get("selected_pattern")

        if not pattern:
            context["critical_error"] = True
            raise ValueError("No pattern selected")

        # Pattern would be applied here
        # For now, just mark as applied

        context["pattern_applied"] = True
        context["applied_pattern_name"] = pattern.name

        return context

    def _validate_pattern(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Validate applied pattern"""
        # Validation logic here
        context["validation_passed"] = True

        return context

    def get_pattern(self, name: str) -> Optional[FSAPattern]:
        """Get pattern by name"""
        return self.patterns.get(name)

    def list_patterns(self, category: Optional[PatternCategory] = None) -> List[FSAPattern]:
        """List all patterns, optionally filtered by category"""
        if category:
            return [p for p in self.patterns.values() if p.category == category]
        return list(self.patterns.values())

    def add_pattern(self, pattern: FSAPattern) -> None:
        """Add a custom pattern to the library"""
        self.patterns[pattern.name.lower().replace(" ", "_")] = pattern
        if self.debug_mode:
            logger.debug(f"Added pattern: {pattern.name}")

    def get_pattern_catalog(self) -> str:
        """Generate pattern catalog documentation"""
        catalog = "FSA Pattern Catalog\n"
        catalog += "=" * 50 + "\n\n"

        by_category = {}
        for pattern in self.patterns.values():
            if pattern.category not in by_category:
                by_category[pattern.category] = []
            by_category[pattern.category].append(pattern)

        for category, patterns in sorted(by_category.items()):
            catalog += f"## {category.value.upper()}\n\n"
            for pattern in patterns:
                catalog += f"### {pattern.name}\n"
                catalog += f"{pattern.description}\n\n"
                catalog += f"**Use Cases:**\n"
                for use_case in pattern.use_cases:
                    catalog += f"- {use_case}\n"
                catalog += f"\n**States:** {', '.join(pattern.states)}\n\n"
                catalog += f"**Example:**\n```python{pattern.example_code}```\n\n"
                catalog += f"**Best Practices:**\n"
                for practice in pattern.best_practices:
                    catalog += f"- {practice}\n"
                catalog += "\n---\n\n"

        return catalog


# Convenience functions for quick pattern access

def get_sequential_workflow_pattern() -> FSAPattern:
    """Get sequential workflow pattern"""
    library = FSAPatternLibrary()
    return library.get_pattern("sequential_workflow")


def get_retry_pattern() -> FSAPattern:
    """Get retry with backoff pattern"""
    library = FSAPatternLibrary()
    return library.get_pattern("retry_with_backoff")


def get_parallel_execution_pattern() -> FSAPattern:
    """Get parallel execution pattern"""
    library = FSAPatternLibrary()
    return library.get_pattern("parallel_execution")


def get_validation_pipeline_pattern() -> FSAPattern:
    """Get validation pipeline pattern"""
    library = FSAPatternLibrary()
    return library.get_pattern("validation_pipeline")


def get_rollback_pattern() -> FSAPattern:
    """Get rollback pattern"""
    library = FSAPatternLibrary()
    return library.get_pattern("rollback_pattern")

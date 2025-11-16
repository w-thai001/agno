"""
FSA Validator

Validates FSA definitions for correctness, completeness, and best practices:
- State machine correctness (reachability, deadlocks, completeness)
- Transition validation (conditions, actions, cycles)
- Structural analysis (entry/exit points, orphaned states)
- Best practices compliance
- Security and safety checks
- Performance analysis

Ensures FSAs are well-formed before execution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from pydantic import BaseModel

from agno.agent import Agent
from agno.fsa.base import FSA, FSAState, FSATransition, FSAExecutionResult
from agno.utils.log import logger


class ValidatorState(str, Enum):
    """States for FSA Validator"""
    INITIAL = "initial"
    PARSING = "parsing"
    STRUCTURAL_ANALYSIS = "structural_analysis"
    REACHABILITY_CHECK = "reachability_check"
    DEADLOCK_DETECTION = "deadlock_detection"
    COMPLETENESS_CHECK = "completeness_check"
    BEST_PRACTICES = "best_practices"
    SECURITY_ANALYSIS = "security_analysis"
    AGGREGATING = "aggregating"
    SUCCESS = "success"
    FAILED = "failed"


class ValidationIssueSeverity(str, Enum):
    """Severity levels for validation issues"""
    CRITICAL = "critical"  # FSA will fail
    ERROR = "error"  # FSA will likely fail
    WARNING = "warning"  # FSA may have issues
    INFO = "info"  # Suggestions for improvement


class ValidationIssueCategory(str, Enum):
    """Categories of validation issues"""
    STRUCTURAL = "structural"
    REACHABILITY = "reachability"
    COMPLETENESS = "completeness"
    TRANSITIONS = "transitions"
    STATES = "states"
    BEST_PRACTICES = "best_practices"
    SECURITY = "security"
    PERFORMANCE = "performance"


class ValidationIssue(BaseModel):
    """Represents a validation issue"""
    id: str
    severity: ValidationIssueSeverity
    category: ValidationIssueCategory
    description: str
    state: Optional[str] = None
    transition: Optional[str] = None
    recommendation: str
    auto_fixable: bool = False
    fix_description: Optional[str] = None


class FSAMetrics(BaseModel):
    """Metrics about the FSA structure"""
    total_states: int
    total_transitions: int
    reachable_states: int
    unreachable_states: int
    terminal_states: int
    average_branching_factor: float
    max_depth: int
    has_cycles: bool
    complexity_score: float  # 0-100


class FSAValidationResult(BaseModel):
    """Result of FSA validation"""
    fsa_name: str
    valid: bool
    issues: List[ValidationIssue]
    metrics: FSAMetrics
    critical_issues: int
    errors: int
    warnings: int
    info: int
    recommendations: List[str]
    passed_checks: List[str]
    failed_checks: List[str]
    error: Optional[str] = None


@dataclass
class FSAValidator(FSA):
    """
    FSA Validator

    Validates FSA definitions for:
    - Structural correctness (well-formed state machine)
    - Reachability (all states reachable from initial)
    - Completeness (no orphaned states or transitions)
    - Deadlock detection
    - Best practices compliance
    - Security considerations
    - Performance characteristics

    Example:
        ```python
        # Create FSA to validate
        my_fsa = MultiStepCodeBuilder(...)

        # Create validator
        validator = FSAValidator(name="FSAChecker")

        # Validate
        result = validator.run({"fsa": my_fsa})

        if result.valid:
            print("FSA is valid!")
        else:
            for issue in result.issues:
                print(f"{issue.severity}: {issue.description}")
        ```
    """

    # Target FSA to validate
    target_fsa: Optional[FSA] = None

    # Results
    issues: List[ValidationIssue] = field(default_factory=list)
    metrics: Optional[FSAMetrics] = None

    # Validation configuration
    require_all_states_reachable: bool = True
    require_no_deadlocks: bool = True
    require_final_states: bool = True
    max_recommended_states: int = 50
    max_recommended_transitions: int = 100
    max_recommended_depth: int = 20

    # Best practices
    recommend_state_hooks: bool = True
    recommend_error_handling: bool = True
    recommend_debug_mode: bool = False

    def __post_init__(self):
        """Initialize validator"""
        self.initial_state = ValidatorState.INITIAL
        self.current_state = self.initial_state
        self.final_states = {ValidatorState.SUCCESS, ValidatorState.FAILED}
        self.state_history = [self.current_state]

        self._setup_transitions()

        if self.debug_mode:
            logger.debug(f"FSAValidator {self.name} initialized")

    def _setup_transitions(self) -> None:
        """Setup validation workflow"""
        # INITIAL -> PARSING
        self.add_transition(
            ValidatorState.INITIAL,
            ValidatorState.PARSING,
            action=self._parse_fsa,
            description="Parse FSA structure"
        )

        # PARSING -> STRUCTURAL_ANALYSIS
        self.add_transition(
            ValidatorState.PARSING,
            ValidatorState.STRUCTURAL_ANALYSIS,
            condition=lambda ctx: ctx.get("parsing_complete", False),
            action=self._analyze_structure,
            description="Analyze FSA structure"
        )

        # STRUCTURAL_ANALYSIS -> REACHABILITY_CHECK
        self.add_transition(
            ValidatorState.STRUCTURAL_ANALYSIS,
            ValidatorState.REACHABILITY_CHECK,
            condition=lambda ctx: ctx.get("structural_analysis_complete", False),
            action=self._check_reachability,
            description="Check state reachability"
        )

        # REACHABILITY_CHECK -> DEADLOCK_DETECTION
        self.add_transition(
            ValidatorState.REACHABILITY_CHECK,
            ValidatorState.DEADLOCK_DETECTION,
            condition=lambda ctx: ctx.get("reachability_check_complete", False),
            action=self._detect_deadlocks,
            description="Detect deadlocks"
        )

        # DEADLOCK_DETECTION -> COMPLETENESS_CHECK
        self.add_transition(
            ValidatorState.DEADLOCK_DETECTION,
            ValidatorState.COMPLETENESS_CHECK,
            condition=lambda ctx: ctx.get("deadlock_detection_complete", False),
            action=self._check_completeness,
            description="Check completeness"
        )

        # COMPLETENESS_CHECK -> BEST_PRACTICES
        self.add_transition(
            ValidatorState.COMPLETENESS_CHECK,
            ValidatorState.BEST_PRACTICES,
            condition=lambda ctx: ctx.get("completeness_check_complete", False),
            action=self._check_best_practices,
            description="Check best practices"
        )

        # BEST_PRACTICES -> SECURITY_ANALYSIS
        self.add_transition(
            ValidatorState.BEST_PRACTICES,
            ValidatorState.SECURITY_ANALYSIS,
            condition=lambda ctx: ctx.get("best_practices_complete", False),
            action=self._analyze_security,
            description="Analyze security"
        )

        # SECURITY_ANALYSIS -> AGGREGATING
        self.add_transition(
            ValidatorState.SECURITY_ANALYSIS,
            ValidatorState.AGGREGATING,
            condition=lambda ctx: ctx.get("security_analysis_complete", False),
            action=self._aggregate_results,
            description="Aggregate results"
        )

        # AGGREGATING -> SUCCESS
        self.add_transition(
            ValidatorState.AGGREGATING,
            ValidatorState.SUCCESS,
            condition=lambda ctx: ctx.get("aggregation_complete", False),
            description="Validation complete"
        )

        # Error handling
        for state in ValidatorState:
            if state not in [ValidatorState.SUCCESS, ValidatorState.FAILED]:
                self.add_transition(
                    state,
                    ValidatorState.FAILED,
                    condition=lambda ctx: ctx.get("critical_error", False),
                    description="Critical error"
                )

    def _parse_fsa(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Parse the FSA structure"""
        fsa = context.get("fsa") or self.target_fsa

        if not fsa:
            context["critical_error"] = True
            raise ValueError("No FSA provided for validation")

        self.target_fsa = fsa

        if self.debug_mode:
            logger.debug(f"Parsing FSA: {fsa.name}")

        # Extract basic structure
        context["states"] = set()
        context["transitions"] = []

        # Parse states from transitions
        for from_state, trans_list in fsa.transitions.items():
            context["states"].add(from_state)
            for trans in trans_list:
                context["states"].add(trans.to_state)
                context["transitions"].append({
                    "from": from_state,
                    "to": trans.to_state,
                    "has_condition": trans.condition is not None,
                    "has_action": trans.action is not None
                })

        # Add final states
        context["states"].update(fsa.final_states)

        context["initial_state"] = fsa.initial_state
        context["final_states"] = fsa.final_states
        context["parsing_complete"] = True

        return context

    def _analyze_structure(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze FSA structural properties"""
        states = context.get("states", set())
        transitions = context.get("transitions", [])
        initial_state = context.get("initial_state")
        final_states = context.get("final_states", set())

        if self.debug_mode:
            logger.debug("Analyzing FSA structure")

        # Check for basic structural issues
        if not states:
            self.issues.append(ValidationIssue(
                id="struct-001",
                severity=ValidationIssueSeverity.CRITICAL,
                category=ValidationIssueCategory.STRUCTURAL,
                description="FSA has no states defined",
                recommendation="Add states and transitions to FSA"
            ))

        if not transitions:
            self.issues.append(ValidationIssue(
                id="struct-002",
                severity=ValidationIssueSeverity.CRITICAL,
                category=ValidationIssueCategory.STRUCTURAL,
                description="FSA has no transitions defined",
                recommendation="Add transitions between states"
            ))

        if initial_state not in states:
            self.issues.append(ValidationIssue(
                id="struct-003",
                severity=ValidationIssueSeverity.CRITICAL,
                category=ValidationIssueCategory.STRUCTURAL,
                description=f"Initial state {initial_state} not in state set",
                recommendation="Ensure initial state is properly defined"
            ))

        if not final_states:
            self.issues.append(ValidationIssue(
                id="struct-004",
                severity=ValidationIssueSeverity.WARNING,
                category=ValidationIssueCategory.STRUCTURAL,
                description="No final states defined",
                recommendation="Define at least one final state"
            ))

        # Check state count
        if len(states) > self.max_recommended_states:
            self.issues.append(ValidationIssue(
                id="struct-005",
                severity=ValidationIssueSeverity.INFO,
                category=ValidationIssueCategory.PERFORMANCE,
                description=f"FSA has {len(states)} states (recommended max: {self.max_recommended_states})",
                recommendation="Consider breaking into smaller FSAs"
            ))

        context["structural_analysis_complete"] = True

        return context

    def _check_reachability(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Check if all states are reachable from initial state"""
        states = context.get("states", set())
        transitions = context.get("transitions", [])
        initial_state = context.get("initial_state")

        if self.debug_mode:
            logger.debug("Checking state reachability")

        # Build reachability graph
        reachable = {initial_state}
        to_visit = [initial_state]

        while to_visit:
            current = to_visit.pop(0)
            for trans in transitions:
                if trans["from"] == current and trans["to"] not in reachable:
                    reachable.add(trans["to"])
                    to_visit.append(trans["to"])

        unreachable = states - reachable

        if unreachable:
            for state in unreachable:
                self.issues.append(ValidationIssue(
                    id=f"reach-{state}",
                    severity=ValidationIssueSeverity.ERROR,
                    category=ValidationIssueCategory.REACHABILITY,
                    description=f"State {state} is unreachable from initial state",
                    state=str(state),
                    recommendation="Add transition path from initial state or remove unused state"
                ))

        context["reachable_states"] = len(reachable)
        context["unreachable_states"] = len(unreachable)
        context["reachability_check_complete"] = True

        return context

    def _detect_deadlocks(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Detect potential deadlocks"""
        states = context.get("states", set())
        transitions = context.get("transitions", [])
        final_states = context.get("final_states", set())

        if self.debug_mode:
            logger.debug("Detecting deadlocks")

        # Find states with no outgoing transitions (excluding final states)
        states_with_outgoing = set(trans["from"] for trans in transitions)
        states_without_outgoing = states - states_with_outgoing - final_states

        if states_without_outgoing:
            for state in states_without_outgoing:
                self.issues.append(ValidationIssue(
                    id=f"deadlock-{state}",
                    severity=ValidationIssueSeverity.ERROR,
                    category=ValidationIssueCategory.COMPLETENESS,
                    description=f"State {state} has no outgoing transitions (potential deadlock)",
                    state=str(state),
                    recommendation="Add transition to final state or another state"
                ))

        context["deadlock_detection_complete"] = True

        return context

    def _check_completeness(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Check FSA completeness"""
        transitions = context.get("transitions", [])
        final_states = context.get("final_states", set())

        if self.debug_mode:
            logger.debug("Checking completeness")

        # Check if there's a path to final states
        can_reach_final = False
        for trans in transitions:
            if trans["to"] in final_states:
                can_reach_final = True
                break

        if not can_reach_final and final_states:
            self.issues.append(ValidationIssue(
                id="complete-001",
                severity=ValidationIssueSeverity.ERROR,
                category=ValidationIssueCategory.COMPLETENESS,
                description="No transition paths lead to final states",
                recommendation="Add transitions to reach final states"
            ))

        # Check for unconditional transitions (could indicate missing logic)
        unconditional_count = sum(1 for t in transitions if not t["has_condition"])
        if unconditional_count == 0 and len(transitions) > 0:
            self.issues.append(ValidationIssue(
                id="complete-002",
                severity=ValidationIssueSeverity.INFO,
                category=ValidationIssueCategory.BEST_PRACTICES,
                description="All transitions have conditions (may be overly restrictive)",
                recommendation="Consider adding some unconditional transitions for default paths"
            ))

        context["completeness_check_complete"] = True

        return context

    def _check_best_practices(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Check best practices compliance"""
        if self.debug_mode:
            logger.debug("Checking best practices")

        fsa = self.target_fsa

        # Check if error handling states exist
        states = context.get("states", set())
        has_error_state = any("error" in str(s).lower() or "fail" in str(s).lower() for s in states)

        if not has_error_state and self.recommend_error_handling:
            self.issues.append(ValidationIssue(
                id="bp-001",
                severity=ValidationIssueSeverity.INFO,
                category=ValidationIssueCategory.BEST_PRACTICES,
                description="No explicit error/failure state found",
                recommendation="Consider adding error handling states"
            ))

        # Check transition count per state
        transitions_per_state = {}
        for trans in context.get("transitions", []):
            from_state = trans["from"]
            transitions_per_state[from_state] = transitions_per_state.get(from_state, 0) + 1

        for state, count in transitions_per_state.items():
            if count > 10:
                self.issues.append(ValidationIssue(
                    id=f"bp-{state}",
                    severity=ValidationIssueSeverity.WARNING,
                    category=ValidationIssueCategory.BEST_PRACTICES,
                    description=f"State {state} has {count} outgoing transitions",
                    state=str(state),
                    recommendation="Consider simplifying state with fewer transitions"
                ))

        context["best_practices_complete"] = True

        return context

    def _analyze_security(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze security considerations"""
        if self.debug_mode:
            logger.debug("Analyzing security")

        transitions = context.get("transitions", [])

        # Check for transitions without conditions (could be security risk)
        unconditional_transitions = [t for t in transitions if not t["has_condition"]]

        if len(unconditional_transitions) > len(transitions) * 0.5:
            self.issues.append(ValidationIssue(
                id="sec-001",
                severity=ValidationIssueSeverity.INFO,
                category=ValidationIssueCategory.SECURITY,
                description="Many transitions lack conditions (potential security concern)",
                recommendation="Add validation conditions to control state flow"
            ))

        context["security_analysis_complete"] = True

        return context

    def _aggregate_results(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Aggregate validation results"""
        if self.debug_mode:
            logger.debug("Aggregating results")

        states = context.get("states", set())
        transitions = context.get("transitions", [])

        # Calculate metrics
        terminal_states = 0
        for state in states:
            has_outgoing = any(t["from"] == state for t in transitions)
            if not has_outgoing:
                terminal_states += 1

        # Calculate average branching factor
        if states:
            avg_branching = len(transitions) / len(states)
        else:
            avg_branching = 0.0

        # Detect cycles
        has_cycles = self._has_cycles(states, transitions)

        # Calculate complexity score
        complexity_score = min(100, len(states) * 2 + len(transitions))

        self.metrics = FSAMetrics(
            total_states=len(states),
            total_transitions=len(transitions),
            reachable_states=context.get("reachable_states", 0),
            unreachable_states=context.get("unreachable_states", 0),
            terminal_states=terminal_states,
            average_branching_factor=avg_branching,
            max_depth=self._calculate_max_depth(context.get("initial_state"), transitions),
            has_cycles=has_cycles,
            complexity_score=complexity_score
        )

        # Count issues by severity
        critical = len([i for i in self.issues if i.severity == ValidationIssueSeverity.CRITICAL])
        errors = len([i for i in self.issues if i.severity == ValidationIssueSeverity.ERROR])
        warnings = len([i for i in self.issues if i.severity == ValidationIssueSeverity.WARNING])
        info = len([i for i in self.issues if i.severity == ValidationIssueSeverity.INFO])

        # Determine if valid
        valid = critical == 0 and errors == 0

        context["valid"] = valid
        context["critical_issues"] = critical
        context["errors"] = errors
        context["warnings"] = warnings
        context["info"] = info
        context["aggregation_complete"] = True

        # Generate recommendations
        recommendations = self._generate_recommendations()
        context["recommendations"] = recommendations

        # Track passed/failed checks
        passed_checks = []
        failed_checks = []

        if context.get("unreachable_states", 0) == 0:
            passed_checks.append("All states reachable")
        else:
            failed_checks.append("Unreachable states found")

        if critical == 0:
            passed_checks.append("No critical issues")
        else:
            failed_checks.append("Critical issues found")

        context["passed_checks"] = passed_checks
        context["failed_checks"] = failed_checks

        return context

    def _has_cycles(self, states: Set, transitions: List[Dict]) -> bool:
        """Detect if FSA has cycles"""
        visited = set()
        rec_stack = set()

        def has_cycle_util(state):
            visited.add(state)
            rec_stack.add(state)

            for trans in transitions:
                if trans["from"] == state:
                    next_state = trans["to"]
                    if next_state not in visited:
                        if has_cycle_util(next_state):
                            return True
                    elif next_state in rec_stack:
                        return True

            rec_stack.remove(state)
            return False

        for state in states:
            if state not in visited:
                if has_cycle_util(state):
                    return True

        return False

    def _calculate_max_depth(self, initial_state, transitions: List[Dict]) -> int:
        """Calculate maximum depth of FSA"""
        depths = {initial_state: 0}
        changed = True

        while changed:
            changed = False
            for trans in transitions:
                if trans["from"] in depths:
                    new_depth = depths[trans["from"]] + 1
                    if trans["to"] not in depths or depths[trans["to"]] > new_depth:
                        depths[trans["to"]] = new_depth
                        changed = True

        return max(depths.values()) if depths else 0

    def _generate_recommendations(self) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []

        if self.metrics:
            if self.metrics.unreachable_states > 0:
                recommendations.append(f"Remove {self.metrics.unreachable_states} unreachable states")

            if self.metrics.complexity_score > 80:
                recommendations.append("Consider splitting FSA into smaller components")

            if self.metrics.max_depth > self.max_recommended_depth:
                recommendations.append(f"FSA depth ({self.metrics.max_depth}) exceeds recommended maximum")

        return recommendations

    def run(self, initial_context: Optional[Dict[str, Any]] = None) -> FSAValidationResult:
        """
        Validate an FSA

        Args:
            initial_context: Context with FSA to validate

        Returns:
            FSAValidationResult with validation details
        """
        # Execute base FSA run
        base_result = super().run(initial_context)

        # Build validation result
        return FSAValidationResult(
            fsa_name=self.target_fsa.name if self.target_fsa else "Unknown",
            valid=self.context.get("valid", False),
            issues=self.issues,
            metrics=self.metrics or FSAMetrics(
                total_states=0,
                total_transitions=0,
                reachable_states=0,
                unreachable_states=0,
                terminal_states=0,
                average_branching_factor=0.0,
                max_depth=0,
                has_cycles=False,
                complexity_score=0.0
            ),
            critical_issues=self.context.get("critical_issues", 0),
            errors=self.context.get("errors", 0),
            warnings=self.context.get("warnings", 0),
            info=self.context.get("info", 0),
            recommendations=self.context.get("recommendations", []),
            passed_checks=self.context.get("passed_checks", []),
            failed_checks=self.context.get("failed_checks", []),
            error=base_result.error
        )

    def get_validation_report(self) -> str:
        """Generate human-readable validation report"""
        report = f"FSA Validation Report\n"
        report += "=" * 50 + "\n\n"

        if self.target_fsa:
            report += f"FSA Name: {self.target_fsa.name}\n"

        if self.metrics:
            report += f"\nMetrics:\n"
            report += f"  States: {self.metrics.total_states} "
            report += f"({self.metrics.reachable_states} reachable, "
            report += f"{self.metrics.unreachable_states} unreachable)\n"
            report += f"  Transitions: {self.metrics.total_transitions}\n"
            report += f"  Max Depth: {self.metrics.max_depth}\n"
            report += f"  Complexity: {self.metrics.complexity_score}/100\n"
            report += f"  Has Cycles: {'Yes' if self.metrics.has_cycles else 'No'}\n"

        if self.issues:
            report += f"\nIssues Found: {len(self.issues)}\n"
            for issue in self.issues[:10]:  # Show first 10
                severity_icon = {
                    "critical": "🔴",
                    "error": "🟠",
                    "warning": "🟡",
                    "info": "🔵"
                }
                icon = severity_icon.get(issue.severity.value, "⚪")
                report += f"  {icon} [{issue.severity.value.upper()}] {issue.description}\n"

        return report

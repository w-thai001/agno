"""
FSA Structure Validator - Validates FSA structure for correctness and best practices.

Performs comprehensive validation including:
- State reachability analysis
- Dead code detection
- Transition validation
- Entry/exit state verification
- Error handling coverage
- Agent compatibility checks
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Set

from agno.workflows.fsa_meta_analyzer.static_analyzer import FSAStructure, FSAState, FSATransition


class ValidationSeverity(str, Enum):
    """Severity levels for validation issues."""

    CRITICAL = 'critical'
    ERROR = 'error'
    WARNING = 'warning'
    INFO = 'info'


@dataclass
class ValidationIssue:
    """Represents a validation issue found in the FSA."""

    severity: ValidationSeverity
    category: str
    message: str
    state: str | None = None
    line_number: int | None = None
    recommendation: str | None = None


@dataclass
class ValidationReport:
    """Complete validation report for an FSA."""

    workflow_name: str
    is_valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    critical_count: int = 0
    error_count: int = 0
    warning_count: int = 0
    info_count: int = 0

    def add_issue(self, issue: ValidationIssue):
        """Add an issue and update counters."""
        self.issues.append(issue)
        if issue.severity == ValidationSeverity.CRITICAL:
            self.critical_count += 1
            self.is_valid = False
        elif issue.severity == ValidationSeverity.ERROR:
            self.error_count += 1
            self.is_valid = False
        elif issue.severity == ValidationSeverity.WARNING:
            self.warning_count += 1
        elif issue.severity == ValidationSeverity.INFO:
            self.info_count += 1


class FSAValidator:
    """Validates FSA structure for correctness and best practices."""

    def __init__(self):
        self.visited_states: Set[str] = set()

    def validate(self, fsa: FSAStructure) -> ValidationReport:
        """
        Perform comprehensive validation on an FSA.

        Args:
            fsa: The FSA structure to validate

        Returns:
            ValidationReport with all findings
        """
        report = ValidationReport(workflow_name=fsa.workflow_name, is_valid=True)

        # Run all validation checks
        self._validate_entry_state(fsa, report)
        self._validate_exit_states(fsa, report)
        self._validate_reachability(fsa, report)
        self._validate_transitions(fsa, report)
        self._validate_error_handling(fsa, report)
        self._validate_state_complexity(fsa, report)
        self._validate_agent_usage(fsa, report)
        self._validate_dead_code(fsa, report)
        self._validate_infinite_loops(fsa, report)
        self._validate_parameters(fsa, report)

        return report

    def _validate_entry_state(self, fsa: FSAStructure, report: ValidationReport):
        """Validate that the FSA has a valid entry state."""
        if not fsa.entry_state:
            report.add_issue(
                ValidationIssue(
                    severity=ValidationSeverity.CRITICAL,
                    category='structure',
                    message='No entry state defined',
                    recommendation='Ensure the workflow has a clear starting point',
                )
            )
        elif fsa.entry_state not in fsa.states:
            report.add_issue(
                ValidationIssue(
                    severity=ValidationSeverity.CRITICAL,
                    category='structure',
                    message=f'Entry state "{fsa.entry_state}" not found in states',
                    state=fsa.entry_state,
                    recommendation='Fix entry state reference',
                )
            )

    def _validate_exit_states(self, fsa: FSAStructure, report: ValidationReport):
        """Validate that the FSA has at least one exit state."""
        if not fsa.exit_states:
            report.add_issue(
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    category='structure',
                    message='No exit states defined - workflow may not terminate properly',
                    recommendation='Add explicit return statements to ensure workflow completes',
                )
            )

        # Check if exit states are reachable
        for exit_state in fsa.exit_states:
            if exit_state not in fsa.states:
                report.add_issue(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        category='structure',
                        message=f'Exit state "{exit_state}" not found in states',
                        state=exit_state,
                    )
                )

    def _validate_reachability(self, fsa: FSAStructure, report: ValidationReport):
        """Validate that all states are reachable from the entry state."""
        if not fsa.entry_state:
            return

        # Build adjacency list
        graph: Dict[str, List[str]] = {state: [] for state in fsa.states}
        for transition in fsa.transitions:
            if transition.from_state in graph:
                graph[transition.from_state].append(transition.to_state)

        # DFS to find reachable states
        reachable = set()
        self._dfs_reachability(fsa.entry_state, graph, reachable)

        # Find unreachable states
        unreachable = set(fsa.states.keys()) - reachable
        for state in unreachable:
            state_obj = fsa.states[state]
            report.add_issue(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category='reachability',
                    message=f'State "{state}" is unreachable from entry state',
                    state=state,
                    line_number=state_obj.line_number,
                    recommendation='Remove unreachable code or fix control flow',
                )
            )

    def _dfs_reachability(self, state: str, graph: Dict[str, List[str]], visited: Set[str]):
        """DFS helper for reachability analysis."""
        if state in visited:
            return
        visited.add(state)
        if state in graph:
            for next_state in graph[state]:
                self._dfs_reachability(next_state, graph, visited)

    def _validate_transitions(self, fsa: FSAStructure, report: ValidationReport):
        """Validate transitions between states."""
        for transition in fsa.transitions:
            # Check if states exist
            if transition.from_state not in fsa.states:
                report.add_issue(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        category='transitions',
                        message=f'Transition from unknown state "{transition.from_state}"',
                        state=transition.from_state,
                        line_number=transition.line_number,
                    )
                )

            if transition.to_state not in fsa.states:
                report.add_issue(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        category='transitions',
                        message=f'Transition to unknown state "{transition.to_state}"',
                        state=transition.to_state,
                        line_number=transition.line_number,
                    )
                )

        # Check for states with no outgoing transitions (except exit states)
        states_with_outgoing = {t.from_state for t in fsa.transitions}
        for state_name in fsa.states:
            if state_name not in states_with_outgoing and state_name not in fsa.exit_states:
                report.add_issue(
                    ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        category='transitions',
                        message=f'State "{state_name}" has no outgoing transitions',
                        state=state_name,
                        line_number=fsa.states[state_name].line_number,
                        recommendation='Ensure state has proper control flow or mark as exit state',
                    )
                )

    def _validate_error_handling(self, fsa: FSAStructure, report: ValidationReport):
        """Validate error handling coverage."""
        # Check if workflow has error states
        if not fsa.error_states:
            # Look for agent calls without error handling
            states_with_agents = [s for s in fsa.states.values() if s.agent_calls]
            if states_with_agents:
                report.add_issue(
                    ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        category='error_handling',
                        message=f'Workflow has {len(states_with_agents)} states with agent calls but no error handling',
                        recommendation='Add try/except blocks around agent calls for robust error handling',
                    )
                )

        # Check for try blocks without corresponding error states
        try_states = [s for s in fsa.states.values() if 'try_' in s.name]
        if len(try_states) > len(fsa.error_states):
            report.add_issue(
                ValidationIssue(
                    severity=ValidationSeverity.INFO,
                    category='error_handling',
                    message='Some try blocks may not have proper exception handlers',
                    recommendation='Verify all try blocks have corresponding except handlers',
                )
            )

    def _validate_state_complexity(self, fsa: FSAStructure, report: ValidationReport):
        """Validate individual state complexity."""
        for state_name, state in fsa.states.items():
            # Check for states with many agent calls
            if len(state.agent_calls) > 3:
                report.add_issue(
                    ValidationIssue(
                        severity=ValidationSeverity.INFO,
                        category='complexity',
                        message=f'State "{state_name}" has {len(state.agent_calls)} agent calls',
                        state=state_name,
                        line_number=state.line_number,
                        recommendation='Consider breaking down into smaller states',
                    )
                )

            # Check for states with many variables
            if len(state.variables_written) > 5:
                report.add_issue(
                    ValidationIssue(
                        severity=ValidationSeverity.INFO,
                        category='complexity',
                        message=f'State "{state_name}" writes to {len(state.variables_written)} variables',
                        state=state_name,
                        line_number=state.line_number,
                        recommendation='Consider simplifying state logic',
                    )
                )

    def _validate_agent_usage(self, fsa: FSAStructure, report: ValidationReport):
        """Validate agent usage patterns."""
        # Check if agents defined in workflow are actually used
        used_agents = set()
        for state in fsa.states.values():
            for agent_call in state.agent_calls:
                # Extract agent name (e.g., "self.my_agent" -> "my_agent")
                if '.' in agent_call:
                    agent_name = agent_call.split('.')[-1]
                    used_agents.add(agent_name)

        defined_agents = set(fsa.agents)
        unused_agents = defined_agents - used_agents

        for agent in unused_agents:
            report.add_issue(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category='agent_usage',
                    message=f'Agent "{agent}" is defined but never used',
                    recommendation='Remove unused agents or add logic to use them',
                )
            )

    def _validate_dead_code(self, fsa: FSAStructure, report: ValidationReport):
        """Detect potential dead code."""
        # States after return statements
        for i, transition in enumerate(fsa.transitions):
            if transition.to_state in fsa.exit_states:
                # Check if there are transitions from this exit state
                next_transitions = [
                    t for t in fsa.transitions[i + 1 :] if t.from_state == transition.to_state
                ]
                if next_transitions:
                    report.add_issue(
                        ValidationIssue(
                            severity=ValidationSeverity.WARNING,
                            category='dead_code',
                            message=f'Code after exit state "{transition.to_state}" may be unreachable',
                            state=transition.to_state,
                            recommendation='Remove unreachable code',
                        )
                    )

    def _validate_infinite_loops(self, fsa: FSAStructure, report: ValidationReport):
        """Detect potential infinite loops."""
        # Build graph
        graph: Dict[str, List[str]] = {state: [] for state in fsa.states}
        for transition in fsa.transitions:
            if transition.from_state in graph:
                graph[transition.from_state].append(transition.to_state)

        # Detect cycles
        for loop_state in fsa.loop_states:
            # Check if loop has an exit condition
            outgoing = graph.get(loop_state, [])
            has_exit = any(target not in fsa.loop_states for target in outgoing)

            if not has_exit:
                report.add_issue(
                    ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        category='infinite_loop',
                        message=f'Loop state "{loop_state}" may not have a clear exit condition',
                        state=loop_state,
                        line_number=fsa.states[loop_state].line_number,
                        recommendation='Ensure loop has a termination condition',
                    )
                )

    def _validate_parameters(self, fsa: FSAStructure, report: ValidationReport):
        """Validate workflow parameters."""
        if not fsa.parameters:
            report.add_issue(
                ValidationIssue(
                    severity=ValidationSeverity.INFO,
                    category='parameters',
                    message='Workflow has no input parameters',
                    recommendation='Consider if workflow should accept parameters',
                )
            )

        # Check for parameters without type annotations
        for param_name, param_info in fsa.parameters.items():
            if param_info['annotation'] == inspect.Parameter.empty:
                report.add_issue(
                    ValidationIssue(
                        severity=ValidationSeverity.INFO,
                        category='parameters',
                        message=f'Parameter "{param_name}" has no type annotation',
                        recommendation='Add type annotations for better clarity and validation',
                    )
                )


import inspect

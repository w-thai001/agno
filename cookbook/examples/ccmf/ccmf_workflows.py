"""
CCMF Workflow Engine - SESSION 1
=================================

This module implements workflow orchestration for the CCMF framework.
It enables the creation, execution, and management of complex multi-step
cognitive workflows that combine patterns, constitutional validation,
and RSI feedback.

Key components:
- Workflow definition and composition
- Step execution and orchestration
- Error handling and recovery
- Workflow monitoring and logging
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
from enum import Enum
import time

from ccmf_patterns import CognitivePattern, PatternResult
from ccmf_constitutional import ComplianceReport, validate_operation
from ccmf_rsi_loop import RSIFeedbackLoop, FeedbackType


class WorkflowStatus(Enum):
    """Status of workflow execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class StepStatus(Enum):
    """Status of individual workflow steps."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class WorkflowStep:
    """Represents a single step in a workflow."""
    step_id: str
    name: str
    description: str
    pattern: Optional[CognitivePattern] = None
    function: Optional[Callable] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    requires_constitutional_validation: bool = True
    retry_on_failure: bool = True
    max_retries: int = 3
    depends_on: List[str] = field(default_factory=list)  # Step IDs this depends on

    status: StepStatus = StepStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    execution_time: float = 0.0
    retry_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert step to dictionary."""
        return {
            'step_id': self.step_id,
            'name': self.name,
            'description': self.description,
            'status': self.status.value,
            'execution_time': self.execution_time,
            'retry_count': self.retry_count,
            'error': self.error,
            'has_result': self.result is not None
        }


@dataclass
class WorkflowExecutionLog:
    """Log entry for workflow execution."""
    timestamp: datetime
    level: str  # INFO, WARNING, ERROR
    step_id: Optional[str]
    message: str
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert log to dictionary."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'level': self.level,
            'step_id': self.step_id,
            'message': self.message,
            'data': self.data
        }


class Workflow:
    """
    Represents a complete workflow with multiple steps.

    A workflow orchestrates the execution of multiple cognitive patterns,
    handles dependencies, validates constitutional compliance, and
    integrates with the RSI feedback loop.
    """

    def __init__(
        self,
        workflow_id: str,
        name: str,
        description: str,
        enable_rsi: bool = True
    ):
        """
        Initialize a workflow.

        Args:
            workflow_id: Unique workflow identifier
            name: Workflow name
            description: Workflow description
            enable_rsi: Whether to enable RSI feedback integration
        """
        self.workflow_id = workflow_id
        self.name = name
        self.description = description
        self.enable_rsi = enable_rsi

        self.steps: List[WorkflowStep] = []
        self.status = WorkflowStatus.PENDING
        self.execution_logs: List[WorkflowExecutionLog] = []

        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.total_execution_time: float = 0.0

        self.rsi_loop: Optional[RSIFeedbackLoop] = None
        if enable_rsi:
            self.rsi_loop = RSIFeedbackLoop()

        self.context: Dict[str, Any] = {}  # Shared context across steps

    def add_step(self, step: WorkflowStep) -> 'Workflow':
        """
        Add a step to the workflow.

        Args:
            step: WorkflowStep to add

        Returns:
            Self for chaining
        """
        self.steps.append(step)
        return self

    def _log(self, level: str, message: str, step_id: Optional[str] = None, data: Optional[Dict[str, Any]] = None):
        """
        Add a log entry.

        Args:
            level: Log level
            message: Log message
            step_id: Optional step ID
            data: Optional additional data
        """
        log = WorkflowExecutionLog(
            timestamp=datetime.now(),
            level=level,
            step_id=step_id,
            message=message,
            data=data or {}
        )
        self.execution_logs.append(log)

    def _validate_step_constitutional_compliance(
        self,
        step: WorkflowStep
    ) -> tuple[bool, ComplianceReport]:
        """
        Validate a step's constitutional compliance.

        Args:
            step: WorkflowStep to validate

        Returns:
            Tuple of (is_compliant, compliance_report)
        """
        # Build validation context
        validation_context = {
            'operation_type': step.name,
            'risk_assessment': 'low',  # Can be made configurable
            'logging_enabled': True,
            'audit_trail': True,
            'resource_estimate': {'cpu': 'medium', 'memory': 'medium'},
            'error_handling': step.retry_on_failure,
            'recovery_strategy': 'retry_with_backoff' if step.retry_on_failure else 'fail',
            'data_classification': 'internal',
            'privacy_check': True,
            'ethical_review': True
        }

        report = validate_operation(validation_context)
        is_compliant = report.compliance_score >= 0.75

        return is_compliant, report

    def _can_execute_step(self, step: WorkflowStep) -> tuple[bool, str]:
        """
        Check if a step can be executed based on dependencies.

        Args:
            step: WorkflowStep to check

        Returns:
            Tuple of (can_execute, reason)
        """
        if not step.depends_on:
            return True, "No dependencies"

        for dep_id in step.depends_on:
            dep_step = next((s for s in self.steps if s.step_id == dep_id), None)
            if not dep_step:
                return False, f"Dependency not found: {dep_id}"
            if dep_step.status != StepStatus.COMPLETED:
                return False, f"Dependency not completed: {dep_id} ({dep_step.status.value})"

        return True, "All dependencies satisfied"

    def _execute_step(self, step: WorkflowStep) -> bool:
        """
        Execute a single workflow step.

        Args:
            step: WorkflowStep to execute

        Returns:
            True if successful, False otherwise
        """
        step.status = StepStatus.RUNNING
        step.start_time = datetime.now()

        self._log("INFO", f"Executing step: {step.name}", step_id=step.step_id)

        try:
            # Constitutional validation
            if step.requires_constitutional_validation:
                is_compliant, compliance_report = self._validate_step_constitutional_compliance(step)
                if not is_compliant:
                    self._log(
                        "ERROR",
                        f"Step failed constitutional validation: {compliance_report.compliance_score:.2%}",
                        step_id=step.step_id,
                        data={'compliance_report': compliance_report.to_dict()}
                    )
                    step.status = StepStatus.FAILED
                    step.error = "Constitutional validation failed"
                    return False

            # Execute the step
            if step.pattern:
                # Execute pattern
                result = step.pattern.execute(**step.parameters)
                step.result = result

                if not result.success:
                    raise RuntimeError(result.error or "Pattern execution failed")

                # Collect RSI feedback
                if self.rsi_loop:
                    self.rsi_loop.collect_feedback(
                        feedback_type=FeedbackType.SUCCESS,
                        source=f"workflow.{self.workflow_id}.{step.step_id}",
                        metrics={
                            'execution_time': result.execution_time,
                            'quality': 1.0  # Can be computed based on result
                        },
                        message=f"Step {step.name} completed successfully"
                    )

            elif step.function:
                # Execute custom function
                start = time.time()
                result = step.function(self.context, **step.parameters)
                execution_time = time.time() - start

                step.result = result

                # Collect RSI feedback
                if self.rsi_loop:
                    self.rsi_loop.collect_feedback(
                        feedback_type=FeedbackType.SUCCESS,
                        source=f"workflow.{self.workflow_id}.{step.step_id}",
                        metrics={
                            'execution_time': execution_time,
                            'quality': 1.0
                        },
                        message=f"Step {step.name} completed successfully"
                    )
            else:
                raise ValueError("Step must have either pattern or function")

            step.status = StepStatus.COMPLETED
            step.end_time = datetime.now()
            step.execution_time = (step.end_time - step.start_time).total_seconds()

            self._log(
                "INFO",
                f"Step completed: {step.name} ({step.execution_time:.2f}s)",
                step_id=step.step_id
            )

            return True

        except Exception as e:
            step.error = str(e)
            self._log(
                "ERROR",
                f"Step failed: {step.name} - {str(e)}",
                step_id=step.step_id
            )

            # Collect RSI feedback for failure
            if self.rsi_loop:
                self.rsi_loop.collect_feedback(
                    feedback_type=FeedbackType.FAILURE,
                    source=f"workflow.{self.workflow_id}.{step.step_id}",
                    metrics={
                        'execution_time': time.time() - step.start_time.timestamp() if step.start_time else 0.0,
                        'quality': 0.0
                    },
                    severity=0.7,
                    message=f"Step {step.name} failed: {str(e)}"
                )

            # Handle retry
            if step.retry_on_failure and step.retry_count < step.max_retries:
                step.retry_count += 1
                self._log(
                    "WARNING",
                    f"Retrying step: {step.name} (attempt {step.retry_count}/{step.max_retries})",
                    step_id=step.step_id
                )
                step.status = StepStatus.PENDING
                return self._execute_step(step)  # Recursive retry

            step.status = StepStatus.FAILED
            step.end_time = datetime.now()
            step.execution_time = (step.end_time - step.start_time).total_seconds()
            return False

    def execute(self) -> Dict[str, Any]:
        """
        Execute the workflow.

        Returns:
            Dictionary with execution results
        """
        self.status = WorkflowStatus.RUNNING
        self.start_time = datetime.now()

        self._log("INFO", f"Starting workflow: {self.name}")

        try:
            # Execute steps in order, respecting dependencies
            for step in self.steps:
                # Check if step can be executed
                can_execute, reason = self._can_execute_step(step)
                if not can_execute:
                    self._log(
                        "WARNING",
                        f"Skipping step {step.name}: {reason}",
                        step_id=step.step_id
                    )
                    step.status = StepStatus.SKIPPED
                    continue

                # Execute step
                success = self._execute_step(step)
                if not success:
                    # Check if workflow should continue
                    self._log(
                        "ERROR",
                        f"Workflow failed at step: {step.name}",
                        step_id=step.step_id
                    )
                    self.status = WorkflowStatus.FAILED
                    break

            # Check if all steps completed
            if all(s.status in [StepStatus.COMPLETED, StepStatus.SKIPPED] for s in self.steps):
                self.status = WorkflowStatus.COMPLETED
                self._log("INFO", "Workflow completed successfully")

            # Run RSI improvement cycle if enabled
            if self.rsi_loop and self.status == WorkflowStatus.COMPLETED:
                self._log("INFO", "Running RSI improvement cycle")
                cycle_result = self.rsi_loop.run_improvement_cycle()
                self._log(
                    "INFO",
                    f"RSI cycle completed - Health: {cycle_result['current_health']:.2%}",
                    data=cycle_result
                )

        except Exception as e:
            self.status = WorkflowStatus.FAILED
            self._log("ERROR", f"Workflow execution error: {str(e)}")

        finally:
            self.end_time = datetime.now()
            self.total_execution_time = (self.end_time - self.start_time).total_seconds()

        return self.get_execution_summary()

    def get_execution_summary(self) -> Dict[str, Any]:
        """
        Get a summary of workflow execution.

        Returns:
            Dictionary with summary data
        """
        completed_steps = sum(1 for s in self.steps if s.status == StepStatus.COMPLETED)
        failed_steps = sum(1 for s in self.steps if s.status == StepStatus.FAILED)
        skipped_steps = sum(1 for s in self.steps if s.status == StepStatus.SKIPPED)

        return {
            'workflow_id': self.workflow_id,
            'name': self.name,
            'status': self.status.value,
            'total_execution_time': self.total_execution_time,
            'steps': {
                'total': len(self.steps),
                'completed': completed_steps,
                'failed': failed_steps,
                'skipped': skipped_steps
            },
            'step_details': [step.to_dict() for step in self.steps],
            'logs': [log.to_dict() for log in self.execution_logs],
            'rsi_enabled': self.enable_rsi,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None
        }


class WorkflowBuilder:
    """
    Builder for creating workflows with a fluent interface.
    """

    def __init__(self, workflow_id: str, name: str, description: str = ""):
        """Initialize the workflow builder."""
        self.workflow = Workflow(workflow_id, name, description)

    def with_rsi(self, enable: bool = True) -> 'WorkflowBuilder':
        """Enable or disable RSI feedback."""
        self.workflow.enable_rsi = enable
        if enable and not self.workflow.rsi_loop:
            self.workflow.rsi_loop = RSIFeedbackLoop()
        return self

    def add_pattern_step(
        self,
        step_id: str,
        name: str,
        pattern: CognitivePattern,
        parameters: Dict[str, Any],
        description: str = "",
        **kwargs
    ) -> 'WorkflowBuilder':
        """Add a pattern-based step."""
        step = WorkflowStep(
            step_id=step_id,
            name=name,
            description=description,
            pattern=pattern,
            parameters=parameters,
            **kwargs
        )
        self.workflow.add_step(step)
        return self

    def add_function_step(
        self,
        step_id: str,
        name: str,
        function: Callable,
        parameters: Dict[str, Any],
        description: str = "",
        **kwargs
    ) -> 'WorkflowBuilder':
        """Add a function-based step."""
        step = WorkflowStep(
            step_id=step_id,
            name=name,
            description=description,
            function=function,
            parameters=parameters,
            **kwargs
        )
        self.workflow.add_step(step)
        return self

    def build(self) -> Workflow:
        """Build and return the workflow."""
        return self.workflow


if __name__ == "__main__":
    # Example usage
    print("CCMF Workflow Engine - Example Usage")
    print("=" * 60)

    from ccmf_patterns import DirectPathAccessPattern, KnownPathSearchPattern

    # Create a workflow
    builder = WorkflowBuilder(
        workflow_id="example_workflow",
        name="Example Workflow",
        description="Demonstrates workflow execution"
    ).with_rsi(True)

    # Add steps
    builder.add_pattern_step(
        step_id="step1",
        name="Check File Existence",
        pattern=DirectPathAccessPattern(),
        parameters={'path': __file__, 'operation': 'exists'},
        description="Check if the current file exists"
    )

    builder.add_pattern_step(
        step_id="step2",
        name="Search Python Files",
        pattern=KnownPathSearchPattern(),
        parameters={
            'search_paths': ['.'],
            'pattern': '*.py',
            'recursive': False
        },
        description="Search for Python files",
        depends_on=['step1']
    )

    # Build and execute workflow
    workflow = builder.build()
    print(f"\nExecuting workflow: {workflow.name}")
    print("-" * 60)

    result = workflow.execute()

    # Display results
    print(f"\nWorkflow Status: {result['status']}")
    print(f"Total Execution Time: {result['total_execution_time']:.2f}s")
    print(f"\nSteps Summary:")
    print(f"  Total: {result['steps']['total']}")
    print(f"  Completed: {result['steps']['completed']}")
    print(f"  Failed: {result['steps']['failed']}")
    print(f"  Skipped: {result['steps']['skipped']}")

    print(f"\nExecution Logs:")
    for log in result['logs'][-5:]:  # Show last 5 logs
        print(f"  [{log['level']}] {log['message']}")

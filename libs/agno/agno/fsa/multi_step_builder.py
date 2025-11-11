"""
FSA-3.1: MultiStepCodeBuilder

Orchestrates multi-step code building by:
- Breaking complex tasks into sequential steps
- Using FSA-1.1 for prompt optimization
- Using FSA-1.2 for template selection
- Using FSA-2.1 for quality validation
- Using FSA-2.2 for model routing
- Managing step dependencies
- Tracking progress and error recovery
"""

from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from pydantic import BaseModel, Field
from agno.utils.log import logger
from datetime import datetime

from agno.fsa.prompt_optimizer import PromptOptimizer, OptimizedPrompt
from agno.fsa.template_selector import TemplateSelector, TemplateSelection, TemplateType
from agno.fsa.quality_validator import QualityValidator, ValidationResult
from agno.fsa.model_router import ModelRouter, RoutingDecision, ModelCapability


class StepStatus(str, Enum):
    """Status of a build step"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class StepType(str, Enum):
    """Types of build steps"""
    ANALYSIS = "analysis"
    DESIGN = "design"
    IMPLEMENTATION = "implementation"
    VALIDATION = "validation"
    INTEGRATION = "integration"
    DOCUMENTATION = "documentation"


class BuildStep(BaseModel):
    """A single step in the build process"""
    id: str = Field(..., description="Step ID")
    name: str = Field(..., description="Step name")
    type: StepType = Field(..., description="Step type")
    description: str = Field(..., description="Step description")
    dependencies: List[str] = Field(default_factory=list, description="Dependent step IDs")
    status: StepStatus = Field(default=StepStatus.PENDING, description="Step status")
    optimized_prompt: Optional[OptimizedPrompt] = Field(None, description="Optimized prompt")
    template_selection: Optional[TemplateSelection] = Field(None, description="Template selection")
    routing_decision: Optional[RoutingDecision] = Field(None, description="Routing decision")
    generated_code: Optional[str] = Field(None, description="Generated code")
    validation_result: Optional[ValidationResult] = Field(None, description="Validation result")
    error: Optional[str] = Field(None, description="Error message if failed")
    start_time: Optional[datetime] = Field(None, description="Step start time")
    end_time: Optional[datetime] = Field(None, description="Step end time")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class BuildProgress(BaseModel):
    """Progress tracking for the build"""
    total_steps: int = Field(..., description="Total number of steps")
    completed_steps: int = Field(0, description="Completed steps")
    failed_steps: int = Field(0, description="Failed steps")
    current_step: Optional[str] = Field(None, description="Current step ID")
    progress_percentage: float = Field(0.0, description="Progress percentage")
    estimated_remaining_time: Optional[float] = Field(None, description="Estimated remaining seconds")


class BuildResult(BaseModel):
    """Result of multi-step build"""
    success: bool = Field(..., description="Whether build succeeded")
    steps: List[BuildStep] = Field(..., description="All build steps")
    integrated_code: Optional[str] = Field(None, description="Final integrated code")
    progress: BuildProgress = Field(..., description="Build progress")
    summary: str = Field(..., description="Build summary")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class MultiStepCodeBuilder:
    """
    FSA-3.1: MultiStepCodeBuilder

    Orchestrates multi-step code building by:
    1. Decomposing complex tasks into sequential steps
    2. Optimizing prompts for each step (FSA-1.1)
    3. Selecting appropriate templates (FSA-1.2)
    4. Routing to appropriate models (FSA-2.2)
    5. Validating code quality (FSA-2.1)
    6. Managing dependencies and integration
    7. Tracking progress and handling errors
    """

    def __init__(
        self,
        debug: bool = False,
        code_generator: Optional[Callable] = None
    ):
        self.debug = debug
        self.code_generator = code_generator or self._default_code_generator

        # Initialize FSA components
        self.prompt_optimizer = PromptOptimizer(debug=debug)
        self.template_selector = TemplateSelector(debug=debug)
        self.quality_validator = QualityValidator(debug=debug)
        self.model_router = ModelRouter(debug=debug)

        logger.info("FSA-3.1: MultiStepCodeBuilder initialized")

    def build(
        self,
        task_description: str,
        context: Optional[Dict[str, Any]] = None
    ) -> BuildResult:
        """
        Execute multi-step build for a task

        Args:
            task_description: Description of the task to build
            context: Additional context for the build

        Returns:
            BuildResult with all steps and integrated code
        """
        logger.info(f"Starting multi-step build: {task_description[:100]}...")

        context = context or {}
        build_start_time = datetime.now()

        try:
            # Step 1: Decompose task into steps
            steps = self.decomposeTask(task_description, context)
            logger.info(f"Task decomposed into {len(steps)} steps")

            # Initialize progress tracking
            progress = BuildProgress(
                total_steps=len(steps),
                completed_steps=0,
                failed_steps=0,
                progress_percentage=0.0
            )

            # Step 2: Build each step
            for step in steps:
                progress.current_step = step.id

                try:
                    self.buildStep(step, context)

                    if step.status == StepStatus.COMPLETED:
                        progress.completed_steps += 1
                    elif step.status == StepStatus.FAILED:
                        progress.failed_steps += 1

                except Exception as e:
                    logger.error(f"Error building step {step.id}: {e}")
                    step.status = StepStatus.FAILED
                    step.error = str(e)
                    progress.failed_steps += 1

                # Update progress
                progress.progress_percentage = (
                    (progress.completed_steps + progress.failed_steps) / progress.total_steps * 100
                )

                if self.debug:
                    logger.debug(f"Progress: {progress.progress_percentage:.1f}%")

            # Step 3: Integrate steps
            integrated_code = self.integrateSteps(steps, context)

            # Step 4: Final validation
            final_validation = self.quality_validator.validate(
                integrated_code,
                language=context.get("language", "python"),
                context=context
            )

            # Determine success
            success = (
                progress.failed_steps == 0 and
                final_validation.passed
            )

            # Generate summary
            summary = self._generate_summary(
                steps,
                progress,
                final_validation,
                success,
                build_start_time
            )

            result = BuildResult(
                success=success,
                steps=steps,
                integrated_code=integrated_code if success else None,
                progress=progress,
                summary=summary,
                metadata={
                    "task_description": task_description,
                    "context": context,
                    "build_duration": (datetime.now() - build_start_time).total_seconds(),
                    "final_validation": final_validation.model_dump()
                }
            )

            logger.info(f"Build completed: {'SUCCESS' if success else 'FAILED'}")
            return result

        except Exception as e:
            logger.error(f"Build failed with error: {e}")
            raise

    def decomposeTask(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[BuildStep]:
        """
        Decompose a complex task into sequential steps

        Args:
            task: Task description
            context: Additional context

        Returns:
            List of BuildStep objects
        """
        if self.debug:
            logger.debug(f"Decomposing task: {task[:100]}...")

        context = context or {}
        steps = []

        # Step 1: Analysis and Planning
        steps.append(BuildStep(
            id="step_1_analysis",
            name="Requirements Analysis",
            type=StepType.ANALYSIS,
            description="Analyze requirements and plan implementation approach",
            dependencies=[]
        ))

        # Step 2: Template Selection (depends on analysis)
        steps.append(BuildStep(
            id="step_2_templates",
            name="Template Selection",
            type=StepType.DESIGN,
            description="Select appropriate code templates and patterns",
            dependencies=["step_1_analysis"]
        ))

        # Analyze task to determine implementation steps
        task_lower = task.lower()

        # Step 3+: Implementation steps based on task analysis
        step_counter = 3

        # Authentication implementation
        if any(word in task_lower for word in ["auth", "authentication", "login", "jwt"]):
            steps.append(BuildStep(
                id=f"step_{step_counter}_auth",
                name="Authentication Implementation",
                type=StepType.IMPLEMENTATION,
                description="Implement authentication system with JWT tokens",
                dependencies=["step_2_templates"]
            ))
            step_counter += 1

        # Database implementation
        if any(word in task_lower for word in ["database", "db", "data", "storage"]):
            steps.append(BuildStep(
                id=f"step_{step_counter}_database",
                name="Database Integration",
                type=StepType.IMPLEMENTATION,
                description="Implement database connection and data layer",
                dependencies=["step_2_templates"]
            ))
            step_counter += 1

        # API/Server implementation
        if any(word in task_lower for word in ["api", "server", "rest", "endpoint"]):
            steps.append(BuildStep(
                id=f"step_{step_counter}_api",
                name="API Server Implementation",
                type=StepType.IMPLEMENTATION,
                description="Implement REST API server with routing",
                dependencies=["step_2_templates"]
            ))
            step_counter += 1

        # Error handling implementation
        if any(word in task_lower for word in ["error", "exception"]) or True:  # Always include
            steps.append(BuildStep(
                id=f"step_{step_counter}_error_handling",
                name="Error Handling Implementation",
                type=StepType.IMPLEMENTATION,
                description="Implement comprehensive error handling",
                dependencies=[f"step_{step_counter-1}_api" if step_counter > 3 else "step_2_templates"]
            ))
            step_counter += 1

        # Integration step
        impl_steps = [s.id for s in steps if s.type == StepType.IMPLEMENTATION]
        steps.append(BuildStep(
            id=f"step_{step_counter}_integration",
            name="Component Integration",
            type=StepType.INTEGRATION,
            description="Integrate all components into cohesive system",
            dependencies=impl_steps
        ))
        step_counter += 1

        # Validation step
        steps.append(BuildStep(
            id=f"step_{step_counter}_validation",
            name="Quality Validation",
            type=StepType.VALIDATION,
            description="Validate code quality and correctness",
            dependencies=[f"step_{step_counter-1}_integration"]
        ))

        if self.debug:
            logger.debug(f"Decomposed into {len(steps)} steps")

        return steps

    def buildStep(
        self,
        step: BuildStep,
        context: Optional[Dict[str, Any]] = None
    ) -> BuildStep:
        """
        Build a single step

        Args:
            step: Step to build
            context: Additional context

        Returns:
            Updated BuildStep
        """
        if self.debug:
            logger.debug(f"Building step: {step.name}")

        context = context or {}
        step.start_time = datetime.now()
        step.status = StepStatus.IN_PROGRESS

        try:
            # Phase 1: Optimize prompt using FSA-1.1
            step.optimized_prompt = self.orchestrateFSAs(
                "optimize_prompt",
                step.description,
                context
            )

            # Phase 2: Select templates using FSA-1.2
            step.template_selection = self.orchestrateFSAs(
                "select_templates",
                step.optimized_prompt.optimized_prompt,
                context
            )

            # Phase 3: Route to model using FSA-2.2
            step.routing_decision = self.orchestrateFSAs(
                "route_model",
                step.optimized_prompt.optimized_prompt,
                {**context, "step_type": step.type}
            )

            # Phase 4: Generate code
            if step.type in [StepType.IMPLEMENTATION, StepType.INTEGRATION]:
                step.generated_code = self.code_generator(
                    step.optimized_prompt.optimized_prompt,
                    step.template_selection,
                    context
                )

                # Phase 5: Validate code using FSA-2.1
                step.validation_result = self.orchestrateFSAs(
                    "validate_quality",
                    step.generated_code,
                    {**context, "language": context.get("language", "python")}
                )

                if not step.validation_result.passed:
                    logger.warning(f"Step {step.id} validation failed")
                    # Could implement retry logic here

            step.status = StepStatus.COMPLETED
            step.end_time = datetime.now()

        except Exception as e:
            logger.error(f"Step {step.id} failed: {e}")
            step.status = StepStatus.FAILED
            step.error = str(e)
            step.end_time = datetime.now()

        return step

    def integrateSteps(
        self,
        steps: List[BuildStep],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Integrate code from all steps

        Args:
            steps: List of completed steps
            context: Additional context

        Returns:
            Integrated code
        """
        if self.debug:
            logger.debug("Integrating steps...")

        context = context or {}
        code_parts = []

        # Add header
        code_parts.append('"""')
        code_parts.append("Multi-Step Code Builder Output")
        code_parts.append(f"Generated by FSA-3.1: MultiStepCodeBuilder")
        code_parts.append('"""')
        code_parts.append("")

        # Add imports
        code_parts.append("# Required imports")
        imports = set()
        for step in steps:
            if step.template_selection:
                for template in step.template_selection.selected_templates:
                    imports.update(template.dependencies)

        if imports:
            for imp in sorted(imports):
                code_parts.append(f"# - {imp}")
            code_parts.append("")

        # Add code from implementation steps
        for step in steps:
            if step.generated_code and step.status == StepStatus.COMPLETED:
                code_parts.append(f"# {step.name}")
                code_parts.append(f"# {step.description}")
                code_parts.append(step.generated_code)
                code_parts.append("")

        integrated = "\n".join(code_parts)

        if self.debug:
            logger.debug(f"Integrated code: {len(integrated)} characters")

        return integrated

    def orchestrateFSAs(
        self,
        operation: str,
        input_data: Any,
        context: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Orchestrate FSA components in pipeline

        Args:
            operation: Operation to perform
            input_data: Input data
            context: Additional context

        Returns:
            Operation result
        """
        context = context or {}

        if operation == "optimize_prompt":
            return self.prompt_optimizer.optimize(input_data, context)

        elif operation == "select_templates":
            return self.template_selector.select_templates(input_data, context)

        elif operation == "route_model":
            return self.model_router.route(
                input_data,
                context.get("required_capabilities"),
                context.get("complexity")
            )

        elif operation == "validate_quality":
            return self.quality_validator.validate(
                input_data,
                context.get("language", "python"),
                context
            )

        else:
            raise ValueError(f"Unknown operation: {operation}")

    def _default_code_generator(
        self,
        prompt: str,
        template_selection: TemplateSelection,
        context: Dict[str, Any]
    ) -> str:
        """
        Default code generator (returns template-based code)

        Args:
            prompt: Optimized prompt
            template_selection: Selected templates
            context: Additional context

        Returns:
            Generated code
        """
        # This is a simplified code generator
        # In production, this would call an actual LLM

        code_parts = []

        for template in template_selection.selected_templates:
            code_parts.append(f"# Template: {template.name}")
            code_parts.append(template.pattern)
            code_parts.append("")

        return "\n".join(code_parts)

    def _generate_summary(
        self,
        steps: List[BuildStep],
        progress: BuildProgress,
        final_validation: ValidationResult,
        success: bool,
        start_time: datetime
    ) -> str:
        """Generate build summary"""
        duration = (datetime.now() - start_time).total_seconds()

        summary_parts = [
            "=" * 60,
            "Multi-Step Code Builder - Build Summary",
            "=" * 60,
            "",
            f"Status: {'SUCCESS' if success else 'FAILED'}",
            f"Duration: {duration:.2f} seconds",
            "",
            "Progress:",
            f"  Total Steps: {progress.total_steps}",
            f"  Completed: {progress.completed_steps}",
            f"  Failed: {progress.failed_steps}",
            f"  Success Rate: {(progress.completed_steps / progress.total_steps * 100):.1f}%",
            "",
            "Final Validation:",
            f"  Quality Score: {final_validation.score:.1f}/100",
            f"  Issues Found: {len(final_validation.issues)}",
            "",
            "Steps:",
        ]

        for step in steps:
            status_symbol = {
                StepStatus.COMPLETED: "✓",
                StepStatus.FAILED: "✗",
                StepStatus.IN_PROGRESS: "◐",
                StepStatus.PENDING: "○",
                StepStatus.SKIPPED: "⊘",
            }.get(step.status, "?")

            summary_parts.append(f"  {status_symbol} {step.name} ({step.status.value})")

        summary_parts.append("")
        summary_parts.append("=" * 60)

        return "\n".join(summary_parts)

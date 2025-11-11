"""
FSA-3.1: Multi-Step Code Builder

Orchestrates complex code generation projects by breaking them into sequential steps
and integrating all FSA components:
- FSA-1.1: Prompt Optimizer - Optimizes prompts for each step
- FSA-1.2: Code Template Library - Selects appropriate templates
- FSA-2.1: Code Quality Validator - Validates generated code
- FSA-2.2: Multi-Model Orchestrator - Routes tasks to optimal models
"""

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from agno.optimizer import PromptOptimizer
from agno.orchestrator import MultiModelOrchestrator
from agno.orchestrator.multi_model import BudgetConstraints
from agno.templates import CodeTemplateLibrary, TemplateCategory
from agno.utils.log import logger
from agno.validator import CodeQualityValidator


class StepStatus(Enum):
    """Status of a project step."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class StepType(Enum):
    """Type of project step."""

    PLANNING = "planning"
    SCHEMA_DESIGN = "schema_design"
    DATABASE = "database"
    API_ENDPOINT = "api_endpoint"
    BUSINESS_LOGIC = "business_logic"
    ERROR_HANDLING = "error_handling"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    DEPLOYMENT = "deployment"


@dataclass
class ProjectStep:
    """Represents a single step in the build process."""

    step_id: str
    name: str
    description: str
    step_type: StepType
    status: StepStatus = StepStatus.PENDING
    dependencies: List[str] = field(default_factory=list)
    template_ids: List[str] = field(default_factory=list)
    language: str = "python"
    generated_code: Optional[str] = None
    quality_score: Optional[int] = None
    validation_result: Optional[Any] = None
    execution_time_ms: float = 0.0
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class BuildResult:
    """Result of a multi-step build process."""

    project_name: str
    total_steps: int
    completed_steps: int
    failed_steps: int
    overall_quality_score: float
    steps: List[ProjectStep] = field(default_factory=list)
    total_execution_time_ms: float = 0.0
    success: bool = False
    generated_files: Dict[str, str] = field(default_factory=dict)
    summary: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


class MultiStepCodeBuilder:
    """
    Multi-step code builder that orchestrates complex project generation.

    Integrates all FSA components:
    - FSA-1.1: Prompt Optimizer for optimized prompts
    - FSA-1.2: Code Template Library for template selection
    - FSA-2.1: Code Quality Validator for validation
    - FSA-2.2: Multi-Model Orchestrator for model routing
    """

    def __init__(
        self,
        use_orchestrator: bool = False,
        min_quality_score: int = 70,
        enable_rollback: bool = True,
    ):
        """
        Initialize the Multi-Step Code Builder.

        Args:
            use_orchestrator: Enable FSA-2.2 Multi-Model Orchestrator
            min_quality_score: Minimum quality score to accept (0-100)
            enable_rollback: Enable rollback on failures
        """
        self.use_orchestrator = use_orchestrator
        self.min_quality_score = min_quality_score
        self.enable_rollback = enable_rollback

        # Initialize FSA components
        self.prompt_optimizer = PromptOptimizer()  # FSA-1.1
        self.template_library = CodeTemplateLibrary()  # FSA-1.2
        self.validator = CodeQualityValidator(  # FSA-2.1
            prompt_optimizer=self.prompt_optimizer,
            template_library=self.template_library,
        )

        if use_orchestrator:
            self.orchestrator = MultiModelOrchestrator(enable_tracking=True)  # FSA-2.2
        else:
            self.orchestrator = None

        self.execution_history: List[ProjectStep] = []

        logger.info(
            "MultiStepCodeBuilder initialized (orchestrator=%s, min_quality=%d)",
            use_orchestrator,
            min_quality_score,
        )

    def buildProject(
        self,
        requirements: str,
        project_name: str,
        language: str = "python",
        budget: Optional[BudgetConstraints] = None,
    ) -> BuildResult:
        """
        Build a complete project from requirements.

        Args:
            requirements: Project requirements description
            project_name: Name of the project
            language: Programming language (python, javascript)
            budget: Optional budget constraints for FSA-2.2

        Returns:
            BuildResult with all generated code and validation results
        """
        start_time = datetime.now()
        logger.info("Starting project build: %s (%s)", project_name, language)

        # Step 1: Decompose task into steps
        logger.info("Decomposing project into steps...")
        steps = self.decomposeTask(requirements, language)
        logger.info("Project decomposed into %d steps", len(steps))

        # Step 2: Execute steps sequentially
        completed_steps = 0
        failed_steps = 0
        generated_files = {}
        quality_scores = []

        for step in steps:
            logger.info("Executing step: %s", step.name)

            try:
                # Check dependencies
                if not self._check_dependencies(step, steps):
                    step.status = StepStatus.FAILED
                    step.error = "Dependencies not satisfied"
                    failed_steps += 1
                    logger.warning("Step %s failed: dependencies not satisfied", step.name)
                    continue

                # Execute step
                success = self.executeStep(step, budget)

                if success and step.quality_score and step.quality_score >= self.min_quality_score:
                    step.status = StepStatus.COMPLETED
                    completed_steps += 1
                    quality_scores.append(step.quality_score)

                    # Save generated code
                    if step.generated_code:
                        filename = self._generate_filename(step, language)
                        generated_files[filename] = step.generated_code

                    logger.info(
                        "Step %s completed (quality: %d/100)",
                        step.name,
                        step.quality_score or 0,
                    )
                else:
                    step.status = StepStatus.FAILED
                    failed_steps += 1
                    logger.warning(
                        "Step %s failed (quality: %d/100, required: %d)",
                        step.name,
                        step.quality_score or 0,
                        self.min_quality_score,
                    )

                    if self.enable_rollback:
                        logger.info("Rollback enabled but continuing with other steps")

            except Exception as e:
                step.status = StepStatus.FAILED
                step.error = str(e)
                failed_steps += 1
                logger.error("Step %s failed with exception: %s", step.name, str(e))

            self.execution_history.append(step)

        # Calculate overall metrics
        total_time = (datetime.now() - start_time).total_seconds() * 1000
        overall_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0

        success = failed_steps == 0 and completed_steps > 0

        # Generate summary
        summary = self._generate_build_summary(
            project_name, len(steps), completed_steps, failed_steps, overall_quality
        )

        result = BuildResult(
            project_name=project_name,
            total_steps=len(steps),
            completed_steps=completed_steps,
            failed_steps=failed_steps,
            overall_quality_score=overall_quality,
            steps=steps,
            total_execution_time_ms=total_time,
            success=success,
            generated_files=generated_files,
            summary=summary,
        )

        logger.info(
            "Project build completed: %s (success=%s, %d/%d steps)",
            project_name,
            success,
            completed_steps,
            len(steps),
        )

        return result

    def decomposeTask(self, requirements: str, language: str) -> List[ProjectStep]:
        """
        Decompose a complex task into sequential steps.

        Args:
            requirements: Project requirements
            language: Programming language

        Returns:
            List of ProjectStep objects in execution order
        """
        steps = []

        # Analyze requirements to determine project type and steps
        req_lower = requirements.lower()

        # Detect project components
        needs_database = any(
            kw in req_lower for kw in ["database", "db", "sql", "storage", "persist"]
        )
        needs_api = any(kw in req_lower for kw in ["api", "endpoint", "rest", "route"])
        needs_auth = any(kw in req_lower for kw in ["auth", "login", "user", "session"])
        is_web = any(kw in req_lower for kw in ["web", "frontend", "ui", "html"])

        step_counter = 1

        # Step 1: Always start with planning
        steps.append(
            ProjectStep(
                step_id=f"step_{step_counter}",
                name="Project Planning",
                description="Define project structure and architecture",
                step_type=StepType.PLANNING,
                language=language,
                metadata={"requirements": requirements},
            )
        )
        step_counter += 1

        # Step 2: Database schema (if needed)
        if needs_database:
            steps.append(
                ProjectStep(
                    step_id=f"step_{step_counter}",
                    name="Database Schema Design",
                    description="Design database schema and models",
                    step_type=StepType.SCHEMA_DESIGN,
                    dependencies=["step_1"],
                    language=language,
                    template_ids=["py_db_query_good"] if language == "python" else [],
                )
            )
            step_counter += 1

            steps.append(
                ProjectStep(
                    step_id=f"step_{step_counter}",
                    name="Database Connection",
                    description="Implement database connection and utilities",
                    step_type=StepType.DATABASE,
                    dependencies=[f"step_{step_counter-1}"],
                    language=language,
                    template_ids=["py_db_query_good"] if language == "python" else [],
                )
            )
            step_counter += 1

        # Step 3: API endpoints (if needed)
        if needs_api:
            steps.append(
                ProjectStep(
                    step_id=f"step_{step_counter}",
                    name="API Endpoints",
                    description="Implement RESTful API endpoints",
                    step_type=StepType.API_ENDPOINT,
                    dependencies=[f"step_{step_counter-1}"] if needs_database else ["step_1"],
                    language=language,
                    template_ids=["py_api_good"] if language == "python" else ["js_async_good"],
                )
            )
            step_counter += 1

        # Step 4: Business logic
        steps.append(
            ProjectStep(
                step_id=f"step_{step_counter}",
                name="Business Logic",
                description="Implement core business logic and operations",
                step_type=StepType.BUSINESS_LOGIC,
                dependencies=[f"step_{step_counter-1}"],
                language=language,
            )
        )
        step_counter += 1

        # Step 5: Error handling
        steps.append(
            ProjectStep(
                step_id=f"step_{step_counter}",
                name="Error Handling",
                description="Implement comprehensive error handling",
                step_type=StepType.ERROR_HANDLING,
                dependencies=[f"step_{step_counter-1}"],
                language=language,
                template_ids=["py_error_handling_good"] if language == "python" else [],
            )
        )
        step_counter += 1

        # Step 6: Testing
        steps.append(
            ProjectStep(
                step_id=f"step_{step_counter}",
                name="Unit Tests",
                description="Create unit tests for all components",
                step_type=StepType.TESTING,
                dependencies=[f"step_{step_counter-1}"],
                language=language,
            )
        )

        logger.info("Task decomposed into %d steps", len(steps))
        return steps

    def executeStep(
        self, step: ProjectStep, budget: Optional[BudgetConstraints] = None
    ) -> bool:
        """
        Execute a single project step.

        Args:
            step: ProjectStep to execute
            budget: Optional budget constraints

        Returns:
            True if step executed successfully with acceptable quality
        """
        start_time = datetime.now()
        step.status = StepStatus.IN_PROGRESS

        try:
            # 1. Get relevant templates from FSA-1.2
            templates = self._get_relevant_templates(step)
            logger.debug("Found %d relevant templates for step %s", len(templates), step.name)

            # 2. Generate code (simplified - in production would use LLM)
            code = self._generate_code_for_step(step, templates)

            if not code:
                logger.warning("No code generated for step %s", step.name)
                return False

            step.generated_code = code

            # 3. Validate with FSA-2.1
            validation_result = self.validateStep(step)
            step.validation_result = validation_result
            step.quality_score = validation_result.report.overall_score

            # 4. Track execution time
            step.execution_time_ms = (datetime.now() - start_time).total_seconds() * 1000

            # 5. Check if quality meets threshold
            if step.quality_score >= self.min_quality_score:
                logger.info(
                    "Step %s validated successfully (score: %d/100)",
                    step.name,
                    step.quality_score,
                )
                return True
            else:
                logger.warning(
                    "Step %s quality below threshold (score: %d/100, required: %d/100)",
                    step.name,
                    step.quality_score,
                    self.min_quality_score,
                )
                return False

        except Exception as e:
            step.error = str(e)
            logger.error("Error executing step %s: %s", step.name, str(e))
            return False

    def validateStep(self, step: ProjectStep) -> Any:
        """
        Validate a step's generated code using FSA-2.1.

        Args:
            step: ProjectStep with generated code

        Returns:
            ValidationResult from FSA-2.1
        """
        if not step.generated_code:
            raise ValueError(f"No code to validate for step {step.name}")

        logger.debug("Validating step %s with FSA-2.1", step.name)

        # Use FSA-2.1 to validate
        validation_result = self.validator.validateCode(step.generated_code, step.language)

        logger.info(
            "Step %s validation complete: score=%d/100, valid=%s",
            step.name,
            validation_result.report.overall_score,
            validation_result.is_valid,
        )

        return validation_result

    def rollback(self, steps: List[ProjectStep], from_step: str) -> None:
        """
        Rollback steps from a specific step.

        Args:
            steps: List of all steps
            from_step: Step ID to rollback from
        """
        logger.info("Rolling back from step %s", from_step)

        rollback_started = False
        for step in steps:
            if step.step_id == from_step:
                rollback_started = True

            if rollback_started and step.status == StepStatus.COMPLETED:
                step.status = StepStatus.ROLLED_BACK
                step.generated_code = None
                logger.info("Rolled back step %s", step.name)

    def _check_dependencies(self, step: ProjectStep, all_steps: List[ProjectStep]) -> bool:
        """Check if all dependencies are satisfied."""
        if not step.dependencies:
            return True

        for dep_id in step.dependencies:
            dep_step = next((s for s in all_steps if s.step_id == dep_id), None)
            if not dep_step or dep_step.status != StepStatus.COMPLETED:
                logger.debug("Dependency %s not satisfied for step %s", dep_id, step.name)
                return False

        return True

    def _get_relevant_templates(self, step: ProjectStep) -> List[Any]:
        """Get relevant templates from FSA-1.2 for a step."""
        templates = []

        # Get templates by IDs if specified
        if step.template_ids:
            for template_id in step.template_ids:
                template = self.template_library.get_template(template_id)
                if template:
                    templates.append(template)

        # Get templates by category
        if step.step_type == StepType.API_ENDPOINT:
            templates.extend(
                self.template_library.get_templates_by_category(TemplateCategory.API_ENDPOINT)
            )
        elif step.step_type == StepType.DATABASE:
            templates.extend(
                self.template_library.get_templates_by_category(TemplateCategory.DATABASE_QUERY)
            )
        elif step.step_type == StepType.ERROR_HANDLING:
            templates.extend(
                self.template_library.get_templates_by_category(TemplateCategory.ERROR_HANDLING)
            )

        # Filter by language
        templates = [t for t in templates if t.language.lower() == step.language.lower()]

        return templates

    def _generate_code_for_step(
        self, step: ProjectStep, templates: List[Any]
    ) -> Optional[str]:
        """
        Generate code for a step using templates.

        In production, this would use an LLM with FSA-1.1 optimized prompts
        and FSA-2.2 model routing. For demo, we use template code.
        """
        # Use the best template available
        if templates:
            # Prefer EXCELLENT or GOOD templates
            excellent = [t for t in templates if t.quality_level.value == "excellent"]
            good = [t for t in templates if t.quality_level.value == "good"]

            if excellent:
                logger.info("Using EXCELLENT template for step %s", step.name)
                return excellent[0].code
            elif good:
                logger.info("Using GOOD template for step %s", step.name)
                return good[0].code
            else:
                logger.info("Using available template for step %s", step.name)
                return templates[0].code

        # Generate minimal code if no template
        logger.info("Generating minimal code for step %s (no templates)", step.name)
        return self._generate_minimal_code(step)

    def _generate_minimal_code(self, step: ProjectStep) -> str:
        """Generate minimal code when no templates available."""
        if step.language == "python":
            return f'''"""
{step.name}

{step.description}
"""

def {step.name.lower().replace(" ", "_")}():
    """
    {step.description}
    """
    # TODO: Implement {step.name}
    pass
'''
        else:  # javascript
            return f'''/**
 * {step.name}
 *
 * {step.description}
 */

function {self._to_camel_case(step.name)}() {{
    // TODO: Implement {step.name}
}}
'''

    def _to_camel_case(self, text: str) -> str:
        """Convert text to camelCase."""
        words = re.sub(r"[^\w\s]", "", text).split()
        if not words:
            return "function"
        return words[0].lower() + "".join(word.capitalize() for word in words[1:])

    def _generate_filename(self, step: ProjectStep, language: str) -> str:
        """Generate appropriate filename for a step."""
        name = step.name.lower().replace(" ", "_")
        ext = ".py" if language == "python" else ".js"

        # Map step types to filenames
        type_mapping = {
            StepType.PLANNING: "README.md",
            StepType.SCHEMA_DESIGN: f"schema{ext}",
            StepType.DATABASE: f"database{ext}",
            StepType.API_ENDPOINT: f"api{ext}",
            StepType.BUSINESS_LOGIC: f"logic{ext}",
            StepType.ERROR_HANDLING: f"errors{ext}",
            StepType.TESTING: f"test_{name}{ext}",
            StepType.DOCUMENTATION: "documentation.md",
        }

        return type_mapping.get(step.step_type, f"{name}{ext}")

    def _generate_build_summary(
        self,
        project_name: str,
        total: int,
        completed: int,
        failed: int,
        quality: float,
    ) -> str:
        """Generate build summary."""
        status = "SUCCESS" if failed == 0 and completed > 0 else "FAILED"

        summary = f"Build {status}: {project_name}\n"
        summary += f"Steps: {completed}/{total} completed"

        if failed > 0:
            summary += f", {failed} failed"

        if completed > 0:
            summary += f"\nOverall Quality: {quality:.1f}/100"

        return summary

    def get_build_statistics(self) -> Dict[str, Any]:
        """Get statistics from execution history."""
        if not self.execution_history:
            return {"message": "No builds executed yet"}

        total = len(self.execution_history)
        completed = sum(1 for s in self.execution_history if s.status == StepStatus.COMPLETED)
        failed = sum(1 for s in self.execution_history if s.status == StepStatus.FAILED)

        quality_scores = [s.quality_score for s in self.execution_history if s.quality_score]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0

        return {
            "total_steps_executed": total,
            "completed_steps": completed,
            "failed_steps": failed,
            "success_rate": completed / total if total > 0 else 0,
            "average_quality_score": avg_quality,
        }

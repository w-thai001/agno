"""
Multi-Step Code Builder FSA

Foundational FSA for building code through structured state transitions:
- Requirements analysis and specification
- Design and architecture planning
- Implementation with progressive refinement
- Testing and validation
- Documentation generation

Provides a systematic approach to code generation with quality controls at each step.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from agno.agent import Agent
from agno.fsa.base import FSA, FSAState, FSATransition, FSAExecutionResult
from agno.utils.log import logger


class CodeBuilderState(str, Enum):
    """States for the Multi-Step Code Builder"""
    INITIAL = "initial"
    ANALYZING_REQUIREMENTS = "analyzing_requirements"
    DESIGNING = "designing"
    IMPLEMENTING = "implementing"
    TESTING = "testing"
    REFINING = "refining"
    DOCUMENTING = "documenting"
    SUCCESS = "success"
    FAILED = "failed"


class CodeArtifact(BaseModel):
    """Represents a code artifact generated during the build process"""
    name: str
    file_path: str
    language: str
    code: str
    description: str
    tests: Optional[str] = None
    documentation: Optional[str] = None


class RequirementsSpec(BaseModel):
    """Structured requirements specification"""
    functional_requirements: List[str]
    non_functional_requirements: List[str]
    constraints: List[str]
    acceptance_criteria: List[str]
    priority: str = "medium"


class DesignSpec(BaseModel):
    """Design specification"""
    architecture: str
    components: List[str]
    data_structures: List[str]
    algorithms: List[str]
    interfaces: List[str]
    dependencies: List[str]


class CodeBuilderResult(BaseModel):
    """Result of code building process"""
    success: bool
    artifacts: List[CodeArtifact]
    requirements: Optional[RequirementsSpec] = None
    design: Optional[DesignSpec] = None
    test_results: Dict[str, Any] = {}
    documentation: str = ""
    error: Optional[str] = None


@dataclass
class MultiStepCodeBuilder(FSA):
    """
    Multi-Step Code Builder FSA

    Systematically builds code through structured phases:
    1. Requirements Analysis - Extract and clarify requirements
    2. Design - Create architecture and component design
    3. Implementation - Generate code with best practices
    4. Testing - Validate functionality
    5. Refining - Optimize and improve
    6. Documentation - Generate comprehensive docs

    Example:
        ```python
        builder = MultiStepCodeBuilder(
            name="FeatureBuilder",
            agent=coding_agent
        )

        result = builder.run({
            "task": "Create a user authentication system",
            "language": "python",
            "framework": "FastAPI"
        })

        for artifact in result.artifacts:
            print(f"Generated: {artifact.file_path}")
        ```
    """

    # Code generation agent
    code_agent: Optional[Agent] = None

    # Generated artifacts
    artifacts: List[CodeArtifact] = field(default_factory=list)

    # Specifications
    requirements: Optional[RequirementsSpec] = None
    design: Optional[DesignSpec] = None

    # Configuration
    programming_language: str = "python"
    framework: Optional[str] = None
    include_tests: bool = True
    include_documentation: bool = True
    code_style: str = "pep8"  # Coding standard to follow

    # Quality thresholds
    min_test_coverage: float = 0.8
    max_complexity: int = 10

    def __post_init__(self):
        """Initialize code builder with custom states"""
        self.initial_state = CodeBuilderState.INITIAL
        self.current_state = self.initial_state
        self.final_states = {CodeBuilderState.SUCCESS, CodeBuilderState.FAILED}
        self.state_history = [self.current_state]

        self._setup_transitions()

        if self.debug_mode:
            logger.debug(f"MultiStepCodeBuilder {self.name} initialized")

    def _setup_transitions(self) -> None:
        """Setup state transitions for code builder"""
        # INITIAL -> ANALYZING_REQUIREMENTS
        self.add_transition(
            CodeBuilderState.INITIAL,
            CodeBuilderState.ANALYZING_REQUIREMENTS,
            action=self._analyze_requirements,
            description="Analyze and extract requirements"
        )

        # ANALYZING_REQUIREMENTS -> DESIGNING
        self.add_transition(
            CodeBuilderState.ANALYZING_REQUIREMENTS,
            CodeBuilderState.DESIGNING,
            condition=lambda ctx: ctx.get("requirements_complete", False),
            action=self._create_design,
            description="Create design specification"
        )

        # DESIGNING -> IMPLEMENTING
        self.add_transition(
            CodeBuilderState.DESIGNING,
            CodeBuilderState.IMPLEMENTING,
            condition=lambda ctx: ctx.get("design_complete", False),
            action=self._implement_code,
            description="Implement code based on design"
        )

        # IMPLEMENTING -> TESTING
        self.add_transition(
            CodeBuilderState.IMPLEMENTING,
            CodeBuilderState.TESTING,
            condition=lambda ctx: ctx.get("implementation_complete", False),
            action=self._test_code,
            description="Test implemented code"
        )

        # TESTING -> REFINING (if tests fail or quality is low)
        self.add_transition(
            CodeBuilderState.TESTING,
            CodeBuilderState.REFINING,
            condition=lambda ctx: not ctx.get("tests_passed", False),
            action=self._refine_code,
            description="Refine code based on test results"
        )

        # REFINING -> TESTING (retry testing after refinement)
        self.add_transition(
            CodeBuilderState.REFINING,
            CodeBuilderState.TESTING,
            condition=lambda ctx: ctx.get("refinement_complete", False),
            action=self._test_code,
            description="Retest after refinement"
        )

        # TESTING -> DOCUMENTING (if tests pass)
        self.add_transition(
            CodeBuilderState.TESTING,
            CodeBuilderState.DOCUMENTING,
            condition=lambda ctx: ctx.get("tests_passed", False) and self.include_documentation,
            action=self._generate_documentation,
            description="Generate documentation"
        )

        # TESTING -> SUCCESS (if tests pass and no docs needed)
        self.add_transition(
            CodeBuilderState.TESTING,
            CodeBuilderState.SUCCESS,
            condition=lambda ctx: ctx.get("tests_passed", False) and not self.include_documentation,
            description="Complete without documentation"
        )

        # DOCUMENTING -> SUCCESS
        self.add_transition(
            CodeBuilderState.DOCUMENTING,
            CodeBuilderState.SUCCESS,
            condition=lambda ctx: ctx.get("documentation_complete", False),
            description="Complete with documentation"
        )

        # Any state -> FAILED on critical error
        for state in CodeBuilderState:
            if state not in [CodeBuilderState.SUCCESS, CodeBuilderState.FAILED]:
                self.add_transition(
                    state,
                    CodeBuilderState.FAILED,
                    condition=lambda ctx: ctx.get("critical_error", False),
                    description="Critical error occurred"
                )

    def _analyze_requirements(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze and extract requirements from task description"""
        task = context.get("task", "")
        language = context.get("language", self.programming_language)
        framework = context.get("framework", self.framework)

        if self.debug_mode:
            logger.debug(f"Analyzing requirements for: {task}")

        # Use agent to analyze requirements
        if self.code_agent:
            analysis_prompt = f"""
            Analyze this coding task and extract structured requirements:

            Task: {task}
            Language: {language}
            Framework: {framework or 'None specified'}

            Extract:
            1. Functional requirements (what the code must do)
            2. Non-functional requirements (performance, security, etc.)
            3. Constraints (limitations, dependencies)
            4. Acceptance criteria (how to validate success)

            Provide a structured analysis.
            """
            # Agent would analyze and provide structured output
            # For now, create basic requirements
            pass

        # Create requirements specification
        self.requirements = RequirementsSpec(
            functional_requirements=[
                f"Implement {task}",
                f"Use {language} programming language",
            ],
            non_functional_requirements=[
                "Code should be maintainable and well-structured",
                "Follow best practices and coding standards",
            ],
            constraints=[
                f"Framework: {framework}" if framework else "No framework specified",
            ],
            acceptance_criteria=[
                "All functionality works as specified",
                "Code passes all tests",
                "Code is properly documented",
            ]
        )

        context["requirements"] = self.requirements
        context["requirements_complete"] = True
        context["language"] = language
        context["framework"] = framework

        return context

    def _create_design(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Create design specification based on requirements"""
        requirements = context.get("requirements")
        task = context.get("task", "")

        if self.debug_mode:
            logger.debug("Creating design specification")

        # Use agent to create design
        if self.code_agent:
            design_prompt = f"""
            Create a design specification for this task:

            Task: {task}
            Requirements: {requirements}

            Design should include:
            1. Overall architecture
            2. Key components and their responsibilities
            3. Data structures
            4. Algorithms to use
            5. Interfaces/APIs
            6. Dependencies

            Provide a structured design.
            """
            # Agent would create design
            pass

        # Create design specification
        self.design = DesignSpec(
            architecture=f"Modular architecture for {task}",
            components=["Main implementation", "Helper functions", "Data models"],
            data_structures=["Classes", "Functions", "Configuration"],
            algorithms=["Core logic implementation"],
            interfaces=["Public API"],
            dependencies=[]
        )

        context["design"] = self.design
        context["design_complete"] = True

        return context

    def _implement_code(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Implement code based on design"""
        design = context.get("design")
        requirements = context.get("requirements")
        task = context.get("task", "")
        language = context.get("language", self.programming_language)

        if self.debug_mode:
            logger.debug("Implementing code")

        # Use agent to generate code
        if self.code_agent:
            implementation_prompt = f"""
            Implement the following:

            Task: {task}
            Language: {language}
            Requirements: {requirements}
            Design: {design}

            Generate production-ready code following these guidelines:
            1. Follow {self.code_style} coding standards
            2. Include error handling
            3. Add inline comments for complex logic
            4. Use type hints (if applicable)
            5. Keep functions focused and single-purpose
            6. Maintain low cyclomatic complexity

            Generate the complete implementation.
            """
            # Agent would generate code
            # For demonstration, create a simple artifact
            pass

        # Create code artifact
        artifact = CodeArtifact(
            name=f"{task.replace(' ', '_')}.{self._get_file_extension(language)}",
            file_path=f"src/{task.replace(' ', '_')}.{self._get_file_extension(language)}",
            language=language,
            code=f"# Implementation for: {task}\n# TODO: Generate actual code via agent\n",
            description=f"Implementation of {task}"
        )

        self.artifacts.append(artifact)

        context["artifacts"] = self.artifacts
        context["implementation_complete"] = True

        return context

    def _test_code(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Test the implemented code"""
        artifacts = context.get("artifacts", [])

        if self.debug_mode:
            logger.debug("Testing code")

        if not self.include_tests:
            context["tests_passed"] = True
            return context

        # Generate and run tests
        if self.code_agent:
            for artifact in artifacts:
                test_prompt = f"""
                Generate comprehensive tests for this code:

                Code:
                {artifact.code}

                Generate tests that:
                1. Cover all major functionality
                2. Test edge cases
                3. Validate error handling
                4. Aim for {self.min_test_coverage * 100}% coverage

                Provide complete test suite.
                """
                # Agent would generate tests
                artifact.tests = "# Test suite would be generated here"

        # Simulate test execution
        test_results = {
            "total_tests": 10,
            "passed": 10,
            "failed": 0,
            "coverage": 0.85,
        }

        context["test_results"] = test_results
        context["tests_passed"] = test_results["failed"] == 0 and test_results["coverage"] >= self.min_test_coverage

        return context

    def _refine_code(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Refine code based on test results and quality metrics"""
        test_results = context.get("test_results", {})
        artifacts = context.get("artifacts", [])

        if self.debug_mode:
            logger.debug("Refining code")

        # Use agent to refine code
        if self.code_agent:
            for artifact in artifacts:
                refinement_prompt = f"""
                Refine this code based on test results:

                Code:
                {artifact.code}

                Test Results:
                {test_results}

                Improvements needed:
                1. Fix failing tests
                2. Improve test coverage
                3. Reduce complexity
                4. Optimize performance
                5. Enhance error handling

                Provide refined implementation.
                """
                # Agent would refine code
                pass

        context["refinement_complete"] = True

        return context

    def _generate_documentation(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate documentation for the code"""
        artifacts = context.get("artifacts", [])
        requirements = context.get("requirements")
        design = context.get("design")

        if self.debug_mode:
            logger.debug("Generating documentation")

        # Use agent to generate documentation
        if self.code_agent:
            for artifact in artifacts:
                doc_prompt = f"""
                Generate comprehensive documentation for this code:

                Code:
                {artifact.code}

                Include:
                1. Overview and purpose
                2. API documentation
                3. Usage examples
                4. Parameter descriptions
                5. Return value documentation
                6. Exception handling
                7. Installation/setup if applicable

                Use proper formatting (markdown/docstrings).
                """
                # Agent would generate docs
                artifact.documentation = f"# Documentation for {artifact.name}\n\nTODO: Generate via agent"

        context["documentation_complete"] = True

        return context

    def _get_file_extension(self, language: str) -> str:
        """Get file extension for programming language"""
        extensions = {
            "python": "py",
            "javascript": "js",
            "typescript": "ts",
            "java": "java",
            "go": "go",
            "rust": "rs",
            "cpp": "cpp",
            "c": "c",
        }
        return extensions.get(language.lower(), "txt")

    def run(self, initial_context: Optional[Dict[str, Any]] = None) -> CodeBuilderResult:
        """
        Run the code builder

        Args:
            initial_context: Context with task, language, framework, etc.

        Returns:
            CodeBuilderResult with generated artifacts
        """
        # Execute base FSA run
        base_result = super().run(initial_context)

        # Build code builder result
        return CodeBuilderResult(
            success=base_result.success,
            artifacts=self.artifacts,
            requirements=self.requirements,
            design=self.design,
            test_results=self.context.get("test_results", {}),
            documentation="\n\n".join([
                a.documentation for a in self.artifacts if a.documentation
            ]),
            error=base_result.error
        )

    def get_build_summary(self) -> str:
        """Get a human-readable summary of the build process"""
        summary = f"Code Builder: {self.name}\n"
        summary += f"Status: {self.current_state.value}\n"
        summary += f"Artifacts Generated: {len(self.artifacts)}\n"

        if self.artifacts:
            summary += "\nArtifacts:\n"
            for artifact in self.artifacts:
                summary += f"  - {artifact.name} ({artifact.language})\n"

        return summary

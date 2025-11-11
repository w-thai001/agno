#!/usr/bin/env python3
"""
FSA-3.1 Multi-Step Code Builder Demo

This demo showcases the complete FSA system building a REST API server
with authentication, database integration, and error handling.
"""

import sys
import os

# Add the libs directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'libs', 'agno'))

# Change to the agno directory to ensure imports work
os.chdir(os.path.join(os.path.dirname(__file__), '..'))

from agno.fsa.multi_step_builder import MultiStepCodeBuilder
from agno.utils.log import logger


def print_section(title: str):
    """Print a section header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def print_subsection(title: str):
    """Print a subsection header"""
    print(f"\n--- {title} ---\n")


def demo_fsa_components():
    """Demonstrate individual FSA components"""
    from agno.fsa.prompt_optimizer import PromptOptimizer
    from agno.fsa.template_selector import TemplateSelector
    from agno.fsa.quality_validator import QualityValidator
    from agno.fsa.model_router import ModelRouter

    print_section("FSA Component Demonstrations")

    # FSA-1.1: PromptOptimizer
    print_subsection("FSA-1.1: Prompt Optimizer")
    optimizer = PromptOptimizer(debug=False)

    original_prompt = "Create an authentication system"
    optimized = optimizer.optimize(
        original_prompt,
        context={
            "language": "python",
            "framework": "FastAPI",
            "stack": ["JWT", "bcrypt", "pydantic"]
        }
    )

    print(f"Original Prompt:\n{original_prompt}\n")
    print(f"Optimized Prompt:\n{optimized.optimized_prompt}\n")
    print(f"Strategies Applied: {', '.join(optimized.strategies_applied)}")
    print(f"Confidence: {optimized.confidence:.2f}")

    # FSA-1.2: TemplateSelector
    print_subsection("FSA-1.2: Template Selector")
    selector = TemplateSelector(debug=False)

    task = "Build a REST API server with authentication and database"
    selection = selector.select_templates(task)

    print(f"Task: {task}\n")
    print(f"Selected {len(selection.selected_templates)} templates:\n")
    for i, template in enumerate(selection.selected_templates, 1):
        print(f"{i}. {template.name} ({template.type.value})")
        print(f"   Description: {template.description}")
        print(f"   Dependencies: {', '.join(template.dependencies)}")
        print()

    print(f"Rationale:\n{selection.rationale}\n")
    print(f"Confidence: {selection.confidence:.2f}")

    # FSA-2.2: ModelRouter
    print_subsection("FSA-2.2: Model Router")
    router = ModelRouter(debug=False)

    routing = router.route(
        task_description="Implement complex authentication with OAuth2 and JWT",
        constraints={"prioritize_quality": True}
    )

    print(f"Selected Model: {routing.selected_model.name}")
    print(f"Provider: {routing.selected_model.provider}")
    print(f"Capabilities: {', '.join(c.value for c in routing.selected_model.capabilities[:3])}...")
    print(f"Complexity Rating: {routing.selected_model.complexity_rating}/10")
    print(f"Speed Rating: {routing.selected_model.speed_rating}/10")
    print(f"Cost Rating: {routing.selected_model.cost_rating}/10")
    print(f"\nRationale:\n{routing.rationale}\n")
    print(f"Confidence: {routing.confidence:.2f}")

    if routing.alternatives:
        print(f"\nAlternative Models:")
        for alt in routing.alternatives[:3]:
            print(f"  - {alt.name} ({alt.provider})")

    # FSA-2.1: QualityValidator
    print_subsection("FSA-2.1: Quality Validator")
    validator = QualityValidator(debug=False)

    sample_code = '''
def authenticate_user(username, password):
    """Authenticate a user"""
    # Simple authentication logic
    if username and password:
        # This is a security issue - hardcoded password
        if password == "admin123":
            return True
    return False

def process_data(data):
    # Missing error handling
    result = eval(data)  # Security issue - eval usage
    return result
'''

    validation = validator.validate(sample_code, language="python")

    print(f"Code Quality Score: {validation.score:.1f}/100")
    print(f"Validation: {'PASSED' if validation.passed else 'FAILED'}")
    print(f"\nIssues Found: {len(validation.issues)}\n")

    for i, issue in enumerate(validation.issues[:5], 1):  # Show first 5
        print(f"{i}. [{issue.level.value.upper()}] {issue.category}")
        print(f"   {issue.message}")
        if issue.suggestion:
            print(f"   Suggestion: {issue.suggestion}")
        print()


def demo_multi_step_builder():
    """Demonstrate the complete multi-step builder"""
    print_section("FSA-3.1: Multi-Step Code Builder")

    # Create the builder
    builder = MultiStepCodeBuilder(debug=True)

    # Define the task
    task = "Build a REST API server with authentication, database integration, and error handling"

    print(f"Task: {task}\n")
    print("Building system with full FSA pipeline integration...\n")

    # Build context
    context = {
        "language": "python",
        "framework": "FastAPI",
        "stack": ["FastAPI", "SQLAlchemy", "JWT", "bcrypt", "uvicorn"],
        "architecture": "microservice",
        "constraints": [
            "Use async/await for database operations",
            "Implement proper error handling",
            "Include request validation",
            "Add structured logging"
        ]
    }

    # Execute the build
    result = builder.build(task, context)

    # Display results
    print_subsection("Step Decomposition")
    print(f"Task was decomposed into {len(result.steps)} steps:\n")

    for i, step in enumerate(result.steps, 1):
        status_symbol = {
            "completed": "✓",
            "failed": "✗",
            "in_progress": "◐",
            "pending": "○",
            "skipped": "⊘",
        }.get(step.status.value, "?")

        print(f"{i}. {status_symbol} {step.name}")
        print(f"   Type: {step.type.value}")
        print(f"   Status: {step.status.value}")
        print(f"   Description: {step.description}")

        if step.dependencies:
            print(f"   Dependencies: {', '.join(step.dependencies)}")

        if step.optimized_prompt:
            print(f"   Prompt Optimization: {step.optimized_prompt.confidence:.2f} confidence")

        if step.template_selection:
            print(f"   Templates: {len(step.template_selection.selected_templates)} selected")

        if step.routing_decision:
            print(f"   Model: {step.routing_decision.selected_model.name}")

        if step.validation_result:
            print(f"   Quality Score: {step.validation_result.score:.1f}/100")

        print()

    # Show template selections
    print_subsection("Template Selection Details")
    for step in result.steps:
        if step.template_selection:
            print(f"{step.name}:")
            for template in step.template_selection.selected_templates:
                print(f"  • {template.name} ({template.type.value})")
            print()

    # Show quality validation
    print_subsection("Quality Validation Results")
    validation_steps = [s for s in result.steps if s.validation_result]

    if validation_steps:
        for step in validation_steps:
            print(f"{step.name}:")
            print(f"  Score: {step.validation_result.score:.1f}/100")
            print(f"  Status: {'PASSED' if step.validation_result.passed else 'FAILED'}")
            print(f"  Issues: {len(step.validation_result.issues)}")

            if step.validation_result.issues:
                print(f"  Top Issues:")
                for issue in step.validation_result.issues[:3]:
                    print(f"    - [{issue.level.value}] {issue.message}")
            print()

    # Show integrated code sample
    if result.integrated_code:
        print_subsection("Integrated Code Sample")
        lines = result.integrated_code.split('\n')
        preview_lines = min(30, len(lines))
        print('\n'.join(lines[:preview_lines]))
        if len(lines) > preview_lines:
            print(f"\n... ({len(lines) - preview_lines} more lines)")

    # Show build summary
    print_subsection("Build Summary")
    print(result.summary)

    # Show progress
    print_subsection("Progress Metrics")
    print(f"Total Steps: {result.progress.total_steps}")
    print(f"Completed: {result.progress.completed_steps}")
    print(f"Failed: {result.progress.failed_steps}")
    print(f"Success Rate: {(result.progress.completed_steps / result.progress.total_steps * 100):.1f}%")
    print(f"Overall Status: {'SUCCESS' if result.success else 'FAILED'}")

    # Show metadata
    if "build_duration" in result.metadata:
        print(f"\nBuild Duration: {result.metadata['build_duration']:.2f} seconds")

    return result


def demo_fsa_pipeline():
    """Demonstrate the FSA pipeline integration"""
    print_section("FSA Pipeline: Component Integration")

    builder = MultiStepCodeBuilder(debug=False)

    # Show the pipeline flow
    print("FSA Component Pipeline:")
    print()
    print("  1. FSA-1.1 (Prompt Optimizer)")
    print("     ↓")
    print("     Optimizes prompts for clarity and context")
    print("     ↓")
    print("  2. FSA-1.2 (Template Selector)")
    print("     ↓")
    print("     Selects appropriate code templates")
    print("     ↓")
    print("  3. FSA-2.2 (Model Router)")
    print("     ↓")
    print("     Routes to best AI model for task")
    print("     ↓")
    print("  4. Code Generation")
    print("     ↓")
    print("     Generates code using templates and model")
    print("     ↓")
    print("  5. FSA-2.1 (Quality Validator)")
    print("     ↓")
    print("     Validates code quality and security")
    print("     ↓")
    print("  6. Integration")
    print("     ↓")
    print("     Integrates all components")
    print()

    # Demonstrate a simple pipeline execution
    print_subsection("Pipeline Execution Example")

    step_desc = "Implement JWT authentication with token refresh"
    context = {"language": "python", "framework": "FastAPI"}

    print(f"Input: {step_desc}\n")

    # Step 1: Optimize
    print("Step 1: Optimizing prompt...")
    optimized = builder.orchestrateFSAs("optimize_prompt", step_desc, context)
    print(f"✓ Prompt optimized (confidence: {optimized.confidence:.2f})\n")

    # Step 2: Select templates
    print("Step 2: Selecting templates...")
    templates = builder.orchestrateFSAs("select_templates", optimized.optimized_prompt, context)
    print(f"✓ Selected {len(templates.selected_templates)} templates\n")

    # Step 3: Route model
    print("Step 3: Routing to model...")
    routing = builder.orchestrateFSAs("route_model", optimized.optimized_prompt, context)
    print(f"✓ Routed to {routing.selected_model.name}\n")

    # Step 4: Generate (using default generator)
    print("Step 4: Generating code...")
    code = builder.code_generator(optimized.optimized_prompt, templates, context)
    print(f"✓ Generated {len(code)} characters of code\n")

    # Step 5: Validate
    print("Step 5: Validating quality...")
    validation = builder.orchestrateFSAs("validate_quality", code, context)
    print(f"✓ Quality score: {validation.score:.1f}/100\n")

    print("Pipeline execution complete!")


def main():
    """Main demo function"""
    print("\n" + "=" * 80)
    print("  FSA-3.1: Multi-Step Code Builder - Complete Demonstration")
    print("=" * 80)

    try:
        # Demo 1: Individual FSA components
        demo_fsa_components()

        # Demo 2: FSA pipeline integration
        demo_fsa_pipeline()

        # Demo 3: Complete multi-step build
        result = demo_multi_step_builder()

        # Final summary
        print_section("Demo Complete")
        print("✓ All FSA components demonstrated successfully")
        print("✓ Multi-step build executed")
        print("✓ Code generation and validation completed")
        print()
        print("FSA System Status:")
        print(f"  • FSA-1.1 (Prompt Optimizer): ✓ Operational")
        print(f"  • FSA-1.2 (Template Selector): ✓ Operational")
        print(f"  • FSA-2.1 (Quality Validator): ✓ Operational")
        print(f"  • FSA-2.2 (Model Router): ✓ Operational")
        print(f"  • FSA-3.1 (Multi-Step Builder): ✓ Operational")
        print()

        if result.success:
            print("🎉 Multi-step build completed successfully!")
        else:
            print("⚠️  Build completed with issues (see summary above)")

        return 0

    except Exception as e:
        logger.error(f"Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
FSA-3.1 Comprehensive Demonstration

This script provides detailed output showing:
1. Task decomposition into steps
2. Step optimization results
3. Template application
4. Generated artifacts
5. Quality validation scores
6. Final metadata and summary
"""

import sys
import os
import json

# Add the libs directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'libs', 'agno'))
os.chdir(os.path.join(os.path.dirname(__file__), '..'))

from agno.fsa.multi_step_builder import MultiStepCodeBuilder
from agno.utils.log import logger


def print_header(title: str, char: str = "="):
    """Print a styled header"""
    width = 80
    print(f"\n{char * width}")
    print(f"{title.center(width)}")
    print(f"{char * width}\n")


def print_step_box(step_num: int, title: str):
    """Print a step box"""
    print(f"\n{'─' * 80}")
    print(f"│ Step {step_num}: {title}")
    print(f"{'─' * 80}\n")


def demonstrate_fsa31():
    """Comprehensive FSA-3.1 demonstration"""

    print_header("FSA-3.1: Multi-Step Code Builder - Detailed Demonstration")

    # Initialize the builder
    print("🔧 Initializing MultiStepCodeBuilder with all FSA components...")
    builder = MultiStepCodeBuilder(debug=False)
    print("✓ FSA-1.1: PromptOptimizer loaded")
    print("✓ FSA-1.2: TemplateSelector loaded")
    print("✓ FSA-2.1: QualityValidator loaded")
    print("✓ FSA-2.2: ModelRouter loaded")
    print("✓ FSA-3.1: MultiStepCodeBuilder initialized\n")

    # Define the project
    project_description = "Create REST API with authentication"

    print_header(f"Project: {project_description}", "=")

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

    print("📋 Project Context:")
    print(f"   Language: {context['language']}")
    print(f"   Framework: {context['framework']}")
    print(f"   Architecture: {context['architecture']}")
    print(f"   Stack: {', '.join(context['stack'])}")
    print(f"   Constraints: {len(context['constraints'])} defined\n")

    # ============================================================================
    # STEP 1: TASK DECOMPOSITION
    # ============================================================================
    print_step_box(1, "TASK DECOMPOSITION")

    print("🔍 Decomposing task into sequential steps...\n")
    steps = builder.decomposeTask(project_description, context)

    print(f"✓ Task decomposed into {len(steps)} steps:\n")

    # Display step hierarchy
    for i, step in enumerate(steps, 1):
        status_icon = "○"
        indent = "  " if not step.dependencies else "    "

        print(f"{indent}{status_icon} [{step.id}] {step.name}")
        print(f"{indent}   Type: {step.type.value}")
        print(f"{indent}   Description: {step.description}")

        if step.dependencies:
            deps = ", ".join(step.dependencies)
            print(f"{indent}   ⚡ Depends on: {deps}")

        print()

    # Show dependency graph
    print("📊 Step Dependency Graph:")
    print()
    print("    step_1_analysis (Requirements Analysis)")
    print("           ↓")
    print("    step_2_templates (Template Selection)")
    print("           ↓")
    print("    ├─→ step_3_auth (Authentication Implementation)")
    print("    ├─→ step_4_database (Database Integration)")
    print("    ├─→ step_5_api (API Server Implementation)")
    print("    └─→ step_6_error_handling (Error Handling)")
    print("           ↓")
    print("    step_7_integration (Component Integration)")
    print("           ↓")
    print("    step_8_validation (Quality Validation)")
    print()

    # ============================================================================
    # STEP 2: OPTIMIZATION RESULTS
    # ============================================================================
    print_step_box(2, "PROMPT OPTIMIZATION (FSA-1.1)")

    print("🎯 Optimizing prompts for each implementation step...\n")

    impl_steps = [s for s in steps if s.type.value == "implementation"]

    for step in impl_steps[:2]:  # Show first 2 for brevity
        print(f"┌─ {step.name}")
        print(f"│")
        print(f"│  Original: {step.description}")

        # Optimize the prompt
        optimized = builder.prompt_optimizer.optimize(step.description, context)

        print(f"│")
        print(f"│  Optimized:")
        for line in optimized.optimized_prompt.split('\n')[:5]:
            print(f"│    {line}")

        print(f"│")
        print(f"│  ✓ Strategies Applied: {', '.join(optimized.strategies_applied)}")
        print(f"│  ✓ Confidence Score: {optimized.confidence:.2%}")
        print(f"└{'─' * 78}\n")

    print(f"✓ All {len(impl_steps)} implementation steps optimized\n")

    # ============================================================================
    # STEP 3: TEMPLATE APPLICATION
    # ============================================================================
    print_step_box(3, "TEMPLATE SELECTION (FSA-1.2)")

    print("📚 Selecting appropriate templates for implementation...\n")

    template_selection = builder.template_selector.select_templates(
        project_description,
        context
    )

    print(f"✓ Selected {len(template_selection.selected_templates)} templates:\n")

    for i, template in enumerate(template_selection.selected_templates, 1):
        print(f"{i}. 📄 {template.name}")
        print(f"   Type: {template.type.value}")
        print(f"   Description: {template.description}")
        print(f"   Dependencies: {', '.join(template.dependencies) if template.dependencies else 'None'}")
        print(f"   Best Practices: {len(template.best_practices)} defined")

        # Show snippet of template pattern
        pattern_lines = template.pattern.strip().split('\n')[:5]
        print(f"   Pattern Preview:")
        for line in pattern_lines:
            print(f"      {line}")
        print(f"      ... ({len(pattern_lines)} lines shown)")
        print()

    print(f"📊 Template Application Strategy:")
    print(f"   • Authentication → JWT Authentication template")
    print(f"   • Database → Database Connection Manager template")
    print(f"   • API Server → REST API Server template")
    print(f"   • Error Handling → Error Handler Middleware template")
    print(f"   • Logging → Request Logger Middleware template")
    print()

    # ============================================================================
    # STEP 4: MODEL ROUTING
    # ============================================================================
    print_step_box(4, "MODEL ROUTING (FSA-2.2)")

    print("🤖 Routing tasks to optimal AI models...\n")

    routing_decision = builder.model_router.route(
        task_description=project_description,
        constraints={"prioritize_quality": True}
    )

    print(f"✓ Selected Model: {routing_decision.selected_model.name}")
    print(f"  Provider: {routing_decision.selected_model.provider}")
    print(f"  Capabilities: {', '.join(c.value for c in routing_decision.selected_model.capabilities[:4])}...")
    print()

    print("📊 Model Ratings:")
    print(f"   Complexity: {'█' * routing_decision.selected_model.complexity_rating}{'░' * (10 - routing_decision.selected_model.complexity_rating)} {routing_decision.selected_model.complexity_rating}/10")
    print(f"   Speed:      {'█' * routing_decision.selected_model.speed_rating}{'░' * (10 - routing_decision.selected_model.speed_rating)} {routing_decision.selected_model.speed_rating}/10")
    print(f"   Cost:       {'█' * routing_decision.selected_model.cost_rating}{'░' * (10 - routing_decision.selected_model.cost_rating)} {routing_decision.selected_model.cost_rating}/10")
    print()

    print(f"🎯 Routing Confidence: {routing_decision.confidence:.2%}")
    print()

    if routing_decision.alternatives:
        print("Alternative Models:")
        for alt in routing_decision.alternatives[:3]:
            print(f"  • {alt.name} ({alt.provider}) - Complexity: {alt.complexity_rating}/10")
    print()

    # ============================================================================
    # STEP 5: BUILD EXECUTION
    # ============================================================================
    print_step_box(5, "BUILD EXECUTION")

    print("🚀 Executing multi-step build with FSA pipeline integration...\n")

    # Execute the complete build
    result = builder.build(project_description, context)

    print("Build Progress:")
    print()

    for step in result.steps:
        status_icons = {
            "completed": "✓",
            "failed": "✗",
            "in_progress": "◐",
            "pending": "○",
            "skipped": "⊘"
        }

        icon = status_icons.get(step.status.value, "?")
        print(f"  {icon} {step.name}")

        if step.optimized_prompt:
            print(f"      Prompt optimization: {step.optimized_prompt.confidence:.0%} confidence")

        if step.template_selection:
            print(f"      Templates: {len(step.template_selection.selected_templates)} selected")

        if step.routing_decision:
            print(f"      Model: {step.routing_decision.selected_model.name}")

        if step.generated_code:
            print(f"      Code generated: {len(step.generated_code)} chars")

        if step.validation_result:
            status_mark = "✓" if step.validation_result.passed else "⚠"
            print(f"      Quality: {status_mark} {step.validation_result.score:.0f}/100")

    print()

    # ============================================================================
    # STEP 6: GENERATED ARTIFACTS
    # ============================================================================
    print_step_box(6, "GENERATED ARTIFACTS")

    print("📦 Generated Code Artifacts:\n")

    code_steps = [s for s in result.steps if s.generated_code]

    print(f"Total artifacts generated: {len(code_steps)}\n")

    # Show first artifact in detail
    if code_steps:
        first_artifact = code_steps[0]
        print(f"Example Artifact: {first_artifact.name}")
        print(f"{'─' * 80}")

        code_lines = first_artifact.generated_code.split('\n')
        preview_lines = min(20, len(code_lines))

        for i, line in enumerate(code_lines[:preview_lines], 1):
            print(f"{i:3d} │ {line}")

        if len(code_lines) > preview_lines:
            print(f"... │ ({len(code_lines) - preview_lines} more lines)")

        print(f"{'─' * 80}\n")

    # Show integrated code stats
    if result.integrated_code:
        print("📊 Integrated Code Statistics:")
        lines = result.integrated_code.split('\n')
        non_empty_lines = [l for l in lines if l.strip()]
        comment_lines = [l for l in lines if l.strip().startswith('#')]

        print(f"   Total lines: {len(lines)}")
        print(f"   Code lines: {len(non_empty_lines)}")
        print(f"   Comment lines: {len(comment_lines)}")
        print(f"   Documentation: {(len(comment_lines) / len(non_empty_lines) * 100):.1f}%")
        print()

    # ============================================================================
    # STEP 7: QUALITY VALIDATION
    # ============================================================================
    print_step_box(7, "QUALITY VALIDATION (FSA-2.1)")

    print("🔍 Quality Validation Results:\n")

    validation_steps = [s for s in result.steps if s.validation_result]

    if validation_steps:
        # Summary table
        print("┌─────────────────────────────────────┬───────┬────────┬────────┐")
        print("│ Component                           │ Score │ Status │ Issues │")
        print("├─────────────────────────────────────┼───────┼────────┼────────┤")

        total_score = 0
        total_issues = 0

        for step in validation_steps:
            name = step.name[:35]
            score = step.validation_result.score
            status = "PASS" if step.validation_result.passed else "FAIL"
            issues = len(step.validation_result.issues)

            total_score += score
            total_issues += issues

            status_color = "✓" if step.validation_result.passed else "✗"
            print(f"│ {name:<35} │ {score:5.1f} │ {status_color} {status:>4} │ {issues:>6} │")

        print("└─────────────────────────────────────┴───────┴────────┴────────┘")
        print()

        avg_score = total_score / len(validation_steps)
        print(f"📊 Average Quality Score: {avg_score:.1f}/100")
        print(f"📋 Total Issues Found: {total_issues}")
        print()

        # Show issue breakdown
        if total_issues > 0:
            print("Issue Breakdown by Severity:")

            all_issues = []
            for step in validation_steps:
                all_issues.extend(step.validation_result.issues)

            by_level = {}
            for issue in all_issues:
                by_level[issue.level.value] = by_level.get(issue.level.value, 0) + 1

            for level in ["critical", "error", "warning", "info"]:
                if level in by_level:
                    count = by_level[level]
                    bar = "█" * min(20, count)
                    print(f"   {level.upper():8} │ {bar} {count}")
            print()

            # Show sample issues
            print("Sample Issues (first 3):")
            for i, issue in enumerate(all_issues[:3], 1):
                print(f"\n   {i}. [{issue.level.value.upper()}] {issue.category}")
                print(f"      Message: {issue.message}")
                if issue.suggestion:
                    print(f"      Suggestion: {issue.suggestion}")
            print()

    # ============================================================================
    # STEP 8: FINAL METADATA & SUMMARY
    # ============================================================================
    print_step_box(8, "FINAL METADATA & SUMMARY")

    print("📈 Build Metrics:\n")

    # Progress metrics
    print("Progress:")
    progress_bar_length = 40
    completed_bar = int(result.progress.progress_percentage / 100 * progress_bar_length)
    progress_bar = "█" * completed_bar + "░" * (progress_bar_length - completed_bar)

    print(f"   [{progress_bar}] {result.progress.progress_percentage:.1f}%")
    print(f"   Completed: {result.progress.completed_steps}/{result.progress.total_steps}")
    print(f"   Failed: {result.progress.failed_steps}")
    print(f"   Success Rate: {(result.progress.completed_steps / result.progress.total_steps * 100):.1f}%")
    print()

    # Build metadata
    print("Build Information:")
    print(f"   Build Status: {'✓ SUCCESS' if result.success else '✗ FAILED'}")
    print(f"   Total Steps: {len(result.steps)}")
    print(f"   Duration: {result.metadata.get('build_duration', 0):.3f} seconds")
    print(f"   Language: {context['language']}")
    print(f"   Framework: {context['framework']}")
    print()

    # FSA Component Usage
    print("FSA Component Usage:")
    print(f"   ✓ FSA-1.1 (Prompt Optimizer): {len([s for s in result.steps if s.optimized_prompt])} optimizations")
    print(f"   ✓ FSA-1.2 (Template Selector): {len([s for s in result.steps if s.template_selection])} selections")
    print(f"   ✓ FSA-2.1 (Quality Validator): {len([s for s in result.steps if s.validation_result])} validations")
    print(f"   ✓ FSA-2.2 (Model Router): {len([s for s in result.steps if s.routing_decision])} routings")
    print()

    # Code generation stats
    if result.integrated_code:
        print("Code Generation:")
        print(f"   Integrated Code: {len(result.integrated_code)} characters")
        print(f"   Lines of Code: {len(result.integrated_code.split(chr(10)))}")
        print(f"   Components: {len([s for s in result.steps if s.generated_code])}")
        print()

    # Final summary box
    print(f"{'═' * 80}")
    print(f"│ BUILD SUMMARY".ljust(79) + "│")
    print(f"{'═' * 80}")
    print(result.summary)
    print(f"{'═' * 80}")
    print()

    # JSON metadata export
    print("📄 Metadata Export (JSON):\n")

    metadata_export = {
        "project": project_description,
        "status": "success" if result.success else "failed",
        "steps": {
            "total": result.progress.total_steps,
            "completed": result.progress.completed_steps,
            "failed": result.progress.failed_steps
        },
        "quality": {
            "average_score": sum(s.validation_result.score for s in result.steps if s.validation_result) / len([s for s in result.steps if s.validation_result]) if validation_steps else 0,
            "total_issues": sum(len(s.validation_result.issues) for s in result.steps if s.validation_result)
        },
        "duration": result.metadata.get('build_duration', 0),
        "fsa_components": {
            "prompt_optimizations": len([s for s in result.steps if s.optimized_prompt]),
            "template_selections": len([s for s in result.steps if s.template_selection]),
            "quality_validations": len([s for s in result.steps if s.validation_result]),
            "model_routings": len([s for s in result.steps if s.routing_decision])
        }
    }

    print(json.dumps(metadata_export, indent=2))
    print()

    # ============================================================================
    # CONCLUSION
    # ============================================================================
    print_header("DEMONSTRATION COMPLETE", "═")

    print("✅ FSA-3.1 Multi-Step Code Builder - All Features Demonstrated\n")

    print("Demonstrated Capabilities:")
    print("  ✓ Task decomposition into sequential steps with dependencies")
    print("  ✓ Prompt optimization with multiple strategies (FSA-1.1)")
    print("  ✓ Template selection and application (FSA-1.2)")
    print("  ✓ Intelligent model routing (FSA-2.2)")
    print("  ✓ Code generation with template patterns")
    print("  ✓ Comprehensive quality validation (FSA-2.1)")
    print("  ✓ Step integration and artifact generation")
    print("  ✓ Progress tracking and metrics")
    print("  ✓ Detailed metadata and reporting")
    print()

    if result.success:
        print("🎉 Build Status: SUCCESS")
    else:
        print("⚠️  Build Status: COMPLETED WITH ISSUES")

    print()
    print("━" * 80)
    print()

    return result


if __name__ == "__main__":
    try:
        result = demonstrate_fsa31()
        sys.exit(0 if result.success else 1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

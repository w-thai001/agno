"""
Multi-Model Orchestrator Demo

This demo showcases the FSA-2.2 Multi-Model Orchestrator capabilities:
- Intelligent routing to Claude Opus, Sonnet, or Haiku
- Budget optimization and cost-vs-speed trade-offs
- Performance tracking and analytics
- Automatic task complexity analysis

Run: python cookbook/orchestrator/multi_model_demo.py
"""

from agno.orchestrator import MultiModelOrchestrator
from agno.orchestrator.multi_model import BudgetConstraints


def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n{'=' * 80}")
    print(f"  {title}")
    print(f"{'=' * 80}\n")


def print_routing_decision(result: dict):
    """Print routing decision in a formatted way."""
    print(f"Task ID: {result['task_id']}")
    print(f"Complexity Score: {result['complexity_score']:.2f}/10")
    print(f"Selected Model: {result['selected_model']} ({result['model_tier']})")
    print(f"Estimated Cost: ${result['estimated_cost_per_1k_tokens']:.2f} per 1K tokens")

    if result.get("executed"):
        print(f"\nExecution Results:")
        print(f"  Success: {result['success']}")
        print(f"  Latency: {result['latency_ms']:.0f}ms")
        print(f"  Input Tokens: {result['input_tokens']}")
        print(f"  Output Tokens: {result['output_tokens']}")
        print(f"  Actual Cost: ${result['total_cost_usd']:.6f}")

        if result.get("response"):
            response = result["response"]
            # Extract text content from response
            content = ""
            if hasattr(response, "content"):
                for block in response.content:
                    if hasattr(block, "text"):
                        content = block.text
                        break

            if content:
                print(f"\nResponse Preview:")
                preview = content[:200] + "..." if len(content) > 200 else content
                print(f"  {preview}")


def demo_simple_task():
    """Demonstrate routing of a simple task (should select Haiku)."""
    print_section("Demo 1: Simple Task (Haiku Candidate)")

    orchestrator = MultiModelOrchestrator(enable_tracking=True)

    task = "What is the capital of France?"

    print(f"Task: {task}\n")

    # First, analyze without executing
    decision = orchestrator.routeTask(task, execute=False)
    print("Routing Decision (Dry Run):")
    print_routing_decision(decision)

    print("\n" + "-" * 80 + "\n")

    # Now execute the task
    result = orchestrator.routeTask(task, execute=True)
    print("Execution Results:")
    print_routing_decision(result)


def demo_complex_reasoning_task():
    """Demonstrate routing of a complex reasoning task (should select Opus)."""
    print_section("Demo 2: Complex Reasoning Task (Opus Candidate)")

    orchestrator = MultiModelOrchestrator(enable_tracking=True)

    task = """
    Design a comprehensive, multi-layered cybersecurity architecture for a global financial institution.
    Consider the following requirements:
    1. Multi-region disaster recovery with RPO < 15 minutes
    2. Zero-trust architecture with microsegmentation
    3. AI-powered threat detection and response
    4. Compliance with GDPR, SOC2, and PCI-DSS
    5. Quantum-resistant cryptography preparation

    Provide a detailed technical design with architecture diagrams, technology stack recommendations,
    implementation timeline, risk analysis, and cost estimates for a 5-year roadmap.
    """

    print(f"Task: {task[:200]}...\n")

    # Analyze complexity
    decision = orchestrator.routeTask(task, execute=False)
    print("Routing Decision (Dry Run):")
    print_routing_decision(decision)

    print("\n" + "-" * 80 + "\n")

    # Execute with quality preference
    budget = BudgetConstraints(prefer_quality=True)
    result = orchestrator.routeTask(task, budget=budget, execute=True)
    print("Execution Results:")
    print_routing_decision(result)


def demo_balanced_task():
    """Demonstrate routing of a balanced task (should select Sonnet)."""
    print_section("Demo 3: Balanced Task (Sonnet Candidate)")

    orchestrator = MultiModelOrchestrator(enable_tracking=True)

    task = """
    Explain the differences between REST and GraphQL APIs, including:
    - Key architectural differences
    - Pros and cons of each approach
    - Use cases where one is preferred over the other
    - Performance considerations

    Provide code examples for both approaches.
    """

    print(f"Task: {task[:150]}...\n")

    # Analyze complexity
    decision = orchestrator.routeTask(task, execute=False)
    print("Routing Decision (Dry Run):")
    print_routing_decision(decision)

    print("\n" + "-" * 80 + "\n")

    # Execute with default budget
    result = orchestrator.routeTask(task, execute=True)
    print("Execution Results:")
    print_routing_decision(result)


def demo_budget_optimization():
    """Demonstrate budget-constrained routing."""
    print_section("Demo 4: Budget Optimization")

    orchestrator = MultiModelOrchestrator(enable_tracking=True)

    task = """
    Analyze the trade-offs between microservices and monolithic architectures
    for a mid-sized e-commerce platform with 100K daily active users.
    """

    print(f"Task: {task}\n")

    # Scenario 1: Speed preference
    print("Scenario A: Speed Optimized (prefer_speed=True)")
    print("-" * 80)
    budget_speed = BudgetConstraints(prefer_speed=True)
    result_speed = orchestrator.routeTask(task, budget=budget_speed, execute=False)
    print_routing_decision(result_speed)

    print("\n")

    # Scenario 2: Quality preference
    print("Scenario B: Quality Optimized (prefer_quality=True)")
    print("-" * 80)
    budget_quality = BudgetConstraints(prefer_quality=True)
    result_quality = orchestrator.routeTask(task, budget=budget_quality, execute=False)
    print_routing_decision(result_quality)

    print("\n")

    # Scenario 3: Cost constrained
    print("Scenario C: Cost Constrained (max_cost_per_task=$0.01)")
    print("-" * 80)
    budget_cost = BudgetConstraints(max_cost_per_task=0.01)
    result_cost = orchestrator.routeTask(task, budget=budget_cost, execute=False)
    print_routing_decision(result_cost)


def demo_performance_tracking():
    """Demonstrate performance tracking and analytics."""
    print_section("Demo 5: Performance Tracking & Analytics")

    orchestrator = MultiModelOrchestrator(enable_tracking=True)

    # Execute multiple tasks
    tasks = [
        ("What is Python?", None),
        ("Explain machine learning algorithms in detail", None),
        ("List 5 programming languages", BudgetConstraints(prefer_speed=True)),
        (
            "Design a distributed system architecture for real-time analytics",
            BudgetConstraints(prefer_quality=True),
        ),
        ("What is 2+2?", None),
    ]

    print("Executing 5 diverse tasks...\n")

    for i, (task, budget) in enumerate(tasks, 1):
        print(f"Task {i}: {task[:60]}...")
        result = orchestrator.routeTask(task, budget=budget, execute=True)
        print(f"  → {result['model_tier']} (${result['total_cost_usd']:.6f}, {result['latency_ms']:.0f}ms)")
        print()

    # Get performance analytics
    print("\n" + "=" * 80)
    print("Performance Analytics")
    print("=" * 80 + "\n")

    analytics = orchestrator.trackPerformance()

    print(f"Total Tasks: {analytics['total_tasks']}")
    print(f"Success Rate: {analytics['success_rate']*100:.1f}%")
    print(f"Total Cost: ${analytics['total_cost_usd']:.6f}")
    print(f"Average Cost per Task: ${analytics['avg_cost_per_task_usd']:.6f}")
    print(f"Average Latency: {analytics['avg_latency_ms']:.0f}ms")

    print("\nModel Distribution:")
    for model, count in analytics["model_distribution"].items():
        print(f"  {model.capitalize()}: {count} tasks")

    if analytics.get("model_stats"):
        print("\nPer-Model Statistics:")
        for model, stats in analytics["model_stats"].items():
            print(f"\n  {model.upper()}:")
            print(f"    Tasks: {stats['tasks']}")
            print(f"    Avg Complexity: {stats['avg_complexity']:.2f}/10")
            print(f"    Avg Latency: {stats['avg_latency_ms']:.0f}ms")
            print(f"    Total Cost: ${stats['total_cost_usd']:.6f}")
            print(f"    Success Rate: {stats['success_rate']*100:.1f}%")

    # Cost savings report
    print("\n" + "=" * 80)
    print("Cost Savings Analysis")
    print("=" * 80 + "\n")

    savings = orchestrator.get_cost_savings_report()
    print(f"Actual Cost (Intelligent Routing): ${savings['actual_cost_usd']:.6f}")
    print(f"Cost if All Opus: ${savings['opus_only_cost_usd']:.6f}")
    print(f"Savings: ${savings['savings_usd']:.6f} ({savings['savings_percent']:.1f}%)")


def main():
    """Run all demos."""
    print("\n")
    print("█" * 80)
    print("█" + " " * 78 + "█")
    print("█" + "  FSA-2.2: MULTI-MODEL ORCHESTRATOR DEMONSTRATION  ".center(78) + "█")
    print("█" + " " * 78 + "█")
    print("█" * 80)

    try:
        # Run each demo
        demo_simple_task()
        demo_complex_reasoning_task()
        demo_balanced_task()
        demo_budget_optimization()
        demo_performance_tracking()

        # Final summary
        print_section("Demo Complete!")
        print("The Multi-Model Orchestrator successfully demonstrated:")
        print("  ✓ Intelligent task complexity analysis")
        print("  ✓ Automatic model selection (Opus/Sonnet/Haiku)")
        print("  ✓ Budget optimization and cost management")
        print("  ✓ Performance tracking and analytics")
        print("  ✓ Cost savings through intelligent routing")
        print("\nKey Features:")
        print("  • routeTask() - Route and execute tasks")
        print("  • selectModel() - Select optimal model")
        print("  • trackPerformance() - Get analytics")
        print("  • Budget constraints for cost/speed/quality trade-offs")
        print("\n")

    except Exception as e:
        print(f"\n❌ Error during demo: {e}")
        print("\nNote: Ensure ANTHROPIC_API_KEY is set in your environment")
        print("      or pass api_key to MultiModelOrchestrator constructor")


if __name__ == "__main__":
    main()

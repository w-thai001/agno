"""⚡ RSI Code Optimizer Example

This example demonstrates using the Recursive Self-Improvement (RSI) Code Optimizer
to automatically optimize code and learn from successful optimizations.

Run `pip install agno openai` to install dependencies.
"""

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.fsa.code_optimizer import RSICodeOptimizer, OptimizationType


def main():
    """Demonstrate RSI Code Optimizer"""

    # Sample code to optimize
    sample_code = """
def process_items(items):
    result = []
    for item in items:
        if item > 0:
            squared = item * item
            result.append(squared)
    return result

def find_max(numbers):
    max_val = numbers[0]
    for num in numbers:
        if num > max_val:
            max_val = num
    return max_val
"""

    # Create optimization agent
    optimization_agent = Agent(
        name="OptimizerAgent",
        model=OpenAIChat(id="gpt-4o"),
        description="Expert at code optimization and performance improvement",
        markdown=True
    )

    # Create optimizer
    optimizer = RSICodeOptimizer(
        name="PythonOptimizer",
        optimization_agent=optimization_agent,
        enable_learning=True,
        enable_self_improvement=True,
        optimization_goals={
            OptimizationType.PERFORMANCE,
            OptimizationType.READABILITY,
            OptimizationType.COMPLEXITY
        },
        debug_mode=True
    )

    # Optimize the code
    result = optimizer.run({
        "code": sample_code,
        "optimization_goals": ["performance", "readability"]
    })

    print("\n" + "=" * 60)
    print("RSI CODE OPTIMIZER RESULTS")
    print("=" * 60)

    print(f"\nSuccess: {result.success}")
    print(f"Total Improvement: {result.total_improvement:.1f}%")
    print(f"Optimizations Applied: {len(result.optimizations_applied)}")
    print(f"Patterns Learned: {len(result.patterns_learned)}")

    print("\n📊 BEFORE METRICS:")
    print(f"   Complexity: {result.before_metrics.cyclomatic_complexity}")
    print(f"   Lines: {result.before_metrics.lines_of_code}")
    print(f"   Readability: {result.before_metrics.readability_score}/100")

    print("\n📈 AFTER METRICS:")
    print(f"   Complexity: {result.after_metrics.cyclomatic_complexity}")
    print(f"   Lines: {result.after_metrics.lines_of_code}")
    print(f"   Readability: {result.after_metrics.readability_score}/100")

    print("\n🔧 OPTIMIZATION OPPORTUNITIES:")
    for i, opp in enumerate(result.opportunities_identified, 1):
        print(f"\n  {i}. {opp.description}")
        print(f"     Type: {opp.type.value}")
        print(f"     Expected Improvement: {opp.expected_improvement}%")
        print(f"     Confidence: {opp.confidence:.0%}")

    print("\n✅ OPTIMIZATIONS APPLIED:")
    for opt in result.optimizations_applied:
        if opt.success:
            print(f"   ✓ {opt.opportunity_id}: {opt.actual_improvement:.1f}% improvement")

    if result.patterns_learned:
        print("\n🧠 PATTERNS LEARNED (Self-Improvement):")
        for pattern in result.patterns_learned:
            print(f"   - {pattern.type.value}: {pattern.success_rate:.0%} success rate")

    if result.self_improvement_gains:
        print("\n🚀 SELF-IMPROVEMENT GAINS:")
        for opt_type, gain in result.self_improvement_gains.items():
            print(f"   - {opt_type}: {gain:.1f}% average improvement")

    # Save learned patterns for future use
    # optimizer.save_knowledge_base("optimizer_knowledge.json")
    print("\n💾 Knowledge base can be saved and reused across optimizations")


if __name__ == "__main__":
    main()

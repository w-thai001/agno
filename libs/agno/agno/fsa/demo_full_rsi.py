"""Full 5-iteration demo of FSA-3.2 RSI Code Optimizer

This script demonstrates the complete recursive self-improvement loop over 5 iterations.
"""

from agno.fsa.rsi_optimizer import RSICodeOptimizer


def main():
    """Run full 5-iteration RSI optimization demo"""

    # Sample JavaScript code to optimize
    sample_code = """function calc(a,b){return a+b}"""

    print("\n" + "=" * 70)
    print("FSA-3.2: FULL RSI CODE OPTIMIZER DEMO (5 ITERATIONS)")
    print("=" * 70)
    print("\nSample Code:")
    print(sample_code)
    print()

    # Initialize optimizer with higher target to force 5 iterations
    optimizer = RSICodeOptimizer(
        convergence_threshold=1.0,   # Very low threshold to continue improving
        plateau_patience=3,          # Wait 3 iterations for plateau
        max_iterations=5,            # Maximum 5 iterations as requested
        target_quality=99.0,         # High target to ensure 5 iterations
    )

    # Execute RSI loop
    result = optimizer.improve_code(
        code=sample_code,
        iterations=5,
        language="javascript",
        verbose=True,
    )

    # Display quality improvement trajectory with detailed scores
    print("\n" + "=" * 70)
    print("DETAILED QUALITY METRICS PER ITERATION")
    print("=" * 70)

    for i, iteration in enumerate(result.iterations):
        print(f"\n{'─' * 70}")
        print(f"ITERATION {iteration.iteration}")
        print(f"{'─' * 70}")
        print(f"Overall Quality Score:  {iteration.quality_score:.2f}/100")
        print(f"Improvement Delta:      {iteration.improvement_delta:+.2f} points")
        print(f"\nDimension Scores:")
        print(f"  • Readability:        {iteration.metrics.readability:.2f}/100")
        print(f"  • Maintainability:    {iteration.metrics.maintainability:.2f}/100")
        print(f"  • Efficiency:         {iteration.metrics.efficiency:.2f}/100")
        print(f"  • Documentation:      {iteration.metrics.documentation:.2f}/100")
        print(f"  • Naming Quality:     {iteration.metrics.naming_quality:.2f}/100")
        print(f"  • Structure:          {iteration.metrics.structure:.2f}/100")
        print(f"  • Best Practices:     {iteration.metrics.best_practices:.2f}/100")
        print(f"\nFocus Areas: {', '.join(iteration.focus_areas)}")

    # Visualize quality trajectory
    print("\n" + "=" * 70)
    print("QUALITY IMPROVEMENT VISUALIZATION")
    print("=" * 70)
    print("\nQuality Score Progress:")

    for iteration in result.iterations:
        bar_length = int(iteration.quality_score / 2)
        bar = "█" * bar_length
        print(f"Iter {iteration.iteration}: {iteration.quality_score:5.2f}/100 |{bar}|")

    # Show improvement rates
    print("\n" + "=" * 70)
    print("IMPROVEMENT RATES")
    print("=" * 70)
    print("\nIteration | Quality | Delta   | Cumulative | Rate")
    print("-" * 70)

    cumulative = 0
    for i, iteration in enumerate(result.iterations):
        if i > 0:
            cumulative += iteration.improvement_delta
            rate = cumulative / iteration.iteration
        else:
            rate = 0

        delta_str = f"{iteration.improvement_delta:+.2f}" if i > 0 else "  N/A "
        cumul_str = f"{cumulative:+.2f}" if i > 0 else "  N/A "
        rate_str = f"{rate:.2f}" if i > 0 else " N/A"

        print(f"    {iteration.iteration}     | {iteration.quality_score:5.2f}  | {delta_str}  |   {cumul_str}   | {rate_str}")

    # Track progress metrics
    progress = optimizer.track_progress(result)

    print("\n" + "=" * 70)
    print("FINAL PERFORMANCE METRICS")
    print("=" * 70)
    print(f"Total Iterations:        {progress['total_iterations']}")
    print(f"Initial Quality:         {progress['initial_quality']:.2f}/100")
    print(f"Final Quality:           {progress['final_quality']:.2f}/100")
    print(f"Total Improvement:       +{progress['total_improvement']:.2f} points")
    print(f"Improvement Percentage:  +{progress['improvement_percentage']:.1f}%")
    print(f"Avg Improvement Rate:    {progress['avg_improvement_rate']:.2f} points/iteration")
    print(f"Converged:               {progress['converged']}")
    print(f"Reason:                  {progress['convergence_reason']}")

    # Show detailed code evolution
    print("\n" + "=" * 70)
    print("CODE EVOLUTION")
    print("=" * 70)

    print("\n[INITIAL CODE]")
    print("-" * 70)
    print(result.initial_code)

    print("\n[FINAL CODE]")
    print("-" * 70)
    print(result.final_code)

    # Export results
    optimizer.export_results(result, "rsi_full_optimization_results.json")

    print("\n" + "=" * 70)
    print("DEMO COMPLETE - RSI LOOP EXECUTED SUCCESSFULLY")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()

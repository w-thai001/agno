"""Demo script for FSA-3.2 RSI Code Optimizer

This script demonstrates the recursive self-improvement loop on sample code.
"""

from agno.fsa.rsi_optimizer import RSICodeOptimizer


def main():
    """Run RSI optimization demo"""

    # Sample JavaScript code to optimize
    sample_code = """function calc(a,b){return a+b}"""

    print("\n" + "=" * 70)
    print("FSA-3.2: RSI CODE OPTIMIZER DEMO")
    print("=" * 70)
    print("\nSample Code:")
    print(sample_code)
    print()

    # Initialize optimizer
    optimizer = RSICodeOptimizer(
        convergence_threshold=2.0,  # Stop if improvement < 2 points
        plateau_patience=2,          # Wait 2 iterations for plateau
        max_iterations=5,            # Maximum 5 iterations as requested
        target_quality=90.0,         # Target quality score
    )

    # Execute RSI loop
    result = optimizer.improve_code(
        code=sample_code,
        iterations=5,
        language="javascript",
        verbose=True,
    )

    # Display quality improvement trajectory
    print("\n" + "=" * 70)
    print("QUALITY IMPROVEMENT TRAJECTORY")
    print("=" * 70)
    print("\nIteration | Quality Score | Delta  | Focus Areas")
    print("-" * 70)

    for i, iteration in enumerate(result.iterations):
        delta_str = f"{iteration.improvement_delta:+.2f}" if i > 0 else "  N/A "
        focus_str = ", ".join(iteration.focus_areas)
        print(f"    {iteration.iteration}     |     {iteration.quality_score:5.2f}     | {delta_str} | {focus_str}")

    # Track progress metrics
    progress = optimizer.track_progress(result)

    print("\n" + "=" * 70)
    print("PERFORMANCE METRICS")
    print("=" * 70)
    print(f"Total Iterations:        {progress['total_iterations']}")
    print(f"Initial Quality:         {progress['initial_quality']:.2f}/100")
    print(f"Final Quality:           {progress['final_quality']:.2f}/100")
    print(f"Total Improvement:       +{progress['total_improvement']:.2f} points")
    print(f"Improvement Percentage:  +{progress['improvement_percentage']:.1f}%")
    print(f"Avg Improvement Rate:    {progress['avg_improvement_rate']:.2f} points/iteration")
    print(f"Converged:               {progress['converged']}")
    print(f"Reason:                  {progress['convergence_reason']}")

    # Show code comparison
    print("\n" + "=" * 70)
    print("CODE COMPARISON")
    print("=" * 70)
    print("\nBEFORE:")
    print("-" * 70)
    print(result.initial_code)
    print("\nAFTER:")
    print("-" * 70)
    print(result.final_code)

    # Export results
    optimizer.export_results(result, "rsi_optimization_results.json")

    print("\n" + "=" * 70)
    print("DEMO COMPLETE")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()

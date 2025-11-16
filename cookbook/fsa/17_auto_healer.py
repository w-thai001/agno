"""🔧 FSA Auto-Healer Example

This example demonstrates automatic error recovery and self-healing capabilities
for resilient FSA execution.

Run `pip install agno` to install dependencies.
"""

from agno.fsa.auto_healer import (
    FSAAutoHealer,
    FailureType,
    RecoveryStrategy,
    HealthStatus
)
from agno.fsa.base import FSA, FSAExecutionResult
from agno.fsa.code_builder import MultiStepCodeBuilder
import random


class FlakyFSA(FSA):
    """Simulated flaky FSA for testing auto-healer"""

    def __init__(self, name: str, failure_rate: float = 0.5, failure_type: str = "transient"):
        super().__init__(name=name)
        self.failure_rate = failure_rate
        self.failure_type = failure_type
        self.attempt_count = 0
        self.heal_count = 0

    def run(self, initial_context=None):
        """Simulate flaky execution"""
        self.attempt_count += 1

        # Simulate recovery after healing attempts
        if self.heal_count > 0 and self.heal_count >= 2:
            # Healed - return success
            return FSAExecutionResult(
                success=True,
                final_state="success",
                context={"result": f"Success after {self.heal_count} healing attempts"},
                duration=0.1,
                transitions_executed=1
            )

        # Randomly fail based on failure rate
        if random.random() < self.failure_rate:
            error_messages = {
                "transient": "Temporary network timeout",
                "intermittent": "Connection refused (occasional)",
                "persistent": "Invalid configuration detected",
                "critical": "Critical system error - database unavailable"
            }

            error = error_messages.get(self.failure_type, "Unknown error")

            return FSAExecutionResult(
                success=False,
                final_state="failed",
                context={"error": error},
                duration=0.1,
                transitions_executed=0
            )

        return FSAExecutionResult(
            success=True,
            final_state="success",
            context={"result": f"Success on attempt {self.attempt_count}"},
            duration=0.1,
            transitions_executed=1
        )

    def reset(self):
        """Reset and track healing"""
        super().reset()
        self.heal_count += 1


def main():
    """Demonstrate FSA Auto-Healer"""

    print("\n" + "=" * 70)
    print("FSA AUTO-HEALER - AUTOMATIC ERROR RECOVERY")
    print("=" * 70)

    # =========================================================================
    # Example 1: Basic Auto-Healing
    # =========================================================================
    print("\n" + "─" * 70)
    print("EXAMPLE 1: BASIC AUTO-HEALING")
    print("─" * 70)

    print("\n🔧 Creating auto-healer...")

    healer = FSAAutoHealer(
        name="MainHealer",
        max_recovery_attempts=3,
        enable_learning=True,
        failure_threshold=3,
        debug_mode=True
    )

    print(f"✓ Auto-healer created")
    print(f"  - Max recovery attempts: {healer.max_recovery_attempts}")
    print(f"  - Learning: {healer.enable_learning}")
    print(f"  - Initial health: {healer.health_status.value}")

    # Create flaky FSA (50% failure rate, transient failures)
    flaky_fsa = FlakyFSA(
        name="FlakyService",
        failure_rate=0.5,
        failure_type="transient"
    )

    print(f"\n🎲 Testing with flaky FSA (50% failure rate, transient failures)")

    print(f"\n🚀 Executing with auto-healing protection...")

    result = healer.heal_execution(
        fsa=flaky_fsa,
        context={"request": "test"}
    )

    print(f"\n📊 Execution Result:")
    print(f"  Success: {'✅' if result.success else '❌'} {result.success}")
    print(f"  Final State: {result.final_state}")

    # Get healing report
    report = healer.get_healing_report()

    print(f"\n📋 Healing Report:")
    print(f"  FSA: {report.fsa_name}")
    print(f"  Failures Detected: {report.failure_count}")
    print(f"  Recovery Attempts: {len(report.recovery_attempts)}")
    print(f"  Successful Recoveries: {report.successful_recoveries} ✅")
    print(f"  Failed Recoveries: {report.failed_recoveries} ❌")
    print(f"  Health Status: {report.health_status.value.upper()}")

    if report.recovery_attempts:
        print(f"\n🔄 Recovery Attempts:")
        for i, attempt in enumerate(report.recovery_attempts, 1):
            status = "✅" if attempt.success else "❌"
            print(f"  {i}. {status} {attempt.strategy.value}")
            print(f"     Duration: {attempt.duration:.3f}s")
            print(f"     Time: {attempt.timestamp}")

    # =========================================================================
    # Example 2: Different Failure Types
    # =========================================================================
    print("\n\n" + "=" * 70)
    print("EXAMPLE 2: HANDLING DIFFERENT FAILURE TYPES")
    print("=" * 70)

    failure_types = [
        ("transient", "Temporary network timeout"),
        ("intermittent", "Occasional connection issues"),
        ("persistent", "Configuration error"),
    ]

    for failure_type, description in failure_types:
        print(f"\n{'─' * 70}")
        print(f"Testing: {failure_type.upper()} - {description}")
        print(f"{'─' * 70}")

        # Create new healer for this test
        type_healer = FSAAutoHealer(
            name=f"{failure_type.capitalize()}Healer",
            max_recovery_attempts=3,
            enable_learning=True,
            debug_mode=False  # Less verbose
        )

        # Create flaky FSA with specific failure type
        type_fsa = FlakyFSA(
            name=f"{failure_type.capitalize()}Service",
            failure_rate=0.7,
            failure_type=failure_type
        )

        print(f"\n🔧 Executing with {failure_type} failures...")

        result = type_healer.heal_execution(type_fsa, context={"test": True})

        type_report = type_healer.get_healing_report()

        status_icon = "✅" if result.success else "❌"
        print(f"\n{status_icon} Result: {'Success' if result.success else 'Failed'}")
        print(f"  Failures: {type_report.failure_count}")
        print(f"  Recoveries: {type_report.successful_recoveries}/{len(type_report.recovery_attempts)}")
        print(f"  Health: {type_report.health_status.value}")

        # Show recovery strategies used
        if type_report.recovery_attempts:
            strategies = [a.strategy.value for a in type_report.recovery_attempts]
            print(f"  Strategies: {', '.join(strategies)}")

    # =========================================================================
    # Example 3: Learning from Recoveries
    # =========================================================================
    print("\n\n" + "=" * 70)
    print("EXAMPLE 3: LEARNING FROM SUCCESSFUL RECOVERIES")
    print("=" * 70)

    learning_healer = FSAAutoHealer(
        name="LearningHealer",
        max_recovery_attempts=3,
        enable_learning=True,
        debug_mode=True
    )

    print("\n🧠 Auto-healer with learning enabled")
    print("   Learning associations between errors and successful strategies...")

    # Simulate multiple failures and recoveries
    for i in range(3):
        print(f"\n  Run {i + 1}:")

        test_fsa = FlakyFSA(
            name=f"TestService{i}",
            failure_rate=0.6,
            failure_type="transient"
        )

        result = learning_healer.heal_execution(test_fsa, context={})

        # Show learned strategies
        learned = learning_healer.get_learned_strategies()
        if learned:
            print(f"  📚 Learned Strategies: {len(learned)}")
            for pattern, strategy in learned.items():
                print(f"     '{pattern}' → {strategy.value}")

    # Final learning report
    final_report = learning_healer.get_healing_report()

    print(f"\n📊 Learning Summary:")
    print(f"  Total Failures: {final_report.failure_count}")
    print(f"  Success Rate: {final_report.successful_recoveries / final_report.failure_count * 100:.1f}%")
    print(f"\n🧠 Learned Patterns ({len(final_report.learned_patterns)}):")
    for pattern in final_report.learned_patterns:
        print(f"  - {pattern}")

    # =========================================================================
    # Example 4: Failure Patterns Analysis
    # =========================================================================
    print("\n\n" + "=" * 70)
    print("EXAMPLE 4: FAILURE PATTERN ANALYSIS")
    print("=" * 70)

    pattern_healer = FSAAutoHealer(
        name="PatternHealer",
        max_recovery_attempts=3,
        failure_threshold=3,
        debug_mode=False
    )

    print("\n📈 Tracking failure patterns...")

    # Simulate various failures
    failure_scenarios = [
        ("transient", 5),
        ("intermittent", 3),
        ("transient", 2)
    ]

    for failure_type, count in failure_scenarios:
        for _ in range(count):
            test_fsa = FlakyFSA(
                name="Service",
                failure_rate=0.8,
                failure_type=failure_type
            )
            pattern_healer.heal_execution(test_fsa, context={})

    # Get failure patterns
    patterns = pattern_healer.get_failure_patterns()

    print(f"\n📊 Failure Patterns Detected:")
    sorted_patterns = sorted(patterns.items(), key=lambda x: x[1], reverse=True)

    for pattern, frequency in sorted_patterns:
        print(f"  {pattern}: {frequency} occurrences")

    # =========================================================================
    # Example 5: Health Monitoring
    # =========================================================================
    print("\n\n" + "=" * 70)
    print("EXAMPLE 5: HEALTH MONITORING")
    print("=" * 70)

    health_healer = FSAAutoHealer(
        name="HealthHealer",
        max_recovery_attempts=3,
        enable_learning=True,
        debug_mode=False
    )

    print("\n💚 Monitoring system health over multiple executions...")

    # Simulate improving reliability over time
    reliability_progression = [0.3, 0.5, 0.7, 0.9]  # Increasing success rate

    for i, success_rate in enumerate(reliability_progression, 1):
        print(f"\n  Phase {i} (Target success rate: {success_rate * 100:.0f}%):")

        # Run multiple times
        for _ in range(5):
            improving_fsa = FlakyFSA(
                name="ImprovingService",
                failure_rate=1 - success_rate,
                failure_type="transient"
            )
            health_healer.heal_execution(improving_fsa, context={})

        # Check health status
        report = health_healer.get_healing_report()
        health_icon = {
            "healthy": "💚",
            "degraded": "💛",
            "unhealthy": "🧡",
            "critical": "❤️"
        }.get(report.health_status.value, "⚪")

        print(f"  {health_icon} Health: {report.health_status.value.upper()}")
        print(f"  Success Rate: {report.successful_recoveries / report.failure_count * 100:.1f}%")
        print(f"  Total Recoveries: {report.successful_recoveries}/{report.failure_count}")

    # =========================================================================
    # Example 6: Production Use Case
    # =========================================================================
    print("\n\n" + "=" * 70)
    print("EXAMPLE 6: PRODUCTION USE CASE")
    print("=" * 70)

    print("\n🏭 Simulating production scenario:")
    print("   - Microservice with occasional failures")
    print("   - Auto-healer provides resilience")
    print("   - Learns optimal recovery strategies")

    prod_healer = FSAAutoHealer(
        name="ProductionHealer",
        max_recovery_attempts=5,
        enable_learning=True,
        failure_threshold=3,
        debug_mode=False
    )

    # Use real FSA
    code_builder = MultiStepCodeBuilder(
        name="APIService",
        programming_language="python"
    )

    print("\n🚀 Executing production workload...")

    for i in range(3):
        print(f"\n  Request {i + 1}:")

        result = prod_healer.heal_execution(
            code_builder,
            context={
                "task": f"Process request {i + 1}",
                "requirements": ["validate", "process", "respond"]
            }
        )

        status = "✅ Success" if result.success else "❌ Failed"
        print(f"  {status}")

    # Final production report
    prod_report = prod_healer.get_healing_report()

    print(f"\n📊 Production Health Report:")
    print(f"  Service: {prod_report.fsa_name}")
    print(f"  Total Failures: {prod_report.failure_count}")
    print(f"  Auto-Recoveries: {prod_report.successful_recoveries}")
    print(f"  Recovery Rate: {prod_report.successful_recoveries / max(prod_report.failure_count, 1) * 100:.1f}%")
    print(f"  Health Status: {prod_report.health_status.value.upper()}")

    health_emoji = {
        HealthStatus.HEALTHY: "💚 Production Ready",
        HealthStatus.DEGRADED: "💛 Needs Attention",
        HealthStatus.UNHEALTHY: "🧡 Requires Investigation",
        HealthStatus.CRITICAL: "❤️ Immediate Action Required"
    }.get(prod_report.health_status, "⚪ Unknown")

    print(f"\n  Status: {health_emoji}")

    # =========================================================================
    # Best Practices
    # =========================================================================
    print("\n\n" + "=" * 70)
    print("AUTO-HEALING BEST PRACTICES")
    print("=" * 70)

    practices = [
        "1. Enable learning to optimize recovery strategies over time",
        "2. Set appropriate max_recovery_attempts based on SLA",
        "3. Monitor health status to detect degradation early",
        "4. Analyze failure patterns to identify systemic issues",
        "5. Use auto-healer for all external service integrations",
        "6. Combine with circuit breaker for comprehensive resilience",
        "7. Log all recovery attempts for post-mortem analysis",
        "8. Set failure thresholds based on acceptable error rates",
        "9. Review learned strategies periodically",
        "10. Test auto-healing with various failure scenarios"
    ]

    for practice in practices:
        print(f"   {practice}")

    print("\n" + "=" * 70)
    print("✅ Auto-healer demonstration complete!")
    print("=" * 70)

    print("\n💡 Key Takeaway: Auto-healer provides automatic recovery,")
    print("   learns from successes, and maintains system reliability!")


if __name__ == "__main__":
    main()

"""⚡ FSA Circuit Breaker Example

This example demonstrates the circuit breaker pattern for resilient FSA execution
with automatic failure detection and recovery.

Run `pip install agno` to install dependencies.
"""

from agno.fsa.circuit_breaker import FSACircuitBreaker, CircuitState
from agno.fsa.code_builder import MultiStepCodeBuilder
from agno.fsa.base import FSA
import time
import random


class UnreliableFSA(FSA):
    """Simulated unreliable FSA for testing circuit breaker"""

    def __init__(self, name: str, failure_rate: float = 0.7):
        super().__init__(name=name)
        self.failure_rate = failure_rate
        self.call_count = 0

    def run(self, initial_context=None):
        """Simulate unreliable execution"""
        self.call_count += 1

        # Simulate work
        time.sleep(0.1)

        # Randomly fail based on failure rate
        if random.random() < self.failure_rate:
            from agno.fsa.base import FSAExecutionResult
            return FSAExecutionResult(
                success=False,
                final_state="failed",
                context={"error": "Simulated failure"},
                duration=0.1,
                transitions_executed=0
            )

        from agno.fsa.base import FSAExecutionResult
        return FSAExecutionResult(
            success=True,
            final_state="success",
            context={"result": f"Success on call {self.call_count}"},
            duration=0.1,
            transitions_executed=1
        )


def fallback_handler(context):
    """Fallback handler when circuit is open"""
    return {"result": "FALLBACK: Service unavailable, using cached data"}


def main():
    """Demonstrate FSA Circuit Breaker"""

    print("\n" + "=" * 70)
    print("FSA CIRCUIT BREAKER - RESILIENCE PATTERN")
    print("=" * 70)

    # =========================================================================
    # Example 1: Basic Circuit Breaker with Unreliable FSA
    # =========================================================================
    print("\n" + "─" * 70)
    print("EXAMPLE 1: BASIC CIRCUIT BREAKER")
    print("─" * 70)

    print("\n🔧 Creating circuit breaker with:")
    print("   - Failure threshold: 3 consecutive failures")
    print("   - Success threshold: 2 consecutive successes")
    print("   - Timeout: 5 seconds")

    circuit_breaker = FSACircuitBreaker(
        name="MainCircuit",
        failure_threshold=3,
        success_threshold=2,
        timeout_seconds=5.0,
        failure_rate_threshold=0.6,
        slow_call_threshold_ms=1000.0,
        debug_mode=True
    )

    print(f"\n✓ Circuit breaker created")
    print(f"   Initial state: {circuit_breaker.circuit_state.value}")

    # Create unreliable FSA (70% failure rate)
    unreliable_fsa = UnreliableFSA(
        name="UnreliableService",
        failure_rate=0.7
    )

    print(f"\n🎲 Testing with unreliable FSA (70% failure rate)")

    # =========================================================================
    # Execute requests until circuit opens
    # =========================================================================
    print("\n" + "─" * 70)
    print("PHASE 1: EXECUTING REQUESTS UNTIL CIRCUIT OPENS")
    print("─" * 70)

    for i in range(10):
        print(f"\n📍 Request {i + 1}:")

        result = circuit_breaker.execute_protected(
            fsa=unreliable_fsa,
            context={"request_id": i + 1},
            fallback=fallback_handler
        )

        metrics = circuit_breaker.get_metrics()

        status_icon = "✅" if circuit_breaker.current_state == "success" else "❌"
        circuit_icon = {
            "closed": "🟢",
            "open": "🔴",
            "half_open": "🟡"
        }.get(metrics.circuit_state.value, "⚪")

        print(f"   {status_icon} Result: {result}")
        print(f"   {circuit_icon} Circuit: {metrics.circuit_state.value.upper()}")
        print(f"   📊 Stats: {metrics.successful_requests}✓ / {metrics.failed_requests}✗ "
              f"(Rate: {metrics.failure_rate:.1%})")
        print(f"   🔄 Consecutive failures: {metrics.consecutive_failures}")

        if metrics.circuit_state == CircuitState.OPEN:
            print(f"   ⚠️  CIRCUIT OPENED! Too many failures detected")
            break

        time.sleep(0.2)

    # =========================================================================
    # Example 2: Circuit Recovery (Half-Open -> Closed)
    # =========================================================================
    print("\n\n" + "=" * 70)
    print("EXAMPLE 2: CIRCUIT RECOVERY")
    print("=" * 70)

    if circuit_breaker.circuit_state == CircuitState.OPEN:
        print(f"\n🔴 Circuit is currently OPEN")
        print(f"   Waiting {circuit_breaker.timeout_seconds} seconds for timeout...")

        # Wait for timeout
        time.sleep(circuit_breaker.timeout_seconds + 0.5)

        print(f"\n⏰ Timeout expired - circuit will transition to HALF-OPEN on next request")

        # Create more reliable FSA for recovery
        reliable_fsa = UnreliableFSA(
            name="RecoveredService",
            failure_rate=0.2  # Only 20% failure rate
        )

        print(f"\n🔧 Switched to more reliable FSA (20% failure rate)")
        print(f"\n📍 Attempting recovery requests:")

        for i in range(5):
            result = circuit_breaker.execute_protected(
                fsa=reliable_fsa,
                context={"recovery_attempt": i + 1},
                fallback=fallback_handler
            )

            metrics = circuit_breaker.get_metrics()
            status = "✅" if circuit_breaker.current_state == "success" else "❌"
            circuit_icon = {
                "closed": "🟢",
                "open": "🔴",
                "half_open": "🟡"
            }.get(metrics.circuit_state.value, "⚪")

            print(f"\n   Attempt {i + 1}: {status}")
            print(f"   {circuit_icon} Circuit: {metrics.circuit_state.value.upper()}")
            print(f"   🔄 Consecutive successes: {circuit_breaker.consecutive_successes}")

            if metrics.circuit_state == CircuitState.CLOSED:
                print(f"\n   🎉 CIRCUIT CLOSED! Service recovered")
                break

            time.sleep(0.2)

    # =========================================================================
    # Example 3: Metrics and Monitoring
    # =========================================================================
    print("\n\n" + "=" * 70)
    print("EXAMPLE 3: CIRCUIT BREAKER METRICS")
    print("=" * 70)

    metrics = circuit_breaker.get_metrics()

    print(f"\n📊 CIRCUIT BREAKER STATISTICS:")
    print(f"   Total Requests: {metrics.total_requests}")
    print(f"   Successful: {metrics.successful_requests} ({metrics.successful_requests / metrics.total_requests * 100:.1f}%)")
    print(f"   Failed: {metrics.failed_requests} ({metrics.failed_requests / metrics.total_requests * 100:.1f}%)")
    print(f"   Failure Rate: {metrics.failure_rate:.1%}")
    print(f"   Avg Response Time: {metrics.avg_response_time:.1f}ms")
    print(f"   Current State: {metrics.circuit_state.value.upper()}")
    print(f"   Consecutive Failures: {metrics.consecutive_failures}")

    # =========================================================================
    # Example 4: State Change History
    # =========================================================================
    print("\n\n" + "=" * 70)
    print("EXAMPLE 4: CIRCUIT STATE HISTORY")
    print("=" * 70)

    history = circuit_breaker.get_state_history()

    print(f"\n📜 State Changes ({len(history)} transitions):")

    for i, event in enumerate(history, 1):
        from_icon = {
            "closed": "🟢",
            "open": "🔴",
            "half_open": "🟡"
        }.get(event.from_state.value, "⚪")

        to_icon = {
            "closed": "🟢",
            "open": "🔴",
            "half_open": "🟡"
        }.get(event.to_state.value, "⚪")

        print(f"\n   {i}. {from_icon} {event.from_state.value.upper()} "
              f"→ {to_icon} {event.to_state.value.upper()}")
        print(f"      Time: {event.timestamp}")
        print(f"      Reason: {event.reason}")
        print(f"      Metrics: {event.metrics.failed_requests}✗ / {event.metrics.total_requests} requests")

    # =========================================================================
    # Example 5: Manual Circuit Control
    # =========================================================================
    print("\n\n" + "=" * 70)
    print("EXAMPLE 5: MANUAL CIRCUIT CONTROL")
    print("=" * 70)

    print("\n🔧 Manual circuit operations:")

    # Force open
    print(f"\n   Current state: {circuit_breaker.circuit_state.value}")
    circuit_breaker.force_open("Testing manual control")
    print(f"   After force_open(): {circuit_breaker.circuit_state.value}")

    # Check if call permitted
    permitted = circuit_breaker.is_call_permitted()
    print(f"   Is call permitted? {permitted}")

    # Force half-open
    circuit_breaker.force_half_open("Testing recovery")
    print(f"   After force_half_open(): {circuit_breaker.circuit_state.value}")

    # Force close
    circuit_breaker.force_close("Service fully recovered")
    print(f"   After force_close(): {circuit_breaker.circuit_state.value}")

    # =========================================================================
    # Example 6: Production Use Case
    # =========================================================================
    print("\n\n" + "=" * 70)
    print("EXAMPLE 6: PRODUCTION USE CASE")
    print("=" * 70)

    print("\n🏭 Simulating production scenario:")
    print("   - External API with intermittent failures")
    print("   - Circuit breaker protects against cascading failures")
    print("   - Fallback provides cached responses")

    # Reset circuit breaker
    circuit_breaker.reset_metrics()
    circuit_breaker.force_close("Starting fresh")

    # Create FSA that simulates external API
    api_fsa = MultiStepCodeBuilder(
        name="ExternalAPI",
        programming_language="python"
    )

    print("\n📡 Making API calls with circuit breaker protection:")

    for i in range(5):
        try:
            result = circuit_breaker.execute_protected(
                fsa=api_fsa,
                context={
                    "task": "Fetch user data",
                    "user_id": i + 1
                },
                fallback=lambda ctx: {
                    "data": "cached_user_data",
                    "source": "cache"
                }
            )

            if result:
                source = result.get("source", "api") if isinstance(result, dict) else "api"
                print(f"   Request {i + 1}: ✅ Success (source: {source})")
            else:
                print(f"   Request {i + 1}: ⚠️  Fallback used")

        except Exception as e:
            print(f"   Request {i + 1}: ❌ Error: {e}")

        time.sleep(0.1)

    # Final metrics
    final_metrics = circuit_breaker.get_metrics()
    print(f"\n📊 Final Metrics:")
    print(f"   Circuit State: {final_metrics.circuit_state.value.upper()}")
    print(f"   Success Rate: {(1 - final_metrics.failure_rate) * 100:.1f}%")
    print(f"   Avg Response Time: {final_metrics.avg_response_time:.1f}ms")

    # =========================================================================
    # Best Practices
    # =========================================================================
    print("\n\n" + "=" * 70)
    print("CIRCUIT BREAKER BEST PRACTICES")
    print("=" * 70)

    practices = [
        "1. Set appropriate failure thresholds based on your SLA",
        "2. Always provide fallback mechanisms for graceful degradation",
        "3. Monitor circuit state changes to detect system issues",
        "4. Use exponential backoff for recovery attempts",
        "5. Consider slow calls as failures to prevent resource exhaustion",
        "6. Reset metrics periodically in long-running systems",
        "7. Log circuit state changes for debugging and analysis",
        "8. Test circuit breaker behavior under various failure scenarios",
        "9. Tune timeout values based on observed recovery times",
        "10. Use circuit breakers for all external service calls"
    ]

    for practice in practices:
        print(f"   {practice}")

    print("\n" + "=" * 70)
    print("✅ Circuit Breaker demonstration complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()

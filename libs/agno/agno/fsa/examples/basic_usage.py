"""
Basic Circuit Breaker FSA Usage Example

Demonstrates basic circuit breaker functionality with simple API calls.
"""

import time
import random
from agno.fsa import CircuitBreakerFSA, CircuitBreakerConfig, CircuitOpenError


def unreliable_api_call(failure_rate=0.3):
    """Simulate an unreliable API call."""
    time.sleep(0.1)  # Simulate network latency

    if random.random() < failure_rate:
        raise ConnectionError("API call failed")

    return {"status": "success", "data": "result"}


def main():
    # Configure circuit breaker
    config = CircuitBreakerConfig(
        failure_threshold=5,
        timeout=3.0,
        failure_rate_threshold=0.5
    )

    # Create circuit breaker
    cb = CircuitBreakerFSA(config=config, name="api_service")

    print("Circuit Breaker Basic Usage Example")
    print("=" * 50)

    # Execute requests
    for i in range(20):
        try:
            result = cb.execute(unreliable_api_call, failure_rate=0.6)
            print(f"Request {i + 1}: Success - {result}")

        except CircuitOpenError as e:
            print(f"Request {i + 1}: Circuit OPEN - {e}")

        except ConnectionError as e:
            print(f"Request {i + 1}: Failed - {e}")

        time.sleep(0.2)

    # Print final metrics
    print("\n" + "=" * 50)
    print("Final Metrics:")
    metrics = cb.get_metrics()
    print(f"State: {metrics.state}")
    print(f"Total Requests: {metrics.total_requests}")
    print(f"Successful: {metrics.successful_requests}")
    print(f"Failed: {metrics.failed_requests}")
    print(f"Rejected: {metrics.rejected_requests}")
    print(f"Failure Rate: {metrics.failure_rate:.1%}")

    cb.shutdown()


if __name__ == "__main__":
    main()

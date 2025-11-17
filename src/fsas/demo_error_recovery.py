"""
Demo script for Error Recovery FSA

This script demonstrates the key features of the Error Recovery FSA.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.fsas.error_recovery_fsa import (
    ErrorRecoveryFSA,
    RecoveryStrategy,
    ErrorType
)


def demo_basic_error_handling():
    """Demonstrate basic error detection and classification."""
    print("=" * 60)
    print("Demo 1: Basic Error Detection and Classification")
    print("=" * 60)

    fsa = ErrorRecoveryFSA()

    # Test different error types
    test_errors = [
        (Exception("HTTP 500 error from API"), "API Error"),
        (TimeoutError("Request timeout exceeded"), "Timeout Error"),
        (ValueError("Invalid schema format"), "Validation Error"),
        (MemoryError("Out of memory"), "Resource Error"),
    ]

    for error, description in test_errors:
        context = fsa.detect_error(error)
        error_type = fsa.classify_failure(context)
        print(f"\n{description}:")
        print(f"  Detected: {type(error).__name__}")
        print(f"  Classified as: {error_type.value}")
        print(f"  FSA State: {fsa.state.value}")

    print(f"\nTotal errors tracked: {len(fsa.error_history)}")


def demo_retry_with_recovery():
    """Demonstrate retry logic with exponential backoff."""
    print("\n" + "=" * 60)
    print("Demo 2: Retry Logic with Exponential Backoff")
    print("=" * 60)

    strategy = RecoveryStrategy(
        max_retries=3,
        base_delay=0.1,
        exponential_base=2.0
    )
    fsa = ErrorRecoveryFSA(strategy=strategy)

    attempt_count = 0

    def flaky_operation():
        nonlocal attempt_count
        attempt_count += 1
        print(f"  Attempt {attempt_count}...")
        if attempt_count < 3:
            raise Exception(f"Temporary failure on attempt {attempt_count}")
        return "Success!"

    print("\nSimulating flaky operation that succeeds on 3rd attempt:")

    try:
        flaky_operation()
    except Exception as e:
        result = fsa.handle_error(
            e,
            recovery_action=flaky_operation,
            context={"operation": "flaky_api_call"}
        )

        print(f"\nRecovery Result:")
        print(f"  Recovered: {result['recovered']}")
        print(f"  Total Attempts: {result.get('attempts', 'N/A')}")
        print(f"  Final Result: {result.get('result', 'N/A')}")


def demo_degraded_mode():
    """Demonstrate graceful degradation with fallback."""
    print("\n" + "=" * 60)
    print("Demo 3: Graceful Degradation with Fallback")
    print("=" * 60)

    def primary_operation():
        raise Exception("Primary service unavailable")

    def fallback_operation():
        return {"cached": True, "data": "Fallback data from cache"}

    strategy = RecoveryStrategy(
        max_retries=2,
        base_delay=0.05,
        enable_degraded_mode=True,
        fallback_action=fallback_operation
    )
    fsa = ErrorRecoveryFSA(strategy=strategy)

    print("\nSimulating service failure with cache fallback:")

    error = Exception("Service unavailable")
    result = fsa.handle_error(error, recovery_action=primary_operation)

    print(f"\nRecovery Result:")
    print(f"  Recovered: {result['recovered']}")
    print(f"  Degraded Mode: {result.get('degraded_mode', False)}")
    print(f"  Fallback Data: {result.get('result', {})}")


def demo_statistics():
    """Demonstrate error statistics tracking."""
    print("\n" + "=" * 60)
    print("Demo 4: Error Statistics and Tracking")
    print("=" * 60)

    fsa = ErrorRecoveryFSA()

    # Generate various errors
    errors = [
        Exception("API connection failed"),
        TimeoutError("Request timeout"),
        Exception("HTTP 502 Bad Gateway"),
        ValueError("Invalid input format"),
        TimeoutError("Another timeout"),
    ]

    print("\nProcessing multiple errors...")
    for error in errors:
        context = fsa.detect_error(error)
        fsa.classify_failure(context)

    stats = fsa.get_error_statistics()

    print(f"\nError Statistics:")
    print(f"  Total Errors: {stats['total_errors']}")
    print(f"  Errors by Type:")
    for error_type, count in stats['by_type'].items():
        print(f"    {error_type}: {count}")
    print(f"  State Transitions: {stats['state_transitions']}")


def demo_complete_workflow():
    """Demonstrate complete error handling workflow."""
    print("\n" + "=" * 60)
    print("Demo 5: Complete Error Handling Workflow")
    print("=" * 60)

    call_count = 0

    def simulated_api_call():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise ConnectionError(f"API temporarily unavailable (attempt {call_count})")
        return {"status": "success", "data": {"user_id": 123, "name": "Test User"}}

    # Custom logging handler
    logged_incidents = []

    def custom_logger(incident):
        logged_incidents.append(incident)
        print(f"\n  Incident logged at {incident['timestamp']}")
        print(f"    Error Type: {incident['error_type']}")
        print(f"    Retries: {incident['retry_count']}")

    strategy = RecoveryStrategy(max_retries=3, base_delay=0.05)
    fsa = ErrorRecoveryFSA(strategy=strategy, log_handler=custom_logger)

    print("\nSimulating API call with automatic recovery:")

    try:
        result = simulated_api_call()
    except Exception as e:
        result = fsa.handle_error(
            e,
            recovery_action=simulated_api_call,
            context={"endpoint": "/api/users/123", "method": "GET"}
        )

        print(f"\nFinal Result:")
        print(f"  Success: {result['recovered']}")
        print(f"  Data: {result.get('result', {})}")
        print(f"  Total API Calls: {call_count}")
        print(f"  Incidents Logged: {len(logged_incidents)}")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("ERROR RECOVERY FSA - DEMONSTRATION")
    print("=" * 60)

    demo_basic_error_handling()
    demo_retry_with_recovery()
    demo_degraded_mode()
    demo_statistics()
    demo_complete_workflow()

    print("\n" + "=" * 60)
    print("All demonstrations completed successfully!")
    print("=" * 60 + "\n")

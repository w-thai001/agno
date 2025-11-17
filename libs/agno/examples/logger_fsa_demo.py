"""
Logger FSA Demo Script

This script demonstrates the capabilities of the Logger FSA including:
- Multiple log levels
- Context injection and management
- Multiple output handlers (console and file)
- Structured logging with JSON format
- Performance metrics tracking
- Custom filtering

Run this script to see the Logger FSA in action!
"""

import sys
import tempfile
from pathlib import Path

# Add the library to path for demo purposes
sys.path.insert(0, str(Path(__file__).parent.parent))

from agno.utils.logger_fsa import LoggerFSA, LogLevel


def demo_basic_logging():
    """Demonstrate basic logging at different levels."""
    print("\n" + "=" * 80)
    print("DEMO 1: Basic Logging with Multiple Levels")
    print("=" * 80 + "\n")

    logger = LoggerFSA(name="demo_app", level=LogLevel.DEBUG)

    logger.debug("This is a debug message - useful for development")
    logger.info("This is an info message - general information")
    logger.warning("This is a warning message - something to pay attention to")
    logger.error("This is an error message - something went wrong")
    logger.critical("This is a critical message - system is in danger!")


def demo_context_injection():
    """Demonstrate context injection and tracking."""
    print("\n" + "=" * 80)
    print("DEMO 2: Context Injection and Tracking")
    print("=" * 80 + "\n")

    logger = LoggerFSA(name="web_app", level=LogLevel.INFO)

    # Add persistent context
    logger.add_context("request_id", "req-123-456-789")
    logger.add_context("user_id", "user-alice")
    logger.add_context("session_id", "session-xyz")

    logger.info("User logged in")
    logger.info("User viewed dashboard")
    logger.info("User updated profile", action="update_profile", field="email")

    # Clear context and start fresh
    logger.clear_context()
    logger.info("New request without context")


def demo_context_stack():
    """Demonstrate context stack for nested operations."""
    print("\n" + "=" * 80)
    print("DEMO 3: Context Stack for Nested Operations")
    print("=" * 80 + "\n")

    logger = LoggerFSA(name="task_processor", level=LogLevel.INFO)

    logger.add_context("job_id", "job-001")
    logger.info("Starting batch job")

    # Push context for nested operation
    logger.push_context()
    logger.add_context("task_id", "task-001")
    logger.info("Processing task 1")
    logger.info("Task 1 completed", status="success", duration_ms=150)
    logger.pop_context()

    # Push context for another nested operation
    logger.push_context()
    logger.add_context("task_id", "task-002")
    logger.info("Processing task 2")
    logger.warning("Task 2 encountered warning", warning_type="rate_limit")
    logger.pop_context()

    logger.info("Batch job completed")


def demo_json_formatting():
    """Demonstrate JSON structured logging."""
    print("\n" + "=" * 80)
    print("DEMO 4: JSON Structured Logging")
    print("=" * 80 + "\n")

    logger = LoggerFSA(name="api_service", level=LogLevel.INFO, output_format="json")

    logger.add_context("environment", "production")
    logger.add_context("region", "us-west-2")

    logger.info("API request received", method="GET", endpoint="/api/users", status_code=200, duration_ms=45)

    logger.warning("Rate limit approaching", current=95, limit=100, client_id="client-123")

    logger.error(
        "Database query failed",
        query="SELECT * FROM users",
        error_code="TIMEOUT",
        retry_count=3,
        will_retry=False,
    )


def demo_multiple_handlers():
    """Demonstrate logging to multiple handlers simultaneously."""
    print("\n" + "=" * 80)
    print("DEMO 5: Multiple Output Handlers (Console + File)")
    print("=" * 80 + "\n")

    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "application.log"
        json_log_file = Path(tmpdir) / "application.json"

        logger = LoggerFSA(name="multi_handler_app", level=LogLevel.INFO, enable_auto_console=False)

        # Add console handler with text format
        logger.configure_handler("console", {"formatter": "text"})

        # Add file handler with text format
        logger.configure_handler("file", {"filepath": str(log_file), "formatter": "text"})

        # Add another file handler with JSON format
        logger.configure_handler("file", {"filepath": str(json_log_file), "formatter": "json"})

        logger.add_context("instance_id", "i-1234567890")

        logger.info("Application started")
        logger.info("Processing data", records_count=1500)
        logger.warning("Memory usage high", usage_percent=85)
        logger.info("Application shutting down gracefully")

        logger.close()

        print(f"\nLogs written to:")
        print(f"  - Console (above)")
        print(f"  - Text file: {log_file}")
        print(f"  - JSON file: {json_log_file}")

        print(f"\nText log file contents:")
        print("-" * 80)
        print(log_file.read_text())

        print(f"\nJSON log file contents:")
        print("-" * 80)
        print(json_log_file.read_text())


def demo_filtering():
    """Demonstrate custom log filtering."""
    print("\n" + "=" * 80)
    print("DEMO 6: Custom Log Filtering")
    print("=" * 80 + "\n")

    logger = LoggerFSA(name="filtered_app", level=LogLevel.DEBUG)

    # Add filter to exclude debug messages containing "verbose"
    logger.add_filter(lambda entry: not (entry.level == "DEBUG" and "verbose" in entry.message.lower()))

    # Add filter to exclude messages with certain context
    logger.add_filter(lambda entry: entry.context.get("internal", False) is not True)

    logger.debug("This debug message will appear")
    logger.debug("This verbose debug message will be filtered out")
    logger.info("This info message will appear")
    logger.info("This internal message will be filtered", internal=True)
    logger.warning("This warning will appear")


def demo_performance_metrics():
    """Demonstrate performance metrics and statistics."""
    print("\n" + "=" * 80)
    print("DEMO 7: Performance Metrics and Statistics")
    print("=" * 80 + "\n")

    logger = LoggerFSA(name="metrics_app", level=LogLevel.DEBUG)

    # Generate various logs
    logger.add_context("app_version", "1.2.3")

    for i in range(5):
        logger.debug(f"Debug message {i}")

    for i in range(10):
        logger.info(f"Info message {i}", iteration=i)

    for i in range(3):
        logger.warning(f"Warning message {i}")

    for i in range(2):
        logger.error(f"Error message {i}")

    logger.critical("Critical situation detected")

    # Get and display statistics
    stats = logger.get_stats()

    print("\nLogging Statistics:")
    print("-" * 80)
    print(f"Total logs: {stats['total_logs']}")
    print(f"\nLogs by level:")
    for level, count in sorted(stats['logs_by_level'].items()):
        print(f"  {level}: {count}")
    print(f"\nPerformance metrics:")
    print(f"  Total time: {stats['total_time_ms']:.2f}ms")
    print(f"  Average time per log: {stats['avg_time_ms']:.4f}ms")
    print(f"\nContext keys used: {', '.join(stats['context_keys'])}")
    print(f"Errors encountered: {stats['errors']}")


def demo_remote_handler():
    """Demonstrate remote handler with custom callback."""
    print("\n" + "=" * 80)
    print("DEMO 8: Remote Handler with Custom Callback")
    print("=" * 80 + "\n")

    # Collect logs in a list (simulating sending to remote service)
    collected_logs = []

    def send_to_remote(entry):
        """Simulate sending log to remote service."""
        collected_logs.append(
            {
                "timestamp": entry.timestamp,
                "level": entry.level,
                "message": entry.message,
                "context": entry.context,
            }
        )
        print(f"  -> Sent to remote: [{entry.level}] {entry.message}")

    logger = LoggerFSA(name="remote_app", level=LogLevel.INFO, enable_auto_console=False)
    logger.configure_handler("remote", {"endpoint": "https://logs.example.com/api/v1/logs", "callback": send_to_remote})

    logger.add_context("datacenter", "dc-east-1")

    logger.info("Service started")
    logger.warning("High latency detected", latency_ms=250)
    logger.error("Connection lost", retry_attempt=1)

    print(f"\nTotal logs collected: {len(collected_logs)}")


def demo_real_world_scenario():
    """Demonstrate a real-world API request processing scenario."""
    print("\n" + "=" * 80)
    print("DEMO 9: Real-World API Request Processing Scenario")
    print("=" * 80 + "\n")

    import time
    import uuid

    logger = LoggerFSA(name="api_server", level=LogLevel.DEBUG, output_format="json")

    # Simulate API request
    request_id = str(uuid.uuid4())
    user_id = "user-12345"

    logger.add_context("request_id", request_id)
    logger.info("Incoming request", method="POST", endpoint="/api/orders", client_ip="192.168.1.100")

    # Authentication
    logger.add_context("user_id", user_id)
    logger.debug("Authenticating user")
    time.sleep(0.01)  # Simulate auth
    logger.info("User authenticated", auth_method="oauth2")

    # Authorization
    logger.debug("Checking user permissions")
    logger.info("User authorized", role="customer", permissions=["read", "write"])

    # Validate request
    logger.debug("Validating request payload")
    logger.info("Request validated", items_count=3, total_amount=99.99)

    # Database operation
    logger.push_context()
    logger.add_context("operation", "database_write")
    logger.debug("Connecting to database")
    logger.info("Database query started", table="orders")
    time.sleep(0.02)  # Simulate DB operation
    logger.info("Database query completed", rows_affected=1, query_time_ms=20)
    logger.pop_context()

    # External API call
    logger.push_context()
    logger.add_context("operation", "payment_processing")
    logger.debug("Calling payment gateway")
    logger.info("Payment processed", payment_method="credit_card", amount=99.99, currency="USD")
    logger.pop_context()

    # Success response
    logger.info(
        "Request completed successfully",
        status_code=201,
        response_time_ms=45,
        resource_created="/api/orders/order-789",
    )

    # Show stats
    print("\n" + "-" * 80)
    stats = logger.get_stats()
    print(f"Request processed with {stats['total_logs']} log entries in {stats['total_time_ms']:.2f}ms")


def main():
    """Run all demos."""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 24 + "Logger FSA Demo Suite" + " " * 33 + "║")
    print("║" + " " * 20 + "Production-Ready Logging System" + " " * 27 + "║")
    print("╚" + "=" * 78 + "╝")

    demos = [
        demo_basic_logging,
        demo_context_injection,
        demo_context_stack,
        demo_json_formatting,
        demo_multiple_handlers,
        demo_filtering,
        demo_performance_metrics,
        demo_remote_handler,
        demo_real_world_scenario,
    ]

    for demo_func in demos:
        try:
            demo_func()
        except Exception as e:
            print(f"\n❌ Error in {demo_func.__name__}: {e}")
            import traceback

            traceback.print_exc()

    print("\n" + "=" * 80)
    print("Demo completed! Check out the code to see how each feature works.")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()

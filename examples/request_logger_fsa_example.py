"""
Example: Request Logger FSA Usage

Demonstrates HTTP request/response logging with state transitions.
"""

from agno.fsa import RequestLoggerFSA, RequestState
import time


def main():
    # Initialize the FSA
    logger = RequestLoggerFSA()

    print("=== Request Logger FSA Demo ===\n")

    # Example 1: Successful GET request
    print("1. Creating GET request...")
    log1 = logger.create_request(
        request_id="req-001",
        method="GET",
        url="https://api.example.com/users",
        headers={"Authorization": "Bearer token123"}
    )
    print(f"   State: {log1.state} | Sent at: {log1.request_sent_at}")

    # Simulate network delay
    time.sleep(0.1)

    print("2. Logging response...")
    log1 = logger.log_response(
        request_id="req-001",
        status_code=200,
        headers={"Content-Type": "application/json"},
        body={"users": [{"id": 1, "name": "Alice"}]}
    )
    print(f"   State: {log1.state} | Status: {log1.status_code} | Duration: {log1.duration_ms:.2f}ms")

    print("3. Completing request...")
    log1 = logger.complete_request("req-001")
    print(f"   State: {log1.state} | Completed\n")

    # Example 2: POST request with error
    print("4. Creating POST request...")
    log2 = logger.create_request(
        request_id="req-002",
        method="POST",
        url="https://api.example.com/users",
        headers={"Content-Type": "application/json"},
        body={"name": "Bob"}
    )
    print(f"   State: {log2.state}")

    print("5. Logging error...")
    log2 = logger.log_error("req-002", "Connection timeout")
    print(f"   State: {log2.state} | Error: {log2.error}\n")

    # Summary
    print("=== All Logs Summary ===")
    for log in logger.get_all_logs():
        print(f"Request {log.request_id}:")
        print(f"  {log.method} {log.url}")
        print(f"  State: {log.state}")
        print(f"  Status: {log.status_code}")
        print(f"  Duration: {log.duration_ms}ms" if log.duration_ms else "  Duration: N/A")
        print(f"  Error: {log.error}" if log.error else "")
        print()


if __name__ == "__main__":
    main()

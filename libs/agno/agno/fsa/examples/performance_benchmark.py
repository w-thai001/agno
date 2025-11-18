"""
Performance Benchmark for Circuit Breaker FSA

Measures throughput, latency, and overhead of circuit breaker operations.
"""

import time
import threading
import statistics
from datetime import datetime
from agno.fsa import CircuitBreakerFSA, CircuitBreakerConfig


def benchmark_throughput(duration_seconds=5):
    """Benchmark request throughput."""
    print("\n" + "=" * 70)
    print("Throughput Benchmark")
    print("=" * 70)

    config = CircuitBreakerConfig(failure_threshold=1000)
    cb = CircuitBreakerFSA(config=config, name="throughput_test")

    request_count = [0]
    stop_flag = [False]

    def simple_func():
        return "success"

    def worker():
        while not stop_flag[0]:
            try:
                cb.execute(simple_func)
                request_count[0] += 1
            except Exception:
                pass

    # Start workers
    num_workers = 10
    threads = [threading.Thread(target=worker) for _ in range(num_workers)]

    start_time = time.time()
    for t in threads:
        t.start()

    # Run for duration
    time.sleep(duration_seconds)
    stop_flag[0] = True

    for t in threads:
        t.join()

    elapsed = time.time() - start_time
    throughput = request_count[0] / elapsed

    print(f"Duration: {elapsed:.2f}s")
    print(f"Total Requests: {request_count[0]:,}")
    print(f"Throughput: {throughput:,.0f} requests/second")
    print(f"Workers: {num_workers}")

    cb.shutdown()
    return throughput


def benchmark_latency(num_requests=1000):
    """Benchmark request latency overhead."""
    print("\n" + "=" * 70)
    print("Latency Benchmark")
    print("=" * 70)

    config = CircuitBreakerConfig()
    cb = CircuitBreakerFSA(config=config, name="latency_test")

    latencies = []

    def simple_func():
        return "success"

    # Warm up
    for _ in range(100):
        cb.execute(simple_func)

    # Measure latency
    for _ in range(num_requests):
        start = time.time()
        cb.execute(simple_func)
        latency = (time.time() - start) * 1000  # Convert to ms
        latencies.append(latency)

    # Calculate statistics
    mean_latency = statistics.mean(latencies)
    median_latency = statistics.median(latencies)
    p95_latency = statistics.quantiles(latencies, n=20)[18]  # 95th percentile
    p99_latency = statistics.quantiles(latencies, n=100)[98]  # 99th percentile
    min_latency = min(latencies)
    max_latency = max(latencies)

    print(f"Requests: {num_requests:,}")
    print(f"Mean Latency: {mean_latency:.3f}ms")
    print(f"Median Latency: {median_latency:.3f}ms")
    print(f"P95 Latency: {p95_latency:.3f}ms")
    print(f"P99 Latency: {p99_latency:.3f}ms")
    print(f"Min Latency: {min_latency:.3f}ms")
    print(f"Max Latency: {max_latency:.3f}ms")

    cb.shutdown()
    return mean_latency


def benchmark_state_transitions():
    """Benchmark state transition performance."""
    print("\n" + "=" * 70)
    print("State Transition Benchmark")
    print("=" * 70)

    config = CircuitBreakerConfig(
        failure_threshold=3,
        timeout=0.1,
        half_open_max_calls=2
    )
    cb = CircuitBreakerFSA(config=config, name="state_test")

    def failing_func():
        raise ValueError("test error")

    def succeeding_func():
        return "success"

    start_time = time.time()

    # Trigger state transitions
    num_cycles = 100
    for cycle in range(num_cycles):
        # CLOSED -> OPEN
        for _ in range(3):
            try:
                cb.execute(failing_func)
            except ValueError:
                pass

        # Wait for OPEN -> HALF_OPEN
        time.sleep(0.11)

        # HALF_OPEN -> CLOSED
        from agno.fsa.circuit_breaker import CircuitState
        cb._transition_to(CircuitState.HALF_OPEN, "test")
        for _ in range(2):
            cb.execute(succeeding_func)

    elapsed = time.time() - start_time
    transitions = cb.get_metrics().state_transitions

    print(f"Cycles: {num_cycles}")
    print(f"Total Transitions: {transitions}")
    print(f"Duration: {elapsed:.2f}s")
    print(f"Transitions per Second: {transitions / elapsed:.1f}")
    print(f"Average Transition Time: {(elapsed / transitions) * 1000:.3f}ms")

    cb.shutdown()


def benchmark_memory_usage():
    """Benchmark memory usage with large request history."""
    print("\n" + "=" * 70)
    print("Memory Usage Benchmark")
    print("=" * 70)

    import sys

    config = CircuitBreakerConfig(rolling_window_size=10000)
    cb = CircuitBreakerFSA(config=config, name="memory_test")

    def simple_func():
        return "success"

    # Measure initial size
    initial_size = sys.getsizeof(cb._request_history)

    # Fill request history
    num_requests = 10000
    for _ in range(num_requests):
        cb.execute(simple_func)

    # Measure final size
    final_size = sys.getsizeof(cb._request_history)
    avg_per_request = (final_size - initial_size) / num_requests

    print(f"Requests: {num_requests:,}")
    print(f"Initial Memory: {initial_size:,} bytes")
    print(f"Final Memory: {final_size:,} bytes")
    print(f"Average per Request: {avg_per_request:.1f} bytes")
    print(f"Total Circuit Breaker Size: ~{final_size / 1024:.1f} KB")

    cb.shutdown()


def main():
    """Run all benchmarks."""
    print("=" * 70)
    print("Circuit Breaker FSA Performance Benchmarks")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # Run benchmarks
    throughput = benchmark_throughput(duration_seconds=5)
    latency = benchmark_latency(num_requests=1000)
    benchmark_state_transitions()
    benchmark_memory_usage()

    # Summary
    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)
    print(f"Peak Throughput: {throughput:,.0f} requests/second")
    print(f"Average Latency: {latency:.3f}ms")
    print(f"Overhead: <{latency:.2f}ms per request")
    print("=" * 70)


if __name__ == "__main__":
    main()

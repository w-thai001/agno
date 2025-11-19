"""
FSA Framework Performance Benchmark

Benchmarks:
1. Registry lookup performance
2. Pipeline execution overhead
3. Health check performance
4. Parallel vs sequential execution
5. Caching effectiveness
6. Memory usage
"""

import gc
import logging
import statistics
import time
import tracemalloc
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List

from agno.fsa import (
    FSARegistry,
    FSAPipeline,
    FSAPipelineManager,
)

# Suppress logs for cleaner benchmark output
logging.basicConfig(level=logging.WARNING)


# ============================================================================
# Benchmark FSA Modules
# ============================================================================

class BenchmarkModule:
    """Simple module for benchmarking"""

    def __init__(self, **kwargs):
        self.work_time_ms = kwargs.get('work_time_ms', 10)

    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute with configurable work time"""
        time.sleep(self.work_time_ms / 1000.0)
        return {"result": "success", "timestamp": time.time()}

    def health_check(self) -> bool:
        """Health check"""
        return True


# ============================================================================
# Benchmark Functions
# ============================================================================

def benchmark_registry_lookup(iterations: int = 10000) -> Dict[str, float]:
    """Benchmark registry module lookup performance"""
    print("\n[Benchmark 1] Registry Lookup Performance")
    print("-" * 60)

    registry = FSARegistry()
    registry.register(
        name="test_module",
        version="1.0.0",
        module_class=BenchmarkModule,
        lazy_load=False,
    )

    # Warm up
    for _ in range(100):
        registry.get("test_module")

    # Benchmark
    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        registry.get("test_module")
        elapsed = (time.perf_counter() - start) * 1000  # ms
        times.append(elapsed)

    return {
        "iterations": iterations,
        "mean_ms": statistics.mean(times),
        "median_ms": statistics.median(times),
        "stdev_ms": statistics.stdev(times) if len(times) > 1 else 0,
        "min_ms": min(times),
        "max_ms": max(times),
        "p95_ms": sorted(times)[int(len(times) * 0.95)],
        "p99_ms": sorted(times)[int(len(times) * 0.99)],
    }


def benchmark_pipeline_overhead(iterations: int = 100) -> Dict[str, float]:
    """Benchmark pipeline execution overhead"""
    print("\n[Benchmark 2] Pipeline Execution Overhead")
    print("-" * 60)

    registry = FSARegistry()
    registry.register(
        name="fast_module",
        version="1.0.0",
        module_class=BenchmarkModule,
        lazy_load=False,
    )

    pipeline = FSAPipeline(name="overhead_test", registry=registry)
    pipeline.add_stage(
        name="stage1",
        fsa_module_name="fast_module",
        inputs={"work_time_ms": 1},  # Minimal work
    )

    manager = FSAPipelineManager(registry=registry, enable_caching=False)

    # Warm up
    for _ in range(10):
        manager.execute_pipeline(pipeline, use_cache=False)

    # Benchmark
    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        result = manager.execute_pipeline(pipeline, use_cache=False)
        elapsed = (time.perf_counter() - start) * 1000  # ms
        times.append(elapsed)

    # Pipeline overhead = total time - FSA execution time (~1ms)
    overhead_times = [t - 1.0 for t in times]

    return {
        "iterations": iterations,
        "total_mean_ms": statistics.mean(times),
        "overhead_mean_ms": statistics.mean(overhead_times),
        "overhead_median_ms": statistics.median(overhead_times),
        "overhead_p95_ms": sorted(overhead_times)[int(len(overhead_times) * 0.95)],
    }


def benchmark_health_checks(iterations: int = 1000) -> Dict[str, float]:
    """Benchmark health check performance"""
    print("\n[Benchmark 3] Health Check Performance")
    print("-" * 60)

    registry = FSARegistry()
    for i in range(5):
        registry.register(
            name=f"module_{i}",
            version="1.0.0",
            module_class=BenchmarkModule,
            lazy_load=False,
        )

    # Warm up
    for _ in range(10):
        registry.health_check_all()

    # Benchmark single module
    single_times = []
    for _ in range(iterations):
        start = time.perf_counter()
        registry.health_check("module_0", force=True)
        elapsed = (time.perf_counter() - start) * 1000  # ms
        single_times.append(elapsed)

    # Benchmark all modules
    all_times = []
    for _ in range(iterations // 10):  # Fewer iterations for all modules
        start = time.perf_counter()
        registry.health_check_all()
        elapsed = (time.perf_counter() - start) * 1000  # ms
        all_times.append(elapsed)

    return {
        "single_module": {
            "iterations": iterations,
            "mean_ms": statistics.mean(single_times),
            "p95_ms": sorted(single_times)[int(len(single_times) * 0.95)],
        },
        "all_modules": {
            "module_count": 5,
            "iterations": len(all_times),
            "mean_ms": statistics.mean(all_times),
            "p95_ms": sorted(all_times)[int(len(all_times) * 0.95)],
        },
    }


def benchmark_parallel_execution() -> Dict[str, Any]:
    """Benchmark parallel vs sequential execution"""
    print("\n[Benchmark 4] Parallel vs Sequential Execution")
    print("-" * 60)

    registry = FSARegistry()
    for i in range(4):
        registry.register(
            name=f"worker_{i}",
            version="1.0.0",
            module_class=BenchmarkModule,
            lazy_load=False,
        )

    # Sequential pipeline
    seq_pipeline = FSAPipeline(name="sequential", registry=registry)
    seq_pipeline.add_stage("stage1", fsa_module_name="worker_0", inputs={"work_time_ms": 50})
    seq_pipeline.add_stage("stage2", fsa_module_name="worker_1", depends_on=["stage1"], inputs={"work_time_ms": 50})
    seq_pipeline.add_stage("stage3", fsa_module_name="worker_2", depends_on=["stage2"], inputs={"work_time_ms": 50})
    seq_pipeline.add_stage("stage4", fsa_module_name="worker_3", depends_on=["stage3"], inputs={"work_time_ms": 50})

    # Parallel pipeline (all stages independent)
    par_pipeline = FSAPipeline(name="parallel", registry=registry)
    par_pipeline.add_stage("stage1", fsa_module_name="worker_0", inputs={"work_time_ms": 50})
    par_pipeline.add_stage("stage2", fsa_module_name="worker_1", inputs={"work_time_ms": 50})
    par_pipeline.add_stage("stage3", fsa_module_name="worker_2", inputs={"work_time_ms": 50})
    par_pipeline.add_stage("stage4", fsa_module_name="worker_3", inputs={"work_time_ms": 50})

    manager = FSAPipelineManager(registry=registry, max_workers=4, enable_caching=False)

    # Benchmark sequential
    seq_times = []
    for _ in range(10):
        result = manager.execute_pipeline(seq_pipeline, use_cache=False)
        seq_times.append(result.total_duration_ms)

    # Benchmark parallel
    par_times = []
    for _ in range(10):
        result = manager.execute_pipeline(par_pipeline, use_cache=False)
        par_times.append(result.total_duration_ms)

    speedup = statistics.mean(seq_times) / statistics.mean(par_times)

    return {
        "sequential": {
            "mean_ms": statistics.mean(seq_times),
            "expected_ms": 200,  # 4 * 50ms
        },
        "parallel": {
            "mean_ms": statistics.mean(par_times),
            "expected_ms": 50,  # max(50ms)
        },
        "speedup": speedup,
    }


def benchmark_caching_effectiveness(iterations: int = 100) -> Dict[str, Any]:
    """Benchmark caching effectiveness"""
    print("\n[Benchmark 5] Caching Effectiveness")
    print("-" * 60)

    registry = FSARegistry()
    registry.register(
        name="expensive_module",
        version="1.0.0",
        module_class=BenchmarkModule,
        lazy_load=False,
    )

    pipeline = FSAPipeline(name="cache_test", registry=registry)
    pipeline.add_stage(
        name="expensive",
        fsa_module_name="expensive_module",
        inputs={"work_time_ms": 100},  # 100ms work
    )

    # Test without caching
    manager_no_cache = FSAPipelineManager(registry=registry, enable_caching=False)

    no_cache_times = []
    for _ in range(iterations):
        start = time.perf_counter()
        manager_no_cache.execute_pipeline(pipeline, use_cache=False)
        elapsed = (time.perf_counter() - start) * 1000
        no_cache_times.append(elapsed)

    # Test with caching
    manager_with_cache = FSAPipelineManager(registry=registry, enable_caching=True)

    with_cache_times = []
    for i in range(iterations):
        start = time.perf_counter()
        manager_with_cache.execute_pipeline(pipeline, use_cache=True)
        elapsed = (time.perf_counter() - start) * 1000
        with_cache_times.append(elapsed)

    # First call should be slow, rest should be fast
    first_call_ms = with_cache_times[0]
    cached_calls_ms = with_cache_times[1:]

    return {
        "no_cache": {
            "mean_ms": statistics.mean(no_cache_times),
            "iterations": iterations,
        },
        "with_cache": {
            "first_call_ms": first_call_ms,
            "cached_mean_ms": statistics.mean(cached_calls_ms) if cached_calls_ms else 0,
            "cache_hit_rate": (iterations - 1) / iterations * 100,
            "speedup": statistics.mean(no_cache_times) / statistics.mean(cached_calls_ms) if cached_calls_ms else 0,
        },
    }


def benchmark_memory_usage(iterations: int = 1000) -> Dict[str, Any]:
    """Benchmark memory usage"""
    print("\n[Benchmark 6] Memory Usage")
    print("-" * 60)

    tracemalloc.start()

    registry = FSARegistry()
    registry.register(
        name="test_module",
        version="1.0.0",
        module_class=BenchmarkModule,
        lazy_load=False,
    )

    pipeline = FSAPipeline(name="memory_test", registry=registry)
    pipeline.add_stage("stage1", fsa_module_name="test_module", inputs={"work_time_ms": 1})

    manager = FSAPipelineManager(registry=registry, enable_caching=False)

    # Get initial memory
    gc.collect()
    snapshot1 = tracemalloc.take_snapshot()

    # Execute many times
    for _ in range(iterations):
        manager.execute_pipeline(pipeline, use_cache=False)

    # Force garbage collection
    gc.collect()
    snapshot2 = tracemalloc.take_snapshot()

    # Calculate memory difference
    top_stats = snapshot2.compare_to(snapshot1, 'lineno')
    total_diff_bytes = sum(stat.size_diff for stat in top_stats)
    total_diff_mb = total_diff_bytes / (1024 * 1024)

    tracemalloc.stop()

    return {
        "iterations": iterations,
        "memory_growth_mb": total_diff_mb,
        "memory_per_execution_kb": (total_diff_bytes / iterations) / 1024,
    }


def benchmark_concurrent_load(num_pipelines: int = 50, max_workers: int = 10) -> Dict[str, Any]:
    """Benchmark concurrent pipeline execution"""
    print("\n[Benchmark 7] Concurrent Load Testing")
    print("-" * 60)

    registry = FSARegistry()
    registry.register(
        name="load_module",
        version="1.0.0",
        module_class=BenchmarkModule,
        lazy_load=False,
    )

    pipeline = FSAPipeline(name="load_test", registry=registry)
    pipeline.add_stage("stage1", fsa_module_name="load_module", inputs={"work_time_ms": 10})

    manager = FSAPipelineManager(registry=registry, max_workers=4, enable_caching=False)

    # Execute concurrently
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(manager.execute_pipeline, pipeline, {"run": i}, False)
            for i in range(num_pipelines)
        ]

        results = [f.result() for f in as_completed(futures)]

    total_time = time.time() - start_time

    # Calculate statistics
    successful = sum(1 for r in results if r.is_successful())
    durations = [r.total_duration_ms for r in results]

    return {
        "num_pipelines": num_pipelines,
        "max_workers": max_workers,
        "total_time_s": total_time,
        "throughput_per_sec": num_pipelines / total_time,
        "success_rate": successful / num_pipelines * 100,
        "mean_duration_ms": statistics.mean(durations),
        "p95_duration_ms": sorted(durations)[int(len(durations) * 0.95)],
    }


# ============================================================================
# Main Benchmark Runner
# ============================================================================

def print_results(name: str, results: Dict[str, Any]) -> None:
    """Pretty print benchmark results"""
    print(f"\nResults:")
    for key, value in results.items():
        if isinstance(value, dict):
            print(f"  {key}:")
            for k, v in value.items():
                if isinstance(v, float):
                    print(f"    {k}: {v:.4f}")
                else:
                    print(f"    {k}: {v}")
        elif isinstance(value, float):
            print(f"  {key}: {value:.4f}")
        else:
            print(f"  {key}: {value}")


def main():
    """Run all benchmarks"""

    print("=" * 70)
    print("FSA Framework Performance Benchmarks")
    print("=" * 70)

    benchmarks = [
        ("Registry Lookup", benchmark_registry_lookup, {}),
        ("Pipeline Overhead", benchmark_pipeline_overhead, {}),
        ("Health Checks", benchmark_health_checks, {}),
        ("Parallel Execution", benchmark_parallel_execution, {}),
        ("Caching Effectiveness", benchmark_caching_effectiveness, {}),
        ("Memory Usage", benchmark_memory_usage, {}),
        ("Concurrent Load", benchmark_concurrent_load, {}),
    ]

    all_results = {}

    for name, benchmark_func, kwargs in benchmarks:
        try:
            results = benchmark_func(**kwargs)
            all_results[name] = results
            print_results(name, results)
        except Exception as e:
            print(f"\n❌ Benchmark '{name}' failed: {e}")
            import traceback
            traceback.print_exc()

    # ========================================================================
    # Summary
    # ========================================================================
    print("\n" + "=" * 70)
    print("Benchmark Summary")
    print("=" * 70)

    if "Registry Lookup" in all_results:
        print(f"\n✓ Registry Lookup: {all_results['Registry Lookup']['mean_ms']:.4f}ms avg")

    if "Pipeline Overhead" in all_results:
        print(f"✓ Pipeline Overhead: {all_results['Pipeline Overhead']['overhead_mean_ms']:.4f}ms avg")

    if "Health Checks" in all_results:
        single = all_results['Health Checks']['single_module']
        print(f"✓ Health Check: {single['mean_ms']:.4f}ms per module")

    if "Parallel Execution" in all_results:
        speedup = all_results['Parallel Execution']['speedup']
        print(f"✓ Parallel Speedup: {speedup:.2f}x")

    if "Caching Effectiveness" in all_results:
        cache = all_results['Caching Effectiveness']['with_cache']
        print(f"✓ Cache Speedup: {cache['speedup']:.2f}x")

    if "Memory Usage" in all_results:
        mem = all_results['Memory Usage']
        print(f"✓ Memory/Execution: {mem['memory_per_execution_kb']:.2f} KB")

    if "Concurrent Load" in all_results:
        load = all_results['Concurrent Load']
        print(f"✓ Throughput: {load['throughput_per_sec']:.1f} pipelines/sec")

    print("\n" + "=" * 70)
    print("All benchmarks completed!")
    print("=" * 70)


if __name__ == "__main__":
    main()

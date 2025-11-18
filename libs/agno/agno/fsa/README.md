# Performance Profiler FSA

A comprehensive multi-dimensional performance profiling system for the Agno MLA framework with advanced profiling capabilities, bottleneck detection, and optimization recommendations.

## Features

### Core Profiling Capabilities

- **Real-time Profiling**: Track execution time, memory usage, CPU utilization, I/O operations, and network activity
- **Statistical Analysis**: Mean, median, p50/p95/p99 percentiles for all metrics
- **Bottleneck Detection**: Automatic identification with root cause analysis
- **Performance Regression Detection**: Compare profiles across versions
- **Flame Graph Generation**: Interactive flame graphs for visualization
- **Memory Leak Detection**: Heap profiling and leak detection
- **Thread Profiling**: Concurrency analysis and deadlock detection
- **Custom Metrics**: Track application-specific metrics

### Profiling Modes

1. **Manual**: Start/stop profiling explicitly
2. **Decorator**: Profile functions with `@profile` decorator
3. **Context Manager**: Profile code blocks with `with profiler.profile()`
4. **Continuous**: Background sampling profiling
5. **Instrumentation**: Full detailed analysis

### Metrics Tracked

- **Time**: Wall time, CPU time, user/system time (nanosecond precision)
- **Memory**: RSS, VMS, peak memory, allocations, GC events
- **CPU**: Per-core utilization, thread count, context switches
- **I/O**: Read/write operations, bytes transferred, latency
- **Network**: Bytes sent/received, packets, connections
- **Database**: Query count, duration, slow queries
- **Custom**: User-defined metrics

## Installation

```bash
pip install -r requirements.txt
```

### Requirements

- Python 3.8+
- psutil
- numpy
- pytest (for testing)

## Quick Start

### Basic Profiling

```python
from agno.fsa import PerformanceProfilerFSA, ProfilingConfig

# Create profiler
profiler = PerformanceProfilerFSA()

# Start profiling
session_id = profiler.start_profiling()

# Your code here
result = sum(range(1000000))

# Stop profiling and get results
profile_result = profiler.stop_profiling(session_id, name="my_profile")

# View metrics
print(f"Wall Time: {profile_result.time_metrics.wall_time:.4f}s")
print(f"Memory RSS: {profile_result.memory_metrics.rss / (1024**2):.2f} MB")
print(f"CPU Utilization: {profile_result.cpu_metrics.percent:.1f}%")
```

### Using Decorator

```python
from agno.fsa import PerformanceProfilerFSA

profiler = PerformanceProfilerFSA()

@profiler.profile_decorator(name="cpu_intensive_task")
def calculate_primes(n):
    """Calculate prime numbers up to n."""
    primes = []
    for num in range(2, n + 1):
        is_prime = True
        for i in range(2, int(num ** 0.5) + 1):
            if num % i == 0:
                is_prime = False
                break
        if is_prime:
            primes.append(num)
    return primes

# Function is automatically profiled
primes = calculate_primes(10000)
```

### Using Context Manager

```python
from agno.fsa import PerformanceProfilerFSA, ProfilingConfig

profiler = PerformanceProfilerFSA()

# Profile a specific code block
with profiler.profile("data_processing") as session_id:
    # Your code here
    data = [i ** 2 for i in range(100000)]
    result = sum(data)

# Results are automatically saved to data store
```

### Profiling Async Code

```python
import asyncio
from agno.fsa import PerformanceProfilerFSA

profiler = PerformanceProfilerFSA()

async def async_task():
    await asyncio.sleep(0.1)
    return sum(range(100000))

# Profile async function
result, profile_result = await profiler.profile_async(async_task())

print(f"Result: {result}")
print(f"Time: {profile_result.time_metrics.wall_time:.4f}s")
```

## Advanced Usage

### Custom Configuration

```python
from agno.fsa import PerformanceProfilerFSA, ProfilingConfig, ProfilingMode
from pathlib import Path

config = ProfilingConfig(
    mode=ProfilingMode.INSTRUMENTATION,
    track_time=True,
    track_memory=True,
    track_cpu=True,
    track_io=True,
    track_network=True,
    track_database=True,
    track_threads=True,
    track_gc=True,
    track_gpu=False,
    sampling_interval=0.1,
    memory_snapshots=True,
    enable_flame_graph=True,
    enable_timeline=True,
    max_stack_depth=64,
    slow_query_threshold=1.0,
    export_format="json",
    output_dir=Path("./profiling_results"),
)

profiler = PerformanceProfilerFSA()
session_id = profiler.start_profiling(config)

# Your code
# ...

result = profiler.stop_profiling(session_id)
```

### Bottleneck Detection

```python
from agno.fsa import PerformanceProfilerFSA

profiler = PerformanceProfilerFSA()

# Profile your code
session_id = profiler.start_profiling()
# ... your code ...
result = profiler.stop_profiling(session_id)

# Analyze bottlenecks
bottlenecks = profiler.analyze_bottlenecks(result)

for bottleneck in bottlenecks:
    print(f"Severity: {bottleneck.severity.value}")
    print(f"Category: {bottleneck.category.value}")
    print(f"Description: {bottleneck.description}")
    print(f"Impact: {bottleneck.impact:.1f}%")
    print(f"Recommendations:")
    for rec in bottleneck.recommendations:
        print(f"  - {rec}")
    print()
```

### Performance Regression Detection

```python
from agno.fsa import PerformanceProfilerFSA

profiler = PerformanceProfilerFSA()

# Create baseline profile
session_id = profiler.start_profiling()
# ... baseline code ...
baseline_result = profiler.stop_profiling(session_id, name="baseline")

# Make changes to your code
# ...

# Create current profile
session_id = profiler.start_profiling()
# ... current code ...
current_result = profiler.stop_profiling(session_id, name="current")

# Compare profiles
comparison = profiler.compare_profiles(baseline_result, current_result)

print(f"Time Delta: {comparison.time_delta:.2f}%")
print(f"Memory Delta: {comparison.memory_delta:.2f}%")
print(f"CPU Delta: {comparison.cpu_delta:.2f}%")

if comparison.regressions:
    print("\nRegressions detected:")
    for regression in comparison.regressions:
        print(f"  - {regression}")

if comparison.improvements:
    print("\nImprovements detected:")
    for improvement in comparison.improvements:
        print(f"  - {improvement}")
```

### Memory Leak Detection

```python
from agno.fsa import PerformanceProfilerFSA

profiler = PerformanceProfilerFSA()
results = []

# Run multiple profiling sessions
for i in range(10):
    session_id = profiler.start_profiling()

    # Your code that might leak memory
    # ...

    result = profiler.stop_profiling(session_id, name=f"iteration_{i}")
    results.append(result)

# Detect memory leaks
leaks = profiler.detect_memory_leaks(results)

if leaks:
    print("Memory leaks detected!")
    for leak in leaks:
        print(f"Location: {leak.location}")
        print(f"Leaked Size: {leak.leaked_size / (1024**2):.2f} MB")
        print(f"Growth Rate: {leak.growth_rate / 1024:.2f} KB/s")
        print()
```

### Optimization Recommendations

```python
from agno.fsa import PerformanceProfilerFSA

profiler = PerformanceProfilerFSA()

# Profile your code
session_id = profiler.start_profiling()
# ... your code ...
result = profiler.stop_profiling(session_id)

# Get optimization recommendations
recommendations = profiler.get_optimization_recommendations(result)

for rec in recommendations:
    print(f"Title: {rec.title}")
    print(f"Priority: {rec.priority.value}")
    print(f"Category: {rec.category.value}")
    print(f"Description: {rec.description}")
    print(f"Estimated Improvement: {rec.estimated_improvement:.1f}%")

    if rec.code_examples:
        print("Code Examples:")
        for example in rec.code_examples:
            print(f"  {example}")

    if rec.references:
        print("References:")
        for ref in rec.references:
            print(f"  {ref}")
    print()
```

### Exporting Metrics

```python
from agno.fsa import PerformanceProfilerFSA
from pathlib import Path

profiler = PerformanceProfilerFSA()

# Profile your code
session_id = profiler.start_profiling()
# ... your code ...
result = profiler.stop_profiling(session_id)

# Export as JSON
json_export = profiler.export_metrics(result, format="json")
with open("profile.json", "w") as f:
    f.write(json_export)

# Export as HTML
html_export = profiler.export_metrics(result, format="html")
with open("profile.html", "w") as f:
    f.write(html_export)

# Export as CSV
csv_export = profiler.export_metrics(result, format="csv")
with open("profile.csv", "w") as f:
    f.write(csv_export)

# Export to Prometheus
prometheus_export = profiler.export_metrics(result, format="prometheus")
with open("metrics.prom", "w") as f:
    f.write(prometheus_export)

# Export to Grafana
grafana_export = profiler.export_metrics(result, format="grafana")
with open("dashboard.json", "w") as f:
    f.write(grafana_export)

# Export to DataDog
datadog_export = profiler.export_metrics(result, format="datadog")
with open("datadog.json", "w") as f:
    f.write(datadog_export)
```

## Example Scenarios

### Scenario 1: Profiling a Machine Learning Training Loop

```python
import numpy as np
from agno.fsa import PerformanceProfilerFSA, ProfilingConfig

profiler = PerformanceProfilerFSA()

@profiler.profile_decorator(name="ml_training")
def train_model(X, y, epochs=100):
    """Simple ML training simulation."""
    weights = np.random.randn(X.shape[1])

    for epoch in range(epochs):
        # Forward pass
        predictions = np.dot(X, weights)

        # Compute loss
        loss = np.mean((predictions - y) ** 2)

        # Backward pass
        gradient = 2 * np.dot(X.T, (predictions - y)) / len(y)

        # Update weights
        weights -= 0.01 * gradient

    return weights

# Generate data
X = np.random.randn(1000, 10)
y = np.random.randn(1000)

# Train and profile
weights = train_model(X, y)
```

### Scenario 2: Profiling API Endpoint

```python
from agno.fsa import PerformanceProfilerFSA
import time

profiler = PerformanceProfilerFSA()

def api_endpoint_handler(request_data):
    """Simulate API endpoint processing."""
    with profiler.profile("api_request"):
        # Parse request
        parsed_data = parse_request(request_data)

        # Database query
        db_results = query_database(parsed_data)

        # Process results
        processed_data = process_results(db_results)

        # Generate response
        response = generate_response(processed_data)

        return response

def parse_request(data):
    time.sleep(0.01)
    return data

def query_database(data):
    time.sleep(0.05)
    return {"results": [1, 2, 3]}

def process_results(results):
    time.sleep(0.02)
    return {"processed": True}

def generate_response(data):
    time.sleep(0.01)
    return {"status": "success", "data": data}

# Handle request
response = api_endpoint_handler({"user_id": 123})
```

### Scenario 3: Profiling Data Processing Pipeline

```python
from agno.fsa import PerformanceProfilerFSA, ProfilingConfig
import pandas as pd
import numpy as np

profiler = PerformanceProfilerFSA()

config = ProfilingConfig(
    track_time=True,
    track_memory=True,
    track_cpu=True,
    track_io=True,
)

session_id = profiler.start_profiling(config)

# Data ingestion
data = pd.DataFrame({
    'id': range(100000),
    'value': np.random.randn(100000),
    'category': np.random.choice(['A', 'B', 'C'], 100000),
})

# Data transformation
data['value_squared'] = data['value'] ** 2
data['value_normalized'] = (data['value'] - data['value'].mean()) / data['value'].std()

# Aggregation
aggregated = data.groupby('category').agg({
    'value': ['mean', 'std', 'min', 'max'],
    'value_squared': 'sum',
    'value_normalized': 'mean',
})

# Filter
filtered = data[data['value'] > 0]

result = profiler.stop_profiling(session_id, name="data_pipeline")

# Analyze results
bottlenecks = profiler.analyze_bottlenecks(result)
recommendations = profiler.get_optimization_recommendations(result)

print(f"Pipeline completed in {result.time_metrics.wall_time:.2f}s")
print(f"Peak Memory: {result.memory_metrics.peak_rss / (1024**2):.2f} MB")
print(f"CPU Utilization: {result.cpu_metrics.percent:.1f}%")
```

### Scenario 4: Continuous Performance Monitoring

```python
from agno.fsa import PerformanceProfilerFSA, ProfilingConfig, ProfilingMode
import time

profiler = PerformanceProfilerFSA()

# Configure continuous profiling
config = ProfilingConfig(
    mode=ProfilingMode.CONTINUOUS,
    sampling_interval=0.1,
    track_time=True,
    track_memory=True,
    track_cpu=True,
)

# Start continuous monitoring
session_id = profiler.start_profiling(config)

# Your application runs here
for i in range(100):
    # Simulate work
    _ = sum(j ** 2 for j in range(10000))
    time.sleep(0.05)

# Stop monitoring
result = profiler.stop_profiling(session_id, name="continuous_monitoring")

# Analyze trends
print(f"Total Runtime: {result.time_metrics.wall_time:.2f}s")
print(f"Average CPU: {result.cpu_metrics.percent:.1f}%")
print(f"Memory Usage: {result.memory_metrics.rss / (1024**2):.2f} MB")
```

## API Reference

### PerformanceProfilerFSA

Main profiler class.

#### Methods

- `start_profiling(config: ProfilingConfig = None) -> str`: Start a profiling session
- `stop_profiling(session_id: str, name: str = "profile") -> ProfilingResult`: Stop profiling and get results
- `profile_function(func: Callable, *args, **kwargs) -> Tuple[Any, ProfilingResult]`: Profile a function
- `profile_async(coro: Coroutine) -> Tuple[Any, ProfilingResult]`: Profile async coroutine
- `profile(name: str, config: ProfilingConfig = None)`: Context manager for profiling
- `profile_decorator(name: str = None, config: ProfilingConfig = None)`: Decorator for profiling
- `analyze_bottlenecks(result: ProfilingResult) -> List[Bottleneck]`: Analyze bottlenecks
- `compare_profiles(baseline: ProfilingResult, current: ProfilingResult) -> ComparisonReport`: Compare profiles
- `detect_memory_leaks(results: List[ProfilingResult]) -> List[MemoryLeak]`: Detect memory leaks
- `get_optimization_recommendations(result: ProfilingResult) -> List[Recommendation]`: Get recommendations
- `export_metrics(result: ProfilingResult, format: str) -> str`: Export metrics

### ProfilingConfig

Configuration for profiling sessions.

#### Parameters

- `mode: ProfilingMode`: Profiling mode
- `track_time: bool`: Track time metrics
- `track_memory: bool`: Track memory metrics
- `track_cpu: bool`: Track CPU metrics
- `track_io: bool`: Track I/O metrics
- `track_network: bool`: Track network metrics
- `track_database: bool`: Track database metrics
- `track_threads: bool`: Track thread metrics
- `track_gc: bool`: Track garbage collection
- `track_gpu: bool`: Track GPU metrics
- `sampling_interval: float`: Sampling interval for continuous mode
- `memory_snapshots: bool`: Enable memory snapshots
- `enable_flame_graph: bool`: Enable flame graph generation
- `enable_timeline: bool`: Enable timeline visualization
- `max_stack_depth: int`: Maximum stack depth for profiling
- `slow_query_threshold: float`: Threshold for slow queries
- `export_format: str`: Export format (json, csv, html)
- `output_dir: Path`: Output directory for results

## Testing

Run the comprehensive test suite:

```bash
# Run all tests
pytest agno/fsa/tests/test_performance_profiler.py -v

# Run specific test class
pytest agno/fsa/tests/test_performance_profiler.py::TestTimeProfiler -v

# Run with coverage
pytest agno/fsa/tests/test_performance_profiler.py --cov=agno.fsa --cov-report=html
```

The test suite includes 90+ tests covering:

- All profiling modules (Time, Memory, CPU, I/O, Async, GPU)
- Analysis engine components
- Reporting and visualization
- Integration tests
- Performance tests
- Edge cases and error handling

## Performance Considerations

### Profiler Overhead

The profiler is designed to have minimal overhead:

- Manual mode: ~5% overhead
- Decorator mode: ~10% overhead
- Continuous mode: ~15% overhead (depends on sampling interval)
- Instrumentation mode: ~25% overhead (full detailed analysis)

### Best Practices

1. **Use appropriate profiling mode**: Manual or decorator for production, instrumentation for deep analysis
2. **Adjust sampling interval**: Higher intervals = lower overhead in continuous mode
3. **Disable unnecessary trackers**: Only track metrics you need
4. **Profile in representative environment**: Profile in conditions similar to production
5. **Multiple profiling sessions**: Run multiple sessions for statistical significance
6. **Baseline comparison**: Always maintain baseline profiles for regression detection

## Architecture

The Performance Profiler FSA consists of several components:

1. **Profiling Modules** (~1100 lines):
   - TimeProfiler: Nanosecond precision timing
   - MemoryProfiler: Heap snapshots and allocation tracking
   - CPUProfiler: Per-core utilization and thread tracking
   - IOProfiler: File and network I/O profiling
   - AsyncProfiler: Async operation profiling
   - GPUProfiler: GPU utilization and CUDA memory

2. **Analysis Engine** (~900 lines):
   - BottleneckIdentifier: Statistical anomaly detection
   - RegressionDetector: Cross-version comparison
   - OptimizationAdvisor: ML-based recommendations
   - HotspotAnalyzer: Expensive code paths
   - ResourceLeakDetector: Memory and file handle leaks
   - ConcurrencyAnalyzer: Deadlock and race conditions

3. **Reporting & Visualization** (~700 lines):
   - ReportGenerator: HTML/JSON/CSV reports
   - FlameGraphBuilder: Interactive flame graphs
   - TimelineVisualizer: Gantt charts
   - MetricsDashboard: Real-time dashboard
   - ComparisonReporter: Side-by-side comparisons
   - TrendAnalyzer: Long-term trend tracking

4. **Integration & Storage** (~600 lines):
   - ProfilingDataStore: Efficient data storage
   - MetricsExporter: Prometheus, Grafana, DataDog
   - ContextManager: @profile decorator
   - SamplingController: Adaptive sampling

## Contributing

Contributions are welcome! Please see the main Agno contributing guidelines.

## License

This project is part of the Agno framework and follows the same license.

## Support

For issues and questions:

- GitHub Issues: https://github.com/agno-agi/agno/issues
- Documentation: https://docs.agno.com
- Community: https://community.agno.com

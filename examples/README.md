# FSA Framework Examples

This directory contains examples demonstrating the FSA Framework capabilities.

## Available Examples

### 1. Integration Example (`fsa_integration_example.py`)

**Purpose**: Demonstrates end-to-end FSA Framework usage with a complete ETL pipeline.

**Features Demonstrated**:
- FSA module registration
- Pipeline construction with dependencies
- Parallel stage execution
- Error handling and retry logic
- Health checks
- Performance monitoring
- Configuration management

**Run**:
```bash
cd examples
python fsa_integration_example.py
```

**Expected Output**:
- Step-by-step execution log
- Pipeline execution order visualization
- Stage results and timing
- Performance metrics
- Success confirmation

### 2. Performance Benchmark (`fsa_benchmark.py`)

**Purpose**: Comprehensive performance benchmarking of FSA Framework components.

**Benchmarks**:
1. **Registry Lookup**: Module retrieval performance
2. **Pipeline Overhead**: Execution overhead measurement
3. **Health Checks**: Health check latency
4. **Parallel Execution**: Sequential vs parallel speedup
5. **Caching Effectiveness**: Cache hit performance
6. **Memory Usage**: Memory footprint per execution
7. **Concurrent Load**: Throughput under concurrent load

**Run**:
```bash
cd examples
python fsa_benchmark.py
```

**Expected Output**:
- Detailed benchmark results for each component
- Performance metrics (mean, median, P95, P99)
- Speedup comparisons
- Memory usage statistics
- Throughput measurements

**Performance Targets**:
- Registry lookup: < 1ms avg
- Pipeline overhead: < 10ms avg
- Health check: < 5ms avg
- Parallel speedup: 2-3x with 4 workers
- Cache speedup: > 10x for expensive operations
- Memory/execution: < 50KB
- Throughput: > 50 pipelines/sec

## Quick Start

### Prerequisites

```bash
# Install agno library
cd libs/agno
pip install -e .

# Install test dependencies (optional)
pip install pytest
```

### Running Examples

```bash
# Run integration example
python examples/fsa_integration_example.py

# Run benchmarks
python examples/fsa_benchmark.py

# Run tests
pytest libs/agno/tests/fsa/test_fsa_integration.py -v
```

## Example Output

### Integration Example Output

```
======================================================================
FSA Framework Integration Example
======================================================================

[Step 1] Loading Configuration...
✓ Environment: development
✓ Max Workers: 2
✓ Caching: True

[Step 2] Registering FSA Modules...
✓ Registered: extractor v1.0.0 (deps: none)
✓ Registered: validator v1.0.0 (deps: ['extractor'])
✓ Registered: transformer v1.0.0 (deps: ['extractor', 'validator'])
✓ Registered: loader v1.0.0 (deps: ['transformer'])
✓ Registered: analyzer v1.0.0 (deps: ['transformer'])

[Step 3] Running Health Checks...
✓ extractor: healthy
✓ validator: healthy
✓ transformer: healthy
✓ loader: healthy
✓ analyzer: healthy

[Step 4] Creating ETL Pipeline...
✓ Pipeline created: etl_workflow
  Stages: 5

  Execution Order:
    Stage 1: extract
    Stage 2: validate
    Stage 3: transform
    Batch 4 (parallel): load, analyze

[Step 5] Executing Pipeline...
  Starting execution...

[Step 6] Execution Results:

✓ Pipeline Status: success
  Total Duration: 450.23ms (wall time: 452.10ms)
  Success Rate: 100.0%

  Stage Results:
    ✓ extract:
       Status: completed
       Duration: 102.45ms
    ✓ validate:
       Status: completed
       Duration: 51.23ms
    ✓ transform:
       Status: completed
       Duration: 82.15ms
    ✓ load:
       Status: completed
       Duration: 122.34ms
    ✓ analyze:
       Status: completed
       Duration: 102.67ms

[Step 7] Performance Metrics:
  Running additional executions for metrics collection...

  Pipeline: etl_workflow
    Execution Count: 4
    Avg Duration: 448.12ms
    Min Duration: 445.23ms
    Max Duration: 452.10ms
    P95 Duration: 452.10ms

[Step 8] Summary:
  ✓ Registered 5 FSA modules
  ✓ Created pipeline with 5 stages
  ✓ Executed 4 times
  ✓ All health checks passed
  ✓ Parallel execution optimized runtime

======================================================================
Example completed successfully!
======================================================================
```

### Benchmark Output

```
======================================================================
FSA Framework Performance Benchmarks
======================================================================

[Benchmark 1] Registry Lookup Performance
------------------------------------------------------------

Results:
  iterations: 10000
  mean_ms: 0.0023
  median_ms: 0.0021
  p95_ms: 0.0034
  p99_ms: 0.0045

[Benchmark 2] Pipeline Execution Overhead
------------------------------------------------------------

Results:
  iterations: 100
  total_mean_ms: 8.45
  overhead_mean_ms: 7.45
  overhead_median_ms: 7.32
  overhead_p95_ms: 9.12

... (more benchmarks) ...

======================================================================
Benchmark Summary
======================================================================

✓ Registry Lookup: 0.0023ms avg
✓ Pipeline Overhead: 7.45ms avg
✓ Health Check: 0.89ms per module
✓ Parallel Speedup: 3.12x
✓ Cache Speedup: 45.23x
✓ Memory/Execution: 12.34 KB
✓ Throughput: 78.5 pipelines/sec

======================================================================
All benchmarks completed!
======================================================================
```

## Customization

### Create Your Own FSA Module

```python
class MyCustomFSA:
    def __init__(self, **kwargs):
        self.dependencies = kwargs.get('dependencies', {})
        # Your initialization code

    def execute(self, **kwargs):
        # Your execution logic
        return {"result": "success"}

    def health_check(self):
        # Your health check logic
        return True

# Register
from agno.fsa import FSARegistry
registry = FSARegistry()
registry.register(
    name="my_custom_fsa",
    version="1.0.0",
    module_class=MyCustomFSA,
)
```

### Create Your Own Pipeline

```python
from agno.fsa import FSAPipeline, FSAPipelineManager

pipeline = FSAPipeline(name="my_pipeline", registry=registry)

pipeline.add_stage(
    name="stage1",
    fsa_module_name="my_custom_fsa",
    inputs={"param": "value"},
)

manager = FSAPipelineManager(registry=registry)
result = manager.execute_pipeline(pipeline)
```

## Troubleshooting

### Import Errors

If you get import errors, ensure agno is installed:
```bash
cd libs/agno
pip install -e .
```

### Module Not Found

Ensure you're running from the correct directory:
```bash
cd /path/to/agno
python examples/fsa_integration_example.py
```

### Performance Issues

Check configuration:
```python
from agno.config import get_fsa_config
config = get_fsa_config()
print(config.to_dict())
```

## Next Steps

1. Review the [FSA Framework Guide](../docs/fsa/FSA-FRAMEWORK-GUIDE.md)
2. Run the integration tests: `pytest libs/agno/tests/fsa/`
3. Explore the framework code in `libs/agno/agno/fsa/`
4. Create your own FSA modules and pipelines
5. Use the CLI: `python -m agno.fsa.cli --help`

## Support

For issues or questions:
- Check the [Framework Guide](../docs/fsa/FSA-FRAMEWORK-GUIDE.md)
- Review test cases in `libs/agno/tests/fsa/test_fsa_integration.py`
- Open an issue in the repository

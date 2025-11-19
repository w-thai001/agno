# FSA Framework - Comprehensive Guide

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Installation](#installation)
4. [Quick Start](#quick-start)
5. [Core Components](#core-components)
6. [Usage Examples](#usage-examples)
7. [Configuration](#configuration)
8. [CLI Reference](#cli-reference)
9. [Performance Optimization](#performance-optimization)
10. [Production Deployment](#production-deployment)
11. [Testing](#testing)
12. [Troubleshooting](#troubleshooting)
13. [Migration Guide](#migration-guide)

---

## Overview

The **FSA (Finite State Agent) Framework** is a production-ready system for building, managing, and orchestrating complex agent workflows in the Agno ecosystem. It provides:

- **Centralized Registry**: Dependency injection and module management
- **Pipeline Orchestration**: Dynamic workflow construction with parallel execution
- **Production Features**: Caching, monitoring, rate limiting, and error recovery
- **CLI Tools**: Command-line interface for all FSA operations
- **Comprehensive Testing**: Integration tests and performance benchmarks

### Key Benefits

✅ **Modularity**: Build reusable FSA components with clear dependencies
✅ **Scalability**: Parallel execution and resource management
✅ **Reliability**: Error recovery, retry logic, and health monitoring
✅ **Performance**: Caching, lazy loading, and < 10ms overhead
✅ **Production-Ready**: Environment-specific configuration and monitoring

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     FSA Framework                            │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   Registry   │───▶│   Pipeline   │───▶│     CLI      │  │
│  │   System     │    │   Manager    │    │   Interface  │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│        │                    │                    │           │
│        ├─ Module Mgmt       ├─ Execution         ├─ Commands│
│        ├─ Dependencies      ├─ Parallel          ├─ Config  │
│        ├─ Health Check      ├─ Caching           └─ Interact│
│        └─ Lazy Loading      └─ Metrics                       │
│                                                               │
├─────────────────────────────────────────────────────────────┤
│                   Production Config                          │
│  Environment | Rate Limiting | Logging | Monitoring          │
└─────────────────────────────────────────────────────────────┘
```

### Component Relationships

```
FSARegistry (registry.py)
    ↓
    Manages FSA modules with dependency injection
    ↓
FSAPipelineManager (pipeline_manager.py)
    ↓
    Orchestrates FSA execution in pipelines
    ↓
FSACLIHandler (cli.py)
    ↓
    Provides command-line interface
    ↓
FSAProductionConfig (config/fsa_production_config.py)
    ↓
    Environment-specific settings
```

---

## Installation

The FSA Framework is included in the Agno library:

```bash
cd libs/agno
pip install -e .
```

### Dependencies

- Python 3.8+
- Standard library only (no external dependencies for core functionality)
- Optional: pytest for running tests

---

## Quick Start

### 1. Register FSA Modules

```python
from agno.fsa import FSARegistry

# Get the global registry
registry = FSARegistry()

# Register a module
registry.register(
    name="my_builder",
    version="1.0.0",
    module_class=MyBuilderClass,
    dependencies=[],
    lazy_load=True,
)
```

### 2. Create a Pipeline

```python
from agno.fsa import FSAPipeline, FSAPipelineManager

# Create pipeline
pipeline = FSAPipeline(name="my_workflow", registry=registry)

# Add stages
pipeline.add_stage(
    name="build",
    fsa_module_name="my_builder",
    inputs={"data": "input_data"},
)

pipeline.add_stage(
    name="optimize",
    fsa_module_name="my_optimizer",
    depends_on=["build"],
)
```

### 3. Execute Pipeline

```python
# Create manager
manager = FSAPipelineManager(registry=registry)

# Execute
result = manager.execute_pipeline(pipeline)

# Check results
if result.is_successful():
    print(f"Success! Duration: {result.total_duration_ms:.2f}ms")
    for stage in result.stage_results:
        print(f"  {stage.stage_name}: {stage.status.value}")
```

### 4. Use CLI

```bash
# Initialize configuration
python -m agno.fsa.cli init

# Validate setup
python -m agno.fsa.cli validate --health-check

# List modules
python -m agno.fsa.cli list

# Check health
python -m agno.fsa.cli health
```

---

## Core Components

### FSA Registry

**Purpose**: Central registration and management of FSA modules

**Features**:
- Module registration with version management
- Dependency injection and resolution
- Lazy loading for performance
- Health monitoring
- Thread-safe operations

**Example**:

```python
from agno.fsa.registry import FSARegistry, get_registry

# Option 1: Create new registry
registry = FSARegistry()

# Option 2: Use global singleton
registry = get_registry()

# Register module
registry.register(
    name="multi_step_builder",
    version="1.0.0",
    module_class=MultiStepBuilder,
    dependencies=["base_module"],
    lazy_load=True,
    metadata={"author": "agno", "type": "builder"},
)

# Get instance (with dependency injection)
instance = registry.get("multi_step_builder")

# Health check
health = registry.health_check("multi_step_builder")
print(f"Status: {health.status.value}")

# List all modules
modules = registry.list_modules()
for module in modules:
    print(f"{module['name']} v{module['version']}")
```

### FSA Pipeline Manager

**Purpose**: Orchestrate FSA execution with pipelines

**Features**:
- Dynamic pipeline construction
- Parallel execution of independent stages
- Error recovery and retry logic
- Result caching
- Performance metrics

**Example**:

```python
from agno.fsa.pipeline_manager import FSAPipeline, FSAPipelineManager

# Create manager
manager = FSAPipelineManager(
    registry=registry,
    max_workers=4,
    enable_caching=True,
)

# Create pipeline
pipeline = FSAPipeline(name="data_processing")

# Add parallel stages
pipeline.add_stage(name="extract", fsa_module_name="extractor")
pipeline.add_stage(name="validate", fsa_module_name="validator")

# Add dependent stage
pipeline.add_stage(
    name="transform",
    fsa_module_name="transformer",
    depends_on=["extract", "validate"],
    retry_config={"max_retries": 3, "backoff_ms": 1000},
)

# Execute
result = manager.execute_pipeline(
    pipeline,
    initial_inputs={"file": "data.csv"},
)

# Get metrics
metrics = manager.get_metrics("data_processing")
print(f"Avg duration: {metrics['avg_duration_ms']:.2f}ms")
```

### FSA CLI

**Purpose**: Command-line interface for FSA operations

**Available Commands**:

```bash
# Initialize configuration
fsa init [--force]

# Build pipeline
fsa build <pipeline-name> [--execute] [--inputs JSON]

# Optimize performance
fsa optimize

# Validate configuration
fsa validate [--health-check]

# Execute orchestration
fsa orchestrate <pipeline-name> [--inputs-file FILE]

# List modules
fsa list [--verbose]

# Check health
fsa health [--module MODULE]
```

### Production Configuration

**Purpose**: Environment-specific settings management

**Supported Environments**:
- `development`: Local development with debug logging
- `staging`: Pre-production testing
- `production`: Production deployment with full monitoring
- `test`: Testing environment with minimal features

**Example**:

```python
from agno.config import get_fsa_config, Environment

# Get config for current environment
config = get_fsa_config()

# Or specify environment
config = get_fsa_config(env="production")

# Access settings
print(f"Max workers: {config.resources.max_workers}")
print(f"Cache enabled: {config.caching.enabled}")
print(f"Rate limit: {config.rate_limiting.requests_per_second}")

# Apply logging configuration
config.apply_logging_config()
```

---

## Usage Examples

### Example 1: Simple FSA Registration and Execution

```python
from agno.fsa import FSARegistry

class SimpleCalculator:
    def execute(self, a: int, b: int) -> int:
        return a + b

    def health_check(self) -> bool:
        return True

# Register
registry = FSARegistry()
registry.register(
    name="calculator",
    version="1.0.0",
    module_class=SimpleCalculator,
)

# Use
calc = registry.get("calculator")
result = calc.execute(a=5, b=3)
print(f"Result: {result}")  # Output: Result: 8
```

### Example 2: Pipeline with Dependencies

```python
from agno.fsa import FSAPipeline, FSAPipelineManager, FSARegistry

# Define FSA classes
class DataLoader:
    def execute(self, file_path: str):
        # Load data
        return {"data": [1, 2, 3, 4, 5]}

class DataProcessor:
    def execute(self, data_loader_output):
        data = data_loader_output["data"]
        return {"processed": [x * 2 for x in data]}

class DataAnalyzer:
    def execute(self, data_processor_output):
        processed = data_processor_output["processed"]
        return {"mean": sum(processed) / len(processed)}

# Register modules
registry = FSARegistry()
registry.register("loader", "1.0.0", module_class=DataLoader)
registry.register("processor", "1.0.0", module_class=DataProcessor)
registry.register("analyzer", "1.0.0", module_class=DataAnalyzer)

# Create pipeline
pipeline = FSAPipeline(name="data_analysis", registry=registry)
pipeline.add_stage("load", fsa_module_name="loader", inputs={"file_path": "data.csv"})
pipeline.add_stage("process", fsa_module_name="processor", depends_on=["load"])
pipeline.add_stage("analyze", fsa_module_name="analyzer", depends_on=["process"])

# Execute
manager = FSAPipelineManager(registry=registry)
result = manager.execute_pipeline(pipeline)

# Get final result
analyzer_result = result.get_stage_result("analyze")
print(f"Analysis result: {analyzer_result.output}")
```

### Example 3: Parallel Execution

```python
from agno.fsa import FSAPipeline, FSAPipelineManager

# Create pipeline with parallel stages
pipeline = FSAPipeline(name="parallel_processing")

# These two stages can run in parallel (no dependencies)
pipeline.add_stage("validate_format", fsa_module_name="format_validator")
pipeline.add_stage("validate_schema", fsa_module_name="schema_validator")

# This stage depends on both validators
pipeline.add_stage(
    "process",
    fsa_module_name="processor",
    depends_on=["validate_format", "validate_schema"],
)

# Execute (validators run in parallel)
result = manager.execute_pipeline(pipeline)
```

### Example 4: Error Handling and Retry

```python
from agno.fsa import FSAPipeline

pipeline = FSAPipeline(name="resilient_workflow")

pipeline.add_stage(
    name="api_call",
    fsa_module_name="external_api",
    retry_config={
        "max_retries": 5,
        "backoff_ms": 2000,
        "backoff_multiplier": 1.5,
    },
    timeout_ms=30000,  # 30 second timeout
)

result = manager.execute_pipeline(pipeline)

# Check retry information
api_stage = result.get_stage_result("api_call")
print(f"Retries needed: {api_stage.retry_count}")
```

### Example 5: CLI Workflow

```bash
# Create configuration
cat > .fsarc.json << EOF
{
  "version": "1.0.0",
  "modules": {
    "builder": {
      "version": "1.0.0",
      "path": "agno.fsa.multi_step_builder.MultiStepBuilder"
    }
  },
  "pipelines": {
    "my_workflow": {
      "description": "Example workflow",
      "stages": [
        {
          "name": "build",
          "fsa_module": "builder",
          "inputs": {"data": "test"}
        }
      ]
    }
  }
}
EOF

# Validate
python -m agno.fsa.cli validate --health-check

# Execute
python -m agno.fsa.cli orchestrate my_workflow

# Check performance
python -m agno.fsa.cli optimize
```

---

## Configuration

### Configuration File (.fsarc.json)

```json
{
  "version": "1.0.0",
  "modules": {
    "module_name": {
      "version": "1.0.0",
      "path": "package.module.ClassName",
      "dependencies": ["other_module"],
      "lazy_load": true
    }
  },
  "pipelines": {
    "pipeline_name": {
      "description": "Pipeline description",
      "stages": [
        {
          "name": "stage1",
          "fsa_module": "module_name",
          "inputs": {"key": "value"},
          "depends_on": [],
          "retry_config": {
            "max_retries": 3,
            "backoff_ms": 1000
          }
        }
      ]
    }
  },
  "settings": {
    "max_workers": 4,
    "enable_caching": true,
    "cache_ttl_seconds": 3600,
    "log_level": "INFO"
  }
}
```

### Environment Variables

```bash
# Environment selection
export FSA_ENVIRONMENT=production

# Redis for caching (production/staging)
export REDIS_URL=redis://localhost:6379

# Allowed CORS origins (production)
export ALLOWED_ORIGINS=https://example.com,https://app.example.com

# Logging
export FSA_LOG_LEVEL=INFO
export FSA_LOG_FILE=/var/log/fsa/app.log
```

---

## CLI Reference

### Command: `init`

Initialize FSA configuration file.

```bash
fsa init [--force]
```

**Options**:
- `--force`: Overwrite existing configuration

**Output**: Creates `.fsarc.json` with default settings

---

### Command: `list`

List all registered FSA modules.

```bash
fsa list [--verbose]
```

**Options**:
- `--verbose`: Show detailed module information

---

### Command: `health`

Check health of FSA modules.

```bash
fsa health [--module MODULE_NAME]
```

**Options**:
- `--module`: Check specific module (default: all)

---

### Command: `build`

Build and optionally execute a pipeline.

```bash
fsa build PIPELINE_NAME [--execute] [--inputs JSON]
```

**Options**:
- `--execute`: Execute pipeline after building
- `--inputs`: Pipeline inputs as JSON string

---

### Command: `validate`

Validate FSA configuration and health.

```bash
fsa validate [--health-check]
```

**Options**:
- `--health-check`: Include health checks for all modules

---

### Command: `optimize`

Analyze performance and suggest optimizations.

```bash
fsa optimize
```

---

### Command: `orchestrate`

Execute a complete FSA orchestration workflow.

```bash
fsa orchestrate PIPELINE_NAME [--inputs-file FILE]
```

**Options**:
- `--inputs-file`: Path to JSON file with inputs

---

## Performance Optimization

### Best Practices

1. **Enable Caching**
   ```python
   manager = FSAPipelineManager(enable_caching=True, cache_ttl_seconds=3600)
   ```

2. **Use Lazy Loading**
   ```python
   registry.register(name="module", version="1.0.0", lazy_load=True, ...)
   ```

3. **Parallel Execution**
   - Design pipelines with independent stages
   - Set appropriate `max_workers`

4. **Optimize Dependencies**
   - Minimize dependency chains
   - Use selective dependencies

5. **Monitor Performance**
   ```python
   metrics = manager.get_metrics()
   print(f"P95 latency: {metrics['my_pipeline']['p95_duration_ms']}ms")
   ```

### Performance Targets

| Metric | Target | Notes |
|--------|--------|-------|
| Registry lookup | < 1ms | Cached instances |
| Pipeline overhead | < 10ms | Per execution |
| Health check | < 5ms | Per module |
| Parallel speedup | 2-3x | With 4+ workers |

---

## Production Deployment

### Checklist

- [ ] Set `FSA_ENVIRONMENT=production`
- [ ] Configure Redis for caching
- [ ] Set up monitoring (Prometheus/Datadog)
- [ ] Enable authentication/authorization
- [ ] Configure rate limiting
- [ ] Set up logging to file/service
- [ ] Test error handling and retries
- [ ] Run load tests
- [ ] Configure resource limits
- [ ] Set up alerts for failures

### Production Configuration

```python
from agno.config import get_fsa_config

config = get_fsa_config(env="production")

# Verify critical settings
assert config.security.api_key_required
assert config.monitoring.enabled
assert config.rate_limiting.enabled
assert config.error_handling.circuit_breaker_enabled

# Apply configuration
config.apply_logging_config()
```

---

## Testing

### Run Tests

```bash
# Run all FSA tests
cd libs/agno
pytest tests/fsa/test_fsa_integration.py -v

# Run specific test class
pytest tests/fsa/test_fsa_integration.py::TestFSARegistry -v

# Run with coverage
pytest tests/fsa/ --cov=agno.fsa --cov-report=html
```

### Test Categories

- **Unit Tests**: Individual component testing
- **Integration Tests**: End-to-end workflow testing
- **Load Tests**: Concurrent execution testing
- **Memory Tests**: Leak detection
- **Benchmark Tests**: Performance validation

---

## Troubleshooting

### Common Issues

#### Issue: Module not registered

```
ValueError: FSA module 'my_module' is not registered
```

**Solution**: Register the module before using it
```python
registry.register(name="my_module", version="1.0.0", module_class=MyModule)
```

---

#### Issue: Circular dependency

```
ValueError: Circular dependency detected in FSA modules
```

**Solution**: Review dependency graph and remove circular references

```python
# Bad: A depends on B, B depends on A
registry.register("A", "1.0.0", dependencies=["B"], ...)
registry.register("B", "1.0.0", dependencies=["A"], ...)

# Good: A depends on B, B has no dependencies
registry.register("B", "1.0.0", dependencies=[], ...)
registry.register("A", "1.0.0", dependencies=["B"], ...)
```

---

#### Issue: Pipeline stage fails repeatedly

```
PipelineStageStatus.FAILED after max retries
```

**Solution**:
1. Check stage error: `stage_result.error`
2. Increase retry count if transient
3. Fix underlying issue in FSA module

---

#### Issue: Slow pipeline execution

**Solution**:
1. Check metrics: `manager.get_metrics()`
2. Enable parallel execution for independent stages
3. Increase `max_workers`
4. Enable caching
5. Profile FSA module execution

---

## Migration Guide

### From Standalone FSAs to Framework

#### Before (Standalone)

```python
# Direct instantiation
builder = MultiStepBuilder()
optimizer = RSIOptimizer()
orchestrator = MetaOrchestrator()

# Manual execution
result1 = builder.execute(data="test")
result2 = optimizer.execute(input=result1)
result3 = orchestrator.execute(input=result2)
```

#### After (Framework)

```python
from agno.fsa import FSARegistry, FSAPipeline, FSAPipelineManager

# Register modules
registry = FSARegistry()
registry.register("builder", "1.0.0", module_class=MultiStepBuilder)
registry.register("optimizer", "1.0.0", module_class=RSIOptimizer)
registry.register("orchestrator", "1.0.0", module_class=MetaOrchestrator)

# Create pipeline
pipeline = FSAPipeline(name="workflow", registry=registry)
pipeline.add_stage("build", fsa_module_name="builder")
pipeline.add_stage("optimize", fsa_module_name="optimizer", depends_on=["build"])
pipeline.add_stage("orchestrate", fsa_module_name="orchestrator", depends_on=["optimize"])

# Execute
manager = FSAPipelineManager(registry=registry)
result = manager.execute_pipeline(pipeline, initial_inputs={"data": "test"})
```

### Benefits of Migration

✅ **Automatic Dependency Management**: No manual passing of outputs
✅ **Error Handling**: Built-in retry and recovery
✅ **Monitoring**: Health checks and metrics
✅ **Caching**: Automatic result caching
✅ **Parallel Execution**: Where possible
✅ **Configuration**: Centralized settings

---

## Support

For issues, questions, or contributions:

- **GitHub Issues**: [agno repository issues](https://github.com/agno/agno/issues)
- **Documentation**: This guide
- **Tests**: See `tests/fsa/test_fsa_integration.py` for examples

---

## License

FSA Framework is part of the Agno project and follows the same license.

---

**Version**: 1.0.0
**Last Updated**: 2025
**Authors**: Agno Team

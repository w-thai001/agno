# 🎯 Service Orchestrator - Production-Ready Service Coordination

A sophisticated workflow for orchestrating multiple services with comprehensive dependency management, parallel execution, error handling, and rollback capabilities. Built on the Agno Framework for production-grade microservices orchestration.

## 📋 Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Core Concepts](#core-concepts)
- [Configuration](#configuration)
- [Advanced Usage](#advanced-usage)
- [API Reference](#api-reference)
- [Best Practices](#best-practices)
- [Examples](#examples)

## ✨ Features

### Core Capabilities

- **🔗 Dependency Management**: Intelligent resolution of service dependencies with topological sorting
- **⚡ Parallel Execution**: Automatic parallel execution of independent services for optimal performance
- **🔄 Automatic Rollback**: Comprehensive rollback capabilities with configurable strategies
- **💔 Circuit Breaker**: Built-in circuit breaker pattern for fault tolerance
- **❤️ Health Monitoring**: Service health checks and status tracking
- **⏱️ Timeout Management**: Per-service timeout configuration
- **🔁 Retry Logic**: Exponential backoff with jitter for failed operations
- **📊 Metrics & Reporting**: Comprehensive execution metrics and performance analysis

### Execution Modes

1. **Sequential**: Services execute one at a time in dependency order
2. **Parallel**: Maximum parallelization of independent services
3. **Hybrid**: Intelligent mix of parallel and sequential execution (recommended)

## 📦 Installation

```bash
pip install agno openai sqlalchemy
```

## 🚀 Quick Start

### Basic Example

```python
from cookbook.workflows.service_orchestrator import (
    ServiceOrchestrator,
    ServiceConfig,
    ExecutionMode,
)

# Define your service function
def my_service(deps: dict) -> dict:
    """Your service logic here."""
    return {"status": "success", "data": "result"}

# Configure the service
service = ServiceConfig(
    name="my_service",
    description="My example service",
    executor=my_service,
    dependencies=[],  # No dependencies
)

# Create orchestrator
orchestrator = ServiceOrchestrator(
    session_id="my-orchestration",
    debug_mode=True,
)

# Run orchestration
result = orchestrator.run(
    services=[service],
    execution_mode=ExecutionMode.HYBRID,
)

# Process results
for response in result:
    print(response.content)
```

## 🧠 Core Concepts

### Service Configuration

Each service is defined using `ServiceConfig`:

```python
ServiceConfig(
    name="database",                    # Unique identifier
    description="Database service",     # Human-readable description
    executor=database_init,             # Function to execute
    dependencies=["config_loader"],     # List of dependency names
    rollback_handler=database_rollback, # Optional rollback function
    health_check=database_health,       # Optional health check function
    critical=True,                      # Trigger rollback on failure
    timeout_config=TimeoutConfig(...),  # Timeout settings
    retry_config=RetryConfig(...),      # Retry settings
)
```

### Dependency Graph

Services are executed based on their dependency relationships:

```
config_loader
    ├── database
    │   ├── api_server
    │   └── worker_pool
    └── cache
        ├── api_server
        └── worker_pool
```

In this example:
- `config_loader` runs first (no dependencies)
- `database` and `cache` run in parallel (both depend only on `config_loader`)
- `api_server` and `worker_pool` run in parallel after both dependencies complete

### Circuit Breaker Pattern

The circuit breaker prevents cascading failures:

- **CLOSED**: Normal operation, requests pass through
- **OPEN**: Too many failures, requests fail fast without execution
- **HALF-OPEN**: Testing if service recovered, limited requests allowed

```python
CircuitBreakerConfig(
    failure_threshold=5,      # Open after 5 consecutive failures
    success_threshold=2,      # Close after 2 successes in half-open
    timeout=60,              # Wait 60s before entering half-open
    enabled=True,
)
```

### Rollback Strategy

Configure when and how rollbacks occur:

```python
RollbackStrategy(
    enabled=True,
    on_any_failure=False,                    # Only rollback critical failures
    critical_services=["database", "cache"], # Services that trigger rollback
    max_concurrent_rollbacks=5,              # Parallel rollback limit
)
```

## ⚙️ Configuration

### Timeout Configuration

```python
TimeoutConfig(
    execution_timeout=30,      # Maximum execution time (seconds)
    health_check_timeout=5,    # Health check timeout (seconds)
)
```

### Retry Configuration

```python
RetryConfig(
    max_attempts=3,           # Total attempts (including first)
    initial_delay=1.0,        # Initial backoff delay (seconds)
    max_delay=60.0,          # Maximum backoff delay (seconds)
    exponential_base=2.0,     # Backoff multiplier
    jitter=True,             # Add randomization to prevent thundering herd
)
```

### Health Check Configuration

```python
HealthCheckConfig(
    enabled=True,
    endpoint=None,                # Optional health endpoint URL
    interval=30,                  # Check interval (seconds)
    healthy_threshold=2,          # Successes to mark healthy
    unhealthy_threshold=3,        # Failures to mark unhealthy
)
```

## 🔧 Advanced Usage

### Complete Microservices Startup Example

```python
import time
from typing import Dict, Any

# Service implementations
def load_config(deps: Dict[str, Any]) -> Dict[str, Any]:
    """Load application configuration."""
    return {
        "db_host": "localhost",
        "db_port": 5432,
        "cache_host": "localhost",
        "cache_port": 6379,
    }

def init_database(deps: Dict[str, Any]) -> Dict[str, Any]:
    """Initialize database connection."""
    config = deps["config_loader"]
    return {
        "connection": f"postgresql://{config['db_host']}:{config['db_port']}",
        "status": "connected",
    }

def init_cache(deps: Dict[str, Any]) -> Dict[str, Any]:
    """Initialize cache connection."""
    config = deps["config_loader"]
    return {
        "connection": f"redis://{config['cache_host']}:{config['cache_port']}",
        "status": "connected",
    }

def start_api(deps: Dict[str, Any]) -> Dict[str, Any]:
    """Start API server."""
    db = deps["database"]
    cache = deps["cache"]
    return {
        "url": "http://localhost:8000",
        "status": "running",
        "db": db,
        "cache": cache,
    }

# Rollback handlers
def rollback_database(result: Dict[str, Any]) -> None:
    """Cleanup database connection."""
    print(f"Closing database connection: {result['connection']}")

def rollback_cache(result: Dict[str, Any]) -> None:
    """Cleanup cache connection."""
    print(f"Closing cache connection: {result['connection']}")

def rollback_api(result: Dict[str, Any]) -> None:
    """Stop API server."""
    print(f"Stopping API server: {result['url']}")

# Health checks
def check_database_health() -> bool:
    """Check if database is healthy."""
    # Implement actual health check logic
    return True

def check_cache_health() -> bool:
    """Check if cache is healthy."""
    # Implement actual health check logic
    return True

# Define services
services = [
    ServiceConfig(
        name="config_loader",
        description="Configuration loader",
        executor=load_config,
        dependencies=[],
        critical=True,
    ),
    ServiceConfig(
        name="database",
        description="PostgreSQL database",
        executor=init_database,
        dependencies=["config_loader"],
        rollback_handler=rollback_database,
        health_check=check_database_health,
        critical=True,
        retry_config=RetryConfig(max_attempts=3),
        timeout_config=TimeoutConfig(execution_timeout=10),
    ),
    ServiceConfig(
        name="cache",
        description="Redis cache",
        executor=init_cache,
        dependencies=["config_loader"],
        rollback_handler=rollback_cache,
        health_check=check_cache_health,
        critical=True,
        retry_config=RetryConfig(max_attempts=3),
    ),
    ServiceConfig(
        name="api_server",
        description="REST API server",
        executor=start_api,
        dependencies=["database", "cache"],
        rollback_handler=rollback_api,
        critical=True,
    ),
]

# Execute orchestration
orchestrator = ServiceOrchestrator(
    session_id="microservices-startup",
    debug_mode=True,
)

result = orchestrator.run(
    services=services,
    execution_mode=ExecutionMode.HYBRID,
    circuit_breaker_config=CircuitBreakerConfig(
        failure_threshold=3,
        timeout=60,
    ),
    rollback_strategy=RollbackStrategy(
        enabled=True,
        critical_services=["database", "cache", "api_server"],
    ),
)

for response in result:
    print(response.content)
```

### ETL Pipeline Example

```python
# ETL pipeline services
def extract_data(deps: Dict[str, Any]) -> Dict[str, Any]:
    """Extract data from source."""
    return {"records": 1000, "data": [...]}

def transform_data(deps: Dict[str, Any]) -> Dict[str, Any]:
    """Transform extracted data."""
    extracted = deps["extract"]
    return {"transformed_records": extracted["records"]}

def load_data(deps: Dict[str, Any]) -> Dict[str, Any]:
    """Load transformed data."""
    transformed = deps["transform"]
    return {"loaded_records": transformed["transformed_records"]}

services = [
    ServiceConfig(
        name="extract",
        executor=extract_data,
        timeout_config=TimeoutConfig(execution_timeout=300),
    ),
    ServiceConfig(
        name="transform",
        executor=transform_data,
        dependencies=["extract"],
        timeout_config=TimeoutConfig(execution_timeout=600),
    ),
    ServiceConfig(
        name="load",
        executor=load_data,
        dependencies=["transform"],
        critical=True,
    ),
]
```

## 📚 API Reference

### ServiceOrchestrator.run()

Execute the service orchestration workflow.

**Parameters:**
- `services: List[ServiceConfig]` - List of services to orchestrate
- `execution_mode: ExecutionMode` - Sequential, parallel, or hybrid (default: HYBRID)
- `circuit_breaker_config: Optional[CircuitBreakerConfig]` - Circuit breaker settings
- `health_check_config: Optional[HealthCheckConfig]` - Health check settings
- `rollback_strategy: Optional[RollbackStrategy]` - Rollback configuration
- `max_parallel_workers: int` - Maximum parallel workers (default: 5)

**Returns:**
- `Iterator[RunResponse]` - Stream of execution updates and final results

### ServiceOrchestrator.get_execution_history()

Get the complete execution history.

**Returns:**
- `List[ServiceResult]` - All service execution results

### ServiceOrchestrator.get_circuit_breaker_status()

Get current status of all circuit breakers.

**Returns:**
- `Dict[str, Dict[str, Any]]` - Circuit breaker status for each service

## 💡 Best Practices

### 1. Service Design

- **Single Responsibility**: Each service should have one clear purpose
- **Idempotency**: Services should be safe to retry
- **Timeout Awareness**: Set realistic timeouts based on expected execution time
- **Error Messages**: Provide clear, actionable error messages

### 2. Dependency Management

- **Minimize Dependencies**: Only declare essential dependencies
- **Avoid Cycles**: Ensure no circular dependencies
- **Loose Coupling**: Services should be as independent as possible

### 3. Error Handling

- **Graceful Degradation**: Non-critical services should not block critical ones
- **Rollback Handlers**: Implement rollback for services with side effects
- **Health Checks**: Implement meaningful health checks for critical services

### 4. Performance Optimization

- **Use Hybrid Mode**: Best balance of safety and performance
- **Tune Worker Pool**: Adjust `max_parallel_workers` based on resources
- **Monitor Metrics**: Track `parallel_efficiency` to optimize execution plan

### 5. Circuit Breaker Configuration

- **Failure Threshold**: Set based on acceptable error rate
- **Timeout Duration**: Balance between fast recovery and stability
- **Monitor Trips**: High trip counts indicate underlying issues

## 📊 Monitoring and Metrics

The orchestrator provides comprehensive metrics:

```python
execution_metrics = result.execution_metrics

print(f"Success Rate: {execution_metrics.successful_services / execution_metrics.total_services:.1%}")
print(f"Parallel Efficiency: {execution_metrics.parallel_efficiency:.1%}")
print(f"Total Retries: {execution_metrics.total_retries}")
print(f"Circuit Breaker Trips: {execution_metrics.circuit_breaker_trips}")
```

### Key Metrics

- **Success Rate**: Percentage of successfully completed services
- **Parallel Efficiency**: Benefit gained from parallel execution (0-100%)
- **Total Duration**: End-to-end orchestration time
- **Circuit Breaker Trips**: Number of circuit breaker activations
- **Total Retries**: Sum of all retry attempts

## 🎓 Examples

### Example 1: Simple Sequential Pipeline

```python
services = [
    ServiceConfig(name="step1", executor=step1_func),
    ServiceConfig(name="step2", executor=step2_func, dependencies=["step1"]),
    ServiceConfig(name="step3", executor=step3_func, dependencies=["step2"]),
]

orchestrator.run(services, execution_mode=ExecutionMode.SEQUENTIAL)
```

### Example 2: Parallel Independent Services

```python
services = [
    ServiceConfig(name="service_a", executor=func_a),
    ServiceConfig(name="service_b", executor=func_b),
    ServiceConfig(name="service_c", executor=func_c),
]

orchestrator.run(services, execution_mode=ExecutionMode.PARALLEL)
```

### Example 3: Diamond Dependency Pattern

```python
# Pattern:     A
#            /   \
#           B     C
#            \   /
#              D

services = [
    ServiceConfig(name="A", executor=func_a),
    ServiceConfig(name="B", executor=func_b, dependencies=["A"]),
    ServiceConfig(name="C", executor=func_c, dependencies=["A"]),
    ServiceConfig(name="D", executor=func_d, dependencies=["B", "C"]),
]

# Execution: A → (B, C in parallel) → D
orchestrator.run(services, execution_mode=ExecutionMode.HYBRID)
```

## 🐛 Troubleshooting

### Common Issues

**Issue**: Services timing out
- **Solution**: Increase `execution_timeout` in `TimeoutConfig`
- **Check**: Ensure service function is not blocking indefinitely

**Issue**: Circuit breaker constantly open
- **Solution**: Reduce `failure_threshold` or increase `timeout`
- **Check**: Investigate underlying service failures

**Issue**: Rollback not triggered
- **Solution**: Set `critical=True` on service or add to `critical_services` list
- **Check**: Ensure `rollback_strategy.enabled=True`

**Issue**: Poor parallel efficiency
- **Solution**: Review dependency graph, minimize dependencies
- **Check**: Ensure services are truly independent

## 📄 License

Part of the Agno Framework. See main repository for license details.

## 🤝 Contributing

Contributions welcome! Please follow the Agno Framework contribution guidelines.

## 📞 Support

For issues, questions, or contributions, please visit the Agno Framework repository.

---

Built with ❤️ using the Agno Framework

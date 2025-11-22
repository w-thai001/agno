# MLA-FSA Framework

**Meta-Learning Architecture Financial Services Agent Framework**

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)]()
[![Coverage](https://img.shields.io/badge/coverage-85%25-green.svg)]()

A comprehensive framework for building, testing, orchestrating, and deploying intelligent Financial Services Agents (FSAs) with production-ready features including parallel execution, fault tolerance, real-time monitoring, and hot-swapping capabilities.

---

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [FSA Components](#fsa-components)
- [Configuration](#configuration)
- [API Documentation](#api-documentation)
- [CLI Reference](#cli-reference)
- [Examples](#examples)
- [Testing](#testing)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

---

## Features

### Core Capabilities

- **Parallel Execution Engine**: Asyncio-based concurrent FSA execution with configurable limits
- **Fault Tolerance**: Circuit breaker pattern with exponential backoff retry logic
- **Real-time Monitoring**: WebSocket server for live metrics and health monitoring
- **Hot-Swapping**: Zero-downtime FSA updates with version management and rollback
- **Performance Optimization**: Automatic bottleneck detection and optimization recommendations
- **Test Suite Generation**: Automated pytest-compatible test generation from FSA specifications

### FSA Types Included

| FSA | Description | Use Case |
|-----|-------------|----------|
| **FSA01** | Data Validation Agent | Input validation and schema enforcement |
| **FSA02** | Market Analysis Agent | Financial market data analysis |
| **FSA03** | Risk Assessment Agent | Risk scoring and evaluation |
| **FSA04** | Portfolio Optimization Agent | Asset allocation optimization |
| **FSA05** | Compliance Checker Agent | Regulatory compliance verification |
| **FSA06** | Report Generation Agent | Automated financial reporting |
| **FSA07** | Alert Management Agent | Real-time alerting and notifications |
| **FSA08** | Data Aggregation Agent | Multi-source data consolidation |
| **FSA09** | Prediction Engine Agent | ML-based forecasting |
| **FSA10** | Test Suite Generator | Automated test generation |

---

## Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager
- Git (for development installation)

### Standard Installation

```bash
# Install from PyPI (when published)
pip install mla-fsa-framework

# Or install from source
git clone https://github.com/agno-agi/agno.git
cd agno/libs/agno/mla_fsa_framework
pip install .
```

### Development Installation

```bash
# Clone the repository
git clone https://github.com/agno-agi/agno.git
cd agno/libs/agno/mla_fsa_framework

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or
.\venv\Scripts\Activate  # Windows PowerShell

# Install in development mode with all dependencies
pip install -e ".[dev]"
```

### Installation Options

```bash
# Core only (minimal dependencies)
pip install mla-fsa-framework

# With testing support
pip install "mla-fsa-framework[test]"

# With monitoring capabilities
pip install "mla-fsa-framework[monitoring]"

# With financial data integrations
pip install "mla-fsa-framework[finance]"

# With AI/ML integrations
pip install "mla-fsa-framework[ai]"

# All features
pip install "mla-fsa-framework[all]"
```

### Windows PowerShell Installation

```powershell
# Run the automated installer
.\install.ps1
```

---

## Quick Start

### 1. Basic FSA Execution

```python
import asyncio
from agno.fsa_integration_layer import FSAIntegrationLayer, FSAConfig

async def main():
    # Initialize the integration layer
    layer = FSAIntegrationLayer(max_concurrency=10)
    await layer.initialize()

    # Define FSA configuration
    config = FSAConfig(
        name="market_analyzer",
        module_path="path/to/market_fsa.py",
        class_name="MarketAnalysisFSA",
        timeout=30.0,
        max_retries=3,
    )

    # Load the FSA
    await layer.load_fsa(config)

    # Execute with input data
    result = await layer.execute(
        "market_analyzer",
        {"symbol": "AAPL", "period": "1y"}
    )

    print(f"Result: {result}")

    # Shutdown gracefully
    await layer.shutdown()

asyncio.run(main())
```

### 2. Parallel Execution

```python
import asyncio
from agno.fsa_integration_layer import FSAIntegrationLayer

async def main():
    layer = FSAIntegrationLayer(max_concurrency=20)
    await layer.initialize()

    # Load multiple FSAs
    # ... (load FSAs)

    # Execute multiple FSAs in parallel
    tasks = [
        ("market_analyzer", {"symbol": "AAPL"}),
        ("market_analyzer", {"symbol": "GOOGL"}),
        ("market_analyzer", {"symbol": "MSFT"}),
        ("risk_assessor", {"portfolio_id": "P001"}),
    ]

    results = await layer.execute_parallel(tasks, timeout=60.0)

    for task, result in zip(tasks, results):
        print(f"{task[0]}: {result}")

asyncio.run(main())
```

### 3. Workflow Orchestration

```python
from agno.fsa_integration_layer import (
    FSAIntegrationLayer,
    WorkflowDefinition,
    WorkflowStep,
)

async def main():
    layer = FSAIntegrationLayer()
    await layer.initialize()

    # Define a workflow
    workflow = WorkflowDefinition(
        name="financial_analysis_pipeline",
        description="Complete financial analysis workflow",
        steps=[
            WorkflowStep(
                name="fetch_data",
                fsa_name="data_aggregator",
                input_mapping={"symbols": "input.symbols"},
            ),
            WorkflowStep(
                name="analyze_market",
                fsa_name="market_analyzer",
                input_mapping={"data": "fetch_data.result"},
                parallel_group="analysis",
            ),
            WorkflowStep(
                name="assess_risk",
                fsa_name="risk_assessor",
                input_mapping={"data": "fetch_data.result"},
                parallel_group="analysis",
            ),
            WorkflowStep(
                name="generate_report",
                fsa_name="report_generator",
                input_mapping={
                    "market_analysis": "analyze_market.result",
                    "risk_assessment": "assess_risk.result",
                },
            ),
        ],
    )

    # Register and execute
    layer.register_workflow(workflow)

    result = await layer.execute_workflow(
        "financial_analysis_pipeline",
        {"symbols": ["AAPL", "GOOGL", "MSFT"]}
    )

    print(result)

asyncio.run(main())
```

### 4. Test Suite Generation

```bash
# Generate tests for an FSA module
fsa-test-gen --module path/to/fsa.py --output tests/generated/

# Generate with all test types
fsa-test-gen --module path/to/fsa.py --output tests/ --all

# Generate and execute tests
fsa-test-gen --module path/to/fsa.py --output tests/ --execute --report html
```

```python
from agno.fsa10_test_suite_generator import FSATestSuiteGenerator

# Initialize generator
generator = FSATestSuiteGenerator(
    output_dir="tests/generated",
    coverage_threshold=80.0,
)

# Parse FSA module
spec = generator.parse_fsa_spec("path/to/market_fsa.py")

# Generate tests
unit_tests = generator.generate_unit_tests(spec)
integration_tests = generator.generate_integration_tests(spec)
edge_cases = generator.identify_edge_cases(spec)

# Write test file
generator.write_test_file(unit_tests, "tests/test_market_fsa.py", spec)

# Execute and get coverage
report = generator.execute_tests("tests/")
print(f"Coverage: {report.coverage.coverage_percentage}%")
```

### 5. Start Monitoring Server

```bash
# Start WebSocket monitoring server
mla-fsa server --host 0.0.0.0 --port 8765

# Generate static HTML dashboard
mla-fsa dashboard --output dashboard.html
```

```python
async def main():
    layer = FSAIntegrationLayer(enable_monitoring=True)
    await layer.initialize()

    # Start monitoring server
    await layer.start_monitoring(host="0.0.0.0", port=8765)

    print("Monitoring server running on ws://0.0.0.0:8765")

    # Keep running
    await asyncio.Event().wait()
```

---

## FSA Components

### FSA10 Test Suite Generator

Automated test generation for FSA modules.

```python
from agno.fsa10_test_suite_generator import FSATestSuiteGenerator

generator = FSATestSuiteGenerator()

# Parse module specifications
spec = generator.parse_fsa_spec("module.py")

# Generate different test types
unit_tests = generator.generate_unit_tests(spec)
integration_tests = generator.generate_integration_tests(spec)
edge_cases = generator.identify_edge_cases(spec)

# Analyze coverage
coverage = generator.analyze_coverage("tests/")

# Execute tests with reporting
report = generator.execute_tests("tests/", report_format="both")
```

### FSA Integration Layer

Production orchestration system.

```python
from agno.fsa_integration_layer import (
    FSAIntegrationLayer,
    FSAConfig,
    ParallelExecutor,
    ErrorRecoveryManager,
    CircuitBreaker,
    HotSwapManager,
    PerformanceOptimizer,
    MonitoringDashboard,
)

# Full initialization
layer = FSAIntegrationLayer(
    max_concurrency=10,
    enable_monitoring=True,
    enable_optimization=True,
)

# Access individual components
executor = layer.executor
error_recovery = layer.error_recovery
hot_swap = layer.hot_swap_manager
optimizer = layer.optimizer
monitoring = layer.monitoring
```

---

## Configuration

### Default Configuration (config.json)

```json
{
  "framework": {
    "name": "MLA-FSA Framework",
    "version": "1.0.0"
  },
  "execution": {
    "max_concurrency": 10,
    "default_timeout": 60.0
  },
  "error_recovery": {
    "max_retries": 3,
    "base_delay": 1.0,
    "max_delay": 60.0,
    "exponential_base": 2.0
  },
  "circuit_breaker": {
    "failure_threshold": 5,
    "recovery_timeout": 30.0
  },
  "monitoring": {
    "enabled": true,
    "websocket_port": 8765,
    "metrics_history_size": 1000
  },
  "logging": {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  }
}
```

### Environment Variables

```bash
# Core settings
MLA_FSA_LOG_LEVEL=INFO
MLA_FSA_MAX_CONCURRENCY=10
MLA_FSA_DEFAULT_TIMEOUT=60

# Monitoring
MLA_FSA_MONITORING_ENABLED=true
MLA_FSA_WEBSOCKET_PORT=8765

# Error recovery
MLA_FSA_MAX_RETRIES=3
MLA_FSA_CIRCUIT_THRESHOLD=5
```

---

## API Documentation

### FSAIntegrationLayer

Main orchestration class.

| Method | Description |
|--------|-------------|
| `initialize()` | Initialize the integration layer |
| `load_fsa(config)` | Load an FSA from configuration |
| `unload_fsa(name)` | Unload an FSA |
| `execute(fsa_name, input_data)` | Execute a single FSA |
| `execute_parallel(tasks)` | Execute multiple FSAs in parallel |
| `execute_workflow(name, input)` | Execute a registered workflow |
| `hot_swap(name, config)` | Hot-swap an FSA implementation |
| `start_monitoring(port)` | Start WebSocket monitoring server |
| `get_health()` | Get system health status |
| `get_statistics()` | Get comprehensive statistics |
| `shutdown()` | Graceful shutdown |

### FSATestSuiteGenerator

Test generation class.

| Method | Description |
|--------|-------------|
| `parse_fsa_spec(path)` | Parse FSA module specifications |
| `generate_unit_tests(spec)` | Generate unit tests |
| `generate_integration_tests(spec)` | Generate integration tests |
| `identify_edge_cases(spec)` | Identify edge cases |
| `analyze_coverage(path)` | Analyze test coverage |
| `execute_tests(path)` | Execute tests with reporting |

### ErrorRecoveryManager

Fault tolerance management.

| Method | Description |
|--------|-------------|
| `execute_with_retry(func, context)` | Execute with retry logic |
| `get_circuit_breaker(name)` | Get/create circuit breaker |
| `register_error_handler(type, handler)` | Register error handler |
| `should_retry(exception)` | Check if exception is retryable |

---

## CLI Reference

### Main CLI (mla-fsa)

```bash
# Start monitoring server
mla-fsa server [--host HOST] [--port PORT] [--concurrency N]

# Generate dashboard
mla-fsa dashboard [--output FILE]

# Health check
mla-fsa health [--json]

# View statistics
mla-fsa stats [--json]

# Load FSA
mla-fsa load --module PATH --class NAME [--name ALIAS]

# Execute FSA
mla-fsa execute FSA_NAME [--input JSON] [--timeout SECONDS]
```

### Test Generator CLI (fsa-test-gen)

```bash
# Generate tests
fsa-test-gen --module PATH --output DIR [--unit] [--integration] [--edge-cases] [--all]

# Execute generated tests
fsa-test-gen --module PATH --output DIR --execute [--report json|html|both]

# Coverage analysis only
fsa-test-gen --coverage PATH [--source SRC] [--coverage-threshold PCT]
```

---

## Examples

### Creating a Custom FSA

```python
from agno.fsa_integration_layer import AbstractFSA, ExecutionContext, FSAConfig

class MyCustomFSA(AbstractFSA):
    """Custom FSA implementation."""

    @property
    def name(self) -> str:
        return "my_custom_fsa"

    async def execute(self, context: ExecutionContext) -> dict:
        """Execute the FSA logic."""
        input_data = context.input_data

        # Your business logic here
        result = await self._process(input_data)

        return {"status": "success", "result": result}

    async def validate_input(self, data: dict) -> bool:
        """Validate input data."""
        required_fields = ["field1", "field2"]
        return all(field in data for field in required_fields)

    async def _process(self, data: dict) -> any:
        """Internal processing logic."""
        # Implementation here
        pass
```

### WebSocket Client for Monitoring

```javascript
// JavaScript WebSocket client
const ws = new WebSocket('ws://localhost:8765');

ws.onopen = () => {
    console.log('Connected to monitoring server');
    ws.send(JSON.stringify({ type: 'get_dashboard' }));
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Received:', data);

    if (data.type === 'event') {
        console.log('Event:', data.event);
    } else if (data.type === 'alert') {
        console.log('Alert:', data.alert);
    }
};
```

---

## Testing

### Run Tests

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=agno --cov-report=html

# Run specific test file
pytest tests/test_fsa_integration.py -v

# Run with parallel execution
pytest tests/ -n auto
```

### Generate Test Suite

```bash
# Generate tests for your FSA
fsa-test-gen --module my_fsa.py --output tests/generated/ --all --execute
```

---

## Monitoring

### WebSocket Events

| Event Type | Description |
|------------|-------------|
| `fsa_load` | FSA loaded |
| `fsa_unload` | FSA unloaded |
| `fsa_swap` | FSA hot-swapped |
| `workflow_started` | Workflow execution started |
| `workflow_completed` | Workflow execution completed |
| `workflow_failed` | Workflow execution failed |
| `alert` | System alert triggered |

### Dashboard Metrics

- Execution count and error rates
- Average execution time
- Active tasks count
- Circuit breaker states
- Memory and CPU usage
- Per-FSA health status

---

## Troubleshooting

### Common Issues

#### 1. WebSocket Connection Failed

```
Error: WebSocket connection failed
```

**Solution:**
```bash
# Ensure websockets is installed
pip install websockets

# Check if port is available
netstat -an | grep 8765
```

#### 2. Circuit Breaker Open

```
Error: Circuit breaker 'fsa_name' is open
```

**Solution:**
- Wait for recovery timeout (default: 30s)
- Check FSA health and fix underlying issues
- Manually reset: `layer.error_recovery.get_circuit_breaker("fsa_name").reset()`

#### 3. Timeout Errors

```
Error: Execution timed out after 60s
```

**Solution:**
- Increase timeout in FSA config
- Optimize FSA logic
- Check external service latency

#### 4. Import Errors

```
Error: Cannot load module
```

**Solution:**
- Verify module path is correct
- Check Python path includes module directory
- Ensure all dependencies are installed

### Debug Mode

```bash
# Enable verbose logging
mla-fsa server --verbose

# Or set environment variable
export MLA_FSA_LOG_LEVEL=DEBUG
```

---

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `pytest tests/`
5. Submit a pull request

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Support

- **Documentation**: [https://docs.agno.dev/fsa-framework](https://docs.agno.dev/fsa-framework)
- **Issues**: [GitHub Issues](https://github.com/agno-agi/agno/issues)
- **Discussions**: [GitHub Discussions](https://github.com/agno-agi/agno/discussions)

---

Made with by the Agno Team

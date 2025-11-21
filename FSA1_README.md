# FSA-1: Meta-Pattern Analyzer

A production-ready Python implementation for analyzing execution logs to identify top-performing patterns and generate optimization recommendations.

## Overview

FSA-1 Meta-Pattern Analyzer uses PowerShell subprocesses (with fallback to bash on Unix systems) for file operations to collect and analyze execution logs. It provides comprehensive statistical analysis of pattern performance including LQ scores, success rates, and execution times.

## Features

- **PowerShell-First Architecture**: Uses PowerShell `Get-ChildItem` and `Get-Content` for file operations
- **Cross-Platform**: Automatic fallback to bash commands on systems without PowerShell
- **Statistical Analysis**: Calculates mean, max, min, and standard deviation for performance metrics
- **Pattern Grouping**: Automatically groups logs by pattern_id
- **Smart Recommendations**: Generates prioritized optimization recommendations
- **Comprehensive Error Handling**: Production-ready with timeout handling and detailed logging
- **Type-Safe**: Full type hints for better IDE support and code quality

## Requirements

- Python 3.7+
- PowerShell or PowerShell Core (optional, falls back to bash on Unix)
- Standard library only (no external dependencies)

## Installation

No installation required! The script is self-contained with only standard library dependencies.

```bash
# Make the script executable
chmod +x fsa1_meta_pattern_analyzer.py
```

## Usage

### Basic Usage

Analyze all logs in the default `./logs` directory:

```bash
python3 fsa1_meta_pattern_analyzer.py
```

### Advanced Options

```bash
# Specify custom logs directory
python3 fsa1_meta_pattern_analyzer.py --logs-dir /path/to/logs

# Filter by specific pattern ID
python3 fsa1_meta_pattern_analyzer.py --pattern-id pattern_001

# Save report to file
python3 fsa1_meta_pattern_analyzer.py --output report.json

# Enable verbose logging
python3 fsa1_meta_pattern_analyzer.py --verbose

# Set custom timeout for file operations (in seconds)
python3 fsa1_meta_pattern_analyzer.py --timeout 60

# Combine options
python3 fsa1_meta_pattern_analyzer.py --logs-dir ./logs --pattern-id pattern_001 --output report.json --verbose
```

### Command-Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--logs-dir` | Directory containing execution logs | `./logs` |
| `--pattern-id` | Filter analysis by specific pattern ID | None (all patterns) |
| `--output` | Output file path for JSON report | stdout |
| `--timeout` | Timeout for file operations in seconds | 30 |
| `--verbose` | Enable verbose logging | False |

## Log File Format

The analyzer expects JSON log files with the following structure:

```json
{
  "pattern_id": "pattern_001",
  "lq_score": 0.92,
  "success": true,
  "execution_time": 1.45,
  "timestamp": "2024-11-21T10:15:30Z",
  "metadata": {
    "model": "gpt-4",
    "task_type": "classification"
  }
}
```

### Required Fields

- `pattern_id`: String identifier for the pattern
- `lq_score` (or `quality_score`): Numeric quality score (0.0 to 1.0)
- `success` (or `status`): Boolean or "success"/"failure" string
- `execution_time` (or `duration`): Numeric execution time in seconds

### Optional Fields

- `timestamp`: ISO 8601 timestamp
- `metadata`: Additional metadata dictionary

## Output Format

The analyzer generates a comprehensive JSON report with the following structure:

```json
{
  "status": "completed",
  "timestamp": "2025-11-21T11:51:42.041677",
  "analysis_duration_seconds": 0.08,
  "logs_analyzed": 6,
  "patterns_found": 3,
  "statistics": {
    "pattern_001": {
      "pattern_id": "pattern_001",
      "execution_count": 3,
      "mean_lq_score": 0.9167,
      "max_lq_score": 0.95,
      "min_lq_score": 0.88,
      "std_dev_lq_score": 0.0351,
      "success_rate": 100.0,
      "total_successes": 3,
      "total_failures": 0,
      "avg_execution_time": 1.45
    }
  },
  "recommendations": [
    {
      "priority": "HIGH",
      "pattern_id": "pattern_001",
      "recommendation_type": "PROMOTE",
      "description": "Pattern 'pattern_001' shows excellent performance...",
      "expected_impact": "High - Can improve overall system quality by 15-25%",
      "metrics": {
        "rank": 1,
        "mean_lq_score": 0.9167,
        "success_rate": 100.0,
        "execution_count": 3,
        "consistency": 0.9617
      }
    }
  ],
  "summary": {
    "top_pattern": "pattern_001",
    "average_success_rate": 66.67,
    "total_executions": 6,
    "high_priority_recommendations": 2
  }
}
```

## Recommendation Types

The analyzer generates four types of recommendations:

### 1. PROMOTE (High Priority)
Patterns with excellent performance (LQ > 0.7) that should be used as templates.

### 2. INVESTIGATE (Medium Priority)
Patterns with below-average performance (LQ < 0.5) that need review or refactoring.

### 3. STABILIZE (Medium Priority)
Patterns with high variance (std dev > 0.2) that need consistency improvements.

### 4. SCALE (Low Priority)
High-performing patterns with limited usage that could be applied more broadly.

## Architecture

### Core Components

#### 1. PowerShellExecutor
Handles subprocess execution with intelligent fallback:
- Primary: PowerShell `Get-ChildItem` and `Get-Content`
- Fallback: Bash `find` and `cat` commands
- Includes timeout handling and comprehensive error management

#### 2. FSA1MetaPatternAnalyzer
Main analyzer class with three key methods:

**collect_execution_logs(pattern_id=None)**
- Uses PowerShell to discover and read JSON log files
- Supports optional filtering by pattern_id
- Returns parsed log entries as dictionaries

**analyze_pattern_performance(logs)**
- Groups logs by pattern_id
- Calculates statistical metrics per pattern
- Returns PatternStatistics objects

**generate_recommendations(analysis)**
- Analyzes pattern statistics
- Generates prioritized recommendations
- Returns sorted list of Recommendation objects

**run_analysis(pattern_id=None)**
- Orchestrates the complete pipeline
- Handles errors and generates final report
- Returns comprehensive JSON report

### Data Models

**PatternStatistics**: Statistical metrics for pattern performance
**Recommendation**: Optimization recommendation with priority and impact

## Error Handling

The analyzer includes comprehensive error handling:

- **File Not Found**: Clear error messages for missing directories
- **Invalid JSON**: Skips invalid files with detailed logging
- **Timeouts**: Configurable timeout for subprocess operations
- **PowerShell Unavailable**: Automatic fallback to bash commands
- **Graceful Degradation**: Continues processing even if some files fail

## Performance

- Typical analysis of 100 log files: < 1 second
- Memory efficient: Streams file reads
- Concurrent-safe: No shared state between analyses

## Testing

The repository includes sample log files for testing:

```bash
# Run with sample logs
python3 fsa1_meta_pattern_analyzer.py --logs-dir ./logs --verbose
```

Sample logs are located in `./logs/` directory with patterns for testing all recommendation types.

## Logging

The analyzer uses Python's standard logging module:

- **INFO**: Progress and completion messages
- **WARNING**: Non-fatal issues (PowerShell fallback, missing data)
- **ERROR**: Fatal errors with stack traces
- **DEBUG**: Detailed subprocess commands and file operations (with --verbose)

## Exit Codes

- **0**: Analysis completed successfully
- **1**: Analysis failed with errors

## Examples

### Example 1: Quick Analysis

```bash
python3 fsa1_meta_pattern_analyzer.py
```

### Example 2: Detailed Report for Specific Pattern

```bash
python3 fsa1_meta_pattern_analyzer.py \
  --pattern-id pattern_001 \
  --output pattern_001_report.json \
  --verbose
```

### Example 3: Production Analysis

```bash
python3 fsa1_meta_pattern_analyzer.py \
  --logs-dir /var/log/execution_logs \
  --timeout 60 \
  --output /reports/fsa1_$(date +%Y%m%d).json
```

## Integration

### As a Python Module

```python
from fsa1_meta_pattern_analyzer import FSA1MetaPatternAnalyzer

# Initialize analyzer
analyzer = FSA1MetaPatternAnalyzer(logs_dir="./logs", timeout=30)

# Run analysis
report = analyzer.run_analysis(pattern_id=None)

# Access results
print(f"Analyzed {report['logs_analyzed']} logs")
print(f"Found {report['patterns_found']} patterns")
print(f"Top pattern: {report['summary']['top_pattern']}")
```

### In CI/CD Pipeline

```yaml
# Example GitHub Actions workflow
- name: Analyze Pattern Performance
  run: |
    python3 fsa1_meta_pattern_analyzer.py \
      --logs-dir ./execution_logs \
      --output artifacts/fsa1_report.json

- name: Upload Report
  uses: actions/upload-artifact@v2
  with:
    name: fsa1-report
    path: artifacts/fsa1_report.json
```

## Troubleshooting

### PowerShell Not Found
The analyzer automatically falls back to bash commands. No action required unless you specifically need PowerShell.

### No Logs Found
Ensure the `--logs-dir` points to a directory containing `.json` files with the expected format.

### Timeout Errors
Increase the timeout: `--timeout 60` (default is 30 seconds)

### Invalid JSON
Check log files for syntax errors. The analyzer logs which files it skips.

## License

MIT License - See LICENSE file for details

## Author

Agno Team

## Version

1.0.0 (2025-11-21)

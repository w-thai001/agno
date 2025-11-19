# FSA Meta-Analyzer

A specialized FSA (Finite State Automaton) for analyzing, validating, and improving other FSAs in the Agno MLA (Multi-Layer Agentic) framework.

## Overview

The FSA Meta-Analyzer provides comprehensive analysis of Agno workflows, treating them as finite state automatons and extracting deep insights about their structure, quality, performance, and optimization opportunities.

## Features

### 1. **Static Structure Analysis** (`static_analyzer.py`)
- Parses workflow `run()` methods using Python AST
- Extracts FSA structure: states, transitions, entry/exit points
- Identifies control flow patterns (if/else, loops, try/except)
- Tracks agent calls and variable usage per state
- Calculates cyclomatic complexity

### 2. **Validation** (`validator.py`)
- Validates FSA correctness and best practices
- Checks state reachability from entry point
- Detects dead code and unreachable states
- Validates transitions between states
- Ensures proper error handling coverage
- Identifies potential infinite loops

### 3. **Performance Profiling** (`profiler.py`)
- Static performance prediction based on structure
- Identifies bottleneck states
- Analyzes hot paths (frequently executed sequences)
- Provides performance optimization recommendations
- Runtime profiling support (for instrumented executions)

### 4. **Quality Metrics** (`quality_metrics.py`)
- Overall quality score (0-100) with letter grade (A-F)
- Maintainability index
- Reliability score
- Efficiency score
- Testability score
- Cohesion and coupling metrics
- Cognitive complexity analysis
- Antipattern detection

### 5. **Pattern Detection** (`pattern_analyzer.py`)
Detects design patterns:
- Pipeline (linear sequences)
- Scatter-Gather (fan-out/fan-in)
- Retry Loop
- Cache-Aside
- Guard Clauses
- Error Handlers

Detects antipatterns:
- God State (too many responsibilities)
- Spaghetti Flow (excessive branching)
- Lava Flow (dead code)

### 6. **Dependency Analysis** (`dependency_analyzer.py`)
- Builds dependency graphs between workflows, agents, and states
- Detects circular dependencies
- Calculates coupling scores
- Identifies highly coupled components
- Generates visualization (Graphviz DOT, Mermaid)
- Topological layer analysis

### 7. **Optimization Recommendations** (`optimizer.py`)
- Generates prioritized optimization recommendations
- Categorizes by priority (critical, high, medium, low)
- Identifies "quick wins" (high impact, low effort)
- Provides code examples for improvements
- Calculates overall health score
- Generates executive summaries

## Installation

The FSA Meta-Analyzer is built into Agno. No additional installation required.

```python
from agno.workflows.fsa_meta_analyzer import FSAMetaAnalyzer
```

## Quick Start

### Analyze a Single Workflow

```python
from agno.workflows.fsa_meta_analyzer import FSAMetaAnalyzer
from my_workflows import MyWorkflow

# Create analyzer
analyzer = FSAMetaAnalyzer(session_id="analysis_1")

# Run analysis
responses = analyzer.run(
    workflow_class=MyWorkflow,
    include_performance=True,
    include_patterns=True,
    include_dependencies=True,
    include_optimization=True,
)

# Print results
for response in responses:
    print(response.content)

# Get detailed report
reports = analyzer.get_cached_reports()
report = reports[0]

print(f"Quality Grade: {report.quality_metrics.quality_grade}")
print(f"Health Score: {report.optimization_plan.health_score}/100")
```

### Analyze Multiple Workflows

```python
from agno.workflows.fsa_meta_analyzer import FSAMetaAnalyzer
from my_workflows import WorkflowA, WorkflowB, WorkflowC

analyzer = FSAMetaAnalyzer()

responses = analyzer.run(
    workflow_classes=[WorkflowA, WorkflowB, WorkflowC],
    include_patterns=True,
    include_dependencies=True,
    generate_visualizations=True,
)

for response in responses:
    print(response.content)
```

### Use Individual Components

```python
from agno.workflows.fsa_meta_analyzer import (
    FSAStaticAnalyzer,
    FSAValidator,
    QualityMetricsCalculator,
    FSAPerformanceProfiler,
    FSAPatternDetector,
    DependencyAnalyzer,
    FSAOptimizer,
)

# 1. Analyze structure
static_analyzer = FSAStaticAnalyzer()
fsa_structure = static_analyzer.analyze_workflow(MyWorkflow)

# 2. Validate
validator = FSAValidator()
validation_report = validator.validate(fsa_structure)

# 3. Calculate quality
quality_calc = QualityMetricsCalculator()
metrics = quality_calc.calculate_metrics(fsa_structure, validation_report)

# 4. Performance analysis
profiler = FSAPerformanceProfiler()
perf_analysis = profiler.analyze_performance_characteristics(fsa_structure)

# 5. Detect patterns
pattern_detector = FSAPatternDetector()
pattern_report = pattern_detector.analyze_patterns(fsa_structure)

# 6. Analyze dependencies
dep_analyzer = DependencyAnalyzer()
dep_report = dep_analyzer.analyze_fsa_dependencies(fsa_structure)

# 7. Generate recommendations
optimizer = FSAOptimizer()
opt_plan = optimizer.generate_optimization_plan(
    fsa=fsa_structure,
    validation_report=validation_report,
    quality_metrics=metrics,
    performance_analysis=perf_analysis,
    pattern_report=pattern_report,
    dependency_report=dep_report,
)

print(f"Health: {opt_plan.overall_health}")
print(f"Recommendations: {len(opt_plan.recommendations)}")
```

## Output Example

```
================================================================================
Analyzing: BlogPostGenerator
================================================================================

## Overview

Structure:
  - States: 12
  - Transitions: 15
  - Agents: 2
  - Cyclomatic Complexity: 8

## Validation Results

Status: ✓ VALID
  - Critical Issues: 0
  - Errors: 0
  - Warnings: 2
  - Info: 3

## Quality Metrics

Overall Quality: Grade B (82/100)

Breakdown:
  - Maintainability: 78/100
  - Reliability: 85/100
  - Efficiency: 82/100
  - Testability: 75/100
  - Best Practices: 90/100

## Performance Analysis

Performance Score: 75/100

Predicted Slowest States:
  - scrape_articles: complexity 45.0
  - write_blog_post: complexity 30.0

## Optimization Plan

Health Status: GOOD (82/100)
Total Recommendations: 7

Quick Wins (2):
  - [HIGH] Add Type Annotations
    Type annotation coverage is 60%. Add type hints to improve...
  - [MEDIUM] Optimize Bottleneck State: scrape_articles
    State identified as performance bottleneck...

Long-term Improvements (3):
  - [HIGH] Improve Error Handling Coverage
    Impact: Reduces failures and improves user experience
    Effort: medium
```

## Architecture

```
fsa_meta_analyzer/
├── __init__.py              # Package exports
├── meta_analyzer.py         # Main workflow orchestrator
├── static_analyzer.py       # AST-based structure extraction
├── validator.py             # Validation engine
├── profiler.py              # Performance profiling
├── quality_metrics.py       # Quality scoring
├── pattern_analyzer.py      # Pattern detection
├── dependency_analyzer.py   # Dependency graph analysis
└── optimizer.py             # Optimization recommendations
```

## Use Cases

### 1. **CI/CD Integration**
Add FSA analysis to your CI pipeline to enforce quality standards:

```python
analyzer = FSAMetaAnalyzer()
responses = list(analyzer.run(workflow_class=MyWorkflow))
reports = analyzer.get_cached_reports()

if reports[0].validation_report.critical_count > 0:
    raise Exception("Critical issues found in workflow")

if reports[0].quality_metrics.quality_grade == 'F':
    raise Exception("Workflow quality below minimum threshold")
```

### 2. **Pre-deployment Checks**
Validate workflows before deployment:

```python
from agno.workflows.fsa_meta_analyzer import FSAValidator, FSAStaticAnalyzer

def validate_workflow(workflow_class):
    analyzer = FSAStaticAnalyzer()
    validator = FSAValidator()

    fsa = analyzer.analyze_workflow(workflow_class)
    report = validator.validate(fsa)

    if not report.is_valid:
        for issue in report.issues:
            if issue.severity.value == 'critical':
                print(f"CRITICAL: {issue.message}")
        return False
    return True
```

### 3. **Documentation Generation**
Auto-generate workflow documentation:

```python
analyzer = FSAMetaAnalyzer()
list(analyzer.run(workflow_class=MyWorkflow))
reports = analyzer.get_cached_reports()

analyzer.export_report(reports[0], "docs/workflow_analysis.json")
```

### 4. **Performance Optimization**
Identify and fix performance bottlenecks:

```python
from agno.workflows.fsa_meta_analyzer import FSAPerformanceProfiler

profiler = FSAPerformanceProfiler()
fsa = FSAStaticAnalyzer().analyze_workflow(MyWorkflow)
perf = profiler.analyze_performance_characteristics(fsa)

for state in perf.profile.bottleneck_states:
    print(f"Optimize: {state}")

for recommendation in perf.recommendations:
    print(f"- {recommendation}")
```

## Advanced Features

### Dependency Graph Visualization

```python
from agno.workflows.fsa_meta_analyzer import DependencyAnalyzer

analyzer = DependencyAnalyzer()
dep_report = analyzer.analyze_multiple_fsas([WorkflowA, WorkflowB])

# Generate Mermaid diagram
mermaid = analyzer.generate_mermaid_diagram(dep_report.graph)
print(mermaid)

# Generate Graphviz DOT
dot = analyzer.generate_graphviz_dot(dep_report.graph)
print(dot)
```

### Pattern Detection Across Projects

```python
from agno.workflows.fsa_meta_analyzer import FSAPatternDetector

detector = FSAPatternDetector()
all_workflows = [Workflow1, Workflow2, Workflow3, ...]

fsa_structures = [
    FSAStaticAnalyzer().analyze_workflow(w) for w in all_workflows
]

pattern_report = detector.analyze_multiple_fsas(fsa_structures)

print(f"Common patterns: {pattern_report.common_patterns}")
print(f"Reusable patterns: {pattern_report.reusable_patterns}")
```

## Best Practices

1. **Run analysis regularly** - Integrate into your development workflow
2. **Address critical issues first** - Focus on validation errors before optimization
3. **Monitor quality trends** - Track quality scores over time
4. **Use quick wins** - Implement low-effort, high-impact improvements
5. **Review antipatterns** - Learn from detected antipatterns to improve design

## Limitations

- **Static Analysis**: Analysis is based on source code, not runtime behavior
- **AST Parsing**: Relies on Python AST; dynamic code generation may not be fully captured
- **Performance Predictions**: Based on heuristics, not actual execution timing
- **Pattern Detection**: Uses common patterns; custom patterns may not be detected

## Contributing

To extend the FSA Meta-Analyzer:

1. Add new validators in `validator.py`
2. Add new quality metrics in `quality_metrics.py`
3. Add new patterns in `pattern_analyzer.py`
4. Add new optimization rules in `optimizer.py`

## License

Part of the Agno framework.

## Examples

See `cookbook/workflows/fsa_meta_analyzer_example.py` for complete examples.

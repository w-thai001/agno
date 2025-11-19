# 🚀 Workflow Optimizer FSA

A meta-analysis FSA that analyzes and optimizes other FSA workflows by detecting bottlenecks, identifying parallelization opportunities, and providing actionable performance improvement strategies.

## Purpose

The Workflow Optimizer FSA provides automated performance analysis and optimization recommendations for FSA workflows. It helps developers:

- **Detect bottlenecks** in workflow execution
- **Identify parallel execution opportunities** to reduce latency
- **Optimize resource usage** (tokens, API calls, memory)
- **Improve agent orchestration** patterns
- **Reduce costs** through smarter caching and tool usage

## Features

### 🔍 Code Analysis
- Agent count and role analysis
- Execution flow mapping
- Sequential vs parallel pattern detection
- Tool usage cataloging
- Complexity scoring (1-10 scale)
- Parallelization opportunity identification

### ⚡ Performance Analysis
- Bottleneck detection from execution logs
- High-cost operation identification
- Redundant API call detection
- Blocking operation analysis
- Token usage pattern analysis

### 💡 Optimization Recommendations
- Specific parallel execution opportunities
- Caching strategy recommendations
- Agent consolidation suggestions
- Tool usage optimizations
- Estimated performance improvement percentages
- Top 3 priority actions for maximum impact

## Architecture

The FSA consists of three specialized agents:

1. **Code Analyzer** (gpt-4o-mini)
   - Analyzes workflow structure and code patterns
   - Returns structured `CodeAnalysis` results

2. **Performance Analyzer** (gpt-4o-mini)
   - Processes execution logs and metrics
   - Returns structured `BottleneckAnalysis` results

3. **Optimization Recommender** (gpt-4o)
   - Synthesizes analysis into actionable recommendations
   - Returns structured `OptimizationRecommendations`

## Usage

### Basic Usage

```python
from agno.workflows.workflow_optimizer import WorkflowOptimizer

# Initialize optimizer
optimizer = WorkflowOptimizer()

# Analyze a workflow
result = optimizer.run(
    workflow_code=your_workflow_code,
    execution_logs=your_execution_logs,
    performance_metrics={
        "total_execution_time": "45.2s",
        "token_usage": 8500,
        "api_calls": 12
    },
    workflow_description="Your workflow description"
)

# Print results
from agno.utils.pprint import pprint_run_response
pprint_run_response(result, markdown=True)
```

### Input Parameters

- **workflow_code** (Optional[str]): Python code of the FSA workflow
- **execution_logs** (Optional[str]): Execution logs from workflow runs
- **performance_metrics** (Optional[Dict]): Metrics like execution time, token usage
- **workflow_description** (Optional[str]): Description of workflow purpose

At least one of `workflow_code` or `execution_logs` must be provided.

### Performance Metrics Format

```python
performance_metrics = {
    "total_execution_time": "45.2 seconds",
    "token_usage": 8500,
    "agent_execution_times": {
        "agent1": "15.3s",
        "agent2": "18.7s",
    },
    "api_calls": 12,
    "cache_hits": 5,
    "cache_misses": 7,
}
```

## Example

See the example in `workflow_optimizer.py` main section:

```bash
python cookbook/workflows/workflow_optimizer.py
```

This runs an analysis on a sample sequential workflow and provides:
- Code structure analysis
- Performance bottleneck identification
- Optimization recommendations with estimated improvements

## Output Structure

The optimizer produces a comprehensive report including:

1. **Code Structure Analysis**
   - Agent count and roles
   - Execution flow description
   - Complexity score
   - Parallelization opportunities

2. **Performance & Bottleneck Analysis**
   - Identified bottlenecks
   - High-cost operations
   - Redundant calls
   - Blocking operations

3. **Optimization Recommendations**
   - Parallel execution opportunities (specific agents/steps)
   - Caching strategies
   - Agent consolidation suggestions
   - Tool optimizations
   - Estimated improvement percentage
   - Top 3 priority actions

## Cost Optimization

This FSA is designed for high-velocity generation at ~$5-6 credits:

- **Code Analyzer**: Uses gpt-4o-mini (fast, cheap)
- **Performance Analyzer**: Uses gpt-4o-mini (fast, cheap)
- **Optimization Recommender**: Uses gpt-4o (quality recommendations)
- **Structured Outputs**: Ensures consistent, parseable results
- **Minimal Steps**: 3-phase sequential execution

## Best Practices

1. **Provide Complete Context**: Include both code and logs for best results
2. **Include Metrics**: Add execution times, token usage, API call counts
3. **Describe Purpose**: Help the analyzer understand workflow intent
4. **Iterate**: Re-analyze after implementing recommendations
5. **Prioritize**: Focus on the top 3 priority actions first

## Dependencies

```bash
pip install openai agno
```

## Integration

The Workflow Optimizer can be:
- Run standalone for ad-hoc analysis
- Integrated into CI/CD pipelines
- Used in development for continuous optimization
- Applied to production workflows for monitoring

## Limitations

- Analysis quality depends on input completeness
- Recommendations are suggestions, not guarantees
- Some optimizations may require architectural changes
- Cost estimates are approximate

## Future Enhancements

Potential improvements:
- Real-time performance monitoring
- A/B testing framework for optimizations
- Automated refactoring suggestions
- Historical performance tracking
- Cost-benefit analysis with ROI calculations

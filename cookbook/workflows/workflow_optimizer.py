"""🚀 Workflow Optimizer FSA - Meta-analysis for FSA Performance

This FSA analyzes and optimizes other FSA workflows by:
- Analyzing workflow code structure and execution patterns
- Detecting performance bottlenecks
- Identifying parallel execution opportunities
- Providing optimization recommendations
- Suggesting refactored workflow improvements

Example Usage:
    optimizer = WorkflowOptimizer()
    result = optimizer.run(
        workflow_code="<FSA code>",
        execution_logs="<logs>",
        performance_metrics={"avg_time": 10.5, "token_usage": 5000}
    )

Run `pip install openai agno` to install dependencies.
"""

from textwrap import dedent
from typing import Any, Dict, Iterator, List, Optional

from agno.agent import Agent, RunResponse
from agno.models.openai import OpenAIChat
from agno.utils.log import logger
from agno.utils.pprint import pprint_run_response
from agno.workflow import Workflow
from pydantic import BaseModel, Field


class CodeAnalysis(BaseModel):
    """Structure for code analysis results"""

    agent_count: int = Field(..., description="Number of agents in the workflow")
    execution_flow: str = Field(..., description="Description of execution flow pattern")
    sequential_steps: List[str] = Field(
        ..., description="List of sequential execution steps"
    )
    potential_parallelism: List[str] = Field(
        ..., description="Steps that could potentially run in parallel"
    )
    tool_usage: Dict[str, int] = Field(
        ..., description="Count of tools used by each agent"
    )
    complexity_score: int = Field(
        ..., description="Complexity score from 1-10", ge=1, le=10
    )


class BottleneckAnalysis(BaseModel):
    """Structure for bottleneck detection results"""

    bottlenecks: List[str] = Field(..., description="Identified bottlenecks")
    high_cost_operations: List[str] = Field(
        ..., description="Operations with high resource costs"
    )
    redundant_calls: List[str] = Field(..., description="Redundant or duplicate calls")
    blocking_operations: List[str] = Field(
        ..., description="Operations that block workflow progress"
    )


class OptimizationRecommendations(BaseModel):
    """Structure for optimization recommendations"""

    parallel_opportunities: List[Dict[str, str]] = Field(
        ...,
        description="Opportunities for parallel execution with descriptions",
    )
    caching_strategies: List[str] = Field(
        ..., description="Recommended caching strategies"
    )
    agent_consolidation: List[str] = Field(
        ..., description="Suggestions for consolidating agents"
    )
    tool_optimization: List[str] = Field(..., description="Tool usage optimizations")
    estimated_improvement: str = Field(
        ..., description="Estimated performance improvement percentage"
    )
    priority_actions: List[str] = Field(
        ..., description="Top 3 priority optimization actions"
    )


class WorkflowOptimizer(Workflow):
    description: str = dedent("""\
    Analyzes FSA workflows to identify performance bottlenecks and optimization opportunities.
    Provides actionable recommendations for improving workflow execution efficiency.
    """)

    # Code Analyzer: Analyzes workflow structure and execution patterns
    code_analyzer: Agent = Agent(
        model=OpenAIChat(id="gpt-4o-mini"),
        name="Code Analyzer",
        role="Analyzes FSA workflow code structure and patterns",
        description=dedent("""\
            Expert at analyzing Python workflow code to understand execution patterns,
            agent orchestration, and structural complexity.
        """),
        instructions=dedent("""\
            Analyze the provided FSA workflow code:
            1. Count the number of agents and their roles
            2. Map out the execution flow in the run() method
            3. Identify sequential vs parallel execution patterns
            4. Catalog tool usage across agents
            5. Assess overall complexity (1-10 scale)
            6. Identify potential parallelization opportunities
            7. Look for conditional branching and loops

            Focus on:
            - Agent dependencies and data flow
            - Sequential bottlenecks that could be parallelized
            - Redundant agent instantiations
            - Tool distribution across agents
        """),
        response_model=CodeAnalysis,
        structured_outputs=True,
        markdown=True,
    )

    # Performance Analyzer: Detects bottlenecks from logs and metrics
    performance_analyzer: Agent = Agent(
        model=OpenAIChat(id="gpt-4o-mini"),
        name="Performance Analyzer",
        role="Detects performance bottlenecks and resource issues",
        description=dedent("""\
            Specialist in analyzing execution logs and performance metrics to identify
            bottlenecks, high-cost operations, and efficiency issues.
        """),
        instructions=dedent("""\
            Analyze execution logs and performance metrics:
            1. Identify time-consuming operations
            2. Detect redundant or duplicate API calls
            3. Find blocking operations that delay workflow
            4. Analyze token usage patterns
            5. Identify memory-intensive operations
            6. Spot error-prone areas requiring retry logic

            Consider:
            - Agent execution times (sequential delays)
            - Tool call frequencies and costs
            - Data transfer between agents
            - Cache hit/miss ratios if available
            - Resource utilization patterns
        """),
        response_model=BottleneckAnalysis,
        structured_outputs=True,
        markdown=True,
    )

    # Optimization Recommender: Provides actionable optimization strategies
    optimization_recommender: Agent = Agent(
        model=OpenAIChat(id="gpt-4o"),
        name="Optimization Recommender",
        role="Generates optimization recommendations and refactoring strategies",
        description=dedent("""\
            Expert strategist that synthesizes code and performance analysis into
            actionable optimization recommendations with measurable impact.
        """),
        instructions=dedent("""\
            Based on code structure and performance analysis, provide:
            1. Specific parallel execution opportunities (which agents/steps)
            2. Caching strategies to reduce redundant operations
            3. Agent consolidation recommendations
            4. Tool usage optimizations
            5. Estimated performance improvement (percentage)
            6. Top 3 priority actions for maximum impact

            Optimization strategies:
            - Parallel agent execution (identify independent agents)
            - Smart caching (session_state, storage)
            - Agent consolidation (merge similar roles)
            - Tool optimization (batch calls, reduce redundancy)
            - Streaming improvements (yield intermediate results)
            - Resource pooling (shared tools, models)

            Provide concrete, implementable suggestions with expected impact.
            Consider cost-benefit tradeoffs (development effort vs gains).
        """),
        response_model=OptimizationRecommendations,
        structured_outputs=True,
        markdown=True,
    )

    def run(
        self,
        workflow_code: Optional[str] = None,
        execution_logs: Optional[str] = None,
        performance_metrics: Optional[Dict[str, Any]] = None,
        workflow_description: Optional[str] = None,
    ) -> Iterator[RunResponse]:
        """
        Runs the workflow optimization analysis.

        Args:
            workflow_code: FSA workflow Python code to analyze
            execution_logs: Execution logs from workflow runs
            performance_metrics: Dict containing metrics like execution_time, token_usage, etc.
            workflow_description: Optional description of the workflow's purpose

        Yields:
            RunResponse with optimization analysis and recommendations
        """
        logger.info("Starting Workflow Optimization Analysis")

        # Validate inputs
        if not workflow_code and not execution_logs:
            yield RunResponse(
                run_id=self.run_id,
                content="Error: Please provide either workflow_code or execution_logs for analysis.",
            )
            return

        # Store inputs in session state
        self.session_state["workflow_code"] = workflow_code or "Not provided"
        self.session_state["execution_logs"] = execution_logs or "Not provided"
        self.session_state["performance_metrics"] = performance_metrics or {}
        self.session_state["workflow_description"] = (
            workflow_description or "Not provided"
        )

        # Phase 1: Code Analysis (if code provided)
        code_analysis_result = None
        if workflow_code:
            logger.info("Phase 1: Analyzing workflow code structure")
            code_analysis_input = dedent(f"""\
                Workflow Description: {workflow_description or 'N/A'}

                Workflow Code:
                ```python
                {workflow_code}
                ```
            """)

            code_analysis: RunResponse = self.code_analyzer.run(code_analysis_input)
            if code_analysis and code_analysis.content:
                code_analysis_result = code_analysis.content
                self.session_state["code_analysis"] = code_analysis_result
                logger.info("Code analysis completed")

        # Phase 2: Performance Analysis (if logs/metrics provided)
        performance_analysis_result = None
        if execution_logs or performance_metrics:
            logger.info("Phase 2: Analyzing performance and bottlenecks")
            performance_input_parts = []

            if workflow_description:
                performance_input_parts.append(
                    f"Workflow Description: {workflow_description}"
                )

            if performance_metrics:
                metrics_str = "\n".join(
                    [f"- {k}: {v}" for k, v in performance_metrics.items()]
                )
                performance_input_parts.append(
                    f"Performance Metrics:\n{metrics_str}"
                )

            if execution_logs:
                performance_input_parts.append(
                    f"Execution Logs:\n```\n{execution_logs}\n```"
                )

            if code_analysis_result:
                performance_input_parts.append(
                    f"Code Structure Context:\n{code_analysis_result}"
                )

            performance_input = "\n\n".join(performance_input_parts)

            performance_analysis: RunResponse = self.performance_analyzer.run(
                performance_input
            )
            if performance_analysis and performance_analysis.content:
                performance_analysis_result = performance_analysis.content
                self.session_state["performance_analysis"] = (
                    performance_analysis_result
                )
                logger.info("Performance analysis completed")

        # Phase 3: Generate Optimization Recommendations
        logger.info("Phase 3: Generating optimization recommendations")
        optimization_input_parts = [
            "# Workflow Optimization Context",
            f"\nWorkflow Description: {workflow_description or 'Not provided'}",
        ]

        if code_analysis_result:
            optimization_input_parts.append(
                f"\n## Code Analysis Results:\n{code_analysis_result}"
            )

        if performance_analysis_result:
            optimization_input_parts.append(
                f"\n## Performance Analysis Results:\n{performance_analysis_result}"
            )

        if performance_metrics:
            metrics_str = "\n".join(
                [f"- {k}: {v}" for k, v in performance_metrics.items()]
            )
            optimization_input_parts.append(
                f"\n## Performance Metrics:\n{metrics_str}"
            )

        optimization_input = "\n".join(optimization_input_parts)

        optimization_recommendations: RunResponse = (
            self.optimization_recommender.run(optimization_input)
        )

        if (
            not optimization_recommendations
            or not optimization_recommendations.content
        ):
            yield RunResponse(
                run_id=self.run_id,
                content="Error: Could not generate optimization recommendations.",
            )
            return

        # Compile final report
        logger.info("Compiling optimization report")
        report_parts = [
            "# 🚀 Workflow Optimization Report\n",
        ]

        if workflow_description:
            report_parts.append(f"**Workflow:** {workflow_description}\n")

        if code_analysis_result:
            report_parts.append(f"## 📊 Code Structure Analysis\n")
            report_parts.append(f"{code_analysis_result}\n")

        if performance_analysis_result:
            report_parts.append(f"## ⚡ Performance & Bottleneck Analysis\n")
            report_parts.append(f"{performance_analysis_result}\n")

        report_parts.append(f"## 💡 Optimization Recommendations\n")
        report_parts.append(f"{optimization_recommendations.content}\n")

        report_parts.append("\n---\n*Analysis complete. Implement priority actions for maximum impact.*")

        final_report = "\n".join(report_parts)
        self.session_state["final_report"] = final_report

        yield RunResponse(
            run_id=self.run_id,
            content=final_report,
        )


if __name__ == "__main__":
    # Example: Analyze a sample workflow
    sample_workflow_code = """
from agno.agent import Agent
from agno.workflow import Workflow, RunResponse
from typing import Iterator

class SampleWorkflow(Workflow):
    researcher: Agent = Agent(
        name="Researcher",
        role="Research information",
        tools=[WebSearchTools()],
    )

    writer: Agent = Agent(
        name="Writer",
        role="Write content",
        tools=[],
    )

    editor: Agent = Agent(
        name="Editor",
        role="Edit and refine",
        tools=[],
    )

    def run(self, topic: str) -> Iterator[RunResponse]:
        # Sequential execution
        research = self.researcher.run(topic)
        draft = self.writer.run(research.content)
        final = self.editor.run(draft.content)
        yield final
    """

    sample_metrics = {
        "total_execution_time": "45.2 seconds",
        "token_usage": 8500,
        "agent_execution_times": {
            "researcher": "15.3s",
            "writer": "18.7s",
            "editor": "11.2s",
        },
        "api_calls": 12,
    }

    sample_logs = """
[INFO] Starting workflow
[INFO] Researcher agent started
[INFO] Researcher completed web search (15.3s)
[INFO] Writer agent started
[INFO] Writer generated draft (18.7s)
[INFO] Editor agent started
[INFO] Editor refined content (11.2s)
[INFO] Workflow completed
    """

    # Run optimizer
    optimizer = WorkflowOptimizer(debug_mode=True)
    result = optimizer.run(
        workflow_code=sample_workflow_code,
        execution_logs=sample_logs,
        performance_metrics=sample_metrics,
        workflow_description="Content creation workflow with research, writing, and editing",
    )

    # Print results
    pprint_run_response(result, markdown=True)

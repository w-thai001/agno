"""
Orchestrator FSA Example - Multi-Stage Research Report Generation

This example demonstrates the OrchestratorFSA coordinating a complex workflow
that generates a comprehensive research report through multiple stages:

1. Topic Research - Gather information on the topic
2. Data Analysis (parallel) - Analyze different aspects
   - Technical Analysis
   - Market Analysis
   - Trend Analysis
3. Synthesis - Combine analyses into insights
4. Report Generation - Create final report

Features demonstrated:
- Sequential and parallel task execution
- Dependency management
- Data flow between tasks
- Error recovery
- Progress monitoring
- State management
"""

from typing import Any, Dict, Iterator, List
import logging

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.run.response import RunResponse
from agno.storage.json import JsonStorage
from agno.workflow.fsa import FSA, FSAConfig, FSAState, StateTransition
from agno.workflow.orchestrator_fsa import (
    ExecutionStrategy,
    FSATask,
    OrchestratorConfig,
    OrchestratorFSA,
    RecoveryStrategy,
)


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Define custom FSA states for research pipeline
class ResearchState(str, FSAState):
    """States for research FSA."""
    IDLE = "idle"
    RESEARCHING = "researching"
    ANALYZING = "analyzing"
    COMPLETED = "completed"


# Custom FSA for research tasks
class ResearchFSA(FSA):
    """
    FSA that performs research on a given topic.

    Uses an AI agent to gather information and analyze it.
    """

    def __init__(self, name: str, agent: Agent, research_type: str = "general"):
        """
        Initialize research FSA.

        Args:
            name: FSA name
            agent: Agent to use for research
            research_type: Type of research (general, technical, market, trend)
        """
        self.agent = agent
        self.research_type = research_type

        config = FSAConfig(
            name=name,
            initial_state=ResearchState.IDLE,
            final_states=[ResearchState.COMPLETED],
            transitions=[
                StateTransition(
                    from_state=ResearchState.IDLE,
                    to_state=ResearchState.RESEARCHING,
                    description=f"Start {research_type} research"
                ),
                StateTransition(
                    from_state=ResearchState.RESEARCHING,
                    to_state=ResearchState.ANALYZING,
                    description="Analyze research data"
                ),
                StateTransition(
                    from_state=ResearchState.ANALYZING,
                    to_state=ResearchState.COMPLETED,
                    description="Complete research"
                )
            ]
        )

        super().__init__(config=config, session_state={})

    def run(self, topic: str = None, input_data: str = None, **kwargs) -> Dict[str, Any]:
        """
        Execute research FSA.

        Args:
            topic: Research topic
            input_data: Optional input from previous tasks
            **kwargs: Additional parameters

        Returns:
            Research results
        """
        if not topic:
            raise ValueError("Topic is required for research")

        logger.info(f"Starting {self.research_type} research on: {topic}")

        # Transition to RESEARCHING
        transition = self.find_transition()
        if transition:
            self.execute_transition(transition)
            self.context.data["topic"] = topic
            self.context.data["input_data"] = input_data

        # Build research prompt based on type
        prompts = {
            "general": f"Research and provide a comprehensive overview of: {topic}",
            "technical": f"Provide a technical analysis of: {topic}. Focus on technical aspects, architecture, implementation details.",
            "market": f"Analyze the market landscape for: {topic}. Include market size, competitors, opportunities.",
            "trend": f"Analyze current trends related to: {topic}. Include emerging patterns, future predictions."
        }

        prompt = prompts.get(self.research_type, prompts["general"])
        if input_data:
            prompt += f"\n\nContext from previous analysis:\n{input_data}"

        # Transition to ANALYZING
        transition = self.find_transition()
        if transition:
            self.execute_transition(transition)

        # Execute research (would normally use agent.run() in real scenario)
        # For this example, we'll simulate the response
        logger.info(f"Executing {self.research_type} research...")

        # In a real scenario, uncomment this:
        # response = self.agent.run(prompt)
        # research_result = response.content

        # Simulated result for demonstration
        research_result = f"""
        {self.research_type.upper()} RESEARCH RESULTS for '{topic}':

        Analysis Type: {self.research_type}
        Key Findings:
        - Finding 1: Detailed analysis point
        - Finding 2: Important insight
        - Finding 3: Critical observation

        Recommendations:
        - Recommendation 1
        - Recommendation 2

        Data Quality: High
        Confidence Level: 85%
        """

        # Transition to COMPLETED
        transition = self.find_transition()
        if transition:
            self.execute_transition(transition)

        result = {
            "research_type": self.research_type,
            "topic": topic,
            "findings": research_result,
            "output": research_result,  # For output mapping
            "confidence": 0.85,
            "metadata": {
                "transitions": self.context.transition_count,
                "final_state": self.context.current_state.value
            }
        }

        logger.info(f"Completed {self.research_type} research")
        return result


# Synthesis FSA
class SynthesisFSA(FSA):
    """
    FSA that synthesizes multiple research results into unified insights.
    """

    def __init__(self, name: str, agent: Agent):
        """Initialize synthesis FSA."""
        self.agent = agent

        config = FSAConfig(
            name=name,
            initial_state=ResearchState.IDLE,
            final_states=[ResearchState.COMPLETED],
            transitions=[
                StateTransition(
                    from_state=ResearchState.IDLE,
                    to_state=ResearchState.ANALYZING,
                    description="Start synthesis"
                ),
                StateTransition(
                    from_state=ResearchState.ANALYZING,
                    to_state=ResearchState.COMPLETED,
                    description="Complete synthesis"
                )
            ]
        )

        super().__init__(config=config, session_state={})

    def run(self, topic: str = None, technical_data: str = None,
            market_data: str = None, trend_data: str = None, **kwargs) -> Dict[str, Any]:
        """
        Synthesize research data.

        Args:
            topic: Research topic
            technical_data: Technical analysis results
            market_data: Market analysis results
            trend_data: Trend analysis results
            **kwargs: Additional parameters

        Returns:
            Synthesized insights
        """
        logger.info(f"Synthesizing research data for: {topic}")

        # Transition to ANALYZING
        transition = self.find_transition()
        if transition:
            self.execute_transition(transition)

        # Combine all data sources
        combined_data = f"""
        SYNTHESIS OF RESEARCH ON: {topic}

        === TECHNICAL ANALYSIS ===
        {technical_data or 'Not available'}

        === MARKET ANALYSIS ===
        {market_data or 'Not available'}

        === TREND ANALYSIS ===
        {trend_data or 'Not available'}

        === UNIFIED INSIGHTS ===
        Based on the comprehensive analysis across technical, market, and trend dimensions,
        the following key insights emerge:

        1. Strategic Positioning: The technical capabilities align well with market demands
        2. Growth Potential: Current trends indicate significant opportunities
        3. Risk Assessment: Balanced risk profile with manageable challenges

        === RECOMMENDATIONS ===
        1. Prioritize technical development in areas X, Y, Z
        2. Focus market efforts on segments A, B
        3. Monitor emerging trends P, Q for strategic pivots
        """

        # Transition to COMPLETED
        transition = self.find_transition()
        if transition:
            self.execute_transition(transition)

        logger.info("Synthesis completed")

        return {
            "synthesis": combined_data,
            "output": combined_data,
            "insights_count": 3,
            "recommendations_count": 3,
            "metadata": {
                "transitions": self.context.transition_count,
                "final_state": self.context.current_state.value
            }
        }


# Progress monitoring callback
def progress_monitor(progress: Dict[str, Any]):
    """Monitor and log orchestration progress."""
    logger.info(
        f"Progress Update - State: {progress['current_state']}, "
        f"Completed: {progress['completed_tasks']}/{progress['total_tasks']} "
        f"({progress['completion_percentage']:.1f}%), "
        f"Failed: {progress['failed_tasks']}"
    )


# Main orchestration workflow
class ResearchReportOrchestrator(OrchestratorFSA):
    """
    Orchestrator for multi-stage research report generation.

    Coordinates research, analysis, synthesis, and report generation.
    """

    description: str = "Multi-stage research report generation with parallel analysis"

    def __init__(self, model: str = "gpt-4", **kwargs):
        """
        Initialize research orchestrator.

        Args:
            model: AI model to use
            **kwargs: Additional workflow parameters
        """
        # Create agents for different tasks
        researcher = Agent(
            name="Researcher",
            role="Research Specialist",
            model=OpenAIChat(id=model),
            description="Gathers and organizes information on topics"
        )

        technical_analyst = Agent(
            name="TechnicalAnalyst",
            role="Technical Analysis Expert",
            model=OpenAIChat(id=model),
            description="Analyzes technical aspects and implementation details"
        )

        market_analyst = Agent(
            name="MarketAnalyst",
            role="Market Analysis Expert",
            model=OpenAIChat(id=model),
            description="Analyzes market landscape and opportunities"
        )

        trend_analyst = Agent(
            name="TrendAnalyst",
            role="Trend Analysis Expert",
            model=OpenAIChat(id=model),
            description="Identifies and analyzes trends"
        )

        synthesizer = Agent(
            name="Synthesizer",
            role="Research Synthesizer",
            model=OpenAIChat(id=model),
            description="Combines multiple analyses into unified insights"
        )

        report_writer = Agent(
            name="ReportWriter",
            role="Report Generator",
            model=OpenAIChat(id=model),
            description="Creates comprehensive research reports"
        )

        # Define orchestration tasks
        tasks = [
            # Stage 1: Initial Research
            FSATask(
                name="initial_research",
                fsa=ResearchFSA("initial_research", researcher, "general"),
                dependencies=[],
                output_mapping={"output": "research_overview"}
            ),

            # Stage 2: Parallel Analysis (all depend on initial research)
            FSATask(
                name="technical_analysis",
                fsa=ResearchFSA("technical_analysis", technical_analyst, "technical"),
                dependencies=["initial_research"],
                input_mapping={"research_overview": "input_data"},
                output_mapping={"output": "technical_data"},
                can_run_parallel=True
            ),
            FSATask(
                name="market_analysis",
                fsa=ResearchFSA("market_analysis", market_analyst, "market"),
                dependencies=["initial_research"],
                input_mapping={"research_overview": "input_data"},
                output_mapping={"output": "market_data"},
                can_run_parallel=True
            ),
            FSATask(
                name="trend_analysis",
                fsa=ResearchFSA("trend_analysis", trend_analyst, "trend"),
                dependencies=["initial_research"],
                input_mapping={"research_overview": "input_data"},
                output_mapping={"output": "trend_data"},
                can_run_parallel=True
            ),

            # Stage 3: Synthesis (depends on all analyses)
            FSATask(
                name="synthesis",
                fsa=SynthesisFSA("synthesis", synthesizer),
                dependencies=["technical_analysis", "market_analysis", "trend_analysis"],
                input_mapping={
                    "technical_data": "technical_data",
                    "market_data": "market_data",
                    "trend_data": "trend_data"
                },
                output_mapping={"output": "synthesized_insights"}
            ),

            # Stage 4: Final Report (depends on synthesis)
            FSATask(
                name="report_generation",
                agent=report_writer,
                dependencies=["synthesis"],
                input_mapping={"synthesized_insights": "synthesis_data"}
            )
        ]

        # Orchestrator configuration
        config = OrchestratorConfig(
            execution_strategy=ExecutionStrategy.ADAPTIVE,
            recovery_strategy=RecoveryStrategy.RETRY,
            max_parallel_tasks=3,
            enable_monitoring=True,
            enable_checkpointing=True,
            task_timeout_seconds=300
        )

        # Initialize orchestrator
        super().__init__(
            tasks=tasks,
            config=config,
            progress_callback=progress_monitor,
            **kwargs
        )

    def run(self, topic: str, **kwargs) -> Iterator[RunResponse]:
        """
        Run the research report orchestration.

        Args:
            topic: Research topic
            **kwargs: Additional parameters

        Yields:
            RunResponse objects with progress updates
        """
        logger.info(f"Starting research report orchestration for topic: {topic}")

        # Add topic to all task contexts
        for task in self.tasks:
            if task.fsa:
                task.fsa.context.data["topic"] = topic

        # Run orchestration
        yield from super().run(**kwargs)


# Example usage
def main():
    """Example usage of the Research Report Orchestrator."""
    # Create storage
    storage = JsonStorage(dir_path="/tmp/agno_orchestrator_demo")

    # Create orchestrator
    orchestrator = ResearchReportOrchestrator(
        storage=storage,
        name="ResearchReportDemo"
    )

    # Run orchestration
    topic = "Artificial Intelligence in Healthcare"

    print(f"\n{'=' * 80}")
    print(f"RESEARCH REPORT ORCHESTRATION DEMO")
    print(f"Topic: {topic}")
    print(f"{'=' * 80}\n")

    try:
        for response in orchestrator.run(topic=topic):
            if response.event == "workflow_started":
                print(f"\n✓ Workflow started")
            elif response.event == "validation_completed":
                print(f"✓ {response.content}")
            elif response.event == "planning_completed":
                print(f"✓ {response.content}")
            elif response.event == "batch_started":
                print(f"\n→ {response.content}")
            elif response.event == "batch_completed":
                print(f"✓ {response.content}")
            elif response.event == "orchestration_finalized":
                print(f"\n{'=' * 80}")
                print(f"ORCHESTRATION COMPLETED")
                print(f"{'=' * 80}")

                result = response.content
                print(f"\nResults:")
                print(f"  Success: {result.success}")
                print(f"  Completed Tasks: {len(result.completed_tasks)}")
                print(f"  Failed Tasks: {len(result.failed_tasks)}")
                print(f"  Execution Time: {result.execution_time_seconds:.2f}s")
                print(f"  Total Transitions: {result.total_transitions}")

                print(f"\nTask Details:")
                for task_name, details in result.task_details.items():
                    print(f"  {task_name}:")
                    print(f"    Status: {details['status']}")
                    print(f"    Retries: {details['retry_count']}")

                print(f"\n{'=' * 80}\n")

    except Exception as e:
        logger.error(f"Orchestration failed: {e}")
        raise


if __name__ == "__main__":
    main()

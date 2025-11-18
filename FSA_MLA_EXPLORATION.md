# FSA (Focused Specialized Agent) & MLA (Multi-Layer Architecture) Exploration

## Current Codebase Structure Overview

### 1. Base Agent Class Location
- **File**: `/home/user/agno/libs/agno/agno/agent/agent.py`
- **Size**: 4189 lines
- **Type**: `@dataclass(init=False)` decorated class
- **Pattern**: Dataclass with explicit `__init__` method

### 2. Directory Structure

```
/home/user/agno/
├── libs/agno/agno/
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── agent.py (4189 lines - Main Agent class)
│   │   └── metrics.py (SessionMetrics)
│   ├── workflow/
│   │   ├── __init__.py
│   │   └── workflow.py (Workflow orchestration class)
│   ├── models/
│   │   ├── base.py (Model base class)
│   │   ├── message.py (Message, Citations, MessageReferences)
│   │   └── response.py (ModelResponse, ModelResponseEvent)
│   ├── memory/
│   │   ├── agent.py (AgentMemory, AgentRun)
│   │   └── workflow.py (WorkflowMemory, WorkflowRun)
│   ├── knowledge/
│   │   └── agent.py (AgentKnowledge)
│   ├── storage/
│   │   ├── base.py (Storage interface)
│   │   └── session/
│   │       ├── agent.py (AgentSession)
│   │       └── workflow.py (WorkflowSession)
│   └── tools/
│       ├── function.py (Function tool wrapper)
│       └── toolkit.py (Toolkit base class)
├── cookbook/
│   ├── getting_started/
│   │   ├── 01_basic_agent.py
│   │   ├── 02_agent_with_tools.py
│   │   ├── 05_agent_team.py
│   │   └── 09_research_workflow.py
│   ├── examples/
│   │   ├── agents/
│   │   │   ├── finance_agent.py
│   │   │   ├── agno_support_agent.py
│   │   │   └── ... (various specialized agents)
│   │   └── apps/
│   │       ├── chess_team/agents.py
│   │       ├── sql_agent/agents.py
│   │       └── ... (team-based applications)
│   └── workflows/
│       ├── content_creator/workflow.py
│       └── ... (workflow examples)
```

## Current Agent Implementation Patterns

### 1. Agent Class Structure

**Key Attributes** (Major categories):

```python
@dataclass(init=False)
class Agent:
    # --- Agent Settings ---
    model: Optional[Model] = None
    name: Optional[str] = None
    agent_id: Optional[str] = None
    introduction: Optional[str] = None
    
    # --- User Settings ---
    user_id: Optional[str] = None
    
    # --- Session Settings ---
    session_id: Optional[str] = None
    session_name: Optional[str] = None
    session_state: Optional[Dict[str, Any]] = None
    
    # --- Agent Context ---
    context: Optional[Dict[str, Any]] = None
    add_context: bool = False
    resolve_context: bool = True
    
    # --- Agent Memory ---
    memory: Optional[AgentMemory] = None
    add_history_to_messages: bool = False
    num_history_responses: int = 3
    
    # --- Agent Knowledge ---
    knowledge: Optional[AgentKnowledge] = None
    add_references: bool = False
    retriever: Optional[Callable] = None
    
    # --- Agent Tools ---
    tools: Optional[List[Union[Toolkit, Callable, Function, Dict]]] = None
    show_tool_calls: bool = False
    tool_call_limit: Optional[int] = None
    tool_choice: Optional[Union[str, Dict]] = None
    
    # --- Agent Reasoning ---
    reasoning: bool = False
    reasoning_model: Optional[Model] = None
    reasoning_agent: Optional[Agent] = None
    
    # --- System Message ---
    system_message: Optional[Union[str, Callable, Message]] = None
    create_default_system_message: bool = True
    description: Optional[str] = None
    goal: Optional[str] = None
    instructions: Optional[Union[str, List[str], Callable]] = None
    expected_output: Optional[str] = None
    
    # --- Agent Team ---
    team: Optional[List[Agent]] = None
    role: Optional[str] = None
    respond_directly: bool = False
    
    # --- Debug & Monitoring ---
    debug_mode: bool = False
    monitoring: bool = False
    telemetry: bool = True
```

### 2. Key Methods

```python
def __init__(self, *, model, name, agent_id, ...): ...
def initialize_agent(self) -> None: ...
def run(
    self,
    message: Optional[Union[str, List, Dict, Message]] = None,
    *,
    stream: bool = False,
    audio: Optional[Sequence[Audio]] = None,
    images: Optional[Sequence[Image]] = None,
    videos: Optional[Sequence[Video]] = None,
    files: Optional[Sequence[File]] = None,
    messages: Optional[Sequence[Union[Dict, Message]]] = None,
    stream_intermediate_steps: bool = False,
    retries: Optional[int] = None,
    **kwargs: Any,
) -> Union[RunResponse, Iterator[RunResponse]]: ...

async def arun(self, ...): ...
def get_tools(self) -> Optional[List[Union[Toolkit, Callable, Function, Dict]]]: ...
def add_tools_to_model(self, model: Model) -> None: ...
def update_model(self) -> None: ...
def resolve_run_context(self) -> None: ...
def read_from_storage(self) -> Optional[AgentSession]: ...
def write_to_storage(self) -> Optional[AgentSession]: ...
```

### 3. Workflow Class Structure

```python
@dataclass(init=False)
class Workflow:
    name: Optional[str] = None
    workflow_id: Optional[str] = None
    description: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    session_state: Dict[str, Any] = field(default_factory=dict)
    memory: Optional[WorkflowMemory] = None
    storage: Optional[Storage] = None
    debug_mode: bool = False
    monitoring: bool = False
    telemetry: bool = True
    
    # Private attributes
    _subclass_run: Optional[Callable] = None
    _run_parameters: Optional[Dict[str, Any]] = None
    _run_return_type: Optional[str] = None

def run(self, **kwargs: Any): ...  # Must be overridden in subclass
def run_workflow(self, **kwargs: Any): ...  # Entry point
```

## Existing Agent Implementation Patterns

### Pattern 1: Single Agent (Simple Specialization)
**File**: `cookbook/examples/agents/finance_agent.py`
```python
finance_agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    tools=[YFinanceTools(...)],
    instructions="<detailed instructions>",
    show_tool_calls=True,
    markdown=True,
)
```

### Pattern 2: Agent Team (Multi-Agent Coordination)
**File**: `cookbook/getting_started/05_agent_team.py`
```python
web_agent = Agent(name="Web Agent", role="Search the web", ...)
finance_agent = Agent(name="Finance Agent", role="Get financial data", ...)
agent_team = Agent(
    team=[web_agent, finance_agent],
    instructions="Coordinate findings",
    ...
)
```

### Pattern 3: Workflow with Agents (Orchestrated Multi-Step)
**File**: `cookbook/getting_started/09_research_workflow.py`
```python
class ResearchReportGenerator(Workflow):
    description: str = "Generate comprehensive research reports"
    
    web_searcher: Agent = Agent(
        model=OpenAIChat(id="gpt-4o-mini"),
        tools=[DuckDuckGoTools()],
        ...
    )
    
    article_scraper: Agent = Agent(...)
    writer: Agent = Agent(...)
    
    def run(self, topic: str, **kwargs) -> Iterator[RunResponse]:
        # Orchestrate agents
        search_results = self.web_searcher.run(topic)
        scraped_articles = self.article_scraper.run(search_results)
        yield from self.writer.run(scraped_articles)
```

### Pattern 4: Specialized Agents in Team (Chess Example)
**File**: `cookbook/examples/apps/chess_team/agents.py`
```python
def get_chess_teams(
    white_model: str = "openai:gpt-4o",
    black_model: str = "anthropic:claude-3-7-sonnet",
    master_model: str = "openai:gpt-4o",
    debug_mode: bool = True,
) -> Dict[str, Agent]:
    white_piece_agent = Agent(
        name="white_piece_agent",
        description="Chess strategist for white pieces",
        model=white_piece_model,
    )
    
    black_piece_agent = Agent(
        name="black_piece_agent",
        description="Chess strategist for black pieces",
        model=black_piece_model,
    )
    
    master_agent = Agent(
        name="master_agent",
        description="Chess master overseeing the game",
        model=master_model,
    )
    
    return {
        "white_piece_agent": white_piece_agent,
        "black_piece_agent": black_piece_agent,
        "master_agent": master_agent,
    }
```

## FSA (Focused Specialized Agent) Architecture

### What is an FSA?
An FSA is a specialized agent with a narrow, well-defined purpose that excels at a specific task or domain. FSAs should:

1. **Have a singular responsibility**: One primary task or capability
2. **Be highly specialized**: Deep expertise in their domain
3. **Be composable**: Work well with other FSAs
4. **Have focused tooling**: Only tools needed for their task
5. **Be reusable**: Clear inputs/outputs for composition

### FSA Implementation Pattern

Based on the codebase patterns, an FSA should:

```python
class SpecializedFSA(Agent):
    """
    A Focused Specialized Agent template.
    """
    
    def __init__(
        self,
        model: Optional[Model] = None,
        name: Optional[str] = None,
        role: Optional[str] = None,
        tools: Optional[List[Union[Toolkit, Callable, Function, Dict]]] = None,
        description: Optional[str] = None,
        instructions: Optional[Union[str, List[str]]] = None,
        expected_output: Optional[str] = None,
        **kwargs: Any,
    ):
        """
        Initialize an FSA with focused parameters.
        
        Args:
            model: The LLM to use for this FSA
            name: Name of the FSA
            role: Role/responsibility of the FSA
            tools: Specific tools for this FSA's task
            description: What this FSA does
            instructions: How to execute the task
            expected_output: Format of expected output
            **kwargs: Additional agent parameters
        """
        super().__init__(
            model=model,
            name=name or self.__class__.__name__,
            role=role,
            description=description or self.__class__.description,
            instructions=instructions or self._get_default_instructions(),
            expected_output=expected_output,
            tools=tools,
            show_tool_calls=False,  # FSAs typically don't show tool calls
            markdown=True,
            **kwargs,
        )
    
    @staticmethod
    def _get_default_instructions() -> str:
        """Override in subclass to provide default instructions"""
        return ""
    
    def execute(self, input_data: Any, **kwargs: Any) -> RunResponse:
        """
        Execute the FSA with given input.
        
        This method should be overridden to provide specific execution logic.
        """
        return self.run(str(input_data), **kwargs)
```

### FSA Directory Structure
```
/home/user/agno/libs/agno/agno/fsas/
├── __init__.py
├── base_fsa.py (Base FSA class)
├── research/
│   ├── __init__.py
│   ├── web_searcher_fsa.py
│   ├── content_analyzer_fsa.py
│   └── report_writer_fsa.py
├── content/
│   ├── __init__.py
│   ├── blog_analyzer_fsa.py
│   ├── social_media_planner_fsa.py
│   └── content_generator_fsa.py
├── finance/
│   ├── __init__.py
│   ├── stock_analyzer_fsa.py
│   └── market_analyst_fsa.py
└── utils/
    ├── __init__.py
    └── fsa_registry.py
```

## MLA (Multi-Layer Architecture) Framework

### What is MLA?
MLA is a hierarchical architecture for organizing and composing FSAs:

1. **Layer 1: Foundation FSAs** - Basic specialized tasks (search, analyze, generate)
2. **Layer 2: Composition FSAs** - Combine multiple FSAs (orchestrator agents)
3. **Layer 3: Workflow Layer** - End-to-end orchestration (high-level tasks)

### MLA Integration Pattern

```python
# Layer 1: Foundation FSAs
class SearchFSA(Agent):
    """Search for information on a topic"""
    def __init__(self, **kwargs):
        super().__init__(
            name="SearchFSA",
            role="Search for information",
            tools=[DuckDuckGoTools()],
            **kwargs,
        )

class AnalyzerFSA(Agent):
    """Analyze and summarize information"""
    def __init__(self, **kwargs):
        super().__init__(
            name="AnalyzerFSA",
            role="Analyze and summarize",
            **kwargs,
        )

# Layer 2: Composition FSA
class ResearchCoordinatorFSA(Agent):
    """Coordinate search and analysis"""
    def __init__(self, **kwargs):
        self.search_fsa = SearchFSA(model=kwargs.get('model'))
        self.analyzer_fsa = AnalyzerFSA(model=kwargs.get('model'))
        
        super().__init__(
            name="ResearchCoordinator",
            role="Coordinate research",
            team=[self.search_fsa, self.analyzer_fsa],
            **kwargs,
        )

# Layer 3: Workflow
class ResearchWorkflow(Workflow):
    """High-level research task orchestration"""
    
    research_coordinator: Agent = ResearchCoordinatorFSA()
    
    def run(self, topic: str) -> Iterator[RunResponse]:
        yield from self.research_coordinator.run(topic, stream=True)
```

### MLA File Structure
```
/home/user/agno/libs/agno/agno/mla/
├── __init__.py
├── layers.py (Layer definitions and interfaces)
├── composition/
│   ├── __init__.py
│   ├── composition_base.py
│   └── coordinator_fsa.py
├── workflow/
│   ├── __init__.py
│   ├── mla_workflow.py (Base workflow for MLA)
│   └── execution_engine.py
└── registry/
    ├── __init__.py
    └── fsa_registry.py (Dynamic FSA discovery and composition)
```

## Integration Points with Framework

### 1. Agent Initialization
- Agents inherit from `@dataclass` with explicit `__init__`
- Use `Agent.__init__()` super call with keyword-only arguments
- Set up model, name, role, tools, instructions

### 2. Execution Models
- **Single execution**: `agent.run(message, stream=False)` → `RunResponse`
- **Streaming execution**: `agent.run(message, stream=True)` → `Iterator[RunResponse]`
- **Async execution**: `await agent.arun(message)` → `RunResponse`

### 3. Tool Integration
- Tools passed as list to `tools` parameter
- Tools can be: `Toolkit`, `Callable`, `Function`, or `Dict`
- Tools added via `agent.add_tools_to_model(model)`

### 4. Memory Management
- Agent memory: `AgentMemory` (chat history, sessions)
- Workflow memory: `WorkflowMemory` (run history)
- Session state: `session_state` dict in both Agent and Workflow
- Persistence: Via `Storage` interface

### 5. Structured Outputs
- Use `response_model` with Pydantic `BaseModel`
- Enable `structured_outputs=True` for model-native support
- Framework automatically parses JSON responses

### 6. Message Handling
- Messages passed as: `str`, `List`, `Dict`, `Message` object
- `Message` type from `agno.models.message`
- System message generation via `create_default_system_message`

### 7. Team Coordination
- Agents use `team` parameter to define sub-agents
- Team agents have `role` parameter
- `respond_directly` controls response routing

## Key Configuration Patterns

### 1. System Message Configuration
```python
Agent(
    system_message="Custom system message",
    # OR
    system_message=lambda: f"Time-aware system message: {datetime.now()}",
    # OR
    create_default_system_message=True,
    description="Agent purpose",
    goal="What the agent achieves",
    instructions="How to execute",
    expected_output="Format of output",
    markdown=True,
    add_datetime_to_instructions=True,
)
```

### 2. Tool Configuration
```python
Agent(
    tools=[
        YFinanceTools(...),
        DuckDuckGoTools(),
        CustomFunction(...),
    ],
    show_tool_calls=True,
    tool_call_limit=10,
    tool_choice="auto",  # or "none" or specific tool dict
)
```

### 3. Memory & Knowledge Configuration
```python
Agent(
    memory=AgentMemory(...),
    add_history_to_messages=True,
    num_history_responses=3,
    
    knowledge=AgentKnowledge(...),
    add_references=True,
    retriever=custom_retriever_function,
    references_format="json",  # or "yaml"
)
```

### 4. Team Configuration
```python
Agent(
    team=[agent1, agent2, agent3],
    role="Team Lead",
    instructions="Coordinate the team",
    add_transfer_instructions=True,
    team_response_separator="\n",
)
```

## Base Classes and Interfaces to Inherit From

### 1. Agent Base Class
- **File**: `/home/user/agno/libs/agno/agno/agent/agent.py`
- **Type**: `@dataclass` decorated class
- **Inheritance**: Direct instantiation or subclass
- **Key Pattern**: Keyword-only `__init__` arguments

### 2. Workflow Base Class
- **File**: `/home/user/agno/libs/agno/agno/workflow/workflow.py`
- **Type**: `@dataclass` decorated class
- **Method to Override**: `run(self, **kwargs) -> Iterator[RunResponse] | RunResponse`
- **Key Features**: Session state, memory, agent management

### 3. Model Interface
- **File**: `/home/user/agno/libs/agno/agno/models/base.py`
- **Implementations**: OpenAIChat, Claude, Gemini, Groq, etc.
- **Key Methods**: Used internally by Agent

### 4. Toolkit Base Class
- **File**: `/home/user/agno/libs/agno/agno/tools/toolkit.py`
- **Purpose**: Group related tools together
- **Usage**: Passed to `Agent.tools`

### 5. Storage Interface
- **File**: `/home/user/agno/libs/agno/agno/storage/base.py`
- **Implementations**: SqliteStorage, JsonStorage, YamlStorage, PostgresStorage
- **Usage**: Persist agent/workflow state

## Recommended FSA Implementation Checklist

- [ ] Create FSA class inheriting from `Agent`
- [ ] Define `__init__` with focused parameters
- [ ] Specify single `role` and `description`
- [ ] Include only relevant `tools`
- [ ] Write clear `instructions` for the task
- [ ] Define `expected_output` format
- [ ] Add docstring with examples
- [ ] Create `execute()` method if custom logic needed
- [ ] Add input validation in `execute()`
- [ ] Return `RunResponse` object
- [ ] Create test cases for FSA
- [ ] Document expected inputs and outputs
- [ ] Add FSA to registry if applicable

## Recommended MLA Workflow Implementation Checklist

- [ ] Create Workflow class inheriting from `Workflow`
- [ ] Define layer 1: Foundation FSAs as class attributes
- [ ] Define layer 2: Composition FSAs (if needed)
- [ ] Implement `run(**kwargs)` method
- [ ] Use `Iterator[RunResponse]` for streaming
- [ ] Use `session_state` for caching intermediate results
- [ ] Call `self.write_to_storage()` to persist state
- [ ] Add proper error handling
- [ ] Add logging for debugging
- [ ] Document workflow steps and FSA integration points
- [ ] Create test cases for each layer
- [ ] Test FSA composition and data flow

## Example Use Cases

### FSA Use Case 1: Simple Task
```python
# Single FSA for stock price analysis
class StockAnalyzerFSA(Agent):
    def __init__(self, model: Model):
        super().__init__(
            model=model,
            name="StockAnalyzer",
            role="Analyze stock data",
            tools=[YFinanceTools(stock_price=True)],
            instructions="Provide detailed stock analysis",
        )
```

### FSA Use Case 2: Composition
```python
# Multiple FSAs composed in a Workflow
class FinancialReportWorkflow(Workflow):
    stock_analyzer: Agent = StockAnalyzerFSA(...)
    market_analyzer: Agent = MarketAnalyzerFSA(...)
    reporter: Agent = ReportWriterFSA(...)
    
    def run(self, ticker: str) -> Iterator[RunResponse]:
        stock_data = self.stock_analyzer.run(ticker)
        market_data = self.market_analyzer.run(ticker)
        yield from self.reporter.run(
            f"Stock: {stock_data}\nMarket: {market_data}"
        )
```

### FSA Use Case 3: MLA Layer
```python
# MLA Pattern with three layers
# Layer 1: Foundation FSAs (search, analyze, generate)
# Layer 2: Coordinator FSA (orchestrates Layer 1)
# Layer 3: Workflow (high-level user interface)

class ResearchWorkflow(Workflow):
    # Layer 1
    search_fsa = SearchFSA(...)
    analyze_fsa = AnalyzeFSA(...)
    
    # Layer 2
    coordinator = CoordinatorFSA(
        team=[search_fsa, analyze_fsa]
    )
    
    def run(self, topic: str):
        # Layer 3: Orchestrate at workflow level
        yield from self.coordinator.run(topic, stream=True)
```

## Performance Considerations

1. **Agent Creation**: ~2μs per agent (very fast)
2. **Memory Usage**: ~3.75KB per agent
3. **Tool Optimization**: Use `tool_call_limit` to prevent excessive calls
4. **Streaming**: Use `stream=True` for real-time feedback
5. **Caching**: Use `session_state` to cache intermediate results
6. **Concurrency**: FSAs can be composed within workflows for parallelization

## Summary

**FSAs** are specialized agents with:
- Single responsibility principle
- Focused tooling and instructions
- Clear input/output contracts
- Reusable across contexts

**MLA** provides:
- Hierarchical organization (Layer 1, 2, 3)
- Clear separation of concerns
- Composable building blocks
- Scalable architecture

**Integration** via:
- Agent `__init__` with keyword-only args
- RunResponse for structured outputs
- Workflow for orchestration
- Storage for persistence
- Memory for state management

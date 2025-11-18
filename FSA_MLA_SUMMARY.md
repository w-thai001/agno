# FSA & MLA Framework - Complete Summary

## Overview

The Agno framework supports building Focused Specialized Agents (FSAs) organized in a Multi-Layer Architecture (MLA):

```
┌─────────────────────────────────────────────────────────────────┐
│                   USER APPLICATION LAYER                        │
│                                                                 │
│  Main application or workflow exposing high-level tasks        │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ calls
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│               LAYER 3: WORKFLOW ORCHESTRATION                   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ class ResearchWorkflow(Workflow):                       │   │
│  │   description = "..."                                  │   │
│  │   def run(self, topic):                                │   │
│  │       # Orchestrate Layer 2 agents                     │   │
│  │       yield from layer2_agent.run(topic)              │   │
│  └─────────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ uses
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│        LAYER 2: COMPOSITION/COORDINATOR AGENTS                  │
│                                                                 │
│  ┌────────────────────────────────────────────────────────┐    │
│  │ coordinator_agent = Agent(                             │    │
│  │   team=[fsa1, fsa2, fsa3],  # Layer 1 agents          │    │
│  │   instructions="Coordinate outputs...",               │    │
│  │ )                                                      │    │
│  └────────────────────────────────────────────────────────┘    │
└────────────────┬──────────────────────────────┬─────────────────┘
                 │                              │
                 │ coordinates                  │ coordinates
                 ▼                              ▼
┌──────────────────────────────────────────────────────────────────┐
│          LAYER 1: FOUNDATION FOCUSED SPECIALIZED AGENTS          │
│                                                                  │
│ ┌────────────────────┐  ┌────────────────────┐  ┌─────────────┐ │
│ │ WebSearcherFSA     │  │ ContentAnalyzerFSA │  │ WriterFSA   │ │
│ │                    │  │                    │  │             │ │
│ │ Tools:             │  │ Tools:             │  │ Tools:      │ │
│ │ - DuckDuckGo       │  │ - Newspaper4k      │  │ - (none)    │ │
│ │                    │  │                    │  │             │ │
│ │ Input: topic       │  │ Input: article URL │  │ Input: data │ │
│ │ Output: articles   │  │ Output: content    │  │ Output: doc │ │
│ └────────────────────┘  └────────────────────┘  └─────────────┘ │
│                                                                  │
│ ┌────────────────────┐  ┌────────────────────┐  ┌─────────────┐ │
│ │ StockAnalyzerFSA   │  │ MarketAnalystFSA   │  │ ... more    │ │
│ │                    │  │                    │  │  FSAs       │ │
│ │ Tools: YFinance    │  │ Tools: Various     │  │             │ │
│ │ ...                │  │ ...                │  │ ...         │ │
│ └────────────────────┘  └────────────────────┘  └─────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

---

## Directory Structure

```
agno/
├── libs/agno/agno/
│   ├── fsas/                           # NEW: All FSAs organized by domain
│   │   ├── __init__.py
│   │   ├── base_fsa.py                # NEW: Base FSA template class
│   │   │
│   │   ├── research/                  # Domain 1
│   │   │   ├── __init__.py
│   │   │   ├── web_searcher_fsa.py    # Layer 1 FSA
│   │   │   ├── content_analyzer_fsa.py
│   │   │   └── report_writer_fsa.py
│   │   │
│   │   ├── finance/                   # Domain 2
│   │   │   ├── __init__.py
│   │   │   ├── stock_analyzer_fsa.py
│   │   │   └── market_analyst_fsa.py
│   │   │
│   │   ├── code_generation/           # Domain 3
│   │   │   ├── __init__.py
│   │   │   ├── code_analyzer_fsa.py
│   │   │   ├── code_generator_fsa.py
│   │   │   └── code_reviewer_fsa.py
│   │   │
│   │   └── utils/
│   │       ├── __init__.py
│   │       └── fsa_registry.py        # FSA discovery & factory
│   │
│   ├── mla/                           # NEW: Multi-Layer Architecture
│   │   ├── __init__.py
│   │   ├── layers.py                 # Layer definitions
│   │   │
│   │   ├── composition/               # Layer 2
│   │   │   ├── __init__.py
│   │   │   ├── composition_base.py
│   │   │   ├── research_coordinator_fsa.py
│   │   │   └── finance_coordinator_fsa.py
│   │   │
│   │   ├── workflows/                 # Layer 3
│   │   │   ├── __init__.py
│   │   │   ├── mla_workflow.py       # Base MLA workflow
│   │   │   ├── research_workflow.py  # Concrete example
│   │   │   └── finance_workflow.py
│   │   │
│   │   └── registry/
│   │       ├── __init__.py
│   │       └── fsa_registry.py
│   │
│   ├── agent/                        # EXISTING: Agent framework
│   │   ├── __init__.py
│   │   ├── agent.py (4189 lines)    # Base Agent class
│   │   └── metrics.py
│   │
│   ├── workflow/                     # EXISTING: Workflow framework
│   │   ├── __init__.py
│   │   └── workflow.py               # Base Workflow class
│   │
│   ├── models/                       # EXISTING
│   │   ├── base.py
│   │   ├── message.py
│   │   └── response.py
│   │
│   ├── memory/                       # EXISTING
│   ├── storage/                      # EXISTING
│   ├── tools/                        # EXISTING
│   └── knowledge/                    # EXISTING
│
└── cookbook/
    ├── fsas/                         # NEW: FSA examples
    │   ├── research/
    │   ├── finance/
    │   └── code_generation/
    │
    └── mla/                          # NEW: MLA examples
        ├── research_workflow.py
        ├── finance_workflow.py
        └── code_generation_workflow.py
```

---

## Agent Base Class Signature

The base `Agent` class from `/home/user/agno/libs/agno/agno/agent/agent.py`:

```python
@dataclass(init=False)
class Agent:
    # Core Configuration
    model: Optional[Model] = None
    name: Optional[str] = None
    role: Optional[str] = None
    description: Optional[str] = None
    
    # Instructions & Behavior
    instructions: Optional[Union[str, List[str], Callable]] = None
    expected_output: Optional[str] = None
    goal: Optional[str] = None
    
    # Tools & Capabilities
    tools: Optional[List[Union[Toolkit, Callable, Function, Dict]]] = None
    show_tool_calls: bool = False
    tool_call_limit: Optional[int] = None
    
    # Team Management
    team: Optional[List[Agent]] = None
    respond_directly: bool = False
    
    # Memory & Knowledge
    memory: Optional[AgentMemory] = None
    knowledge: Optional[AgentKnowledge] = None
    
    # Session Management
    session_id: Optional[str] = None
    session_state: Optional[Dict[str, Any]] = None
    
    # Debug & Monitoring
    debug_mode: bool = False
    monitoring: bool = False
    telemetry: bool = True
    
    def run(
        self,
        message: Optional[Union[str, List, Dict, Message]] = None,
        *,
        stream: bool = False,
        **kwargs: Any,
    ) -> Union[RunResponse, Iterator[RunResponse]]: ...
    
    async def arun(self, ...) -> RunResponse: ...
```

---

## Workflow Base Class Signature

The base `Workflow` class from `/home/user/agno/libs/agno/agno/workflow/workflow.py`:

```python
@dataclass(init=False)
class Workflow:
    # Core Configuration
    name: Optional[str] = None
    workflow_id: Optional[str] = None
    description: Optional[str] = None
    
    # Session & State
    session_id: Optional[str] = None
    session_state: Dict[str, Any] = field(default_factory=dict)
    
    # Memory & Storage
    memory: Optional[WorkflowMemory] = None
    storage: Optional[Storage] = None
    
    # Debug & Monitoring
    debug_mode: bool = False
    monitoring: bool = False
    telemetry: bool = True
    
    def __init__(
        self,
        *,
        name: Optional[str] = None,
        workflow_id: Optional[str] = None,
        session_id: Optional[str] = None,
        session_state: Optional[Dict[str, Any]] = None,
        memory: Optional[WorkflowMemory] = None,
        storage: Optional[Storage] = None,
        **kwargs: Any,
    ): ...
    
    def run(self, **kwargs: Any): ...  # MUST OVERRIDE
    
    def run_workflow(self, **kwargs: Any): ...  # Entry point
    
    def write_to_storage(self) -> Optional[WorkflowSession]: ...
    
    def read_from_storage(self) -> Optional[WorkflowSession]: ...
```

---

## FSA Base Class Template

Recommended `BaseFSA` class to inherit from:

```python
class BaseFSA(Agent):
    """
    Base Focused Specialized Agent.
    
    Characteristics:
    - Single responsibility principle
    - Focused tooling
    - Clear input/output contracts
    - Reusable and composable
    """
    
    # FSA Metadata
    fsa_name: str = ""
    fsa_domain: str = ""
    fsa_responsibility: str = ""
    
    def __init__(
        self,
        model: Optional[Model] = None,
        name: Optional[str] = None,
        role: Optional[str] = None,
        tools: Optional[List[Union[Toolkit, Function]]] = None,
        instructions: Optional[str] = None,
        expected_output: Optional[str] = None,
        **kwargs: Any,
    ):
        """Initialize FSA with focused configuration."""
        super().__init__(
            model=model,
            name=name or self.fsa_name,
            role=role or self.fsa_responsibility,
            tools=tools,
            instructions=instructions or self._get_default_instructions(),
            expected_output=expected_output,
            show_tool_calls=False,
            markdown=True,
            **kwargs,
        )
    
    @staticmethod
    def _get_default_instructions() -> str:
        """Override to provide default instructions."""
        return ""
    
    def execute(self, input_data: Any, **kwargs: Any):
        """Execute FSA with input validation."""
        if not self.validate_input(input_data):
            raise ValueError(f"Invalid input: {input_data}")
        return self.run(str(input_data), **kwargs)
    
    def validate_input(self, input_data: Any) -> bool:
        """Override to validate input."""
        return input_data is not None
```

---

## MLA Base Workflow Template

Recommended `MLAWorkflow` class for orchestration:

```python
class MLAWorkflow(Workflow):
    """
    Base Multi-Layer Architecture Workflow.
    
    Layers:
    - Layer 1: Foundation FSAs (specific tasks)
    - Layer 2: Composition/Coordinator FSAs (orchestrate Layer 1)
    - Layer 3: Workflow (expose to users)
    """
    
    description: str = ""
    
    # Override with Layer 1 FSAs as class attributes
    # Example:
    # web_searcher: Agent = WebSearcherFSA(...)
    # content_analyzer: Agent = ContentAnalyzerFSA(...)
    # report_writer: Agent = WriterFSA(...)
    
    def run(self, **kwargs: Any) -> Iterator[RunResponse]:
        """
        Orchestrate Layer 1 & 2 FSAs.
        
        Must override to define workflow steps.
        """
        logger.error(f"{self.__class__.__name__}.run() not implemented")
        return iter([])
    
    def _execute_fsa(
        self,
        fsa: Agent,
        input_data: Any,
        **kwargs: Any,
    ) -> RunResponse:
        """
        Helper to execute an FSA.
        
        Args:
            fsa: The FSA (Agent) to execute
            input_data: Input for the FSA
            **kwargs: Additional run parameters
            
        Returns:
            RunResponse from FSA execution
        """
        return fsa.run(str(input_data), **kwargs)
    
    def _cache_result(
        self,
        key: str,
        value: Any,
    ) -> None:
        """Cache intermediate result in session_state."""
        self.session_state[key] = value
        self.write_to_storage()
    
    def _get_cached(self, key: str) -> Optional[Any]:
        """Retrieve cached result from session_state."""
        return self.session_state.get(key)
```

---

## Integration with Existing Framework

### 1. How FSAs Integrate with Agent
```python
# FSA is a specialized Agent instance
fsa = WebSearcherFSA(model=OpenAIChat(id="gpt-4o"))

# Can be used like any Agent
response = fsa.execute("AI breakthroughs")
response = fsa.run("AI breakthroughs", stream=True)
```

### 2. How Workflows Orchestrate FSAs
```python
# Workflow has FSAs as class attributes
class ResearchWorkflow(Workflow):
    web_searcher: Agent = WebSearcherFSA(...)
    analyzer: Agent = ContentAnalyzerFSA(...)
    writer: Agent = WriterFSA(...)
    
    def run(self, topic: str):
        # Call FSAs in orchestrated sequence
        search_results = self.web_searcher.run(topic)
        analysis = self.analyzer.run(search_results.content)
        yield from self.writer.run(analysis.content, stream=True)
```

### 3. How Teams Coordinate FSAs
```python
# Team is a coordinating Agent with sub-agents
coordinator = Agent(
    team=[searcher_fsa, analyzer_fsa, writer_fsa],
    instructions="Coordinate findings...",
)

# Team automatically routes requests
response = coordinator.run("Research topic", stream=True)
```

---

## Key Differences: FSA vs Agent vs Workflow vs MLA

| Aspect | FSA | Agent | Workflow | MLA |
|--------|-----|-------|----------|-----|
| **Scope** | Single task | Flexible | Multi-step | Hierarchical |
| **Responsibility** | Narrow | General | Orchestration | Architecture |
| **Reusability** | High | Medium | Low | Very High |
| **Composition** | As team member | Direct use | Layer 1 attribute | 3-layer design |
| **Specialization** | Deep | General | None | Structured |
| **Tools** | Focused | Any | None | Focused (Layer 1) |
| **Execution** | Direct | Direct | Orchestrated | Orchestrated |

---

## Implementation Patterns

### Pattern 1: Create a Simple FSA
```python
class MyFSA(Agent):
    def __init__(self, model: Model):
        super().__init__(
            model=model,
            name="MyFSA",
            role="Do one specific thing",
            tools=[SpecificTool()],
            instructions="Clear steps...",
        )

# Usage
fsa = MyFSA(model=OpenAIChat(id="gpt-4o"))
result = fsa.run("input", stream=True)
```

### Pattern 2: Compose FSAs in a Team
```python
coordinator = Agent(
    team=[fsa1, fsa2, fsa3],
    instructions="Coordinate team...",
)
result = coordinator.run("task", stream=True)
```

### Pattern 3: Orchestrate FSAs in Workflow
```python
class MyWorkflow(Workflow):
    fsa1: Agent = MyFSA1(...)
    fsa2: Agent = MyFSA2(...)
    
    def run(self, topic: str) -> Iterator[RunResponse]:
        result1 = self.fsa1.run(topic)
        yield from self.fsa2.run(result1.content, stream=True)

workflow = MyWorkflow(storage=SqliteStorage(...))
for response in workflow.run_workflow(topic="example"):
    print(response.content)
```

### Pattern 4: Multi-Layer MLA
```python
# Layer 1: FSAs
searcher = WebSearcherFSA(...)
analyzer = AnalyzerFSA(...)

# Layer 2: Coordinator
coordinator = Agent(team=[searcher, analyzer], ...)

# Layer 3: Workflow
class MLAWorkflow(Workflow):
    coordinator: Agent = coordinator
    def run(self, topic):
        yield from self.coordinator.run(topic, stream=True)
```

---

## Common FSA Domains

Based on cookbook examples, recommended FSA domains:

```
research/
├── web_searcher_fsa.py       # Search web for information
├── content_analyzer_fsa.py   # Extract & analyze content
├── report_writer_fsa.py      # Generate reports
└── knowledge_linker_fsa.py   # Link knowledge sources

finance/
├── stock_analyzer_fsa.py     # Analyze stocks
├── market_analyst_fsa.py     # Analyze markets
├── risk_analyzer_fsa.py      # Risk assessment
└── portfolio_optimizer_fsa.py # Portfolio optimization

code_generation/
├── code_analyzer_fsa.py      # Analyze code
├── code_generator_fsa.py     # Generate code
├── code_reviewer_fsa.py      # Review code
└── test_writer_fsa.py        # Write tests

content/
├── blog_analyzer_fsa.py      # Analyze blogs
├── social_media_planner_fsa.py # Plan posts
├── content_generator_fsa.py  # Generate content
└── content_optimizer_fsa.py  # Optimize content
```

---

## Execution Flow

### Single FSA Execution
```
User Input → FSA.run() → Tool Calls → LLM Response → RunResponse
```

### Team Execution
```
User Input → Coordinator.run() 
          → Routes to FSA1 → Tool Calls → LLM Response
          → Routes to FSA2 → Tool Calls → LLM Response
          → Combines responses → RunResponse
```

### Workflow Execution
```
User Input → Workflow.run_workflow()
          → FSA1.run() → Cache result
          → FSA2.run(cached1) → Cache result
          → FSA3.run(cached2) → Stream response
          → Write to storage → Complete
```

### MLA Execution
```
User Input → Workflow.run() (Layer 3)
          → Coordinator.run() (Layer 2)
          → FSA.run() (Layer 1)
          → Tool Calls → LLM
          ← Responses propagate back up
          → Final output
```

---

## Performance Characteristics

- **Agent Creation**: ~2μs per agent (very fast)
- **Memory per Agent**: ~3.75KB
- **FSA Overhead**: Negligible (inherits from Agent)
- **Team Coordination**: Linear with team size
- **Workflow Overhead**: Minimal (just orchestration)
- **MLA Overhead**: Linear with layer count

---

## Files to Create/Modify

### For FSA Support:
- [ ] `/home/user/agno/libs/agno/agno/fsas/__init__.py` - Create
- [ ] `/home/user/agno/libs/agno/agno/fsas/base_fsa.py` - Create
- [ ] `/home/user/agno/libs/agno/agno/fsas/*/` - Create domain directories

### For MLA Support:
- [ ] `/home/user/agno/libs/agno/agno/mla/__init__.py` - Create
- [ ] `/home/user/agno/libs/agno/agno/mla/layers.py` - Create
- [ ] `/home/user/agno/libs/agno/agno/mla/composition/` - Create
- [ ] `/home/user/agno/libs/agno/agno/mla/workflows/` - Create

### For Examples:
- [ ] `/home/user/agno/cookbook/fsas/` - Create
- [ ] `/home/user/agno/cookbook/mla/` - Create

---

## Documentation References

1. **Base Agent**: `/home/user/agno/libs/agno/agno/agent/agent.py` (4189 lines)
2. **Workflow**: `/home/user/agno/libs/agno/agno/workflow/workflow.py`
3. **Examples**: `/home/user/agno/cookbook/examples/`
4. **Getting Started**: `/home/user/agno/cookbook/getting_started/`

---

## Recommended Workflow

1. **Start**: Define Layer 1 FSAs (focused specialists)
2. **Compose**: Create Layer 2 Coordinators if needed
3. **Orchestrate**: Create Layer 3 Workflows for end-to-end tasks
4. **Test**: Test each layer independently then integrated
5. **Register**: Add to FSA registry for discovery
6. **Document**: Add docstrings and examples


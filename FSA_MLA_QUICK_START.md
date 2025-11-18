# FSA & MLA Quick Start Guide

## What You Need to Know

This repository contains comprehensive documentation on implementing **Focused Specialized Agents (FSAs)** and **Multi-Layer Architecture (MLA)** in the Agno framework.

## Documentation Files

### 1. FSA_MLA_SUMMARY.md (22 KB)
**Start here for the complete overview**
- High-level architecture overview with diagrams
- Directory structure for FSAs and MLA
- Base class signatures and templates
- Integration points with existing framework
- Performance characteristics
- Implementation checklist

### 2. FSA_MLA_EXPLORATION.md (21 KB)
**Deep dive into framework analysis**
- Codebase structure and file locations
- Detailed Agent class attributes (60+ fields)
- Workflow class structure
- Existing agent implementation patterns
- Configuration patterns for every feature
- Base classes and interfaces
- 5 different implementation examples

### 3. FSA_MLA_CONCRETE_EXAMPLES.md (24 KB)
**Real code examples from the cookbook**
- Pattern 1: Simple Single-Purpose FSA (Finance domain)
- Pattern 2: Specialized Agents in Team (Chess example)
- Pattern 3: Workflow with FSA Composition (Research workflow)
- Pattern 4: Agent Team Coordination
- Concrete directory structure
- BaseFSA template implementation
- Concrete FSA implementation example

## Quick Comparison

| Document | Best For | Key Sections |
|----------|----------|--------------|
| **SUMMARY** | Overview & planning | Architecture diagram, directory layout, class signatures |
| **EXPLORATION** | Deep understanding | Codebase analysis, all agent attributes, configuration patterns |
| **CONCRETE_EXAMPLES** | Hands-on learning | Real code from cookbook, implementation templates |

## The 3-Layer Architecture

```
LAYER 3: Workflow          (ResearchWorkflow, FinanceWorkflow)
    ↓
LAYER 2: Coordinator FSAs  (Team of specialized agents)
    ↓
LAYER 1: Foundation FSAs   (WebSearcher, Analyzer, Writer, etc.)
```

## Key Concepts

### FSA (Focused Specialized Agent)
- Single responsibility principle
- Narrow, deep specialization
- Focused tooling and instructions
- Clear input/output contracts
- Reusable across contexts

### MLA (Multi-Layer Architecture)
- Layer 1: Foundation FSAs (basic tasks)
- Layer 2: Composition FSAs (orchestrate Layer 1)
- Layer 3: Workflow Layer (high-level user interface)

## Implementation Steps

### 1. Create a Simple FSA
```python
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.duckduckgo import DuckDuckGoTools

web_searcher = Agent(
    name="WebSearcher",
    role="Search the web",
    model=OpenAIChat(id="gpt-4o"),
    tools=[DuckDuckGoTools()],
    instructions="Search for information...",
)

result = web_searcher.run("topic", stream=True)
```

### 2. Create a Team of FSAs
```python
coordinator = Agent(
    team=[web_searcher, analyzer, writer],
    instructions="Coordinate the team...",
)

result = coordinator.run("task", stream=True)
```

### 3. Create a Workflow with FSAs
```python
from agno.workflow import Workflow

class ResearchWorkflow(Workflow):
    web_searcher: Agent = Agent(...)
    analyzer: Agent = Agent(...)
    writer: Agent = Agent(...)
    
    def run(self, topic: str):
        search_results = self.web_searcher.run(topic)
        analysis = self.analyzer.run(search_results.content)
        yield from self.writer.run(analysis.content, stream=True)

workflow = ResearchWorkflow()
for response in workflow.run_workflow(topic="AI"):
    print(response.content)
```

### 4. Create MLA with 3 Layers
```python
# Layer 1: FSAs
web_searcher = WebSearcherFSA(...)
analyzer = AnalyzerFSA(...)
writer = WriterFSA(...)

# Layer 2: Coordinator (team of Layer 1)
coordinator = Agent(team=[web_searcher, analyzer, writer])

# Layer 3: Workflow (orchestrate everything)
class ResearchMLAWorkflow(Workflow):
    coordinator: Agent = coordinator
    
    def run(self, topic: str):
        yield from self.coordinator.run(topic, stream=True)
```

## Directory Structure You'll Create

```
agno/libs/agno/agno/
├── fsas/                      # All FSAs by domain
│   ├── base_fsa.py           # Base template
│   ├── research/             # Domain 1
│   ├── finance/              # Domain 2
│   ├── code_generation/      # Domain 3
│   └── utils/
│
└── mla/                       # Multi-Layer Architecture
    ├── layers.py
    ├── composition/           # Layer 2
    ├── workflows/             # Layer 3
    └── registry/
```

## Key Files in Agno Framework

| File | Purpose | Lines |
|------|---------|-------|
| `agent/agent.py` | Base Agent class | 4189 |
| `workflow/workflow.py` | Base Workflow class | ~800 |
| `models/base.py` | Model interface | - |
| `tools/toolkit.py` | Toolkit base | - |
| `storage/base.py` | Storage interface | - |

## Common FSA Domains

- **research**: Web search, content analysis, report writing
- **finance**: Stock analysis, market analysis, portfolio optimization
- **code_generation**: Code analysis, code generation, code review
- **content**: Blog analysis, social media planning, content generation

## Recommended Reading Order

1. **Start with FSA_MLA_SUMMARY.md**
   - Get the big picture
   - Understand the 3-layer architecture
   - See the directory structure

2. **Read FSA_MLA_CONCRETE_EXAMPLES.md**
   - Study real code from cookbook
   - Understand implementation patterns
   - See concrete examples

3. **Dive into FSA_MLA_EXPLORATION.md**
   - Understand all agent attributes
   - Learn configuration patterns
   - Explore framework details

## Key Takeaways

- FSAs are specialized agents with single responsibility
- MLA provides hierarchical organization in 3 layers
- All FSAs inherit from `Agent` class
- Use `Workflow` to orchestrate FSAs
- Use `Agent.team` to coordinate FSAs
- Session state stores intermediate results
- Storage persists workflow state

## Files to Create

### FSA Files
- [ ] `libs/agno/agno/fsas/__init__.py`
- [ ] `libs/agno/agno/fsas/base_fsa.py`
- [ ] `libs/agno/agno/fsas/research/`
- [ ] `libs/agno/agno/fsas/finance/`
- [ ] `libs/agno/agno/fsas/code_generation/`

### MLA Files
- [ ] `libs/agno/agno/mla/__init__.py`
- [ ] `libs/agno/agno/mla/layers.py`
- [ ] `libs/agno/agno/mla/composition/`
- [ ] `libs/agno/agno/mla/workflows/`

### Example Files
- [ ] `cookbook/fsas/`
- [ ] `cookbook/mla/`

## Questions Answered in Documentation

- **What is an FSA?** → See SUMMARY.md "FSA Architecture"
- **How do I create one?** → See CONCRETE_EXAMPLES.md "Pattern 1"
- **How do I compose FSAs?** → See CONCRETE_EXAMPLES.md "Pattern 2-4"
- **What are all the Agent attributes?** → See EXPLORATION.md "Agent Class Structure"
- **How do I use workflows?** → See CONCRETE_EXAMPLES.md "Pattern 3"
- **What's the directory layout?** → See SUMMARY.md "Directory Structure"

## Performance Notes

- Agent creation: ~2μs
- Memory per agent: ~3.75KB
- FSA overhead: Negligible
- Team coordination: Linear with team size

## Next Steps

1. Read FSA_MLA_SUMMARY.md (10 min)
2. Review CONCRETE_EXAMPLES.md (15 min)
3. Explore EXPLORATION.md for details (20 min)
4. Start implementing FSAs in `libs/agno/agno/fsas/`
5. Create workflows in `cookbook/mla/`

---

**For detailed information, see:**
- FSA_MLA_SUMMARY.md - Architecture & overview
- FSA_MLA_EXPLORATION.md - Framework analysis
- FSA_MLA_CONCRETE_EXAMPLES.md - Real code examples

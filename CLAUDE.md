# CLAUDE.md - AI Assistant Guide for Agno Development

This document provides comprehensive guidance for AI assistants working on the Agno codebase. It covers the repository structure, development workflows, coding conventions, and best practices.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Repository Structure](#repository-structure)
3. [Development Environment Setup](#development-environment-setup)
4. [Coding Conventions](#coding-conventions)
5. [Architecture Patterns](#architecture-patterns)
6. [Testing Guidelines](#testing-guidelines)
7. [Development Workflow](#development-workflow)
8. [Adding New Components](#adding-new-components)
9. [Common Tasks](#common-tasks)
10. [Important Files and Directories](#important-files-and-directories)
11. [Performance Considerations](#performance-considerations)
12. [Documentation Standards](#documentation-standards)

---

## Project Overview

**Agno** is a lightweight, high-performance framework for building multi-modal AI agents with memory, knowledge, and tools.

### Key Characteristics
- **Lightweight**: Agent instantiation ~2μs (~10,000x faster than LangGraph)
- **Model Agnostic**: Supports 23+ LLM providers (OpenAI, Anthropic, Google, Cohere, AWS Bedrock, Azure, etc.)
- **Multi-Modal**: Native support for text, image, audio, and video
- **Production-Ready**: Comprehensive memory, storage, and deployment options
- **Developer-Friendly**: 100+ cookbook examples, extensive documentation

### License
Mozilla Public License 2.0 (MPL-2.0)

### Python Support
- Minimum: Python 3.7
- Maximum: Python 3.12
- Recommended: Python 3.12 for development

---

## Repository Structure

### Top-Level Organization

```
/home/user/agno/
├── .github/              # CI/CD workflows, issue templates, PR templates
├── cookbook/             # 100+ examples and tutorials
├── evals/               # Performance, accuracy, and reliability evaluations
├── libs/                # Core library code (monorepo structure)
│   ├── agno/           # Main Agno library
│   ├── infra/
│   │   ├── agno_docker/ # Docker infrastructure package
│   │   └── agno_aws/    # AWS infrastructure package
├── scripts/            # Build and development scripts
├── .editorconfig       # Editor configuration
├── .gitignore         # Git ignore rules
├── CODEOWNERS         # Code ownership
├── CODE_OF_CONDUCT.md # Community guidelines
├── CONTRIBUTING.md    # Contribution guidelines
├── LICENSE            # MPL 2.0 license
└── README.md          # Project documentation
```

### Core Library Structure (`libs/agno/agno/`)

The main library is organized into modular components:

#### **Agent System** (`agent/`)
- `agent.py` - Main Agent implementation (~4,200 lines)
- `metrics.py` - Performance metrics tracking

#### **Models** (`models/`) - 23+ Providers
Major providers include:
- `anthropic/` - Claude models
- `openai/` - GPT models + OpenAI-like base class
- `google/` - Gemini models
- `aws/` - AWS Bedrock
- `azure/` - Azure OpenAI
- `cohere/` - Cohere models
- `groq/`, `mistral/`, `ollama/`, `deepseek/`, `xai/`, etc.

#### **Tools** (`tools/`) - 70+ Pre-built Tools
Categories:
- **Web Search**: DuckDuckGo, Google, Exa, Tavily, SerpAPI
- **APIs**: GitHub, Gmail, Google Calendar, Google Sheets, Google Maps, Slack, Discord
- **Databases**: DuckDB, Postgres, SQL
- **Media**: YouTube, DALL-E, ElevenLabs, Replicate
- **Finance**: YFinance, OpenBB
- **Web Scraping**: Firecrawl, Crawl4AI, Newspaper4k, Browserbase
- **AI/ML**: MCP (Model Context Protocol), AgentQL, Fal

#### **Knowledge Management** (`knowledge/`)
- `agent.py` - Agentic RAG implementation
- Knowledge sources: PDF, DOCX, CSV, JSON, ArXiv, Wikipedia, YouTube, Website
- URL-based: PDF URL, CSV URL
- LangChain and LlamaIndex integration
- S3 support for cloud documents

#### **Vector Databases** (`vectordb/`) - 12 Implementations
- LanceDB, PGVector, ChromaDB, Qdrant, Pinecone
- MongoDB, SingleStore, Cassandra, Weaviate, Milvus
- ClickHouse, Upstash

#### **Embedders** (`embedder/`) - 13 Implementations
- OpenAI, Azure OpenAI, Cohere, Google, Mistral
- Ollama, VoyageAI, HuggingFace, SentenceTransformer
- FastEmbed, Fireworks, Together

#### **Storage** (`storage/`)
Backends: SQLite, PostgreSQL, MongoDB, YAML, JSON, DynamoDB, SingleStore
Subdirectories:
- `agent/` - Agent-specific storage
- `session/` - Session management
- `workflow/` - Workflow state

#### **Memory** (`memory/`)
- `agent.py` - Agent memory (~15,675 bytes)
- `manager.py` - Memory manager
- `summarizer.py` - Memory summarization
- `classifier.py` - Memory classification
- `db/` - Database backends

#### **Document Processing** (`document/`)
- **Readers** (`reader/`): PDF, DOCX, CSV, JSON, Text, ArXiv, URL, Website, YouTube
- **Chunking** (`chunking/`): Fixed, Recursive, Semantic, Agentic, Document-aware

#### **Reasoning** (`reasoning/`)
- `default.py` - Default reasoning
- `openai.py` - OpenAI o1/o3 reasoning
- `deepseek.py` - DeepSeek R1 reasoning
- `groq.py` - Groq reasoning
- `step.py` - Reasoning steps

#### **Workflow** (`workflow/`)
- `workflow.py` - Workflow orchestration (~26,000 bytes)

#### **API & CLI**
- **API** (`api/`): Agent API, Playground API, User/Team/Workspace management
- **CLI** (`cli/`): Entry point, config, operator commands, auth

#### **Utilities** (`utils/`)
30+ utility modules: JSON schema, OpenAI helpers, formatting, logging, git, filesystem, etc.

#### **Other Modules**
- `run/` - Response handling
- `file/` - File management
- `eval/` - Evaluation helpers
- `infra/` - Infrastructure config
- `playground/` - Interactive development
- `workspace/` - Multi-agent workspaces

### Cookbook Structure (`cookbook/`)

- **getting_started/** - 19 beginner examples
- **agent_concepts/** - Advanced concepts (async, RAG, memory, teams, multimodal)
- **models/** - Provider-specific examples (23 providers)
- **tools/** - Tool usage examples
- **storage/** - Storage backend examples
- **workflows/** - Complete workflow examples
- **examples/** - Full applications
- **hackathon/** - Hackathon resources
- **playground/** - Interactive examples

### Evaluations (`evals/`)

- **accuracy/** - Accuracy evaluations
- **reliability/** - Reliability tests
- **performance/** - Performance benchmarks (vs LangGraph, CrewAI)

---

## Development Environment Setup

### Prerequisites
- Python 3.7+ (3.12 recommended for development)
- `uv` package manager (recommended) or `pip`

### Setup Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/agno-agi/agno.git
   cd agno
   ```

2. **Check for uv**
   ```bash
   uv --version
   # If not installed:
   pip install uv
   ```

3. **Run development setup**
   ```bash
   # Unix/Linux/macOS
   ./scripts/dev_setup.sh

   # Windows
   .\scripts\dev_setup.bat
   ```

   This will:
   - Create a `.venv` virtual environment
   - Install all required packages
   - Install `agno`, `agno-docker`, and `agno-aws` in editable mode

4. **Activate virtual environment**
   ```bash
   # Unix/Linux/macOS
   source .venv/bin/activate

   # Windows
   .venv\Scripts\activate
   ```

5. **Install additional dependencies**
   ```bash
   # Use uv pip for all package installations
   uv pip install <package-name>
   ```

### Development Scripts

Located in `/home/user/agno/scripts/`:

- **`dev_setup.sh`** - Initial development setup
- **`format.sh`** - Format code (all libraries + cookbook)
- **`validate.sh`** - Validate code (formatting, linting, type checking)
- **`test.sh`** - Run tests with coverage
- **`cookbook_setup.sh`** - Setup cookbook environment
- **`perf_setup.sh`** - Setup performance evaluation environment

Library-specific scripts in `libs/agno/scripts/`, `libs/infra/agno_docker/scripts/`, etc.

---

## Coding Conventions

### Code Style

#### Formatting
- **Formatter**: Ruff
- **Line Length**: 120 characters
- **Import Violations**: Ignored in `__init__.py` files (F401)

#### Indentation (`.editorconfig`)
- **Python**: 4 spaces
- **Other files**: 2 spaces
- **Line Endings**: LF (Unix style)
- **Charset**: UTF-8
- **Trim trailing whitespace**: Yes
- **Insert final newline**: Yes

#### Type Checking
- **Type Checker**: mypy
- **Configuration**: Strict mode with Pydantic plugin
- **Check untyped defs**: Yes
- **No implicit optional**: Yes
- **Warn unused configs**: Yes
- **Disable**: override errors
- **Exclude**: `tests*`

### Python Conventions

#### Imports
```python
from __future__ import annotations  # Always use for Python 3.7+ compatibility

from typing import Any, Optional, List, Dict
from pydantic import BaseModel

# Group imports: stdlib, third-party, local
```

#### Docstrings
Use Google-style docstrings for classes and functions:

```python
"""Summary line in triple quotes.

Longer description if needed. Explain the purpose and behavior.

Args:
    param1 (type): Description of param1.
    param2 (type): Description of param2.

Returns:
    type: Description of return value.

Example:
    >>> agent = Agent(model=OpenAIChat(id="gpt-4o"))
    >>> agent.print_response("Hello")
"""
```

#### File Headers
Cookbook examples should include informative headers:

```python
"""🗽 Feature Name - Brief Description

This example shows how to [main purpose].
[Additional context about what this demonstrates].

Example prompts to try:
- "Prompt 1"
- "Prompt 2"

Run `pip install <dependencies>` to install dependencies.
"""
```

#### Class Design
```python
from pydantic import BaseModel
from dataclasses import dataclass

# For data models - use Pydantic BaseModel
class MyModel(BaseModel):
    field1: str
    field2: Optional[int] = None

# For simple data containers - use dataclass
@dataclass
class MyData:
    field1: str
    field2: int = 0
```

#### Error Handling
```python
from agno.exceptions import ModelProviderError, StopAgentRun

# Use specific exceptions
try:
    result = some_operation()
except ImportError:
    raise ImportError("`package-name` not installed. Please install using `pip install package-name`")
```

### Naming Conventions

- **Classes**: PascalCase (`Agent`, `OpenAIChat`, `DuckDuckGoTools`)
- **Functions/Methods**: snake_case (`print_response`, `search_web`)
- **Variables**: snake_case (`session_id`, `max_results`)
- **Constants**: UPPER_SNAKE_CASE (`DEFAULT_TIMEOUT`, `MAX_RETRIES`)
- **Private**: Leading underscore (`_internal_method`, `_helper_function`)

---

## Architecture Patterns

### Plugin Architecture

Agno uses a consistent plugin architecture across modules:

#### Base Class Pattern
Each module defines a base class/interface:

```python
# Example: Vector Database base
class VectorDb:
    """Base class for vector databases"""

    def create(self): ...
    def search(self, query): ...
    def insert(self, documents): ...
    def delete(self): ...
```

#### Provider Implementation Pattern
Each provider implements the base interface:

```python
# Example: LanceDB implementation
class LanceDb(VectorDb):
    def __init__(self, uri: str, table_name: str, ...):
        super().__init__()
        # Provider-specific initialization

    def create(self):
        # LanceDB-specific implementation
        ...
```

### Module Organization Pattern

**Consistent structure for providers:**

```
models/
├── openai/
│   ├── __init__.py      # Export main classes
│   ├── chat.py          # OpenAIChat implementation
│   └── like.py          # OpenAILike base class for API-compatible providers
├── anthropic/
│   ├── __init__.py
│   └── claude.py        # Claude implementation
└── xai/
    ├── __init__.py
    └── xai.py           # xAI implementation (inherits OpenAILike)
```

**Key Points:**
1. Each provider gets its own directory (or file for simple implementations)
2. `__init__.py` exports the main classes
3. Complex providers have multiple files
4. OpenAI-compatible providers inherit from `OpenAILike`

### Toolkit Pattern (Tools)

Tools inherit from `Toolkit` base class:

```python
from agno.tools import Toolkit

class DuckDuckGoTools(Toolkit):
    def __init__(
        self,
        search: bool = True,
        news: bool = True,
        # ... other params
    ):
        super().__init__(name="duckduckgo")

        # Register functions conditionally
        if search:
            self.register(self.duckduckgo_search)
        if news:
            self.register(self.duckduckgo_news)

    def duckduckgo_search(self, query: str) -> str:
        """Search DuckDuckGo for a query."""
        # Implementation
        ...
```

### Agent-First Design

Agents are the core abstraction:

```python
from agno.agent import Agent
from agno.models.openai import OpenAIChat

agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    tools=[...],           # Optional tools
    knowledge=...,         # Optional knowledge base
    storage=...,          # Optional storage
    memory=...,           # Optional memory
    instructions="...",   # Optional instructions
    description="...",    # Optional description
)

# Simple, Pythonic API
response = agent.run("Your query")
agent.print_response("Your query", stream=True)
```

### Dependency Injection

Optional dependencies are clearly separated:

```python
# In pyproject.toml
[project.optional-dependencies]
anthropic = ["anthropic"]
pgvector = ["pgvector"]

# In code - graceful handling
try:
    from anthropic import Anthropic
except ImportError:
    raise ImportError(
        "`anthropic` not installed. "
        "Please install using `pip install 'agno[anthropic]'`"
    )
```

---

## Testing Guidelines

### Test Structure

```
libs/agno/tests/
├── unit/                # Unit tests
│   ├── storage/
│   ├── vector_dbs/
│   ├── tools/
│   └── utils/
└── integration/         # Integration tests
    ├── agent/
    ├── knowledge/
    ├── storage/
    ├── teams/
    └── tools/
```

### Test Framework

- **Framework**: pytest
- **Async Support**: pytest-asyncio (mode: auto)
- **Coverage**: pytest-cov
- **Timeout**: timeout-decorator

### Running Tests

```bash
# All tests with coverage
./scripts/test.sh

# Specific test file
pytest ./libs/agno/tests/unit/utils/test_string.py

# Specific test function
pytest ./libs/agno/tests/unit/utils/test_string.py::test_parse_json

# Integration tests
pytest ./libs/agno/tests/integration/
```

### Writing Tests

```python
import pytest
from agno.agent import Agent
from agno.models.openai import OpenAIChat

def test_basic_agent():
    """Test basic agent creation and response."""
    agent = Agent(model=OpenAIChat(id="gpt-4o"))
    response = agent.run("Hello")
    assert response is not None

@pytest.mark.asyncio
async def test_async_agent():
    """Test async agent."""
    agent = Agent(model=OpenAIChat(id="gpt-4o"))
    response = await agent.arun("Hello")
    assert response is not None
```

### Test Requirements

1. **Unit tests** for new utilities and helpers
2. **Integration tests** for new providers, tools, vector databases
3. **Coverage**: Aim for high coverage on core modules
4. **Async**: Use `@pytest.mark.asyncio` for async tests
5. **Fixtures**: Use fixtures for common test setup

---

## Development Workflow

### Before Starting Work

1. **Check git status**
   ```bash
   git status
   git pull origin main
   ```

2. **Create feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

### During Development

1. **Make changes** following coding conventions

2. **Format code regularly**
   ```bash
   ./scripts/format.sh
   ```

3. **Validate code**
   ```bash
   ./scripts/validate.sh
   ```

4. **Run tests**
   ```bash
   ./scripts/test.sh
   # Or specific tests
   pytest ./libs/agno/tests/unit/...
   ```

### Before Committing

**CRITICAL**: Always run before submitting PR:

```bash
# 1. Format
./scripts/format.sh

# 2. Validate (formatting, linting, type checking)
./scripts/validate.sh

# 3. Test
./scripts/test.sh
```

### Committing Changes

```bash
git add <files>
git commit -m "Brief description of changes

Longer description if needed.
- Change 1
- Change 2
"
```

### Creating Pull Requests

1. Push to your branch
   ```bash
   git push origin feature/your-feature-name
   ```

2. Create PR on GitHub
   - Clear title describing the change
   - Reference any related issues
   - Include examples/screenshots if applicable

3. Ensure CI passes
   - GitHub Actions will run validation and tests
   - Fix any failures before requesting review

---

## Adding New Components

### Adding a New Model Provider

1. **Setup environment** (see [Development Environment Setup](#development-environment-setup))

2. **Create provider directory**
   ```bash
   mkdir -p libs/agno/agno/models/<provider_name>
   ```

3. **Implement the model**

   **If OpenAI API-compatible:**
   ```python
   # libs/agno/agno/models/<provider>/provider.py
   from agno.models.openai.like import OpenAILike

   class ProviderChat(OpenAILike):
       id: str = "model-id"
       name: str = "ProviderName"
       provider: str = "Provider"

       api_key: Optional[str] = None
       base_url: str = "https://api.provider.com/v1"
   ```

   **If custom API:**
   - Study `agno/models/anthropic/claude.py` or `agno/models/cohere/chat.py`
   - Implement the Model interface
   - Reach out on Discord for guidance

4. **Create `__init__.py`**
   ```python
   # libs/agno/agno/models/<provider>/__init__.py
   from agno.models.<provider>.<provider> import ProviderChat

   __all__ = ["ProviderChat"]
   ```

5. **Add optional dependency**
   ```toml
   # libs/agno/pyproject.toml
   [project.optional-dependencies]
   provider = ["provider-sdk"]
   ```

6. **Add cookbook example**
   ```bash
   mkdir -p cookbook/providers/<provider>
   # Add example showing how to use the provider
   ```

7. **Format and validate**
   ```bash
   ./scripts/format.sh
   ./scripts/validate.sh
   ```

8. **Submit PR** (see [Creating Pull Requests](#creating-pull-requests))

### Adding a New Tool

1. **Setup environment**

2. **Create tool file**
   ```python
   # libs/agno/agno/tools/<tool_name>.py
   from typing import Optional
   from agno.tools import Toolkit

   try:
       from some_package import SomeClient
   except ImportError:
       raise ImportError(
           "`some-package` not installed. "
           "Please install using `pip install some-package`"
       )

   class ToolNameTools(Toolkit):
       def __init__(
           self,
           feature1: bool = True,
           feature2: bool = False,
           api_key: Optional[str] = None,
       ):
           super().__init__(name="tool_name")

           self.api_key = api_key

           # Register functions conditionally
           if feature1:
               self.register(self.feature1_function)
           if feature2:
               self.register(self.feature2_function)

       def feature1_function(self, param: str) -> str:
           """Description of what this function does.

           Args:
               param: Description of parameter.

           Returns:
               Description of return value.
           """
           # Implementation
           ...
   ```

3. **Add optional dependency**
   ```toml
   # libs/agno/pyproject.toml
   [project.optional-dependencies]
   toolname = ["some-package"]

   tools = [
       # ... existing tools
       "agno[toolname]",
   ]
   ```

4. **Add cookbook example**
   ```bash
   # cookbook/tools/<tool_name>.py
   ```

5. **Format, validate, test**
   ```bash
   ./scripts/format.sh
   ./scripts/validate.sh
   ./scripts/test.sh
   ```

6. **Submit PR**

### Adding a New Vector Database

1. **Setup environment**

2. **Create vectordb directory**
   ```bash
   mkdir -p libs/agno/agno/vectordb/<db_name>
   ```

3. **Implement VectorDb interface**
   ```python
   # libs/agno/agno/vectordb/<db_name>/<db_name>.py
   from agno.vectordb.base import VectorDb

   class DbNameVectorDb(VectorDb):
       def __init__(self, ...):
           super().__init__()
           # Implementation

       def create(self):
           """Create the vector database."""
           ...

       def search(self, query, limit=5):
           """Search for similar vectors."""
           ...

       # Implement other required methods
   ```

4. **Study existing implementation**
   - Reference: `libs/agno/agno/vectordb/pgvector/pgvector.py`

5. **Create `__init__.py`**
   ```python
   # libs/agno/agno/vectordb/<db_name>/__init__.py
   from agno.vectordb.<db_name>.<db_name> import DbNameVectorDb

   __all__ = ["DbNameVectorDb"]
   ```

6. **Add optional dependency**
   ```toml
   # libs/agno/pyproject.toml
   [project.optional-dependencies]
   dbname = ["dbname-client"]

   vectordbs = [
       # ... existing dbs
       "agno[dbname]",
   ]
   ```

7. **Add cookbook example**
   ```bash
   # cookbook/agent_concepts/knowledge/vector_dbs/<db_name>.py
   ```

8. **Format, validate, test**

9. **Submit PR**

---

## Common Tasks

### Running Examples

```bash
# Activate virtual environment
source .venv/bin/activate

# Set API key
export OPENAI_API_KEY=sk-...

# Run example
python cookbook/getting_started/01_basic_agent.py
```

### Checking Code Quality

```bash
# Format with Ruff
./scripts/format.sh

# Validate (format, lint, type check)
./scripts/validate.sh
```

### Running Performance Benchmarks

```bash
# Setup performance environment
./scripts/perf_setup.sh
source .venvs/perfenv/bin/activate

# Run Agno benchmark
python evals/performance/instantiation_with_tool.py

# Run comparison (LangGraph)
python evals/performance/other/langgraph_instantiation.py
```

### Debugging

```python
# Enable debug logging
from agno.utils.log import set_log_level_to_debug
set_log_level_to_debug()

# Or via environment variable
export AGNO_LOG_LEVEL=DEBUG
```

### Working with the CLI

```bash
# Install in dev mode (done by dev_setup.sh)
uv pip install -e libs/agno

# CLI is now available
ag --help
agno --help

# Common commands
ag init         # Initialize a new agent project
ag serve        # Start the playground server
```

---

## Important Files and Directories

### Critical Files to Know

| File | Purpose |
|------|---------|
| `libs/agno/agno/agent/agent.py` | Core Agent implementation (~4,200 lines) |
| `libs/agno/pyproject.toml` | Main package configuration, dependencies |
| `libs/agno/agno/models/openai/like.py` | Base class for OpenAI-compatible providers |
| `libs/agno/agno/tools/toolkit.py` | Base class for tools |
| `libs/agno/agno/vectordb/base.py` | Vector database interface |
| `CONTRIBUTING.md` | Contribution guidelines |
| `README.md` | Project overview and quick start |

### Configuration Files

| File | Purpose |
|------|---------|
| `.editorconfig` | Editor configuration (indentation, line endings) |
| `pyproject.toml` | Package configuration, dependencies, tool settings |
| `.github/workflows/test.yml` | CI test workflow |
| `.github/workflows/performance.yml` | Performance benchmark workflow |

### Scripts Directory

| Script | Purpose |
|--------|---------|
| `scripts/dev_setup.sh` | Initial development setup |
| `scripts/format.sh` | Format all code |
| `scripts/validate.sh` | Validate all code |
| `scripts/test.sh` | Run all tests |

---

## Performance Considerations

### Why Performance Matters

Agno is designed for **high-performance agentic systems**:
- AI workflows can spawn thousands of agents
- Even small inefficiencies compound at scale
- Performance is a core design principle

### Key Metrics

- **Agent instantiation**: ~2μs (~10,000x faster than LangGraph)
- **Memory footprint**: ~3.75KiB (~50x less than LangGraph)

### Performance Best Practices

1. **Minimize instantiation overhead**
   - Keep Agent initialization lightweight
   - Lazy-load dependencies when possible

2. **Efficient tool calls**
   - Parallelize independent tool calls
   - Cache results where appropriate

3. **Memory management**
   - Use memory summarization for long conversations
   - Clean up sessions when done

4. **Model selection**
   - Choose appropriate models for tasks
   - Use smaller models for simple tasks

### Running Benchmarks

```bash
# Setup
./scripts/perf_setup.sh
source .venvs/perfenv/bin/activate

# Instantiation benchmark
python evals/performance/instantiation_with_tool.py

# Memory benchmark
python evals/performance/memory_usage.py
```

---

## Documentation Standards

### Inline Documentation

1. **Docstrings**: All public classes, methods, and functions should have docstrings
2. **Type hints**: Use type hints for all function parameters and return values
3. **Comments**: Explain complex logic, not obvious code

### Example Documentation

```python
"""Brief one-line summary.

Longer description explaining the purpose, behavior, and usage.

Args:
    param1 (str): Description of param1.
    param2 (Optional[int]): Description of param2. Defaults to None.

Returns:
    bool: Description of return value.

Raises:
    ValueError: When parameter is invalid.
    ImportError: When required package is not installed.

Example:
    >>> from agno.agent import Agent
    >>> agent = Agent(model=...)
    >>> result = agent.run("query")
"""
```

### Cookbook Examples

Every cookbook example should include:

1. **Header docstring** explaining the example
2. **Installation instructions** for required dependencies
3. **Example prompts** to try
4. **Comments** explaining key concepts
5. **Clear, runnable code**

Example:

```python
"""🚀 Feature Name - Description

This example demonstrates [what it does].
[Additional context].

Example prompts to try:
- "Prompt 1"
- "Prompt 2"

Run `pip install openai agno` to install dependencies.
"""

from agno.agent import Agent
from agno.models.openai import OpenAIChat

# Create agent with clear explanation
agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    description="Clear description of what this agent does",
)

# Run example
agent.print_response("Example query", stream=True)
```

---

## Additional Resources

### External Documentation
- **Main Docs**: https://docs.agno.com
- **Examples**: https://docs.agno.com/examples/introduction
- **Community Forum**: https://community.agno.com
- **Discord**: https://discord.gg/4MtYHHrgA8
- **GitHub**: https://github.com/agno-agi/agno

### Internal References
- `CONTRIBUTING.md` - Detailed contribution guidelines
- `CODE_OF_CONDUCT.md` - Community guidelines
- `cookbook/` - 100+ examples
- `evals/` - Evaluation suite

---

## Quick Reference Checklist

When working on the Agno codebase, ensure:

- [ ] Virtual environment is activated
- [ ] Code follows conventions (4 spaces for Python, 120 char line length)
- [ ] Type hints are used
- [ ] Docstrings are present for public APIs
- [ ] Optional dependencies are properly handled
- [ ] Import errors have helpful messages
- [ ] Code is formatted: `./scripts/format.sh`
- [ ] Code is validated: `./scripts/validate.sh`
- [ ] Tests pass: `./scripts/test.sh`
- [ ] Cookbook example added (if applicable)
- [ ] Dependencies added to `pyproject.toml` (if applicable)
- [ ] Changes committed with clear message
- [ ] PR created with description

---

## Notes for AI Assistants

### Key Principles

1. **Simplicity First**: Agno emphasizes simplicity over complexity
2. **Performance Matters**: Always consider performance implications
3. **Model Agnostic**: Don't assume any specific model provider
4. **Developer Experience**: Code should be intuitive and well-documented

### Common Patterns

1. **Optional Dependencies**: Always use try/except with helpful error messages
2. **Plugin Architecture**: Follow existing patterns for new providers/tools/databases
3. **Type Safety**: Use type hints, but remember Python 3.7+ compatibility
4. **Testing**: Write both unit and integration tests
5. **Examples**: Provide runnable cookbook examples

### When in Doubt

1. **Check existing implementations**: Look at similar components
2. **Follow conventions**: Consistency is key
3. **Ask for guidance**: Use Discord or create GitHub discussions
4. **Test thoroughly**: Run all validation scripts
5. **Document clearly**: Help future developers understand your code

---

**Last Updated**: 2025-11-19
**Agno Version**: 1.1.13
**Maintainer**: Agno Team

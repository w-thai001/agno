# Agno Workflow Library - Comprehensive Catalog

**Generated:** 2025-11-19 09:09:38
**Repository:** w-thai001/agno
**Total Workflow Files:** 39
**Total Lines of Code:** 5,360

---

## Table of Contents

1. [Overview](#overview)
2. [Quick Reference](#quick-reference)
3. [Library Statistics](#library-statistics)
4. [Category Navigation](#category-navigation)
5. [Core Workflow Implementation](#core-workflow-implementation)
6. [Usage Examples](#usage-examples)
7. [Integration Patterns](#integration-patterns)
8. [Storage Backends](#storage-backends)

---

## Overview

The Agno Workflow Library provides a comprehensive framework for building AI-powered workflows and multi-agent orchestration systems. The library includes:

- **Core Framework:** `libs/agno/agno/workflow/workflow.py` (603 LOC) - High complexity orchestration engine
- **Storage Integrations:** Support for JSON, YAML, SQLite, PostgreSQL, MongoDB, and SingleStore
- **Domain-Specific Workflows:** Pre-built workflows for content generation, research, recruitment, and more
- **Memory Management:** Workflow session storage and state persistence
- **Testing Suite:** Comprehensive integration tests for all storage backends

---

## Quick Reference

### By Complexity & Domain

| Name | Language | Domain | LOC | Complexity | Description |
|------|----------|--------|-----|------------|-------------|
| **workflow.py** | Python | networking | 603 | **high** | Core workflow orchestration engine |
| **09_research_workflow.py** | Python | messaging | 427 | medium | Advanced Research Workflow - AI Research Assistant |
| **blog_post_generator.py** | Python | messaging | 433 | medium | Blog Post Generator - AI Content Creation Studio |
| **personalized_email_generator.py** | Python | messaging | 465 | medium | Personalized email generation workflow |
| **linear.py** | Python | messaging | 388 | medium | Linear project management integration |
| **startup_idea_validator.py** | Python | messaging | 276 | medium | Startup idea validation workflow |
| **investment_report_generator.py** | Python | networking | 230 | low | Investment Report Generator - AI Financial Analysis Studio |
| **employee_recruiter.py** | Python | messaging | 203 | medium | Employee recruitment workflow with screening |
| **content_creator/workflow.py** | Python | messaging | 203 | medium | Content planning and publishing workflow |
| **product_manager.py** | Python | networking | 178 | medium | Product manager workflow with Linear integration |

### By Domain Category

#### Messaging (9 files)
Content generation, email automation, chat workflows, and communication systems.

#### Networking (19 files)
HTTP APIs, data fetching, external service integrations, and request/response handling.

#### Workflow (9 files)
Core workflow orchestration, state management, and workflow infrastructure.

#### Concurrency (2 files)
Async operations, parallel execution, and scheduling systems.

---

## Library Statistics

### Language Distribution
- **Python:** 36 files (92.3%)
- **Markdown:** 1 file (2.6%)
- **Text:** 2 files (5.1%)

### Complexity Distribution
- **Low Complexity:** 26 files (66.7%)
- **Medium Complexity:** 12 files (30.8%)
- **High Complexity:** 1 file (2.6%)

### Domain Distribution
- **Networking:** 19 files (48.7%)
- **Messaging:** 9 files (23.1%)
- **Workflow:** 9 files (23.1%)
- **Concurrency:** 2 files (5.1%)

### Lines of Code
- **Total LOC:** 5,360
- **Average LOC:** 137.4 per file
- **Largest File:** workflow.py (603 LOC)

---

## Category Navigation

### 1. Messaging Workflows

#### Content Generation
- **cookbook/workflows/blog_post_generator.py** (433 LOC)
  - Blog post generation from research
  - DuckDuckGo search integration
  - Article scraping with Newspaper4k
  - Cached results for efficiency

- **cookbook/workflows/content_creator/workflow.py** (203 LOC)
  - Multi-platform content creation (Twitter, LinkedIn)
  - Firecrawl blog scraping
  - Content planning and scheduling
  - Integration with Typefully API

- **cookbook/workflows/personalized_email_generator.py** (465 LOC)
  - Company research with Exa
  - Personalized email drafting
  - Caching for company data
  - Multi-step email refinement

#### Research & Analysis
- **cookbook/getting_started/09_research_workflow.py** (427 LOC)
  - Multi-stage research pipeline
  - Search result aggregation
  - Article scraping and analysis
  - Comprehensive report generation

- **cookbook/workflows/startup_idea_validator.py** (276 LOC)
  - Idea clarification agent
  - Market research automation
  - Competitor analysis
  - Google search integration

#### Workflow Management
- **cookbook/workflows/employee_recruiter.py** (203 LOC)
  - Resume parsing from PDF
  - Candidate screening
  - Interview scheduling
  - Email generation

### 2. Networking Workflows

#### News & Data Aggregation
- **cookbook/workflows/hackernews_reporter.py** (91 LOC)
  - HackerNews API integration
  - Top stories retrieval
  - Article summarization
  - Newspaper4k parsing

- **cookbook/workflows/investment_report_generator.py** (230 LOC)
  - YFinance integration
  - Financial data analysis
  - Report generation
  - SQLite storage

#### Tool Integrations
- **libs/agno/agno/tools/linear.py** (388 LOC)
  - Linear API GraphQL queries
  - Issue creation and updates
  - Workflow issue tracking
  - Priority management

### 3. Core Workflow Infrastructure

#### Main Workflow Engine
- **libs/agno/agno/workflow/workflow.py** (603 LOC)
  - Session management
  - State persistence
  - Memory initialization
  - Storage integration
  - Deep copy utilities
  - Monitoring and telemetry

#### Memory Management
- **libs/agno/agno/memory/workflow.py** (39 LOC)
  - WorkflowMemory class
  - WorkflowRun tracking
  - Memory serialization
  - State management

#### Session Storage
- **libs/agno/agno/storage/session/workflow.py** (62 LOC)
  - WorkflowSession dataclass
  - Session serialization
  - Monitoring data
  - Telemetry integration

### 4. Storage Backends

The library supports multiple storage backends with consistent APIs:

#### Production Examples
- **JSON:** `cookbook/storage/json_storage/json_storage_for_workflow.py`
- **YAML:** `cookbook/storage/yaml_storage/yaml_storage_for_workflow.py`
- **SQLite:** `cookbook/storage/sqllite_storage/sqlite_storage_for_workflow.py`
- **PostgreSQL:** `cookbook/storage/postgres_storage/postgres_storage_for_workflow.py`
- **MongoDB:** `cookbook/storage/mongodb_storage/mongodb_storage_for_workflow.py`
- **SingleStore:** `cookbook/storage/singlestore_storage/singlestore_storage_for_workflow.py`

#### Test Coverage
- **test_json_storage_workflow.py** (206 LOC)
- **test_sqlite_storage_workflow.py** (210 LOC)
- **test_yaml_storage_workflow.py** (206 LOC)

---

## Core Workflow Implementation

### Main Classes

#### Workflow Class (`libs/agno/agno/workflow/workflow.py:603`)

**Key Methods:**
- `run()` - Execute the workflow
- `run_workflow()` - Internal workflow execution
- `get_workflow_session()` - Session retrieval
- `load_workflow_session()` - Session loading from storage
- `write_to_storage()` - Persist workflow state
- `delete_session()` - Remove workflow session
- `set_session_id()` - Session identifier management
- `deep_copy()` - Deep copy workflow state

**Key Features:**
- Session-based state management
- Multiple storage backend support
- Memory initialization and management
- Monitoring and telemetry hooks
- Debug mode support

#### WorkflowMemory Class (`libs/agno/agno/memory/workflow.py:39`)

**Key Methods:**
- `add_run()` - Add workflow run to memory
- `to_dict()` - Serialize memory state
- `deep_copy()` - Deep copy memory
- `clear()` - Clear memory state

#### WorkflowSession Class (`libs/agno/agno/storage/session/workflow.py:62`)

**Key Methods:**
- `to_dict()` - Serialize session
- `from_dict()` - Deserialize session
- `telemetry_data()` - Get telemetry data
- `monitoring_data()` - Get monitoring data

---

## Usage Examples

### Example 1: Basic Workflow with Storage

```python
from agno.workflow import Workflow
from agno.agent import Agent
from agno.storage.sqlite import SqliteStorage

# Define workflow
class SimpleWorkflow(Workflow):
    def run(self, message: str) -> str:
        agent = Agent(
            name="Assistant",
            instructions="You are a helpful assistant"
        )
        response = agent.run(message)
        return response.content

# Initialize with storage
workflow = SimpleWorkflow(
    session_id="user_123",
    storage=SqliteStorage(
        table_name="workflow_sessions",
        db_file="workflows.db"
    )
)

# Execute workflow
result = workflow.run("Tell me a joke")
print(result)
```

### Example 2: Research Workflow with Caching

From `cookbook/getting_started/09_research_workflow.py`:

```python
from agno.workflow import Workflow
from agno.agent import Agent
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.newspaper4k import Newspaper4kTools

class ResearchWorkflow(Workflow):
    def run(self, topic: str):
        # Step 1: Search for articles
        search_results = self.get_search_results(topic)

        # Step 2: Scrape articles
        articles = self.scrape_articles(search_results)

        # Step 3: Generate report
        report = self.write_research_report(articles)

        return report

    def get_search_results(self, topic: str):
        # Check cache first
        cached = self.get_cached_search_results(topic)
        if cached:
            return cached

        # Search with DuckDuckGo
        searcher = Agent(tools=[DuckDuckGoTools()])
        results = searcher.run(f"Search for: {topic}")

        # Cache results
        self.add_search_results_to_cache(topic, results)
        return results
```

### Example 3: Multi-Agent Content Workflow

From `cookbook/workflows/content_creator/workflow.py`:

```python
from agno.workflow import Workflow
from agno.agent import Agent
from agno.tools.firecrawl import FirecrawlTools

class ContentPlanningWorkflow(Workflow):
    def run(self, blog_url: str):
        # Step 1: Scrape blog content
        blog_content = self.scrape_blog_post(blog_url)

        # Step 2: Generate content plan
        plan = self.generate_plan(blog_content)

        # Step 3: Schedule and publish
        self.schedule_and_publish(plan)

        return plan
```

### Example 4: HackerNews Reporter with Storage

From `cookbook/workflows/hackernews_reporter.py`:

```python
from agno.workflow import Workflow
from agno.agent import Agent
from agno.tools.newspaper4k import Newspaper4kTools
import httpx
import json

class HackerNewsReporter(Workflow):
    def run(self):
        # Fetch top stories
        stories = self.get_top_hackernews_stories(limit=5)

        # Analyze with AI agent
        reporter = Agent(
            name="HackerNews Reporter",
            tools=[Newspaper4kTools()],
            instructions="Summarize tech news articles"
        )

        report = reporter.run(stories)
        return report

    def get_top_hackernews_stories(self, limit: int = 5):
        response = httpx.get(
            "https://hacker-news.firebaseio.com/v0/topstories.json"
        )
        story_ids = response.json()[:limit]

        stories = []
        for story_id in story_ids:
            story_response = httpx.get(
                f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
            )
            stories.append(story_response.json())

        return stories
```

---

## Integration Patterns

### Pattern 1: Caching with Workflow Memory

Many workflows use caching to avoid redundant operations:

```python
def get_cached_data(self, key: str):
    """Retrieve data from workflow memory cache"""
    if self.memory and self.memory.runs:
        for run in self.memory.runs:
            if run.get(key):
                return run[key]
    return None

def add_to_cache(self, key: str, value: any):
    """Add data to workflow memory cache"""
    if not self.memory:
        self.initialize_memory()
    self.memory.add_run({key: value})
```

### Pattern 2: Multi-Step Workflow Pipeline

Common pattern for complex workflows:

```python
class PipelineWorkflow(Workflow):
    def run(self, input_data):
        # Step 1: Data collection
        raw_data = self.collect_data(input_data)

        # Step 2: Data processing
        processed_data = self.process_data(raw_data)

        # Step 3: Analysis
        analysis = self.analyze_data(processed_data)

        # Step 4: Report generation
        report = self.generate_report(analysis)

        return report
```

### Pattern 3: Agent Orchestration

Multiple specialized agents working together:

```python
class MultiAgentWorkflow(Workflow):
    def run(self, task):
        # Researcher agent
        researcher = Agent(
            name="Researcher",
            tools=[SearchTools()],
            instructions="Find relevant information"
        )

        # Writer agent
        writer = Agent(
            name="Writer",
            instructions="Create engaging content"
        )

        # Editor agent
        editor = Agent(
            name="Editor",
            instructions="Review and improve content"
        )

        # Pipeline: research -> write -> edit
        research = researcher.run(task)
        draft = writer.run(research)
        final = editor.run(draft)

        return final
```

### Pattern 4: Storage Backend Integration

All storage examples follow this pattern:

```python
from agno.workflow import Workflow
from agno.storage.{backend} import {Backend}Storage

workflow = Workflow(
    session_id="unique_session",
    storage={Backend}Storage(
        table_name="workflow_sessions",
        # Backend-specific configuration
    )
)

# Workflow automatically persists state
result = workflow.run(input_data)

# Retrieve previous session
loaded_workflow = Workflow.load_workflow_session(
    session_id="unique_session",
    storage=storage_backend
)
```

---

## Storage Backends

### Supported Storage Types

| Backend | File | Configuration | Use Case |
|---------|------|---------------|----------|
| **JSON** | `agno.storage.json` | `file_path`, `auto_save` | Development, simple persistence |
| **YAML** | `agno.storage.yaml` | `file_path`, `auto_save` | Human-readable configs |
| **SQLite** | `agno.storage.sqlite` | `db_file`, `table_name` | Local production, single-user |
| **PostgreSQL** | `agno.storage.postgres` | `db_url`, `table_name` | Production, multi-user |
| **MongoDB** | `agno.storage.mongodb` | `connection_string`, `database` | Document-based workflows |
| **SingleStore** | Custom implementation | `engine`, `table_name` | High-performance analytics |

### Storage Configuration Examples

#### SQLite
```python
from agno.storage.sqlite import SqliteStorage

storage = SqliteStorage(
    table_name="workflow_sessions",
    db_file="./data/workflows.db"
)
```

#### PostgreSQL
```python
from agno.storage.postgres import PostgresStorage

storage = PostgresStorage(
    table_name="workflow_sessions",
    db_url="postgresql://user:pass@localhost:5432/agno"
)
```

#### MongoDB
```python
from agno.storage.mongodb import MongoDbStorage

storage = MongoDbStorage(
    collection_name="workflow_sessions",
    connection_string="mongodb://localhost:27017",
    database="agno"
)
```

---

## Key Dependencies

### Core Dependencies
- **agno.workflow** - Main workflow framework
- **agno.agent** - Agent orchestration
- **agno.storage.*** - Storage backends
- **agno.memory.workflow** - Memory management
- **pydantic** - Data validation (BaseModel)

### Tool Dependencies
- **agno.tools.duckduckgo** - DuckDuckGo search
- **agno.tools.newspaper4k** - Article scraping
- **agno.tools.firecrawl** - Web scraping
- **agno.tools.exa** - Company research
- **agno.tools.linear** - Project management
- **agno.tools.yfinance** - Financial data

### External Libraries
- **httpx** - HTTP requests
- **requests** - HTTP client
- **pypdf** - PDF parsing
- **textwrap** - Text formatting

---

## Relationship Graph

The workflow playground demonstrates workflow composition:

**workflows_playground.py** depends on:
- `investment_report_generator.py`
- `personalized_email_generator.py`
- `blog_post_generator.py`
- `startup_idea_validator.py`

This creates a centralized playground for testing and demonstrating multiple workflows.

---

## Next Steps

See `fsa_organization_recommendations.md` for:
- Directory structure improvements
- Naming conventions
- Documentation gaps
- Testing coverage recommendations
- Performance optimization opportunities

---

## Additional Resources

### Testing
All storage backends have comprehensive integration tests in:
- `libs/agno/tests/integration/storage/`

### Examples
Production-ready workflow examples in:
- `cookbook/workflows/`
- `cookbook/getting_started/`
- `cookbook/storage/*/`

### Documentation
- Main README: `README.md`
- Workflow-specific READMEs in cookbook subdirectories
- This catalog: `FSA_LIBRARY_README.md`

---

**End of FSA Library Catalog**

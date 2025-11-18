# FSA & MLA - Concrete Implementation Examples

## 1. Concrete FSA Example from Codebase

### Pattern 1: Simple Single-Purpose FSA (Finance Domain)
**File**: `/home/user/agno/cookbook/examples/agents/finance_agent.py`

```python
from textwrap import dedent
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.yfinance import YFinanceTools

# This is a basic FSA pattern
finance_agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    tools=[
        YFinanceTools(
            stock_price=True,
            analyst_recommendations=True,
            stock_fundamentals=True,
            historical_prices=True,
            company_info=True,
            company_news=True,
        )
    ],
    instructions=dedent("""\
        You are a seasoned Wall Street analyst with deep expertise in market analysis!
        
        Follow these steps for comprehensive financial analysis:
        1. Market Overview - Latest stock price, 52-week high and low
        2. Financial Deep Dive - Key metrics (P/E, Market Cap, EPS)
        3. Professional Insights - Analyst recommendations breakdown
        4. Market Context - Industry trends and competitive analysis
        
        Your reporting style:
        - Begin with an executive summary
        - Use tables for data presentation
        - Include clear section headers
        - Highlight key insights with bullet points
    """),
    add_datetime_to_instructions=True,
    show_tool_calls=True,
    markdown=True,
)

# Usage
finance_agent.print_response(
    "What's the latest news and financial performance of Apple (AAPL)?",
    stream=True
)
```

**Key FSA Characteristics**:
- Single responsibility: Financial analysis
- Focused tools: Only YFinance tools
- Clear instructions: Step-by-step analysis process
- Reusable: Can be composed with other agents

---

## 2. Concrete Team/Multi-Agent FSA Example

### Pattern 2: Specialized Agents Forming a Team
**File**: `/home/user/agno/cookbook/examples/apps/chess_team/agents.py`

```python
from typing import Dict
from agno.agent import Agent
from agno.models.anthropic import Claude
from agno.models.openai import OpenAIChat

def get_chess_teams(
    white_model: str = "openai:gpt-4o",
    black_model: str = "anthropic:claude-3-7-sonnet",
    master_model: str = "openai:gpt-4o",
    debug_mode: bool = True,
) -> Dict[str, Agent]:
    """
    Creates specialized chess agents with distinct roles.
    
    Each agent is an FSA with a single, focused responsibility.
    """
    
    # Layer 1: White Piece Strategy FSA
    white_piece_agent = Agent(
        name="white_piece_agent",
        description="""You are a chess strategist for white pieces. 
                       Given a list of legal moves, analyze them and 
                       choose the best one based on standard chess strategy.
                       Consider piece development, center control, and king safety.
                       Respond ONLY with your chosen move in UCI notation (e.g., 'e2e4').""",
        model=OpenAIChat(id=white_model),
        debug_mode=debug_mode,
    )
    
    # Layer 1: Black Piece Strategy FSA
    black_piece_agent = Agent(
        name="black_piece_agent",
        description="""You are a chess strategist for black pieces.
                       Given a list of legal moves, analyze them and 
                       choose the best one based on standard chess strategy.
                       Consider piece development, center control, and king safety.
                       Respond ONLY with your chosen move in UCI notation (e.g., 'e7e5').""",
        model=Claude(id=black_model),
        debug_mode=debug_mode,
    )
    
    # Layer 1: Master Game Evaluator FSA
    master_agent = Agent(
        name="master_agent",
        description="""You are a chess master overseeing the game.
                       Your responsibilities:
                       1. Analyze the current board state
                       2. Check for checkmate, stalemate, draw by repetition
                       3. Provide commentary on the game state
                       4. Evaluate position and suggest who has advantage
                       
                       Respond with a JSON object containing:
                       {
                           "game_over": true/false,
                           "result": "white_win"/"black_win"/"draw"/null,
                           "reason": "explanation if game is over",
                           "commentary": "brief analysis of position",
                           "advantage": "white"/"black"/"equal"
                       }""",
        model=OpenAIChat(id=master_model),
        debug_mode=debug_mode,
    )
    
    return {
        "white_piece_agent": white_piece_agent,
        "black_piece_agent": black_piece_agent,
        "master_agent": master_agent,
    }

# Usage in main application
if __name__ == "__main__":
    agents = get_chess_teams()
    # Each agent is an FSA that can be called independently or composed
    white_move = agents["white_piece_agent"].run("Available moves: e2e4, d2d4, c2c4")
    # Master evaluates the resulting position
    evaluation = agents["master_agent"].run(f"After white move: {white_move.content}")
```

**Key FSA Pattern Characteristics**:
- Each agent is a separate FSA with a distinct role
- Clear input/output contracts
- Can be called independently or as a team
- Highly specializable to different domains

---

## 3. Concrete Workflow with FSA Composition

### Pattern 3: Workflow Composing Multiple FSAs
**File**: `/home/user/agno/cookbook/getting_started/09_research_workflow.py` (excerpts)

```python
from typing import Iterator, Optional, Dict
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.storage.sqlite import SqliteStorage
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.newspaper4k import Newspaper4kTools
from agno.workflow import RunEvent, RunResponse, Workflow
from pydantic import BaseModel, Field

# Define data models
class Article(BaseModel):
    title: str = Field(..., description="Title of the article.")
    url: str = Field(..., description="Link to the article.")
    summary: Optional[str] = Field(..., description="Summary of the article.")

class SearchResults(BaseModel):
    articles: list[Article]

class ScrapedArticle(BaseModel):
    title: str
    url: str
    content: Optional[str]

# MLA Layer 1: Foundation FSAs as class attributes
class ResearchReportGenerator(Workflow):
    description: str = """Generate comprehensive research reports that combine 
                          academic rigor with engaging storytelling."""
    
    # Layer 1: Foundation FSA - Web Searcher
    web_searcher: Agent = Agent(
        model=OpenAIChat(id="gpt-4o-mini"),
        tools=[DuckDuckGoTools()],
        description="""You are ResearchBot-X, an expert at discovering and 
                      evaluating academic and scientific sources.""",
        instructions="""You're a meticulous research assistant!
                       Search for 10-15 sources and identify 5-7 most authoritative.
                       Prioritize:
                       - Peer-reviewed articles and academic publications
                       - Recent developments from reputable institutions
                       - Authoritative news sources and expert commentary
                       - Diverse perspectives from recognized experts
                       Avoid opinion pieces and non-authoritative sources.""",
        response_model=SearchResults,
        structured_outputs=True,
    )
    
    # Layer 1: Foundation FSA - Content Analyzer
    article_scraper: Agent = Agent(
        model=OpenAIChat(id="gpt-4o-mini"),
        tools=[Newspaper4kTools()],
        description="""You are ContentBot-X, an expert at extracting and 
                      structuring academic content.""",
        instructions="""You're a precise content curator with attention to detail!
                       When processing content:
                          - Extract content from the article
                          - Preserve academic citations and references
                          - Maintain technical accuracy in terminology
                          - Structure content logically with clear sections
                          - Extract key findings and methodology details""",
        response_model=ScrapedArticle,
        structured_outputs=True,
    )
    
    # Layer 1: Foundation FSA - Report Writer
    writer: Agent = Agent(
        model=OpenAIChat(id="gpt-4o"),
        description="""You are Professor X-2000, a distinguished AI research 
                      scientist combining academic rigor with engaging narrative.""",
        instructions="""Channel the expertise of a world-class academic researcher!
                       🎯 Analysis Phase: Evaluate credibility, cross-reference findings
                       💡 Synthesis Phase: Develop coherent narrative framework
                       ✍️ Writing Phase: Clear presentation, academic tone""",
        expected_output="""# {Compelling Title}
                          ## Executive Summary
                          {Concise overview}
                          ## Key Findings
                          {Major discoveries}
                          ## Analysis
                          {Critical evaluation}
                          ## References
                          {Proper citations}""",
        markdown=True,
    )

    # Layer 2 & 3: Orchestrate FSAs in workflow
    def run(
        self,
        topic: str,
        use_search_cache: bool = True,
        use_scrape_cache: bool = True,
    ) -> Iterator[RunResponse]:
        """
        Orchestrate Layer 1 FSAs to generate a complete research report.
        
        Workflow Steps:
        1. Web Searcher FSA: Find articles on topic
        2. Article Scraper FSA: Extract content from articles
        3. Writer FSA: Generate report from scraped content
        """
        logger.info(f"Generating a report on: {topic}")

        # Step 1: Use web_searcher FSA
        search_results: Optional[SearchResults] = self.get_search_results(
            topic, use_search_cache
        )
        if search_results is None or len(search_results.articles) == 0:
            yield RunResponse(
                event=RunEvent.workflow_completed,
                content=f"Sorry, could not find any articles on: {topic}",
            )
            return

        # Step 2: Use article_scraper FSA on each search result
        scraped_articles: Dict[str, ScrapedArticle] = self.scrape_articles(
            search_results, use_scrape_cache
        )

        # Step 3: Use writer FSA to generate final report
        yield from self.write_research_report(topic, scraped_articles)

    def get_search_results(
        self, topic: str, use_search_cache: bool
    ) -> Optional[SearchResults]:
        """Call the web_searcher FSA"""
        if use_search_cache:
            cached = self.session_state.get("search_results", {}).get(topic)
            if cached is not None:
                return SearchResults.model_validate(cached)

        # Call web_searcher FSA
        searcher_response: RunResponse = self.web_searcher.run(topic)
        if (
            searcher_response is not None
            and isinstance(searcher_response.content, SearchResults)
        ):
            self.session_state.setdefault("search_results", {})
            self.session_state["search_results"][topic] = (
                searcher_response.content.model_dump()
            )
            self.write_to_storage()
            return searcher_response.content
        return None

    def scrape_articles(
        self, search_results: SearchResults, use_scrape_cache: bool
    ) -> Dict[str, ScrapedArticle]:
        """Call the article_scraper FSA on each article"""
        scraped_articles: Dict[str, ScrapedArticle] = {}
        
        for article in search_results.articles:
            # Call article_scraper FSA
            scraper_response: RunResponse = self.article_scraper.run(article.url)
            if (
                scraper_response is not None
                and isinstance(scraper_response.content, ScrapedArticle)
            ):
                scraped_articles[scraper_response.content.url] = (
                    scraper_response.content
                )
        
        return scraped_articles

    def write_research_report(
        self, topic: str, scraped_articles: Dict[str, ScrapedArticle]
    ) -> Iterator[RunResponse]:
        """Call the writer FSA with aggregated information"""
        writer_input = {
            "topic": topic,
            "articles": [v.model_dump() for v in scraped_articles.values()],
        }
        # Call writer FSA and stream the response
        yield from self.writer.run(json.dumps(writer_input, indent=4), stream=True)


# Usage in main
if __name__ == "__main__":
    generator = ResearchReportGenerator(
        session_id="generate-report-on-quantum-computing",
        storage=SqliteStorage(
            table_name="research_workflow",
            db_file="tmp/workflows.db",
        ),
    )
    
    # Execute workflow: coordinates Layer 1 FSAs
    report_stream: Iterator[RunResponse] = generator.run(
        topic="quantum computing breakthroughs 2024",
        use_search_cache=True,
    )
    
    # Stream results
    for response in report_stream:
        print(response.content)
```

**Key MLA Pattern Characteristics**:
- **Layer 1**: Three Foundation FSAs (web_searcher, article_scraper, writer)
- **Layer 2-3**: Workflow orchestrates FSA composition
- **Caching**: Uses `session_state` for intermediate results
- **Streaming**: FSAs produce streaming responses
- **Error Handling**: Graceful degradation if any FSA fails

---

## 4. Agent Team Pattern (Simpler Composition)

### Pattern 4: Agent Team Coordination
**File**: `/home/user/agno/cookbook/getting_started/05_agent_team.py` (excerpts)

```python
from textwrap import dedent
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.yfinance import YFinanceTools

# Layer 1: Specialized FSAs
web_agent = Agent(
    name="Web Agent",
    role="Search the web for information",
    model=OpenAIChat(id="gpt-4o"),
    tools=[DuckDuckGoTools()],
    instructions=dedent("""\
        You are an experienced web researcher and news analyst!
        
        Follow these steps when searching for information:
        1. Start with the most recent and relevant sources
        2. Cross-reference information from multiple sources
        3. Prioritize reputable news outlets and official sources
        4. Always cite your sources with links
        5. Focus on market-moving news and significant developments
    """),
    show_tool_calls=True,
    markdown=True,
)

finance_agent = Agent(
    name="Finance Agent",
    role="Get financial data",
    model=OpenAIChat(id="gpt-4o"),
    tools=[
        YFinanceTools(
            stock_price=True,
            analyst_recommendations=True,
            company_info=True
        )
    ],
    instructions=dedent("""\
        You are a skilled financial analyst!
        
        Follow these steps when analyzing financial data:
        1. Start with the latest stock price, trading volume, and daily range
        2. Present detailed analyst recommendations
        3. Include key metrics: P/E ratio, market cap, 52-week range
        4. Use tables for structured data presentation
    """),
    show_tool_calls=True,
    markdown=True,
)

# Layer 2: Team Coordination Agent
agent_team = Agent(
    team=[web_agent, finance_agent],
    model=OpenAIChat(id="gpt-4o"),
    instructions=dedent("""\
        You are the lead editor of a prestigious financial news desk!
        
        Your role:
        1. Coordinate between the web researcher and financial analyst
        2. Combine their findings into a compelling narrative
        3. Ensure all information is properly sourced and verified
        4. Present a balanced view of both news and data
        5. Highlight key risks and opportunities
    """),
    add_datetime_to_instructions=True,
    show_tool_calls=True,
    markdown=True,
)

# Usage: Team automatically routes requests to specialized FSAs
agent_team.print_response(
    "Summarize analyst recommendations and share latest news for NVDA",
    stream=True
)
```

**Key Team Pattern Characteristics**:
- Simpler than workflow pattern
- Direct team parameter with FSAs
- Automatic routing to team members
- Leader coordinates responses
- Good for synchronous coordination

---

## 5. Directory Structure Comparison

### Recommended Directory Layout for FSA/MLA Project

```
/home/user/agno/libs/agno/agno/
├── fsas/                              # All FSAs organized by domain
│   ├── __init__.py
│   ├── base_fsa.py                    # Base FSA class template
│   │
│   ├── research/                      # Domain 1: Research FSAs
│   │   ├── __init__.py
│   │   ├── web_searcher_fsa.py        # Layer 1: Search task
│   │   ├── content_analyzer_fsa.py    # Layer 1: Analysis task
│   │   └── report_writer_fsa.py       # Layer 1: Writing task
│   │
│   ├── finance/                       # Domain 2: Finance FSAs
│   │   ├── __init__.py
│   │   ├── stock_analyzer_fsa.py      # Layer 1
│   │   ├── market_analyst_fsa.py      # Layer 1
│   │   └── portfolio_optimizer_fsa.py # Layer 1
│   │
│   ├── content/                       # Domain 3: Content FSAs
│   │   ├── __init__.py
│   │   ├── blog_analyzer_fsa.py
│   │   ├── social_media_planner_fsa.py
│   │   └── content_generator_fsa.py
│   │
│   └── utils/
│       ├── __init__.py
│       └── fsa_registry.py            # FSA discovery & composition
│
├── mla/                               # MLA Framework
│   ├── __init__.py
│   ├── layers.py                      # Layer definitions
│   │
│   ├── composition/                   # Layer 2 Composition FSAs
│   │   ├── __init__.py
│   │   ├── composition_base.py
│   │   ├── research_coordinator_fsa.py
│   │   └── finance_coordinator_fsa.py
│   │
│   ├── workflows/                     # Layer 3 Workflows
│   │   ├── __init__.py
│   │   ├── mla_workflow.py            # Base workflow
│   │   ├── research_workflow.py       # Example: Research workflow
│   │   └── finance_workflow.py        # Example: Finance workflow
│   │
│   └── registry/
│       ├── __init__.py
│       └── fsa_registry.py
│
└── agent/                             # Existing Agent framework
    ├── agent.py
    └── metrics.py
```

---

## 6. Concrete FSA Base Class Implementation

### Template for Creating FSAs

```python
# File: /home/user/agno/libs/agno/agno/fsas/base_fsa.py

from typing import Any, List, Optional, Union
from agno.agent import Agent
from agno.models.base import Model
from agno.tools.function import Function
from agno.tools.toolkit import Toolkit

class BaseFSA(Agent):
    """
    Base Focused Specialized Agent class.
    
    Provides common patterns for creating highly specialized agents
    with a single responsibility and focused tooling.
    """
    
    # FSA metadata
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
        """Initialize an FSA with focused configuration."""
        
        # Use class-defined metadata if not provided
        fsa_name = name or self.fsa_name or self.__class__.__name__
        fsa_role = role or self.fsa_responsibility
        
        # Initialize parent Agent with FSA-specific defaults
        super().__init__(
            model=model,
            name=fsa_name,
            role=fsa_role,
            description=self.__class__.__doc__ or f"{fsa_name} FSA",
            instructions=instructions or self._get_default_instructions(),
            expected_output=expected_output,
            tools=tools,
            # FSA-specific defaults
            show_tool_calls=False,
            markdown=True,
            debug_mode=kwargs.pop("debug_mode", False),
            **kwargs,
        )
    
    @staticmethod
    def _get_default_instructions() -> str:
        """
        Override in subclass to provide default instructions.
        
        Returns:
            Default instruction string for this FSA
        """
        return "Execute the assigned task."
    
    def validate_input(self, input_data: Any) -> bool:
        """
        Validate input before execution.
        
        Override in subclass for custom validation.
        
        Args:
            input_data: Input to validate
            
        Returns:
            True if valid, False otherwise
        """
        return input_data is not None
    
    def execute(self, input_data: Any, **kwargs: Any):
        """
        Execute the FSA with given input.
        
        Args:
            input_data: Input to process
            **kwargs: Additional arguments for agent.run()
            
        Returns:
            RunResponse from agent execution
        """
        if not self.validate_input(input_data):
            raise ValueError(f"Invalid input: {input_data}")
        
        return self.run(str(input_data), **kwargs)
```

### Concrete Implementation Example

```python
# File: /home/user/agno/libs/agno/agno/fsas/research/web_searcher_fsa.py

from typing import Optional
from agno.fsas.base_fsa import BaseFSA
from agno.models.base import Model
from agno.tools.duckduckgo import DuckDuckGoTools

class WebSearcherFSA(BaseFSA):
    """
    Search the web for information on a given topic.
    
    Responsibilities:
    - Find relevant web sources
    - Extract key information
    - Return structured search results
    
    Example:
        fsa = WebSearcherFSA(model=OpenAIChat(id="gpt-4o"))
        results = fsa.execute("latest AI breakthroughs 2024")
    """
    
    fsa_name = "WebSearcher"
    fsa_domain = "research"
    fsa_responsibility = "Search the web for information"
    
    def __init__(self, model: Optional[Model] = None, **kwargs):
        super().__init__(
            model=model,
            tools=[DuckDuckGoTools()],
            expected_output="""
            {
                "articles": [
                    {
                        "title": "...",
                        "url": "...",
                        "summary": "..."
                    }
                ]
            }
            """,
            **kwargs,
        )
    
    @staticmethod
    def _get_default_instructions() -> str:
        return """You are an expert web researcher.
        
        When searching for information:
        1. Find 5-10 most relevant sources
        2. Prioritize recent and authoritative sources
        3. Extract key information from each source
        4. Return structured results with title, URL, and summary
        5. Always include source URLs
        
        Return results as valid JSON."""
```

---

## Summary of Patterns

| Pattern | Type | Use Case | Composition |
|---------|------|----------|-------------|
| **Single FSA** | FSA | Simple, focused task | Standalone |
| **Agent Team** | Multi-Agent | Parallel specialized tasks | Direct team parameter |
| **Workflow** | Orchestration | Multi-step sequential workflow | Layer 1 FSAs as attributes |
| **MLA Pattern** | Architecture | Complex, hierarchical tasks | Layer 1 → Layer 2 → Layer 3 |

**Key Takeaway**: Start with FSAs, compose them into teams, then orchestrate with workflows or MLA.


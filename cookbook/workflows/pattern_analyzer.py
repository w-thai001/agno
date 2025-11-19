"""
Pattern Analyzer FSA - Meta-Analysis for FSA Code and Architectures

This workflow analyzes code patterns, design patterns, and architectural patterns
in FSA (Workflow) implementations to provide insights, recommendations, and
best practice validation.

Features:
- Pattern detection (design patterns, architectural patterns)
- Similarity analysis between FSAs
- Best practice validation
- Code quality assessment
- Architecture recommendations

Usage:
    from cookbook.workflows.pattern_analyzer import PatternAnalyzerFSA

    analyzer = PatternAnalyzerFSA(
        session_id="pattern-analysis-001",
        debug_mode=True
    )

    # Analyze a single FSA file
    result = analyzer.run(
        fsa_files=["cookbook/workflows/blog_post_generator.py"],
        analysis_type="comprehensive"
    )

    # Compare multiple FSAs
    result = analyzer.run(
        fsa_files=[
            "cookbook/workflows/blog_post_generator.py",
            "cookbook/workflows/startup_idea_validator.py"
        ],
        analysis_type="similarity"
    )
"""

from typing import List, Dict, Any, Optional, Iterator
from pathlib import Path
from pydantic import BaseModel, Field
from agno.workflow import Workflow, RunResponse, RunEvent
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.storage.workflow.sqlite import SqliteStorage


# ============================================================================
# Pydantic Models for Structured Outputs
# ============================================================================

class DesignPattern(BaseModel):
    """Represents a detected design pattern"""
    pattern_name: str = Field(..., description="Name of the design pattern (e.g., Factory, Strategy, Observer)")
    confidence: float = Field(..., description="Confidence score (0.0 to 1.0)")
    location: str = Field(..., description="Where the pattern was found (file:line or class name)")
    description: str = Field(..., description="How the pattern is implemented")
    code_snippet: Optional[str] = Field(None, description="Relevant code snippet demonstrating the pattern")


class ArchitecturalPattern(BaseModel):
    """Represents a detected architectural pattern"""
    pattern_name: str = Field(..., description="Name of the architectural pattern (e.g., MVC, Pipeline, Layered)")
    components: List[str] = Field(..., description="Key components implementing this pattern")
    description: str = Field(..., description="How the architecture is structured")
    quality_score: float = Field(..., description="Quality assessment (0.0 to 1.0)")


class BestPracticeCheck(BaseModel):
    """Best practice validation result"""
    practice: str = Field(..., description="The best practice being checked")
    status: str = Field(..., description="Status: 'pass', 'warning', or 'fail'")
    details: str = Field(..., description="Detailed explanation of the finding")
    recommendation: Optional[str] = Field(None, description="Recommendation if not passing")


class CodeQualityMetrics(BaseModel):
    """Code quality metrics"""
    complexity_score: float = Field(..., description="Code complexity (0.0=simple to 1.0=complex)")
    maintainability_score: float = Field(..., description="Maintainability score (0.0 to 1.0)")
    modularity_score: float = Field(..., description="How modular the code is (0.0 to 1.0)")
    reusability_score: float = Field(..., description="Reusability potential (0.0 to 1.0)")
    key_observations: List[str] = Field(..., description="Key observations about code quality")


class SimilarityAnalysis(BaseModel):
    """Similarity analysis between FSAs"""
    file_pair: str = Field(..., description="The two files being compared")
    similarity_score: float = Field(..., description="Overall similarity (0.0 to 1.0)")
    structural_similarity: float = Field(..., description="Structural similarity")
    pattern_similarity: float = Field(..., description="Pattern usage similarity")
    common_patterns: List[str] = Field(..., description="Patterns found in both")
    differences: List[str] = Field(..., description="Key differences")


class PatternAnalysisReport(BaseModel):
    """Complete pattern analysis report"""
    summary: str = Field(..., description="Executive summary of the analysis")
    files_analyzed: List[str] = Field(..., description="Files that were analyzed")
    design_patterns: List[DesignPattern] = Field(default_factory=list, description="Detected design patterns")
    architectural_patterns: List[ArchitecturalPattern] = Field(default_factory=list, description="Detected architectural patterns")
    best_practices: List[BestPracticeCheck] = Field(default_factory=list, description="Best practice validation results")
    code_quality: Optional[CodeQualityMetrics] = Field(None, description="Code quality metrics")
    similarity_analyses: List[SimilarityAnalysis] = Field(default_factory=list, description="Similarity comparisons")
    recommendations: List[str] = Field(..., description="Top recommendations for improvement")
    overall_score: float = Field(..., description="Overall quality score (0.0 to 1.0)")


# ============================================================================
# Pattern Analyzer FSA Workflow
# ============================================================================

class PatternAnalyzerFSA(Workflow):
    """
    Pattern Analyzer FSA for meta-analysis of FSA implementations.

    This workflow analyzes FSA code to detect patterns, validate best practices,
    assess code quality, and provide actionable recommendations.
    """

    description: str = "Analyzes code patterns, design patterns, and architectural patterns in FSA implementations"

    # ========================================================================
    # Agents - Using cost-efficient models
    # ========================================================================

    code_reader: Agent = Agent(
        name="Code Reader",
        role="Code Analysis Specialist",
        model=OpenAIChat(id="gpt-4o-mini"),
        description=(
            "You are an expert at reading and understanding code structure. "
            "You analyze code files to extract key information about classes, methods, "
            "agents, workflows, data flow, and overall architecture."
        ),
        instructions=[
            "Read the provided code files thoroughly",
            "Identify all classes, methods, and functions",
            "Map out the workflow structure and data flow",
            "Extract agent definitions and their configurations",
            "Note any imports, dependencies, and external integrations",
            "Provide a clear structural summary"
        ],
        markdown=True,
    )

    pattern_detector: Agent = Agent(
        name="Pattern Detector",
        role="Design Pattern Recognition Expert",
        model=OpenAIChat(id="gpt-4o"),  # Using gpt-4o for pattern detection accuracy
        description=(
            "You are an expert in software design patterns and architectural patterns. "
            "You can identify common patterns like Factory, Strategy, Observer, Decorator, "
            "as well as architectural patterns like MVC, Pipeline, Layered Architecture, etc."
        ),
        instructions=[
            "Analyze the code structure for design patterns",
            "Identify architectural patterns in the overall structure",
            "Look for Gang of Four patterns and modern patterns",
            "Check for FSA-specific patterns (sequential, branching, streaming)",
            "Assess the quality of pattern implementation",
            "Provide confidence scores for detected patterns",
            "Extract relevant code snippets demonstrating patterns"
        ],
        response_model=List[DesignPattern],
        structured_outputs=True,
    )

    architecture_analyzer: Agent = Agent(
        name="Architecture Analyzer",
        role="Software Architecture Expert",
        model=OpenAIChat(id="gpt-4o-mini"),
        description=(
            "You are an expert in software architecture analysis. "
            "You evaluate the overall architecture, component organization, "
            "modularity, and structural quality of FSA implementations."
        ),
        instructions=[
            "Analyze the high-level architecture",
            "Identify architectural layers and components",
            "Assess modularity and separation of concerns",
            "Evaluate the workflow orchestration strategy",
            "Check for scalability and maintainability patterns",
            "Provide quality scores for architectural decisions"
        ],
        response_model=List[ArchitecturalPattern],
        structured_outputs=True,
    )

    best_practice_validator: Agent = Agent(
        name="Best Practice Validator",
        role="Code Quality and Best Practices Expert",
        model=OpenAIChat(id="gpt-4o-mini"),
        description=(
            "You are an expert in Python best practices and FSA (Workflow) best practices. "
            "You validate code against established standards and identify areas for improvement."
        ),
        instructions=[
            "Check for proper use of type hints and Pydantic models",
            "Validate agent configuration and usage",
            "Check for proper error handling and edge cases",
            "Verify storage and session management patterns",
            "Check for code documentation and clarity",
            "Validate naming conventions and code style",
            "Check for security best practices",
            "Assess code complexity and maintainability"
        ],
        response_model=List[BestPracticeCheck],
        structured_outputs=True,
    )

    quality_assessor: Agent = Agent(
        name="Quality Assessor",
        role="Code Quality Metrics Specialist",
        model=OpenAIChat(id="gpt-4o-mini"),
        description=(
            "You are an expert at assessing code quality through various metrics. "
            "You evaluate complexity, maintainability, modularity, and reusability."
        ),
        instructions=[
            "Calculate complexity scores based on nesting, branching, and logic",
            "Assess maintainability through code clarity and structure",
            "Evaluate modularity and component separation",
            "Determine reusability potential of components",
            "Identify code smells and anti-patterns",
            "Provide actionable observations"
        ],
        response_model=CodeQualityMetrics,
        structured_outputs=True,
    )

    similarity_analyzer: Agent = Agent(
        name="Similarity Analyzer",
        role="Code Similarity Expert",
        model=OpenAIChat(id="gpt-4o-mini"),
        description=(
            "You are an expert at comparing code files and identifying similarities and differences. "
            "You analyze structural similarity, pattern usage, and implementation approaches."
        ),
        instructions=[
            "Compare code structure and organization",
            "Identify common patterns and shared approaches",
            "Calculate similarity scores for different aspects",
            "Highlight key differences in implementation",
            "Note reusable components or patterns",
            "Provide detailed comparison insights"
        ],
        response_model=SimilarityAnalysis,
        structured_outputs=True,
    )

    report_generator: Agent = Agent(
        name="Report Generator",
        role="Technical Report Writer",
        model=OpenAIChat(id="gpt-4o-mini"),
        description=(
            "You are an expert at synthesizing technical analysis into clear, actionable reports. "
            "You create comprehensive pattern analysis reports with prioritized recommendations."
        ),
        instructions=[
            "Synthesize all analysis results into a coherent report",
            "Create a clear executive summary",
            "Prioritize recommendations by impact",
            "Calculate an overall quality score",
            "Ensure the report is actionable and clear",
            "Highlight the most important findings"
        ],
        markdown=True,
    )

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def read_file_contents(self, file_path: str) -> str:
        """Read and return file contents"""
        try:
            path = Path(file_path)
            if not path.exists():
                return f"Error: File not found: {file_path}"

            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()

            return f"File: {file_path}\n{'='*80}\n{content}"
        except Exception as e:
            return f"Error reading {file_path}: {str(e)}"

    def analyze_code_structure(self, file_contents: str) -> str:
        """Analyze code structure using the code reader agent"""
        prompt = f"""
        Analyze the following FSA (Workflow) code and provide a detailed structural analysis:

        {file_contents}

        Please provide:
        1. Overall structure and purpose
        2. List of classes and their roles
        3. Agents defined and their configurations
        4. Workflow execution flow
        5. Data models and structures used
        6. Key methods and their purposes
        7. Dependencies and integrations
        """

        response = self.code_reader.run(prompt)
        return response.content

    def detect_patterns(self, file_contents: str, structural_analysis: str) -> List[DesignPattern]:
        """Detect design patterns in the code"""
        prompt = f"""
        Based on this code and structural analysis, identify all design patterns used:

        CODE:
        {file_contents}

        STRUCTURAL ANALYSIS:
        {structural_analysis}

        Identify design patterns such as:
        - Creational: Factory, Builder, Singleton, Prototype
        - Structural: Adapter, Decorator, Facade, Composite
        - Behavioral: Strategy, Observer, Chain of Responsibility, Template Method
        - FSA-specific: Sequential Pipeline, Conditional Branching, Event-Driven

        For each pattern, provide:
        - Pattern name
        - Confidence score (0.0 to 1.0)
        - Exact location in code
        - Description of how it's implemented
        - Code snippet if applicable
        """

        response = self.pattern_detector.run(prompt)
        return response.content if isinstance(response.content, list) else []

    def analyze_architecture(self, file_contents: str, structural_analysis: str) -> List[ArchitecturalPattern]:
        """Analyze architectural patterns"""
        prompt = f"""
        Based on this code and structural analysis, identify architectural patterns:

        CODE:
        {file_contents}

        STRUCTURAL ANALYSIS:
        {structural_analysis}

        Identify patterns such as:
        - Layered Architecture
        - Model-View-Controller (MVC)
        - Pipeline Architecture
        - Event-Driven Architecture
        - Microservices patterns
        - FSA orchestration patterns

        For each pattern, provide:
        - Pattern name
        - Key components
        - Description of the architecture
        - Quality score (0.0 to 1.0)
        """

        response = self.architecture_analyzer.run(prompt)
        return response.content if isinstance(response.content, list) else []

    def validate_best_practices(self, file_contents: str) -> List[BestPracticeCheck]:
        """Validate against best practices"""
        prompt = f"""
        Validate this FSA code against best practices:

        {file_contents}

        Check for:
        - Proper type hints and Pydantic model usage
        - Agent configuration and structured outputs
        - Error handling and edge cases
        - Code documentation and clarity
        - Naming conventions (PEP 8)
        - Security best practices (no hardcoded secrets, input validation)
        - Storage and session management
        - Complexity and code organization
        - DRY principle and code reuse
        - FSA-specific best practices (session_state usage, RunResponse returns)

        For each check, provide:
        - Practice being checked
        - Status: 'pass', 'warning', or 'fail'
        - Details explaining the finding
        - Recommendation if needed
        """

        response = self.best_practice_validator.run(prompt)
        return response.content if isinstance(response.content, list) else []

    def assess_code_quality(self, file_contents: str, structural_analysis: str) -> CodeQualityMetrics:
        """Assess code quality metrics"""
        prompt = f"""
        Assess the code quality of this FSA implementation:

        CODE:
        {file_contents}

        STRUCTURAL ANALYSIS:
        {structural_analysis}

        Provide metrics for:
        - Complexity score (nesting, branching, cyclomatic complexity)
        - Maintainability score (readability, documentation, clarity)
        - Modularity score (separation of concerns, component independence)
        - Reusability score (component reuse potential, generalization)
        - Key observations (strengths and weaknesses)

        Each score should be 0.0 (worst) to 1.0 (best).
        """

        response = self.quality_assessor.run(prompt)
        return response.content if isinstance(response.content, CodeQualityMetrics) else CodeQualityMetrics(
            complexity_score=0.5,
            maintainability_score=0.5,
            modularity_score=0.5,
            reusability_score=0.5,
            key_observations=["Analysis failed"]
        )

    def compare_fsas(self, file1_content: str, file2_content: str, file1_path: str, file2_path: str) -> SimilarityAnalysis:
        """Compare two FSA implementations for similarity"""
        prompt = f"""
        Compare these two FSA implementations and provide a detailed similarity analysis:

        FILE 1: {file1_path}
        {file1_content}

        FILE 2: {file2_path}
        {file2_content}

        Analyze:
        - Overall similarity score (0.0 to 1.0)
        - Structural similarity (code organization, class structure)
        - Pattern similarity (shared design patterns and approaches)
        - Common patterns found in both
        - Key differences in implementation

        Provide a detailed comparison with specific examples.
        """

        response = self.similarity_analyzer.run(prompt)
        return response.content if isinstance(response.content, SimilarityAnalysis) else SimilarityAnalysis(
            file_pair=f"{file1_path} vs {file2_path}",
            similarity_score=0.0,
            structural_similarity=0.0,
            pattern_similarity=0.0,
            common_patterns=[],
            differences=["Analysis failed"]
        )

    def generate_report(
        self,
        files_analyzed: List[str],
        design_patterns: List[DesignPattern],
        architectural_patterns: List[ArchitecturalPattern],
        best_practices: List[BestPracticeCheck],
        code_quality: Optional[CodeQualityMetrics],
        similarity_analyses: List[SimilarityAnalysis]
    ) -> PatternAnalysisReport:
        """Generate comprehensive analysis report"""

        # Calculate overall score
        scores = []
        if code_quality:
            scores.extend([
                code_quality.complexity_score,
                code_quality.maintainability_score,
                code_quality.modularity_score,
                code_quality.reusability_score
            ])

        if architectural_patterns:
            scores.extend([p.quality_score for p in architectural_patterns])

        # Best practices score
        if best_practices:
            pass_count = sum(1 for p in best_practices if p.status == 'pass')
            bp_score = pass_count / len(best_practices) if best_practices else 0.5
            scores.append(bp_score)

        overall_score = sum(scores) / len(scores) if scores else 0.5

        # Generate recommendations
        recommendations = []

        # From best practices
        for bp in best_practices:
            if bp.status in ['warning', 'fail'] and bp.recommendation:
                recommendations.append(f"[{bp.practice}] {bp.recommendation}")

        # From code quality
        if code_quality:
            if code_quality.complexity_score < 0.6:
                recommendations.append("Reduce code complexity by breaking down complex methods")
            if code_quality.maintainability_score < 0.6:
                recommendations.append("Improve code documentation and naming clarity")
            if code_quality.modularity_score < 0.6:
                recommendations.append("Enhance modularity by separating concerns into distinct components")

        # Pattern recommendations
        pattern_names = [p.pattern_name.lower() for p in design_patterns]
        if 'factory' not in pattern_names and len(design_patterns) > 3:
            recommendations.append("Consider using Factory pattern for object creation")
        if 'strategy' not in pattern_names:
            recommendations.append("Consider Strategy pattern for algorithm variations")

        # Limit to top 5 recommendations
        recommendations = recommendations[:5] if recommendations else ["Code looks good! Continue following best practices."]

        # Create summary
        summary_prompt = f"""
        Create an executive summary for this pattern analysis:

        Files: {', '.join(files_analyzed)}
        Design Patterns Found: {len(design_patterns)}
        Architectural Patterns: {len(architectural_patterns)}
        Best Practice Checks: {len(best_practices)} ({sum(1 for p in best_practices if p.status == 'pass')} passed)
        Overall Score: {overall_score:.2f}/1.0

        Key Findings:
        - Design Patterns: {[p.pattern_name for p in design_patterns[:3]]}
        - Architecture: {[p.pattern_name for p in architectural_patterns[:2]]}
        - Top Issues: {[p.practice for p in best_practices if p.status == 'fail'][:3]}

        Write a 2-3 sentence executive summary.
        """

        summary_response = self.report_generator.run(summary_prompt)
        summary = summary_response.content if isinstance(summary_response.content, str) else "Analysis complete."

        return PatternAnalysisReport(
            summary=summary,
            files_analyzed=files_analyzed,
            design_patterns=design_patterns,
            architectural_patterns=architectural_patterns,
            best_practices=best_practices,
            code_quality=code_quality,
            similarity_analyses=similarity_analyses,
            recommendations=recommendations,
            overall_score=overall_score
        )

    # ========================================================================
    # Main Workflow Execution
    # ========================================================================

    def run(
        self,
        fsa_files: List[str],
        analysis_type: str = "comprehensive",
        pattern_definitions: Optional[Dict[str, Any]] = None
    ) -> RunResponse:
        """
        Run pattern analysis on FSA implementations.

        Args:
            fsa_files: List of file paths to FSA implementations to analyze
            analysis_type: Type of analysis - "comprehensive", "patterns_only", "quality_only", or "similarity"
            pattern_definitions: Optional custom pattern definitions to look for

        Returns:
            RunResponse containing PatternAnalysisReport
        """

        # Validate inputs
        if not fsa_files:
            return RunResponse(
                content="Error: No FSA files provided for analysis",
                event=RunEvent.workflow_completed,
                run_id=self.run_id,
                session_id=self.session_id
            )

        print(f"\n{'='*80}")
        print(f"Pattern Analyzer FSA - Starting Analysis")
        print(f"{'='*80}")
        print(f"Files to analyze: {len(fsa_files)}")
        print(f"Analysis type: {analysis_type}")
        print(f"{'='*80}\n")

        # Initialize result collections
        all_design_patterns = []
        all_architectural_patterns = []
        all_best_practices = []
        all_quality_metrics = []
        similarity_analyses = []

        # Read all files
        file_contents = {}
        for file_path in fsa_files:
            print(f"📄 Reading: {file_path}")
            content = self.read_file_contents(file_path)
            file_contents[file_path] = content

        # Perform analysis based on type
        if analysis_type in ["comprehensive", "patterns_only"]:
            print(f"\n🔍 Analyzing patterns...")

            for file_path, content in file_contents.items():
                print(f"\n  Analyzing: {file_path}")

                # Step 1: Code structure analysis
                print(f"    ├─ Reading code structure...")
                structural_analysis = self.analyze_code_structure(content)

                # Step 2: Pattern detection
                print(f"    ├─ Detecting design patterns...")
                design_patterns = self.detect_patterns(content, structural_analysis)
                all_design_patterns.extend(design_patterns)
                print(f"    │  Found {len(design_patterns)} patterns")

                # Step 3: Architecture analysis
                print(f"    └─ Analyzing architecture...")
                arch_patterns = self.analyze_architecture(content, structural_analysis)
                all_architectural_patterns.extend(arch_patterns)
                print(f"       Found {len(arch_patterns)} architectural patterns")

        if analysis_type in ["comprehensive", "quality_only"]:
            print(f"\n✅ Validating best practices and quality...")

            for file_path, content in file_contents.items():
                print(f"\n  Validating: {file_path}")

                # Best practices validation
                print(f"    ├─ Checking best practices...")
                bp_checks = self.validate_best_practices(content)
                all_best_practices.extend(bp_checks)
                passed = sum(1 for p in bp_checks if p.status == 'pass')
                print(f"    │  {passed}/{len(bp_checks)} checks passed")

                # Quality assessment
                print(f"    └─ Assessing code quality...")
                structural_analysis = self.analyze_code_structure(content)
                quality = self.assess_code_quality(content, structural_analysis)
                all_quality_metrics.append(quality)
                print(f"       Quality score: {quality.maintainability_score:.2f}")

        if analysis_type == "similarity" and len(fsa_files) >= 2:
            print(f"\n🔗 Performing similarity analysis...")

            # Compare each pair of files
            for i in range(len(fsa_files)):
                for j in range(i + 1, len(fsa_files)):
                    file1 = fsa_files[i]
                    file2 = fsa_files[j]
                    print(f"  Comparing: {file1} <-> {file2}")

                    similarity = self.compare_fsas(
                        file_contents[file1],
                        file_contents[file2],
                        file1,
                        file2
                    )
                    similarity_analyses.append(similarity)
                    print(f"    Similarity: {similarity.similarity_score:.2%}")

        # Average quality metrics if multiple files
        avg_quality = None
        if all_quality_metrics:
            avg_quality = CodeQualityMetrics(
                complexity_score=sum(q.complexity_score for q in all_quality_metrics) / len(all_quality_metrics),
                maintainability_score=sum(q.maintainability_score for q in all_quality_metrics) / len(all_quality_metrics),
                modularity_score=sum(q.modularity_score for q in all_quality_metrics) / len(all_quality_metrics),
                reusability_score=sum(q.reusability_score for q in all_quality_metrics) / len(all_quality_metrics),
                key_observations=[obs for q in all_quality_metrics for obs in q.key_observations]
            )

        # Generate final report
        print(f"\n📊 Generating analysis report...")
        report = self.generate_report(
            files_analyzed=fsa_files,
            design_patterns=all_design_patterns,
            architectural_patterns=all_architectural_patterns,
            best_practices=all_best_practices,
            code_quality=avg_quality,
            similarity_analyses=similarity_analyses
        )

        print(f"\n{'='*80}")
        print(f"✅ Analysis Complete!")
        print(f"{'='*80}")
        print(f"Overall Score: {report.overall_score:.2f}/1.0")
        print(f"Design Patterns: {len(report.design_patterns)}")
        print(f"Architectural Patterns: {len(report.architectural_patterns)}")
        print(f"Best Practice Checks: {len(report.best_practices)}")
        print(f"Top Recommendations: {len(report.recommendations)}")
        print(f"{'='*80}\n")

        return RunResponse(
            content=report,
            event=RunEvent.workflow_completed,
            run_id=self.run_id,
            session_id=self.session_id
        )


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == "__main__":
    import json
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.markdown import Markdown

    console = Console()

    # Create analyzer with storage
    analyzer = PatternAnalyzerFSA(
        session_id="pattern-analysis-demo",
        storage=SqliteStorage(
            table_name="pattern_analyses",
            db_file="tmp/pattern_analyzer.db"
        ),
        debug_mode=True
    )

    # Example 1: Comprehensive analysis of a single FSA
    console.print("\n[bold cyan]Example 1: Comprehensive Analysis[/bold cyan]\n")

    result1 = analyzer.run(
        fsa_files=["cookbook/workflows/blog_post_generator.py"],
        analysis_type="comprehensive"
    )

    report: PatternAnalysisReport = result1.content

    # Display report
    console.print(Panel(report.summary, title="[bold]Executive Summary[/bold]", border_style="green"))

    # Design Patterns Table
    if report.design_patterns:
        patterns_table = Table(title="Design Patterns Detected", show_header=True, header_style="bold magenta")
        patterns_table.add_column("Pattern", style="cyan")
        patterns_table.add_column("Confidence", justify="right")
        patterns_table.add_column("Location", style="yellow")

        for pattern in report.design_patterns[:5]:  # Top 5
            patterns_table.add_row(
                pattern.pattern_name,
                f"{pattern.confidence:.1%}",
                pattern.location
            )

        console.print(patterns_table)

    # Best Practices Table
    if report.best_practices:
        bp_table = Table(title="Best Practice Validation", show_header=True, header_style="bold blue")
        bp_table.add_column("Practice", style="cyan")
        bp_table.add_column("Status", justify="center")
        bp_table.add_column("Details")

        for bp in report.best_practices[:10]:  # Top 10
            status_style = "green" if bp.status == "pass" else "yellow" if bp.status == "warning" else "red"
            bp_table.add_row(
                bp.practice,
                f"[{status_style}]{bp.status.upper()}[/{status_style}]",
                bp.details[:50] + "..." if len(bp.details) > 50 else bp.details
            )

        console.print(bp_table)

    # Quality Metrics
    if report.code_quality:
        quality_table = Table(title="Code Quality Metrics", show_header=True, header_style="bold yellow")
        quality_table.add_column("Metric", style="cyan")
        quality_table.add_column("Score", justify="right")
        quality_table.add_column("Rating")

        def get_rating(score: float) -> str:
            if score >= 0.8:
                return "[green]Excellent[/green]"
            elif score >= 0.6:
                return "[yellow]Good[/yellow]"
            elif score >= 0.4:
                return "[orange1]Fair[/orange1]"
            else:
                return "[red]Needs Improvement[/red]"

        quality_table.add_row("Complexity", f"{report.code_quality.complexity_score:.2f}", get_rating(report.code_quality.complexity_score))
        quality_table.add_row("Maintainability", f"{report.code_quality.maintainability_score:.2f}", get_rating(report.code_quality.maintainability_score))
        quality_table.add_row("Modularity", f"{report.code_quality.modularity_score:.2f}", get_rating(report.code_quality.modularity_score))
        quality_table.add_row("Reusability", f"{report.code_quality.reusability_score:.2f}", get_rating(report.code_quality.reusability_score))

        console.print(quality_table)

    # Recommendations
    console.print("\n[bold green]Top Recommendations:[/bold green]")
    for i, rec in enumerate(report.recommendations, 1):
        console.print(f"  {i}. {rec}")

    console.print(f"\n[bold]Overall Quality Score: {report.overall_score:.2f}/1.0[/bold]")

    # Example 2: Similarity analysis between multiple FSAs
    console.print("\n\n[bold cyan]Example 2: Similarity Analysis[/bold cyan]\n")

    result2 = analyzer.run(
        fsa_files=[
            "cookbook/workflows/blog_post_generator.py",
            "cookbook/workflows/startup_idea_validator.py"
        ],
        analysis_type="similarity"
    )

    report2: PatternAnalysisReport = result2.content

    if report2.similarity_analyses:
        for sim in report2.similarity_analyses:
            console.print(Panel(
                f"Overall Similarity: {sim.similarity_score:.1%}\n"
                f"Structural: {sim.structural_similarity:.1%} | Pattern: {sim.pattern_similarity:.1%}\n\n"
                f"Common Patterns: {', '.join(sim.common_patterns) if sim.common_patterns else 'None'}\n\n"
                f"Key Differences:\n" + "\n".join(f"  • {diff}" for diff in sim.differences[:3]),
                title=f"[bold]Similarity: {sim.file_pair}[/bold]",
                border_style="blue"
            ))

    console.print("\n[bold green]✅ Pattern Analysis Complete![/bold green]\n")

"""
FSA Dependency Graph Analyzer

Analyzes dependencies between FSAs to detect cycles, missing dependencies,
and optimal execution order.

Example usage:
    python cookbook/workflows/fsa_dependency_analyzer.py
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple
from textwrap import dedent

from agno.workflow import Workflow, RunResponse
from agno.utils.log import logger

try:
    from agno.agent import Agent
    from agno.models.openai import OpenAIChat
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False
    Agent = None
    OpenAIChat = None


@dataclass
class FSANode:
    """Represents an FSA node in the dependency graph."""

    name: str
    fsa_type: str  # "workflow" or "agent"
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        return isinstance(other, FSANode) and self.name == other.name


@dataclass
class DependencyGraph:
    """Represents the dependency graph structure."""

    nodes: Dict[str, FSANode] = field(default_factory=dict)
    adjacency_list: Dict[str, List[str]] = field(default_factory=dict)

    def add_node(self, node: FSANode) -> None:
        """Add a node to the graph."""
        self.nodes[node.name] = node
        if node.name not in self.adjacency_list:
            self.adjacency_list[node.name] = []

    def add_edge(self, from_node: str, to_node: str) -> None:
        """Add a directed edge from one node to another."""
        if from_node not in self.adjacency_list:
            self.adjacency_list[from_node] = []
        if to_node not in self.adjacency_list[from_node]:
            self.adjacency_list[from_node].append(to_node)

    def get_dependencies(self, node_name: str) -> List[str]:
        """Get all dependencies for a node."""
        return self.adjacency_list.get(node_name, [])

    def to_dict(self) -> Dict[str, Any]:
        """Convert graph to dictionary representation."""
        return {
            "nodes": {
                name: {
                    "name": node.name,
                    "type": node.fsa_type,
                    "dependencies": node.dependencies,
                    "metadata": node.metadata,
                }
                for name, node in self.nodes.items()
            },
            "edges": {
                name: deps for name, deps in self.adjacency_list.items() if deps
            },
        }


class DependencyAnalyzer:
    """Core analysis engine for dependency graphs."""

    def __init__(self, graph: DependencyGraph):
        self.graph = graph
        self.visited: Set[str] = set()
        self.rec_stack: Set[str] = set()
        self.cycles: List[List[str]] = []

    def detect_cycles(self) -> List[List[str]]:
        """
        Detect cycles in the dependency graph using DFS.

        Returns:
            List of cycles, where each cycle is a list of node names.
        """
        self.cycles = []
        self.visited = set()
        self.rec_stack = set()

        for node_name in self.graph.nodes:
            if node_name not in self.visited:
                self._dfs_cycle_detection(node_name, [])

        return self.cycles

    def _dfs_cycle_detection(
        self, node: str, path: List[str]
    ) -> bool:
        """
        DFS helper for cycle detection.

        Args:
            node: Current node being visited
            path: Current path in the DFS traversal

        Returns:
            True if a cycle is detected, False otherwise
        """
        self.visited.add(node)
        self.rec_stack.add(node)
        current_path = path + [node]

        for neighbor in self.graph.get_dependencies(node):
            if neighbor not in self.visited:
                if self._dfs_cycle_detection(neighbor, current_path):
                    return True
            elif neighbor in self.rec_stack:
                # Cycle detected
                cycle_start = current_path.index(neighbor)
                cycle = current_path[cycle_start:] + [neighbor]
                if cycle not in self.cycles:
                    self.cycles.append(cycle)
                return True

        self.rec_stack.remove(node)
        return False

    def topological_sort(self) -> Tuple[List[str], bool]:
        """
        Perform topological sort to find optimal execution order.

        Returns:
            Tuple of (execution_order, has_cycles)
            - execution_order: List of node names in execution order
            - has_cycles: True if graph has cycles (sort is invalid)
        """
        # First check for cycles
        cycles = self.detect_cycles()
        if cycles:
            return [], True

        # Calculate in-degrees
        in_degree = {node: 0 for node in self.graph.nodes}
        for node in self.graph.nodes:
            for dep in self.graph.get_dependencies(node):
                if dep in in_degree:
                    in_degree[dep] += 1

        # Find all nodes with in-degree 0
        queue = [node for node, degree in in_degree.items() if degree == 0]
        execution_order = []

        while queue:
            # Sort queue for deterministic ordering
            queue.sort()
            node = queue.pop(0)
            execution_order.append(node)

            # Reduce in-degree for dependent nodes
            for dep in self.graph.get_dependencies(node):
                if dep in in_degree:
                    in_degree[dep] -= 1
                    if in_degree[dep] == 0:
                        queue.append(dep)

        # Check if all nodes were processed
        if len(execution_order) != len(self.graph.nodes):
            return execution_order, True  # Cycle exists

        return execution_order, False

    def find_missing_dependencies(self) -> List[str]:
        """
        Find dependencies that are referenced but not defined.

        Returns:
            List of missing dependency names
        """
        defined_nodes = set(self.graph.nodes.keys())
        referenced_nodes = set()

        for deps in self.graph.adjacency_list.values():
            referenced_nodes.update(deps)

        missing = referenced_nodes - defined_nodes
        return sorted(list(missing))

    def calculate_depth(self) -> Dict[str, int]:
        """
        Calculate the depth of each node in the dependency tree.
        Depth = longest path from a root node.

        Returns:
            Dictionary mapping node names to their depths
        """
        depth = {node: 0 for node in self.graph.nodes}
        execution_order, has_cycles = self.topological_sort()

        if has_cycles:
            return depth

        # Process nodes in topological order
        for node in execution_order:
            for dep in self.graph.get_dependencies(node):
                if dep in depth:
                    depth[dep] = max(depth[dep], depth[node] + 1)

        return depth


class FSADependencyAnalyzer(Workflow):
    """
    FSA Dependency Graph Analyzer Workflow

    Analyzes dependencies between FSAs to detect cycles, missing dependencies,
    and optimal execution order.
    """

    description: str = "Analyzes FSA dependency relationships and execution ordering"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Initialize analysis agent only if OpenAI is available
        if HAS_OPENAI:
            self.analysis_agent = Agent(
                name="Dependency Analysis Agent",
                model=OpenAIChat(id="gpt-4o-mini"),
                instructions=[
                    "You are an expert at analyzing FSA dependency graphs.",
                    "Provide clear, actionable insights about the dependency structure.",
                    "Highlight potential issues and optimization opportunities.",
                    "Format your analysis in a clear, structured way.",
                ],
                markdown=True,
                show_tool_calls=False,
            )
        else:
            self.analysis_agent = None

    def build_dependency_graph(
        self, fsa_collection: List[Dict[str, Any]]
    ) -> DependencyGraph:
        """
        Build a dependency graph from a collection of FSAs.

        Args:
            fsa_collection: List of FSA definitions, each containing:
                - name: FSA name
                - type: "workflow" or "agent"
                - dependencies: List of dependency names
                - metadata: Optional metadata dictionary

        Returns:
            DependencyGraph object
        """
        graph = DependencyGraph()

        # First pass: Add all nodes
        for fsa_def in fsa_collection:
            node = FSANode(
                name=fsa_def["name"],
                fsa_type=fsa_def.get("type", "agent"),
                dependencies=fsa_def.get("dependencies", []),
                metadata=fsa_def.get("metadata", {}),
            )
            graph.add_node(node)

        # Second pass: Add edges based on dependencies
        for fsa_def in fsa_collection:
            node_name = fsa_def["name"]
            for dep in fsa_def.get("dependencies", []):
                # Edge goes from node to its dependency (node depends on dep)
                graph.add_edge(node_name, dep)

        return graph

    def analyze_dependencies(
        self, fsa_collection: List[Dict[str, Any]], execution_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Main analysis method that produces the complete dependency analysis.

        Args:
            fsa_collection: List of FSA definitions
            execution_context: Optional context for analysis

        Returns:
            Dictionary containing:
                - dependency_graph: Graph structure
                - execution_order: Optimal execution order
                - cycle_warnings: List of detected cycles
                - missing_dependencies: List of missing dependencies
                - depth_analysis: Depth of each node
                - statistics: Analysis statistics
        """
        # Build the graph
        graph = self.build_dependency_graph(fsa_collection)

        # Create analyzer
        analyzer = DependencyAnalyzer(graph)

        # Perform analysis
        cycles = analyzer.detect_cycles()
        execution_order, has_cycles = analyzer.topological_sort()
        missing_deps = analyzer.find_missing_dependencies()
        depth_analysis = analyzer.calculate_depth()

        # Compile results
        results = {
            "dependency_graph": graph.to_dict(),
            "execution_order": execution_order,
            "cycle_warnings": [
                {
                    "cycle": cycle,
                    "severity": "critical",
                    "message": f"Circular dependency detected: {' -> '.join(cycle)}",
                }
                for cycle in cycles
            ],
            "missing_dependencies": [
                {
                    "name": dep,
                    "severity": "error",
                    "message": f"Dependency '{dep}' is referenced but not defined",
                }
                for dep in missing_deps
            ],
            "depth_analysis": depth_analysis,
            "statistics": {
                "total_fsas": len(graph.nodes),
                "total_dependencies": sum(
                    len(deps) for deps in graph.adjacency_list.values()
                ),
                "has_cycles": has_cycles or len(cycles) > 0,
                "missing_count": len(missing_deps),
                "max_depth": max(depth_analysis.values()) if depth_analysis else 0,
            },
            "execution_context": execution_context or {},
        }

        return results

    def run(
        self,
        fsa_collection: List[Dict[str, Any]],
        execution_context: Optional[Dict[str, Any]] = None,
    ) -> Iterator[RunResponse]:
        """
        Run the FSA dependency analysis workflow.

        Args:
            fsa_collection: List of FSA definitions
            execution_context: Optional context for analysis

        Yields:
            RunResponse containing analysis results
        """
        logger.info("Starting FSA Dependency Analysis")
        logger.info(f"Analyzing {len(fsa_collection)} FSAs")

        # Perform analysis
        results = self.analyze_dependencies(fsa_collection, execution_context)

        # Format results for the analysis agent
        analysis_prompt = self._format_analysis_prompt(results)

        # Get insights from the analysis agent if available
        if self.analysis_agent:
            logger.info("Generating analysis insights")
            yield from self.analysis_agent.run(analysis_prompt)
        else:
            # Simple text output when agent is not available
            logger.info("OpenAI not available, providing basic analysis")
            print("\n" + "="*80)
            print("FSA DEPENDENCY ANALYSIS RESULTS")
            print("="*80)
            print(analysis_prompt)
            print("="*80 + "\n")

        # Store results in session state
        self.session_state["analysis_results"] = results

        logger.info("FSA Dependency Analysis complete")

    def _format_analysis_prompt(self, results: Dict[str, Any]) -> str:
        """Format the analysis results into a prompt for the analysis agent."""
        stats = results["statistics"]

        prompt = dedent(f"""
        Analyze the following FSA dependency graph and provide insights:

        ## Statistics
        - Total FSAs: {stats['total_fsas']}
        - Total Dependencies: {stats['total_dependencies']}
        - Has Cycles: {stats['has_cycles']}
        - Missing Dependencies: {stats['missing_count']}
        - Maximum Depth: {stats['max_depth']}

        ## Execution Order
        {self._format_execution_order(results['execution_order'], results['depth_analysis'])}

        ## Cycle Warnings
        {self._format_cycles(results['cycle_warnings'])}

        ## Missing Dependencies
        {self._format_missing(results['missing_dependencies'])}

        ## Dependency Graph Structure
        {self._format_graph(results['dependency_graph'])}

        Please provide:
        1. An overall assessment of the dependency structure
        2. Potential issues and their severity
        3. Recommendations for optimization
        4. Execution strategy suggestions
        """).strip()

        return prompt

    def _format_execution_order(
        self, execution_order: List[str], depth_analysis: Dict[str, int]
    ) -> str:
        """Format execution order for display."""
        if not execution_order:
            return "❌ No valid execution order (cycles detected)"

        lines = ["✅ Recommended execution order:"]
        for i, node in enumerate(execution_order, 1):
            depth = depth_analysis.get(node, 0)
            lines.append(f"  {i}. {node} (depth: {depth})")

        return "\n".join(lines)

    def _format_cycles(self, cycle_warnings: List[Dict[str, Any]]) -> str:
        """Format cycle warnings for display."""
        if not cycle_warnings:
            return "✅ No cycles detected"

        lines = [f"❌ {len(cycle_warnings)} cycle(s) detected:"]
        for i, warning in enumerate(cycle_warnings, 1):
            lines.append(f"  {i}. {warning['message']}")

        return "\n".join(lines)

    def _format_missing(self, missing_dependencies: List[Dict[str, Any]]) -> str:
        """Format missing dependencies for display."""
        if not missing_dependencies:
            return "✅ No missing dependencies"

        lines = [f"❌ {len(missing_dependencies)} missing dependenc{'y' if len(missing_dependencies) == 1 else 'ies'}:"]
        for i, dep in enumerate(missing_dependencies, 1):
            lines.append(f"  {i}. {dep['message']}")

        return "\n".join(lines)

    def _format_graph(self, graph_dict: Dict[str, Any]) -> str:
        """Format graph structure for display."""
        lines = ["Nodes and their dependencies:"]

        for node_name, node_info in sorted(graph_dict["nodes"].items()):
            deps = node_info.get("dependencies", [])
            if deps:
                lines.append(f"  - {node_name} → {', '.join(deps)}")
            else:
                lines.append(f"  - {node_name} (no dependencies)")

        return "\n".join(lines)


# Example usage with sample FSAs
def create_sample_fsas() -> List[Dict[str, Any]]:
    """Create sample FSA definitions for testing."""
    return [
        {
            "name": "DataCollector",
            "type": "agent",
            "dependencies": [],
            "metadata": {
                "description": "Collects raw data from various sources",
                "tools": ["web_scraper", "api_client"],
            },
        },
        {
            "name": "DataProcessor",
            "type": "agent",
            "dependencies": ["DataCollector"],
            "metadata": {
                "description": "Processes and cleans collected data",
                "tools": ["data_cleaner", "validator"],
            },
        },
        {
            "name": "DataAnalyzer",
            "type": "agent",
            "dependencies": ["DataProcessor"],
            "metadata": {
                "description": "Analyzes processed data for insights",
                "tools": ["statistical_analyzer", "ml_model"],
            },
        },
        {
            "name": "ReportGenerator",
            "type": "workflow",
            "dependencies": ["DataAnalyzer", "DataProcessor"],
            "metadata": {
                "description": "Generates comprehensive reports from analysis",
                "tools": ["pdf_generator", "chart_creator"],
            },
        },
    ]


def create_cyclic_sample_fsas() -> List[Dict[str, Any]]:
    """Create sample FSA definitions with a cycle for testing."""
    return [
        {
            "name": "FSA_A",
            "type": "agent",
            "dependencies": ["FSA_B"],
            "metadata": {"description": "FSA A depends on B"},
        },
        {
            "name": "FSA_B",
            "type": "agent",
            "dependencies": ["FSA_C"],
            "metadata": {"description": "FSA B depends on C"},
        },
        {
            "name": "FSA_C",
            "type": "agent",
            "dependencies": ["FSA_A"],  # Creates cycle: A -> B -> C -> A
            "metadata": {"description": "FSA C depends on A (creates cycle!)"},
        },
        {
            "name": "FSA_D",
            "type": "agent",
            "dependencies": ["FSA_X"],  # Missing dependency
            "metadata": {"description": "FSA D depends on missing FSA_X"},
        },
    ]


if __name__ == "__main__":
    # Example 1: Valid dependency graph
    print("\n" + "=" * 80)
    print("EXAMPLE 1: Valid Dependency Graph")
    print("=" * 80 + "\n")

    analyzer = FSADependencyAnalyzer(name="FSA Dependency Analyzer")
    sample_fsas = create_sample_fsas()

    # Run analysis and consume the iterator
    for response in analyzer.run(
        fsa_collection=sample_fsas,
        execution_context={"environment": "development", "version": "1.0.0"},
    ):
        pass  # Consume the generator

    # Print detailed results
    results = analyzer.session_state.get("analysis_results", {})
    print("\n--- Raw Analysis Results ---")
    print(f"Execution Order: {results.get('execution_order', [])}")
    print(f"Cycles: {len(results.get('cycle_warnings', []))}")
    print(f"Missing Dependencies: {len(results.get('missing_dependencies', []))}")
    print(f"Statistics: {results.get('statistics', {})}")

    # Example 2: Cyclic dependency graph
    print("\n" + "=" * 80)
    print("EXAMPLE 2: Cyclic Dependency Graph (with issues)")
    print("=" * 80 + "\n")

    analyzer2 = FSADependencyAnalyzer(name="FSA Dependency Analyzer - Cyclic")
    cyclic_fsas = create_cyclic_sample_fsas()

    # Run analysis and consume the iterator
    for response in analyzer2.run(
        fsa_collection=cyclic_fsas,
        execution_context={"environment": "testing", "version": "1.0.0"},
    ):
        pass  # Consume the generator

    # Print detailed results
    results2 = analyzer2.session_state.get("analysis_results", {})
    print("\n--- Raw Analysis Results ---")
    print(f"Execution Order: {results2.get('execution_order', [])} (empty due to cycles)")
    print(f"Cycles Detected: {len(results2.get('cycle_warnings', []))}")
    for cycle in results2.get('cycle_warnings', []):
        print(f"  - {cycle['message']}")
    print(f"Missing Dependencies: {len(results2.get('missing_dependencies', []))}")
    for missing in results2.get('missing_dependencies', []):
        print(f"  - {missing['message']}")

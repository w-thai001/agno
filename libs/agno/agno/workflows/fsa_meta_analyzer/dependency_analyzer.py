"""
FSA Dependency Graph Analyzer - Analyzes dependencies between FSAs and agents.

Builds dependency graphs, detects circular dependencies, analyzes coupling,
and identifies opportunities for modularization.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple

from agno.workflows.fsa_meta_analyzer.static_analyzer import FSAStructure


@dataclass
class DependencyNode:
    """Represents a node in the dependency graph."""

    name: str
    node_type: str  # 'workflow', 'agent', 'state'
    dependencies: Set[str] = field(default_factory=set)
    dependents: Set[str] = field(default_factory=set)


@dataclass
class DependencyCycle:
    """Represents a circular dependency."""

    cycle_path: List[str]
    severity: str  # 'critical', 'warning', 'info'
    description: str


@dataclass
class DependencyGraph:
    """Complete dependency graph."""

    nodes: Dict[str, DependencyNode] = field(default_factory=dict)
    edges: List[Tuple[str, str]] = field(default_factory=list)
    cycles: List[DependencyCycle] = field(default_factory=list)
    layers: List[Set[str]] = field(default_factory=list)  # Topological layers


@dataclass
class DependencyAnalysisReport:
    """Analysis report for dependencies."""

    graph: DependencyGraph
    total_dependencies: int = 0
    circular_dependencies: int = 0
    max_dependency_depth: int = 0
    highly_coupled_components: List[str] = field(default_factory=list)
    loosely_coupled_components: List[str] = field(default_factory=list)
    isolated_components: List[str] = field(default_factory=list)
    coupling_score: float = 0.0
    recommendations: List[str] = field(default_factory=list)


class DependencyAnalyzer:
    """Analyzes dependencies between FSAs, agents, and states."""

    def __init__(self):
        self.graph = DependencyGraph()

    def analyze_fsa_dependencies(self, fsa: FSAStructure) -> DependencyAnalysisReport:
        """
        Analyze dependencies within a single FSA.

        Args:
            fsa: The FSA structure to analyze

        Returns:
            DependencyAnalysisReport with dependency information
        """
        graph = DependencyGraph()

        # Build state dependency graph
        self._build_state_dependency_graph(fsa, graph)

        # Build agent dependency graph
        self._build_agent_dependency_graph(fsa, graph)

        # Detect cycles
        self._detect_cycles(graph)

        # Calculate topological layers
        self._calculate_layers(graph)

        # Create analysis report
        report = DependencyAnalysisReport(graph=graph)
        self._analyze_coupling(graph, report)
        self._identify_highly_coupled_components(graph, report)
        self._calculate_metrics(graph, report)
        self._generate_recommendations(report)

        return report

    def analyze_multiple_fsas(
        self, fsas: List[FSAStructure]
    ) -> DependencyAnalysisReport:
        """
        Analyze dependencies across multiple FSAs.

        Args:
            fsas: List of FSA structures to analyze

        Returns:
            DependencyAnalysisReport with cross-FSA dependencies
        """
        graph = DependencyGraph()

        # Build workflow nodes
        for fsa in fsas:
            workflow_node = DependencyNode(
                name=fsa.workflow_name, node_type='workflow'
            )
            graph.nodes[fsa.workflow_name] = workflow_node

            # Add agent dependencies
            for agent in fsa.agents:
                agent_key = f'{fsa.workflow_name}.{agent}'
                if agent_key not in graph.nodes:
                    agent_node = DependencyNode(name=agent_key, node_type='agent')
                    graph.nodes[agent_key] = agent_node

                # Workflow depends on agent
                workflow_node.dependencies.add(agent_key)
                graph.edges.append((fsa.workflow_name, agent_key))

                # Agent is depended on by workflow
                graph.nodes[agent_key].dependents.add(fsa.workflow_name)

        # Detect cycles
        self._detect_cycles(graph)

        # Calculate layers
        self._calculate_layers(graph)

        # Create analysis report
        report = DependencyAnalysisReport(graph=graph)
        self._analyze_coupling(graph, report)
        self._identify_highly_coupled_components(graph, report)
        self._calculate_metrics(graph, report)
        self._generate_recommendations(report)

        return report

    def _build_state_dependency_graph(self, fsa: FSAStructure, graph: DependencyGraph):
        """Build dependency graph for states within an FSA."""
        # Add state nodes
        for state_name in fsa.states:
            state_key = f'{fsa.workflow_name}.{state_name}'
            graph.nodes[state_key] = DependencyNode(name=state_key, node_type='state')

        # Add state transition dependencies
        for transition in fsa.transitions:
            from_key = f'{fsa.workflow_name}.{transition.from_state}'
            to_key = f'{fsa.workflow_name}.{transition.to_state}'

            if from_key in graph.nodes and to_key in graph.nodes:
                graph.nodes[from_key].dependencies.add(to_key)
                graph.nodes[to_key].dependents.add(from_key)
                graph.edges.append((from_key, to_key))

    def _build_agent_dependency_graph(self, fsa: FSAStructure, graph: DependencyGraph):
        """Build dependency graph for agents within an FSA."""
        # Add agent nodes
        for agent in fsa.agents:
            agent_key = f'{fsa.workflow_name}.{agent}'
            if agent_key not in graph.nodes:
                graph.nodes[agent_key] = DependencyNode(name=agent_key, node_type='agent')

        # Link states to agents they use
        for state_name, state in fsa.states.items():
            state_key = f'{fsa.workflow_name}.{state_name}'

            for agent_call in state.agent_calls:
                # Extract agent name from call (e.g., "self.my_agent.run()" -> "my_agent")
                agent_name = agent_call.split('.')[-1] if '.' in agent_call else agent_call
                agent_key = f'{fsa.workflow_name}.{agent_name}'

                if state_key in graph.nodes:
                    if agent_key not in graph.nodes:
                        graph.nodes[agent_key] = DependencyNode(
                            name=agent_key, node_type='agent'
                        )

                    # State depends on agent
                    graph.nodes[state_key].dependencies.add(agent_key)
                    graph.nodes[agent_key].dependents.add(state_key)
                    graph.edges.append((state_key, agent_key))

    def _detect_cycles(self, graph: DependencyGraph):
        """Detect circular dependencies using DFS."""
        visited: Set[str] = set()
        rec_stack: Set[str] = set()
        cycles: List[DependencyCycle] = []

        def dfs_cycle_detection(node: str, path: List[str]):
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            if node in graph.nodes:
                for dependency in graph.nodes[node].dependencies:
                    if dependency not in visited:
                        dfs_cycle_detection(dependency, path[:])
                    elif dependency in rec_stack:
                        # Found a cycle
                        cycle_start = path.index(dependency)
                        cycle_path = path[cycle_start:] + [dependency]

                        # Determine severity
                        severity = 'critical'
                        if all(
                            graph.nodes[n].node_type == 'state' for n in cycle_path[:-1]
                        ):
                            severity = 'warning'  # State cycles are expected in loops

                        cycle = DependencyCycle(
                            cycle_path=cycle_path,
                            severity=severity,
                            description=f'Circular dependency: {" -> ".join(cycle_path)}',
                        )
                        cycles.append(cycle)

            path.pop()
            rec_stack.remove(node)

        for node_name in graph.nodes:
            if node_name not in visited:
                dfs_cycle_detection(node_name, [])

        graph.cycles = cycles

    def _calculate_layers(self, graph: DependencyGraph):
        """Calculate topological layers (depth levels) in the dependency graph."""
        # Calculate in-degree for each node
        in_degree: Dict[str, int] = {node: 0 for node in graph.nodes}

        for node_name, node in graph.nodes.items():
            for dependent in node.dependents:
                if dependent in in_degree:
                    in_degree[node_name] += 1

        # Kahn's algorithm for topological sort by layers
        layers: List[Set[str]] = []
        current_layer = {node for node, degree in in_degree.items() if degree == 0}

        while current_layer:
            layers.append(current_layer)
            next_layer: Set[str] = set()

            for node_name in current_layer:
                if node_name in graph.nodes:
                    for dependency in graph.nodes[node_name].dependencies:
                        if dependency in in_degree:
                            in_degree[dependency] -= 1
                            if in_degree[dependency] == 0:
                                next_layer.add(dependency)

            current_layer = next_layer

        graph.layers = layers

    def _analyze_coupling(self, graph: DependencyGraph, report: DependencyAnalysisReport):
        """Analyze coupling between components."""
        if not graph.nodes:
            report.coupling_score = 0.0
            return

        # Calculate average coupling (dependencies per node)
        total_dependencies = sum(len(node.dependencies) for node in graph.nodes.values())
        avg_coupling = total_dependencies / len(graph.nodes)

        # Normalize to 0-100 scale (lower is better)
        # Assume 0-2 deps = excellent (100), 5+ deps = poor (0)
        report.coupling_score = max(0, 100 - (avg_coupling * 20))

        report.total_dependencies = total_dependencies

    def _identify_highly_coupled_components(
        self, graph: DependencyGraph, report: DependencyAnalysisReport
    ):
        """Identify components with high coupling."""
        highly_coupled = []
        loosely_coupled = []
        isolated = []

        for node_name, node in graph.nodes.items():
            total_coupling = len(node.dependencies) + len(node.dependents)

            if total_coupling == 0:
                isolated.append(node_name)
            elif total_coupling >= 5:
                highly_coupled.append(node_name)
            elif total_coupling <= 2:
                loosely_coupled.append(node_name)

        report.highly_coupled_components = highly_coupled
        report.loosely_coupled_components = loosely_coupled
        report.isolated_components = isolated

    def _calculate_metrics(self, graph: DependencyGraph, report: DependencyAnalysisReport):
        """Calculate dependency metrics."""
        report.circular_dependencies = len(graph.cycles)
        report.max_dependency_depth = len(graph.layers)

    def _generate_recommendations(self, report: DependencyAnalysisReport):
        """Generate recommendations based on dependency analysis."""
        recommendations = []

        # Circular dependencies
        if report.circular_dependencies > 0:
            critical_cycles = sum(
                1 for c in report.graph.cycles if c.severity == 'critical'
            )
            if critical_cycles > 0:
                recommendations.append(
                    f'CRITICAL: Found {critical_cycles} circular dependencies. '
                    f'Break cycles by introducing interfaces or dependency injection.'
                )

        # High coupling
        if report.highly_coupled_components:
            recommendations.append(
                f'Found {len(report.highly_coupled_components)} highly coupled components. '
                f'Consider breaking them down into smaller, more focused components.'
            )

        # Deep dependency chains
        if report.max_dependency_depth > 10:
            recommendations.append(
                f'Dependency depth is {report.max_dependency_depth} layers. '
                f'Consider flattening the architecture to reduce complexity.'
            )

        # Isolated components
        if report.isolated_components:
            recommendations.append(
                f'Found {len(report.isolated_components)} isolated components. '
                f'Verify these are intentionally standalone or remove if unused.'
            )

        # Low coupling score
        if report.coupling_score < 60:
            recommendations.append(
                f'Coupling score is {report.coupling_score:.0f}/100. '
                f'Reduce dependencies between components to improve maintainability.'
            )

        # Good practices
        if report.coupling_score >= 80 and report.circular_dependencies == 0:
            recommendations.append(
                'Excellent dependency structure! Low coupling and no circular dependencies.'
            )

        report.recommendations = recommendations

    def generate_graphviz_dot(self, graph: DependencyGraph) -> str:
        """
        Generate Graphviz DOT format for visualization.

        Returns:
            DOT format string for rendering the dependency graph
        """
        lines = ['digraph Dependencies {', '  rankdir=LR;', '  node [shape=box];', '']

        # Define node styles
        for node_name, node in graph.nodes.items():
            style = ''
            if node.node_type == 'workflow':
                style = 'style=filled, fillcolor=lightblue'
            elif node.node_type == 'agent':
                style = 'style=filled, fillcolor=lightgreen'
            elif node.node_type == 'state':
                style = 'style=filled, fillcolor=lightyellow'

            label = node_name.split('.')[-1]  # Use short name
            lines.append(f'  "{node_name}" [label="{label}", {style}];')

        lines.append('')

        # Add edges
        for from_node, to_node in graph.edges:
            lines.append(f'  "{from_node}" -> "{to_node}";')

        # Highlight cycles
        if graph.cycles:
            lines.append('')
            lines.append('  // Cycles (highlighted in red)')
            for cycle in graph.cycles:
                if cycle.severity == 'critical':
                    for i in range(len(cycle.cycle_path) - 1):
                        from_n = cycle.cycle_path[i]
                        to_n = cycle.cycle_path[i + 1]
                        lines.append(
                            f'  "{from_n}" -> "{to_n}" [color=red, penwidth=2];'
                        )

        lines.append('}')
        return '\n'.join(lines)

    def generate_mermaid_diagram(self, graph: DependencyGraph) -> str:
        """
        Generate Mermaid diagram format for visualization.

        Returns:
            Mermaid format string for rendering the dependency graph
        """
        lines = ['graph TD']

        # Add nodes and edges
        for from_node, to_node in graph.edges:
            from_label = from_node.split('.')[-1]
            to_label = to_node.split('.')[-1]

            # Sanitize labels for Mermaid
            from_id = from_node.replace('.', '_').replace(' ', '_')
            to_id = to_node.replace('.', '_').replace(' ', '_')

            lines.append(f'  {from_id}[{from_label}] --> {to_id}[{to_label}]')

        # Highlight cycles
        if graph.cycles:
            lines.append('')
            lines.append('  %% Cycles')
            for cycle in graph.cycles:
                if cycle.severity == 'critical':
                    for i in range(len(cycle.cycle_path) - 1):
                        from_n = cycle.cycle_path[i].replace('.', '_').replace(' ', '_')
                        to_n = cycle.cycle_path[i + 1].replace('.', '_').replace(' ', '_')
                        lines.append(f'  {from_n} -.->|cycle| {to_n}')

        # Add styling
        lines.append('')
        lines.append('  classDef workflow fill:#bbdefb')
        lines.append('  classDef agent fill:#c8e6c9')
        lines.append('  classDef state fill:#fff9c4')

        return '\n'.join(lines)

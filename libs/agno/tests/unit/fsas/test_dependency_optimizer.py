"""
Comprehensive tests for Dependency Optimizer FSA

Tests cover graph building, topological sorting, cycle detection, conflict resolution,
redundancy elimination, parallel execution planning, and dependency validation.
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

from agno.fsas.dependency_optimizer import (
    CircularDependencyError,
    Conflict,
    ConflictType,
    Cycle,
    DependencyGraph,
    DependencyNode,
    DependencyOptimizerError,
    DependencyOptimizerFSA,
    DependencyType,
    ExecutionPlan,
    OptimizedGraph,
    Resolution,
    ResolutionStrategy,
    ValidationResult,
)


@pytest.fixture
def optimizer():
    """Create Dependency Optimizer FSA instance"""
    return DependencyOptimizerFSA()


@pytest.fixture
def simple_fsas():
    """Simple FSA specifications without circular dependencies"""
    return [
        {'id': 'A', 'name': 'FSA_A', 'dependencies': []},
        {'id': 'B', 'name': 'FSA_B', 'dependencies': ['A']},
        {'id': 'C', 'name': 'FSA_C', 'dependencies': ['A']},
        {'id': 'D', 'name': 'FSA_D', 'dependencies': ['B', 'C']},
    ]


@pytest.fixture
def complex_fsas():
    """Complex FSA specifications with multiple levels"""
    return [
        {'id': 'A', 'name': 'FSA_A', 'dependencies': []},
        {'id': 'B', 'name': 'FSA_B', 'dependencies': ['A']},
        {'id': 'C', 'name': 'FSA_C', 'dependencies': ['A']},
        {'id': 'D', 'name': 'FSA_D', 'dependencies': ['B']},
        {'id': 'E', 'name': 'FSA_E', 'dependencies': ['C']},
        {'id': 'F', 'name': 'FSA_F', 'dependencies': ['D', 'E']},
    ]


@pytest.fixture
def circular_fsas():
    """FSA specifications with circular dependencies"""
    return [
        {'id': 'A', 'name': 'FSA_A', 'dependencies': ['B']},
        {'id': 'B', 'name': 'FSA_B', 'dependencies': ['C']},
        {'id': 'C', 'name': 'FSA_C', 'dependencies': ['A']},
    ]


@pytest.fixture
def sample_graph():
    """Create a sample dependency graph"""
    graph = DependencyGraph()

    # Create nodes
    for fsa_id in ['A', 'B', 'C', 'D']:
        node = DependencyNode(fsa_id=fsa_id, fsa_name=f'FSA_{fsa_id}')
        graph.add_node(node)

    # Add edges: D depends on B and C, B and C depend on A
    graph.add_edge('B', 'A')
    graph.add_edge('C', 'A')
    graph.add_edge('D', 'B')
    graph.add_edge('D', 'C')

    return graph


class TestDependencyOptimizerInitialization:
    """Test Dependency Optimizer FSA initialization"""

    def test_init_default(self):
        """Test initialization with default parameters"""
        optimizer = DependencyOptimizerFSA()
        assert optimizer is not None
        assert optimizer.name == "DependencyOptimizerFSA"
        assert optimizer.enable_parallel_execution is True
        assert optimizer.max_parallel_fsas == 4

    def test_init_with_config(self):
        """Test initialization with custom configuration"""
        config = {
            "enable_parallel_execution": False,
            "max_parallel_fsas": 8,
            "allow_circular_deps": True,
            "cache_resolved_deps": False
        }
        optimizer = DependencyOptimizerFSA(config=config)
        assert optimizer.enable_parallel_execution is False
        assert optimizer.max_parallel_fsas == 8
        assert optimizer.allow_circular_deps is True
        assert optimizer.cache_resolved_deps is False


class TestDependencyGraphBuilding:
    """Test dependency graph construction"""

    def test_analyze_dependencies_simple(self, optimizer, simple_fsas):
        """Test building graph from simple FSA specifications"""
        graph = optimizer.analyze_dependencies(simple_fsas)

        assert isinstance(graph, DependencyGraph)
        assert len(graph.nodes) == 4
        assert 'A' in graph.nodes
        assert 'B' in graph.nodes
        assert 'C' in graph.nodes
        assert 'D' in graph.nodes

    def test_analyze_dependencies_edges(self, optimizer, simple_fsas):
        """Test that edges are created correctly"""
        graph = optimizer.analyze_dependencies(simple_fsas)

        # Check edges
        assert ('B', 'A') in graph.edges
        assert ('C', 'A') in graph.edges
        assert ('D', 'B') in graph.edges
        assert ('D', 'C') in graph.edges

    def test_analyze_dependencies_with_types(self, optimizer):
        """Test dependency type handling"""
        fsas = [
            {'id': 'A', 'name': 'FSA_A', 'dependencies': []},
            {
                'id': 'B',
                'name': 'FSA_B',
                'dependencies': [
                    {'id': 'A', 'type': 'required'},
                    {'id': 'C', 'type': 'optional'}
                ]
            },
            {'id': 'C', 'name': 'FSA_C', 'dependencies': []},
        ]

        graph = optimizer.analyze_dependencies(fsas)

        node_b = graph.get_node('B')
        assert node_b is not None
        assert 'A' in node_b.dependency_types
        assert node_b.dependency_types['A'] == DependencyType.REQUIRED

    def test_analyze_dependencies_depth_calculation(self, optimizer, complex_fsas):
        """Test that depths are calculated correctly"""
        graph = optimizer.analyze_dependencies(complex_fsas)

        # Check depths
        assert graph.nodes['A'].depth == 0  # No dependencies
        assert graph.nodes['B'].depth == 1  # Depends on A
        assert graph.nodes['C'].depth == 1  # Depends on A
        assert graph.nodes['D'].depth == 2  # Depends on B
        assert graph.nodes['E'].depth == 2  # Depends on C
        assert graph.nodes['F'].depth == 3  # Depends on D and E


class TestTopologicalSort:
    """Test topological sorting for execution order"""

    def test_optimize_execution_order_simple(self, optimizer, simple_fsas):
        """Test execution order optimization"""
        graph = optimizer.analyze_dependencies(simple_fsas)
        order = optimizer.optimize_execution_order(graph)

        assert isinstance(order, list)
        assert len(order) == 4

        # A should come before B, C, D
        assert order.index('A') < order.index('B')
        assert order.index('A') < order.index('C')
        assert order.index('A') < order.index('D')

        # B and C should come before D
        assert order.index('B') < order.index('D')
        assert order.index('C') < order.index('D')

    def test_optimize_execution_order_complex(self, optimizer, complex_fsas):
        """Test execution order for complex dependencies"""
        graph = optimizer.analyze_dependencies(complex_fsas)
        order = optimizer.optimize_execution_order(graph)

        # Verify all FSAs are included
        assert len(order) == 6
        assert set(order) == {'A', 'B', 'C', 'D', 'E', 'F'}

        # Verify dependency ordering
        assert order.index('A') < order.index('B')
        assert order.index('A') < order.index('C')
        assert order.index('B') < order.index('D')
        assert order.index('C') < order.index('E')
        assert order.index('D') < order.index('F')
        assert order.index('E') < order.index('F')

    def test_execution_order_updates_nodes(self, optimizer, simple_fsas):
        """Test that execution order is stored in nodes"""
        graph = optimizer.analyze_dependencies(simple_fsas)
        order = optimizer.optimize_execution_order(graph)

        for idx, fsa_id in enumerate(order):
            node = graph.get_node(fsa_id)
            assert node is not None
            assert node.execution_order == idx


class TestCircularDependencyDetection:
    """Test circular dependency detection"""

    def test_detect_no_cycles(self, optimizer, simple_fsas):
        """Test that no cycles are detected in acyclic graph"""
        graph = optimizer.analyze_dependencies(simple_fsas)
        cycles = optimizer.detect_circular_dependencies(graph)

        assert isinstance(cycles, list)
        assert len(cycles) == 0

    def test_detect_simple_cycle(self, optimizer, circular_fsas):
        """Test detection of simple circular dependency"""
        graph = optimizer.analyze_dependencies(circular_fsas)
        cycles = optimizer.detect_circular_dependencies(graph)

        assert len(cycles) > 0
        cycle = cycles[0]
        assert isinstance(cycle, Cycle)
        assert len(cycle.fsas_in_cycle) > 0

        # All FSAs should be in the cycle
        assert set(cycle.fsas_in_cycle[:-1]) == {'A', 'B', 'C'}

    def test_cycle_break_point_suggestions(self, optimizer, circular_fsas):
        """Test that break points are suggested for cycles"""
        graph = optimizer.analyze_dependencies(circular_fsas)
        cycles = optimizer.detect_circular_dependencies(graph)

        assert len(cycles) > 0
        cycle = cycles[0]
        assert len(cycle.break_point_suggestions) > 0

    def test_circular_dependency_error(self, optimizer, circular_fsas):
        """Test that circular dependencies raise error when not allowed"""
        graph = optimizer.analyze_dependencies(circular_fsas)

        with pytest.raises(CircularDependencyError):
            optimizer.optimize_execution_order(graph)

    def test_circular_dependency_allowed(self, circular_fsas):
        """Test that circular dependencies can be allowed"""
        optimizer = DependencyOptimizerFSA(config={'allow_circular_deps': True})
        graph = optimizer.analyze_dependencies(circular_fsas)

        # Should not raise error
        order = optimizer.optimize_execution_order(graph)
        assert isinstance(order, list)


class TestConflictResolution:
    """Test dependency conflict resolution"""

    def test_resolve_conflicts_basic(self, optimizer):
        """Test basic conflict resolution"""
        conflicts = [
            Conflict(
                fsa1='A',
                fsa2='B',
                conflict_type=ConflictType.VERSION,
                priority=1
            )
        ]

        resolution = optimizer.resolve_conflicts(conflicts)

        assert isinstance(resolution, Resolution)
        assert len(resolution.modifications) > 0

    def test_resolve_conflicts_with_strategy(self, optimizer):
        """Test conflict resolution with specific strategy"""
        conflicts = [
            Conflict(
                fsa1='A',
                fsa2='B',
                conflict_type=ConflictType.VERSION,
                priority=1,
                resolution_strategy=ResolutionStrategy.UPGRADE
            )
        ]

        resolution = optimizer.resolve_conflicts(conflicts)

        assert any('Upgrade' in mod for mod in resolution.modifications)

    def test_resolve_conflicts_priority_order(self, optimizer):
        """Test that conflicts are resolved by priority"""
        conflicts = [
            Conflict(
                fsa1='A',
                fsa2='B',
                conflict_type=ConflictType.VERSION,
                priority=1
            ),
            Conflict(
                fsa1='C',
                fsa2='D',
                conflict_type=ConflictType.RESOURCE,
                priority=10
            )
        ]

        resolution = optimizer.resolve_conflicts(conflicts)

        # Higher priority conflict should be resolved first
        assert len(resolution.modifications) >= 2

    def test_suggest_resolution_strategy(self, optimizer):
        """Test automatic strategy suggestion"""
        # Version conflict -> Upgrade
        conflict = Conflict(
            fsa1='A',
            fsa2='B',
            conflict_type=ConflictType.VERSION
        )
        strategy = optimizer._suggest_resolution_strategy(conflict)
        assert strategy == ResolutionStrategy.UPGRADE

        # Resource conflict -> Queue
        conflict = Conflict(
            fsa1='A',
            fsa2='B',
            conflict_type=ConflictType.RESOURCE
        )
        strategy = optimizer._suggest_resolution_strategy(conflict)
        assert strategy == ResolutionStrategy.QUEUE


class TestRedundancyElimination:
    """Test redundancy elimination"""

    def test_eliminate_redundancy_simple(self, optimizer, sample_graph):
        """Test redundancy elimination on simple graph"""
        result = optimizer.eliminate_redundancy(sample_graph)

        assert isinstance(result, OptimizedGraph)
        assert result.optimized_graph is not None

    def test_eliminate_transitive_dependencies(self, optimizer):
        """Test elimination of transitive dependencies"""
        # Create graph with transitive dependency
        # A -> B -> C and A -> C (redundant)
        graph = DependencyGraph()
        for fsa_id in ['A', 'B', 'C']:
            node = DependencyNode(fsa_id=fsa_id, fsa_name=f'FSA_{fsa_id}')
            graph.add_node(node)

        graph.add_edge('A', 'B')
        graph.add_edge('B', 'C')
        graph.add_edge('A', 'C')  # Transitive - should be eliminated

        result = optimizer.eliminate_redundancy(graph)

        # Original has 3 edges
        assert len(graph.edges) == 3

        # Optimized should have 2 edges (A->C removed)
        assert len(result.optimized_graph.edges) == 2
        assert result.redundancies_eliminated == 1

    def test_redundancy_elimination_performance_gain(self, optimizer, sample_graph):
        """Test that performance gain is calculated"""
        result = optimizer.eliminate_redundancy(sample_graph)

        assert result.performance_gain >= 0
        assert isinstance(result.optimizations_applied, list)


class TestParallelExecutionPlanning:
    """Test parallel execution planning"""

    def test_plan_parallel_execution_simple(self, optimizer, simple_fsas):
        """Test parallel execution planning"""
        graph = optimizer.analyze_dependencies(simple_fsas)
        plan = optimizer.plan_parallel_execution(graph)

        assert isinstance(plan, ExecutionPlan)
        assert len(plan.sequential_stages) > 0

    def test_parallel_groups_identification(self, optimizer, simple_fsas):
        """Test that parallel groups are identified"""
        graph = optimizer.analyze_dependencies(simple_fsas)
        plan = optimizer.plan_parallel_execution(graph)

        # B and C can run in parallel (both depend only on A)
        assert len(plan.parallel_groups) > 0

    def test_plan_respects_dependencies(self, optimizer, complex_fsas):
        """Test that parallel plan respects dependencies"""
        graph = optimizer.analyze_dependencies(complex_fsas)
        plan = optimizer.plan_parallel_execution(graph)

        # Verify stages respect dependencies
        executed = set()
        for stage in plan.sequential_stages:
            for fsa_id in stage:
                node = graph.get_node(fsa_id)
                if node:
                    # All dependencies should have been executed
                    for dep_id in node.dependencies:
                        assert dep_id in executed
            executed.update(stage)

    def test_parallel_execution_disabled(self, simple_fsas):
        """Test behavior when parallel execution is disabled"""
        optimizer = DependencyOptimizerFSA(config={'enable_parallel_execution': False})
        graph = optimizer.analyze_dependencies(simple_fsas)
        plan = optimizer.plan_parallel_execution(graph)

        # Should still create stages, but no parallel groups
        assert len(plan.sequential_stages) > 0

    def test_max_parallel_fsas_limit(self, optimizer):
        """Test that parallel FSAs are limited"""
        # Create many FSAs that can run in parallel
        fsas = [
            {'id': 'ROOT', 'name': 'ROOT', 'dependencies': []}
        ]
        for i in range(10):
            fsas.append({
                'id': f'FSA_{i}',
                'name': f'FSA_{i}',
                'dependencies': ['ROOT']
            })

        graph = optimizer.analyze_dependencies(fsas)
        plan = optimizer.plan_parallel_execution(graph)

        # Check that no parallel group exceeds max_parallel_fsas
        for group in plan.parallel_groups:
            assert len(group) <= optimizer.max_parallel_fsas


class TestDependencyValidation:
    """Test dependency validation"""

    def test_validate_dependencies_all_available(self, optimizer):
        """Test validation when all dependencies are available"""
        fsa = {
            'id': 'A',
            'name': 'FSA_A',
            'dependencies': ['B', 'C']
        }
        available_fsas = ['B', 'C', 'D']

        result = optimizer.validate_dependencies(fsa, available_fsas)

        assert isinstance(result, ValidationResult)
        assert result.is_valid is True
        assert len(result.missing_dependencies) == 0

    def test_validate_dependencies_missing_required(self, optimizer):
        """Test validation with missing required dependencies"""
        fsa = {
            'id': 'A',
            'name': 'FSA_A',
            'dependencies': [
                {'id': 'B', 'type': 'required'},
                {'id': 'C', 'type': 'required'}
            ]
        }
        available_fsas = ['B']  # C is missing

        result = optimizer.validate_dependencies(fsa, available_fsas)

        assert result.is_valid is False
        assert 'C' in result.missing_dependencies
        assert len(result.errors) > 0

    def test_validate_dependencies_missing_optional(self, optimizer):
        """Test validation with missing optional dependencies"""
        fsa = {
            'id': 'A',
            'name': 'FSA_A',
            'dependencies': [
                {'id': 'B', 'type': 'required'},
                {'id': 'C', 'type': 'optional'}
            ]
        }
        available_fsas = ['B']  # C is missing but optional

        result = optimizer.validate_dependencies(fsa, available_fsas)

        assert result.is_valid is True
        assert len(result.errors) == 0
        assert len(result.warnings) > 0  # Should have warning about optional dep


class TestDependencyInjection:
    """Test dependency injection"""

    def test_inject_dependencies(self, optimizer):
        """Test injecting dependencies into FSA"""
        fsa = {'id': 'A', 'name': 'FSA_A'}
        deps = {'dep1': 'value1', 'dep2': 'value2'}

        result = optimizer.inject_dependencies(fsa, deps)

        assert 'injected_dependencies' in result
        assert result['injected_dependencies'] == deps

    def test_inject_dependencies_caching(self, optimizer):
        """Test that dependencies are cached when enabled"""
        optimizer.cache_resolved_deps = True
        fsa = {'id': 'A', 'name': 'FSA_A'}
        deps = {'dep1': 'value1'}

        optimizer.inject_dependencies(fsa, deps)

        # Check cache
        assert 'A' in optimizer._dependency_cache
        assert optimizer._dependency_cache['A'] == deps


class TestRuntimeDependencyResolution:
    """Test runtime dependency resolution"""

    def test_resolve_runtime_dependencies(self, optimizer):
        """Test resolving dependencies at runtime"""
        fsa = {
            'id': 'A',
            'name': 'FSA_A',
            'dependencies': ['B', 'C']
        }
        context = {
            'B': 'value_b',
            'C': 'value_c'
        }

        resolved = optimizer.resolve_runtime_dependencies(fsa, context)

        assert 'B' in resolved
        assert 'C' in resolved
        assert resolved['B'] == 'value_b'

    def test_resolve_conditional_dependencies(self, optimizer):
        """Test resolving conditional dependencies"""
        fsa = {
            'id': 'A',
            'name': 'FSA_A',
            'dependencies': [
                {'id': 'B', 'type': 'required'},
                {'id': 'C', 'type': 'conditional', 'condition': 'feature_flag'}
            ]
        }
        context = {
            'B': 'value_b',
            'C': 'value_c',
            'feature_flag': True
        }

        resolved = optimizer.resolve_runtime_dependencies(fsa, context)

        assert 'B' in resolved
        assert 'C' in resolved

    def test_resolve_runtime_dependencies_caching(self, optimizer):
        """Test that runtime resolution uses cache"""
        optimizer.cache_resolved_deps = True
        fsa = {'id': 'A', 'name': 'FSA_A', 'dependencies': ['B']}
        context = {'B': 'value_b'}

        # First resolution
        resolved1 = optimizer.resolve_runtime_dependencies(fsa, context)

        # Second resolution should use cache
        resolved2 = optimizer.resolve_runtime_dependencies(fsa, context)

        assert resolved1 == resolved2


class TestCascadeOptimization:
    """Test end-to-end cascade optimization"""

    def test_optimize_cascade_pipeline(self, optimizer, complex_fsas):
        """Test complete cascade optimization"""
        cascade = {'fsas': complex_fsas}

        optimized = optimizer.optimize_cascade_pipeline(cascade)

        assert 'execution_plan' in optimized
        assert 'optimization_applied' in optimized
        assert 'performance_gain' in optimized

    def test_cascade_optimization_includes_plan(self, optimizer, simple_fsas):
        """Test that optimized cascade includes execution plan"""
        cascade = {'fsas': simple_fsas}

        optimized = optimizer.optimize_cascade_pipeline(cascade)

        plan = optimized['execution_plan']
        assert 'sequential_stages' in plan
        assert 'parallel_groups' in plan


class TestVisualizationExport:
    """Test dependency visualization export"""

    def test_export_dependency_viz(self, optimizer, sample_graph, tmp_path):
        """Test exporting dependency visualization"""
        output_path = tmp_path / "deps.dot"

        success = optimizer.export_dependency_viz(sample_graph, str(output_path))

        assert success is True
        assert output_path.exists()

        content = output_path.read_text()
        assert 'digraph Dependencies' in content
        assert 'FSA_A' in content

    def test_export_viz_with_dependency_types(self, optimizer, tmp_path):
        """Test that different dependency types are shown"""
        graph = DependencyGraph()

        node_a = DependencyNode(fsa_id='A', fsa_name='FSA_A')
        node_b = DependencyNode(fsa_id='B', fsa_name='FSA_B')
        graph.add_node(node_a)
        graph.add_node(node_b)

        graph.add_edge('B', 'A', DependencyType.OPTIONAL)

        output_path = tmp_path / "deps.dot"
        success = optimizer.export_dependency_viz(graph, str(output_path))

        assert success is True

        content = output_path.read_text()
        assert 'dashed' in content  # Optional dependencies shown as dashed


class TestDepthComputation:
    """Test dependency depth computation"""

    def test_compute_dependency_depth(self, optimizer, sample_graph):
        """Test computing dependency depths"""
        depths = optimizer.compute_dependency_depth(sample_graph)

        assert isinstance(depths, dict)
        assert len(depths) == len(sample_graph.nodes)

        # Check specific depths
        assert depths['A'] == 0
        assert depths['B'] == 1
        assert depths['C'] == 1
        assert depths['D'] == 2

    def test_depth_updates_graph_nodes(self, optimizer, sample_graph):
        """Test that depths are updated in graph nodes"""
        optimizer.compute_dependency_depth(sample_graph)

        for fsa_id, node in sample_graph.nodes.items():
            assert node.depth >= 0


class TestGraphOperations:
    """Test graph data structure operations"""

    def test_add_node(self):
        """Test adding nodes to graph"""
        graph = DependencyGraph()
        node = DependencyNode(fsa_id='A', fsa_name='FSA_A')

        graph.add_node(node)

        assert 'A' in graph.nodes
        assert graph.get_node('A') == node

    def test_add_edge(self):
        """Test adding edges to graph"""
        graph = DependencyGraph()

        node_a = DependencyNode(fsa_id='A', fsa_name='FSA_A')
        node_b = DependencyNode(fsa_id='B', fsa_name='FSA_B')
        graph.add_node(node_a)
        graph.add_node(node_b)

        graph.add_edge('B', 'A')

        assert ('B', 'A') in graph.edges
        assert 'A' in graph.nodes['B'].dependencies
        assert 'B' in graph.nodes['A'].dependents

    def test_graph_to_dict(self, sample_graph):
        """Test converting graph to dictionary"""
        graph_dict = sample_graph.to_dict()

        assert 'nodes' in graph_dict
        assert 'edges' in graph_dict
        assert 'metadata' in graph_dict
        assert len(graph_dict['nodes']) == 4


class TestErrorHandling:
    """Test error handling"""

    def test_validate_input_none(self, optimizer):
        """Test that None input raises error"""
        with pytest.raises(DependencyOptimizerError, match="cannot be None"):
            optimizer.validate_input(None)

    def test_execute_invalid_task(self, optimizer):
        """Test handling of invalid task"""
        with pytest.raises(DependencyOptimizerError, match="cannot be empty"):
            optimizer.execute("")

    def test_cleanup(self, optimizer):
        """Test cleanup clears cache"""
        optimizer._dependency_cache['A'] = {'dep': 'value'}

        optimizer.cleanup()

        assert len(optimizer._dependency_cache) == 0
        assert optimizer.state == {}

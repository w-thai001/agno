"""
Dependency Optimizer FSA - Example Usage

This module demonstrates various ways to use the Dependency Optimizer FSA
for analyzing dependencies, optimizing execution order, and orchestrating
complex FSA cascades.
"""

from agno.fsas.dependency_optimizer import (
    Conflict,
    ConflictType,
    DependencyOptimizerFSA,
    DependencyType,
    ResolutionStrategy,
)


def example_simple_dependency_analysis():
    """Example 1: Simple dependency analysis"""
    print("\n" + "="*60)
    print("Example 1: Simple Dependency Analysis")
    print("="*60)

    optimizer = DependencyOptimizerFSA()

    # Define FSAs with dependencies
    fsas = [
        {'id': 'DataLoader', 'name': 'DataLoader', 'dependencies': []},
        {'id': 'DataCleaner', 'name': 'DataCleaner', 'dependencies': ['DataLoader']},
        {'id': 'DataValidator', 'name': 'DataValidator', 'dependencies': ['DataLoader']},
        {'id': 'DataProcessor', 'name': 'DataProcessor', 'dependencies': ['DataCleaner', 'DataValidator']},
    ]

    # Analyze dependencies
    graph = optimizer.analyze_dependencies(fsas)

    print(f"\nDependency Graph:")
    print(f"  Nodes: {len(graph.nodes)}")
    print(f"  Edges: {len(graph.edges)}")

    for node_id, node in graph.nodes.items():
        print(f"\n  {node.fsa_name}:")
        print(f"    Dependencies: {node.dependencies}")
        print(f"    Dependents: {node.dependents}")
        print(f"    Depth: {node.depth}")

    return graph


def example_execution_order_optimization():
    """Example 2: Optimize execution order"""
    print("\n" + "="*60)
    print("Example 2: Execution Order Optimization")
    print("="*60)

    optimizer = DependencyOptimizerFSA()

    # Complex FSA cascade
    fsas = [
        {'id': 'ConfigLoader', 'name': 'ConfigLoader', 'dependencies': []},
        {'id': 'DatabaseConnector', 'name': 'DatabaseConnector', 'dependencies': ['ConfigLoader']},
        {'id': 'CacheManager', 'name': 'CacheManager', 'dependencies': ['ConfigLoader']},
        {'id': 'DataFetcher', 'name': 'DataFetcher', 'dependencies': ['DatabaseConnector']},
        {'id': 'DataTransformer', 'name': 'DataTransformer', 'dependencies': ['DataFetcher', 'CacheManager']},
        {'id': 'DataExporter', 'name': 'DataExporter', 'dependencies': ['DataTransformer']},
    ]

    # Analyze and optimize
    graph = optimizer.analyze_dependencies(fsas)
    execution_order = optimizer.optimize_execution_order(graph)

    print(f"\nOptimal Execution Order:")
    for idx, fsa_id in enumerate(execution_order, 1):
        node = graph.get_node(fsa_id)
        print(f"  {idx}. {node.fsa_name} (depth: {node.depth})")

    return execution_order


def example_circular_dependency_detection():
    """Example 3: Detect circular dependencies"""
    print("\n" + "="*60)
    print("Example 3: Circular Dependency Detection")
    print("="*60)

    optimizer = DependencyOptimizerFSA()

    # FSAs with circular dependency
    fsas = [
        {'id': 'ServiceA', 'name': 'ServiceA', 'dependencies': ['ServiceB']},
        {'id': 'ServiceB', 'name': 'ServiceB', 'dependencies': ['ServiceC']},
        {'id': 'ServiceC', 'name': 'ServiceC', 'dependencies': ['ServiceA']},
    ]

    graph = optimizer.analyze_dependencies(fsas)

    # Detect cycles
    cycles = optimizer.detect_circular_dependencies(graph)

    if cycles:
        print(f"\n⚠ Circular Dependencies Detected: {len(cycles)}")
        for i, cycle in enumerate(cycles, 1):
            print(f"\n  Cycle {i}:")
            print(f"    FSAs in cycle: {' -> '.join(cycle.fsas_in_cycle)}")
            print(f"    Severity: {cycle.severity}")
            print(f"    Suggested break points:")
            for from_id, to_id in cycle.break_point_suggestions:
                print(f"      - Break dependency: {from_id} -> {to_id}")
    else:
        print("\n✓ No circular dependencies found")

    return cycles


def example_parallel_execution_planning():
    """Example 4: Plan parallel execution"""
    print("\n" + "="*60)
    print("Example 4: Parallel Execution Planning")
    print("="*60)

    optimizer = DependencyOptimizerFSA()

    # FSAs with parallelization opportunities
    fsas = [
        {'id': 'Initialize', 'name': 'Initialize', 'dependencies': []},
        {'id': 'FetchUsers', 'name': 'FetchUsers', 'dependencies': ['Initialize']},
        {'id': 'FetchProducts', 'name': 'FetchProducts', 'dependencies': ['Initialize']},
        {'id': 'FetchOrders', 'name': 'FetchOrders', 'dependencies': ['Initialize']},
        {'id': 'ProcessUsers', 'name': 'ProcessUsers', 'dependencies': ['FetchUsers']},
        {'id': 'ProcessProducts', 'name': 'ProcessProducts', 'dependencies': ['FetchProducts']},
        {'id': 'ProcessOrders', 'name': 'ProcessOrders', 'dependencies': ['FetchOrders']},
        {'id': 'GenerateReport', 'name': 'GenerateReport',
         'dependencies': ['ProcessUsers', 'ProcessProducts', 'ProcessOrders']},
    ]

    graph = optimizer.analyze_dependencies(fsas)
    plan = optimizer.plan_parallel_execution(graph)

    print(f"\nExecution Plan:")
    print(f"  Total Stages: {len(plan.sequential_stages)}")
    print(f"  Parallel Groups: {len(plan.parallel_groups)}")

    print(f"\n  Sequential Stages:")
    for idx, stage in enumerate(plan.sequential_stages, 1):
        if len(stage) > 1:
            print(f"    Stage {idx} (PARALLEL): {', '.join(stage)}")
        else:
            print(f"    Stage {idx}: {', '.join(stage)}")

    print(f"\n  Optimization Notes:")
    for note in plan.optimization_notes:
        print(f"    - {note}")

    return plan


def example_redundancy_elimination():
    """Example 5: Eliminate redundant dependencies"""
    print("\n" + "="*60)
    print("Example 5: Redundancy Elimination")
    print("="*60)

    optimizer = DependencyOptimizerFSA()

    # FSAs with redundant transitive dependencies
    fsas = [
        {'id': 'A', 'name': 'FSA_A', 'dependencies': []},
        {'id': 'B', 'name': 'FSA_B', 'dependencies': ['A']},
        {'id': 'C', 'name': 'FSA_C', 'dependencies': ['B', 'A']},  # A is redundant (transitive)
        {'id': 'D', 'name': 'FSA_D', 'dependencies': ['C', 'B', 'A']},  # B and A are redundant
    ]

    graph = optimizer.analyze_dependencies(fsas)

    print(f"\nOriginal Graph:")
    print(f"  Total edges: {len(graph.edges)}")
    for from_id, to_id in graph.edges:
        print(f"    {from_id} -> {to_id}")

    # Eliminate redundancy
    optimized = optimizer.eliminate_redundancy(graph)

    print(f"\nOptimized Graph:")
    print(f"  Total edges: {len(optimized.optimized_graph.edges)}")
    for from_id, to_id in optimized.optimized_graph.edges:
        print(f"    {from_id} -> {to_id}")

    print(f"\nOptimization Results:")
    print(f"  Redundancies eliminated: {optimized.redundancies_eliminated}")
    print(f"  Performance gain: {optimized.performance_gain:.1f}%")

    print(f"\n  Optimizations Applied:")
    for opt in optimized.optimizations_applied:
        print(f"    - {opt}")

    return optimized


def example_conflict_resolution():
    """Example 6: Resolve dependency conflicts"""
    print("\n" + "="*60)
    print("Example 6: Dependency Conflict Resolution")
    print("="*60)

    optimizer = DependencyOptimizerFSA()

    # Define conflicts
    conflicts = [
        Conflict(
            fsa1='ModuleA_v1',
            fsa2='ModuleA_v2',
            conflict_type=ConflictType.VERSION,
            priority=10,
            details={'current': '1.0', 'required': '2.0'}
        ),
        Conflict(
            fsa1='DatabaseWriter',
            fsa2='CacheWriter',
            conflict_type=ConflictType.RESOURCE,
            priority=5,
            details={'resource': 'storage_lock'}
        ),
        Conflict(
            fsa1='DataProcessorA',
            fsa2='DataProcessorB',
            conflict_type=ConflictType.EXECUTION_ORDER,
            priority=7
        ),
    ]

    # Resolve conflicts
    resolution = optimizer.resolve_conflicts(conflicts)

    print(f"\nConflict Resolution:")
    print(f"  Conflicts resolved: {len(conflicts)}")

    print(f"\n  Resolved Order:")
    for fsa_id in resolution.resolved_order:
        print(f"    - {fsa_id}")

    print(f"\n  Modifications:")
    for mod in resolution.modifications:
        print(f"    - {mod}")

    if resolution.warnings:
        print(f"\n  Warnings:")
        for warning in resolution.warnings:
            print(f"    ⚠ {warning}")

    return resolution


def example_dependency_validation():
    """Example 7: Validate FSA dependencies"""
    print("\n" + "="*60)
    print("Example 7: Dependency Validation")
    print("="*60)

    optimizer = DependencyOptimizerFSA()

    # Define FSA with dependencies
    fsa = {
        'id': 'DataPipeline',
        'name': 'DataPipeline',
        'dependencies': [
            {'id': 'DataLoader', 'type': 'required'},
            {'id': 'DataCleaner', 'type': 'required'},
            {'id': 'DataValidator', 'type': 'optional'},
            {'id': 'DataCache', 'type': 'optional'},
        ]
    }

    # Available FSAs (DataValidator is missing)
    available_fsas = ['DataLoader', 'DataCleaner', 'DataCache']

    # Validate
    result = optimizer.validate_dependencies(fsa, available_fsas)

    print(f"\nValidation Result for {fsa['name']}:")
    print(f"  Status: {'✓ Valid' if result.is_valid else '✗ Invalid'}")

    if result.missing_dependencies:
        print(f"\n  Missing Dependencies:")
        for dep in result.missing_dependencies:
            print(f"    - {dep}")

    if result.errors:
        print(f"\n  Errors:")
        for error in result.errors:
            print(f"    ✗ {error}")

    if result.warnings:
        print(f"\n  Warnings:")
        for warning in result.warnings:
            print(f"    ⚠ {warning}")

    return result


def example_dependency_injection():
    """Example 8: Runtime dependency injection"""
    print("\n" + "="*60)
    print("Example 8: Dependency Injection")
    print("="*60)

    optimizer = DependencyOptimizerFSA()

    # FSA specification
    fsa = {
        'id': 'DataProcessor',
        'name': 'DataProcessor',
        'dependencies': ['database', 'cache', 'logger']
    }

    # Dependencies to inject
    dependencies = {
        'database': {'connection': 'postgresql://localhost/mydb'},
        'cache': {'type': 'redis', 'host': 'localhost'},
        'logger': {'level': 'INFO', 'output': 'console'}
    }

    # Inject dependencies
    fsa_with_deps = optimizer.inject_dependencies(fsa, dependencies)

    print(f"\nFSA: {fsa_with_deps['name']}")
    print(f"  Dependencies injected:")
    for dep_name, dep_config in fsa_with_deps['injected_dependencies'].items():
        print(f"    - {dep_name}: {dep_config}")

    return fsa_with_deps


def example_cascade_optimization():
    """Example 9: Complete cascade optimization"""
    print("\n" + "="*60)
    print("Example 9: Complete Cascade Optimization")
    print("="*60)

    optimizer = DependencyOptimizerFSA()

    # Define a complete data processing cascade
    cascade = {
        'name': 'DataProcessingPipeline',
        'fsas': [
            {
                'id': 'config_loader',
                'name': 'ConfigurationLoader',
                'dependencies': []
            },
            {
                'id': 'db_connector',
                'name': 'DatabaseConnector',
                'dependencies': ['config_loader']
            },
            {
                'id': 'api_client',
                'name': 'APIClient',
                'dependencies': ['config_loader']
            },
            {
                'id': 'data_fetcher',
                'name': 'DataFetcher',
                'dependencies': ['db_connector', 'api_client']
            },
            {
                'id': 'data_validator',
                'name': 'DataValidator',
                'dependencies': ['data_fetcher']
            },
            {
                'id': 'data_transformer',
                'name': 'DataTransformer',
                'dependencies': ['data_validator']
            },
            {
                'id': 'data_enricher',
                'name': 'DataEnricher',
                'dependencies': ['data_transformer', 'api_client']
            },
            {
                'id': 'cache_writer',
                'name': 'CacheWriter',
                'dependencies': ['data_enricher']
            },
            {
                'id': 'db_writer',
                'name': 'DatabaseWriter',
                'dependencies': ['data_enricher']
            },
            {
                'id': 'report_generator',
                'name': 'ReportGenerator',
                'dependencies': ['cache_writer', 'db_writer']
            },
        ]
    }

    # Optimize cascade
    optimized_cascade = optimizer.optimize_cascade_pipeline(cascade)

    print(f"\nCascade: {cascade['name']}")
    print(f"  FSAs: {len(cascade['fsas'])}")

    print(f"\n  Execution Plan:")
    plan = optimized_cascade['execution_plan']
    for idx, stage in enumerate(plan['sequential_stages'], 1):
        if len(stage) > 1:
            print(f"    Stage {idx} (Parallel): {', '.join(stage)}")
        else:
            print(f"    Stage {idx}: {', '.join(stage)}")

    print(f"\n  Optimizations Applied:")
    for opt in optimized_cascade['optimization_applied']:
        print(f"    - {opt}")

    print(f"\n  Performance Gain: {optimized_cascade['performance_gain']:.1f}%")

    return optimized_cascade


def example_visualization_export():
    """Example 10: Export dependency visualization"""
    print("\n" + "="*60)
    print("Example 10: Dependency Visualization Export")
    print("="*60)

    optimizer = DependencyOptimizerFSA()

    # Create a complex dependency graph
    fsas = [
        {'id': 'A', 'name': 'ServiceA', 'dependencies': []},
        {'id': 'B', 'name': 'ServiceB', 'dependencies': ['A']},
        {'id': 'C', 'name': 'ServiceC', 'dependencies': ['A']},
        {'id': 'D', 'name': 'ServiceD', 'dependencies': ['B']},
        {'id': 'E', 'name': 'ServiceE', 'dependencies': ['C']},
        {'id': 'F', 'name': 'ServiceF', 'dependencies': ['D', 'E']},
    ]

    graph = optimizer.analyze_dependencies(fsas)

    # Export visualization
    output_path = '/tmp/dependencies.dot'
    success = optimizer.export_dependency_viz(graph, output_path)

    if success:
        print(f"\n✓ Dependency visualization exported to: {output_path}")
        print(f"\n  To generate image, run:")
        print(f"    dot -Tpng {output_path} -o dependencies.png")
        print(f"    # or")
        print(f"    dot -Tsvg {output_path} -o dependencies.svg")
    else:
        print(f"\n✗ Failed to export visualization")

    return success


def example_complex_real_world_scenario():
    """Example 11: Complex real-world data pipeline"""
    print("\n" + "="*60)
    print("Example 11: Real-World Data Pipeline Optimization")
    print("="*60)

    optimizer = DependencyOptimizerFSA()

    # Real-world ML pipeline with complex dependencies
    fsas = [
        # Infrastructure
        {'id': 'env_setup', 'name': 'EnvironmentSetup', 'dependencies': []},
        {'id': 'config_loader', 'name': 'ConfigLoader', 'dependencies': ['env_setup']},

        # Data Sources (can run in parallel)
        {'id': 'fetch_db', 'name': 'FetchFromDatabase',
         'dependencies': ['config_loader']},
        {'id': 'fetch_api', 'name': 'FetchFromAPI',
         'dependencies': ['config_loader']},
        {'id': 'fetch_files', 'name': 'FetchFromFiles',
         'dependencies': ['config_loader']},

        # Data Processing (parallel per source)
        {'id': 'clean_db', 'name': 'CleanDatabaseData',
         'dependencies': ['fetch_db']},
        {'id': 'clean_api', 'name': 'CleanAPIData',
         'dependencies': ['fetch_api']},
        {'id': 'clean_files', 'name': 'CleanFileData',
         'dependencies': ['fetch_files']},

        # Data Integration
        {'id': 'merge_data', 'name': 'MergeAllData',
         'dependencies': ['clean_db', 'clean_api', 'clean_files']},

        # Feature Engineering
        {'id': 'feature_extraction', 'name': 'FeatureExtraction',
         'dependencies': ['merge_data']},
        {'id': 'feature_selection', 'name': 'FeatureSelection',
         'dependencies': ['feature_extraction']},

        # Model Operations
        {'id': 'model_training', 'name': 'ModelTraining',
         'dependencies': ['feature_selection']},
        {'id': 'model_validation', 'name': 'ModelValidation',
         'dependencies': ['model_training']},

        # Outputs (parallel)
        {'id': 'save_model', 'name': 'SaveModel',
         'dependencies': ['model_validation']},
        {'id': 'generate_metrics', 'name': 'GenerateMetrics',
         'dependencies': ['model_validation']},
        {'id': 'create_report', 'name': 'CreateReport',
         'dependencies': ['model_validation']},

        # Final step
        {'id': 'deploy', 'name': 'DeployModel',
         'dependencies': ['save_model', 'generate_metrics', 'create_report']},
    ]

    print(f"\nAnalyzing complex ML pipeline with {len(fsas)} FSAs...")

    # Analyze
    graph = optimizer.analyze_dependencies(fsas)

    print(f"\n  Dependency Graph:")
    print(f"    Nodes: {len(graph.nodes)}")
    print(f"    Edges: {len(graph.edges)}")
    print(f"    Max Depth: {max(n.depth for n in graph.nodes.values())}")

    # Check for cycles
    cycles = optimizer.detect_circular_dependencies(graph)
    if cycles:
        print(f"\n  ⚠ Circular dependencies detected: {len(cycles)}")
    else:
        print(f"\n  ✓ No circular dependencies")

    # Optimize execution order
    order = optimizer.optimize_execution_order(graph)

    # Plan parallel execution
    plan = optimizer.plan_parallel_execution(graph)

    print(f"\n  Execution Plan:")
    print(f"    Total stages: {len(plan.sequential_stages)}")
    print(f"    Parallel groups: {len(plan.parallel_groups)}")

    # Show detailed stages
    print(f"\n  Detailed Execution Stages:")
    for idx, stage in enumerate(plan.sequential_stages, 1):
        stage_names = [graph.get_node(fsa_id).fsa_name for fsa_id in stage]
        if len(stage) > 1:
            print(f"    Stage {idx} [PARALLEL - {len(stage)} FSAs]:")
            for name in stage_names:
                print(f"      - {name}")
        else:
            print(f"    Stage {idx}: {stage_names[0]}")

    # Eliminate redundancy
    optimized = optimizer.eliminate_redundancy(graph)

    print(f"\n  Optimization Results:")
    print(f"    Redundancies eliminated: {optimized.redundancies_eliminated}")
    print(f"    Performance gain: {optimized.performance_gain:.1f}%")

    # Export visualization
    viz_path = '/tmp/ml_pipeline_deps.dot'
    optimizer.export_dependency_viz(graph, viz_path)
    print(f"\n  Visualization exported to: {viz_path}")

    return {
        'graph': graph,
        'plan': plan,
        'optimized': optimized
    }


def run_all_examples():
    """Run all examples"""
    print("\n" + "="*80)
    print(" Dependency Optimizer FSA - Comprehensive Examples ".center(80, "="))
    print("="*80)

    examples = [
        example_simple_dependency_analysis,
        example_execution_order_optimization,
        example_circular_dependency_detection,
        example_parallel_execution_planning,
        example_redundancy_elimination,
        example_conflict_resolution,
        example_dependency_validation,
        example_dependency_injection,
        example_cascade_optimization,
        example_visualization_export,
        example_complex_real_world_scenario,
    ]

    for example in examples:
        try:
            example()
        except Exception as e:
            print(f"\n✗ Example failed: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "="*80)
    print(" Examples Complete ".center(80, "="))
    print("="*80)


if __name__ == "__main__":
    # Run all examples
    run_all_examples()

    # Or run individual examples:
    # example_simple_dependency_analysis()
    # example_execution_order_optimization()
    # example_parallel_execution_planning()
    # example_complex_real_world_scenario()

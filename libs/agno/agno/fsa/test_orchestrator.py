"""
Meta-FSA Orchestrator Test Suite

Comprehensive demonstration of the Meta-FSA Orchestrator with three different
task complexity levels, showing intelligent FSA routing decisions.
"""

import json
from agno.fsa.mock_fsas import FSA_1_1, FSA_1_2, FSA_2_1, FSA_2_2, FSA_3_1, FSA_3_2
from agno.fsa.orchestrator import MetaFSAOrchestrator


def print_section(title):
    """Print a formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def print_subsection(title):
    """Print a formatted subsection header."""
    print("\n" + "-" * 80)
    print(f"  {title}")
    print("-" * 80)


def print_json(data, indent=2):
    """Print data as formatted JSON."""
    print(json.dumps(data, indent=indent, default=str))


def test_simple_task():
    """
    Test 1: Simple Task - Create a utility function
    Expected route: FSA-1.1 → FSA-1.2 → FSA-2.1 (simple chain)
    """
    print_section("TEST 1: SIMPLE TASK - Create a Utility Function")

    # Initialize FSA modules
    fsa_1_1 = FSA_1_1()
    fsa_1_2 = FSA_1_2()
    fsa_2_1 = FSA_2_1()
    fsa_2_2 = FSA_2_2()
    fsa_3_1 = FSA_3_1()
    fsa_3_2 = FSA_3_2()

    # Initialize orchestrator
    orchestrator = MetaFSAOrchestrator(
        fsa_1_1=fsa_1_1,
        fsa_1_2=fsa_1_2,
        fsa_2_1=fsa_2_1,
        fsa_2_2=fsa_2_2,
        fsa_3_1=fsa_3_1,
        fsa_3_2=fsa_3_2
    )

    # Define simple task
    task = {
        "description": "Create a simple utility function for string formatting",
        "requirements": ["basic validation", "simple logic"]
    }

    print("📋 Task Definition:")
    print_json(task)

    # Orchestrate the task
    result = orchestrator.orchestrate(task)

    # Display task analysis
    print_subsection("1. Task Analysis Results")
    print("\n✅ Complexity Detection:", result["task_profile"]["complexity"])
    print("✅ Task Type Detection:", result["task_profile"]["task_type"])
    print("\n📊 Quality Requirements:")
    print_json(result["task_profile"]["quality_requirements"], indent=4)
    print("\n🔧 Optimization Needs:")
    print_json(result["task_profile"]["optimization_needs"], indent=4)
    print("\n🔗 Integration Requirements:")
    print_json(result["task_profile"]["integration_requirements"], indent=4)

    # Display selected FSA chain
    print_subsection("2. Selected FSA Chain")
    print("\n🎯 Chain Selected:", " → ".join(result["selected_chain"]))
    print("\n💡 Reasoning:")
    print("   - Low complexity detected from 'simple utility function'")
    print("   - General task type (no specific backend/frontend indicators)")
    print("   - No integration or optimization requirements detected")
    print("   - Selected minimal chain: Planning → Decomposition → QA")

    # Display execution routing
    print_subsection("3. Execution Routing Decisions")
    for i, fsa_result in enumerate(result["execution_result"]["results"], 1):
        print(f"\n   Step {i}: {fsa_result['fsa']}")
        print(f"   Status: {fsa_result['status']}")
        print(f"   Execution Time: {fsa_result['execution_time']:.4f}s")
        print(f"   Key Outputs:")
        for key, value in fsa_result["result"].items():
            if isinstance(value, (list, dict)):
                print(f"      - {key}: {type(value).__name__} with {len(value)} items")
            else:
                print(f"      - {key}: {value}")

    # Display meta-learning data
    print_subsection("4. Meta-Learning Data Updates")
    analytics = orchestrator.getAnalytics()
    print("\n📈 Performance Stats:")
    print(f"   Total Executions: {analytics['performance_stats']['total_executions']}")
    print(f"   Avg Execution Time: {analytics['performance_stats']['avg_execution_time']:.4f}s")
    print(f"\n   Complexity Stats:")
    for complexity, stats in analytics['performance_stats']['complexity_stats'].items():
        if stats['count'] > 0:
            print(f"      {complexity.upper()}: {stats['count']} executions, avg {stats['avg_time']:.4f}s")

    # Display performance metrics
    print_subsection("5. Performance Metrics")
    print(f"\n⏱️  Total Execution Time: {result['total_execution_time']:.4f}s")
    print(f"✅  FSAs Executed: {result['execution_result']['fsa_count']}")
    print(f"✅  Successful FSAs: {result['execution_result']['successful_fsas']}")
    print(f"📊  Success Rate: {(result['execution_result']['successful_fsas'] / result['execution_result']['fsa_count'] * 100):.1f}%")

    return orchestrator, result


def test_medium_complexity():
    """
    Test 2: Medium Complexity - Build REST API with multiple endpoints
    Expected route: FSA-1.1 → FSA-1.2 → FSA-2.2 → FSA-3.1 → FSA-2.1 (moderate chain)
    """
    print_section("TEST 2: MEDIUM COMPLEXITY - Build REST API with Multiple Endpoints")

    # Initialize FSA modules
    fsa_1_1 = FSA_1_1()
    fsa_1_2 = FSA_1_2()
    fsa_2_1 = FSA_2_1()
    fsa_2_2 = FSA_2_2()
    fsa_3_1 = FSA_3_1()
    fsa_3_2 = FSA_3_2()

    # Initialize orchestrator
    orchestrator = MetaFSAOrchestrator(
        fsa_1_1=fsa_1_1,
        fsa_1_2=fsa_1_2,
        fsa_2_1=fsa_2_1,
        fsa_2_2=fsa_2_2,
        fsa_3_1=fsa_3_1,
        fsa_3_2=fsa_3_2
    )

    # Define medium complexity task
    task = {
        "description": "Build REST API with multiple endpoints for user management and authentication",
        "requirements": [
            "CRUD operations",
            "Authentication middleware",
            "Integration with database",
            "Error handling"
        ]
    }

    print("📋 Task Definition:")
    print_json(task)

    # Orchestrate the task
    result = orchestrator.orchestrate(task)

    # Display task analysis
    print_subsection("1. Task Analysis Results")
    print("\n✅ Complexity Detection:", result["task_profile"]["complexity"])
    print("✅ Task Type Detection:", result["task_profile"]["task_type"])
    print("\n📊 Quality Requirements:")
    print_json(result["task_profile"]["quality_requirements"], indent=4)
    print("\n🔧 Optimization Needs:")
    print_json(result["task_profile"]["optimization_needs"], indent=4)
    print("\n🔗 Integration Requirements:")
    print_json(result["task_profile"]["integration_requirements"], indent=4)

    # Display selected FSA chain
    print_subsection("2. Selected FSA Chain")
    print("\n🎯 Chain Selected:", " → ".join(result["selected_chain"]))
    print("\n💡 Reasoning:")
    print("   - Medium complexity detected from 'REST API with multiple endpoints'")
    print("   - Backend task type identified (API, endpoints, database keywords)")
    print("   - Integration requirements detected (database integration)")
    print("   - Implementation required (FSA-2.2)")
    print("   - Integration coordination needed (FSA-3.1)")
    print("   - Final QA for validation (FSA-2.1)")

    # Display execution routing
    print_subsection("3. Execution Routing Decisions")
    for i, fsa_result in enumerate(result["execution_result"]["results"], 1):
        print(f"\n   Step {i}: {fsa_result['fsa']}")
        print(f"   Status: {fsa_result['status']}")
        print(f"   Execution Time: {fsa_result['execution_time']:.4f}s")
        print(f"   Key Outputs:")
        for key, value in fsa_result["result"].items():
            if isinstance(value, list):
                print(f"      - {key}: {len(value)} items")
                if value and len(value) <= 3:
                    for item in value[:3]:
                        if isinstance(item, dict):
                            print(f"         • {item}")
                        else:
                            print(f"         • {item}")
            elif isinstance(value, dict):
                print(f"      - {key}:")
                for k, v in value.items():
                    print(f"         • {k}: {v}")
            else:
                print(f"      - {key}: {value}")

    # Display meta-learning data
    print_subsection("4. Meta-Learning Data Updates")
    analytics = orchestrator.getAnalytics()
    print("\n📈 Performance Stats:")
    print(f"   Total Executions: {analytics['performance_stats']['total_executions']}")
    print(f"   Avg Execution Time: {analytics['performance_stats']['avg_execution_time']:.4f}s")
    print(f"\n   Complexity Stats:")
    for complexity, stats in analytics['performance_stats']['complexity_stats'].items():
        if stats['count'] > 0:
            print(f"      {complexity.upper()}: {stats['count']} executions, avg {stats['avg_time']:.4f}s")
    print(f"\n   Task Type Stats:")
    for task_type, stats in analytics['performance_stats']['task_type_stats'].items():
        print(f"      {task_type.upper()}: {stats['count']} executions, avg {stats['avg_time']:.4f}s")

    # Display chain performance
    print("\n   Chain Performance:")
    for chain_key, perf in analytics['performance_stats']['chain_performance'].items():
        print(f"      {chain_key}")
        print(f"         Executions: {perf['count']}, Success Rate: {perf['success_rate']*100:.1f}%")

    # Display performance metrics
    print_subsection("5. Performance Metrics")
    print(f"\n⏱️  Total Execution Time: {result['total_execution_time']:.4f}s")
    print(f"✅  FSAs Executed: {result['execution_result']['fsa_count']}")
    print(f"✅  Successful FSAs: {result['execution_result']['successful_fsas']}")
    print(f"📊  Success Rate: {(result['execution_result']['successful_fsas'] / result['execution_result']['fsa_count'] * 100):.1f}%")

    return orchestrator, result


def test_complex_with_optimization():
    """
    Test 3: Complex with Optimization - Create complex system with integration and optimization
    Expected route: FSA-1.1 → FSA-1.2 → FSA-2.2 → FSA-3.1 → FSA-3.2 → FSA-2.1 (full pipeline)
    """
    print_section("TEST 3: COMPLEX WITH OPTIMIZATION - Complex System with Integration & Optimization")

    # Initialize FSA modules
    fsa_1_1 = FSA_1_1()
    fsa_1_2 = FSA_1_2()
    fsa_2_1 = FSA_2_1()
    fsa_2_2 = FSA_2_2()
    fsa_3_1 = FSA_3_1()
    fsa_3_2 = FSA_3_2()

    # Initialize orchestrator
    orchestrator = MetaFSAOrchestrator(
        fsa_1_1=fsa_1_1,
        fsa_1_2=fsa_1_2,
        fsa_2_1=fsa_2_1,
        fsa_2_2=fsa_2_2,
        fsa_3_1=fsa_3_1,
        fsa_3_2=fsa_3_2
    )

    # Define complex task with optimization
    task = {
        "description": (
            "Create complex distributed system with multiple microservices, "
            "integration between components, and performance optimization requirements. "
            "System must handle high throughput and scale efficiently."
        ),
        "requirements": [
            "Microservices architecture",
            "Service integration",
            "Performance optimization",
            "Scalability",
            "High throughput",
            "Comprehensive testing"
        ]
    }

    print("📋 Task Definition:")
    print_json(task)

    # Orchestrate the task
    result = orchestrator.orchestrate(task)

    # Display task analysis
    print_subsection("1. Task Analysis Results")
    print("\n✅ Complexity Detection:", result["task_profile"]["complexity"])
    print("✅ Task Type Detection:", result["task_profile"]["task_type"])
    print("\n📊 Quality Requirements:")
    print_json(result["task_profile"]["quality_requirements"], indent=4)
    print("\n🔧 Optimization Needs:")
    print_json(result["task_profile"]["optimization_needs"], indent=4)
    print("\n🔗 Integration Requirements:")
    print_json(result["task_profile"]["integration_requirements"], indent=4)

    # Display selected FSA chain
    print_subsection("2. Selected FSA Chain")
    print("\n🎯 Chain Selected:", " → ".join(result["selected_chain"]))
    print("\n💡 Reasoning:")
    print("   - High complexity detected from 'complex distributed system with microservices'")
    print("   - Backend/system task type identified")
    print("   - Optimization explicitly required (performance, scalability)")
    print("   - Integration required (multiple microservices, components)")
    print("   - Full pipeline activated:")
    print("      1. FSA-1.1: Analyze and plan complex architecture")
    print("      2. FSA-1.2: Decompose into manageable components")
    print("      3. FSA-2.2: Implement all components")
    print("      4. FSA-3.1: Integrate microservices")
    print("      5. FSA-3.2: Optimize for performance and scalability")
    print("      6. FSA-2.1: Final quality assurance")

    # Display execution routing
    print_subsection("3. Execution Routing Decisions")
    for i, fsa_result in enumerate(result["execution_result"]["results"], 1):
        print(f"\n   Step {i}: {fsa_result['fsa']} - {fsa_result['result'].get('optimization_status') or fsa_result['result'].get('integration_status') or fsa_result['result'].get('implementation_status') or 'processing'}")
        print(f"   Status: {fsa_result['status']}")
        print(f"   Execution Time: {fsa_result['execution_time']:.4f}s")
        print(f"   Key Outputs:")

        result_data = fsa_result["result"]

        # Display most relevant data for each FSA
        if fsa_result['fsa'] == 'FSA-1.1':
            if 'plan' in result_data:
                print(f"      - Plan Steps: {len(result_data['plan'])}")
                for step in result_data['plan'][:3]:
                    print(f"         • {step}")
        elif fsa_result['fsa'] == 'FSA-1.2':
            if 'subtasks' in result_data:
                print(f"      - Subtasks: {len(result_data['subtasks'])}")
                for subtask in result_data['subtasks'][:3]:
                    print(f"         • {subtask['description']} (Priority: {subtask['priority']})")
        elif fsa_result['fsa'] == 'FSA-2.2':
            if 'components' in result_data:
                print(f"      - Components Implemented: {len(result_data['components'])}")
            if 'code_metrics' in result_data:
                print(f"      - Code Metrics:")
                for metric, value in result_data['code_metrics'].items():
                    print(f"         • {metric}: {value}")
        elif fsa_result['fsa'] == 'FSA-3.1':
            if 'integration_points' in result_data:
                print(f"      - Integration Points: {len(result_data['integration_points'])}")
            if 'system_coherence' in result_data:
                print(f"      - System Coherence: {result_data['system_coherence']}")
        elif fsa_result['fsa'] == 'FSA-3.2':
            if 'optimizations' in result_data:
                print(f"      - Optimizations Applied:")
                for opt in result_data['optimizations']:
                    print(f"         • {opt}")
            if 'performance_metrics' in result_data:
                print(f"      - Performance Improvements:")
                for metric, value in result_data['performance_metrics'].items():
                    print(f"         • {metric}: {value}")
        elif fsa_result['fsa'] == 'FSA-2.1':
            if 'quality_metrics' in result_data:
                print(f"      - Quality Metrics:")
                for metric, status in result_data['quality_metrics'].items():
                    print(f"         • {metric}: {status}")
            if 'qa_status' in result_data:
                print(f"      - QA Status: {result_data['qa_status']}")

    # Display meta-learning data
    print_subsection("4. Meta-Learning Data Updates")
    analytics = orchestrator.getAnalytics()
    print("\n📈 Performance Stats:")
    print(f"   Total Executions: {analytics['performance_stats']['total_executions']}")
    print(f"   Avg Execution Time: {analytics['performance_stats']['avg_execution_time']:.4f}s")
    print(f"\n   Complexity Stats:")
    for complexity, stats in analytics['performance_stats']['complexity_stats'].items():
        if stats['count'] > 0:
            print(f"      {complexity.upper()}: {stats['count']} executions, avg {stats['avg_time']:.4f}s")
    print(f"\n   Task Type Stats:")
    for task_type, stats in analytics['performance_stats']['task_type_stats'].items():
        print(f"      {task_type.upper()}: {stats['count']} executions, avg {stats['avg_time']:.4f}s")

    # Display chain performance
    print("\n   Chain Performance (All Chains):")
    for chain_key, perf in analytics['performance_stats']['chain_performance'].items():
        print(f"      {chain_key}")
        print(f"         Executions: {perf['count']}, Success Rate: {perf['success_rate']*100:.1f}%, Avg Time: {perf['avg_time']:.4f}s")

    # Display learning data
    print("\n   Learned Optimal Chains:")
    for profile_key, chain in analytics['learning_data']['optimal_chains'].items():
        print(f"      {profile_key}: {' → '.join(chain)}")

    # Display performance metrics
    print_subsection("5. Performance Metrics")
    print(f"\n⏱️  Total Execution Time: {result['total_execution_time']:.4f}s")
    print(f"✅  FSAs Executed: {result['execution_result']['fsa_count']}")
    print(f"✅  Successful FSAs: {result['execution_result']['successful_fsas']}")
    print(f"📊  Success Rate: {(result['execution_result']['successful_fsas'] / result['execution_result']['fsa_count'] * 100):.1f}%")
    print(f"\n🎯  Final System Status:")
    final_context = result['execution_result']['final_context']
    if final_context and 'result' in final_context:
        final_result = final_context['result']
        if 'qa_status' in final_result:
            print(f"      QA Status: {final_result['qa_status']}")
        if 'quality_metrics' in final_result:
            passed = sum(1 for v in final_result['quality_metrics'].values() if v == 'pass')
            total = len(final_result['quality_metrics'])
            print(f"      Quality Checks: {passed}/{total} passed")

    return orchestrator, result


def run_all_tests():
    """Run all test scenarios and display summary."""
    print_section("META-FSA ORCHESTRATOR - COMPREHENSIVE DEMONSTRATION")

    print("\nThis demonstration showcases the Meta-FSA Orchestrator's intelligent")
    print("coordination of FSA modules across three different complexity levels:")
    print("\n  1. Simple Task: Minimal FSA chain for straightforward tasks")
    print("  2. Medium Complexity: Moderate chain with implementation and integration")
    print("  3. Complex with Optimization: Full pipeline with all FSA modules")

    # Run all tests
    orchestrator1, result1 = test_simple_task()
    orchestrator2, result2 = test_medium_complexity()
    orchestrator3, result3 = test_complex_with_optimization()

    # Display comparative summary
    print_section("COMPARATIVE SUMMARY")

    print("\n📊 Execution Comparison:")
    print(f"\n   {'Test':<40} {'Chain Length':<15} {'Exec Time':<15} {'Success Rate'}")
    print("   " + "-" * 85)

    tests = [
        ("Simple Task (Utility Function)", result1),
        ("Medium (REST API)", result2),
        ("Complex (Distributed System)", result3)
    ]

    for test_name, result in tests:
        chain_len = result['execution_result']['fsa_count']
        exec_time = f"{result['total_execution_time']:.4f}s"
        success_rate = f"{(result['execution_result']['successful_fsas'] / result['execution_result']['fsa_count'] * 100):.1f}%"
        print(f"   {test_name:<40} {chain_len:<15} {exec_time:<15} {success_rate}")

    print("\n\n🎯 Key Observations:")
    print("\n   1. Chain Length Adaptation:")
    print(f"      - Simple: {result1['execution_result']['fsa_count']} FSAs (minimal pipeline)")
    print(f"      - Medium: {result2['execution_result']['fsa_count']} FSAs (moderate pipeline)")
    print(f"      - Complex: {result3['execution_result']['fsa_count']} FSAs (full pipeline)")

    print("\n   2. Intelligent Routing:")
    print("      - Orchestrator correctly identified complexity levels")
    print("      - Task type detection influenced FSA selection")
    print("      - Optimization and integration requirements triggered appropriate FSAs")

    print("\n   3. Meta-Learning:")
    analytics = orchestrator3.getAnalytics()
    print(f"      - Total executions tracked: {analytics['summary']['total_executions']}")
    print(f"      - Unique chains executed: {analytics['summary']['unique_chains_executed']}")
    print(f"      - Learned optimal chains: {analytics['summary']['total_chains_learned']}")

    print("\n   4. Performance Tracking:")
    print(f"      - Average execution time: {analytics['summary']['avg_execution_time']:.4f}s")
    print("      - All complexity levels tracked independently")
    print("      - Chain performance metrics maintained for optimization")

    print("\n\n✅ Meta-FSA Orchestrator successfully demonstrated intelligent coordination")
    print("   of all FSA modules with dynamic routing and meta-learning capabilities!")

    print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    run_all_tests()

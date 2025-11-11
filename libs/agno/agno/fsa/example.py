"""
Simple Example: Meta-FSA Orchestrator Usage

This example demonstrates basic usage of the Meta-FSA Orchestrator
with a simple task.
"""

from agno.fsa.mock_fsas import FSA_1_1, FSA_1_2, FSA_2_1, FSA_2_2, FSA_3_1, FSA_3_2
from agno.fsa.orchestrator import MetaFSAOrchestrator


def main():
    """Simple example of orchestrator usage."""
    print("=" * 70)
    print("  Meta-FSA Orchestrator - Simple Example")
    print("=" * 70)

    # Step 1: Initialize all FSA modules
    print("\n1. Initializing FSA modules...")
    fsa_1_1 = FSA_1_1()
    fsa_1_2 = FSA_1_2()
    fsa_2_1 = FSA_2_1()
    fsa_2_2 = FSA_2_2()
    fsa_3_1 = FSA_3_1()
    fsa_3_2 = FSA_3_2()
    print("   ✓ All FSA modules initialized")

    # Step 2: Initialize the orchestrator
    print("\n2. Initializing Meta-FSA Orchestrator...")
    orchestrator = MetaFSAOrchestrator(
        fsa_1_1=fsa_1_1,
        fsa_1_2=fsa_1_2,
        fsa_2_1=fsa_2_1,
        fsa_2_2=fsa_2_2,
        fsa_3_1=fsa_3_1,
        fsa_3_2=fsa_3_2
    )
    print("   ✓ Orchestrator initialized with 6 FSA modules")

    # Step 3: Define a task
    print("\n3. Defining task...")
    task = {
        "description": "Build REST API with authentication and user management",
        "requirements": [
            "User CRUD operations",
            "JWT authentication",
            "Password hashing",
            "Input validation"
        ]
    }
    print(f"   Task: {task['description']}")
    print(f"   Requirements: {len(task['requirements'])} items")

    # Step 4: Orchestrate the task
    print("\n4. Orchestrating task execution...")
    result = orchestrator.orchestrate(task)

    # Step 5: Display results
    print("\n5. Results:")
    print(f"   Status: {result['status']}")
    print(f"   Detected Complexity: {result['task_profile']['complexity']}")
    print(f"   Detected Task Type: {result['task_profile']['task_type']}")
    print(f"\n   Selected FSA Chain:")
    print(f"   {' → '.join(result['selected_chain'])}")
    print(f"\n   Execution Summary:")
    print(f"   - Total FSAs Executed: {result['execution_result']['fsa_count']}")
    print(f"   - Successful FSAs: {result['execution_result']['successful_fsas']}")
    print(f"   - Total Execution Time: {result['total_execution_time']:.4f}s")
    print(f"   - Success Rate: {(result['execution_result']['successful_fsas'] / result['execution_result']['fsa_count'] * 100):.1f}%")

    # Step 6: View analytics
    print("\n6. Analytics:")
    analytics = orchestrator.getAnalytics()
    print(f"   Total Orchestrator Executions: {analytics['summary']['total_executions']}")
    print(f"   Average Execution Time: {analytics['summary']['avg_execution_time']:.4f}s")
    print(f"   Unique Chains Executed: {analytics['summary']['unique_chains_executed']}")
    print(f"   Learned Optimal Chains: {analytics['summary']['total_chains_learned']}")

    # Step 7: Try another task to see meta-learning
    print("\n7. Testing meta-learning with a second task...")
    task2 = {
        "description": "Create complex distributed system with microservices and optimization",
        "requirements": [
            "Microservices architecture",
            "Service discovery",
            "Load balancing",
            "Performance optimization"
        ]
    }
    print(f"   Task: {task2['description']}")

    result2 = orchestrator.orchestrate(task2)
    print(f"\n   Selected FSA Chain:")
    print(f"   {' → '.join(result2['selected_chain'])}")
    print(f"   Execution Time: {result2['total_execution_time']:.4f}s")

    # Updated analytics
    analytics = orchestrator.getAnalytics()
    print(f"\n   Updated Analytics:")
    print(f"   Total Executions: {analytics['summary']['total_executions']}")
    print(f"   Average Execution Time: {analytics['summary']['avg_execution_time']:.4f}s")
    print(f"   Learned Optimal Chains: {analytics['summary']['total_chains_learned']}")

    print("\n" + "=" * 70)
    print("  Example completed successfully!")
    print("=" * 70)


if __name__ == "__main__":
    main()

"""
FSA-2: Autonomous Workflow Composer

A production-ready workflow composition system that generates optimized workflows
from high-level task descriptions with DAG-based dependency management.

Features:
- Natural language task parsing
- DAG-based dependency management with cycle detection
- Automatic parallelization for independent tasks
- Multiple execution strategies (sequential, parallel, hybrid)
- Resource estimation and allocation
- Critical path analysis
- Workflow templates (ETL, ML Pipeline, Data Processing)
- Execution time estimation
- PowerShell subprocess integration for file operations
"""

import json
import subprocess
import sys
from typing import Dict, List, Tuple, Any, Optional, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
import re
from pathlib import Path
import networkx as nx
from collections import defaultdict


class ExecutionStrategy(Enum):
    """Workflow execution strategies."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    HYBRID = "hybrid"


class ResourceType(Enum):
    """Resource types for allocation."""
    CPU = "cpu"
    MEMORY = "memory"
    GPU = "gpu"
    DISK = "disk"
    NETWORK = "network"


@dataclass
class Task:
    """Represents a single workflow task."""
    id: str
    name: str
    description: str
    action: str
    dependencies: List[str] = field(default_factory=list)
    estimated_duration: float = 1.0  # in minutes
    resources: Dict[str, float] = field(default_factory=dict)
    parameters: Dict[str, Any] = field(default_factory=dict)
    priority: int = 1
    retries: int = 0
    timeout: int = 300  # seconds

    def to_dict(self) -> Dict:
        """Convert task to dictionary."""
        return asdict(self)


@dataclass
class WorkflowMetadata:
    """Metadata for workflow composition."""
    name: str
    description: str
    created_at: str
    strategy: str
    total_tasks: int
    estimated_duration: float
    critical_path_length: int
    parallelization_factor: float


class WorkflowTemplate:
    """Predefined workflow templates for common patterns."""

    @staticmethod
    def etl_pipeline() -> List[Task]:
        """Generate ETL (Extract, Transform, Load) pipeline template."""
        return [
            Task(
                id="extract",
                name="Extract Data",
                description="Extract data from source systems",
                action="extract_data",
                dependencies=[],
                estimated_duration=5.0,
                resources={"cpu": 2.0, "memory": 4.0, "network": 1.0},
                priority=1
            ),
            Task(
                id="validate",
                name="Validate Data",
                description="Validate extracted data quality",
                action="validate_data",
                dependencies=["extract"],
                estimated_duration=2.0,
                resources={"cpu": 1.0, "memory": 2.0},
                priority=2
            ),
            Task(
                id="transform",
                name="Transform Data",
                description="Apply transformations and business logic",
                action="transform_data",
                dependencies=["validate"],
                estimated_duration=10.0,
                resources={"cpu": 4.0, "memory": 8.0},
                priority=3
            ),
            Task(
                id="aggregate",
                name="Aggregate Results",
                description="Aggregate transformed data",
                action="aggregate_data",
                dependencies=["transform"],
                estimated_duration=3.0,
                resources={"cpu": 2.0, "memory": 4.0},
                priority=4
            ),
            Task(
                id="load",
                name="Load Data",
                description="Load data into target system",
                action="load_data",
                dependencies=["aggregate"],
                estimated_duration=7.0,
                resources={"cpu": 2.0, "memory": 4.0, "disk": 10.0, "network": 2.0},
                priority=5
            )
        ]

    @staticmethod
    def ml_pipeline() -> List[Task]:
        """Generate ML (Machine Learning) pipeline template."""
        return [
            Task(
                id="data_ingestion",
                name="Data Ingestion",
                description="Ingest training data",
                action="ingest_data",
                dependencies=[],
                estimated_duration=3.0,
                resources={"cpu": 1.0, "memory": 2.0, "disk": 5.0},
                priority=1
            ),
            Task(
                id="preprocessing",
                name="Data Preprocessing",
                description="Preprocess and clean data",
                action="preprocess_data",
                dependencies=["data_ingestion"],
                estimated_duration=8.0,
                resources={"cpu": 4.0, "memory": 16.0},
                priority=2
            ),
            Task(
                id="feature_engineering",
                name="Feature Engineering",
                description="Extract and engineer features",
                action="engineer_features",
                dependencies=["preprocessing"],
                estimated_duration=12.0,
                resources={"cpu": 4.0, "memory": 16.0},
                priority=3
            ),
            Task(
                id="train_model",
                name="Model Training",
                description="Train machine learning model",
                action="train_model",
                dependencies=["feature_engineering"],
                estimated_duration=30.0,
                resources={"cpu": 8.0, "memory": 32.0, "gpu": 2.0},
                priority=4
            ),
            Task(
                id="evaluate_model",
                name="Model Evaluation",
                description="Evaluate model performance",
                action="evaluate_model",
                dependencies=["train_model"],
                estimated_duration=5.0,
                resources={"cpu": 2.0, "memory": 8.0},
                priority=5
            ),
            Task(
                id="deploy_model",
                name="Model Deployment",
                description="Deploy model to production",
                action="deploy_model",
                dependencies=["evaluate_model"],
                estimated_duration=10.0,
                resources={"cpu": 2.0, "memory": 4.0, "network": 1.0},
                priority=6
            )
        ]

    @staticmethod
    def data_processing() -> List[Task]:
        """Generate parallel data processing pipeline template."""
        return [
            Task(
                id="init",
                name="Initialize Processing",
                description="Initialize data processing environment",
                action="initialize",
                dependencies=[],
                estimated_duration=1.0,
                resources={"cpu": 1.0, "memory": 2.0},
                priority=1
            ),
            Task(
                id="partition_1",
                name="Process Partition 1",
                description="Process first data partition",
                action="process_partition",
                dependencies=["init"],
                estimated_duration=15.0,
                resources={"cpu": 4.0, "memory": 8.0},
                parameters={"partition_id": 1},
                priority=2
            ),
            Task(
                id="partition_2",
                name="Process Partition 2",
                description="Process second data partition",
                action="process_partition",
                dependencies=["init"],
                estimated_duration=15.0,
                resources={"cpu": 4.0, "memory": 8.0},
                parameters={"partition_id": 2},
                priority=2
            ),
            Task(
                id="partition_3",
                name="Process Partition 3",
                description="Process third data partition",
                action="process_partition",
                dependencies=["init"],
                estimated_duration=15.0,
                resources={"cpu": 4.0, "memory": 8.0},
                parameters={"partition_id": 3},
                priority=2
            ),
            Task(
                id="merge",
                name="Merge Results",
                description="Merge processed partitions",
                action="merge_results",
                dependencies=["partition_1", "partition_2", "partition_3"],
                estimated_duration=5.0,
                resources={"cpu": 2.0, "memory": 16.0, "disk": 10.0},
                priority=3
            ),
            Task(
                id="finalize",
                name="Finalize Processing",
                description="Finalize and cleanup",
                action="finalize",
                dependencies=["merge"],
                estimated_duration=2.0,
                resources={"cpu": 1.0, "memory": 2.0},
                priority=4
            )
        ]


class WorkflowComposer:
    """
    Autonomous Workflow Composer for generating optimized workflows.

    Parses task descriptions, builds dependency graphs, optimizes execution,
    and generates executable workflow definitions.
    """

    def __init__(self):
        """Initialize the workflow composer."""
        self.tasks: Dict[str, Task] = {}
        self.graph: Optional[nx.DiGraph] = None
        self.metadata: Optional[WorkflowMetadata] = None
        self.execution_plan: Optional[Dict] = None

    def parse_task_description(self, description: str) -> Dict:
        """
        Parse natural language task descriptions into structured task definitions.

        Args:
            description: High-level task description in natural language

        Returns:
            Dictionary containing parsed tasks with dependencies

        Example:
            >>> description = '''
            ... Create a data pipeline:
            ... 1. Extract data from database (depends on: none)
            ... 2. Clean the data (depends on: extract)
            ... 3. Transform data (depends on: clean)
            ... 4. Load to warehouse (depends on: transform)
            ... '''
            >>> result = composer.parse_task_description(description)
        """
        tasks = []
        task_id_counter = 1

        # Split description into lines
        lines = [line.strip() for line in description.split('\n') if line.strip()]

        # Pattern to match task descriptions
        # Supports formats like:
        # - "1. Task name (depends on: dep1, dep2)"
        # - "Task name [depends: dep1]"
        # - "- Task name"

        task_pattern = re.compile(
            r'(?:[\d]+\.|[-*])\s*(.+?)(?:\(depends on:\s*(.*?)\)|\[depends:\s*(.*?)\])?$',
            re.IGNORECASE
        )

        for line in lines:
            match = task_pattern.match(line)
            if match:
                task_name = match.group(1).strip()
                depends_str = match.group(2) or match.group(3) or ""

                # Parse dependencies
                dependencies = []
                if depends_str and depends_str.lower() != 'none':
                    dependencies = [
                        dep.strip()
                        for dep in re.split(r'[,;]', depends_str)
                        if dep.strip()
                    ]

                # Generate task ID from name
                task_id = re.sub(r'[^a-z0-9]+', '_', task_name.lower())

                # Estimate duration based on keywords
                duration = self._estimate_duration(task_name)

                # Estimate resources based on task type
                resources = self._estimate_resources(task_name)

                task = Task(
                    id=task_id,
                    name=task_name,
                    description=task_name,
                    action=task_id,
                    dependencies=dependencies,
                    estimated_duration=duration,
                    resources=resources,
                    priority=task_id_counter
                )

                tasks.append(task)
                self.tasks[task_id] = task
                task_id_counter += 1

        return {
            "tasks": [task.to_dict() for task in tasks],
            "total_tasks": len(tasks),
            "parsed_at": datetime.now().isoformat()
        }

    def _estimate_duration(self, task_name: str) -> float:
        """Estimate task duration based on keywords in task name."""
        task_lower = task_name.lower()

        # Duration multipliers for different operation types
        if any(word in task_lower for word in ['train', 'training', 'model']):
            return 30.0
        elif any(word in task_lower for word in ['transform', 'process', 'compute']):
            return 10.0
        elif any(word in task_lower for word in ['extract', 'load', 'deploy']):
            return 5.0
        elif any(word in task_lower for word in ['validate', 'check', 'test']):
            return 2.0
        else:
            return 3.0

    def _estimate_resources(self, task_name: str) -> Dict[str, float]:
        """Estimate resource requirements based on task name."""
        task_lower = task_name.lower()
        resources = {"cpu": 1.0, "memory": 2.0}

        if any(word in task_lower for word in ['train', 'training', 'model']):
            resources = {"cpu": 8.0, "memory": 32.0, "gpu": 2.0}
        elif any(word in task_lower for word in ['transform', 'process', 'compute']):
            resources = {"cpu": 4.0, "memory": 16.0}
        elif any(word in task_lower for word in ['extract', 'load']):
            resources = {"cpu": 2.0, "memory": 4.0, "network": 1.0, "disk": 5.0}
        elif any(word in task_lower for word in ['deploy']):
            resources = {"cpu": 2.0, "memory": 4.0, "network": 2.0}

        return resources

    def build_dependency_graph(self, tasks: List[Dict]) -> nx.DiGraph:
        """
        Create a directed acyclic graph (DAG) from task definitions.

        Args:
            tasks: List of task dictionaries with dependencies

        Returns:
            NetworkX DiGraph representing task dependencies

        Raises:
            ValueError: If invalid task structure or missing dependencies
        """
        graph = nx.DiGraph()

        # First pass: Add all nodes
        task_map = {}
        for task_dict in tasks:
            if isinstance(task_dict, dict):
                task = Task(**task_dict) if 'id' in task_dict else None
                if not task:
                    continue
            else:
                task = task_dict

            task_map[task.id] = task
            graph.add_node(
                task.id,
                task=task,
                name=task.name,
                duration=task.estimated_duration,
                resources=task.resources,
                priority=task.priority
            )

        # Second pass: Add edges for dependencies
        for task_id, task in task_map.items():
            for dep_id in task.dependencies:
                # Try to find dependency by exact ID or by normalized name
                dep_found = False

                if dep_id in task_map:
                    graph.add_edge(dep_id, task_id)
                    dep_found = True
                else:
                    # Try to match by normalized name
                    normalized_dep = re.sub(r'[^a-z0-9]+', '_', dep_id.lower())
                    for tid in task_map.keys():
                        if tid == normalized_dep or task_map[tid].name.lower() == dep_id.lower():
                            graph.add_edge(tid, task_id)
                            dep_found = True
                            break

                if not dep_found:
                    raise ValueError(f"Dependency '{dep_id}' not found for task '{task_id}'")

        self.graph = graph
        return graph

    def detect_cycles(self, graph: nx.DiGraph) -> List[List[str]]:
        """
        Detect circular dependencies in the workflow graph.

        Args:
            graph: NetworkX DiGraph to check for cycles

        Returns:
            List of cycles found (each cycle is a list of task IDs)
        """
        try:
            cycles = list(nx.simple_cycles(graph))
            return cycles
        except Exception as e:
            print(f"Error detecting cycles: {e}", file=sys.stderr)
            return []

    def optimize_workflow(self, graph: nx.DiGraph) -> nx.DiGraph:
        """
        Optimize workflow execution order and resource allocation.

        Optimization strategies:
        - Identify parallel execution opportunities
        - Balance resource allocation
        - Prioritize critical path tasks
        - Minimize overall execution time

        Args:
            graph: Input workflow graph

        Returns:
            Optimized workflow graph with updated priorities
        """
        if not nx.is_directed_acyclic_graph(graph):
            cycles = self.detect_cycles(graph)
            raise ValueError(f"Graph contains cycles: {cycles}")

        # Calculate critical path
        critical_path = self._calculate_critical_path(graph)

        # Mark critical path tasks with higher priority
        for node in critical_path:
            graph.nodes[node]['critical'] = True
            graph.nodes[node]['priority'] = 10

        # Calculate parallel execution levels
        levels = self._calculate_execution_levels(graph)

        # Assign execution levels to nodes
        for level_num, level_nodes in enumerate(levels):
            for node in level_nodes:
                graph.nodes[node]['execution_level'] = level_num
                graph.nodes[node]['parallelizable'] = len(level_nodes) > 1

        # Optimize resource allocation within each level
        for level_nodes in levels:
            self._optimize_level_resources(graph, level_nodes)

        return graph

    def _calculate_critical_path(self, graph: nx.DiGraph) -> List[str]:
        """Calculate the critical path (longest path) in the workflow."""
        if len(graph.nodes) == 0:
            return []

        try:
            # Find longest path based on task durations
            longest_path = nx.dag_longest_path(
                graph,
                weight='duration',
                default_weight=1.0
            )
            return longest_path
        except Exception as e:
            print(f"Error calculating critical path: {e}", file=sys.stderr)
            return []

    def _calculate_execution_levels(self, graph: nx.DiGraph) -> List[List[str]]:
        """
        Calculate execution levels for parallel processing.
        Tasks at the same level can be executed in parallel.
        """
        if len(graph.nodes) == 0:
            return []

        # Use topological generations for level calculation
        try:
            generations = list(nx.topological_generations(graph))
            return [list(gen) for gen in generations]
        except Exception as e:
            print(f"Error calculating execution levels: {e}", file=sys.stderr)
            # Fallback to topological sort
            topo_order = list(nx.topological_sort(graph))
            return [[node] for node in topo_order]

    def _optimize_level_resources(self, graph: nx.DiGraph, level_nodes: List[str]) -> None:
        """Optimize resource allocation for tasks at the same execution level."""
        if len(level_nodes) <= 1:
            return

        # Calculate total resources needed
        total_resources = defaultdict(float)
        for node in level_nodes:
            resources = graph.nodes[node].get('resources', {})
            for resource_type, amount in resources.items():
                total_resources[resource_type] += amount

        # Store resource summary in each node
        for node in level_nodes:
            graph.nodes[node]['level_total_resources'] = dict(total_resources)

    def generate_execution_plan(
        self,
        graph: nx.DiGraph,
        strategy: str = "hybrid"
    ) -> Dict:
        """
        Generate an executable workflow plan based on the specified strategy.

        Args:
            graph: Optimized workflow graph
            strategy: Execution strategy ('sequential', 'parallel', or 'hybrid')

        Returns:
            Dictionary containing the execution plan with stages and timing
        """
        if strategy not in [s.value for s in ExecutionStrategy]:
            raise ValueError(f"Invalid strategy: {strategy}. Must be one of {[s.value for s in ExecutionStrategy]}")

        # Get execution levels
        levels = self._calculate_execution_levels(graph)

        # Calculate critical path
        critical_path = self._calculate_critical_path(graph)

        stages = []
        cumulative_time = 0.0

        if strategy == ExecutionStrategy.SEQUENTIAL.value:
            # Execute all tasks sequentially
            for node in nx.topological_sort(graph):
                task_data = graph.nodes[node]
                duration = task_data.get('duration', 1.0)

                stages.append({
                    "stage": len(stages) + 1,
                    "type": "sequential",
                    "tasks": [node],
                    "start_time": cumulative_time,
                    "duration": duration,
                    "end_time": cumulative_time + duration,
                    "critical": node in critical_path
                })

                cumulative_time += duration

        elif strategy == ExecutionStrategy.PARALLEL.value:
            # Execute all tasks at each level in parallel
            for level_num, level_nodes in enumerate(levels):
                # Find maximum duration in this level
                max_duration = max(
                    graph.nodes[node].get('duration', 1.0)
                    for node in level_nodes
                )

                stages.append({
                    "stage": level_num + 1,
                    "type": "parallel",
                    "tasks": level_nodes,
                    "start_time": cumulative_time,
                    "duration": max_duration,
                    "end_time": cumulative_time + max_duration,
                    "critical": any(node in critical_path for node in level_nodes)
                })

                cumulative_time += max_duration

        else:  # hybrid
            # Mix of parallel and sequential based on resource constraints
            for level_num, level_nodes in enumerate(levels):
                # Calculate total resources for this level
                total_cpu = sum(
                    graph.nodes[node].get('resources', {}).get('cpu', 1.0)
                    for node in level_nodes
                )

                # If resource usage is high, split into sub-stages
                if total_cpu > 16.0 and len(level_nodes) > 2:
                    # Sequential sub-stages
                    for node in level_nodes:
                        duration = graph.nodes[node].get('duration', 1.0)
                        stages.append({
                            "stage": len(stages) + 1,
                            "type": "sequential",
                            "tasks": [node],
                            "start_time": cumulative_time,
                            "duration": duration,
                            "end_time": cumulative_time + duration,
                            "critical": node in critical_path
                        })
                        cumulative_time += duration
                else:
                    # Parallel stage
                    max_duration = max(
                        graph.nodes[node].get('duration', 1.0)
                        for node in level_nodes
                    )

                    stages.append({
                        "stage": len(stages) + 1,
                        "type": "parallel",
                        "tasks": level_nodes,
                        "start_time": cumulative_time,
                        "duration": max_duration,
                        "end_time": cumulative_time + max_duration,
                        "critical": any(node in critical_path for node in level_nodes)
                    })

                    cumulative_time += max_duration

        # Calculate parallelization factor
        sequential_time = sum(
            graph.nodes[node].get('duration', 1.0)
            for node in graph.nodes
        )
        parallelization_factor = sequential_time / cumulative_time if cumulative_time > 0 else 1.0

        execution_plan = {
            "strategy": strategy,
            "total_stages": len(stages),
            "stages": stages,
            "estimated_duration": cumulative_time,
            "sequential_duration": sequential_time,
            "parallelization_factor": round(parallelization_factor, 2),
            "critical_path": critical_path,
            "critical_path_length": len(critical_path)
        }

        self.execution_plan = execution_plan
        return execution_plan

    def export_workflow(self, graph: nx.DiGraph, output_path: str) -> None:
        """
        Export workflow definition to JSON file using PowerShell subprocess.

        Args:
            output_path: Path where workflow JSON should be saved

        Raises:
            subprocess.TimeoutExpired: If PowerShell operation times out
            subprocess.CalledProcessError: If PowerShell operation fails
        """
        # Prepare workflow data
        workflow_data = {
            "metadata": {
                "name": self.metadata.name if self.metadata else "Untitled Workflow",
                "description": self.metadata.description if self.metadata else "",
                "created_at": datetime.now().isoformat(),
                "composer_version": "1.0.0",
                "strategy": self.metadata.strategy if self.metadata else "hybrid"
            },
            "tasks": {},
            "dependencies": {},
            "execution_plan": self.execution_plan or {},
            "graph_properties": {
                "total_nodes": graph.number_of_nodes(),
                "total_edges": graph.number_of_edges(),
                "is_dag": nx.is_directed_acyclic_graph(graph),
                "density": nx.density(graph)
            }
        }

        # Export task data
        for node in graph.nodes:
            task_data = graph.nodes[node]
            workflow_data["tasks"][node] = {
                "id": node,
                "name": task_data.get('name', node),
                "duration": task_data.get('duration', 1.0),
                "resources": task_data.get('resources', {}),
                "priority": task_data.get('priority', 1),
                "execution_level": task_data.get('execution_level', 0),
                "critical": task_data.get('critical', False),
                "parallelizable": task_data.get('parallelizable', False)
            }

            # Export dependencies
            predecessors = list(graph.predecessors(node))
            if predecessors:
                workflow_data["dependencies"][node] = predecessors

        # Convert to JSON
        json_content = json.dumps(workflow_data, indent=2)

        # Use PowerShell to write file
        try:
            # Escape content for PowerShell
            escaped_content = json_content.replace("'", "''").replace("`", "``")

            # PowerShell command to write file
            ps_command = f"""
            $content = @'
{json_content}
'@
            $content | Out-File -FilePath '{output_path}' -Encoding UTF8
            """

            result = subprocess.run(
                ["powershell", "-Command", ps_command],
                capture_output=True,
                text=True,
                timeout=30,
                check=True
            )

            if result.returncode == 0:
                print(f"Workflow exported successfully to: {output_path}")
            else:
                raise RuntimeError(f"PowerShell export failed: {result.stderr}")

        except subprocess.TimeoutExpired:
            raise subprocess.TimeoutExpired(
                cmd="powershell",
                timeout=30,
                output="PowerShell file write operation timed out"
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"PowerShell error during export: {e.stderr}")

    def load_template(self, template_name: str) -> List[Task]:
        """
        Load a predefined workflow template.

        Args:
            template_name: Name of the template ('etl', 'ml_pipeline', 'data_processing')

        Returns:
            List of tasks from the template
        """
        templates = {
            'etl': WorkflowTemplate.etl_pipeline,
            'ml_pipeline': WorkflowTemplate.ml_pipeline,
            'data_processing': WorkflowTemplate.data_processing
        }

        if template_name not in templates:
            raise ValueError(
                f"Unknown template: {template_name}. "
                f"Available templates: {list(templates.keys())}"
            )

        tasks = templates[template_name]()

        # Store tasks in composer
        for task in tasks:
            self.tasks[task.id] = task

        return tasks

    def analyze_workflow(self, graph: nx.DiGraph) -> Dict:
        """
        Perform comprehensive workflow analysis.

        Args:
            graph: Workflow graph to analyze

        Returns:
            Dictionary containing analysis results
        """
        analysis = {
            "graph_metrics": {
                "total_tasks": graph.number_of_nodes(),
                "total_dependencies": graph.number_of_edges(),
                "is_dag": nx.is_directed_acyclic_graph(graph),
                "density": round(nx.density(graph), 3),
                "average_degree": round(
                    sum(dict(graph.degree()).values()) / graph.number_of_nodes(), 2
                ) if graph.number_of_nodes() > 0 else 0
            },
            "execution_metrics": {},
            "resource_metrics": {},
            "parallelization_metrics": {}
        }

        if graph.number_of_nodes() == 0:
            return analysis

        # Critical path analysis
        critical_path = self._calculate_critical_path(graph)
        critical_path_duration = sum(
            graph.nodes[node].get('duration', 1.0)
            for node in critical_path
        )

        # Execution levels
        levels = self._calculate_execution_levels(graph)
        max_parallel_tasks = max(len(level) for level in levels) if levels else 0

        # Total sequential time
        total_duration = sum(
            graph.nodes[node].get('duration', 1.0)
            for node in graph.nodes
        )

        analysis["execution_metrics"] = {
            "critical_path_length": len(critical_path),
            "critical_path_duration": round(critical_path_duration, 2),
            "total_sequential_duration": round(total_duration, 2),
            "execution_levels": len(levels),
            "max_parallel_tasks": max_parallel_tasks,
            "parallelization_potential": round(
                total_duration / critical_path_duration, 2
            ) if critical_path_duration > 0 else 1.0
        }

        # Resource analysis
        total_resources = defaultdict(float)
        for node in graph.nodes:
            resources = graph.nodes[node].get('resources', {})
            for resource_type, amount in resources.items():
                total_resources[resource_type] += amount

        analysis["resource_metrics"] = {
            "total_resources": dict(total_resources),
            "average_resources_per_task": {
                resource: round(amount / graph.number_of_nodes(), 2)
                for resource, amount in total_resources.items()
            }
        }

        # Parallelization analysis
        parallelizable_tasks = sum(
            1 for node in graph.nodes
            if graph.nodes[node].get('parallelizable', False)
        )

        analysis["parallelization_metrics"] = {
            "parallelizable_tasks": parallelizable_tasks,
            "parallelizable_percentage": round(
                100 * parallelizable_tasks / graph.number_of_nodes(), 2
            ),
            "sequential_tasks": graph.number_of_nodes() - parallelizable_tasks
        }

        return analysis


def run_composer() -> Dict:
    """
    Orchestrate the complete workflow composition pipeline.

    This is the main entry point that demonstrates the full capabilities
    of the FSA-2 Autonomous Workflow Composer.

    Returns:
        Dictionary containing composition results and metrics
    """
    print("=" * 80)
    print("FSA-2: Autonomous Workflow Composer")
    print("=" * 80)
    print()

    composer = WorkflowComposer()
    results = {
        "success": False,
        "workflows": [],
        "errors": []
    }

    try:
        # Example 1: Natural Language Task Description
        print("Example 1: Natural Language Task Parsing")
        print("-" * 80)

        description = """
        Build a data processing pipeline:
        1. Extract data from API (depends on: none)
        2. Validate data quality (depends on: extract)
        3. Clean and normalize (depends on: validate)
        4. Transform data (depends on: clean)
        5. Generate reports (depends on: transform)
        6. Send notifications (depends on: generate)
        """

        parsed = composer.parse_task_description(description)
        print(f"✓ Parsed {parsed['total_tasks']} tasks from description")

        # Build dependency graph
        graph = composer.build_dependency_graph(parsed['tasks'])
        print(f"✓ Built dependency graph with {graph.number_of_nodes()} nodes")

        # Detect cycles
        cycles = composer.detect_cycles(graph)
        if cycles:
            print(f"✗ Found {len(cycles)} cycles in graph: {cycles}")
        else:
            print("✓ No cycles detected - valid DAG")

        # Optimize workflow
        optimized_graph = composer.optimize_workflow(graph)
        print("✓ Workflow optimized")

        # Generate execution plans for all strategies
        for strategy in ['sequential', 'parallel', 'hybrid']:
            plan = composer.generate_execution_plan(optimized_graph, strategy)
            print(f"✓ Generated {strategy} execution plan:")
            print(f"  - Stages: {plan['total_stages']}")
            print(f"  - Duration: {plan['estimated_duration']:.1f} min")
            print(f"  - Speedup: {plan['parallelization_factor']:.2f}x")

        # Analyze workflow
        analysis = composer.analyze_workflow(optimized_graph)
        print(f"✓ Workflow analysis completed")
        print(f"  - Parallelizable tasks: {analysis['parallelization_metrics']['parallelizable_percentage']:.1f}%")

        # Export workflow
        output_path = "/home/user/agno/workflow_example1.json"
        composer.metadata = WorkflowMetadata(
            name="Data Processing Pipeline",
            description="Natural language parsed workflow",
            created_at=datetime.now().isoformat(),
            strategy="hybrid",
            total_tasks=parsed['total_tasks'],
            estimated_duration=composer.execution_plan['estimated_duration'],
            critical_path_length=len(composer.execution_plan['critical_path']),
            parallelization_factor=composer.execution_plan['parallelization_factor']
        )
        composer.export_workflow(optimized_graph, output_path)

        results["workflows"].append({
            "name": "Natural Language Pipeline",
            "file": output_path,
            "analysis": analysis
        })

        print()

        # Example 2: ETL Template
        print("Example 2: ETL Template Workflow")
        print("-" * 80)

        composer2 = WorkflowComposer()
        etl_tasks = composer2.load_template('etl')
        print(f"✓ Loaded ETL template with {len(etl_tasks)} tasks")

        etl_graph = composer2.build_dependency_graph([task.to_dict() for task in etl_tasks])
        etl_optimized = composer2.optimize_workflow(etl_graph)
        etl_plan = composer2.generate_execution_plan(etl_optimized, 'hybrid')

        print(f"✓ ETL workflow optimized:")
        print(f"  - Duration: {etl_plan['estimated_duration']:.1f} min")
        print(f"  - Speedup: {etl_plan['parallelization_factor']:.2f}x")

        etl_output = "/home/user/agno/workflow_etl.json"
        composer2.metadata = WorkflowMetadata(
            name="ETL Pipeline",
            description="Extract, Transform, Load workflow",
            created_at=datetime.now().isoformat(),
            strategy="hybrid",
            total_tasks=len(etl_tasks),
            estimated_duration=etl_plan['estimated_duration'],
            critical_path_length=len(etl_plan['critical_path']),
            parallelization_factor=etl_plan['parallelization_factor']
        )
        composer2.export_workflow(etl_optimized, etl_output)

        results["workflows"].append({
            "name": "ETL Pipeline",
            "file": etl_output,
            "analysis": composer2.analyze_workflow(etl_optimized)
        })

        print()

        # Example 3: ML Pipeline Template
        print("Example 3: ML Pipeline Workflow")
        print("-" * 80)

        composer3 = WorkflowComposer()
        ml_tasks = composer3.load_template('ml_pipeline')
        print(f"✓ Loaded ML Pipeline template with {len(ml_tasks)} tasks")

        ml_graph = composer3.build_dependency_graph([task.to_dict() for task in ml_tasks])
        ml_optimized = composer3.optimize_workflow(ml_graph)
        ml_plan = composer3.generate_execution_plan(ml_optimized, 'sequential')

        print(f"✓ ML Pipeline workflow optimized:")
        print(f"  - Duration: {ml_plan['estimated_duration']:.1f} min")
        print(f"  - Critical path: {ml_plan['critical_path_length']} tasks")

        ml_output = "/home/user/agno/workflow_ml_pipeline.json"
        composer3.metadata = WorkflowMetadata(
            name="ML Training Pipeline",
            description="Machine Learning model training workflow",
            created_at=datetime.now().isoformat(),
            strategy="sequential",
            total_tasks=len(ml_tasks),
            estimated_duration=ml_plan['estimated_duration'],
            critical_path_length=len(ml_plan['critical_path']),
            parallelization_factor=ml_plan['parallelization_factor']
        )
        composer3.export_workflow(ml_optimized, ml_output)

        results["workflows"].append({
            "name": "ML Pipeline",
            "file": ml_output,
            "analysis": composer3.analyze_workflow(ml_optimized)
        })

        print()

        # Example 4: Data Processing with Parallelization
        print("Example 4: Parallel Data Processing Workflow")
        print("-" * 80)

        composer4 = WorkflowComposer()
        data_tasks = composer4.load_template('data_processing')
        print(f"✓ Loaded Data Processing template with {len(data_tasks)} tasks")

        data_graph = composer4.build_dependency_graph([task.to_dict() for task in data_tasks])
        data_optimized = composer4.optimize_workflow(data_graph)
        data_plan = composer4.generate_execution_plan(data_optimized, 'parallel')

        print(f"✓ Data Processing workflow optimized:")
        print(f"  - Duration: {data_plan['estimated_duration']:.1f} min")
        print(f"  - Speedup: {data_plan['parallelization_factor']:.2f}x")
        print(f"  - Parallel stages: {sum(1 for s in data_plan['stages'] if s['type'] == 'parallel')}")

        data_output = "/home/user/agno/workflow_data_processing.json"
        composer4.metadata = WorkflowMetadata(
            name="Parallel Data Processing",
            description="Highly parallelized data processing workflow",
            created_at=datetime.now().isoformat(),
            strategy="parallel",
            total_tasks=len(data_tasks),
            estimated_duration=data_plan['estimated_duration'],
            critical_path_length=len(data_plan['critical_path']),
            parallelization_factor=data_plan['parallelization_factor']
        )
        composer4.export_workflow(data_optimized, data_output)

        results["workflows"].append({
            "name": "Parallel Data Processing",
            "file": data_output,
            "analysis": composer4.analyze_workflow(data_optimized)
        })

        print()
        print("=" * 80)
        print("Summary")
        print("=" * 80)
        print(f"✓ Successfully composed {len(results['workflows'])} workflows")
        for workflow in results["workflows"]:
            print(f"\n{workflow['name']}:")
            print(f"  File: {workflow['file']}")
            print(f"  Tasks: {workflow['analysis']['graph_metrics']['total_tasks']}")
            print(f"  Dependencies: {workflow['analysis']['graph_metrics']['total_dependencies']}")
            print(f"  Parallelizable: {workflow['analysis']['parallelization_metrics']['parallelizable_percentage']:.1f}%")

        results["success"] = True

    except Exception as e:
        error_msg = f"Error in workflow composition: {str(e)}"
        print(f"\n✗ {error_msg}", file=sys.stderr)
        results["errors"].append(error_msg)
        import traceback
        traceback.print_exc()

    return results


if __name__ == "__main__":
    """Main execution entry point."""
    try:
        results = run_composer()

        if results["success"]:
            print("\n✓ FSA-2 Workflow Composer completed successfully!")
            sys.exit(0)
        else:
            print("\n✗ FSA-2 Workflow Composer encountered errors")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\n✗ Workflow composition interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n✗ Fatal error: {e}", file=sys.stderr)
        sys.exit(1)

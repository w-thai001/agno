"""
MLA Task Deconstructor and Goal Aligner

A sophisticated task analysis system using Maximum Leverage Analysis (MLA) principles
to break down complex goals into optimally prioritized, actionable subtasks.

This module implements:
- Task deconstruction into hierarchical subtasks
- Maximum Leverage Analysis for prioritization
- Goal alignment and dependency resolution
- Strategic optimization and resource allocation
- Multi-dimensional impact assessment

MLA v3.0 Principles Applied:
1. Prioritize by leverage (impact × reusability)
2. Infer missing requirements from context
3. Optimize for maximum reusability
4. Strategic enhancement and future-proofing
5. Autonomous completion with documented assumptions

Author: FSA Generation Sprint
Version: 1.0.0
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from agno.utils.log import logger


class TaskComplexity(Enum):
    """Task complexity levels."""
    TRIVIAL = 1
    SIMPLE = 2
    MODERATE = 3
    COMPLEX = 4
    VERY_COMPLEX = 5


class TaskCategory(Enum):
    """Task categories for classification."""
    RESEARCH = "research"
    PLANNING = "planning"
    IMPLEMENTATION = "implementation"
    TESTING = "testing"
    OPTIMIZATION = "optimization"
    DOCUMENTATION = "documentation"
    INTEGRATION = "integration"
    DEPLOYMENT = "deployment"


@dataclass
class ImpactMetrics:
    """
    Multi-dimensional impact assessment for tasks.

    Measures various dimensions of task impact to calculate overall leverage.
    """
    # Direct value delivered (0-10)
    direct_value: float = 5.0

    # Reusability across projects/contexts (0-10)
    reusability: float = 5.0

    # Unblocks or enables other tasks (0-10)
    enablement: float = 5.0

    # Strategic importance (0-10)
    strategic_value: float = 5.0

    # Learning/knowledge gain (0-10)
    learning_value: float = 5.0

    # Time efficiency improvement (0-10)
    time_efficiency: float = 5.0

    # Risk reduction (0-10)
    risk_reduction: float = 5.0

    def calculate_leverage_score(self, weights: Optional[Dict[str, float]] = None) -> float:
        """
        Calculate overall leverage score.

        Uses weighted combination of impact dimensions.

        Args:
            weights: Optional custom weights for each dimension

        Returns:
            Leverage score (0-100)
        """
        default_weights = {
            "direct_value": 0.20,
            "reusability": 0.20,
            "enablement": 0.15,
            "strategic_value": 0.15,
            "learning_value": 0.10,
            "time_efficiency": 0.10,
            "risk_reduction": 0.10,
        }

        weights = weights or default_weights

        score = (
            self.direct_value * weights["direct_value"] +
            self.reusability * weights["reusability"] +
            self.enablement * weights["enablement"] +
            self.strategic_value * weights["strategic_value"] +
            self.learning_value * weights["learning_value"] +
            self.time_efficiency * weights["time_efficiency"] +
            self.risk_reduction * weights["risk_reduction"]
        ) * 10  # Scale to 0-100

        return min(100.0, max(0.0, score))


@dataclass
class Task:
    """
    A task or subtask in the decomposition hierarchy.

    Represents a single actionable unit with metadata for MLA analysis.
    """
    # Unique identifier
    id: str

    # Task title/description
    title: str

    # Detailed description
    description: str = ""

    # Parent task ID (None for root tasks)
    parent_id: Optional[str] = None

    # Task category
    category: TaskCategory = TaskCategory.IMPLEMENTATION

    # Complexity level
    complexity: TaskComplexity = TaskComplexity.MODERATE

    # Estimated effort (hours)
    estimated_hours: float = 1.0

    # Impact metrics for MLA
    impact: ImpactMetrics = field(default_factory=ImpactMetrics)

    # Dependencies (task IDs that must complete first)
    dependencies: List[str] = field(default_factory=list)

    # Subtasks
    subtasks: List[Task] = field(default_factory=list)

    # Requirements
    requirements: List[str] = field(default_factory=list)

    # Acceptance criteria
    acceptance_criteria: List[str] = field(default_factory=list)

    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Calculated leverage score (computed)
    leverage_score: float = 0.0

    # Priority rank (computed during analysis)
    priority_rank: int = 0

    def calculate_leverage(self, weights: Optional[Dict[str, float]] = None) -> float:
        """Calculate and store leverage score."""
        self.leverage_score = self.impact.calculate_leverage_score(weights)
        return self.leverage_score

    def add_subtask(self, subtask: Task) -> Task:
        """Add a subtask."""
        subtask.parent_id = self.id
        self.subtasks.append(subtask)
        return self

    def add_dependency(self, task_id: str) -> Task:
        """Add a dependency."""
        if task_id not in self.dependencies:
            self.dependencies.append(task_id)
        return self

    def add_requirement(self, requirement: str) -> Task:
        """Add a requirement."""
        self.requirements.append(requirement)
        return self

    def add_acceptance_criterion(self, criterion: str) -> Task:
        """Add an acceptance criterion."""
        self.acceptance_criteria.append(criterion)
        return self

    def get_all_subtasks(self, recursive: bool = True) -> List[Task]:
        """
        Get all subtasks.

        Args:
            recursive: Include subtasks of subtasks

        Returns:
            List of subtasks
        """
        if not recursive:
            return self.subtasks

        all_subtasks = []
        for subtask in self.subtasks:
            all_subtasks.append(subtask)
            all_subtasks.extend(subtask.get_all_subtasks(recursive=True))

        return all_subtasks

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "category": self.category.value,
            "complexity": self.complexity.value,
            "estimated_hours": self.estimated_hours,
            "leverage_score": self.leverage_score,
            "priority_rank": self.priority_rank,
            "dependencies": self.dependencies,
            "requirements": self.requirements,
            "acceptance_criteria": self.acceptance_criteria,
            "subtasks": [st.to_dict() for st in self.subtasks],
        }


@dataclass
class Goal:
    """
    A high-level goal to be deconstructed.

    Represents the ultimate objective with success criteria.
    """
    # Goal title
    title: str

    # Detailed description
    description: str

    # Success criteria
    success_criteria: List[str] = field(default_factory=list)

    # Constraints
    constraints: List[str] = field(default_factory=list)

    # Context information
    context: Dict[str, Any] = field(default_factory=dict)

    # Root tasks (top-level tasks)
    tasks: List[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> Goal:
        """Add a root task."""
        self.tasks.append(task)
        return self

    def add_success_criterion(self, criterion: str) -> Goal:
        """Add a success criterion."""
        self.success_criteria.append(criterion)
        return self

    def add_constraint(self, constraint: str) -> Goal:
        """Add a constraint."""
        self.constraints.append(constraint)
        return self

    def get_all_tasks(self, recursive: bool = True) -> List[Task]:
        """
        Get all tasks.

        Args:
            recursive: Include all subtasks recursively

        Returns:
            List of all tasks
        """
        if not recursive:
            return self.tasks

        all_tasks = []
        for task in self.tasks:
            all_tasks.append(task)
            all_tasks.extend(task.get_all_subtasks(recursive=True))

        return all_tasks


class MLATaskDeconstructor:
    """
    MLA Task Deconstructor and Goal Aligner.

    Breaks down complex goals into optimally prioritized tasks using
    Maximum Leverage Analysis principles.

    Features:
    - Hierarchical task decomposition
    - Multi-dimensional impact assessment
    - Leverage-based prioritization
    - Dependency resolution
    - Strategic optimization
    - Goal alignment validation

    Example:
        ```python
        # Create goal
        goal = Goal(
            title="Build AI Agent Framework",
            description="Create a production-ready AI agent framework",
        )
        goal.add_success_criterion("Framework is modular and extensible")
        goal.add_success_criterion("Supports multiple AI models")

        # Deconstruct
        deconstructor = MLATaskDeconstructor()
        result = deconstructor.deconstruct(goal)

        # Get prioritized tasks
        prioritized = result.get_prioritized_tasks()
        for task in prioritized[:10]:
            print(f"{task.priority_rank}. {task.title} (leverage: {task.leverage_score:.1f})")
        ```
    """

    def __init__(self, leverage_weights: Optional[Dict[str, float]] = None):
        """
        Initialize deconstructor.

        Args:
            leverage_weights: Custom weights for leverage calculation
        """
        self.leverage_weights = leverage_weights

    def deconstruct(
        self,
        goal: Goal,
        auto_generate_subtasks: bool = True,
        max_depth: int = 3,
    ) -> DeconstructionResult:
        """
        Deconstruct a goal into prioritized tasks.

        Args:
            goal: Goal to deconstruct
            auto_generate_subtasks: Automatically generate subtasks for complex tasks
            max_depth: Maximum depth for subtask generation

        Returns:
            Deconstruction result with analyzed tasks
        """
        logger.info(f"Deconstructing goal: {goal.title}")

        # Step 1: Auto-generate subtasks if enabled
        if auto_generate_subtasks:
            self._auto_generate_subtasks(goal, max_depth)

        # Step 2: Calculate leverage scores
        all_tasks = goal.get_all_tasks(recursive=True)
        for task in all_tasks:
            task.calculate_leverage(self.leverage_weights)

        logger.info(f"Analyzed {len(all_tasks)} tasks")

        # Step 3: Prioritize tasks
        prioritized = self._prioritize_tasks(all_tasks)

        # Step 4: Validate dependencies
        dependency_issues = self._validate_dependencies(all_tasks)

        # Step 5: Align with goal
        alignment_score = self._calculate_goal_alignment(goal)

        # Create result
        result = DeconstructionResult(
            goal=goal,
            all_tasks=all_tasks,
            prioritized_tasks=prioritized,
            dependency_issues=dependency_issues,
            alignment_score=alignment_score,
        )

        logger.info(f"Deconstruction complete: {len(prioritized)} prioritized tasks")

        return result

    def _auto_generate_subtasks(self, goal: Goal, max_depth: int, current_depth: int = 0) -> None:
        """
        Automatically generate subtasks for complex tasks.

        Uses heuristics to break down tasks based on category and complexity.
        """
        if current_depth >= max_depth:
            return

        for task in goal.tasks:
            self._generate_subtasks_for_task(task, max_depth, current_depth)

    def _generate_subtasks_for_task(self, task: Task, max_depth: int, current_depth: int) -> None:
        """Generate subtasks for a single task."""
        # Only decompose if complex enough and no existing subtasks
        if task.complexity.value < 3 or task.subtasks:
            return

        # Generate subtasks based on category
        if task.category == TaskCategory.IMPLEMENTATION:
            subtask_templates = [
                ("Design", TaskCategory.PLANNING, TaskComplexity.MODERATE),
                ("Implement Core Logic", TaskCategory.IMPLEMENTATION, TaskComplexity.COMPLEX),
                ("Add Error Handling", TaskCategory.IMPLEMENTATION, TaskComplexity.SIMPLE),
                ("Write Tests", TaskCategory.TESTING, TaskComplexity.MODERATE),
                ("Document", TaskCategory.DOCUMENTATION, TaskComplexity.SIMPLE),
            ]
        elif task.category == TaskCategory.RESEARCH:
            subtask_templates = [
                ("Literature Review", TaskCategory.RESEARCH, TaskComplexity.MODERATE),
                ("Prototype/POC", TaskCategory.IMPLEMENTATION, TaskComplexity.SIMPLE),
                ("Analysis", TaskCategory.PLANNING, TaskComplexity.MODERATE),
                ("Documentation", TaskCategory.DOCUMENTATION, TaskComplexity.SIMPLE),
            ]
        else:
            # Generic decomposition
            subtask_templates = [
                ("Planning", TaskCategory.PLANNING, TaskComplexity.SIMPLE),
                ("Execution", task.category, TaskComplexity.MODERATE),
                ("Validation", TaskCategory.TESTING, TaskComplexity.SIMPLE),
            ]

        for idx, (title, category, complexity) in enumerate(subtask_templates):
            subtask = Task(
                id=f"{task.id}_sub{idx + 1}",
                title=f"{title} for {task.title}",
                description=f"Auto-generated subtask: {title}",
                category=category,
                complexity=complexity,
                estimated_hours=task.estimated_hours / len(subtask_templates),
            )
            task.add_subtask(subtask)

            # Recursively generate for subtasks
            if current_depth + 1 < max_depth:
                self._generate_subtasks_for_task(subtask, max_depth, current_depth + 1)

    def _prioritize_tasks(self, tasks: List[Task]) -> List[Task]:
        """
        Prioritize tasks using MLA principles.

        Sorts by leverage score and assigns priority ranks.
        """
        # Sort by leverage score (descending)
        sorted_tasks = sorted(tasks, key=lambda t: t.leverage_score, reverse=True)

        # Assign priority ranks
        for idx, task in enumerate(sorted_tasks):
            task.priority_rank = idx + 1

        return sorted_tasks

    def _validate_dependencies(self, tasks: List[Task]) -> List[str]:
        """
        Validate task dependencies.

        Returns list of dependency issues.
        """
        issues = []
        task_ids = {task.id for task in tasks}

        for task in tasks:
            for dep_id in task.dependencies:
                if dep_id not in task_ids:
                    issues.append(f"Task '{task.id}' depends on non-existent task '{dep_id}'")

        # Check for circular dependencies
        def has_cycle(task_id: str, visited: Set[str], rec_stack: Set[str]) -> bool:
            visited.add(task_id)
            rec_stack.add(task_id)

            task = next((t for t in tasks if t.id == task_id), None)
            if task:
                for dep_id in task.dependencies:
                    if dep_id not in visited:
                        if has_cycle(dep_id, visited, rec_stack):
                            return True
                    elif dep_id in rec_stack:
                        return True

            rec_stack.remove(task_id)
            return False

        visited = set()
        for task in tasks:
            if task.id not in visited:
                if has_cycle(task.id, visited, set()):
                    issues.append(f"Circular dependency detected involving task '{task.id}'")

        return issues

    def _calculate_goal_alignment(self, goal: Goal) -> float:
        """
        Calculate how well tasks align with goal.

        Returns alignment score (0-100).
        """
        # Simple heuristic: check if tasks cover key aspects
        all_tasks = goal.get_all_tasks(recursive=True)

        if not all_tasks:
            return 0.0

        # Check category coverage
        categories = {task.category for task in all_tasks}
        category_coverage = len(categories) / len(TaskCategory)

        # Check if high-leverage tasks exist
        high_leverage_count = sum(1 for t in all_tasks if t.leverage_score >= 70)
        leverage_factor = min(1.0, high_leverage_count / max(1, len(all_tasks) * 0.2))

        # Check requirements coverage
        total_requirements = sum(len(t.requirements) for t in all_tasks)
        requirements_factor = min(1.0, total_requirements / max(1, len(all_tasks)))

        # Combined score
        alignment_score = (
            category_coverage * 0.3 +
            leverage_factor * 0.4 +
            requirements_factor * 0.3
        ) * 100

        return alignment_score

    def suggest_optimizations(self, result: DeconstructionResult) -> List[str]:
        """
        Suggest optimizations for the task breakdown.

        Args:
            result: Deconstruction result

        Returns:
            List of optimization suggestions
        """
        suggestions = []

        # Check for missing high-leverage categories
        all_tasks = result.all_tasks
        categories = {task.category for task in all_tasks}

        if TaskCategory.TESTING not in categories:
            suggestions.append("Consider adding testing tasks to ensure quality")

        if TaskCategory.DOCUMENTATION not in categories:
            suggestions.append("Add documentation tasks for better maintainability")

        # Check for bottlenecks (tasks with many dependents)
        dependents_count = {}
        for task in all_tasks:
            for dep_id in task.dependencies:
                dependents_count[dep_id] = dependents_count.get(dep_id, 0) + 1

        bottlenecks = [task_id for task_id, count in dependents_count.items() if count >= 3]
        if bottlenecks:
            suggestions.append(f"Consider parallelizing or splitting bottleneck tasks: {', '.join(bottlenecks)}")

        # Check leverage distribution
        high_leverage = sum(1 for t in all_tasks if t.leverage_score >= 70)
        if high_leverage < len(all_tasks) * 0.2:
            suggestions.append("Consider enhancing task impact metrics to increase leverage")

        return suggestions


@dataclass
class DeconstructionResult:
    """
    Result of task deconstruction.

    Contains analyzed and prioritized tasks with metadata.
    """
    # Original goal
    goal: Goal

    # All tasks (flat list)
    all_tasks: List[Task]

    # Tasks sorted by priority
    prioritized_tasks: List[Task]

    # Dependency validation issues
    dependency_issues: List[str]

    # Goal alignment score (0-100)
    alignment_score: float

    def get_prioritized_tasks(self, top_n: Optional[int] = None) -> List[Task]:
        """Get top N prioritized tasks."""
        if top_n:
            return self.prioritized_tasks[:top_n]
        return self.prioritized_tasks

    def get_tasks_by_category(self, category: TaskCategory) -> List[Task]:
        """Get tasks filtered by category."""
        return [t for t in self.all_tasks if t.category == category]

    def get_high_leverage_tasks(self, threshold: float = 70.0) -> List[Task]:
        """Get tasks with leverage score above threshold."""
        return [t for t in self.all_tasks if t.leverage_score >= threshold]

    def get_ready_tasks(self) -> List[Task]:
        """Get tasks with no pending dependencies (ready to execute)."""
        completed_ids = set()  # In real usage, track completed tasks
        return [
            t for t in self.prioritized_tasks
            if all(dep_id in completed_ids for dep_id in t.dependencies)
        ]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "goal": {
                "title": self.goal.title,
                "description": self.goal.description,
                "success_criteria": self.goal.success_criteria,
            },
            "summary": {
                "total_tasks": len(self.all_tasks),
                "high_leverage_tasks": len(self.get_high_leverage_tasks()),
                "alignment_score": self.alignment_score,
                "dependency_issues_count": len(self.dependency_issues),
            },
            "prioritized_tasks": [t.to_dict() for t in self.prioritized_tasks[:20]],  # Top 20
            "dependency_issues": self.dependency_issues,
        }

    def print_summary(self) -> None:
        """Print a summary of the deconstruction."""
        print(f"\n{'=' * 60}")
        print(f"GOAL: {self.goal.title}")
        print(f"{'=' * 60}")
        print(f"\nTotal Tasks: {len(self.all_tasks)}")
        print(f"High Leverage Tasks (≥70): {len(self.get_high_leverage_tasks())}")
        print(f"Goal Alignment Score: {self.alignment_score:.1f}/100")

        if self.dependency_issues:
            print(f"\n⚠️  Dependency Issues: {len(self.dependency_issues)}")
            for issue in self.dependency_issues[:5]:
                print(f"  - {issue}")

        print(f"\nTop 10 Prioritized Tasks:")
        print(f"{'Rank':<6} {'Leverage':<10} {'Category':<15} {'Title'}")
        print("-" * 70)

        for task in self.prioritized_tasks[:10]:
            print(
                f"{task.priority_rank:<6} "
                f"{task.leverage_score:<10.1f} "
                f"{task.category.value:<15} "
                f"{task.title[:40]}"
            )

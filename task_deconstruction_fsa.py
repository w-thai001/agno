"""
Task Deconstruction FSA (Finite State Automaton)

A production-ready implementation for decomposing complex tasks into atomic actions
with dependency tracking and LQ (Local Quality) scoring for prioritization.

Follows MLA (Multi-Level Abstraction) principles for hierarchical task breakdown.
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Set, Tuple
import re


class FSAState(Enum):
    """FSA states for task decomposition process."""
    INIT = auto()
    ANALYZING = auto()
    DECOMPOSING = auto()
    PRIORITIZING = auto()
    VALIDATING = auto()
    COMPLETE = auto()
    ERROR = auto()


class ActionType(Enum):
    """Types of atomic actions."""
    READ = auto()
    WRITE = auto()
    MODIFY = auto()
    ANALYZE = auto()
    VALIDATE = auto()
    EXECUTE = auto()
    PLAN = auto()


@dataclass
class AtomicAction:
    """Represents an atomic action in the task decomposition."""
    id: str
    description: str
    action_type: ActionType
    dependencies: Set[str] = field(default_factory=set)
    priority_score: float = 0.0
    complexity: int = 1  # 1-10 scale
    metadata: Dict = field(default_factory=dict)

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if isinstance(other, AtomicAction):
            return self.id == other.id
        return False

    def __repr__(self):
        return f"AtomicAction(id={self.id}, type={self.action_type.name}, priority={self.priority_score:.2f})"


class TaskDecompositionError(Exception):
    """Custom exception for task decomposition errors."""
    pass


class TaskDecompositionFSA:
    """
    Finite State Automaton for decomposing complex tasks into atomic actions.

    This class implements an FSA-based approach to break down complex task descriptions
    into manageable atomic actions with dependency tracking and priority scoring.

    Attributes:
        state: Current FSA state
        actions: List of decomposed atomic actions
        dependency_graph: Adjacency list representation of action dependencies
    """

    def __init__(self):
        """Initialize the Task Decomposition FSA."""
        self.state: FSAState = FSAState.INIT
        self.actions: List[AtomicAction] = []
        self.dependency_graph: Dict[str, Set[str]] = {}
        self._action_counter: int = 0

    def decompose(
        self,
        task_description: str,
        context: Optional[Dict] = None
    ) -> List[AtomicAction]:
        """
        Decompose a complex task into atomic actions with dependencies and priorities.

        Args:
            task_description: Natural language description of the task
            context: Optional context dictionary with additional information
                    (e.g., project_type, complexity_level, constraints)

        Returns:
            List of AtomicAction objects sorted by priority score

        Raises:
            TaskDecompositionError: If task decomposition fails
            ValueError: If inputs are invalid
        """
        # Validate inputs
        self._validate_inputs(task_description, context)

        # Initialize context
        context = context or {}
        self.state = FSAState.ANALYZING

        try:
            # Step 1: Analyze task and extract key components
            components = self._analyze_task(task_description, context)

            # Step 2: Decompose into atomic actions
            self.state = FSAState.DECOMPOSING
            self._decompose_components(components, context)

            # Step 3: Build dependency graph
            self._build_dependency_graph()

            # Step 4: Calculate priority scores using LQ scoring
            self.state = FSAState.PRIORITIZING
            self._calculate_priority_scores(context)

            # Step 5: Validate decomposition
            self.state = FSAState.VALIDATING
            self._validate_decomposition()

            # Step 6: Sort by priority and return
            self.state = FSAState.COMPLETE
            sorted_actions = sorted(self.actions, key=lambda a: a.priority_score, reverse=True)

            return sorted_actions

        except Exception as e:
            self.state = FSAState.ERROR
            raise TaskDecompositionError(f"Task decomposition failed: {str(e)}") from e

    def _validate_inputs(self, task_description: str, context: Optional[Dict]) -> None:
        """Validate input parameters."""
        if not task_description or not isinstance(task_description, str):
            raise ValueError("task_description must be a non-empty string")

        if task_description.strip() == "":
            raise ValueError("task_description cannot be empty or whitespace only")

        if context is not None and not isinstance(context, dict):
            raise ValueError("context must be a dictionary or None")

    def _analyze_task(self, task_description: str, context: Dict) -> List[str]:
        """
        Analyze task description and extract key components.

        Uses pattern matching and keyword analysis to identify task components.
        """
        components = []

        # Normalize text
        text = task_description.lower().strip()

        # Extract action verbs and their objects
        action_patterns = [
            (r'\b(create|build|implement|develop)\b\s+(.+?)(?:\.|,|and|$)', ActionType.WRITE),
            (r'\b(read|analyze|review|examine|check)\b\s+(.+?)(?:\.|,|and|$)', ActionType.ANALYZE),
            (r'\b(modify|update|change|refactor|fix)\b\s+(.+?)(?:\.|,|and|$)', ActionType.MODIFY),
            (r'\b(validate|verify|test|ensure)\b\s+(.+?)(?:\.|,|and|$)', ActionType.VALIDATE),
            (r'\b(execute|run|perform|do)\b\s+(.+?)(?:\.|,|and|$)', ActionType.EXECUTE),
            (r'\b(plan|design|outline|structure)\b\s+(.+?)(?:\.|,|and|$)', ActionType.PLAN),
        ]

        for pattern, action_type in action_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                component = {
                    'type': action_type,
                    'description': match.group(0).strip(),
                    'object': match.group(2).strip() if len(match.groups()) > 1 else ""
                }
                components.append(component)

        # If no patterns matched, create generic actions based on complexity
        if not components:
            components = self._create_default_components(task_description, context)

        return components

    def _create_default_components(self, task_description: str, context: Dict) -> List[Dict]:
        """Create default components when no patterns are matched."""
        complexity = context.get('complexity_level', 'medium')

        if complexity == 'simple':
            return [
                {'type': ActionType.ANALYZE, 'description': f'Analyze: {task_description}', 'object': 'task'},
                {'type': ActionType.EXECUTE, 'description': f'Execute: {task_description}', 'object': 'task'}
            ]
        else:
            return [
                {'type': ActionType.PLAN, 'description': f'Plan: {task_description}', 'object': 'task'},
                {'type': ActionType.ANALYZE, 'description': f'Analyze requirements: {task_description}', 'object': 'requirements'},
                {'type': ActionType.EXECUTE, 'description': f'Execute: {task_description}', 'object': 'task'},
                {'type': ActionType.VALIDATE, 'description': f'Validate: {task_description}', 'object': 'results'}
            ]

    def _decompose_components(self, components: List[Dict], context: Dict) -> None:
        """Decompose components into atomic actions."""
        self.actions = []
        self._action_counter = 0

        for component in components:
            action = self._create_atomic_action(component, context)
            self.actions.append(action)

            # For complex tasks, add sub-actions
            if context.get('complexity_level') == 'high' and component['type'] in [ActionType.WRITE, ActionType.MODIFY]:
                sub_actions = self._create_sub_actions(action, context)
                self.actions.extend(sub_actions)

    def _create_atomic_action(self, component: Dict, context: Dict) -> AtomicAction:
        """Create an atomic action from a component."""
        action_id = f"action_{self._action_counter}"
        self._action_counter += 1

        # Determine complexity based on action type and context
        complexity_map = {
            ActionType.READ: 2,
            ActionType.ANALYZE: 4,
            ActionType.PLAN: 5,
            ActionType.WRITE: 6,
            ActionType.MODIFY: 5,
            ActionType.EXECUTE: 7,
            ActionType.VALIDATE: 3,
        }

        base_complexity = complexity_map.get(component['type'], 5)

        # Adjust for context
        if context.get('complexity_level') == 'high':
            base_complexity = min(10, base_complexity + 2)
        elif context.get('complexity_level') == 'simple':
            base_complexity = max(1, base_complexity - 2)

        action = AtomicAction(
            id=action_id,
            description=component['description'],
            action_type=component['type'],
            complexity=base_complexity,
            metadata={
                'object': component.get('object', ''),
                'context': context
            }
        )

        return action

    def _create_sub_actions(self, parent_action: AtomicAction, context: Dict) -> List[AtomicAction]:
        """Create sub-actions for complex actions."""
        sub_actions = []

        if parent_action.action_type == ActionType.WRITE:
            # Break down writing into design, implement, test
            for phase in ['design', 'implement', 'test']:
                action_id = f"action_{self._action_counter}"
                self._action_counter += 1

                sub_action = AtomicAction(
                    id=action_id,
                    description=f"{phase.capitalize()} phase for: {parent_action.description}",
                    action_type=ActionType.WRITE if phase == 'implement' else ActionType.VALIDATE,
                    complexity=max(1, parent_action.complexity - 2),
                    dependencies={parent_action.id} if phase != 'design' else set(),
                    metadata={'parent': parent_action.id, 'phase': phase}
                )
                sub_actions.append(sub_action)

        return sub_actions

    def _build_dependency_graph(self) -> None:
        """Build dependency graph from atomic actions."""
        self.dependency_graph = {action.id: action.dependencies.copy() for action in self.actions}

        # Add implicit dependencies based on action types
        action_order = [
            ActionType.PLAN,
            ActionType.READ,
            ActionType.ANALYZE,
            ActionType.WRITE,
            ActionType.MODIFY,
            ActionType.EXECUTE,
            ActionType.VALIDATE,
        ]

        # Create type-based dependencies
        for i, action in enumerate(self.actions):
            action_type_idx = action_order.index(action.action_type) if action.action_type in action_order else -1

            for j, other_action in enumerate(self.actions[:i]):
                other_type_idx = action_order.index(other_action.action_type) if other_action.action_type in action_order else -1

                # If this action should come after another action type
                if action_type_idx > other_type_idx and other_type_idx >= 0:
                    # Add dependency if they share context
                    if self._actions_related(action, other_action):
                        action.dependencies.add(other_action.id)
                        self.dependency_graph[action.id].add(other_action.id)

    def _actions_related(self, action1: AtomicAction, action2: AtomicAction) -> bool:
        """Check if two actions are related based on their metadata."""
        # Check if they share the same parent
        if action1.metadata.get('parent') == action2.id or action2.metadata.get('parent') == action1.id:
            return True

        # Check if they operate on the same object
        obj1 = action1.metadata.get('object', '')
        obj2 = action2.metadata.get('object', '')

        if obj1 and obj2 and obj1 == obj2:
            return True

        return False

    def _calculate_priority_scores(self, context: Dict) -> None:
        """
        Calculate priority scores using LQ (Local Quality) scoring.

        LQ Score = (Urgency * Importance) / (Complexity * Dependencies)

        Where:
        - Urgency: Based on dependency chain length (actions with more dependents are more urgent)
        - Importance: Based on action type and context
        - Complexity: Inherent complexity of the action
        - Dependencies: Number of dependencies (blocking factors)
        """
        # Calculate dependent counts (how many actions depend on this one)
        dependent_counts = {action.id: 0 for action in self.actions}
        for action in self.actions:
            for dep_id in action.dependencies:
                dependent_counts[dep_id] = dependent_counts.get(dep_id, 0) + 1

        # Importance weights by action type
        importance_weights = {
            ActionType.PLAN: 10,
            ActionType.ANALYZE: 8,
            ActionType.READ: 7,
            ActionType.WRITE: 9,
            ActionType.MODIFY: 8,
            ActionType.EXECUTE: 7,
            ActionType.VALIDATE: 6,
        }

        for action in self.actions:
            # Urgency: higher if more actions depend on this
            urgency = 5 + (dependent_counts.get(action.id, 0) * 2)

            # Importance: based on action type
            importance = importance_weights.get(action.action_type, 5)

            # Adjust importance based on context
            if context.get('priority') == 'high':
                importance *= 1.5

            # Complexity: use the action's complexity
            complexity = max(1, action.complexity)

            # Dependencies: number of blocking dependencies
            dependency_count = len(action.dependencies)
            dependency_factor = max(1, dependency_count + 1)

            # Calculate LQ score
            lq_score = (urgency * importance) / (complexity * dependency_factor)
            action.priority_score = round(lq_score, 2)

    def _validate_decomposition(self) -> None:
        """Validate the decomposition for consistency and correctness."""
        if not self.actions:
            raise TaskDecompositionError("No actions generated during decomposition")

        # Check for circular dependencies
        if self._has_circular_dependencies():
            raise TaskDecompositionError("Circular dependencies detected in action graph")

        # Validate that all dependency references exist
        all_ids = {action.id for action in self.actions}
        for action in self.actions:
            for dep_id in action.dependencies:
                if dep_id not in all_ids:
                    raise TaskDecompositionError(
                        f"Action {action.id} references non-existent dependency {dep_id}"
                    )

    def _has_circular_dependencies(self) -> bool:
        """Detect circular dependencies using DFS."""
        visited = set()
        rec_stack = set()

        def visit(node_id: str) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)

            for neighbor_id in self.dependency_graph.get(node_id, set()):
                if neighbor_id not in visited:
                    if visit(neighbor_id):
                        return True
                elif neighbor_id in rec_stack:
                    return True

            rec_stack.remove(node_id)
            return False

        for action in self.actions:
            if action.id not in visited:
                if visit(action.id):
                    return True

        return False

    def get_dependency_graph(self) -> Dict[str, Set[str]]:
        """
        Get the dependency graph as an adjacency list.

        Returns:
            Dictionary mapping action IDs to sets of dependency IDs
        """
        return self.dependency_graph.copy()

    def get_execution_order(self) -> List[AtomicAction]:
        """
        Get actions in topologically sorted order (execution order).

        Returns:
            List of actions in dependency-respecting execution order
        """
        # Topological sort using Kahn's algorithm
        in_degree = {action.id: len(action.dependencies) for action in self.actions}
        queue = [action for action in self.actions if in_degree[action.id] == 0]
        result = []

        while queue:
            # Sort queue by priority score
            queue.sort(key=lambda a: a.priority_score, reverse=True)
            current = queue.pop(0)
            result.append(current)

            # Reduce in-degree for dependent actions
            for action in self.actions:
                if current.id in action.dependencies:
                    in_degree[action.id] -= 1
                    if in_degree[action.id] == 0:
                        queue.append(action)

        return result

    def reset(self) -> None:
        """Reset the FSA to initial state."""
        self.state = FSAState.INIT
        self.actions = []
        self.dependency_graph = {}
        self._action_counter = 0

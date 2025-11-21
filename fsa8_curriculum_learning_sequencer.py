"""
FSA-8: CURRICULUM LEARNING SEQUENCER - PYTHON IMPLEMENTATION

A production-ready Python module for adaptive learning path generation and curriculum sequencing.

Key Features:
- Cross-platform subprocess support (Bash/PowerShell)
- Learning path generation with skill dependencies
- Prerequisites management
- Adaptive difficulty scaling
- Performance tracking and monitoring
- Sequence optimization using DAG algorithms
- Pre-built curriculum templates
- Export and visualization capabilities

Author: Agno Team
Version: 1.0.0
Python: 3.8+
"""

import json
import logging
import os
import platform
import subprocess
import sys
from collections import defaultdict, deque
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any, Union
import uuid


# ============================================================================
# CONFIGURATION AND LOGGING
# ============================================================================

class LogLevel(Enum):
    """Logging levels for the curriculum sequencer."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class CurriculumConfig:
    """Global configuration for curriculum learning sequencer."""

    # Platform detection
    IS_WINDOWS = platform.system() == "Windows"
    IS_LINUX = platform.system() == "Linux"
    IS_MAC = platform.system() == "Darwin"

    # Subprocess shell configuration
    SHELL_CMD = "powershell.exe" if IS_WINDOWS else "/bin/bash"
    SHELL_FLAG = "-Command" if IS_WINDOWS else "-c"

    # Default directories
    BASE_DIR = Path.cwd()
    DATA_DIR = BASE_DIR / "curriculum_data"
    EXPORT_DIR = BASE_DIR / "curriculum_exports"
    LOG_DIR = BASE_DIR / "curriculum_logs"

    # Performance thresholds
    MIN_MASTERY_SCORE = 0.7
    EXCELLENCE_SCORE = 0.9
    DEFAULT_DIFFICULTY = 0.5

    # Optimization parameters
    MAX_PREREQUISITES = 10
    MAX_PATH_LENGTH = 100
    DEFAULT_TIME_ESTIMATE = 60  # minutes

    @classmethod
    def setup_directories(cls):
        """Create necessary directories if they don't exist."""
        for directory in [cls.DATA_DIR, cls.EXPORT_DIR, cls.LOG_DIR]:
            directory.mkdir(parents=True, exist_ok=True)


def setup_logging(
    level: LogLevel = LogLevel.INFO,
    log_file: Optional[str] = None
) -> logging.Logger:
    """
    Setup logging configuration for the curriculum sequencer.

    Args:
        level: Logging level
        log_file: Optional log file path

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger("CurriculumLearningSequencer")
    logger.setLevel(getattr(logging, level.value))

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.value))
    console_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)

    # File handler if specified
    if log_file:
        # Ensure directory exists
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(getattr(logging, level.value))
        file_handler.setFormatter(console_format)
        logger.addHandler(file_handler)

    return logger


# Ensure directories exist before setting up logger
CurriculumConfig.setup_directories()

# Initialize global logger
LOGGER = setup_logging(
    LogLevel.INFO,
    str(CurriculumConfig.LOG_DIR / f"curriculum_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
)


# ============================================================================
# DATA MODELS
# ============================================================================

class DifficultyLevel(Enum):
    """Difficulty levels for learning modules."""
    BEGINNER = 1
    ELEMENTARY = 2
    INTERMEDIATE = 3
    ADVANCED = 4
    EXPERT = 5


class ModuleStatus(Enum):
    """Status of a learning module."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    MASTERED = "mastered"
    NEEDS_REVIEW = "needs_review"


class LearningStyle(Enum):
    """Different learning styles for personalization."""
    VISUAL = "visual"
    AUDITORY = "auditory"
    KINESTHETIC = "kinesthetic"
    READING_WRITING = "reading_writing"
    MIXED = "mixed"


@dataclass
class Skill:
    """Represents a skill to be learned."""
    skill_id: str
    name: str
    description: str
    category: str
    difficulty: DifficultyLevel = DifficultyLevel.INTERMEDIATE
    estimated_time: int = 60  # minutes
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert skill to dictionary."""
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "difficulty": self.difficulty.value,
            "estimated_time": self.estimated_time,
            "tags": self.tags,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Skill':
        """Create skill from dictionary."""
        data['difficulty'] = DifficultyLevel(data.get('difficulty', 3))
        return cls(**data)


@dataclass
class LearningModule:
    """Represents a learning module in the curriculum."""
    module_id: str
    skill: Skill
    prerequisites: List[str] = field(default_factory=list)
    learning_objectives: List[str] = field(default_factory=list)
    resources: List[Dict[str, str]] = field(default_factory=list)
    assessments: List[Dict[str, Any]] = field(default_factory=list)
    status: ModuleStatus = ModuleStatus.NOT_STARTED
    difficulty_score: float = 0.5
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert module to dictionary."""
        return {
            "module_id": self.module_id,
            "skill": self.skill.to_dict(),
            "prerequisites": self.prerequisites,
            "learning_objectives": self.learning_objectives,
            "resources": self.resources,
            "assessments": self.assessments,
            "status": self.status.value,
            "difficulty_score": self.difficulty_score,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


@dataclass
class LearnerProfile:
    """Represents a learner's profile and preferences."""
    learner_id: str
    name: str
    learning_style: LearningStyle = LearningStyle.MIXED
    skill_levels: Dict[str, float] = field(default_factory=dict)
    completed_modules: List[str] = field(default_factory=list)
    in_progress_modules: List[str] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    preferences: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert profile to dictionary."""
        return {
            "learner_id": self.learner_id,
            "name": self.name,
            "learning_style": self.learning_style.value,
            "skill_levels": self.skill_levels,
            "completed_modules": self.completed_modules,
            "in_progress_modules": self.in_progress_modules,
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "preferences": self.preferences,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


@dataclass
class ProgressRecord:
    """Represents a learner's progress on a module."""
    record_id: str
    learner_id: str
    module_id: str
    start_time: datetime
    completion_time: Optional[datetime] = None
    score: float = 0.0
    attempts: int = 0
    time_spent: int = 0  # minutes
    assessments_passed: int = 0
    total_assessments: int = 0
    notes: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert progress record to dictionary."""
        return {
            "record_id": self.record_id,
            "learner_id": self.learner_id,
            "module_id": self.module_id,
            "start_time": self.start_time.isoformat(),
            "completion_time": self.completion_time.isoformat() if self.completion_time else None,
            "score": self.score,
            "attempts": self.attempts,
            "time_spent": self.time_spent,
            "assessments_passed": self.assessments_passed,
            "total_assessments": self.total_assessments,
            "notes": self.notes,
            "metadata": self.metadata
        }


@dataclass
class LearningPath:
    """Represents an optimized learning path."""
    path_id: str
    learner_id: str
    modules: List[str]  # Ordered list of module IDs
    estimated_duration: int  # Total minutes
    difficulty_progression: List[float]
    prerequisites_satisfied: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert learning path to dictionary."""
        return {
            "path_id": self.path_id,
            "learner_id": self.learner_id,
            "modules": self.modules,
            "estimated_duration": self.estimated_duration,
            "difficulty_progression": self.difficulty_progression,
            "prerequisites_satisfied": self.prerequisites_satisfied,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata
        }


# ============================================================================
# EXCEPTION CLASSES
# ============================================================================

class CurriculumError(Exception):
    """Base exception for curriculum sequencer errors."""
    pass


class PrerequisiteError(CurriculumError):
    """Exception raised for prerequisite violations."""
    pass


class CircularDependencyError(CurriculumError):
    """Exception raised when circular dependencies are detected."""
    pass


class ModuleNotFoundError(CurriculumError):
    """Exception raised when a module is not found."""
    pass


class InvalidDifficultyError(CurriculumError):
    """Exception raised for invalid difficulty values."""
    pass


class SubprocessError(CurriculumError):
    """Exception raised for subprocess execution errors."""
    pass


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

class SubprocessExecutor:
    """Cross-platform subprocess executor for file operations."""

    @staticmethod
    def execute_command(command: str, timeout: int = 30) -> Tuple[str, str, int]:
        """
        Execute a shell command across platforms.

        Args:
            command: Command to execute
            timeout: Command timeout in seconds

        Returns:
            Tuple of (stdout, stderr, return_code)

        Raises:
            SubprocessError: If command execution fails
        """
        try:
            if CurriculumConfig.IS_WINDOWS:
                # PowerShell command
                full_command = [
                    CurriculumConfig.SHELL_CMD,
                    CurriculumConfig.SHELL_FLAG,
                    command
                ]
            else:
                # Bash command
                full_command = [
                    CurriculumConfig.SHELL_CMD,
                    CurriculumConfig.SHELL_FLAG,
                    command
                ]

            LOGGER.debug(f"Executing command: {command}")

            result = subprocess.run(
                full_command,
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=False
            )

            return result.stdout, result.stderr, result.returncode

        except subprocess.TimeoutExpired as e:
            error_msg = f"Command timed out after {timeout} seconds: {command}"
            LOGGER.error(error_msg)
            raise SubprocessError(error_msg) from e
        except Exception as e:
            error_msg = f"Failed to execute command: {command}. Error: {str(e)}"
            LOGGER.error(error_msg)
            raise SubprocessError(error_msg) from e

    @staticmethod
    def write_file(file_path: Path, content: str) -> bool:
        """
        Write content to a file using subprocess.

        Args:
            file_path: Path to the file
            content: Content to write

        Returns:
            True if successful, False otherwise
        """
        try:
            # Escape content for shell
            escaped_content = content.replace('"', '\\"').replace('$', '\\$')

            if CurriculumConfig.IS_WINDOWS:
                command = f'Set-Content -Path "{file_path}" -Value "{escaped_content}"'
            else:
                command = f'echo "{escaped_content}" > "{file_path}"'

            stdout, stderr, returncode = SubprocessExecutor.execute_command(command)

            if returncode != 0:
                LOGGER.error(f"Failed to write file {file_path}: {stderr}")
                return False

            LOGGER.debug(f"Successfully wrote file: {file_path}")
            return True

        except Exception as e:
            LOGGER.error(f"Error writing file {file_path}: {str(e)}")
            return False

    @staticmethod
    def read_file(file_path: Path) -> Optional[str]:
        """
        Read content from a file using subprocess.

        Args:
            file_path: Path to the file

        Returns:
            File content or None if failed
        """
        try:
            if CurriculumConfig.IS_WINDOWS:
                command = f'Get-Content -Path "{file_path}" -Raw'
            else:
                command = f'cat "{file_path}"'

            stdout, stderr, returncode = SubprocessExecutor.execute_command(command)

            if returncode != 0:
                LOGGER.error(f"Failed to read file {file_path}: {stderr}")
                return None

            return stdout

        except Exception as e:
            LOGGER.error(f"Error reading file {file_path}: {str(e)}")
            return None

    @staticmethod
    def create_directory(dir_path: Path) -> bool:
        """
        Create a directory using subprocess.

        Args:
            dir_path: Path to the directory

        Returns:
            True if successful, False otherwise
        """
        try:
            if CurriculumConfig.IS_WINDOWS:
                command = f'New-Item -ItemType Directory -Path "{dir_path}" -Force'
            else:
                command = f'mkdir -p "{dir_path}"'

            stdout, stderr, returncode = SubprocessExecutor.execute_command(command)

            if returncode != 0 and "already exists" not in stderr.lower():
                LOGGER.error(f"Failed to create directory {dir_path}: {stderr}")
                return False

            LOGGER.debug(f"Successfully created directory: {dir_path}")
            return True

        except Exception as e:
            LOGGER.error(f"Error creating directory {dir_path}: {str(e)}")
            return False


def generate_id(prefix: str = "") -> str:
    """Generate a unique ID with optional prefix."""
    unique_id = str(uuid.uuid4())[:8]
    return f"{prefix}_{unique_id}" if prefix else unique_id


# ============================================================================
# CORE CLASS: PREREQUISITE MANAGER
# ============================================================================

class PrerequisiteManager:
    """
    Manages skill dependencies and prerequisites in the curriculum.

    Features:
    - Dependency graph management
    - Circular dependency detection
    - Topological sorting
    - Prerequisite validation
    """

    def __init__(self):
        """Initialize the prerequisite manager."""
        self.dependencies: Dict[str, Set[str]] = defaultdict(set)
        self.dependents: Dict[str, Set[str]] = defaultdict(set)
        self.modules: Dict[str, LearningModule] = {}
        LOGGER.info("PrerequisiteManager initialized")

    def add_module(self, module: LearningModule) -> None:
        """
        Add a learning module to the prerequisite graph.

        Args:
            module: Learning module to add

        Raises:
            CircularDependencyError: If adding creates circular dependency
        """
        try:
            self.modules[module.module_id] = module

            # Add dependencies
            for prereq in module.prerequisites:
                self.dependencies[module.module_id].add(prereq)
                self.dependents[prereq].add(module.module_id)

            # Check for circular dependencies
            if self._has_circular_dependency(module.module_id):
                # Rollback
                del self.modules[module.module_id]
                for prereq in module.prerequisites:
                    self.dependencies[module.module_id].discard(prereq)
                    self.dependents[prereq].discard(module.module_id)

                raise CircularDependencyError(
                    f"Adding module {module.module_id} would create circular dependency"
                )

            LOGGER.info(f"Added module {module.module_id} to prerequisite graph")

        except Exception as e:
            LOGGER.error(f"Error adding module {module.module_id}: {str(e)}")
            raise

    def remove_module(self, module_id: str) -> bool:
        """
        Remove a module from the prerequisite graph.

        Args:
            module_id: ID of the module to remove

        Returns:
            True if successful, False otherwise
        """
        try:
            if module_id not in self.modules:
                LOGGER.warning(f"Module {module_id} not found")
                return False

            # Remove from modules
            del self.modules[module_id]

            # Remove dependencies
            if module_id in self.dependencies:
                for prereq in self.dependencies[module_id]:
                    self.dependents[prereq].discard(module_id)
                del self.dependencies[module_id]

            # Remove dependents
            if module_id in self.dependents:
                for dependent in self.dependents[module_id]:
                    self.dependencies[dependent].discard(module_id)
                del self.dependents[module_id]

            LOGGER.info(f"Removed module {module_id} from prerequisite graph")
            return True

        except Exception as e:
            LOGGER.error(f"Error removing module {module_id}: {str(e)}")
            return False

    def get_prerequisites(self, module_id: str, recursive: bool = False) -> Set[str]:
        """
        Get prerequisites for a module.

        Args:
            module_id: ID of the module
            recursive: If True, get all transitive prerequisites

        Returns:
            Set of prerequisite module IDs
        """
        if not recursive:
            return self.dependencies.get(module_id, set()).copy()

        # Get all transitive prerequisites using BFS
        prerequisites = set()
        queue = deque([module_id])
        visited = {module_id}

        while queue:
            current = queue.popleft()
            for prereq in self.dependencies.get(current, set()):
                if prereq not in visited:
                    prerequisites.add(prereq)
                    visited.add(prereq)
                    queue.append(prereq)

        return prerequisites

    def get_dependents(self, module_id: str, recursive: bool = False) -> Set[str]:
        """
        Get modules that depend on this module.

        Args:
            module_id: ID of the module
            recursive: If True, get all transitive dependents

        Returns:
            Set of dependent module IDs
        """
        if not recursive:
            return self.dependents.get(module_id, set()).copy()

        # Get all transitive dependents using BFS
        dependents = set()
        queue = deque([module_id])
        visited = {module_id}

        while queue:
            current = queue.popleft()
            for dependent in self.dependents.get(current, set()):
                if dependent not in visited:
                    dependents.add(dependent)
                    visited.add(dependent)
                    queue.append(dependent)

        return dependents

    def validate_prerequisites(
        self,
        module_id: str,
        completed_modules: Set[str]
    ) -> Tuple[bool, List[str]]:
        """
        Check if prerequisites are satisfied for a module.

        Args:
            module_id: ID of the module to check
            completed_modules: Set of completed module IDs

        Returns:
            Tuple of (are_satisfied, missing_prerequisites)
        """
        prerequisites = self.get_prerequisites(module_id, recursive=False)
        missing = [p for p in prerequisites if p not in completed_modules]

        return len(missing) == 0, missing

    def topological_sort(self) -> List[str]:
        """
        Perform topological sort on the prerequisite graph.

        Returns:
            Ordered list of module IDs

        Raises:
            CircularDependencyError: If circular dependency exists
        """
        try:
            # Calculate in-degree for each node
            in_degree = defaultdict(int)
            for module_id in self.modules:
                in_degree[module_id] = len(self.dependencies.get(module_id, set()))

            # Queue of nodes with no prerequisites
            queue = deque([m for m in self.modules if in_degree[m] == 0])
            sorted_modules = []

            while queue:
                current = queue.popleft()
                sorted_modules.append(current)

                # Reduce in-degree for dependents
                for dependent in self.dependents.get(current, set()):
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        queue.append(dependent)

            # Check if all modules were sorted
            if len(sorted_modules) != len(self.modules):
                raise CircularDependencyError("Circular dependency detected in prerequisite graph")

            LOGGER.info(f"Topological sort completed: {len(sorted_modules)} modules")
            return sorted_modules

        except Exception as e:
            LOGGER.error(f"Error in topological sort: {str(e)}")
            raise

    def _has_circular_dependency(self, start_module: str) -> bool:
        """
        Check if adding a module creates circular dependency using DFS.

        Args:
            start_module: Module ID to check

        Returns:
            True if circular dependency exists, False otherwise
        """
        visited = set()
        rec_stack = set()

        def dfs(module_id: str) -> bool:
            visited.add(module_id)
            rec_stack.add(module_id)

            for prereq in self.dependencies.get(module_id, set()):
                if prereq not in visited:
                    if dfs(prereq):
                        return True
                elif prereq in rec_stack:
                    return True

            rec_stack.remove(module_id)
            return False

        return dfs(start_module)

    def get_learning_levels(self) -> Dict[int, List[str]]:
        """
        Group modules into learning levels based on dependency depth.

        Returns:
            Dictionary mapping level number to list of module IDs
        """
        levels = defaultdict(list)
        sorted_modules = self.topological_sort()

        # Calculate level for each module
        module_levels = {}
        for module_id in sorted_modules:
            prereqs = self.get_prerequisites(module_id, recursive=False)
            if not prereqs:
                module_levels[module_id] = 0
            else:
                max_prereq_level = max(module_levels[p] for p in prereqs)
                module_levels[module_id] = max_prereq_level + 1

        # Group by level
        for module_id, level in module_levels.items():
            levels[level].append(module_id)

        return dict(levels)

    def export_graph(self, file_path: Path) -> bool:
        """
        Export prerequisite graph to JSON file.

        Args:
            file_path: Path to export file

        Returns:
            True if successful, False otherwise
        """
        try:
            graph_data = {
                "modules": {
                    mid: module.to_dict()
                    for mid, module in self.modules.items()
                },
                "dependencies": {
                    mid: list(deps)
                    for mid, deps in self.dependencies.items()
                },
                "dependents": {
                    mid: list(deps)
                    for mid, deps in self.dependents.items()
                }
            }

            json_content = json.dumps(graph_data, indent=2)
            return SubprocessExecutor.write_file(file_path, json_content)

        except Exception as e:
            LOGGER.error(f"Error exporting prerequisite graph: {str(e)}")
            return False


# ============================================================================
# CORE CLASS: DIFFICULTY SCALER
# ============================================================================

class DifficultyScaler:
    """
    Manages adaptive difficulty adjustment based on learner performance.

    Features:
    - Dynamic difficulty scaling
    - Performance-based adjustments
    - Smooth difficulty progression
    - Personalized difficulty curves
    """

    def __init__(
        self,
        min_difficulty: float = 0.1,
        max_difficulty: float = 1.0,
        adjustment_rate: float = 0.1
    ):
        """
        Initialize the difficulty scaler.

        Args:
            min_difficulty: Minimum difficulty level (0.0-1.0)
            max_difficulty: Maximum difficulty level (0.0-1.0)
            adjustment_rate: Rate of difficulty adjustment (0.0-1.0)
        """
        self.min_difficulty = min_difficulty
        self.max_difficulty = max_difficulty
        self.adjustment_rate = adjustment_rate
        self.learner_difficulties: Dict[str, float] = {}
        LOGGER.info("DifficultyScaler initialized")

    def calculate_difficulty(
        self,
        base_difficulty: float,
        performance_score: float,
        current_difficulty: Optional[float] = None
    ) -> float:
        """
        Calculate adjusted difficulty based on performance.

        Args:
            base_difficulty: Base difficulty of the module (0.0-1.0)
            performance_score: Learner's performance score (0.0-1.0)
            current_difficulty: Current difficulty level

        Returns:
            Adjusted difficulty level (0.0-1.0)
        """
        try:
            if not 0.0 <= base_difficulty <= 1.0:
                raise InvalidDifficultyError(f"Invalid base difficulty: {base_difficulty}")

            if not 0.0 <= performance_score <= 1.0:
                raise InvalidDifficultyError(f"Invalid performance score: {performance_score}")

            # Start with base difficulty if no current difficulty
            if current_difficulty is None:
                current_difficulty = base_difficulty

            # Calculate adjustment based on performance
            if performance_score >= CurriculumConfig.EXCELLENCE_SCORE:
                # Excellent performance - increase difficulty
                adjustment = self.adjustment_rate * 1.5
            elif performance_score >= CurriculumConfig.MIN_MASTERY_SCORE:
                # Good performance - slight increase
                adjustment = self.adjustment_rate * 0.5
            elif performance_score >= 0.5:
                # Average performance - maintain difficulty
                adjustment = 0.0
            else:
                # Poor performance - decrease difficulty
                adjustment = -self.adjustment_rate * 1.0

            # Apply adjustment
            new_difficulty = current_difficulty + adjustment

            # Clamp to valid range
            new_difficulty = max(self.min_difficulty, min(self.max_difficulty, new_difficulty))

            LOGGER.debug(
                f"Difficulty adjusted: {current_difficulty:.2f} -> {new_difficulty:.2f} "
                f"(performance: {performance_score:.2f})"
            )

            return new_difficulty

        except Exception as e:
            LOGGER.error(f"Error calculating difficulty: {str(e)}")
            return base_difficulty

    def get_learner_difficulty(self, learner_id: str) -> float:
        """
        Get current difficulty level for a learner.

        Args:
            learner_id: ID of the learner

        Returns:
            Current difficulty level
        """
        return self.learner_difficulties.get(learner_id, CurriculumConfig.DEFAULT_DIFFICULTY)

    def update_learner_difficulty(
        self,
        learner_id: str,
        new_difficulty: float
    ) -> None:
        """
        Update difficulty level for a learner.

        Args:
            learner_id: ID of the learner
            new_difficulty: New difficulty level
        """
        if not 0.0 <= new_difficulty <= 1.0:
            raise InvalidDifficultyError(f"Invalid difficulty: {new_difficulty}")

        self.learner_difficulties[learner_id] = new_difficulty
        LOGGER.info(f"Updated difficulty for learner {learner_id}: {new_difficulty:.2f}")

    def generate_difficulty_progression(
        self,
        start_difficulty: float,
        end_difficulty: float,
        num_steps: int,
        progression_type: str = "linear"
    ) -> List[float]:
        """
        Generate a difficulty progression curve.

        Args:
            start_difficulty: Starting difficulty level
            end_difficulty: Ending difficulty level
            num_steps: Number of steps in progression
            progression_type: Type of progression ("linear", "exponential", "logarithmic")

        Returns:
            List of difficulty levels
        """
        try:
            if num_steps < 2:
                return [start_difficulty]

            progression = []

            if progression_type == "linear":
                step = (end_difficulty - start_difficulty) / (num_steps - 1)
                progression = [start_difficulty + i * step for i in range(num_steps)]

            elif progression_type == "exponential":
                # Exponential growth
                import math
                for i in range(num_steps):
                    t = i / (num_steps - 1)
                    difficulty = start_difficulty + (end_difficulty - start_difficulty) * (math.exp(t) - 1) / (math.e - 1)
                    progression.append(difficulty)

            elif progression_type == "logarithmic":
                # Logarithmic growth
                import math
                for i in range(num_steps):
                    t = i / (num_steps - 1)
                    difficulty = start_difficulty + (end_difficulty - start_difficulty) * math.log(1 + t) / math.log(2)
                    progression.append(difficulty)

            else:
                LOGGER.warning(f"Unknown progression type: {progression_type}, using linear")
                return self.generate_difficulty_progression(
                    start_difficulty, end_difficulty, num_steps, "linear"
                )

            # Clamp all values to valid range
            progression = [max(self.min_difficulty, min(self.max_difficulty, d)) for d in progression]

            return progression

        except Exception as e:
            LOGGER.error(f"Error generating difficulty progression: {str(e)}")
            return [start_difficulty] * num_steps

    def recommend_next_difficulty(
        self,
        learner_id: str,
        recent_scores: List[float],
        current_difficulty: float
    ) -> float:
        """
        Recommend next difficulty level based on recent performance.

        Args:
            learner_id: ID of the learner
            recent_scores: List of recent performance scores
            current_difficulty: Current difficulty level

        Returns:
            Recommended difficulty level
        """
        if not recent_scores:
            return current_difficulty

        # Calculate average recent performance
        avg_score = sum(recent_scores) / len(recent_scores)

        # Calculate trend (improving or declining)
        if len(recent_scores) >= 2:
            recent_avg = sum(recent_scores[-3:]) / min(3, len(recent_scores))
            earlier_avg = sum(recent_scores[:-3]) / max(1, len(recent_scores) - 3) if len(recent_scores) > 3 else avg_score
            trend = recent_avg - earlier_avg
        else:
            trend = 0.0

        # Adjust based on trend
        if trend > 0.1:
            # Improving - can increase difficulty more
            multiplier = 1.2
        elif trend < -0.1:
            # Declining - be more conservative
            multiplier = 0.8
        else:
            # Stable
            multiplier = 1.0

        base_adjustment = self.calculate_difficulty(
            current_difficulty,
            avg_score,
            current_difficulty
        )

        # Apply trend multiplier
        adjustment = (base_adjustment - current_difficulty) * multiplier
        new_difficulty = current_difficulty + adjustment

        # Clamp to valid range
        new_difficulty = max(self.min_difficulty, min(self.max_difficulty, new_difficulty))

        self.update_learner_difficulty(learner_id, new_difficulty)

        return new_difficulty


# ============================================================================
# CORE CLASS: PROGRESS TRACKER
# ============================================================================

class ProgressTracker:
    """
    Tracks and monitors learner progress through the curriculum.

    Features:
    - Progress recording and retrieval
    - Performance analytics
    - Achievement tracking
    - Learning velocity calculation
    """

    def __init__(self):
        """Initialize the progress tracker."""
        self.progress_records: Dict[str, ProgressRecord] = {}
        self.learner_records: Dict[str, List[str]] = defaultdict(list)
        self.module_records: Dict[str, List[str]] = defaultdict(list)
        LOGGER.info("ProgressTracker initialized")

    def record_progress(self, record: ProgressRecord) -> None:
        """
        Record a learner's progress on a module.

        Args:
            record: Progress record to store
        """
        self.progress_records[record.record_id] = record
        self.learner_records[record.learner_id].append(record.record_id)
        self.module_records[record.module_id].append(record.record_id)

        LOGGER.info(
            f"Recorded progress for learner {record.learner_id} "
            f"on module {record.module_id} (score: {record.score:.2f})"
        )

    def get_learner_progress(self, learner_id: str) -> List[ProgressRecord]:
        """
        Get all progress records for a learner.

        Args:
            learner_id: ID of the learner

        Returns:
            List of progress records
        """
        record_ids = self.learner_records.get(learner_id, [])
        return [self.progress_records[rid] for rid in record_ids]

    def get_module_progress(self, module_id: str) -> List[ProgressRecord]:
        """
        Get all progress records for a module.

        Args:
            module_id: ID of the module

        Returns:
            List of progress records
        """
        record_ids = self.module_records.get(module_id, [])
        return [self.progress_records[rid] for rid in record_ids]

    def calculate_completion_rate(self, learner_id: str, total_modules: int) -> float:
        """
        Calculate completion rate for a learner.

        Args:
            learner_id: ID of the learner
            total_modules: Total number of modules in curriculum

        Returns:
            Completion rate (0.0-1.0)
        """
        if total_modules == 0:
            return 0.0

        records = self.get_learner_progress(learner_id)
        completed = sum(1 for r in records if r.completion_time is not None)

        return completed / total_modules

    def calculate_average_score(self, learner_id: str) -> float:
        """
        Calculate average score for a learner.

        Args:
            learner_id: ID of the learner

        Returns:
            Average score (0.0-1.0)
        """
        records = self.get_learner_progress(learner_id)

        if not records:
            return 0.0

        completed_records = [r for r in records if r.completion_time is not None]

        if not completed_records:
            return 0.0

        return sum(r.score for r in completed_records) / len(completed_records)

    def calculate_learning_velocity(self, learner_id: str) -> float:
        """
        Calculate learning velocity (modules per day).

        Args:
            learner_id: ID of the learner

        Returns:
            Modules completed per day
        """
        records = self.get_learner_progress(learner_id)
        completed_records = [r for r in records if r.completion_time is not None]

        if len(completed_records) < 2:
            return 0.0

        # Sort by completion time
        sorted_records = sorted(completed_records, key=lambda r: r.completion_time)

        first_completion = sorted_records[0].completion_time
        last_completion = sorted_records[-1].completion_time

        days_elapsed = (last_completion - first_completion).total_seconds() / 86400

        if days_elapsed == 0:
            return 0.0

        return len(completed_records) / days_elapsed

    def get_struggling_modules(
        self,
        learner_id: str,
        threshold_score: float = 0.6,
        min_attempts: int = 2
    ) -> List[str]:
        """
        Identify modules where learner is struggling.

        Args:
            learner_id: ID of the learner
            threshold_score: Score threshold for struggling
            min_attempts: Minimum attempts to consider

        Returns:
            List of module IDs where learner is struggling
        """
        records = self.get_learner_progress(learner_id)
        struggling = []

        for record in records:
            if (record.attempts >= min_attempts and
                record.score < threshold_score):
                struggling.append(record.module_id)

        return struggling

    def get_mastered_modules(
        self,
        learner_id: str,
        mastery_score: float = None
    ) -> List[str]:
        """
        Get modules that learner has mastered.

        Args:
            learner_id: ID of the learner
            mastery_score: Minimum score for mastery (default from config)

        Returns:
            List of mastered module IDs
        """
        if mastery_score is None:
            mastery_score = CurriculumConfig.EXCELLENCE_SCORE

        records = self.get_learner_progress(learner_id)
        mastered = []

        for record in records:
            if (record.completion_time is not None and
                record.score >= mastery_score):
                mastered.append(record.module_id)

        return mastered

    def generate_progress_report(self, learner_id: str) -> Dict[str, Any]:
        """
        Generate comprehensive progress report for a learner.

        Args:
            learner_id: ID of the learner

        Returns:
            Progress report dictionary
        """
        records = self.get_learner_progress(learner_id)

        completed_records = [r for r in records if r.completion_time is not None]
        in_progress_records = [r for r in records if r.completion_time is None]

        total_time_spent = sum(r.time_spent for r in records)

        report = {
            "learner_id": learner_id,
            "total_modules_attempted": len(records),
            "modules_completed": len(completed_records),
            "modules_in_progress": len(in_progress_records),
            "average_score": self.calculate_average_score(learner_id),
            "total_time_spent_minutes": total_time_spent,
            "learning_velocity": self.calculate_learning_velocity(learner_id),
            "mastered_modules": self.get_mastered_modules(learner_id),
            "struggling_modules": self.get_struggling_modules(learner_id),
            "recent_activity": [
                {
                    "module_id": r.module_id,
                    "score": r.score,
                    "completion_time": r.completion_time.isoformat() if r.completion_time else None
                }
                for r in sorted(records, key=lambda x: x.start_time, reverse=True)[:5]
            ]
        }

        return report

    def export_progress(self, learner_id: str, file_path: Path) -> bool:
        """
        Export learner progress to JSON file.

        Args:
            learner_id: ID of the learner
            file_path: Path to export file

        Returns:
            True if successful, False otherwise
        """
        try:
            report = self.generate_progress_report(learner_id)
            records = self.get_learner_progress(learner_id)

            export_data = {
                "report": report,
                "detailed_records": [r.to_dict() for r in records]
            }

            json_content = json.dumps(export_data, indent=2)
            return SubprocessExecutor.write_file(file_path, json_content)

        except Exception as e:
            LOGGER.error(f"Error exporting progress: {str(e)}")
            return False


# ============================================================================
# CORE CLASS: PATH OPTIMIZER
# ============================================================================

class PathOptimizer:
    """
    Optimizes learning paths using DAG algorithms.

    Features:
    - Optimal path generation
    - Multi-criteria optimization (time, difficulty, prerequisites)
    - Personalized path recommendations
    - Alternative path generation
    """

    def __init__(self, prerequisite_manager: PrerequisiteManager):
        """
        Initialize the path optimizer.

        Args:
            prerequisite_manager: Prerequisite manager instance
        """
        self.prerequisite_manager = prerequisite_manager
        LOGGER.info("PathOptimizer initialized")

    def generate_optimal_path(
        self,
        learner_profile: LearnerProfile,
        target_skills: List[str],
        optimization_criteria: str = "balanced"
    ) -> Optional[LearningPath]:
        """
        Generate optimal learning path for a learner.

        Args:
            learner_profile: Learner's profile
            target_skills: List of target skill/module IDs
            optimization_criteria: Optimization strategy
                - "shortest": Minimize number of modules
                - "fastest": Minimize total time
                - "easiest": Minimize difficulty progression
                - "balanced": Balance all criteria

        Returns:
            Optimized learning path or None if impossible
        """
        try:
            # Get all required modules including prerequisites
            required_modules = set(target_skills)
            for skill_id in target_skills:
                prereqs = self.prerequisite_manager.get_prerequisites(skill_id, recursive=True)
                required_modules.update(prereqs)

            # Remove already completed modules
            required_modules -= set(learner_profile.completed_modules)

            if not required_modules:
                LOGGER.info("All target modules already completed")
                return None

            # Get topological ordering
            all_sorted = self.prerequisite_manager.topological_sort()

            # Filter to required modules only
            sorted_required = [m for m in all_sorted if m in required_modules]

            # Calculate path metrics
            total_duration = 0
            difficulty_progression = []

            for module_id in sorted_required:
                module = self.prerequisite_manager.modules.get(module_id)
                if module:
                    total_duration += module.skill.estimated_time
                    difficulty_progression.append(module.difficulty_score)

            # Create learning path
            path = LearningPath(
                path_id=generate_id("path"),
                learner_id=learner_profile.learner_id,
                modules=sorted_required,
                estimated_duration=total_duration,
                difficulty_progression=difficulty_progression,
                prerequisites_satisfied=True,
                metadata={
                    "optimization_criteria": optimization_criteria,
                    "target_skills": target_skills,
                    "generated_at": datetime.now().isoformat()
                }
            )

            LOGGER.info(
                f"Generated optimal path with {len(sorted_required)} modules, "
                f"estimated duration: {total_duration} minutes"
            )

            return path

        except Exception as e:
            LOGGER.error(f"Error generating optimal path: {str(e)}")
            return None

    def generate_adaptive_path(
        self,
        learner_profile: LearnerProfile,
        target_skills: List[str],
        difficulty_scaler: DifficultyScaler
    ) -> Optional[LearningPath]:
        """
        Generate adaptive learning path based on learner's current level.

        Args:
            learner_profile: Learner's profile
            target_skills: List of target skill/module IDs
            difficulty_scaler: Difficulty scaler instance

        Returns:
            Adaptive learning path or None if impossible
        """
        try:
            # Get base optimal path
            base_path = self.generate_optimal_path(
                learner_profile,
                target_skills,
                "balanced"
            )

            if not base_path:
                return None

            # Get learner's current difficulty level
            current_difficulty = difficulty_scaler.get_learner_difficulty(
                learner_profile.learner_id
            )

            # Adjust module selection based on difficulty
            adapted_modules = []
            for module_id in base_path.modules:
                module = self.prerequisite_manager.modules.get(module_id)
                if module:
                    # Check if module difficulty matches learner level
                    if abs(module.difficulty_score - current_difficulty) <= 0.3:
                        adapted_modules.append(module_id)
                    elif module.difficulty_score < current_difficulty:
                        # Module too easy, but keep if it's a prerequisite
                        if any(module_id in self.prerequisite_manager.get_prerequisites(m, False)
                               for m in base_path.modules):
                            adapted_modules.append(module_id)
                    else:
                        # Module too difficult, include but flag for review
                        adapted_modules.append(module_id)

            # Recalculate metrics
            total_duration = sum(
                self.prerequisite_manager.modules[m].skill.estimated_time
                for m in adapted_modules
                if m in self.prerequisite_manager.modules
            )

            difficulty_progression = [
                self.prerequisite_manager.modules[m].difficulty_score
                for m in adapted_modules
                if m in self.prerequisite_manager.modules
            ]

            # Create adapted path
            adapted_path = LearningPath(
                path_id=generate_id("path"),
                learner_id=learner_profile.learner_id,
                modules=adapted_modules,
                estimated_duration=total_duration,
                difficulty_progression=difficulty_progression,
                prerequisites_satisfied=True,
                metadata={
                    "optimization_type": "adaptive",
                    "base_path_id": base_path.path_id,
                    "learner_difficulty": current_difficulty,
                    "target_skills": target_skills,
                    "generated_at": datetime.now().isoformat()
                }
            )

            LOGGER.info(f"Generated adaptive path with {len(adapted_modules)} modules")

            return adapted_path

        except Exception as e:
            LOGGER.error(f"Error generating adaptive path: {str(e)}")
            return None

    def find_alternative_paths(
        self,
        learner_profile: LearnerProfile,
        target_skill: str,
        max_alternatives: int = 3
    ) -> List[LearningPath]:
        """
        Find alternative learning paths to reach a target skill.

        Args:
            learner_profile: Learner's profile
            target_skill: Target skill/module ID
            max_alternatives: Maximum number of alternatives to generate

        Returns:
            List of alternative learning paths
        """
        alternatives = []

        try:
            # Generate paths with different optimization criteria
            criteria = ["shortest", "fastest", "easiest", "balanced"]

            for criterion in criteria[:max_alternatives]:
                path = self.generate_optimal_path(
                    learner_profile,
                    [target_skill],
                    criterion
                )
                if path:
                    alternatives.append(path)

            LOGGER.info(f"Generated {len(alternatives)} alternative paths")

        except Exception as e:
            LOGGER.error(f"Error finding alternative paths: {str(e)}")

        return alternatives

    def validate_path(self, path: LearningPath) -> Tuple[bool, List[str]]:
        """
        Validate that a learning path satisfies all prerequisites.

        Args:
            path: Learning path to validate

        Returns:
            Tuple of (is_valid, list_of_violations)
        """
        violations = []
        completed = set()

        for module_id in path.modules:
            prereqs = self.prerequisite_manager.get_prerequisites(module_id, recursive=False)
            missing = [p for p in prereqs if p not in completed]

            if missing:
                violations.append(
                    f"Module {module_id} missing prerequisites: {missing}"
                )

            completed.add(module_id)

        is_valid = len(violations) == 0

        if is_valid:
            LOGGER.info(f"Path {path.path_id} validation successful")
        else:
            LOGGER.warning(f"Path {path.path_id} has {len(violations)} violations")

        return is_valid, violations


# ============================================================================
# CORE CLASS: CURRICULUM TEMPLATE
# ============================================================================

class CurriculumTemplate:
    """
    Provides pre-built curriculum structures and templates.

    Features:
    - Template library management
    - Customizable curriculum templates
    - Template instantiation
    - Template export/import
    """

    def __init__(self):
        """Initialize the curriculum template manager."""
        self.templates: Dict[str, Dict[str, Any]] = {}
        self._initialize_default_templates()
        LOGGER.info("CurriculumTemplate initialized with default templates")

    def _initialize_default_templates(self) -> None:
        """Initialize default curriculum templates."""

        # Programming Fundamentals Template
        self.templates["programming_fundamentals"] = {
            "name": "Programming Fundamentals",
            "description": "Complete programming fundamentals curriculum",
            "skills": [
                {
                    "skill_id": "prog_001",
                    "name": "Variables and Data Types",
                    "category": "Programming",
                    "difficulty": DifficultyLevel.BEGINNER,
                    "estimated_time": 120,
                    "prerequisites": []
                },
                {
                    "skill_id": "prog_002",
                    "name": "Control Flow",
                    "category": "Programming",
                    "difficulty": DifficultyLevel.BEGINNER,
                    "estimated_time": 150,
                    "prerequisites": ["prog_001"]
                },
                {
                    "skill_id": "prog_003",
                    "name": "Functions",
                    "category": "Programming",
                    "difficulty": DifficultyLevel.ELEMENTARY,
                    "estimated_time": 180,
                    "prerequisites": ["prog_002"]
                },
                {
                    "skill_id": "prog_004",
                    "name": "Data Structures",
                    "category": "Programming",
                    "difficulty": DifficultyLevel.INTERMEDIATE,
                    "estimated_time": 240,
                    "prerequisites": ["prog_003"]
                },
                {
                    "skill_id": "prog_005",
                    "name": "Object-Oriented Programming",
                    "category": "Programming",
                    "difficulty": DifficultyLevel.INTERMEDIATE,
                    "estimated_time": 300,
                    "prerequisites": ["prog_004"]
                }
            ]
        }

        # Data Science Fundamentals Template
        self.templates["data_science_fundamentals"] = {
            "name": "Data Science Fundamentals",
            "description": "Data science and analytics curriculum",
            "skills": [
                {
                    "skill_id": "ds_001",
                    "name": "Python Basics",
                    "category": "Data Science",
                    "difficulty": DifficultyLevel.BEGINNER,
                    "estimated_time": 180,
                    "prerequisites": []
                },
                {
                    "skill_id": "ds_002",
                    "name": "Statistics Fundamentals",
                    "category": "Data Science",
                    "difficulty": DifficultyLevel.ELEMENTARY,
                    "estimated_time": 240,
                    "prerequisites": ["ds_001"]
                },
                {
                    "skill_id": "ds_003",
                    "name": "Data Manipulation",
                    "category": "Data Science",
                    "difficulty": DifficultyLevel.INTERMEDIATE,
                    "estimated_time": 300,
                    "prerequisites": ["ds_001", "ds_002"]
                },
                {
                    "skill_id": "ds_004",
                    "name": "Data Visualization",
                    "category": "Data Science",
                    "difficulty": DifficultyLevel.INTERMEDIATE,
                    "estimated_time": 240,
                    "prerequisites": ["ds_003"]
                },
                {
                    "skill_id": "ds_005",
                    "name": "Machine Learning Basics",
                    "category": "Data Science",
                    "difficulty": DifficultyLevel.ADVANCED,
                    "estimated_time": 480,
                    "prerequisites": ["ds_002", "ds_003"]
                }
            ]
        }

        # Web Development Template
        self.templates["web_development"] = {
            "name": "Web Development",
            "description": "Full-stack web development curriculum",
            "skills": [
                {
                    "skill_id": "web_001",
                    "name": "HTML & CSS",
                    "category": "Web Development",
                    "difficulty": DifficultyLevel.BEGINNER,
                    "estimated_time": 120,
                    "prerequisites": []
                },
                {
                    "skill_id": "web_002",
                    "name": "JavaScript Fundamentals",
                    "category": "Web Development",
                    "difficulty": DifficultyLevel.ELEMENTARY,
                    "estimated_time": 240,
                    "prerequisites": ["web_001"]
                },
                {
                    "skill_id": "web_003",
                    "name": "Frontend Framework",
                    "category": "Web Development",
                    "difficulty": DifficultyLevel.INTERMEDIATE,
                    "estimated_time": 360,
                    "prerequisites": ["web_002"]
                },
                {
                    "skill_id": "web_004",
                    "name": "Backend Development",
                    "category": "Web Development",
                    "difficulty": DifficultyLevel.INTERMEDIATE,
                    "estimated_time": 420,
                    "prerequisites": ["web_002"]
                },
                {
                    "skill_id": "web_005",
                    "name": "Database Design",
                    "category": "Web Development",
                    "difficulty": DifficultyLevel.ADVANCED,
                    "estimated_time": 300,
                    "prerequisites": ["web_004"]
                }
            ]
        }

    def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a curriculum template by ID.

        Args:
            template_id: ID of the template

        Returns:
            Template dictionary or None if not found
        """
        return self.templates.get(template_id)

    def list_templates(self) -> List[Dict[str, str]]:
        """
        List all available templates.

        Returns:
            List of template summaries
        """
        return [
            {
                "template_id": tid,
                "name": template["name"],
                "description": template["description"],
                "num_skills": len(template["skills"])
            }
            for tid, template in self.templates.items()
        ]

    def create_custom_template(
        self,
        template_id: str,
        name: str,
        description: str,
        skills: List[Dict[str, Any]]
    ) -> bool:
        """
        Create a custom curriculum template.

        Args:
            template_id: Unique template ID
            name: Template name
            description: Template description
            skills: List of skill definitions

        Returns:
            True if successful, False otherwise
        """
        try:
            if template_id in self.templates:
                LOGGER.warning(f"Template {template_id} already exists")
                return False

            self.templates[template_id] = {
                "name": name,
                "description": description,
                "skills": skills
            }

            LOGGER.info(f"Created custom template: {template_id}")
            return True

        except Exception as e:
            LOGGER.error(f"Error creating template: {str(e)}")
            return False

    def instantiate_template(
        self,
        template_id: str,
        prerequisite_manager: PrerequisiteManager
    ) -> bool:
        """
        Instantiate a template into actual learning modules.

        Args:
            template_id: ID of the template to instantiate
            prerequisite_manager: Prerequisite manager to add modules to

        Returns:
            True if successful, False otherwise
        """
        try:
            template = self.get_template(template_id)
            if not template:
                LOGGER.error(f"Template {template_id} not found")
                return False

            # Create modules from template
            for skill_data in template["skills"]:
                difficulty = skill_data.get("difficulty", DifficultyLevel.INTERMEDIATE)

                skill = Skill(
                    skill_id=skill_data["skill_id"],
                    name=skill_data["name"],
                    description=skill_data.get("description", ""),
                    category=skill_data["category"],
                    difficulty=difficulty,
                    estimated_time=skill_data.get("estimated_time", 60),
                    tags=skill_data.get("tags", []),
                    metadata=skill_data.get("metadata", {})
                )

                # Convert DifficultyLevel to score (1-5 -> 0.2-1.0)
                difficulty_score = difficulty.value / 5.0

                module = LearningModule(
                    module_id=skill_data["skill_id"],
                    skill=skill,
                    prerequisites=skill_data.get("prerequisites", []),
                    difficulty_score=difficulty_score
                )

                prerequisite_manager.add_module(module)

            LOGGER.info(f"Instantiated template {template_id}: {len(template['skills'])} modules")
            return True

        except Exception as e:
            LOGGER.error(f"Error instantiating template: {str(e)}")
            return False

    def export_template(self, template_id: str, file_path: Path) -> bool:
        """
        Export a template to JSON file.

        Args:
            template_id: ID of the template
            file_path: Path to export file

        Returns:
            True if successful, False otherwise
        """
        try:
            template = self.get_template(template_id)
            if not template:
                LOGGER.error(f"Template {template_id} not found")
                return False

            json_content = json.dumps(template, indent=2, default=str)
            return SubprocessExecutor.write_file(file_path, json_content)

        except Exception as e:
            LOGGER.error(f"Error exporting template: {str(e)}")
            return False

    def import_template(self, template_id: str, file_path: Path) -> bool:
        """
        Import a template from JSON file.

        Args:
            template_id: ID for the imported template
            file_path: Path to import file

        Returns:
            True if successful, False otherwise
        """
        try:
            content = SubprocessExecutor.read_file(file_path)
            if not content:
                LOGGER.error(f"Failed to read template file: {file_path}")
                return False

            template_data = json.loads(content)
            self.templates[template_id] = template_data

            LOGGER.info(f"Imported template: {template_id}")
            return True

        except Exception as e:
            LOGGER.error(f"Error importing template: {str(e)}")
            return False


# ============================================================================
# MAIN CLASS: CURRICULUM LEARNING SEQUENCER
# ============================================================================

class CurriculumLearningSequencer:
    """
    Main orchestrator for curriculum learning and sequencing.

    This class coordinates all components to provide complete curriculum
    management functionality including:
    - Learning path generation
    - Progress tracking
    - Difficulty adaptation
    - Prerequisite management
    - Curriculum optimization
    """

    def __init__(
        self,
        config: Optional[CurriculumConfig] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the curriculum learning sequencer.

        Args:
            config: Configuration object
            logger: Logger instance
        """
        self.config = config or CurriculumConfig()
        self.logger = logger or LOGGER

        # Initialize components
        self.prerequisite_manager = PrerequisiteManager()
        self.difficulty_scaler = DifficultyScaler()
        self.progress_tracker = ProgressTracker()
        self.path_optimizer = PathOptimizer(self.prerequisite_manager)
        self.curriculum_template = CurriculumTemplate()

        # Initialize storage
        self.learner_profiles: Dict[str, LearnerProfile] = {}
        self.learning_paths: Dict[str, LearningPath] = {}

        # Setup directories
        self.config.setup_directories()

        self.logger.info("CurriculumLearningSequencer initialized successfully")

    # ========================================================================
    # LEARNER MANAGEMENT
    # ========================================================================

    def create_learner(
        self,
        name: str,
        learning_style: LearningStyle = LearningStyle.MIXED,
        preferences: Optional[Dict[str, Any]] = None
    ) -> LearnerProfile:
        """
        Create a new learner profile.

        Args:
            name: Learner's name
            learning_style: Preferred learning style
            preferences: Additional preferences

        Returns:
            Created learner profile
        """
        learner_id = generate_id("learner")

        profile = LearnerProfile(
            learner_id=learner_id,
            name=name,
            learning_style=learning_style,
            preferences=preferences or {}
        )

        self.learner_profiles[learner_id] = profile
        self.logger.info(f"Created learner profile: {learner_id}")

        return profile

    def get_learner(self, learner_id: str) -> Optional[LearnerProfile]:
        """Get a learner profile by ID."""
        return self.learner_profiles.get(learner_id)

    def update_learner_profile(
        self,
        learner_id: str,
        **updates
    ) -> bool:
        """
        Update a learner's profile.

        Args:
            learner_id: ID of the learner
            **updates: Fields to update

        Returns:
            True if successful, False otherwise
        """
        profile = self.get_learner(learner_id)
        if not profile:
            self.logger.error(f"Learner {learner_id} not found")
            return False

        for key, value in updates.items():
            if hasattr(profile, key):
                setattr(profile, key, value)

        profile.updated_at = datetime.now()
        self.logger.info(f"Updated learner profile: {learner_id}")

        return True

    # ========================================================================
    # MODULE AND CURRICULUM MANAGEMENT
    # ========================================================================

    def add_module(self, module: LearningModule) -> bool:
        """
        Add a learning module to the curriculum.

        Args:
            module: Learning module to add

        Returns:
            True if successful, False otherwise
        """
        try:
            self.prerequisite_manager.add_module(module)
            self.logger.info(f"Added module: {module.module_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error adding module: {str(e)}")
            return False

    def load_template(self, template_id: str) -> bool:
        """
        Load a curriculum template.

        Args:
            template_id: ID of the template to load

        Returns:
            True if successful, False otherwise
        """
        return self.curriculum_template.instantiate_template(
            template_id,
            self.prerequisite_manager
        )

    def get_available_templates(self) -> List[Dict[str, str]]:
        """Get list of available curriculum templates."""
        return self.curriculum_template.list_templates()

    # ========================================================================
    # LEARNING PATH GENERATION
    # ========================================================================

    def generate_learning_path(
        self,
        learner_id: str,
        target_skills: List[str],
        adaptive: bool = True
    ) -> Optional[LearningPath]:
        """
        Generate an optimized learning path for a learner.

        Args:
            learner_id: ID of the learner
            target_skills: List of target skill/module IDs
            adaptive: Whether to use adaptive difficulty

        Returns:
            Generated learning path or None if failed
        """
        profile = self.get_learner(learner_id)
        if not profile:
            self.logger.error(f"Learner {learner_id} not found")
            return None

        if adaptive:
            path = self.path_optimizer.generate_adaptive_path(
                profile,
                target_skills,
                self.difficulty_scaler
            )
        else:
            path = self.path_optimizer.generate_optimal_path(
                profile,
                target_skills
            )

        if path:
            self.learning_paths[path.path_id] = path
            self.logger.info(f"Generated learning path: {path.path_id}")

        return path

    def get_next_module(self, learner_id: str) -> Optional[str]:
        """
        Get the next recommended module for a learner.

        Args:
            learner_id: ID of the learner

        Returns:
            Next module ID or None
        """
        profile = self.get_learner(learner_id)
        if not profile:
            return None

        # Get all modules sorted topologically
        sorted_modules = self.prerequisite_manager.topological_sort()

        # Filter to incomplete modules
        completed = set(profile.completed_modules)
        incomplete = [m for m in sorted_modules if m not in completed]

        # Find first module with satisfied prerequisites
        for module_id in incomplete:
            satisfied, _ = self.prerequisite_manager.validate_prerequisites(
                module_id,
                completed
            )
            if satisfied:
                return module_id

        return None

    # ========================================================================
    # PROGRESS TRACKING
    # ========================================================================

    def start_module(
        self,
        learner_id: str,
        module_id: str
    ) -> Optional[ProgressRecord]:
        """
        Start tracking progress on a module.

        Args:
            learner_id: ID of the learner
            module_id: ID of the module

        Returns:
            Created progress record or None
        """
        profile = self.get_learner(learner_id)
        if not profile:
            self.logger.error(f"Learner {learner_id} not found")
            return None

        module = self.prerequisite_manager.modules.get(module_id)
        if not module:
            self.logger.error(f"Module {module_id} not found")
            return None

        # Validate prerequisites
        satisfied, missing = self.prerequisite_manager.validate_prerequisites(
            module_id,
            set(profile.completed_modules)
        )

        if not satisfied:
            self.logger.warning(
                f"Prerequisites not satisfied for module {module_id}: {missing}"
            )

        # Create progress record
        record = ProgressRecord(
            record_id=generate_id("progress"),
            learner_id=learner_id,
            module_id=module_id,
            start_time=datetime.now(),
            total_assessments=len(module.assessments)
        )

        self.progress_tracker.record_progress(record)

        # Update profile
        if module_id not in profile.in_progress_modules:
            profile.in_progress_modules.append(module_id)

        return record

    def complete_module(
        self,
        learner_id: str,
        module_id: str,
        score: float,
        time_spent: int
    ) -> bool:
        """
        Mark a module as completed.

        Args:
            learner_id: ID of the learner
            module_id: ID of the module
            score: Completion score (0.0-1.0)
            time_spent: Time spent in minutes

        Returns:
            True if successful, False otherwise
        """
        try:
            profile = self.get_learner(learner_id)
            if not profile:
                return False

            # Get progress record
            records = self.progress_tracker.get_learner_progress(learner_id)
            module_records = [r for r in records if r.module_id == module_id]

            if not module_records:
                self.logger.error(f"No progress record found for module {module_id}")
                return False

            # Update most recent record
            record = module_records[-1]
            record.completion_time = datetime.now()
            record.score = score
            record.time_spent = time_spent

            # Update profile
            if module_id in profile.in_progress_modules:
                profile.in_progress_modules.remove(module_id)

            if module_id not in profile.completed_modules:
                profile.completed_modules.append(module_id)

            # Update difficulty
            current_difficulty = self.difficulty_scaler.get_learner_difficulty(learner_id)
            new_difficulty = self.difficulty_scaler.calculate_difficulty(
                current_difficulty,
                score,
                current_difficulty
            )
            self.difficulty_scaler.update_learner_difficulty(learner_id, new_difficulty)

            self.logger.info(
                f"Completed module {module_id} for learner {learner_id} "
                f"(score: {score:.2f})"
            )

            return True

        except Exception as e:
            self.logger.error(f"Error completing module: {str(e)}")
            return False

    def get_learner_progress_report(self, learner_id: str) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive progress report for a learner.

        Args:
            learner_id: ID of the learner

        Returns:
            Progress report dictionary or None
        """
        profile = self.get_learner(learner_id)
        if not profile:
            return None

        report = self.progress_tracker.generate_progress_report(learner_id)
        report["profile"] = profile.to_dict()

        return report

    # ========================================================================
    # EXPORT AND VISUALIZATION
    # ========================================================================

    def export_curriculum(self, file_path: Path) -> bool:
        """
        Export complete curriculum to JSON file.

        Args:
            file_path: Path to export file

        Returns:
            True if successful, False otherwise
        """
        try:
            curriculum_data = {
                "modules": {
                    mid: module.to_dict()
                    for mid, module in self.prerequisite_manager.modules.items()
                },
                "learners": {
                    lid: learner.to_dict()
                    for lid, learner in self.learner_profiles.items()
                },
                "learning_paths": {
                    pid: path.to_dict()
                    for pid, path in self.learning_paths.items()
                },
                "exported_at": datetime.now().isoformat()
            }

            json_content = json.dumps(curriculum_data, indent=2)
            return SubprocessExecutor.write_file(file_path, json_content)

        except Exception as e:
            self.logger.error(f"Error exporting curriculum: {str(e)}")
            return False

    def export_learner_report(
        self,
        learner_id: str,
        file_path: Path,
        format: str = "json"
    ) -> bool:
        """
        Export learner report to file.

        Args:
            learner_id: ID of the learner
            file_path: Path to export file
            format: Export format ("json" or "text")

        Returns:
            True if successful, False otherwise
        """
        try:
            report = self.get_learner_progress_report(learner_id)
            if not report:
                return False

            if format == "json":
                content = json.dumps(report, indent=2)
            elif format == "text":
                content = self._format_report_as_text(report)
            else:
                self.logger.error(f"Unknown format: {format}")
                return False

            return SubprocessExecutor.write_file(file_path, content)

        except Exception as e:
            self.logger.error(f"Error exporting learner report: {str(e)}")
            return False

    def _format_report_as_text(self, report: Dict[str, Any]) -> str:
        """Format progress report as human-readable text."""
        lines = [
            "=" * 80,
            "LEARNER PROGRESS REPORT",
            "=" * 80,
            "",
            f"Learner ID: {report['learner_id']}",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "SUMMARY",
            "-" * 80,
            f"Total Modules Attempted: {report['total_modules_attempted']}",
            f"Modules Completed: {report['modules_completed']}",
            f"Modules In Progress: {report['modules_in_progress']}",
            f"Average Score: {report['average_score']:.2%}",
            f"Total Time Spent: {report['total_time_spent_minutes']} minutes",
            f"Learning Velocity: {report['learning_velocity']:.2f} modules/day",
            "",
            "MASTERED MODULES",
            "-" * 80,
        ]

        for module_id in report['mastered_modules']:
            lines.append(f"  - {module_id}")

        if report['struggling_modules']:
            lines.extend([
                "",
                "STRUGGLING MODULES",
                "-" * 80,
            ])
            for module_id in report['struggling_modules']:
                lines.append(f"  - {module_id}")

        lines.extend([
            "",
            "RECENT ACTIVITY",
            "-" * 80,
        ])

        for activity in report['recent_activity']:
            lines.append(
                f"  - {activity['module_id']}: "
                f"Score {activity['score']:.2%} "
                f"({activity['completion_time'] or 'In Progress'})"
            )

        lines.extend(["", "=" * 80])

        return "\n".join(lines)

    def generate_visualization_data(self, learner_id: str) -> Dict[str, Any]:
        """
        Generate data for curriculum visualization.

        Args:
            learner_id: ID of the learner

        Returns:
            Visualization data dictionary
        """
        profile = self.get_learner(learner_id)
        if not profile:
            return {}

        # Get dependency graph
        levels = self.prerequisite_manager.get_learning_levels()

        # Get progress data
        progress = self.progress_tracker.get_learner_progress(learner_id)

        # Build visualization data
        viz_data = {
            "nodes": [],
            "edges": [],
            "levels": {}
        }

        # Add nodes (modules)
        for level, module_ids in levels.items():
            viz_data["levels"][level] = []
            for module_id in module_ids:
                module = self.prerequisite_manager.modules.get(module_id)
                if module:
                    node = {
                        "id": module_id,
                        "name": module.skill.name,
                        "level": level,
                        "difficulty": module.difficulty_score,
                        "status": "completed" if module_id in profile.completed_modules else "incomplete"
                    }
                    viz_data["nodes"].append(node)
                    viz_data["levels"][level].append(module_id)

        # Add edges (dependencies)
        for module_id, prereqs in self.prerequisite_manager.dependencies.items():
            for prereq in prereqs:
                viz_data["edges"].append({
                    "from": prereq,
                    "to": module_id
                })

        return viz_data


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main entry point for demonstration."""
    print("=" * 80)
    print("FSA-8: CURRICULUM LEARNING SEQUENCER")
    print("=" * 80)
    print()

    # Initialize sequencer
    sequencer = CurriculumLearningSequencer()

    # Load a template curriculum
    print("Loading programming fundamentals template...")
    sequencer.load_template("programming_fundamentals")

    # Create a learner
    print("Creating learner profile...")
    learner = sequencer.create_learner("John Doe", LearningStyle.VISUAL)
    print(f"Created learner: {learner.learner_id}")
    print()

    # Generate learning path
    print("Generating learning path...")
    path = sequencer.generate_learning_path(
        learner.learner_id,
        ["prog_005"],  # Target: OOP
        adaptive=True
    )

    if path:
        print(f"Generated path with {len(path.modules)} modules")
        print(f"Estimated duration: {path.estimated_duration} minutes")
        print(f"Modules: {' -> '.join(path.modules)}")
    print()

    # Get available templates
    print("Available curriculum templates:")
    templates = sequencer.get_available_templates()
    for template in templates:
        print(f"  - {template['name']}: {template['description']}")
    print()

    # Export curriculum
    export_path = CurriculumConfig.EXPORT_DIR / "curriculum_export.json"
    print(f"Exporting curriculum to: {export_path}")
    sequencer.export_curriculum(export_path)

    print()
    print("=" * 80)
    print("Demonstration complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()

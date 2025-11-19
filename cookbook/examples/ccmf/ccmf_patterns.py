"""
CCMF Pattern Library - SESSION 1
=================================

This module defines cognitive access patterns for the CCMF framework.
Each pattern represents a specific strategy for accessing, processing,
or managing information in AI workflows.

Patterns included:
- DirectPathAccessPattern: Direct file/resource access
- KnownPathSearchPattern: Search in known locations
- GitRepositoryFilePattern: Git repository file access
- CheckpointRecoveryPattern: State checkpoint and recovery
- GitStateAnalysisPattern: Git state analysis and tracking
- CompositeStateRecoveryPattern: Multi-source state recovery
"""

import os
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from pathlib import Path
from datetime import datetime
import json
import hashlib


@dataclass
class PatternResult:
    """Result of a pattern execution."""
    success: bool
    pattern_name: str
    data: Any
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    execution_time: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            'success': self.success,
            'pattern_name': self.pattern_name,
            'data': self.data,
            'metadata': self.metadata,
            'error': self.error,
            'execution_time': self.execution_time,
            'timestamp': self.timestamp.isoformat()
        }


class CognitivePattern(ABC):
    """Base class for all cognitive patterns."""

    def __init__(self, name: str, description: str):
        """Initialize the pattern."""
        self.name = name
        self.description = description
        self.execution_count = 0
        self.success_count = 0
        self.failure_count = 0

    @abstractmethod
    def execute(self, **kwargs) -> PatternResult:
        """Execute the pattern."""
        pass

    def _record_execution(self, result: PatternResult):
        """Record execution statistics."""
        self.execution_count += 1
        if result.success:
            self.success_count += 1
        else:
            self.failure_count += 1

    def get_stats(self) -> Dict[str, Any]:
        """Get pattern execution statistics."""
        success_rate = (self.success_count / self.execution_count * 100
                       if self.execution_count > 0 else 0.0)
        return {
            'name': self.name,
            'executions': self.execution_count,
            'successes': self.success_count,
            'failures': self.failure_count,
            'success_rate': success_rate
        }


class DirectPathAccessPattern(CognitivePattern):
    """
    Direct path access pattern for known file/resource locations.

    This pattern is used when the exact path to a resource is known
    and direct access is the most efficient approach.
    """

    def __init__(self):
        super().__init__(
            name="DirectPathAccessPattern",
            description="Direct access to files/resources at known paths"
        )

    def execute(self, path: str, operation: str = "read", **kwargs) -> PatternResult:
        """
        Execute direct path access.

        Args:
            path: Path to the resource
            operation: Operation type ('read', 'exists', 'stat')
            **kwargs: Additional operation-specific parameters

        Returns:
            PatternResult with the operation result
        """
        import time
        start_time = time.time()

        try:
            path_obj = Path(path)

            if operation == "exists":
                data = path_obj.exists()
                metadata = {'path': str(path), 'operation': operation}

            elif operation == "stat":
                if not path_obj.exists():
                    raise FileNotFoundError(f"Path not found: {path}")
                stat = path_obj.stat()
                data = {
                    'size': stat.st_size,
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    'is_file': path_obj.is_file(),
                    'is_dir': path_obj.is_dir()
                }
                metadata = {'path': str(path), 'operation': operation}

            elif operation == "read":
                if not path_obj.exists():
                    raise FileNotFoundError(f"File not found: {path}")
                if not path_obj.is_file():
                    raise ValueError(f"Not a file: {path}")

                encoding = kwargs.get('encoding', 'utf-8')
                with open(path_obj, 'r', encoding=encoding) as f:
                    data = f.read()
                metadata = {
                    'path': str(path),
                    'operation': operation,
                    'size': len(data),
                    'encoding': encoding
                }

            else:
                raise ValueError(f"Unknown operation: {operation}")

            execution_time = time.time() - start_time
            result = PatternResult(
                success=True,
                pattern_name=self.name,
                data=data,
                metadata=metadata,
                execution_time=execution_time
            )

        except Exception as e:
            execution_time = time.time() - start_time
            result = PatternResult(
                success=False,
                pattern_name=self.name,
                data=None,
                error=str(e),
                execution_time=execution_time
            )

        self._record_execution(result)
        return result


class KnownPathSearchPattern(CognitivePattern):
    """
    Search pattern for finding files in known directory structures.

    This pattern searches through predefined paths and directories
    to locate resources based on name patterns or criteria.
    """

    def __init__(self):
        super().__init__(
            name="KnownPathSearchPattern",
            description="Search for files in known directory structures"
        )

    def execute(
        self,
        search_paths: List[str],
        pattern: str,
        recursive: bool = True,
        **kwargs
    ) -> PatternResult:
        """
        Execute path search.

        Args:
            search_paths: List of paths to search
            pattern: File pattern to match (e.g., "*.py", "config.*")
            recursive: Whether to search recursively
            **kwargs: Additional search parameters

        Returns:
            PatternResult with list of matching files
        """
        import time
        import fnmatch
        start_time = time.time()

        try:
            matches = []

            for search_path in search_paths:
                path_obj = Path(search_path)
                if not path_obj.exists():
                    continue

                if recursive:
                    for root, dirs, files in os.walk(path_obj):
                        for filename in files:
                            if fnmatch.fnmatch(filename, pattern):
                                matches.append(str(Path(root) / filename))
                else:
                    if path_obj.is_dir():
                        for item in path_obj.iterdir():
                            if item.is_file() and fnmatch.fnmatch(item.name, pattern):
                                matches.append(str(item))

            execution_time = time.time() - start_time
            result = PatternResult(
                success=True,
                pattern_name=self.name,
                data=matches,
                metadata={
                    'search_paths': search_paths,
                    'pattern': pattern,
                    'recursive': recursive,
                    'matches_found': len(matches)
                },
                execution_time=execution_time
            )

        except Exception as e:
            execution_time = time.time() - start_time
            result = PatternResult(
                success=False,
                pattern_name=self.name,
                data=[],
                error=str(e),
                execution_time=execution_time
            )

        self._record_execution(result)
        return result


class GitRepositoryFilePattern(CognitivePattern):
    """
    Pattern for accessing files within Git repositories.

    This pattern provides Git-aware file access, including
    version history, branch awareness, and repository state.
    """

    def __init__(self):
        super().__init__(
            name="GitRepositoryFilePattern",
            description="Git-aware file access and repository operations"
        )

    def execute(
        self,
        repo_path: str,
        operation: str = "status",
        file_path: Optional[str] = None,
        **kwargs
    ) -> PatternResult:
        """
        Execute Git repository operation.

        Args:
            repo_path: Path to Git repository
            operation: Operation type ('status', 'log', 'show', 'diff')
            file_path: Optional specific file path
            **kwargs: Additional operation parameters

        Returns:
            PatternResult with operation data
        """
        import time
        start_time = time.time()

        try:
            repo_path_obj = Path(repo_path)
            if not repo_path_obj.exists():
                raise ValueError(f"Repository path not found: {repo_path}")

            # Check if it's a git repository
            git_dir = repo_path_obj / ".git"
            if not git_dir.exists():
                raise ValueError(f"Not a git repository: {repo_path}")

            if operation == "status":
                cmd = ["git", "-C", str(repo_path_obj), "status", "--short"]
                result_output = subprocess.check_output(cmd, text=True)
                data = {
                    'raw_output': result_output,
                    'has_changes': bool(result_output.strip())
                }

            elif operation == "log":
                limit = kwargs.get('limit', 10)
                cmd = ["git", "-C", str(repo_path_obj), "log",
                       f"--max-count={limit}", "--oneline"]
                if file_path:
                    cmd.append("--")
                    cmd.append(file_path)
                result_output = subprocess.check_output(cmd, text=True)
                data = {
                    'commits': result_output.strip().split('\n') if result_output.strip() else [],
                    'file_path': file_path
                }

            elif operation == "show":
                if not file_path:
                    raise ValueError("file_path required for 'show' operation")
                ref = kwargs.get('ref', 'HEAD')
                cmd = ["git", "-C", str(repo_path_obj), "show",
                       f"{ref}:{file_path}"]
                result_output = subprocess.check_output(cmd, text=True)
                data = {
                    'content': result_output,
                    'file_path': file_path,
                    'ref': ref
                }

            elif operation == "diff":
                cmd = ["git", "-C", str(repo_path_obj), "diff"]
                if file_path:
                    cmd.append("--")
                    cmd.append(file_path)
                result_output = subprocess.check_output(cmd, text=True)
                data = {
                    'diff': result_output,
                    'file_path': file_path,
                    'has_changes': bool(result_output.strip())
                }

            else:
                raise ValueError(f"Unknown operation: {operation}")

            execution_time = time.time() - start_time
            result = PatternResult(
                success=True,
                pattern_name=self.name,
                data=data,
                metadata={
                    'repo_path': str(repo_path_obj),
                    'operation': operation,
                    'file_path': file_path
                },
                execution_time=execution_time
            )

        except subprocess.CalledProcessError as e:
            execution_time = time.time() - start_time
            result = PatternResult(
                success=False,
                pattern_name=self.name,
                data=None,
                error=f"Git command failed: {e}",
                execution_time=execution_time
            )

        except Exception as e:
            execution_time = time.time() - start_time
            result = PatternResult(
                success=False,
                pattern_name=self.name,
                data=None,
                error=str(e),
                execution_time=execution_time
            )

        self._record_execution(result)
        return result


@dataclass
class Checkpoint:
    """Represents a state checkpoint."""
    checkpoint_id: str
    timestamp: datetime
    state_data: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert checkpoint to dictionary."""
        return {
            'checkpoint_id': self.checkpoint_id,
            'timestamp': self.timestamp.isoformat(),
            'state_data': self.state_data,
            'metadata': self.metadata
        }


class CheckpointRecoveryPattern(CognitivePattern):
    """
    Pattern for creating and recovering from state checkpoints.

    This pattern enables saving system state at key points and
    recovering to those states when needed.
    """

    def __init__(self, checkpoint_dir: str = ".ccmf_checkpoints"):
        super().__init__(
            name="CheckpointRecoveryPattern",
            description="State checkpoint creation and recovery"
        )
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def execute(
        self,
        operation: str,
        checkpoint_id: Optional[str] = None,
        state_data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> PatternResult:
        """
        Execute checkpoint operation.

        Args:
            operation: Operation type ('save', 'load', 'list', 'delete')
            checkpoint_id: Checkpoint identifier
            state_data: State data to save (for 'save' operation)
            **kwargs: Additional parameters

        Returns:
            PatternResult with operation result
        """
        import time
        start_time = time.time()

        try:
            if operation == "save":
                if not state_data:
                    raise ValueError("state_data required for 'save' operation")

                # Generate checkpoint ID if not provided
                if not checkpoint_id:
                    checkpoint_id = f"checkpoint_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

                checkpoint = Checkpoint(
                    checkpoint_id=checkpoint_id,
                    timestamp=datetime.now(),
                    state_data=state_data,
                    metadata=kwargs.get('metadata', {})
                )

                # Save checkpoint
                checkpoint_file = self.checkpoint_dir / f"{checkpoint_id}.json"
                with open(checkpoint_file, 'w') as f:
                    json.dump(checkpoint.to_dict(), f, indent=2)

                data = {
                    'checkpoint_id': checkpoint_id,
                    'file_path': str(checkpoint_file),
                    'saved_at': checkpoint.timestamp.isoformat()
                }

            elif operation == "load":
                if not checkpoint_id:
                    raise ValueError("checkpoint_id required for 'load' operation")

                checkpoint_file = self.checkpoint_dir / f"{checkpoint_id}.json"
                if not checkpoint_file.exists():
                    raise FileNotFoundError(f"Checkpoint not found: {checkpoint_id}")

                with open(checkpoint_file, 'r') as f:
                    checkpoint_data = json.load(f)

                data = checkpoint_data

            elif operation == "list":
                checkpoints = []
                for checkpoint_file in self.checkpoint_dir.glob("*.json"):
                    with open(checkpoint_file, 'r') as f:
                        checkpoint_data = json.load(f)
                        checkpoints.append({
                            'checkpoint_id': checkpoint_data['checkpoint_id'],
                            'timestamp': checkpoint_data['timestamp'],
                            'metadata': checkpoint_data.get('metadata', {})
                        })

                checkpoints.sort(key=lambda x: x['timestamp'], reverse=True)
                data = {'checkpoints': checkpoints, 'count': len(checkpoints)}

            elif operation == "delete":
                if not checkpoint_id:
                    raise ValueError("checkpoint_id required for 'delete' operation")

                checkpoint_file = self.checkpoint_dir / f"{checkpoint_id}.json"
                if not checkpoint_file.exists():
                    raise FileNotFoundError(f"Checkpoint not found: {checkpoint_id}")

                checkpoint_file.unlink()
                data = {'checkpoint_id': checkpoint_id, 'deleted': True}

            else:
                raise ValueError(f"Unknown operation: {operation}")

            execution_time = time.time() - start_time
            result = PatternResult(
                success=True,
                pattern_name=self.name,
                data=data,
                metadata={'operation': operation},
                execution_time=execution_time
            )

        except Exception as e:
            execution_time = time.time() - start_time
            result = PatternResult(
                success=False,
                pattern_name=self.name,
                data=None,
                error=str(e),
                execution_time=execution_time
            )

        self._record_execution(result)
        return result


class GitStateAnalysisPattern(CognitivePattern):
    """
    Pattern for analyzing Git repository state.

    Provides comprehensive analysis of repository state including
    branches, commits, changes, and statistics.
    """

    def __init__(self):
        super().__init__(
            name="GitStateAnalysisPattern",
            description="Comprehensive Git repository state analysis"
        )

    def execute(self, repo_path: str, **kwargs) -> PatternResult:
        """
        Execute Git state analysis.

        Args:
            repo_path: Path to Git repository
            **kwargs: Additional analysis parameters

        Returns:
            PatternResult with analysis data
        """
        import time
        start_time = time.time()

        try:
            repo_path_obj = Path(repo_path)
            if not repo_path_obj.exists():
                raise ValueError(f"Repository path not found: {repo_path}")

            git_dir = repo_path_obj / ".git"
            if not git_dir.exists():
                raise ValueError(f"Not a git repository: {repo_path}")

            analysis = {}

            # Current branch
            cmd = ["git", "-C", str(repo_path_obj), "branch", "--show-current"]
            analysis['current_branch'] = subprocess.check_output(cmd, text=True).strip()

            # Status
            cmd = ["git", "-C", str(repo_path_obj), "status", "--short"]
            status_output = subprocess.check_output(cmd, text=True)
            analysis['has_uncommitted_changes'] = bool(status_output.strip())
            analysis['status_summary'] = status_output.strip()

            # Recent commits
            cmd = ["git", "-C", str(repo_path_obj), "log", "--max-count=5", "--oneline"]
            commits_output = subprocess.check_output(cmd, text=True)
            analysis['recent_commits'] = commits_output.strip().split('\n') if commits_output.strip() else []

            # Remote info
            try:
                cmd = ["git", "-C", str(repo_path_obj), "remote", "-v"]
                remotes_output = subprocess.check_output(cmd, text=True)
                analysis['remotes'] = remotes_output.strip().split('\n') if remotes_output.strip() else []
            except subprocess.CalledProcessError:
                analysis['remotes'] = []

            # Commit count
            try:
                cmd = ["git", "-C", str(repo_path_obj), "rev-list", "--count", "HEAD"]
                count_output = subprocess.check_output(cmd, text=True)
                analysis['total_commits'] = int(count_output.strip())
            except subprocess.CalledProcessError:
                analysis['total_commits'] = 0

            execution_time = time.time() - start_time
            result = PatternResult(
                success=True,
                pattern_name=self.name,
                data=analysis,
                metadata={'repo_path': str(repo_path_obj)},
                execution_time=execution_time
            )

        except Exception as e:
            execution_time = time.time() - start_time
            result = PatternResult(
                success=False,
                pattern_name=self.name,
                data=None,
                error=str(e),
                execution_time=execution_time
            )

        self._record_execution(result)
        return result


class CompositeStateRecoveryPattern(CognitivePattern):
    """
    Pattern for multi-source state recovery.

    Combines multiple recovery strategies (checkpoints, Git state, file state)
    to provide robust state recovery capabilities.
    """

    def __init__(self, checkpoint_dir: str = ".ccmf_checkpoints"):
        super().__init__(
            name="CompositeStateRecoveryPattern",
            description="Multi-source state recovery with fallback strategies"
        )
        self.checkpoint_pattern = CheckpointRecoveryPattern(checkpoint_dir)
        self.git_pattern = GitStateAnalysisPattern()

    def execute(
        self,
        repo_path: str,
        recovery_sources: List[str] = None,
        **kwargs
    ) -> PatternResult:
        """
        Execute composite state recovery.

        Args:
            repo_path: Path to repository
            recovery_sources: List of sources to attempt ('checkpoint', 'git', 'filesystem')
            **kwargs: Additional parameters

        Returns:
            PatternResult with recovered state
        """
        import time
        start_time = time.time()

        if recovery_sources is None:
            recovery_sources = ['checkpoint', 'git', 'filesystem']

        try:
            recovered_state = {
                'sources': {},
                'recovery_timestamp': datetime.now().isoformat()
            }

            # Try checkpoint recovery
            if 'checkpoint' in recovery_sources:
                checkpoint_result = self.checkpoint_pattern.execute(operation='list')
                if checkpoint_result.success and checkpoint_result.data['count'] > 0:
                    latest_checkpoint = checkpoint_result.data['checkpoints'][0]
                    load_result = self.checkpoint_pattern.execute(
                        operation='load',
                        checkpoint_id=latest_checkpoint['checkpoint_id']
                    )
                    if load_result.success:
                        recovered_state['sources']['checkpoint'] = {
                            'success': True,
                            'data': load_result.data
                        }

            # Try Git state recovery
            if 'git' in recovery_sources:
                git_result = self.git_pattern.execute(repo_path=repo_path)
                if git_result.success:
                    recovered_state['sources']['git'] = {
                        'success': True,
                        'data': git_result.data
                    }

            # Try filesystem state recovery
            if 'filesystem' in recovery_sources:
                try:
                    repo_path_obj = Path(repo_path)
                    if repo_path_obj.exists():
                        fs_state = {
                            'path': str(repo_path_obj),
                            'exists': True,
                            'is_dir': repo_path_obj.is_dir(),
                            'files_count': len(list(repo_path_obj.rglob('*'))) if repo_path_obj.is_dir() else 0
                        }
                        recovered_state['sources']['filesystem'] = {
                            'success': True,
                            'data': fs_state
                        }
                except Exception as e:
                    recovered_state['sources']['filesystem'] = {
                        'success': False,
                        'error': str(e)
                    }

            execution_time = time.time() - start_time
            result = PatternResult(
                success=True,
                pattern_name=self.name,
                data=recovered_state,
                metadata={
                    'repo_path': repo_path,
                    'recovery_sources': recovery_sources,
                    'sources_attempted': len(recovery_sources),
                    'sources_succeeded': sum(1 for s in recovered_state['sources'].values() if s.get('success', False))
                },
                execution_time=execution_time
            )

        except Exception as e:
            execution_time = time.time() - start_time
            result = PatternResult(
                success=False,
                pattern_name=self.name,
                data=None,
                error=str(e),
                execution_time=execution_time
            )

        self._record_execution(result)
        return result


# Pattern registry
PATTERN_REGISTRY = {
    'DirectPathAccessPattern': DirectPathAccessPattern,
    'KnownPathSearchPattern': KnownPathSearchPattern,
    'GitRepositoryFilePattern': GitRepositoryFilePattern,
    'CheckpointRecoveryPattern': CheckpointRecoveryPattern,
    'GitStateAnalysisPattern': GitStateAnalysisPattern,
    'CompositeStateRecoveryPattern': CompositeStateRecoveryPattern
}


def get_pattern(pattern_name: str, **kwargs) -> CognitivePattern:
    """
    Get a pattern instance by name.

    Args:
        pattern_name: Name of the pattern
        **kwargs: Additional parameters for pattern initialization

    Returns:
        Pattern instance
    """
    if pattern_name not in PATTERN_REGISTRY:
        raise ValueError(f"Unknown pattern: {pattern_name}")

    pattern_class = PATTERN_REGISTRY[pattern_name]
    return pattern_class(**kwargs)


if __name__ == "__main__":
    # Example usage
    print("CCMF Pattern Library - Example Usage")
    print("=" * 60)

    # Test DirectPathAccessPattern
    print("\n1. DirectPathAccessPattern")
    pattern = DirectPathAccessPattern()
    result = pattern.execute(path=__file__, operation="stat")
    print(f"   Success: {result.success}")
    print(f"   Data: {result.data}")
    print(f"   Stats: {pattern.get_stats()}")

    # Test KnownPathSearchPattern
    print("\n2. KnownPathSearchPattern")
    pattern = KnownPathSearchPattern()
    result = pattern.execute(
        search_paths=["."],
        pattern="*.py",
        recursive=False
    )
    print(f"   Success: {result.success}")
    print(f"   Files found: {len(result.data)}")
    print(f"   Stats: {pattern.get_stats()}")

    # Test CheckpointRecoveryPattern
    print("\n3. CheckpointRecoveryPattern")
    pattern = CheckpointRecoveryPattern()
    # Save a checkpoint
    result = pattern.execute(
        operation="save",
        checkpoint_id="test_checkpoint",
        state_data={'test': 'data', 'value': 123}
    )
    print(f"   Save success: {result.success}")
    # List checkpoints
    result = pattern.execute(operation="list")
    print(f"   Checkpoints: {result.data['count']}")
    print(f"   Stats: {pattern.get_stats()}")

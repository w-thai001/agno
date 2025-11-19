"""
Claude Code Mastery Framework (CCMF) v1.0 - State Recovery Workflows Module

This module implements checkpoint recovery and composite workflow patterns for state management.

State recovery workflows enable robust recovery from interruptions by:
1. Checkpoint recovery from saved state files
2. Git repository state analysis
3. Composite recovery combining multiple sources

All workflows use constitutional PowerShell and git commands only.

Patterns:
1. CheckpointRecoveryPattern - Recover state from checkpoint files
2. GitStateAnalysisPattern - Analyze git repository state
3. CompositeStateRecoveryPattern - Multi-source state recovery
"""

import json
import logging
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from agno.ccmf_constitutional import BasePattern, ConstitutionalValidator
from agno.ccmf_patterns import KnownPathSearchPattern

# Configure logging
logger = logging.getLogger(__name__)


class CheckpointRecoveryPattern(BasePattern):
    """
    Recover state from checkpoint files using PowerShell subprocess.

    This pattern searches for and recovers state from checkpoint files,
    supporting multiple recovery strategies:
    - latest: Use most recent checkpoint
    - all: Recover all available checkpoints
    - specific: Use specific checkpoint path

    Constitutional compliance:
    - Uses only PowerShell subprocess commands
    - No prohibited file methods
    - Validates all file operations

    Recovery process:
    1. Search checkpoint paths using PowerShell Test-Path
    2. Validate checkpoint files
    3. Extract timestamps from filenames
    4. Select checkpoint based on strategy
    5. Load and return recovered state
    """

    # Checkpoint filename pattern: checkpoint_YYYYMMDD_HHMMSS.json
    CHECKPOINT_PATTERN = re.compile(r'checkpoint_(\d{8})_(\d{6})\.json')

    # Operation timeouts
    TIMEOUT_TEST = 10  # seconds
    TIMEOUT_READ = 30  # seconds

    def __init__(self, validator: Optional[ConstitutionalValidator] = None):
        """
        Initialize the CheckpointRecoveryPattern.

        Args:
            validator: Constitutional validator instance (creates new if None)
        """
        super().__init__(
            pattern_id="checkpoint_recovery_v1",
            pattern_name="Checkpoint Recovery Pattern",
            pattern_description="Recover state from checkpoint files using PowerShell subprocess",
            constitutional_requirements=["ASAEP", "OFAP", "TFCP"],
            version="1.0.0",
            validator=validator
        )

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute checkpoint recovery operation.

        Args:
            inputs: Dictionary containing:
                - checkpoint_paths (List[str]): List of potential checkpoint file paths
                - recovery_strategy (str): "latest", "all", or "specific"
                - specific_path (str, optional): Specific path if strategy is "specific"

        Returns:
            Dictionary containing:
                - success (bool): Whether recovery succeeded
                - checkpoint_used (str, optional): Path to checkpoint used
                - recovered_state (Any, optional): Recovered state data
                - checkpoint_age (float, optional): Age in seconds
                - recovery_strategy (str): Strategy used
                - all_checkpoints (List[Dict], optional): All found checkpoints if strategy is "all"

        Raises:
            ValueError: If required inputs are missing or invalid
        """
        # Validate inputs
        if "checkpoint_paths" not in inputs:
            raise ValueError("Missing required input: checkpoint_paths")
        if "recovery_strategy" not in inputs:
            raise ValueError("Missing required input: recovery_strategy")

        checkpoint_paths = inputs["checkpoint_paths"]
        recovery_strategy = inputs["recovery_strategy"]

        if not isinstance(checkpoint_paths, list):
            raise ValueError("checkpoint_paths must be a list")

        if recovery_strategy not in ["latest", "all", "specific"]:
            raise ValueError("recovery_strategy must be 'latest', 'all', or 'specific'")

        if recovery_strategy == "specific" and "specific_path" not in inputs:
            raise ValueError("specific_path required when recovery_strategy is 'specific'")

        logger.info("Starting checkpoint recovery with strategy: %s", recovery_strategy)

        # Search for valid checkpoints
        valid_checkpoints = []
        for path in checkpoint_paths:
            checkpoint_info = self._validate_checkpoint(path)
            if checkpoint_info:
                valid_checkpoints.append(checkpoint_info)

        if not valid_checkpoints:
            logger.warning("No valid checkpoints found")
            return {
                "success": False,
                "recovery_strategy": recovery_strategy,
                "error": "No valid checkpoints found",
                "searched_paths": checkpoint_paths
            }

        logger.info("Found %d valid checkpoints", len(valid_checkpoints))

        # Select checkpoint based on strategy
        if recovery_strategy == "specific":
            specific_path = inputs["specific_path"]
            selected = next((c for c in valid_checkpoints if c["path"] == specific_path), None)
            if not selected:
                return {
                    "success": False,
                    "recovery_strategy": recovery_strategy,
                    "error": f"Specific checkpoint not found: {specific_path}",
                    "available_checkpoints": [c["path"] for c in valid_checkpoints]
                }
        elif recovery_strategy == "latest":
            selected = self._select_checkpoint(valid_checkpoints, "latest")
        else:  # all
            return self._recover_all_checkpoints(valid_checkpoints, recovery_strategy)

        # Recover state from selected checkpoint
        recovery_result = self._load_checkpoint(selected)

        return recovery_result

    def _validate_checkpoint(self, path: str) -> Optional[Dict[str, Any]]:
        """
        Validate a checkpoint file using PowerShell Test-Path.

        Args:
            path: Path to checkpoint file

        Returns:
            Checkpoint info dict if valid, None if invalid
        """
        try:
            # Constitutional validation
            is_valid, violation = self.validator.validate_file_operation(
                operation="test",
                file_path=path,
                method="powershell_subprocess"
            )

            if not is_valid:
                logger.warning("Constitutional validation failed for %s: %s", path, violation)
                return None

            # Test if file exists
            result = subprocess.run(
                ["powershell", "-Command", f"Test-Path '{path}'"],
                capture_output=True,
                text=True,
                timeout=self.TIMEOUT_TEST,
                check=False
            )

            exists = result.stdout.strip().lower() == "true"

            if not exists:
                return None

            # Extract timestamp from filename
            timestamp = self._parse_checkpoint_timestamp(path)

            if not timestamp:
                logger.warning("Could not parse timestamp from %s", path)
                return None

            # Calculate age
            age_seconds = (datetime.now() - timestamp).total_seconds()

            return {
                "path": path,
                "timestamp": timestamp,
                "age_seconds": age_seconds,
                "exists": True
            }

        except subprocess.TimeoutExpired:
            logger.error("Timeout validating checkpoint: %s", path)
            return None

        except Exception as e:
            logger.exception("Error validating checkpoint %s", path)
            return None

    def _parse_checkpoint_timestamp(self, path: str) -> Optional[datetime]:
        """
        Extract timestamp from checkpoint filename.

        Expected format: checkpoint_YYYYMMDD_HHMMSS.json

        Args:
            path: Checkpoint file path

        Returns:
            Datetime object if parsed, None otherwise
        """
        filename = Path(path).name
        match = self.CHECKPOINT_PATTERN.match(filename)

        if not match:
            return None

        date_str = match.group(1)  # YYYYMMDD
        time_str = match.group(2)  # HHMMSS

        try:
            timestamp = datetime.strptime(f"{date_str}_{time_str}", "%Y%m%d_%H%M%S")
            return timestamp
        except ValueError:
            return None

    def _select_checkpoint(
        self,
        checkpoints: List[Dict[str, Any]],
        strategy: str
    ) -> Dict[str, Any]:
        """
        Select checkpoint based on strategy.

        Args:
            checkpoints: List of valid checkpoint info dicts
            strategy: Selection strategy ("latest" or "all")

        Returns:
            Selected checkpoint info
        """
        if strategy == "latest":
            # Select most recent (smallest age)
            return min(checkpoints, key=lambda c: c["age_seconds"])

        # For "all", this shouldn't be called
        return checkpoints[0]

    def _load_checkpoint(self, checkpoint_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Load state from checkpoint file using PowerShell Get-Content.

        Args:
            checkpoint_info: Checkpoint information dict

        Returns:
            Recovery result dict
        """
        path = checkpoint_info["path"]

        try:
            # Constitutional validation
            is_valid, violation = self.validator.validate_file_operation(
                operation="read",
                file_path=path,
                method="powershell_subprocess"
            )

            if not is_valid:
                return {
                    "success": False,
                    "checkpoint_used": path,
                    "recovery_strategy": "latest",
                    "error": f"Constitutional validation failed: {violation}"
                }

            # Read checkpoint file
            result = subprocess.run(
                ["powershell", "-Command", f"Get-Content '{path}' -Raw"],
                capture_output=True,
                text=True,
                timeout=self.TIMEOUT_READ,
                check=False
            )

            if result.returncode != 0:
                return {
                    "success": False,
                    "checkpoint_used": path,
                    "error": result.stderr
                }

            # Parse JSON state
            try:
                recovered_state = json.loads(result.stdout)
            except json.JSONDecodeError as e:
                return {
                    "success": False,
                    "checkpoint_used": path,
                    "error": f"Invalid JSON in checkpoint: {e}"
                }

            logger.info("Successfully recovered state from %s (age: %.1fs)",
                       path, checkpoint_info["age_seconds"])

            return {
                "success": True,
                "checkpoint_used": path,
                "recovered_state": recovered_state,
                "checkpoint_age": checkpoint_info["age_seconds"],
                "checkpoint_timestamp": checkpoint_info["timestamp"].isoformat(),
                "recovery_strategy": "latest"
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "checkpoint_used": path,
                "error": f"Timeout reading checkpoint after {self.TIMEOUT_READ}s"
            }

        except Exception as e:
            logger.exception("Error loading checkpoint %s", path)
            return {
                "success": False,
                "checkpoint_used": path,
                "error": str(e)
            }

    def _recover_all_checkpoints(
        self,
        checkpoints: List[Dict[str, Any]],
        recovery_strategy: str
    ) -> Dict[str, Any]:
        """
        Recover state from all available checkpoints.

        Args:
            checkpoints: List of valid checkpoint info dicts
            recovery_strategy: Strategy name

        Returns:
            Recovery result with all checkpoints
        """
        all_recovered = []

        for checkpoint_info in checkpoints:
            recovery = self._load_checkpoint(checkpoint_info)
            all_recovered.append(recovery)

        successful = [r for r in all_recovered if r.get("success")]

        return {
            "success": len(successful) > 0,
            "recovery_strategy": recovery_strategy,
            "all_checkpoints": all_recovered,
            "total_checkpoints": len(checkpoints),
            "successful_recoveries": len(successful),
            "failed_recoveries": len(checkpoints) - len(successful)
        }

    def calculate_lq(self, execution_result: Any) -> float:
        """
        Calculate Leverage Quotient for checkpoint recovery.

        Checkpoint recovery has high LQ (7.5) because:
        - High value for state recovery
        - Enables continuation from interruptions
        - Relatively low cost

        Args:
            execution_result: Result from execute()

        Returns:
            LQ score (7.5 for successful recovery, 0.0 for failures)
        """
        if not isinstance(execution_result, dict):
            return 0.0

        success = execution_result.get("success", False)

        if success:
            # High LQ for successful recovery
            progress = 1.0
            efficiency = 0.90  # High efficiency for state recovery
            cost = 0.12  # Low cost

            lq = self.validator.calculate_leverage_quotient(
                progress_towards_goal=progress,
                energy_efficiency=efficiency,
                cost=cost
            )
            return lq  # Should be approximately 7.5
        else:
            return 0.0


class GitStateAnalysisPattern(BasePattern):
    """
    Analyze git repository state using git commands.

    This pattern provides comprehensive analysis of git repository state:
    - Current branch
    - Working tree status (uncommitted changes)
    - Recent commit history
    - Diff statistics

    Constitutional compliance:
    - Uses only git subprocess commands
    - No prohibited file methods
    - Validates git repository structure

    Analysis includes:
    - git status --porcelain (working tree)
    - git log -n <depth> --oneline (recent commits)
    - git diff --stat (uncommitted changes)
    - git branch --show-current (current branch)
    """

    # Operation timeouts
    TIMEOUT_STATUS = 10   # seconds
    TIMEOUT_LOG = 15      # seconds
    TIMEOUT_DIFF = 20     # seconds
    TIMEOUT_BRANCH = 5    # seconds

    def __init__(self, validator: Optional[ConstitutionalValidator] = None):
        """
        Initialize the GitStateAnalysisPattern.

        Args:
            validator: Constitutional validator instance (creates new if None)
        """
        super().__init__(
            pattern_id="git_state_analysis_v1",
            pattern_name="Git State Analysis Pattern",
            pattern_description="Analyze git repository state using git commands",
            constitutional_requirements=["ASAEP", "OFAP", "TFCP"],
            version="1.0.0",
            validator=validator
        )

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute git state analysis operation.

        Args:
            inputs: Dictionary containing:
                - repo_path (str): Path to git repository root
                - analysis_depth (int, optional): Number of commits to analyze (default: 10)

        Returns:
            Dictionary containing:
                - success (bool): Whether analysis succeeded
                - current_branch (str): Current branch name
                - uncommitted_files (List[str]): Files with uncommitted changes
                - recent_commits (List[str]): Recent commit messages
                - diff_summary (str): Summary of uncommitted changes
                - is_clean (bool): True if no uncommitted changes
                - repo_path (str): Repository path

        Raises:
            ValueError: If required inputs are missing or invalid
        """
        # Validate inputs
        if "repo_path" not in inputs:
            raise ValueError("Missing required input: repo_path")

        repo_path = inputs["repo_path"]
        analysis_depth = inputs.get("analysis_depth", 10)

        # Validate git repository
        if not self._is_git_repository(repo_path):
            return {
                "success": False,
                "repo_path": repo_path,
                "error": "Not a valid git repository (no .git directory found)"
            }

        logger.info("Analyzing git state for repository: %s", repo_path)

        # Get current branch
        current_branch = self._get_current_branch(repo_path)

        # Get working tree status
        status_result = self._get_status(repo_path)

        # Get recent commits
        commits = self._get_recent_commits(repo_path, analysis_depth)

        # Get diff summary
        diff_summary = self._get_diff_summary(repo_path)

        # Determine if working tree is clean
        is_clean = len(status_result.get("uncommitted_files", [])) == 0

        result = {
            "success": True,
            "current_branch": current_branch,
            "uncommitted_files": status_result.get("uncommitted_files", []),
            "recent_commits": commits,
            "diff_summary": diff_summary,
            "is_clean": is_clean,
            "repo_path": repo_path,
            "analysis_depth": analysis_depth
        }

        logger.info("Git state analysis complete: branch=%s, clean=%s, commits=%d",
                   current_branch, is_clean, len(commits))

        return result

    def _is_git_repository(self, repo_path: str) -> bool:
        """
        Check if path is a valid git repository.

        Args:
            repo_path: Path to check

        Returns:
            True if valid git repository, False otherwise
        """
        git_dir = Path(repo_path) / ".git"
        return git_dir.exists() and git_dir.is_dir()

    def _get_current_branch(self, repo_path: str) -> str:
        """
        Get current git branch using git branch --show-current.

        Args:
            repo_path: Repository path

        Returns:
            Branch name or "unknown" if failed
        """
        try:
            # Constitutional validation
            is_valid, violation = self.validator.validate_file_operation(
                operation="git_branch",
                file_path=repo_path,
                method="git_command"
            )

            if not is_valid:
                logger.warning("Validation failed for git branch: %s", violation)
                return "unknown"

            result = subprocess.run(
                ["git", "-C", repo_path, "branch", "--show-current"],
                capture_output=True,
                text=True,
                timeout=self.TIMEOUT_BRANCH,
                check=False
            )

            if result.returncode == 0:
                return result.stdout.strip() or "detached HEAD"

            return "unknown"

        except Exception as e:
            logger.exception("Error getting current branch")
            return "unknown"

    def _get_status(self, repo_path: str) -> Dict[str, Any]:
        """
        Get working tree status using git status --porcelain.

        Args:
            repo_path: Repository path

        Returns:
            Dictionary with uncommitted files
        """
        try:
            # Constitutional validation
            is_valid, violation = self.validator.validate_file_operation(
                operation="git_status",
                file_path=repo_path,
                method="git_command"
            )

            if not is_valid:
                logger.warning("Validation failed for git status: %s", violation)
                return {"uncommitted_files": []}

            result = subprocess.run(
                ["git", "-C", repo_path, "status", "--porcelain"],
                capture_output=True,
                text=True,
                timeout=self.TIMEOUT_STATUS,
                check=False
            )

            if result.returncode != 0:
                logger.error("git status failed: %s", result.stderr)
                return {"uncommitted_files": []}

            # Parse porcelain output
            uncommitted_files = []
            for line in result.stdout.split('\n'):
                if line.strip():
                    # Format: "XY filename" where XY are status codes
                    parts = line.strip().split(maxsplit=1)
                    if len(parts) == 2:
                        uncommitted_files.append(parts[1])

            return {"uncommitted_files": uncommitted_files}

        except subprocess.TimeoutExpired:
            logger.error("git status timeout")
            return {"uncommitted_files": []}

        except Exception as e:
            logger.exception("Error getting git status")
            return {"uncommitted_files": []}

    def _get_recent_commits(self, repo_path: str, depth: int) -> List[str]:
        """
        Get recent commits using git log.

        Args:
            repo_path: Repository path
            depth: Number of commits to retrieve

        Returns:
            List of commit messages
        """
        try:
            # Constitutional validation
            is_valid, violation = self.validator.validate_file_operation(
                operation="git_log",
                file_path=repo_path,
                method="git_command"
            )

            if not is_valid:
                logger.warning("Validation failed for git log: %s", violation)
                return []

            result = subprocess.run(
                ["git", "-C", repo_path, "log", f"-n{depth}", "--oneline"],
                capture_output=True,
                text=True,
                timeout=self.TIMEOUT_LOG,
                check=False
            )

            if result.returncode != 0:
                logger.error("git log failed: %s", result.stderr)
                return []

            commits = [c.strip() for c in result.stdout.split('\n') if c.strip()]
            return commits

        except subprocess.TimeoutExpired:
            logger.error("git log timeout")
            return []

        except Exception as e:
            logger.exception("Error getting git log")
            return []

    def _get_diff_summary(self, repo_path: str) -> str:
        """
        Get diff summary using git diff --stat.

        Args:
            repo_path: Repository path

        Returns:
            Diff summary string
        """
        try:
            # Constitutional validation
            is_valid, violation = self.validator.validate_file_operation(
                operation="git_diff",
                file_path=repo_path,
                method="git_command"
            )

            if not is_valid:
                logger.warning("Validation failed for git diff: %s", violation)
                return ""

            result = subprocess.run(
                ["git", "-C", repo_path, "diff", "--stat"],
                capture_output=True,
                text=True,
                timeout=self.TIMEOUT_DIFF,
                check=False
            )

            if result.returncode != 0:
                logger.error("git diff failed: %s", result.stderr)
                return ""

            return result.stdout.strip()

        except subprocess.TimeoutExpired:
            logger.error("git diff timeout")
            return ""

        except Exception as e:
            logger.exception("Error getting git diff")
            return ""

    def calculate_lq(self, execution_result: Any) -> float:
        """
        Calculate Leverage Quotient for git state analysis.

        Git state analysis has high LQ (8.5) because:
        - Git provides reliable, versioned state information
        - Very low cost (git is fast)
        - High value for understanding repository state

        Args:
            execution_result: Result from execute()

        Returns:
            LQ score (8.5 for successful analysis, 0.0 for failures)
        """
        if not isinstance(execution_result, dict):
            return 0.0

        success = execution_result.get("success", False)

        if success:
            # High LQ for git analysis
            progress = 1.0
            efficiency = 0.95  # Very high efficiency
            cost = 0.11  # Very low cost

            lq = self.validator.calculate_leverage_quotient(
                progress_towards_goal=progress,
                energy_efficiency=efficiency,
                cost=cost
            )
            return lq  # Should be approximately 8.5
        else:
            return 0.0


class CompositeStateRecoveryPattern(BasePattern):
    """
    Orchestrate multi-source state recovery (checkpoints + git + known paths).

    This pattern combines multiple recovery sources for robust state recovery:
    1. Checkpoint files (highest priority - saved state)
    2. Git repository analysis (medium priority - version control state)
    3. Known path fallbacks (lowest priority - default locations)

    The pattern tries sources in order and merges results to provide
    comprehensive state recovery with confidence scoring.

    Constitutional compliance:
    - Uses CheckpointRecoveryPattern, GitStateAnalysisPattern, KnownPathSearchPattern
    - All underlying operations use PowerShell/git subprocess
    - No prohibited methods
    """

    def __init__(self, validator: Optional[ConstitutionalValidator] = None):
        """
        Initialize the CompositeStateRecoveryPattern.

        Args:
            validator: Constitutional validator instance (creates new if None)
        """
        super().__init__(
            pattern_id="composite_state_recovery_v1",
            pattern_name="Composite State Recovery Pattern",
            pattern_description="Multi-source state recovery combining checkpoints, git, and known paths",
            constitutional_requirements=["ASAEP", "OFAP", "TFCP"],
            version="1.0.0",
            validator=validator
        )

        # Initialize sub-patterns
        self.checkpoint_pattern = CheckpointRecoveryPattern(validator)
        self.git_pattern = GitStateAnalysisPattern(validator)
        self.path_search_pattern = KnownPathSearchPattern(validator)

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute composite state recovery operation.

        Args:
            inputs: Dictionary containing:
                - checkpoint_paths (List[str]): Paths to search for checkpoints
                - repo_path (str): Path to git repository
                - fallback_paths (List[str]): Fallback paths to search

        Returns:
            Dictionary containing:
                - success (bool): Whether recovery succeeded
                - recovery_sources_used (List[str]): Sources that provided data
                - merged_state (Dict): Combined state from all sources
                - confidence_score (float): Confidence in recovery (0.0-1.0)
                - recovery_time (float): Time taken for recovery
                - checkpoint_result (Dict, optional): Checkpoint recovery result
                - git_result (Dict, optional): Git analysis result
                - fallback_result (Dict, optional): Fallback search result

        Raises:
            ValueError: If required inputs are missing
        """
        # Validate inputs
        if "checkpoint_paths" not in inputs:
            raise ValueError("Missing required input: checkpoint_paths")
        if "repo_path" not in inputs:
            raise ValueError("Missing required input: repo_path")
        if "fallback_paths" not in inputs:
            raise ValueError("Missing required input: fallback_paths")

        logger.info("Starting composite state recovery")
        recovery_start = datetime.now()

        sources_used = []
        recovery_sources = []

        # Try checkpoint recovery first (highest priority)
        checkpoint_result = None
        try:
            logger.info("Attempting checkpoint recovery...")
            checkpoint_success, checkpoint_result, checkpoint_error = self.checkpoint_pattern.execute_with_validation({
                "checkpoint_paths": inputs["checkpoint_paths"],
                "recovery_strategy": "latest"
            })

            if checkpoint_success and checkpoint_result.get("success"):
                sources_used.append("checkpoint")
                recovery_sources.append({
                    "source": "checkpoint",
                    "priority": 1,
                    "data": checkpoint_result
                })
                logger.info("Checkpoint recovery succeeded")
        except Exception as e:
            logger.warning("Checkpoint recovery failed: %s", e)

        # Try git state analysis (medium priority)
        git_result = None
        try:
            logger.info("Attempting git state analysis...")
            git_success, git_result, git_error = self.git_pattern.execute_with_validation({
                "repo_path": inputs["repo_path"],
                "analysis_depth": 10
            })

            if git_success and git_result.get("success"):
                sources_used.append("git")
                recovery_sources.append({
                    "source": "git",
                    "priority": 2,
                    "data": git_result
                })
                logger.info("Git state analysis succeeded")
        except Exception as e:
            logger.warning("Git analysis failed: %s", e)

        # Try fallback paths (lowest priority)
        fallback_result = None
        try:
            logger.info("Attempting fallback path search...")
            fallback_success, fallback_result, fallback_error = self.path_search_pattern.execute_with_validation({
                "search_paths": inputs["fallback_paths"],
                "read_content": False
            })

            if fallback_success and fallback_result.get("found"):
                sources_used.append("fallback")
                recovery_sources.append({
                    "source": "fallback",
                    "priority": 3,
                    "data": fallback_result
                })
                logger.info("Fallback path search succeeded")
        except Exception as e:
            logger.warning("Fallback search failed: %s", e)

        # Merge recovery sources
        merged_state = self._merge_recovery_sources(recovery_sources)

        # Calculate confidence score
        confidence_score = self._calculate_confidence_score({
            "sources_used": sources_used,
            "checkpoint_result": checkpoint_result,
            "git_result": git_result,
            "fallback_result": fallback_result
        })

        # Calculate recovery time
        recovery_time = (datetime.now() - recovery_start).total_seconds()

        success = len(sources_used) > 0

        result = {
            "success": success,
            "recovery_sources_used": sources_used,
            "merged_state": merged_state,
            "confidence_score": confidence_score,
            "recovery_time": recovery_time,
            "checkpoint_result": checkpoint_result,
            "git_result": git_result,
            "fallback_result": fallback_result
        }

        logger.info("Composite recovery complete: sources=%s, confidence=%.2f",
                   sources_used, confidence_score)

        return result

    def _merge_recovery_sources(
        self,
        sources: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Merge data from multiple recovery sources.

        Sources are merged by priority (lower number = higher priority).
        Higher priority sources override lower priority ones.

        Args:
            sources: List of source dictionaries with priority and data

        Returns:
            Merged state dictionary
        """
        if not sources:
            return {}

        # Sort by priority (ascending - lower is higher priority)
        sorted_sources = sorted(sources, key=lambda s: s["priority"])

        merged = {
            "recovery_metadata": {
                "sources_count": len(sources),
                "primary_source": sorted_sources[0]["source"] if sources else None,
                "merge_timestamp": datetime.now().isoformat()
            }
        }

        # Merge data from each source (reverse order so higher priority overwrites)
        for source in reversed(sorted_sources):
            source_name = source["source"]
            source_data = source["data"]

            merged[source_name] = source_data

            # Extract key state information
            if source_name == "checkpoint":
                if "recovered_state" in source_data:
                    merged["state"] = source_data["recovered_state"]
                    merged["state_source"] = "checkpoint"

            elif source_name == "git":
                merged["git_state"] = {
                    "branch": source_data.get("current_branch"),
                    "is_clean": source_data.get("is_clean"),
                    "uncommitted_files": source_data.get("uncommitted_files", [])
                }

            elif source_name == "fallback":
                if "path" in source_data:
                    merged["fallback_path"] = source_data["path"]

        return merged

    def _calculate_confidence_score(self, recovery_result: Dict[str, Any]) -> float:
        """
        Calculate confidence score for recovery reliability.

        Confidence is based on:
        - Checkpoint recovery: 0.9 (highest confidence)
        - Git + checkpoint: 0.95 (very high confidence)
        - Git only: 0.7 (good confidence)
        - Fallback only: 0.4 (low confidence)
        - No recovery: 0.0

        Args:
            recovery_result: Recovery result dictionary

        Returns:
            Confidence score (0.0 to 1.0)
        """
        sources_used = recovery_result.get("sources_used", [])

        if not sources_used:
            return 0.0

        checkpoint_result = recovery_result.get("checkpoint_result")
        git_result = recovery_result.get("git_result")

        # Checkpoint + Git = highest confidence
        if "checkpoint" in sources_used and "git" in sources_used:
            base_score = 0.95

            # Bonus if git shows clean state
            if git_result and git_result.get("is_clean"):
                base_score = 0.98

            return base_score

        # Checkpoint only = very high confidence
        if "checkpoint" in sources_used:
            checkpoint_age = checkpoint_result.get("checkpoint_age", 0)

            # Recent checkpoint = higher confidence
            if checkpoint_age < 3600:  # Less than 1 hour
                return 0.95
            elif checkpoint_age < 86400:  # Less than 1 day
                return 0.90
            else:
                return 0.85

        # Git only = good confidence
        if "git" in sources_used:
            if git_result.get("is_clean"):
                return 0.75
            else:
                return 0.70

        # Fallback only = low confidence
        if "fallback" in sources_used:
            return 0.40

        return 0.0

    def calculate_lq(self, execution_result: Any) -> float:
        """
        Calculate Leverage Quotient for composite state recovery.

        LQ varies based on recovery sources used:
        - Checkpoint recovery: 9.0 (best case)
        - Checkpoint + Git: 9.5 (excellent)
        - Git only: 7.0 (good)
        - Fallback only: 4.0 (acceptable)
        - Failed: 0.0

        Args:
            execution_result: Result from execute()

        Returns:
            LQ score based on recovery quality
        """
        if not isinstance(execution_result, dict):
            return 0.0

        success = execution_result.get("success", False)
        if not success:
            return 0.0

        sources_used = execution_result.get("recovery_sources_used", [])

        # Calculate LQ based on sources
        if "checkpoint" in sources_used and "git" in sources_used:
            # Best case: checkpoint + git validation
            progress = 1.0
            efficiency = 0.98
            cost = 0.10
        elif "checkpoint" in sources_used:
            # Good case: checkpoint recovery
            progress = 1.0
            efficiency = 0.95
            cost = 0.11
        elif "git" in sources_used:
            # Decent case: git state analysis
            progress = 0.85
            efficiency = 0.90
            cost = 0.11
        elif "fallback" in sources_used:
            # Fallback case
            progress = 0.60
            efficiency = 0.75
            cost = 0.15
        else:
            return 0.0

        lq = self.validator.calculate_leverage_quotient(
            progress_towards_goal=progress,
            energy_efficiency=efficiency,
            cost=cost
        )

        return lq


# Module-level convenience functions
def create_checkpoint_recovery_pattern(
    validator: Optional[ConstitutionalValidator] = None
) -> CheckpointRecoveryPattern:
    """
    Factory function to create a CheckpointRecoveryPattern instance.

    Args:
        validator: Constitutional validator (creates new if None)

    Returns:
        CheckpointRecoveryPattern instance
    """
    return CheckpointRecoveryPattern(validator=validator)


def create_git_state_analysis_pattern(
    validator: Optional[ConstitutionalValidator] = None
) -> GitStateAnalysisPattern:
    """
    Factory function to create a GitStateAnalysisPattern instance.

    Args:
        validator: Constitutional validator (creates new if None)

    Returns:
        GitStateAnalysisPattern instance
    """
    return GitStateAnalysisPattern(validator=validator)


def create_composite_state_recovery_pattern(
    validator: Optional[ConstitutionalValidator] = None
) -> CompositeStateRecoveryPattern:
    """
    Factory function to create a CompositeStateRecoveryPattern instance.

    Args:
        validator: Constitutional validator (creates new if None)

    Returns:
        CompositeStateRecoveryPattern instance
    """
    return CompositeStateRecoveryPattern(validator=validator)


# Module metadata
__version__ = "1.0.0"
__author__ = "CCMF Contributors"
__description__ = "CCMF State Recovery Workflows - Checkpoint and git-based state recovery"

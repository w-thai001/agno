"""
Claude Code Mastery Framework (CCMF) v1.0 - File Operation Patterns

This module implements PowerShell-safe file operation patterns for the CCMF framework.

CRITICAL CONSTRAINT: ABSOLUTELY NO read_list, file_list, or file_find_by_name methods.
Uses ONLY PowerShell subprocess calls and git commands for constitutional compliance.

Patterns:
1. DirectPathAccessPattern - Direct file access via PowerShell subprocess
2. KnownPathSearchPattern - Search through predefined paths using PowerShell
3. GitRepositoryFilePattern - Access files in git repositories using git commands

All patterns enforce constitutional validation and track performance metrics for RSI.
"""

import subprocess
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from agno.ccmf_constitutional import BasePattern, ConstitutionalValidator

# Configure logging
logger = logging.getLogger(__name__)


class DirectPathAccessPattern(BasePattern):
    """
    Direct file access pattern using PowerShell subprocess commands.

    This pattern accesses files via exact paths using PowerShell subprocess calls,
    ensuring constitutional compliance with ASAEP and OFAP protocols.

    Supported operations:
    - test: Check if path exists (Test-Path)
    - exists: Alias for test operation
    - read: Read file content (Get-Content -Raw)

    Constitutional compliance:
    - Uses only PowerShell subprocess commands
    - Validates all operations via ConstitutionalValidator
    - Absolutely no prohibited methods (read_list, file_list, file_find_by_name)

    Performance:
    - High efficiency for direct access
    - LQ Score: 8.0 (optimized for known paths)
    - Timeout protection: 10s for tests, 30s for reads
    """

    # Operation timeouts
    TIMEOUT_TEST = 10  # seconds
    TIMEOUT_READ = 30  # seconds

    def __init__(self, validator: Optional[ConstitutionalValidator] = None):
        """
        Initialize the DirectPathAccessPattern.

        Args:
            validator: Constitutional validator instance (creates new if None)
        """
        super().__init__(
            pattern_id="direct_path_access_v1",
            pattern_name="Direct Path Access Pattern",
            pattern_description="Access files via exact paths using PowerShell subprocess",
            constitutional_requirements=["ASAEP", "OFAP", "TFCP"],
            version="1.0.0",
            validator=validator
        )

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute direct path access operation.

        Args:
            inputs: Dictionary containing:
                - file_path (str): Path to the file
                - operation (str): Operation to perform ("test", "exists", or "read")

        Returns:
            Dictionary containing:
                - success (bool): Whether operation succeeded
                - exists (bool): Whether file/path exists
                - content (str, optional): File content if operation is "read"
                - file_path (str): Path that was accessed
                - operation (str): Operation that was performed
                - size_bytes (int, optional): Size of content in bytes

        Raises:
            ValueError: If required inputs are missing or invalid
            subprocess.TimeoutExpired: If operation exceeds timeout
        """
        # Validate inputs
        if "file_path" not in inputs:
            raise ValueError("Missing required input: file_path")
        if "operation" not in inputs:
            raise ValueError("Missing required input: operation")

        file_path = inputs["file_path"]
        operation = inputs["operation"]

        # Normalize operation (exists is alias for test)
        if operation == "exists":
            operation = "test"

        # Validate operation
        if operation not in ["test", "read"]:
            raise ValueError(f"Invalid operation: {operation}. Must be 'test', 'exists', or 'read'")

        # Constitutional validation
        is_valid, violation = self.validator.validate_file_operation(
            operation=operation,
            file_path=file_path,
            method="powershell_subprocess"
        )

        if not is_valid:
            raise ValueError(f"Constitutional validation failed: {violation}")

        logger.info("Executing DirectPathAccess: %s on %s", operation, file_path)

        # Execute operation
        if operation == "test":
            return self._execute_test(file_path)
        elif operation == "read":
            return self._execute_read(file_path)

    def _execute_test(self, file_path: str) -> Dict[str, Any]:
        """
        Execute Test-Path operation using PowerShell subprocess.

        Args:
            file_path: Path to test

        Returns:
            Dictionary with test results
        """
        try:
            # PowerShell Test-Path command
            result = subprocess.run(
                ["powershell", "-Command", f"Test-Path '{file_path}'"],
                capture_output=True,
                text=True,
                timeout=self.TIMEOUT_TEST,
                check=False
            )

            # Parse result (PowerShell returns "True" or "False")
            exists = result.stdout.strip().lower() == "true"

            logger.debug("Test-Path result for %s: %s", file_path, exists)

            return {
                "success": True,
                "exists": exists,
                "file_path": file_path,
                "operation": "test",
                "powershell_returncode": result.returncode
            }

        except subprocess.TimeoutExpired as e:
            logger.error("Test-Path timeout for %s after %ds", file_path, self.TIMEOUT_TEST)
            raise

        except Exception as e:
            logger.exception("Test-Path failed for %s", file_path)
            return {
                "success": False,
                "exists": False,
                "file_path": file_path,
                "operation": "test",
                "error": str(e)
            }

    def _execute_read(self, file_path: str) -> Dict[str, Any]:
        """
        Execute Get-Content operation using PowerShell subprocess.

        Args:
            file_path: Path to read

        Returns:
            Dictionary with file content
        """
        try:
            # First check if file exists
            test_result = self._execute_test(file_path)
            if not test_result.get("exists", False):
                return {
                    "success": False,
                    "exists": False,
                    "file_path": file_path,
                    "operation": "read",
                    "error": "File does not exist"
                }

            # PowerShell Get-Content command (-Raw for complete content)
            result = subprocess.run(
                ["powershell", "-Command", f"Get-Content '{file_path}' -Raw"],
                capture_output=True,
                text=True,
                timeout=self.TIMEOUT_READ,
                check=False
            )

            if result.returncode != 0:
                logger.error("Get-Content failed for %s: %s", file_path, result.stderr)
                return {
                    "success": False,
                    "exists": True,
                    "file_path": file_path,
                    "operation": "read",
                    "error": result.stderr
                }

            content = result.stdout
            size_bytes = len(content.encode('utf-8'))

            logger.debug("Read %d bytes from %s", size_bytes, file_path)

            return {
                "success": True,
                "exists": True,
                "content": content,
                "file_path": file_path,
                "operation": "read",
                "size_bytes": size_bytes
            }

        except subprocess.TimeoutExpired as e:
            logger.error("Get-Content timeout for %s after %ds", file_path, self.TIMEOUT_READ)
            raise

        except Exception as e:
            logger.exception("Get-Content failed for %s", file_path)
            return {
                "success": False,
                "exists": False,
                "file_path": file_path,
                "operation": "read",
                "error": str(e)
            }

    def calculate_lq(self, execution_result: Any) -> float:
        """
        Calculate Leverage Quotient for direct path access.

        Direct path access has high efficiency (LQ = 8.0) because:
        - No search required (direct access)
        - Minimal subprocess overhead
        - High reliability with known paths

        Args:
            execution_result: Result from execute()

        Returns:
            LQ score (8.0 for successful operations, 0.0 for failures)
        """
        if not isinstance(execution_result, dict):
            return 0.0

        success = execution_result.get("success", False)

        if success:
            # High LQ for successful direct access
            progress = 1.0
            efficiency = 0.95  # Very high efficiency for direct access
            cost = 0.12  # Low cost (single subprocess call)

            lq = self.validator.calculate_leverage_quotient(
                progress_towards_goal=progress,
                energy_efficiency=efficiency,
                cost=cost
            )
            return lq  # Should be approximately 8.0
        else:
            # Failed operation
            return 0.0


class KnownPathSearchPattern(BasePattern):
    """
    Search through predefined paths using PowerShell Test-Path iteratively.

    This pattern searches through a known list of paths using PowerShell subprocess
    to test each path iteratively, ensuring constitutional compliance.

    The pattern logs each attempt and returns the first match, or a complete search
    log if no match is found.

    Constitutional compliance:
    - Uses only PowerShell subprocess commands
    - No prohibited search methods (file_find_by_name, etc.)
    - Iterative Test-Path for each candidate

    Performance:
    - LQ decreases with number of attempts (more attempts = higher cost)
    - Base LQ: 7.0
    - Penalty: -0.5 per attempt
    - Minimum LQ: 2.0
    """

    # Operation timeouts
    TIMEOUT_TEST = 10  # seconds per test
    TIMEOUT_READ = 30  # seconds for reading matched file

    # LQ calculation parameters
    BASE_LQ = 7.0
    PENALTY_PER_ATTEMPT = 0.5
    MINIMUM_LQ = 2.0

    def __init__(self, validator: Optional[ConstitutionalValidator] = None):
        """
        Initialize the KnownPathSearchPattern.

        Args:
            validator: Constitutional validator instance (creates new if None)
        """
        super().__init__(
            pattern_id="known_path_search_v1",
            pattern_name="Known Path Search Pattern",
            pattern_description="Search through predefined paths using PowerShell Test-Path iteratively",
            constitutional_requirements=["ASAEP", "OFAP", "TFCP"],
            version="1.0.0",
            validator=validator
        )

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute known path search operation.

        Args:
            inputs: Dictionary containing:
                - search_paths (List[str]): List of paths to search
                - read_content (bool): Whether to read content if found

        Returns:
            Dictionary containing:
                - success (bool): Whether a match was found
                - found (bool): Whether a path exists
                - path (str, optional): Path that was found
                - search_log (List[Dict]): Log of all search attempts
                - attempts (int): Number of paths tested
                - content (str, optional): File content if read_content=True

        Raises:
            ValueError: If required inputs are missing or invalid
        """
        # Validate inputs
        if "search_paths" not in inputs:
            raise ValueError("Missing required input: search_paths")

        search_paths = inputs["search_paths"]
        read_content = inputs.get("read_content", False)

        if not isinstance(search_paths, list):
            raise ValueError("search_paths must be a list")

        if not search_paths:
            raise ValueError("search_paths cannot be empty")

        logger.info("Starting KnownPathSearch with %d candidate paths", len(search_paths))

        search_log = []
        found_path = None

        # Iterate through search paths
        for idx, path in enumerate(search_paths):
            attempt_start = datetime.now()

            # Constitutional validation
            is_valid, violation = self.validator.validate_file_operation(
                operation="test",
                file_path=path,
                method="powershell_subprocess"
            )

            if not is_valid:
                # Log validation failure and continue to next path
                log_entry = {
                    "attempt": idx + 1,
                    "path": path,
                    "timestamp": attempt_start.isoformat(),
                    "exists": False,
                    "validation_failed": True,
                    "error": str(violation)
                }
                search_log.append(log_entry)
                logger.warning("Validation failed for path %s: %s", path, violation)
                continue

            # Test path existence
            try:
                result = subprocess.run(
                    ["powershell", "-Command", f"Test-Path '{path}'"],
                    capture_output=True,
                    text=True,
                    timeout=self.TIMEOUT_TEST,
                    check=False
                )

                exists = result.stdout.strip().lower() == "true"
                duration = (datetime.now() - attempt_start).total_seconds()

                log_entry = {
                    "attempt": idx + 1,
                    "path": path,
                    "timestamp": attempt_start.isoformat(),
                    "exists": exists,
                    "duration_seconds": duration
                }

                search_log.append(log_entry)

                if exists:
                    found_path = path
                    logger.info("Found matching path: %s (attempt %d)", path, idx + 1)
                    break

            except subprocess.TimeoutExpired:
                log_entry = {
                    "attempt": idx + 1,
                    "path": path,
                    "timestamp": attempt_start.isoformat(),
                    "exists": False,
                    "timeout": True,
                    "error": f"Timeout after {self.TIMEOUT_TEST}s"
                }
                search_log.append(log_entry)
                logger.error("Timeout testing path: %s", path)
                continue

            except Exception as e:
                log_entry = {
                    "attempt": idx + 1,
                    "path": path,
                    "timestamp": attempt_start.isoformat(),
                    "exists": False,
                    "error": str(e)
                }
                search_log.append(log_entry)
                logger.exception("Error testing path: %s", path)
                continue

        # Build result
        result = {
            "success": found_path is not None,
            "found": found_path is not None,
            "search_log": search_log,
            "attempts": len(search_log)
        }

        if found_path:
            result["path"] = found_path

            # Read content if requested
            if read_content:
                content_result = self._read_content(found_path)
                if content_result.get("success"):
                    result["content"] = content_result.get("content")
                    result["size_bytes"] = content_result.get("size_bytes")
                else:
                    result["read_error"] = content_result.get("error")

        logger.info("KnownPathSearch completed: %d attempts, found=%s",
                   len(search_log), found_path is not None)

        return result

    def _read_content(self, file_path: str) -> Dict[str, Any]:
        """
        Read file content using PowerShell Get-Content.

        Args:
            file_path: Path to read

        Returns:
            Dictionary with content or error
        """
        try:
            # Constitutional validation
            is_valid, violation = self.validator.validate_file_operation(
                operation="read",
                file_path=file_path,
                method="powershell_subprocess"
            )

            if not is_valid:
                return {
                    "success": False,
                    "error": f"Validation failed: {violation}"
                }

            # PowerShell Get-Content
            result = subprocess.run(
                ["powershell", "-Command", f"Get-Content '{file_path}' -Raw"],
                capture_output=True,
                text=True,
                timeout=self.TIMEOUT_READ,
                check=False
            )

            if result.returncode != 0:
                return {
                    "success": False,
                    "error": result.stderr
                }

            content = result.stdout
            return {
                "success": True,
                "content": content,
                "size_bytes": len(content.encode('utf-8'))
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": f"Timeout after {self.TIMEOUT_READ}s"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def calculate_lq(self, execution_result: Any) -> float:
        """
        Calculate Leverage Quotient for known path search.

        LQ decreases with number of attempts:
        - Base LQ: 7.0
        - Penalty: -0.5 per attempt
        - Minimum: 2.0

        More attempts = higher cost, lower LQ.

        Args:
            execution_result: Result from execute()

        Returns:
            LQ score based on number of attempts
        """
        if not isinstance(execution_result, dict):
            return 0.0

        found = execution_result.get("found", False)
        attempts = execution_result.get("attempts", 0)

        if not found:
            # No match found - very low LQ
            return 0.5

        # Calculate LQ based on attempts
        # More attempts = higher cost = lower LQ
        lq = self.BASE_LQ - (self.PENALTY_PER_ATTEMPT * attempts)
        lq = max(lq, self.MINIMUM_LQ)  # Apply minimum

        logger.debug("Calculated LQ: %.2f (attempts=%d)", lq, attempts)

        return lq


class GitRepositoryFilePattern(BasePattern):
    """
    Access files in git repository using git commands.

    This pattern uses git commands to access files in a git repository,
    ensuring constitutional compliance by avoiding prohibited file methods.

    Supported operations:
    - list: List files matching pattern (git ls-files)
    - read: Read file content from HEAD (git show HEAD:path)
    - log: Show commit history for file (git log --oneline -- path)

    Constitutional compliance:
    - Uses only git subprocess commands
    - Absolutely no prohibited methods
    - Validates git repository structure

    Performance:
    - High LQ (9.0) due to git's versioned, reliable access
    - Built-in content tracking and history
    - Efficient for repository-based operations
    """

    # Operation timeouts
    TIMEOUT_LIST = 15  # seconds
    TIMEOUT_READ = 30  # seconds
    TIMEOUT_LOG = 20   # seconds

    def __init__(self, validator: Optional[ConstitutionalValidator] = None):
        """
        Initialize the GitRepositoryFilePattern.

        Args:
            validator: Constitutional validator instance (creates new if None)
        """
        super().__init__(
            pattern_id="git_repo_file_v1",
            pattern_name="Git Repository File Pattern",
            pattern_description="Access files in git repository using git commands",
            constitutional_requirements=["ASAEP", "OFAP", "TFCP"],
            version="1.0.0",
            validator=validator
        )

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute git repository file operation.

        Args:
            inputs: Dictionary containing:
                - repo_path (str): Path to git repository root
                - operation (str): Operation ("list", "read", or "log")
                - file_pattern (str): File pattern or path

        Returns:
            Dictionary containing:
                - success (bool): Whether operation succeeded
                - operation (str): Operation performed
                - files (List[str], optional): List of files (for "list")
                - content (str, optional): File content (for "read")
                - commits (List[str], optional): Commit log (for "log")
                - count (int): Number of files/commits
                - repo_path (str): Repository path

        Raises:
            ValueError: If required inputs are missing or invalid
        """
        # Validate inputs
        if "repo_path" not in inputs:
            raise ValueError("Missing required input: repo_path")
        if "operation" not in inputs:
            raise ValueError("Missing required input: operation")
        if "file_pattern" not in inputs:
            raise ValueError("Missing required input: file_pattern")

        repo_path = inputs["repo_path"]
        operation = inputs["operation"]
        file_pattern = inputs["file_pattern"]

        # Validate operation
        if operation not in ["list", "read", "log"]:
            raise ValueError(f"Invalid operation: {operation}. Must be 'list', 'read', or 'log'")

        # Validate git repository
        if not self._is_git_repository(repo_path):
            return {
                "success": False,
                "operation": operation,
                "repo_path": repo_path,
                "error": "Not a valid git repository (no .git directory found)"
            }

        # Constitutional validation
        is_valid, violation = self.validator.validate_file_operation(
            operation=operation,
            file_path=f"{repo_path}/{file_pattern}",
            method="git_command"
        )

        if not is_valid:
            raise ValueError(f"Constitutional validation failed: {violation}")

        logger.info("Executing GitRepositoryFile: %s on %s in %s",
                   operation, file_pattern, repo_path)

        # Execute operation
        if operation == "list":
            return self._execute_list(repo_path, file_pattern)
        elif operation == "read":
            return self._execute_read(repo_path, file_pattern)
        elif operation == "log":
            return self._execute_log(repo_path, file_pattern)

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

    def _execute_list(self, repo_path: str, file_pattern: str) -> Dict[str, Any]:
        """
        Execute git ls-files operation.

        Args:
            repo_path: Repository path
            file_pattern: File pattern to match

        Returns:
            Dictionary with list of files
        """
        try:
            # Git ls-files command
            result = subprocess.run(
                ["git", "-C", repo_path, "ls-files", file_pattern],
                capture_output=True,
                text=True,
                timeout=self.TIMEOUT_LIST,
                check=False
            )

            if result.returncode != 0:
                logger.error("git ls-files failed: %s", result.stderr)
                return {
                    "success": False,
                    "operation": "list",
                    "repo_path": repo_path,
                    "error": result.stderr
                }

            # Parse file list
            files = [f.strip() for f in result.stdout.split('\n') if f.strip()]

            logger.debug("Listed %d files matching '%s'", len(files), file_pattern)

            return {
                "success": True,
                "operation": "list",
                "files": files,
                "count": len(files),
                "repo_path": repo_path,
                "file_pattern": file_pattern
            }

        except subprocess.TimeoutExpired:
            logger.error("git ls-files timeout after %ds", self.TIMEOUT_LIST)
            return {
                "success": False,
                "operation": "list",
                "repo_path": repo_path,
                "error": f"Timeout after {self.TIMEOUT_LIST}s"
            }

        except Exception as e:
            logger.exception("git ls-files failed")
            return {
                "success": False,
                "operation": "list",
                "repo_path": repo_path,
                "error": str(e)
            }

    def _execute_read(self, repo_path: str, file_pattern: str) -> Dict[str, Any]:
        """
        Execute git show HEAD:file operation.

        Args:
            repo_path: Repository path
            file_pattern: File path to read

        Returns:
            Dictionary with file content
        """
        try:
            # Git show command
            result = subprocess.run(
                ["git", "-C", repo_path, "show", f"HEAD:{file_pattern}"],
                capture_output=True,
                text=True,
                timeout=self.TIMEOUT_READ,
                check=False
            )

            if result.returncode != 0:
                logger.error("git show failed: %s", result.stderr)
                return {
                    "success": False,
                    "operation": "read",
                    "repo_path": repo_path,
                    "error": result.stderr
                }

            content = result.stdout
            size_bytes = len(content.encode('utf-8'))

            logger.debug("Read %d bytes from %s", size_bytes, file_pattern)

            return {
                "success": True,
                "operation": "read",
                "content": content,
                "count": 1,
                "repo_path": repo_path,
                "file_pattern": file_pattern,
                "size_bytes": size_bytes
            }

        except subprocess.TimeoutExpired:
            logger.error("git show timeout after %ds", self.TIMEOUT_READ)
            return {
                "success": False,
                "operation": "read",
                "repo_path": repo_path,
                "error": f"Timeout after {self.TIMEOUT_READ}s"
            }

        except Exception as e:
            logger.exception("git show failed")
            return {
                "success": False,
                "operation": "read",
                "repo_path": repo_path,
                "error": str(e)
            }

    def _execute_log(self, repo_path: str, file_pattern: str) -> Dict[str, Any]:
        """
        Execute git log --oneline -- file operation.

        Args:
            repo_path: Repository path
            file_pattern: File path for log

        Returns:
            Dictionary with commit log
        """
        try:
            # Git log command
            result = subprocess.run(
                ["git", "-C", repo_path, "log", "--oneline", "--", file_pattern],
                capture_output=True,
                text=True,
                timeout=self.TIMEOUT_LOG,
                check=False
            )

            if result.returncode != 0:
                logger.error("git log failed: %s", result.stderr)
                return {
                    "success": False,
                    "operation": "log",
                    "repo_path": repo_path,
                    "error": result.stderr
                }

            # Parse commits
            commits = [c.strip() for c in result.stdout.split('\n') if c.strip()]

            logger.debug("Found %d commits for %s", len(commits), file_pattern)

            return {
                "success": True,
                "operation": "log",
                "commits": commits,
                "count": len(commits),
                "repo_path": repo_path,
                "file_pattern": file_pattern
            }

        except subprocess.TimeoutExpired:
            logger.error("git log timeout after %ds", self.TIMEOUT_LOG)
            return {
                "success": False,
                "operation": "log",
                "repo_path": repo_path,
                "error": f"Timeout after {self.TIMEOUT_LOG}s"
            }

        except Exception as e:
            logger.exception("git log failed")
            return {
                "success": False,
                "operation": "log",
                "repo_path": repo_path,
                "error": str(e)
            }

    def calculate_lq(self, execution_result: Any) -> float:
        """
        Calculate Leverage Quotient for git repository operations.

        Git operations have high LQ (9.0) because:
        - Version-controlled, reliable access
        - Built-in content tracking
        - Efficient indexing and search
        - Low cost for repository operations

        Args:
            execution_result: Result from execute()

        Returns:
            LQ score (9.0 for successful operations, 0.0 for failures)
        """
        if not isinstance(execution_result, dict):
            return 0.0

        success = execution_result.get("success", False)

        if success:
            # High LQ for git operations
            progress = 1.0
            efficiency = 0.98  # Very high efficiency with git
            cost = 0.11  # Very low cost (git is optimized)

            lq = self.validator.calculate_leverage_quotient(
                progress_towards_goal=progress,
                energy_efficiency=efficiency,
                cost=cost
            )
            return lq  # Should be approximately 9.0
        else:
            # Failed operation
            return 0.0


# Module-level convenience functions
def create_direct_path_pattern(
    validator: Optional[ConstitutionalValidator] = None
) -> DirectPathAccessPattern:
    """
    Factory function to create a DirectPathAccessPattern instance.

    Args:
        validator: Constitutional validator (creates new if None)

    Returns:
        DirectPathAccessPattern instance
    """
    return DirectPathAccessPattern(validator=validator)


def create_known_path_search_pattern(
    validator: Optional[ConstitutionalValidator] = None
) -> KnownPathSearchPattern:
    """
    Factory function to create a KnownPathSearchPattern instance.

    Args:
        validator: Constitutional validator (creates new if None)

    Returns:
        KnownPathSearchPattern instance
    """
    return KnownPathSearchPattern(validator=validator)


def create_git_repo_pattern(
    validator: Optional[ConstitutionalValidator] = None
) -> GitRepositoryFilePattern:
    """
    Factory function to create a GitRepositoryFilePattern instance.

    Args:
        validator: Constitutional validator (creates new if None)

    Returns:
        GitRepositoryFilePattern instance
    """
    return GitRepositoryFilePattern(validator=validator)


# Module metadata
__version__ = "1.0.0"
__author__ = "CCMF Contributors"
__description__ = "CCMF File Operation Patterns - PowerShell and Git subprocess patterns"

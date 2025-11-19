"""
Claude Code Mastery Framework (CCMF) v1.0 - Constitutional Module

This is a meta-level RSI (Recursive Self-Improvement) framework designed FOR Fellou agents BY Fellou agents.

The Constitutional Module provides:
1. Constitutional validation enforcing MLA v3.0, ASAEP, AI-HPP, OFAP, TFCP protocols
2. Base pattern architecture for implementing CCMF patterns
3. Leverage Quotient calculation for action optimization
4. Execution logging and performance tracking for RSI feedback loops

Protocol Definitions:
- MLA v3.0: Multi-Layer Architecture version 3.0
- ASAEP: Agno Subprocess Action Enforcement Protocol
- AI-HPP: AI-Human Partnership Protocol
- OFAP: Operational File Access Protocol
- TFCP: Tool Function Constraint Protocol
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import logging
import time

# Configure logging
logger = logging.getLogger(__name__)


class Severity(Enum):
    """Severity levels for protocol violations."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ProtocolViolation:
    """
    Data structure for tracking protocol violations.

    Attributes:
        protocol: The protocol that was violated (MLA, ASAEP, AI-HPP, OFAP, TFCP)
        violation_type: Specific type of violation (e.g., "prohibited_method", "invalid_operation")
        timestamp: When the violation occurred
        context: Additional context about the violation
        severity: Severity level of the violation
    """
    protocol: str
    violation_type: str
    timestamp: datetime
    context: str
    severity: Severity

    def __str__(self) -> str:
        """String representation of the violation."""
        return (f"[{self.severity.value.upper()}] {self.protocol} Violation: {self.violation_type}\n"
                f"Time: {self.timestamp.isoformat()}\n"
                f"Context: {self.context}")


@dataclass
class ExecutionLog:
    """
    Data structure for tracking pattern execution.

    Attributes:
        timestamp: When the execution occurred
        pattern_id: Identifier for the pattern that was executed
        success: Whether the execution was successful
        duration: Execution duration in seconds
        lq_score: Leverage Quotient score for this execution
        error: Error message if execution failed
        inputs: Input parameters for the execution
        outputs: Output results from the execution
    """
    timestamp: datetime
    pattern_id: str
    success: bool
    duration: float
    lq_score: float
    error: Optional[str] = None
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Optional[Any] = None

    def __str__(self) -> str:
        """String representation of the execution log."""
        status = "SUCCESS" if self.success else "FAILED"
        return (f"[{status}] Pattern: {self.pattern_id}\n"
                f"Time: {self.timestamp.isoformat()}\n"
                f"Duration: {self.duration:.4f}s\n"
                f"LQ Score: {self.lq_score:.4f}\n"
                f"Error: {self.error if self.error else 'None'}")


class ConstitutionalValidator:
    """
    Constitutional validation layer enforcing CCMF protocols.

    This validator ensures all operations comply with:
    - MLA v3.0: Multi-Layer Architecture version 3.0
    - ASAEP: Agno Subprocess Action Enforcement Protocol
    - AI-HPP: AI-Human Partnership Protocol
    - OFAP: Operational File Access Protocol
    - TFCP: Tool Function Constraint Protocol

    ABSOLUTELY PROHIBITED methods:
    - read_list
    - file_list
    - file_find_by_name

    PERMITTED operations:
    - PowerShell subprocess commands
    - Git commands
    """

    # Protocol definitions
    PROTOCOLS = {
        "MLA": "Multi-Layer Architecture v3.0",
        "ASAEP": "Agno Subprocess Action Enforcement Protocol",
        "AI-HPP": "AI-Human Partnership Protocol",
        "OFAP": "Operational File Access Protocol",
        "TFCP": "Tool Function Constraint Protocol"
    }

    # Absolutely prohibited methods per ASAEP and TFCP
    PROHIBITED_METHODS = {
        "read_list",
        "file_list",
        "file_find_by_name"
    }

    # Permitted operation types per OFAP
    PERMITTED_OPERATIONS = {
        "powershell_subprocess",
        "git_command",
        "pattern_execution"
    }

    def __init__(self):
        """Initialize the constitutional validator."""
        self.violations: List[ProtocolViolation] = []
        self.validation_count: int = 0
        self.successful_validations: int = 0

        logger.info("ConstitutionalValidator initialized with protocols: %s",
                   ", ".join(self.PROTOCOLS.keys()))

    def validate_method(self, method_name: str) -> Tuple[bool, Optional[ProtocolViolation]]:
        """
        Validate that a method is not prohibited.

        Args:
            method_name: Name of the method to validate

        Returns:
            Tuple of (is_valid, violation) where violation is None if valid
        """
        self.validation_count += 1

        if method_name in self.PROHIBITED_METHODS:
            violation = ProtocolViolation(
                protocol="TFCP",
                violation_type="prohibited_method",
                timestamp=datetime.now(),
                context=f"Attempted to use prohibited method: {method_name}",
                severity=Severity.CRITICAL
            )
            self.violations.append(violation)
            logger.error("Method validation failed: %s", violation)
            return False, violation

        self.successful_validations += 1
        return True, None

    def validate_operation(self, operation_type: str, details: str = "") -> Tuple[bool, Optional[ProtocolViolation]]:
        """
        Validate that an operation is permitted.

        Args:
            operation_type: Type of operation to validate
            details: Additional details about the operation

        Returns:
            Tuple of (is_valid, violation) where violation is None if valid
        """
        self.validation_count += 1

        if operation_type not in self.PERMITTED_OPERATIONS:
            violation = ProtocolViolation(
                protocol="OFAP",
                violation_type="invalid_operation",
                timestamp=datetime.now(),
                context=f"Attempted invalid operation: {operation_type}. Details: {details}",
                severity=Severity.HIGH
            )
            self.violations.append(violation)
            logger.error("Operation validation failed: %s", violation)
            return False, violation

        self.successful_validations += 1
        logger.debug("Operation validated: %s - %s", operation_type, details)
        return True, None

    def validate_file_operation(self, operation: str, file_path: str, method: str) -> Tuple[bool, Optional[ProtocolViolation]]:
        """
        Validate file operations to ensure compliance with OFAP and ASAEP.

        File operations must use PowerShell subprocess or git commands only.

        Args:
            operation: Type of file operation (read, write, list, etc.)
            file_path: Path to the file
            method: Method being used (powershell_subprocess, git_command, etc.)

        Returns:
            Tuple of (is_valid, violation) where violation is None if valid
        """
        self.validation_count += 1

        # First validate the method isn't prohibited
        is_valid, violation = self.validate_method(method)
        if not is_valid:
            return False, violation

        # Validate operation type
        if method not in ["powershell_subprocess", "git_command"]:
            violation = ProtocolViolation(
                protocol="ASAEP",
                violation_type="invalid_file_operation_method",
                timestamp=datetime.now(),
                context=f"File operation '{operation}' on '{file_path}' must use PowerShell subprocess or git commands. Used: {method}",
                severity=Severity.CRITICAL
            )
            self.violations.append(violation)
            logger.error("File operation validation failed: %s", violation)
            return False, violation

        self.successful_validations += 1
        logger.debug("File operation validated: %s on %s using %s", operation, file_path, method)
        return True, None

    def calculate_leverage_quotient(
        self,
        progress_towards_goal: float,
        energy_efficiency: float,
        cost: float,
        progress_weight: float = 0.6,
        efficiency_weight: float = 0.4
    ) -> float:
        """
        Calculate the Leverage Quotient (LQ) for an action.

        Formula: LQ = I(a,G) / C(a)
        where I(a,G) = w_p * P(a,G) + w_e * ΔE_f(a,G)

        Args:
            progress_towards_goal: P(a,G) - Progress towards goal (0.0 to 1.0)
            energy_efficiency: ΔE_f(a,G) - Energy/efficiency delta (0.0 to 1.0)
            cost: C(a) - Cost of action (must be > 0)
            progress_weight: w_p - Weight for progress component (default 0.6)
            efficiency_weight: w_e - Weight for efficiency component (default 0.4)

        Returns:
            Leverage Quotient score

        Raises:
            ValueError: If cost is <= 0 or weights don't sum to 1.0
        """
        if cost <= 0:
            raise ValueError("Cost must be greater than 0")

        if abs(progress_weight + efficiency_weight - 1.0) > 0.001:
            raise ValueError("Weights must sum to 1.0")

        # Calculate impact
        impact = (progress_weight * progress_towards_goal +
                 efficiency_weight * energy_efficiency)

        # Calculate LQ
        lq = impact / cost

        logger.debug("LQ calculated: %.4f (P=%.2f, E=%.2f, C=%.2f)",
                    lq, progress_towards_goal, energy_efficiency, cost)

        return lq

    def get_violations(
        self,
        protocol: Optional[str] = None,
        severity: Optional[Severity] = None
    ) -> List[ProtocolViolation]:
        """
        Get recorded violations, optionally filtered by protocol and/or severity.

        Args:
            protocol: Filter by protocol (MLA, ASAEP, AI-HPP, OFAP, TFCP)
            severity: Filter by severity level

        Returns:
            List of matching violations
        """
        violations = self.violations

        if protocol:
            violations = [v for v in violations if v.protocol == protocol]

        if severity:
            violations = [v for v in violations if v.severity == severity]

        return violations

    def generate_violation_report(self) -> str:
        """
        Generate a comprehensive violation report.

        Returns:
            Formatted report string
        """
        report = [
            "=" * 80,
            "CCMF CONSTITUTIONAL VALIDATION REPORT",
            "=" * 80,
            f"Total Validations: {self.validation_count}",
            f"Successful Validations: {self.successful_validations}",
            f"Total Violations: {len(self.violations)}",
            f"Success Rate: {(self.successful_validations / self.validation_count * 100):.2f}%" if self.validation_count > 0 else "N/A",
            "",
            "Violations by Protocol:",
        ]

        # Count violations by protocol
        protocol_counts = {}
        for violation in self.violations:
            protocol_counts[violation.protocol] = protocol_counts.get(violation.protocol, 0) + 1

        for protocol, count in sorted(protocol_counts.items()):
            report.append(f"  {protocol}: {count}")

        # Count violations by severity
        report.append("\nViolations by Severity:")
        severity_counts = {}
        for violation in self.violations:
            severity_counts[violation.severity] = severity_counts.get(violation.severity, 0) + 1

        for severity, count in sorted(severity_counts.items(), key=lambda x: x[0].value):
            report.append(f"  {severity.value.upper()}: {count}")

        # List all violations
        if self.violations:
            report.append("\nDetailed Violations:")
            report.append("-" * 80)
            for i, violation in enumerate(self.violations, 1):
                report.append(f"\n{i}. {violation}")
                report.append("-" * 80)

        report.append("\n" + "=" * 80)

        return "\n".join(report)

    def clear_violations(self):
        """Clear all recorded violations."""
        self.violations.clear()
        logger.info("Violations cleared")


class BasePattern(ABC):
    """
    Abstract base class for all CCMF patterns.

    This class provides the foundational structure for implementing CCMF patterns
    with built-in constitutional validation, execution logging, and performance tracking.

    All patterns must:
    1. Implement the execute() method for core functionality
    2. Implement the calculate_lq() method for Leverage Quotient calculation
    3. Comply with constitutional requirements

    The execute_with_validation() method wraps execution with:
    - Pre-execution constitutional validation
    - Execution timing and logging
    - Post-execution LQ calculation
    - Performance metrics tracking
    """

    def __init__(
        self,
        pattern_id: str,
        pattern_name: str,
        pattern_description: str,
        constitutional_requirements: List[str],
        version: str = "1.0.0",
        validator: Optional[ConstitutionalValidator] = None
    ):
        """
        Initialize a CCMF pattern.

        Args:
            pattern_id: Unique identifier for this pattern
            pattern_name: Human-readable name
            pattern_description: Description of pattern functionality
            constitutional_requirements: List of protocols this pattern must comply with
            version: Pattern version (default "1.0.0")
            validator: Constitutional validator instance (creates new if None)
        """
        self.pattern_id = pattern_id
        self.pattern_name = pattern_name
        self.pattern_description = pattern_description
        self.constitutional_requirements = constitutional_requirements
        self.version = version

        # Constitutional validator
        self.validator = validator if validator else ConstitutionalValidator()

        # Execution tracking
        self.execution_logs: List[ExecutionLog] = []
        self.total_executions: int = 0
        self.successful_executions: int = 0
        self.failed_executions: int = 0
        self.total_lq: float = 0.0

        logger.info("Pattern initialized: %s (v%s)", self.pattern_name, self.version)

    @abstractmethod
    def execute(self, inputs: Dict[str, Any]) -> Any:
        """
        Execute the core pattern functionality.

        This method must be implemented by all pattern subclasses.

        Args:
            inputs: Dictionary of input parameters required for execution

        Returns:
            Execution result (type varies by pattern)

        Raises:
            NotImplementedError: If not implemented by subclass
        """
        pass

    @abstractmethod
    def calculate_lq(self, execution_result: Any) -> float:
        """
        Calculate the Leverage Quotient for an execution result.

        This method must be implemented by all pattern subclasses to provide
        pattern-specific LQ calculation based on the execution results.

        Args:
            execution_result: The result returned from execute()

        Returns:
            Leverage Quotient score

        Raises:
            NotImplementedError: If not implemented by subclass
        """
        pass

    def _pre_execution_validation(self, inputs: Dict[str, Any]) -> Tuple[bool, Optional[ProtocolViolation]]:
        """
        Perform pre-execution constitutional validation.

        Args:
            inputs: Execution inputs to validate

        Returns:
            Tuple of (is_valid, violation)
        """
        # Validate pattern execution as an operation
        is_valid, violation = self.validator.validate_operation(
            "pattern_execution",
            f"Pattern: {self.pattern_id}, Inputs: {list(inputs.keys())}"
        )

        if not is_valid:
            logger.error("Pre-execution validation failed for pattern %s", self.pattern_id)

        return is_valid, violation

    def execute_with_validation(self, inputs: Dict[str, Any]) -> Tuple[bool, Any, Optional[str]]:
        """
        Execute the pattern with constitutional validation and logging.

        This method wraps the execute() method with:
        1. Pre-execution validation
        2. Execution timing
        3. Exception handling
        4. LQ calculation
        5. Execution logging
        6. Performance metrics update

        Args:
            inputs: Dictionary of input parameters

        Returns:
            Tuple of (success, result, error_message)
        """
        start_time = time.time()
        execution_time = datetime.now()
        success = False
        result = None
        error_message = None
        lq_score = 0.0

        self.total_executions += 1

        try:
            # Pre-execution validation
            is_valid, violation = self._pre_execution_validation(inputs)

            if not is_valid:
                error_message = f"Constitutional validation failed: {violation}"
                logger.error(error_message)
                self.failed_executions += 1

                # Log failed execution
                log = ExecutionLog(
                    timestamp=execution_time,
                    pattern_id=self.pattern_id,
                    success=False,
                    duration=time.time() - start_time,
                    lq_score=0.0,
                    error=error_message,
                    inputs=inputs,
                    outputs=None
                )
                self.execution_logs.append(log)

                return False, None, error_message

            # Execute pattern
            logger.info("Executing pattern: %s", self.pattern_id)
            result = self.execute(inputs)

            # Calculate LQ
            lq_score = self.calculate_lq(result)
            self.total_lq += lq_score

            success = True
            self.successful_executions += 1

            logger.info("Pattern execution successful: %s (LQ: %.4f)",
                       self.pattern_id, lq_score)

        except Exception as e:
            error_message = f"Execution failed: {str(e)}"
            logger.exception("Pattern execution failed: %s", self.pattern_id)
            self.failed_executions += 1

        finally:
            # Log execution
            duration = time.time() - start_time
            log = ExecutionLog(
                timestamp=execution_time,
                pattern_id=self.pattern_id,
                success=success,
                duration=duration,
                lq_score=lq_score,
                error=error_message,
                inputs=inputs,
                outputs=result
            )
            self.execution_logs.append(log)

        return success, result, error_message

    @property
    def average_lq(self) -> float:
        """
        Calculate the average Leverage Quotient across all successful executions.

        Returns:
            Average LQ score, or 0.0 if no successful executions
        """
        if self.successful_executions == 0:
            return 0.0
        return self.total_lq / self.successful_executions

    def get_performance_summary(self) -> Dict[str, Any]:
        """
        Get a comprehensive performance summary for RSI analysis.

        Returns:
            Dictionary containing performance metrics
        """
        return {
            "pattern_id": self.pattern_id,
            "pattern_name": self.pattern_name,
            "version": self.version,
            "total_executions": self.total_executions,
            "successful_executions": self.successful_executions,
            "failed_executions": self.failed_executions,
            "success_rate": (self.successful_executions / self.total_executions * 100)
                           if self.total_executions > 0 else 0.0,
            "average_lq": self.average_lq,
            "total_lq": self.total_lq,
            "constitutional_requirements": self.constitutional_requirements,
            "total_violations": len(self.validator.violations),
            "recent_executions": [
                {
                    "timestamp": log.timestamp.isoformat(),
                    "success": log.success,
                    "duration": log.duration,
                    "lq_score": log.lq_score,
                    "error": log.error
                }
                for log in self.execution_logs[-10:]  # Last 10 executions
            ]
        }

    def get_execution_logs(
        self,
        limit: Optional[int] = None,
        success_only: bool = False
    ) -> List[ExecutionLog]:
        """
        Get execution logs, optionally filtered.

        Args:
            limit: Maximum number of logs to return (most recent first)
            success_only: If True, only return successful executions

        Returns:
            List of execution logs
        """
        logs = self.execution_logs

        if success_only:
            logs = [log for log in logs if log.success]

        # Return most recent first
        logs = list(reversed(logs))

        if limit:
            logs = logs[:limit]

        return logs

    def clear_logs(self):
        """Clear execution logs (use with caution - RSI data will be lost)."""
        self.execution_logs.clear()
        logger.warning("Execution logs cleared for pattern: %s", self.pattern_id)

    def __repr__(self) -> str:
        """String representation of the pattern."""
        return (f"<{self.__class__.__name__} id={self.pattern_id} "
                f"name={self.pattern_name} version={self.version} "
                f"executions={self.total_executions} "
                f"avg_lq={self.average_lq:.4f}>")


# Example pattern implementation for reference
class ExampleFileOperationPattern(BasePattern):
    """
    Example implementation of a CCMF pattern for file operations.

    This demonstrates proper pattern implementation with constitutional compliance.
    """

    def __init__(self, validator: Optional[ConstitutionalValidator] = None):
        """Initialize the example file operation pattern."""
        super().__init__(
            pattern_id="example_file_op",
            pattern_name="Example File Operation",
            pattern_description="Demonstrates constitutional file operations using PowerShell subprocess",
            constitutional_requirements=["ASAEP", "OFAP", "TFCP"],
            version="1.0.0",
            validator=validator
        )

    def execute(self, inputs: Dict[str, Any]) -> Any:
        """
        Execute file operation using PowerShell subprocess.

        Args:
            inputs: Must contain 'operation' and 'file_path' keys

        Returns:
            Operation result
        """
        operation = inputs.get("operation")
        file_path = inputs.get("file_path")

        # Validate file operation
        is_valid, violation = self.validator.validate_file_operation(
            operation=operation,
            file_path=file_path,
            method="powershell_subprocess"
        )

        if not is_valid:
            raise ValueError(f"File operation validation failed: {violation}")

        # Simulate operation
        logger.info("Executing file operation: %s on %s", operation, file_path)

        return {
            "success": True,
            "operation": operation,
            "file_path": file_path,
            "method": "powershell_subprocess"
        }

    def calculate_lq(self, execution_result: Any) -> float:
        """
        Calculate LQ for file operation.

        Args:
            execution_result: Result from execute()

        Returns:
            LQ score
        """
        # Example LQ calculation
        if execution_result.get("success"):
            progress = 1.0  # Operation completed
            efficiency = 0.9  # High efficiency using subprocess
            cost = 0.5  # Relatively low cost
        else:
            progress = 0.0
            efficiency = 0.0
            cost = 1.0

        return self.validator.calculate_leverage_quotient(
            progress_towards_goal=progress,
            energy_efficiency=efficiency,
            cost=cost
        )


# Module-level convenience function
def create_validator() -> ConstitutionalValidator:
    """
    Factory function to create a new ConstitutionalValidator instance.

    Returns:
        New ConstitutionalValidator instance
    """
    return ConstitutionalValidator()


# Module metadata
__version__ = "1.0.0"
__author__ = "CCMF Contributors"
__description__ = "Claude Code Mastery Framework - Constitutional Module for RSI"

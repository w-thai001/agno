"""🎯 Service Orchestrator - Advanced Multi-Service Coordination System!

This sophisticated workflow demonstrates how to orchestrate multiple services with comprehensive
dependency management, parallel execution, error handling, and rollback capabilities. The system
is designed for production-grade service coordination scenarios.

Key capabilities:
- Intelligent dependency resolution and execution ordering
- Parallel execution of independent services for optimal performance
- Circuit breaker pattern for fault tolerance
- Health monitoring and status tracking
- Automatic rollback on critical failures
- Timeout management per service
- Retry logic with exponential backoff
- Result aggregation and transformation
- Comprehensive execution metrics

Use cases:
- Microservices orchestration
- ETL pipeline coordination
- Multi-stage deployment workflows
- Distributed system initialization
- Service mesh coordination
- API gateway orchestration
- Data processing pipelines
- Multi-cloud service management

Run `pip install agno openai sqlalchemy` to install dependencies.
"""

import asyncio
import time
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from enum import Enum
from textwrap import dedent
from typing import Any, Callable, Dict, Iterator, List, Optional, Set

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.storage.sqlite import SqliteStorage
from agno.utils.log import logger
from agno.utils.pprint import pprint_run_response
from agno.workflow import RunEvent, RunResponse, Workflow
from pydantic import BaseModel, Field


# ============================================================================
# Enums and Constants
# ============================================================================


class ExecutionMode(str, Enum):
    """Execution mode for service orchestration."""

    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    HYBRID = "hybrid"  # Parallel where possible, sequential for dependencies


class ServiceStatus(str, Enum):
    """Status of a service execution."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    ROLLED_BACK = "rolled_back"
    TIMEOUT = "timeout"


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Circuit is open, requests fail fast
    HALF_OPEN = "half_open"  # Testing if service recovered


# ============================================================================
# Pydantic Models
# ============================================================================


class TimeoutConfig(BaseModel):
    """Timeout configuration for a service."""

    execution_timeout: int = Field(
        default=30, description="Maximum execution time in seconds"
    )
    health_check_timeout: int = Field(
        default=5, description="Health check timeout in seconds"
    )


class RetryConfig(BaseModel):
    """Retry configuration with exponential backoff."""

    max_attempts: int = Field(default=3, description="Maximum retry attempts")
    initial_delay: float = Field(
        default=1.0, description="Initial delay in seconds before first retry"
    )
    max_delay: float = Field(default=60.0, description="Maximum delay between retries")
    exponential_base: float = Field(
        default=2.0, description="Base for exponential backoff"
    )
    jitter: bool = Field(
        default=True, description="Add random jitter to prevent thundering herd"
    )


class CircuitBreakerConfig(BaseModel):
    """Circuit breaker configuration."""

    failure_threshold: int = Field(
        default=5, description="Number of failures before opening circuit"
    )
    success_threshold: int = Field(
        default=2, description="Number of successes to close circuit from half-open"
    )
    timeout: int = Field(
        default=60, description="Time in seconds before attempting to close circuit"
    )
    enabled: bool = Field(default=True, description="Enable circuit breaker")


class HealthCheckConfig(BaseModel):
    """Health check configuration."""

    enabled: bool = Field(default=True, description="Enable health checks")
    endpoint: Optional[str] = Field(
        default=None, description="Health check endpoint URL"
    )
    interval: int = Field(
        default=30, description="Health check interval in seconds"
    )
    healthy_threshold: int = Field(
        default=2, description="Consecutive successes to mark healthy"
    )
    unhealthy_threshold: int = Field(
        default=3, description="Consecutive failures to mark unhealthy"
    )


class RollbackStrategy(BaseModel):
    """Rollback configuration."""

    enabled: bool = Field(default=True, description="Enable automatic rollback")
    on_any_failure: bool = Field(
        default=False, description="Rollback on any service failure"
    )
    critical_services: List[str] = Field(
        default_factory=list, description="Services whose failure triggers rollback"
    )
    max_concurrent_rollbacks: int = Field(
        default=5, description="Maximum concurrent rollback operations"
    )


class ServiceConfig(BaseModel):
    """Configuration for a service to be orchestrated."""

    name: str = Field(..., description="Unique service identifier")
    description: Optional[str] = Field(
        default=None, description="Service description"
    )
    executor: Callable = Field(
        ..., description="Function to execute the service"
    )
    dependencies: List[str] = Field(
        default_factory=list, description="List of service names this depends on"
    )
    timeout_config: TimeoutConfig = Field(
        default_factory=TimeoutConfig, description="Timeout settings"
    )
    retry_config: RetryConfig = Field(
        default_factory=RetryConfig, description="Retry settings"
    )
    rollback_handler: Optional[Callable] = Field(
        default=None, description="Function to rollback this service"
    )
    health_check: Optional[Callable] = Field(
        default=None, description="Health check function"
    )
    critical: bool = Field(
        default=False, description="Whether failure should trigger rollback"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional service metadata"
    )

    class Config:
        arbitrary_types_allowed = True


class ServiceResult(BaseModel):
    """Result from a service execution."""

    service_name: str = Field(..., description="Name of the service")
    status: ServiceStatus = Field(..., description="Execution status")
    result: Optional[Any] = Field(default=None, description="Service result data")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    start_time: float = Field(..., description="Execution start timestamp")
    end_time: float = Field(..., description="Execution end timestamp")
    duration: float = Field(..., description="Execution duration in seconds")
    attempts: int = Field(default=1, description="Number of execution attempts")
    rolled_back: bool = Field(
        default=False, description="Whether service was rolled back"
    )

    class Config:
        arbitrary_types_allowed = True


class ExecutionMetrics(BaseModel):
    """Metrics for the orchestration execution."""

    total_services: int = Field(..., description="Total number of services")
    successful_services: int = Field(
        default=0, description="Number of successful services"
    )
    failed_services: int = Field(default=0, description="Number of failed services")
    skipped_services: int = Field(default=0, description="Number of skipped services")
    rolled_back_services: int = Field(
        default=0, description="Number of rolled back services"
    )
    total_duration: float = Field(..., description="Total execution time in seconds")
    parallel_efficiency: float = Field(
        default=0.0,
        description="Efficiency gain from parallel execution (0.0-1.0)",
    )
    circuit_breaker_trips: int = Field(
        default=0, description="Number of circuit breaker activations"
    )
    total_retries: int = Field(default=0, description="Total number of retries")


class OrchestrationResult(BaseModel):
    """Comprehensive result from the orchestration."""

    status: str = Field(..., description="Overall orchestration status")
    execution_results: Dict[str, ServiceResult] = Field(
        default_factory=dict, description="Results from all services"
    )
    execution_metrics: ExecutionMetrics = Field(
        ..., description="Performance metrics"
    )
    failed_services: List[str] = Field(
        default_factory=list, description="List of failed service names"
    )
    rollback_status: Optional[Dict[str, bool]] = Field(
        default=None, description="Rollback status for each service"
    )
    execution_plan: List[List[str]] = Field(
        default_factory=list, description="Execution order (batches of services)"
    )

    class Config:
        arbitrary_types_allowed = True


# ============================================================================
# Circuit Breaker Implementation
# ============================================================================


@dataclass
class CircuitBreaker:
    """Circuit breaker for fault tolerance."""

    config: CircuitBreakerConfig
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[float] = None
    trip_count: int = 0

    def record_success(self) -> None:
        """Record a successful execution."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                logger.info("Circuit breaker closing after successful recovery")
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.success_count = 0
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0

    def record_failure(self) -> None:
        """Record a failed execution."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.state == CircuitState.CLOSED:
            if self.failure_count >= self.config.failure_threshold:
                logger.warning(
                    f"Circuit breaker opening after {self.failure_count} failures"
                )
                self.state = CircuitState.OPEN
                self.trip_count += 1
        elif self.state == CircuitState.HALF_OPEN:
            logger.warning("Circuit breaker re-opening after failure in half-open state")
            self.state = CircuitState.OPEN
            self.success_count = 0

    def can_execute(self) -> bool:
        """Check if execution is allowed."""
        if not self.config.enabled:
            return True

        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            if (
                self.last_failure_time
                and time.time() - self.last_failure_time >= self.config.timeout
            ):
                logger.info("Circuit breaker entering half-open state")
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
                return True
            return False

        # Half-open state
        return True

    def get_trip_count(self) -> int:
        """Get the number of times circuit has tripped."""
        return self.trip_count


# ============================================================================
# Service Orchestrator Workflow
# ============================================================================


class ServiceOrchestrator(Workflow):
    """Advanced workflow for orchestrating multiple services with comprehensive management capabilities.

    This workflow provides production-ready service orchestration with:
    - Intelligent dependency resolution using topological sorting
    - Parallel execution of independent services
    - Circuit breaker pattern for fault tolerance
    - Health monitoring and status tracking
    - Automatic rollback on failures
    - Retry logic with exponential backoff
    - Comprehensive metrics and reporting
    """

    description: str = dedent("""\
    A sophisticated service orchestrator that coordinates multiple services with
    dependency management, parallel execution, error handling, and rollback capabilities.
    Designed for production-grade microservices orchestration, ETL pipelines, and
    complex distributed system coordination.
    """)

    # Monitoring Agent: Tracks service health and status
    monitor_agent: Agent = Agent(
        model=OpenAIChat(id="gpt-4o-mini"),
        description=dedent("""\
        You are ServiceMonitor-X, a specialized monitoring and observability agent.
        Your expertise includes:
        - Real-time service health tracking
        - Performance metrics analysis
        - Anomaly detection
        - Status reporting and alerting
        - Resource utilization monitoring\
        """),
        instructions=dedent("""\
        1. Monitor service execution in real-time
        2. Track performance metrics and health status
        3. Identify anomalies and potential issues
        4. Generate comprehensive status reports
        5. Alert on critical failures or degradation\
        """),
    )

    # Coordinator Agent: Manages orchestration decisions
    coordinator_agent: Agent = Agent(
        model=OpenAIChat(id="gpt-4o"),
        description=dedent("""\
        You are OrchestrationMaster-X, an elite service coordination specialist.
        Your strengths include:
        - Intelligent execution planning
        - Dependency resolution
        - Resource optimization
        - Error recovery strategies
        - Rollback coordination\
        """),
        instructions=dedent("""\
        1. Analyze service dependencies and create optimal execution plans
        2. Coordinate parallel execution for maximum efficiency
        3. Monitor execution and make real-time decisions
        4. Handle failures with appropriate recovery strategies
        5. Coordinate rollbacks when necessary
        6. Generate comprehensive execution reports\
        """),
        markdown=True,
    )

    def __init__(self, **kwargs):
        """Initialize the ServiceOrchestrator workflow."""
        super().__init__(**kwargs)
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._health_status: Dict[str, bool] = {}
        self._execution_history: List[ServiceResult] = []

    def run(
        self,
        services: List[ServiceConfig],
        execution_mode: ExecutionMode = ExecutionMode.HYBRID,
        circuit_breaker_config: Optional[CircuitBreakerConfig] = None,
        health_check_config: Optional[HealthCheckConfig] = None,
        rollback_strategy: Optional[RollbackStrategy] = None,
        max_parallel_workers: int = 5,
    ) -> Iterator[RunResponse]:
        """Execute the service orchestration workflow.

        Args:
            services: List of services to orchestrate
            execution_mode: Sequential, parallel, or hybrid execution
            circuit_breaker_config: Circuit breaker configuration
            health_check_config: Health check configuration
            rollback_strategy: Rollback configuration
            max_parallel_workers: Maximum number of parallel workers

        Yields:
            RunResponse objects with orchestration progress and results
        """
        logger.info(
            f"Starting orchestration of {len(services)} services in {execution_mode} mode"
        )
        start_time = time.time()

        # Initialize configurations
        cb_config = circuit_breaker_config or CircuitBreakerConfig()
        hc_config = health_check_config or HealthCheckConfig()
        rb_strategy = rollback_strategy or RollbackStrategy()

        # Initialize circuit breakers
        self._initialize_circuit_breakers(services, cb_config)

        # Validate service dependencies
        validation_error = self._validate_dependencies(services)
        if validation_error:
            yield RunResponse(
                event=RunEvent.workflow_completed,
                content=f"❌ Dependency validation failed: {validation_error}",
            )
            return

        # Create execution plan
        execution_plan = self._create_execution_plan(services, execution_mode)
        logger.info(f"Execution plan created with {len(execution_plan)} stages")

        yield RunResponse(
            content=f"📋 Execution plan created: {len(execution_plan)} stages for {len(services)} services"
        )

        # Perform health checks
        if hc_config.enabled:
            health_check_results = self._perform_health_checks(services, hc_config)
            unhealthy = [s for s, h in health_check_results.items() if not h]
            if unhealthy:
                yield RunResponse(
                    content=f"⚠️  Warning: {len(unhealthy)} services failed health checks: {unhealthy}"
                )

        # Execute services according to plan
        execution_results: Dict[str, ServiceResult] = {}
        failed_services: List[str] = []
        total_retries = 0
        circuit_breaker_trips = 0

        for stage_num, stage_services in enumerate(execution_plan, 1):
            yield RunResponse(
                content=f"\n🚀 Stage {stage_num}/{len(execution_plan)}: Executing {len(stage_services)} service(s)"
            )

            # Execute services in this stage (parallel if multiple)
            stage_results = self._execute_stage(
                stage_services,
                services,
                execution_results,
                max_parallel_workers,
            )

            # Process results
            for service_name, result in stage_results.items():
                execution_results[service_name] = result
                total_retries += result.attempts - 1

                if result.status == ServiceStatus.SUCCESS:
                    yield RunResponse(
                        content=f"  ✅ {service_name}: Success ({result.duration:.2f}s, {result.attempts} attempt(s))"
                    )
                elif result.status == ServiceStatus.FAILED:
                    failed_services.append(service_name)
                    yield RunResponse(
                        content=f"  ❌ {service_name}: Failed - {result.error}"
                    )

                    # Check if we need to rollback
                    service_config = next(
                        (s for s in services if s.name == service_name), None
                    )
                    if service_config and (
                        rb_strategy.on_any_failure
                        or service_config.critical
                        or service_name in rb_strategy.critical_services
                    ):
                        yield RunResponse(
                            content=f"🔄 Critical service {service_name} failed, initiating rollback..."
                        )
                        rollback_status = self._perform_rollback(
                            services, execution_results, rb_strategy
                        )
                        break

        # Calculate metrics
        end_time = time.time()
        total_duration = end_time - start_time

        # Count circuit breaker trips
        for cb in self._circuit_breakers.values():
            circuit_breaker_trips += cb.get_trip_count()

        metrics = ExecutionMetrics(
            total_services=len(services),
            successful_services=sum(
                1
                for r in execution_results.values()
                if r.status == ServiceStatus.SUCCESS
            ),
            failed_services=len(failed_services),
            skipped_services=sum(
                1
                for r in execution_results.values()
                if r.status == ServiceStatus.SKIPPED
            ),
            rolled_back_services=sum(
                1 for r in execution_results.values() if r.rolled_back
            ),
            total_duration=total_duration,
            parallel_efficiency=self._calculate_efficiency(
                execution_results, total_duration
            ),
            circuit_breaker_trips=circuit_breaker_trips,
            total_retries=total_retries,
        )

        # Create final result
        overall_status = (
            "SUCCESS" if len(failed_services) == 0 else "PARTIAL_SUCCESS"
            if metrics.successful_services > 0 else "FAILED"
        )

        orchestration_result = OrchestrationResult(
            status=overall_status,
            execution_results=execution_results,
            execution_metrics=metrics,
            failed_services=failed_services,
            execution_plan=execution_plan,
        )

        # Generate summary report
        yield RunResponse(
            content=self._generate_summary_report(orchestration_result)
        )

        # Store result in session state
        self.session_state["last_orchestration_result"] = orchestration_result.model_dump()
        self._execution_history.extend(execution_results.values())

        yield RunResponse(
            event=RunEvent.workflow_completed,
            content=f"\n✨ Orchestration completed with status: {overall_status}",
        )

    def _initialize_circuit_breakers(
        self, services: List[ServiceConfig], config: CircuitBreakerConfig
    ) -> None:
        """Initialize circuit breakers for all services."""
        for service in services:
            self._circuit_breakers[service.name] = CircuitBreaker(config=config)

    def _validate_dependencies(self, services: List[ServiceConfig]) -> Optional[str]:
        """Validate that all service dependencies exist and there are no cycles."""
        service_names = {s.name for s in services}

        # Check for missing dependencies
        for service in services:
            for dep in service.dependencies:
                if dep not in service_names:
                    return f"Service '{service.name}' depends on non-existent service '{dep}'"

        # Check for circular dependencies
        if self._has_circular_dependencies(services):
            return "Circular dependency detected in service graph"

        return None

    def _has_circular_dependencies(self, services: List[ServiceConfig]) -> bool:
        """Check for circular dependencies using DFS."""
        graph = {s.name: set(s.dependencies) for s in services}
        visited = set()
        rec_stack = set()

        def has_cycle(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)

            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        for service in services:
            if service.name not in visited:
                if has_cycle(service.name):
                    return True
        return False

    def _create_execution_plan(
        self, services: List[ServiceConfig], mode: ExecutionMode
    ) -> List[List[str]]:
        """Create execution plan based on dependencies and execution mode.

        Returns a list of stages, where each stage contains services that can be executed in parallel.
        """
        if mode == ExecutionMode.SEQUENTIAL:
            # Simple sequential execution based on topological sort
            sorted_services = self._topological_sort(services)
            return [[s] for s in sorted_services]

        # For PARALLEL and HYBRID modes, group services by dependency level
        return self._create_parallel_execution_plan(services)

    def _topological_sort(self, services: List[ServiceConfig]) -> List[str]:
        """Perform topological sort on services based on dependencies."""
        graph = {s.name: set(s.dependencies) for s in services}
        in_degree = {s.name: len(s.dependencies) for s in services}
        queue = deque([s.name for s in services if len(s.dependencies) == 0])
        result = []

        while queue:
            node = queue.popleft()
            result.append(node)

            # Reduce in-degree for dependent services
            for service in services:
                if node in service.dependencies:
                    in_degree[service.name] -= 1
                    if in_degree[service.name] == 0:
                        queue.append(service.name)

        return result

    def _create_parallel_execution_plan(
        self, services: List[ServiceConfig]
    ) -> List[List[str]]:
        """Create execution plan with maximum parallelization.

        Services with no dependencies can run in parallel.
        Each subsequent stage runs services whose dependencies have completed.
        """
        graph = {s.name: set(s.dependencies) for s in services}
        completed = set()
        stages = []

        while len(completed) < len(services):
            # Find all services that can run in this stage
            current_stage = []
            for service in services:
                if service.name not in completed:
                    # Check if all dependencies are completed
                    if all(dep in completed for dep in service.dependencies):
                        current_stage.append(service.name)

            if not current_stage:
                # This shouldn't happen if validation passed
                logger.error("Unable to create execution plan - possible circular dependency")
                break

            stages.append(current_stage)
            completed.update(current_stage)

        return stages

    def _perform_health_checks(
        self, services: List[ServiceConfig], config: HealthCheckConfig
    ) -> Dict[str, bool]:
        """Perform health checks on all services."""
        results = {}
        for service in services:
            if service.health_check:
                try:
                    is_healthy = service.health_check()
                    results[service.name] = is_healthy
                    self._health_status[service.name] = is_healthy
                except Exception as e:
                    logger.warning(
                        f"Health check failed for {service.name}: {str(e)}"
                    )
                    results[service.name] = False
                    self._health_status[service.name] = False
            else:
                results[service.name] = True  # Assume healthy if no check defined

        return results

    def _execute_stage(
        self,
        stage_services: List[str],
        all_services: List[ServiceConfig],
        completed_results: Dict[str, ServiceResult],
        max_workers: int,
    ) -> Dict[str, ServiceResult]:
        """Execute all services in a stage (in parallel if multiple)."""
        service_configs = {s.name: s for s in all_services}
        results = {}

        if len(stage_services) == 1:
            # Single service - execute directly
            service_name = stage_services[0]
            service_config = service_configs[service_name]
            results[service_name] = self._execute_service(
                service_config, completed_results
            )
        else:
            # Multiple services - execute in parallel
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(
                        self._execute_service,
                        service_configs[svc_name],
                        completed_results,
                    ): svc_name
                    for svc_name in stage_services
                }

                for future in as_completed(futures):
                    service_name = futures[future]
                    try:
                        results[service_name] = future.result()
                    except Exception as e:
                        logger.error(
                            f"Unexpected error executing {service_name}: {str(e)}"
                        )
                        results[service_name] = ServiceResult(
                            service_name=service_name,
                            status=ServiceStatus.FAILED,
                            error=f"Unexpected execution error: {str(e)}",
                            start_time=time.time(),
                            end_time=time.time(),
                            duration=0.0,
                        )

        return results

    def _execute_service(
        self,
        service: ServiceConfig,
        completed_results: Dict[str, ServiceResult],
    ) -> ServiceResult:
        """Execute a single service with retry logic and circuit breaker."""
        circuit_breaker = self._circuit_breakers.get(service.name)

        # Check circuit breaker
        if circuit_breaker and not circuit_breaker.can_execute():
            logger.warning(
                f"Circuit breaker open for {service.name}, skipping execution"
            )
            return ServiceResult(
                service_name=service.name,
                status=ServiceStatus.SKIPPED,
                error="Circuit breaker open",
                start_time=time.time(),
                end_time=time.time(),
                duration=0.0,
            )

        # Retry loop
        last_error = None
        for attempt in range(service.retry_config.max_attempts):
            start_time = time.time()

            try:
                # Execute the service
                logger.info(
                    f"Executing {service.name} (attempt {attempt + 1}/{service.retry_config.max_attempts})"
                )

                # Prepare input data from dependencies
                dependency_results = {
                    dep: completed_results[dep].result
                    for dep in service.dependencies
                    if dep in completed_results
                }

                # Execute with timeout
                result = self._execute_with_timeout(
                    service.executor,
                    dependency_results,
                    service.timeout_config.execution_timeout,
                )

                end_time = time.time()
                duration = end_time - start_time

                # Success!
                if circuit_breaker:
                    circuit_breaker.record_success()

                return ServiceResult(
                    service_name=service.name,
                    status=ServiceStatus.SUCCESS,
                    result=result,
                    start_time=start_time,
                    end_time=end_time,
                    duration=duration,
                    attempts=attempt + 1,
                )

            except TimeoutError as e:
                end_time = time.time()
                last_error = f"Execution timeout after {service.timeout_config.execution_timeout}s"
                logger.warning(f"{service.name} attempt {attempt + 1} timed out")

            except Exception as e:
                end_time = time.time()
                last_error = str(e)
                logger.warning(
                    f"{service.name} attempt {attempt + 1} failed: {last_error}"
                )

            # Record failure
            if circuit_breaker:
                circuit_breaker.record_failure()

            # Calculate backoff delay
            if attempt < service.retry_config.max_attempts - 1:
                delay = self._calculate_backoff_delay(service.retry_config, attempt)
                logger.info(f"Retrying {service.name} in {delay:.2f}s")
                time.sleep(delay)

        # All attempts failed
        return ServiceResult(
            service_name=service.name,
            status=ServiceStatus.FAILED,
            error=last_error or "Unknown error",
            start_time=start_time,
            end_time=end_time,
            duration=end_time - start_time,
            attempts=service.retry_config.max_attempts,
        )

    def _execute_with_timeout(
        self, func: Callable, args: Dict[str, Any], timeout: int
    ) -> Any:
        """Execute a function with a timeout."""
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(func, args)
            try:
                return future.result(timeout=timeout)
            except TimeoutError:
                future.cancel()
                raise TimeoutError(f"Execution exceeded timeout of {timeout}s")

    def _calculate_backoff_delay(
        self, config: RetryConfig, attempt: int
    ) -> float:
        """Calculate exponential backoff delay with jitter."""
        delay = min(
            config.initial_delay * (config.exponential_base ** attempt),
            config.max_delay,
        )

        if config.jitter:
            import random
            delay *= random.uniform(0.5, 1.5)

        return delay

    def _perform_rollback(
        self,
        services: List[ServiceConfig],
        execution_results: Dict[str, ServiceResult],
        strategy: RollbackStrategy,
    ) -> Dict[str, bool]:
        """Perform rollback for executed services."""
        if not strategy.enabled:
            return {}

        logger.info("Starting rollback process")
        rollback_status = {}

        # Get services that were successfully executed (in reverse order)
        successful_services = [
            name
            for name, result in execution_results.items()
            if result.status == ServiceStatus.SUCCESS
        ]
        successful_services.reverse()

        # Perform rollbacks
        for service_name in successful_services:
            service_config = next(
                (s for s in services if s.name == service_name), None
            )

            if service_config and service_config.rollback_handler:
                try:
                    logger.info(f"Rolling back {service_name}")
                    service_config.rollback_handler(
                        execution_results[service_name].result
                    )
                    rollback_status[service_name] = True

                    # Update result
                    execution_results[service_name].rolled_back = True

                except Exception as e:
                    logger.error(f"Rollback failed for {service_name}: {str(e)}")
                    rollback_status[service_name] = False
            else:
                logger.warning(
                    f"No rollback handler for {service_name}, skipping"
                )
                rollback_status[service_name] = False

        return rollback_status

    def _calculate_efficiency(
        self, results: Dict[str, ServiceResult], total_duration: float
    ) -> float:
        """Calculate parallel execution efficiency."""
        if not results or total_duration == 0:
            return 0.0

        # Sum of all individual service durations
        sequential_duration = sum(r.duration for r in results.values())

        # Efficiency is the ratio of sequential time to actual time
        # 1.0 means perfect parallelization, 0.0 means no benefit
        efficiency = (
            sequential_duration / total_duration - 1.0
        ) / max(len(results) - 1, 1)

        return max(0.0, min(1.0, efficiency))

    def _generate_summary_report(self, result: OrchestrationResult) -> str:
        """Generate a comprehensive summary report."""
        metrics = result.execution_metrics

        report = dedent(f"""\

        ═══════════════════════════════════════════════════════════════
        📊 SERVICE ORCHESTRATION SUMMARY
        ═══════════════════════════════════════════════════════════════

        Overall Status: {result.status}

        📈 Execution Metrics:
        ─────────────────────────────────────────────────────────────
        • Total Services:        {metrics.total_services}
        • Successful:            {metrics.successful_services} ✅
        • Failed:                {metrics.failed_services} ❌
        • Skipped:               {metrics.skipped_services} ⏭️
        • Rolled Back:           {metrics.rolled_back_services} 🔄

        ⚡ Performance:
        ─────────────────────────────────────────────────────────────
        • Total Duration:        {metrics.total_duration:.2f}s
        • Parallel Efficiency:   {metrics.parallel_efficiency:.1%}
        • Circuit Breaker Trips: {metrics.circuit_breaker_trips}
        • Total Retries:         {metrics.total_retries}

        📋 Execution Plan:
        ─────────────────────────────────────────────────────────────
        """)

        for i, stage in enumerate(result.execution_plan, 1):
            report += f"Stage {i}: {', '.join(stage)}\n        "

        if result.failed_services:
            report += dedent(f"""

        ❌ Failed Services:
        ─────────────────────────────────────────────────────────────
        """)
            for service_name in result.failed_services:
                service_result = result.execution_results[service_name]
                report += f"• {service_name}: {service_result.error}\n        "

        report += "\n        ═══════════════════════════════════════════════════════════════\n        "

        return report

    def get_execution_history(self) -> List[ServiceResult]:
        """Get the execution history."""
        return self._execution_history

    def get_circuit_breaker_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all circuit breakers."""
        return {
            name: {
                "state": cb.state.value,
                "failure_count": cb.failure_count,
                "trip_count": cb.trip_count,
            }
            for name, cb in self._circuit_breakers.items()
        }


# ============================================================================
# Example Usage
# ============================================================================


if __name__ == "__main__":
    import random

    # Define example service functions
    def database_init(deps: Dict[str, Any]) -> Dict[str, Any]:
        """Initialize database service."""
        logger.info("Initializing database...")
        time.sleep(random.uniform(0.5, 1.5))
        return {"db_connection": "postgresql://localhost:5432/mydb", "status": "ready"}

    def cache_init(deps: Dict[str, Any]) -> Dict[str, Any]:
        """Initialize cache service."""
        logger.info("Initializing cache...")
        time.sleep(random.uniform(0.3, 1.0))
        return {"redis_connection": "redis://localhost:6379", "status": "ready"}

    def api_server_start(deps: Dict[str, Any]) -> Dict[str, Any]:
        """Start API server (depends on database and cache)."""
        logger.info("Starting API server...")
        db_info = deps.get("database", {})
        cache_info = deps.get("cache", {})
        time.sleep(random.uniform(1.0, 2.0))
        return {
            "api_url": "http://localhost:8000",
            "status": "running",
            "db": db_info,
            "cache": cache_info,
        }

    def worker_pool_start(deps: Dict[str, Any]) -> Dict[str, Any]:
        """Start worker pool (depends on database and cache)."""
        logger.info("Starting worker pool...")
        time.sleep(random.uniform(0.8, 1.5))
        return {"workers": 4, "status": "running"}

    def monitoring_start(deps: Dict[str, Any]) -> Dict[str, Any]:
        """Start monitoring (depends on all other services)."""
        logger.info("Starting monitoring...")
        time.sleep(random.uniform(0.5, 1.0))
        return {"monitoring_url": "http://localhost:9090", "status": "active"}

    # Rollback handlers
    def database_rollback(result: Dict[str, Any]) -> None:
        """Rollback database initialization."""
        logger.info("Rolling back database initialization...")
        time.sleep(0.2)

    def cache_rollback(result: Dict[str, Any]) -> None:
        """Rollback cache initialization."""
        logger.info("Rolling back cache initialization...")
        time.sleep(0.2)

    def api_server_rollback(result: Dict[str, Any]) -> None:
        """Rollback API server."""
        logger.info("Stopping API server...")
        time.sleep(0.3)

    # Health check functions
    def database_health() -> bool:
        """Check database health."""
        return True

    def cache_health() -> bool:
        """Check cache health."""
        return True

    # Define services
    services = [
        ServiceConfig(
            name="database",
            description="PostgreSQL database initialization",
            executor=database_init,
            dependencies=[],
            rollback_handler=database_rollback,
            health_check=database_health,
            critical=True,
            retry_config=RetryConfig(max_attempts=3, initial_delay=1.0),
        ),
        ServiceConfig(
            name="cache",
            description="Redis cache initialization",
            executor=cache_init,
            dependencies=[],
            rollback_handler=cache_rollback,
            health_check=cache_health,
            critical=True,
            retry_config=RetryConfig(max_attempts=3, initial_delay=1.0),
        ),
        ServiceConfig(
            name="api_server",
            description="REST API server",
            executor=api_server_start,
            dependencies=["database", "cache"],
            rollback_handler=api_server_rollback,
            critical=True,
            timeout_config=TimeoutConfig(execution_timeout=5),
        ),
        ServiceConfig(
            name="worker_pool",
            description="Background worker pool",
            executor=worker_pool_start,
            dependencies=["database", "cache"],
            critical=False,
            timeout_config=TimeoutConfig(execution_timeout=5),
        ),
        ServiceConfig(
            name="monitoring",
            description="Monitoring and observability",
            executor=monitoring_start,
            dependencies=["api_server", "worker_pool"],
            critical=False,
        ),
    ]

    # Initialize the orchestrator
    orchestrator = ServiceOrchestrator(
        session_id="service-orchestration-demo",
        storage=SqliteStorage(
            table_name="service_orchestrator_workflows",
            db_file="tmp/agno_workflows.db",
        ),
        debug_mode=True,
    )

    # Execute orchestration
    print("\n🎯 Starting Service Orchestration Demo\n")
    print("=" * 70)

    result = orchestrator.run(
        services=services,
        execution_mode=ExecutionMode.HYBRID,
        circuit_breaker_config=CircuitBreakerConfig(
            failure_threshold=3,
            timeout=30,
            enabled=True,
        ),
        rollback_strategy=RollbackStrategy(
            enabled=True,
            on_any_failure=False,
            critical_services=["database", "cache", "api_server"],
        ),
        max_parallel_workers=3,
    )

    # Display results
    pprint_run_response(result, markdown=True)

    # Display circuit breaker status
    print("\n📊 Circuit Breaker Status:")
    print("=" * 70)
    cb_status = orchestrator.get_circuit_breaker_status()
    for service, status in cb_status.items():
        print(f"{service}: {status}")

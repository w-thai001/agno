"""Service Orchestrator FSA - Core Infrastructure Track

This module provides a finite state automaton-based service orchestrator for managing
service lifecycles, dependencies, health monitoring, and failure recovery.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from uuid import uuid4

from agno.utils.log import logger


class ServiceState(Enum):
    """Service states in the FSA"""

    UNREGISTERED = "unregistered"
    REGISTERED = "registered"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"
    RECOVERING = "recovering"


class HealthStatus(Enum):
    """Health check status"""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


@dataclass
class ServiceConfig:
    """Configuration for a service"""

    name: str
    start_handler: Optional[Callable] = None
    stop_handler: Optional[Callable] = None
    health_check: Optional[Callable] = None
    dependencies: List[str] = field(default_factory=list)
    restart_on_failure: bool = True
    max_restart_attempts: int = 3
    restart_delay: float = 1.0
    startup_timeout: float = 30.0
    shutdown_timeout: float = 10.0
    health_check_interval: float = 5.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ServiceInstance:
    """Runtime instance of a service"""

    config: ServiceConfig
    service_id: str = field(default_factory=lambda: str(uuid4()))
    state: ServiceState = ServiceState.UNREGISTERED
    health_status: HealthStatus = HealthStatus.UNKNOWN
    restart_count: int = 0
    last_health_check: float = 0.0
    last_state_change: float = field(default_factory=time.time)
    error_message: Optional[str] = None
    runtime_data: Dict[str, Any] = field(default_factory=dict)


class ServiceOrchestrator:
    """
    FSA-based Service Orchestrator for Core Infrastructure

    Features:
    - Service lifecycle management (start, stop, restart)
    - Service dependency resolution and ordering
    - Health monitoring and status tracking
    - Graceful shutdown coordination
    - Service registry with auto-discovery
    - Failure handling and recovery
    """

    def __init__(
        self,
        name: str = "ServiceOrchestrator",
        auto_start: bool = True,
        shutdown_grace_period: float = 30.0,
    ):
        self.name = name
        self.auto_start = auto_start
        self.shutdown_grace_period = shutdown_grace_period

        # Service registry
        self._services: Dict[str, ServiceInstance] = {}
        self._service_name_to_id: Dict[str, str] = {}

        # Monitoring tasks
        self._health_check_tasks: Dict[str, asyncio.Task] = {}
        self._running = False
        self._shutdown_event = asyncio.Event()

        logger.info(f"ServiceOrchestrator '{name}' initialized")

    def register_service(self, config: ServiceConfig) -> str:
        """
        Register a service with the orchestrator

        Args:
            config: Service configuration

        Returns:
            Service ID
        """
        if config.name in self._service_name_to_id:
            raise ValueError(f"Service '{config.name}' already registered")

        instance = ServiceInstance(config=config, state=ServiceState.REGISTERED)
        self._services[instance.service_id] = instance
        self._service_name_to_id[config.name] = instance.service_id

        logger.info(f"Service '{config.name}' registered with ID {instance.service_id}")
        return instance.service_id

    def unregister_service(self, service_name: str) -> None:
        """
        Unregister a service from the orchestrator

        Args:
            service_name: Name of the service to unregister
        """
        service_id = self._service_name_to_id.get(service_name)
        if not service_id:
            raise ValueError(f"Service '{service_name}' not found")

        instance = self._services[service_id]
        if instance.state not in [ServiceState.STOPPED, ServiceState.FAILED, ServiceState.REGISTERED]:
            raise ValueError(f"Cannot unregister service '{service_name}' in state {instance.state}")

        # Clean up
        if service_id in self._health_check_tasks:
            self._health_check_tasks[service_id].cancel()
            del self._health_check_tasks[service_id]

        del self._services[service_id]
        del self._service_name_to_id[service_name]

        logger.info(f"Service '{service_name}' unregistered")

    def get_service(self, service_name: str) -> Optional[ServiceInstance]:
        """Get service instance by name"""
        service_id = self._service_name_to_id.get(service_name)
        return self._services.get(service_id) if service_id else None

    def list_services(self) -> List[ServiceInstance]:
        """List all registered services"""
        return list(self._services.values())

    def _resolve_dependencies(self, service_name: str) -> List[str]:
        """
        Resolve service dependencies in startup order

        Args:
            service_name: Name of the service

        Returns:
            List of service names in dependency order
        """
        visited: Set[str] = set()
        order: List[str] = []

        def visit(name: str, path: Set[str]):
            if name in path:
                raise ValueError(f"Circular dependency detected: {' -> '.join(path)} -> {name}")
            if name in visited:
                return

            instance = self.get_service(name)
            if not instance:
                raise ValueError(f"Dependency '{name}' not found")

            path.add(name)
            for dep in instance.config.dependencies:
                visit(dep, path.copy())
            path.remove(name)

            visited.add(name)
            order.append(name)

        visit(service_name, set())
        return order

    async def start_service(self, service_name: str, with_dependencies: bool = True) -> None:
        """
        Start a service (and optionally its dependencies)

        Args:
            service_name: Name of the service to start
            with_dependencies: Whether to start dependencies first
        """
        if with_dependencies:
            # Resolve and start dependencies first
            order = self._resolve_dependencies(service_name)
        else:
            order = [service_name]

        for name in order:
            await self._start_single_service(name)

    async def _start_single_service(self, service_name: str) -> None:
        """Start a single service"""
        instance = self.get_service(service_name)
        if not instance:
            raise ValueError(f"Service '{service_name}' not found")

        # Check current state
        if instance.state == ServiceState.RUNNING:
            logger.info(f"Service '{service_name}' already running")
            return

        if instance.state not in [ServiceState.REGISTERED, ServiceState.STOPPED, ServiceState.FAILED]:
            raise ValueError(f"Cannot start service '{service_name}' from state {instance.state}")

        # Transition to STARTING
        self._transition_state(instance, ServiceState.STARTING)

        try:
            # Execute start handler
            if instance.config.start_handler:
                if asyncio.iscoroutinefunction(instance.config.start_handler):
                    await asyncio.wait_for(
                        instance.config.start_handler(), timeout=instance.config.startup_timeout
                    )
                else:
                    instance.config.start_handler()

            # Transition to RUNNING
            self._transition_state(instance, ServiceState.RUNNING)
            instance.restart_count = 0
            instance.error_message = None

            # Start health monitoring
            self._start_health_monitoring(instance)

            logger.info(f"Service '{service_name}' started successfully")

        except asyncio.TimeoutError:
            error_msg = f"Service '{service_name}' startup timed out"
            logger.error(error_msg)
            instance.error_message = error_msg
            self._transition_state(instance, ServiceState.FAILED)
            raise

        except Exception as e:
            error_msg = f"Service '{service_name}' failed to start: {e}"
            logger.error(error_msg)
            instance.error_message = str(e)
            self._transition_state(instance, ServiceState.FAILED)

            # Attempt recovery if enabled
            if instance.config.restart_on_failure:
                await self._attempt_recovery(instance)
            raise

    async def stop_service(self, service_name: str, graceful: bool = True) -> None:
        """
        Stop a service

        Args:
            service_name: Name of the service to stop
            graceful: Whether to wait for graceful shutdown
        """
        instance = self.get_service(service_name)
        if not instance:
            raise ValueError(f"Service '{service_name}' not found")

        if instance.state == ServiceState.STOPPED:
            logger.info(f"Service '{service_name}' already stopped")
            return

        if instance.state not in [ServiceState.RUNNING, ServiceState.FAILED, ServiceState.DEGRADED]:
            logger.warning(f"Stopping service '{service_name}' from state {instance.state}")

        # Transition to STOPPING
        self._transition_state(instance, ServiceState.STOPPING)

        # Stop health monitoring
        if instance.service_id in self._health_check_tasks:
            self._health_check_tasks[instance.service_id].cancel()
            del self._health_check_tasks[instance.service_id]

        try:
            # Execute stop handler
            if instance.config.stop_handler:
                if asyncio.iscoroutinefunction(instance.config.stop_handler):
                    if graceful:
                        await asyncio.wait_for(
                            instance.config.stop_handler(), timeout=instance.config.shutdown_timeout
                        )
                    else:
                        task = asyncio.create_task(instance.config.stop_handler())
                        await asyncio.wait([task], timeout=instance.config.shutdown_timeout)
                else:
                    instance.config.stop_handler()

            # Transition to STOPPED
            self._transition_state(instance, ServiceState.STOPPED)
            logger.info(f"Service '{service_name}' stopped successfully")

        except asyncio.TimeoutError:
            logger.warning(f"Service '{service_name}' shutdown timed out")
            self._transition_state(instance, ServiceState.STOPPED)

        except Exception as e:
            logger.error(f"Error stopping service '{service_name}': {e}")
            self._transition_state(instance, ServiceState.STOPPED)

    async def restart_service(self, service_name: str) -> None:
        """
        Restart a service

        Args:
            service_name: Name of the service to restart
        """
        logger.info(f"Restarting service '{service_name}'")
        await self.stop_service(service_name)
        await asyncio.sleep(0.5)  # Brief pause
        await self.start_service(service_name, with_dependencies=False)

    def _transition_state(self, instance: ServiceInstance, new_state: ServiceState) -> None:
        """Transition service to a new state"""
        old_state = instance.state
        instance.state = new_state
        instance.last_state_change = time.time()
        logger.debug(f"Service '{instance.config.name}' transitioned from {old_state} to {new_state}")

    def _start_health_monitoring(self, instance: ServiceInstance) -> None:
        """Start health monitoring for a service"""
        if instance.service_id in self._health_check_tasks:
            self._health_check_tasks[instance.service_id].cancel()

        if instance.config.health_check:
            task = asyncio.create_task(self._health_monitor_loop(instance))
            self._health_check_tasks[instance.service_id] = task

    async def _health_monitor_loop(self, instance: ServiceInstance) -> None:
        """Health monitoring loop for a service"""
        while instance.state == ServiceState.RUNNING:
            try:
                await asyncio.sleep(instance.config.health_check_interval)

                if instance.config.health_check:
                    # Execute health check
                    if asyncio.iscoroutinefunction(instance.config.health_check):
                        is_healthy = await instance.config.health_check()
                    else:
                        is_healthy = instance.config.health_check()

                    instance.last_health_check = time.time()

                    # Update health status
                    if is_healthy:
                        instance.health_status = HealthStatus.HEALTHY
                    else:
                        instance.health_status = HealthStatus.UNHEALTHY
                        logger.warning(f"Service '{instance.config.name}' is unhealthy")

                        # Trigger recovery if enabled
                        if instance.config.restart_on_failure:
                            await self._attempt_recovery(instance)
                            break

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error for '{instance.config.name}': {e}")
                instance.health_status = HealthStatus.UNKNOWN

    async def _attempt_recovery(self, instance: ServiceInstance) -> None:
        """
        Attempt to recover a failed service

        Args:
            instance: Service instance to recover
        """
        if instance.restart_count >= instance.config.max_restart_attempts:
            logger.error(
                f"Service '{instance.config.name}' exceeded max restart attempts ({instance.config.max_restart_attempts})"
            )
            self._transition_state(instance, ServiceState.FAILED)
            return

        instance.restart_count += 1
        self._transition_state(instance, ServiceState.RECOVERING)

        logger.info(
            f"Attempting recovery for service '{instance.config.name}' (attempt {instance.restart_count}/{instance.config.max_restart_attempts})"
        )

        await asyncio.sleep(instance.config.restart_delay)

        try:
            await self.restart_service(instance.config.name)
        except Exception as e:
            logger.error(f"Recovery failed for service '{instance.config.name}': {e}")
            self._transition_state(instance, ServiceState.FAILED)

    async def start_all(self) -> None:
        """Start all registered services in dependency order"""
        self._running = True

        # Collect all services
        all_services = list(self._service_name_to_id.keys())

        # Build dependency graph and start in order
        started = set()
        for service_name in all_services:
            if service_name not in started:
                order = self._resolve_dependencies(service_name)
                for name in order:
                    if name not in started:
                        try:
                            await self._start_single_service(name)
                            started.add(name)
                        except Exception as e:
                            logger.error(f"Failed to start service '{name}': {e}")

        logger.info(f"ServiceOrchestrator '{self.name}' started all services")

    async def stop_all(self, graceful: bool = True) -> None:
        """Stop all services in reverse dependency order"""
        self._running = False
        self._shutdown_event.set()

        # Get all running services
        running_services = [
            instance.config.name for instance in self._services.values() if instance.state == ServiceState.RUNNING
        ]

        # Reverse dependency order for shutdown
        shutdown_order = []
        for service_name in running_services:
            if service_name not in shutdown_order:
                order = self._resolve_dependencies(service_name)
                for name in reversed(order):
                    if name not in shutdown_order:
                        shutdown_order.append(name)

        # Stop services
        for service_name in shutdown_order:
            try:
                await self.stop_service(service_name, graceful=graceful)
            except Exception as e:
                logger.error(f"Error stopping service '{service_name}': {e}")

        # Cancel all health check tasks
        for task in self._health_check_tasks.values():
            task.cancel()
        self._health_check_tasks.clear()

        logger.info(f"ServiceOrchestrator '{self.name}' stopped all services")

    def get_status(self) -> Dict[str, Any]:
        """Get orchestrator status"""
        services_status = []
        for instance in self._services.values():
            services_status.append(
                {
                    "name": instance.config.name,
                    "service_id": instance.service_id,
                    "state": instance.state.value,
                    "health_status": instance.health_status.value,
                    "restart_count": instance.restart_count,
                    "error_message": instance.error_message,
                    "last_state_change": instance.last_state_change,
                }
            )

        return {
            "orchestrator_name": self.name,
            "running": self._running,
            "total_services": len(self._services),
            "services": services_status,
        }

    async def wait_for_shutdown(self) -> None:
        """Wait for shutdown signal"""
        await self._shutdown_event.wait()

"""Tests for Service Orchestrator FSA"""

import asyncio
import pytest
from unittest.mock import AsyncMock, Mock

from agno.fsa.service_orchestrator import (
    HealthStatus,
    ServiceConfig,
    ServiceOrchestrator,
    ServiceState,
)


class TestServiceOrchestrator:
    """Test cases for ServiceOrchestrator"""

    @pytest.fixture
    def orchestrator(self):
        """Create a fresh orchestrator instance"""
        return ServiceOrchestrator(name="TestOrchestrator")

    @pytest.fixture
    def simple_service_config(self):
        """Create a simple service configuration"""
        return ServiceConfig(
            name="test_service",
            start_handler=Mock(),
            stop_handler=Mock(),
            health_check=Mock(return_value=True),
        )

    def test_orchestrator_initialization(self, orchestrator):
        """Test orchestrator initialization"""
        assert orchestrator.name == "TestOrchestrator"
        assert orchestrator._running is False
        assert len(orchestrator._services) == 0

    def test_service_registration(self, orchestrator, simple_service_config):
        """Test service registration"""
        service_id = orchestrator.register_service(simple_service_config)

        assert service_id is not None
        assert len(orchestrator._services) == 1
        assert simple_service_config.name in orchestrator._service_name_to_id

        instance = orchestrator.get_service(simple_service_config.name)
        assert instance is not None
        assert instance.state == ServiceState.REGISTERED
        assert instance.config.name == simple_service_config.name

    def test_duplicate_service_registration(self, orchestrator, simple_service_config):
        """Test that duplicate service registration raises error"""
        orchestrator.register_service(simple_service_config)

        with pytest.raises(ValueError, match="already registered"):
            orchestrator.register_service(simple_service_config)

    def test_service_unregistration(self, orchestrator, simple_service_config):
        """Test service unregistration"""
        orchestrator.register_service(simple_service_config)
        orchestrator.unregister_service(simple_service_config.name)

        assert len(orchestrator._services) == 0
        assert simple_service_config.name not in orchestrator._service_name_to_id

    def test_list_services(self, orchestrator):
        """Test listing all services"""
        config1 = ServiceConfig(name="service1")
        config2 = ServiceConfig(name="service2")

        orchestrator.register_service(config1)
        orchestrator.register_service(config2)

        services = orchestrator.list_services()
        assert len(services) == 2
        assert {s.config.name for s in services} == {"service1", "service2"}

    @pytest.mark.asyncio
    async def test_start_simple_service(self, orchestrator):
        """Test starting a simple service"""
        start_handler = Mock()
        config = ServiceConfig(
            name="test_service",
            start_handler=start_handler,
            health_check=Mock(return_value=True),
        )

        orchestrator.register_service(config)
        await orchestrator.start_service("test_service", with_dependencies=False)

        instance = orchestrator.get_service("test_service")
        assert instance.state == ServiceState.RUNNING
        assert start_handler.called

    @pytest.mark.asyncio
    async def test_start_async_service(self, orchestrator):
        """Test starting a service with async handler"""
        start_handler = AsyncMock()
        config = ServiceConfig(
            name="async_service",
            start_handler=start_handler,
            health_check=Mock(return_value=True),
        )

        orchestrator.register_service(config)
        await orchestrator.start_service("async_service", with_dependencies=False)

        instance = orchestrator.get_service("async_service")
        assert instance.state == ServiceState.RUNNING
        assert start_handler.called

    @pytest.mark.asyncio
    async def test_stop_service(self, orchestrator):
        """Test stopping a service"""
        stop_handler = Mock()
        config = ServiceConfig(
            name="test_service",
            start_handler=Mock(),
            stop_handler=stop_handler,
        )

        orchestrator.register_service(config)
        await orchestrator.start_service("test_service", with_dependencies=False)
        await orchestrator.stop_service("test_service")

        instance = orchestrator.get_service("test_service")
        assert instance.state == ServiceState.STOPPED
        assert stop_handler.called

    @pytest.mark.asyncio
    async def test_restart_service(self, orchestrator):
        """Test restarting a service"""
        start_handler = Mock()
        stop_handler = Mock()
        config = ServiceConfig(
            name="test_service",
            start_handler=start_handler,
            stop_handler=stop_handler,
        )

        orchestrator.register_service(config)
        await orchestrator.start_service("test_service", with_dependencies=False)

        # Reset mocks
        start_handler.reset_mock()
        stop_handler.reset_mock()

        await orchestrator.restart_service("test_service")

        instance = orchestrator.get_service("test_service")
        assert instance.state == ServiceState.RUNNING
        assert start_handler.called
        assert stop_handler.called

    @pytest.mark.asyncio
    async def test_dependency_resolution(self, orchestrator):
        """Test dependency resolution and ordering"""
        # Create services with dependencies
        # service_c depends on service_b
        # service_b depends on service_a
        config_a = ServiceConfig(name="service_a", start_handler=Mock())
        config_b = ServiceConfig(name="service_b", dependencies=["service_a"], start_handler=Mock())
        config_c = ServiceConfig(name="service_c", dependencies=["service_b"], start_handler=Mock())

        orchestrator.register_service(config_a)
        orchestrator.register_service(config_b)
        orchestrator.register_service(config_c)

        # Start service_c, which should start dependencies first
        await orchestrator.start_service("service_c", with_dependencies=True)

        # All services should be running
        assert orchestrator.get_service("service_a").state == ServiceState.RUNNING
        assert orchestrator.get_service("service_b").state == ServiceState.RUNNING
        assert orchestrator.get_service("service_c").state == ServiceState.RUNNING

    @pytest.mark.asyncio
    async def test_circular_dependency_detection(self, orchestrator):
        """Test that circular dependencies are detected"""
        config_a = ServiceConfig(name="service_a", dependencies=["service_b"])
        config_b = ServiceConfig(name="service_b", dependencies=["service_a"])

        orchestrator.register_service(config_a)
        orchestrator.register_service(config_b)

        with pytest.raises(ValueError, match="Circular dependency detected"):
            await orchestrator.start_service("service_a", with_dependencies=True)

    @pytest.mark.asyncio
    async def test_health_monitoring(self, orchestrator):
        """Test health monitoring"""
        health_check_count = 0

        def health_check():
            nonlocal health_check_count
            health_check_count += 1
            return health_check_count <= 2

        config = ServiceConfig(
            name="monitored_service",
            start_handler=Mock(),
            health_check=health_check,
            health_check_interval=0.1,
        )

        orchestrator.register_service(config)
        await orchestrator.start_service("monitored_service", with_dependencies=False)

        # Wait for health checks
        await asyncio.sleep(0.3)

        instance = orchestrator.get_service("monitored_service")
        assert instance.last_health_check > 0

    @pytest.mark.asyncio
    async def test_async_health_check(self, orchestrator):
        """Test async health check"""
        async def async_health_check():
            await asyncio.sleep(0.01)
            return True

        config = ServiceConfig(
            name="async_monitored",
            start_handler=Mock(),
            health_check=async_health_check,
            health_check_interval=0.1,
        )

        orchestrator.register_service(config)
        await orchestrator.start_service("async_monitored", with_dependencies=False)

        await asyncio.sleep(0.3)

        instance = orchestrator.get_service("async_monitored")
        assert instance.health_status == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_failure_handling(self, orchestrator):
        """Test service failure handling"""
        def failing_start():
            raise RuntimeError("Service failed to start")

        config = ServiceConfig(
            name="failing_service",
            start_handler=failing_start,
            restart_on_failure=False,
        )

        orchestrator.register_service(config)

        with pytest.raises(RuntimeError):
            await orchestrator.start_service("failing_service", with_dependencies=False)

        instance = orchestrator.get_service("failing_service")
        assert instance.state == ServiceState.FAILED
        assert instance.error_message is not None

    @pytest.mark.asyncio
    async def test_automatic_recovery(self, orchestrator):
        """Test automatic recovery on failure"""
        attempt_count = 0

        def start_handler():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 2:
                raise RuntimeError("Temporary failure")

        config = ServiceConfig(
            name="recoverable_service",
            start_handler=start_handler,
            restart_on_failure=True,
            max_restart_attempts=3,
            restart_delay=0.1,
        )

        orchestrator.register_service(config)

        # First attempt will fail, but recovery should succeed
        try:
            await orchestrator.start_service("recoverable_service", with_dependencies=False)
        except RuntimeError:
            pass

        # Wait for recovery
        await asyncio.sleep(0.5)

        instance = orchestrator.get_service("recoverable_service")
        # After recovery, it should be running
        assert instance.restart_count > 0

    @pytest.mark.asyncio
    async def test_max_restart_attempts_exceeded(self, orchestrator):
        """Test that max restart attempts is respected"""
        def always_fail():
            raise RuntimeError("Permanent failure")

        config = ServiceConfig(
            name="permanently_failing",
            start_handler=always_fail,
            restart_on_failure=True,
            max_restart_attempts=2,
            restart_delay=0.05,
        )

        orchestrator.register_service(config)

        with pytest.raises(RuntimeError):
            await orchestrator.start_service("permanently_failing", with_dependencies=False)

        # Wait for recovery attempts
        await asyncio.sleep(0.5)

        instance = orchestrator.get_service("permanently_failing")
        assert instance.state == ServiceState.FAILED

    @pytest.mark.asyncio
    async def test_startup_timeout(self, orchestrator):
        """Test startup timeout"""
        async def slow_start():
            await asyncio.sleep(10)

        config = ServiceConfig(
            name="slow_service",
            start_handler=slow_start,
            startup_timeout=0.1,
            restart_on_failure=False,
        )

        orchestrator.register_service(config)

        with pytest.raises(asyncio.TimeoutError):
            await orchestrator.start_service("slow_service", with_dependencies=False)

        instance = orchestrator.get_service("slow_service")
        assert instance.state == ServiceState.FAILED

    @pytest.mark.asyncio
    async def test_shutdown_timeout(self, orchestrator):
        """Test shutdown timeout"""
        async def slow_stop():
            await asyncio.sleep(10)

        config = ServiceConfig(
            name="slow_shutdown",
            start_handler=Mock(),
            stop_handler=slow_stop,
            shutdown_timeout=0.1,
        )

        orchestrator.register_service(config)
        await orchestrator.start_service("slow_shutdown", with_dependencies=False)
        await orchestrator.stop_service("slow_shutdown")

        instance = orchestrator.get_service("slow_shutdown")
        assert instance.state == ServiceState.STOPPED

    @pytest.mark.asyncio
    async def test_start_all_services(self, orchestrator):
        """Test starting all services"""
        config1 = ServiceConfig(name="service1", start_handler=Mock())
        config2 = ServiceConfig(name="service2", dependencies=["service1"], start_handler=Mock())
        config3 = ServiceConfig(name="service3", start_handler=Mock())

        orchestrator.register_service(config1)
        orchestrator.register_service(config2)
        orchestrator.register_service(config3)

        await orchestrator.start_all()

        assert orchestrator.get_service("service1").state == ServiceState.RUNNING
        assert orchestrator.get_service("service2").state == ServiceState.RUNNING
        assert orchestrator.get_service("service3").state == ServiceState.RUNNING

    @pytest.mark.asyncio
    async def test_stop_all_services(self, orchestrator):
        """Test stopping all services"""
        config1 = ServiceConfig(name="service1", start_handler=Mock(), stop_handler=Mock())
        config2 = ServiceConfig(name="service2", start_handler=Mock(), stop_handler=Mock())

        orchestrator.register_service(config1)
        orchestrator.register_service(config2)

        await orchestrator.start_all()
        await orchestrator.stop_all()

        assert orchestrator.get_service("service1").state == ServiceState.STOPPED
        assert orchestrator.get_service("service2").state == ServiceState.STOPPED

    @pytest.mark.asyncio
    async def test_get_status(self, orchestrator):
        """Test getting orchestrator status"""
        config = ServiceConfig(name="test_service", start_handler=Mock())
        orchestrator.register_service(config)
        await orchestrator.start_service("test_service", with_dependencies=False)

        status = orchestrator.get_status()

        assert status["orchestrator_name"] == "TestOrchestrator"
        assert status["total_services"] == 1
        assert len(status["services"]) == 1
        assert status["services"][0]["name"] == "test_service"
        assert status["services"][0]["state"] == ServiceState.RUNNING.value

    @pytest.mark.asyncio
    async def test_service_already_running(self, orchestrator):
        """Test starting an already running service"""
        config = ServiceConfig(name="test_service", start_handler=Mock())
        orchestrator.register_service(config)

        await orchestrator.start_service("test_service", with_dependencies=False)

        # Starting again should be idempotent
        await orchestrator.start_service("test_service", with_dependencies=False)

        instance = orchestrator.get_service("test_service")
        assert instance.state == ServiceState.RUNNING

    @pytest.mark.asyncio
    async def test_service_already_stopped(self, orchestrator):
        """Test stopping an already stopped service"""
        config = ServiceConfig(name="test_service", start_handler=Mock(), stop_handler=Mock())
        orchestrator.register_service(config)

        await orchestrator.start_service("test_service", with_dependencies=False)
        await orchestrator.stop_service("test_service")

        # Stopping again should be idempotent
        await orchestrator.stop_service("test_service")

        instance = orchestrator.get_service("test_service")
        assert instance.state == ServiceState.STOPPED

    def test_get_nonexistent_service(self, orchestrator):
        """Test getting a service that doesn't exist"""
        service = orchestrator.get_service("nonexistent")
        assert service is None

    @pytest.mark.asyncio
    async def test_start_nonexistent_service(self, orchestrator):
        """Test starting a service that doesn't exist"""
        with pytest.raises(ValueError, match="not found"):
            await orchestrator.start_service("nonexistent")

    @pytest.mark.asyncio
    async def test_stop_nonexistent_service(self, orchestrator):
        """Test stopping a service that doesn't exist"""
        with pytest.raises(ValueError, match="not found"):
            await orchestrator.stop_service("nonexistent")

    def test_unregister_nonexistent_service(self, orchestrator):
        """Test unregistering a service that doesn't exist"""
        with pytest.raises(ValueError, match="not found"):
            orchestrator.unregister_service("nonexistent")

    @pytest.mark.asyncio
    async def test_unregister_running_service(self, orchestrator):
        """Test that unregistering a running service raises error"""
        config = ServiceConfig(name="test_service", start_handler=Mock())
        orchestrator.register_service(config)
        await orchestrator.start_service("test_service", with_dependencies=False)

        with pytest.raises(ValueError, match="Cannot unregister"):
            orchestrator.unregister_service("test_service")

    @pytest.mark.asyncio
    async def test_missing_dependency(self, orchestrator):
        """Test starting service with missing dependency"""
        config = ServiceConfig(name="service_with_missing_dep", dependencies=["nonexistent"])
        orchestrator.register_service(config)

        with pytest.raises(ValueError, match="not found"):
            await orchestrator.start_service("service_with_missing_dep", with_dependencies=True)

    @pytest.mark.asyncio
    async def test_complex_dependency_graph(self, orchestrator):
        """Test complex dependency graph"""
        # Create a more complex dependency structure:
        #     A
        #    / \
        #   B   C
        #    \ /
        #     D

        config_a = ServiceConfig(name="A", start_handler=Mock())
        config_b = ServiceConfig(name="B", dependencies=["A"], start_handler=Mock())
        config_c = ServiceConfig(name="C", dependencies=["A"], start_handler=Mock())
        config_d = ServiceConfig(name="D", dependencies=["B", "C"], start_handler=Mock())

        orchestrator.register_service(config_a)
        orchestrator.register_service(config_b)
        orchestrator.register_service(config_c)
        orchestrator.register_service(config_d)

        await orchestrator.start_service("D", with_dependencies=True)

        # All services should be running
        assert orchestrator.get_service("A").state == ServiceState.RUNNING
        assert orchestrator.get_service("B").state == ServiceState.RUNNING
        assert orchestrator.get_service("C").state == ServiceState.RUNNING
        assert orchestrator.get_service("D").state == ServiceState.RUNNING

    @pytest.mark.asyncio
    async def test_graceful_vs_ungraceful_shutdown(self, orchestrator):
        """Test graceful vs ungraceful shutdown"""
        stop_handler = AsyncMock()

        config = ServiceConfig(
            name="test_service",
            start_handler=Mock(),
            stop_handler=stop_handler,
            shutdown_timeout=1.0,
        )

        orchestrator.register_service(config)
        await orchestrator.start_service("test_service", with_dependencies=False)

        # Graceful shutdown
        await orchestrator.stop_service("test_service", graceful=True)
        assert stop_handler.called

        # Restart and test ungraceful
        stop_handler.reset_mock()
        await orchestrator.start_service("test_service", with_dependencies=False)
        await orchestrator.stop_service("test_service", graceful=False)
        assert stop_handler.called

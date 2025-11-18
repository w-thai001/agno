"""Unit tests for ServiceLocatorFSA."""

import pytest
import tempfile
from pathlib import Path

from agno.fsas.service_locator_fsa import (
    ServiceLocatorFSA,
    LocatorConfig,
    ServiceScope,
    ServiceStatus,
    PluginStatus,
    ServiceMetadata,
    ServiceRegistration,
    PluginInfo,
    ServiceInfo,
    LocatorOp,
    LocatorResult,
    ValidationResult,
    RegisterResult,
    LocateResult,
    ResolveResult,
    CreateResult,
    CacheResult,
    InvalidateResult,
    DiscoveryResult,
    PluginLoadResult,
    PluginUnloadResult,
    VersionResult,
    UnregisterResult,
    ClearResult,
    AvailabilityResult,
    DependencyList,
    FactoryRegisterResult,
    OverrideResult,
    CloneResult,
)


# ==================== Mock Services ====================

class MockService:
    """Mock service for testing."""
    def __init__(self):
        self.name = "MockService"


class MockServiceA:
    """Mock service A."""
    def __init__(self):
        self.value = "ServiceA"


class MockServiceB:
    """Mock service B."""
    def __init__(self):
        self.value = "ServiceB"


def mock_service_factory():
    """Factory function for mock service."""
    return MockService()


def mock_service_a_factory():
    """Factory function for mock service A."""
    return MockServiceA()


# ==================== Fixtures ====================

@pytest.fixture
def locator():
    """Create service locator instance."""
    config = LocatorConfig()
    return ServiceLocatorFSA(config)


@pytest.fixture
def configured_locator():
    """Create pre-configured service locator."""
    config = LocatorConfig(
        enable_caching=True,
        enable_lazy_loading=True,
        thread_safe=True,
    )
    locator = ServiceLocatorFSA(config)

    # Register some services
    locator.register_service("test_service", MockService, mock_service_factory)

    return locator


# ==================== Test Classes ====================

class TestServiceLocatorBasics:
    """Test basic service locator functionality."""

    def test_initialization(self):
        """Test service locator initialization."""
        config = LocatorConfig()
        locator = ServiceLocatorFSA(config)
        assert locator.config == config
        assert locator.fsa_id is not None

    def test_initialization_with_custom_config(self):
        """Test initialization with custom configuration."""
        config = LocatorConfig(
            enable_caching=False,
            enable_plugins=False,
        )
        locator = ServiceLocatorFSA(config)
        assert locator.config.enable_caching is False
        assert locator.config.enable_plugins is False

    def test_validation_success(self, locator):
        """Test successful configuration validation."""
        config = LocatorConfig(max_cache_size=500)
        result = locator.validate(config)
        assert result.valid is True

    def test_validation_failure(self, locator):
        """Test configuration validation failure."""
        config = LocatorConfig(max_cache_size=-1)
        result = locator.validate(config)
        assert result.valid is False
        assert len(result.errors) > 0


class TestServiceRegistration:
    """Test service registration."""

    def test_register_service(self, locator):
        """Test registering a service."""
        result = locator.register_service(
            "my_service",
            MockService,
            mock_service_factory
        )
        assert result.registered is True
        assert result.service_name == "my_service"

    def test_register_service_with_scope(self, locator):
        """Test registering service with specific scope."""
        result = locator.register_service(
            "singleton_service",
            MockService,
            mock_service_factory,
            ServiceScope.SINGLETON
        )
        assert result.registered is True
        assert locator.services["singleton_service"].scope == ServiceScope.SINGLETON

    def test_register_duplicate_service(self):
        """Test registering duplicate service."""
        config = LocatorConfig(allow_override=False)
        locator = ServiceLocatorFSA(config)

        locator.register_service("dup_service", MockService, mock_service_factory)

        # Try to register again with override disabled
        result = locator.register_service("dup_service", MockService, mock_service_factory)
        assert result.registered is False

    def test_register_service_with_override(self):
        """Test registering service with override allowed."""
        config = LocatorConfig(allow_override=True)
        locator = ServiceLocatorFSA(config)

        locator.register_service("service", MockService, mock_service_factory)
        result = locator.register_service("service", MockService, mock_service_factory)

        # Should succeed with override enabled
        assert result.registered is True


class TestServiceRetrieval:
    """Test service retrieval."""

    def test_get_service(self, configured_locator):
        """Test getting a service."""
        service = configured_locator.get_service("test_service")
        assert service is not None
        assert isinstance(service, MockService)

    def test_get_nonexistent_service(self, locator):
        """Test getting non-existent service."""
        service = locator.get_service("nonexistent")
        assert service is None

    def test_get_singleton_service(self, locator):
        """Test getting singleton service returns same instance."""
        locator.register_service(
            "singleton",
            MockService,
            mock_service_factory,
            ServiceScope.SINGLETON
        )

        service1 = locator.get_service("singleton")
        service2 = locator.get_service("singleton")

        assert service1 is service2

    def test_get_transient_service(self, locator):
        """Test getting transient service returns different instances."""
        locator.register_service(
            "transient",
            MockService,
            mock_service_factory,
            ServiceScope.TRANSIENT
        )

        service1 = locator.get_service("transient")
        service2 = locator.get_service("transient")

        assert service1 is not service2


class TestServiceLocation:
    """Test service location by interface."""

    def test_locate_service_by_type(self, locator):
        """Test locating service by type."""
        locator.register_service("mock", MockService, mock_service_factory)

        result = locator.locate_service(MockService)
        assert result.found is True
        assert isinstance(result.service, MockService)

    def test_locate_nonexistent_service(self, locator):
        """Test locating non-existent service."""
        result = locator.locate_service(MockServiceA)
        assert result.found is False


class TestServiceResolution:
    """Test service resolution."""

    def test_resolve_service_eager(self, configured_locator):
        """Test eager service resolution."""
        result = configured_locator.resolve_service("test_service", lazy=False)
        assert result.resolved is True
        assert isinstance(result.service, MockService)

    def test_resolve_service_lazy(self, configured_locator):
        """Test lazy service resolution."""
        result = configured_locator.resolve_service("test_service", lazy=True)
        assert result.resolved is True
        # Should return factory for lazy loading
        assert result.service is not None

    def test_resolve_from_cache(self, locator):
        """Test resolving service from cache."""
        locator.register_service(
            "cached",
            MockService,
            mock_service_factory,
            ServiceScope.SINGLETON
        )

        # First call creates and caches
        result1 = locator.resolve_service("cached")

        # Second call should be from cache
        result2 = locator.resolve_service("cached")

        assert result2.from_cache is True


class TestServiceCreation:
    """Test service creation."""

    def test_create_service(self, locator):
        """Test creating a service."""
        result = locator.create_service("new_service", mock_service_factory)
        assert result.created is True
        assert isinstance(result.service, MockService)

    def test_create_service_with_invalid_factory(self, locator):
        """Test creating service with invalid factory."""
        result = locator.create_service("invalid", "not_a_callable")
        assert result.created is False


class TestServiceCaching:
    """Test service caching."""

    def test_cache_service(self, locator):
        """Test caching a service."""
        service = MockService()
        result = locator.cache_service("cached_service", service)
        assert result.cached is True

    def test_cache_size_limit(self):
        """Test cache size limit enforcement."""
        config = LocatorConfig(max_cache_size=2)
        locator = ServiceLocatorFSA(config)

        # Cache services up to limit
        locator.cache_service("s1", MockService())
        locator.cache_service("s2", MockService())

        # Try to cache beyond limit
        result = locator.cache_service("s3", MockService())
        assert result.cached is False

    def test_cache_disabled(self):
        """Test caching when disabled."""
        config = LocatorConfig(enable_caching=False)
        locator = ServiceLocatorFSA(config)

        result = locator.cache_service("service", MockService())
        assert result.cached is False


class TestCacheInvalidation:
    """Test cache invalidation."""

    def test_invalidate_cache(self, locator):
        """Test invalidating cached service."""
        service = MockService()
        locator.cache_service("service", service)

        result = locator.invalidate_cache("service")
        assert result.invalidated is True

    def test_invalidate_nonexistent_cache(self, locator):
        """Test invalidating non-existent cache entry."""
        result = locator.invalidate_cache("nonexistent")
        assert result.invalidated is False


class TestServiceDiscovery:
    """Test service discovery."""

    def test_discover_services(self, locator):
        """Test service discovery."""
        # Discovery requires actual package - will return empty
        result = locator.discover_services("nonexistent.package")
        assert isinstance(result, DiscoveryResult)

    def test_discover_services_disabled(self):
        """Test discovery when disabled."""
        config = LocatorConfig(enable_discovery=False)
        locator = ServiceLocatorFSA(config)

        result = locator.discover_services("some.package")
        assert result.discovered is False


class TestPluginLoading:
    """Test plugin loading."""

    def test_load_plugin_nonexistent(self, locator):
        """Test loading non-existent plugin."""
        result = locator.load_plugin("nonexistent.py")
        assert result.loaded is False

    def test_load_plugin_disabled(self):
        """Test plugin loading when disabled."""
        config = LocatorConfig(enable_plugins=False)
        locator = ServiceLocatorFSA(config)

        result = locator.load_plugin("plugin.py")
        assert result.loaded is False


class TestPluginUnloading:
    """Test plugin unloading."""

    def test_unload_nonexistent_plugin(self, locator):
        """Test unloading non-existent plugin."""
        result = locator.unload_plugin("nonexistent")
        assert result.unloaded is False


class TestServiceMetadata:
    """Test service metadata."""

    def test_get_service_metadata(self, configured_locator):
        """Test getting service metadata."""
        metadata = configured_locator.get_service_metadata("test_service")
        assert metadata is not None
        assert metadata.name == "test_service"

    def test_get_nonexistent_metadata(self, locator):
        """Test getting metadata for non-existent service."""
        metadata = locator.get_service_metadata("nonexistent")
        assert metadata is None


class TestVersionManagement:
    """Test service version management."""

    def test_set_service_version(self, configured_locator):
        """Test setting service version."""
        result = configured_locator.set_service_version("test_service", "2.0.0")
        assert result.success is True
        assert result.version == "2.0.0"

    def test_set_version_for_nonexistent_service(self, locator):
        """Test setting version for non-existent service."""
        result = locator.set_service_version("nonexistent", "1.0.0")
        assert result.success is False


class TestServiceListing:
    """Test service listing."""

    def test_get_all_services(self, configured_locator):
        """Test getting all registered services."""
        services = configured_locator.get_all_services()
        assert len(services) > 0
        assert isinstance(services[0], ServiceInfo)

    def test_get_all_services_empty(self, locator):
        """Test getting services from empty registry."""
        services = locator.get_all_services()
        assert len(services) == 0


class TestServiceUnregistration:
    """Test service unregistration."""

    def test_unregister_service(self, configured_locator):
        """Test unregistering a service."""
        result = configured_locator.unregister_service("test_service")
        assert result.unregistered is True

    def test_unregister_nonexistent_service(self, locator):
        """Test unregistering non-existent service."""
        result = locator.unregister_service("nonexistent")
        assert result.unregistered is False


class TestRegistryClearing:
    """Test registry clearing."""

    def test_clear_registry(self, configured_locator):
        """Test clearing all registrations."""
        result = configured_locator.clear_registry()
        assert result.cleared is True
        assert result.cleared_count > 0


class TestServiceAvailability:
    """Test service availability checking."""

    def test_check_service_availability(self, configured_locator):
        """Test checking service availability."""
        result = configured_locator.check_service_availability("test_service")
        assert result.available is True

    def test_check_nonexistent_service(self, locator):
        """Test checking non-existent service."""
        result = locator.check_service_availability("nonexistent")
        assert result.available is False


class TestServiceDependencies:
    """Test service dependency queries."""

    def test_get_service_dependencies(self, configured_locator):
        """Test getting service dependencies."""
        deps = configured_locator.get_service_dependencies("test_service")
        assert isinstance(deps, DependencyList)
        assert deps.service_name == "test_service"

    def test_get_dependencies_for_nonexistent_service(self, locator):
        """Test getting dependencies for non-existent service."""
        deps = locator.get_service_dependencies("nonexistent")
        assert deps.resolved is False


class TestFactoryRegistration:
    """Test factory registration."""

    def test_register_service_factory(self, locator):
        """Test registering a service factory."""
        result = locator.register_service_factory(
            "factory_service",
            mock_service_factory,
            singleton=False
        )
        assert result.registered is True
        assert result.singleton is False

    def test_register_singleton_factory(self, locator):
        """Test registering singleton factory."""
        result = locator.register_service_factory(
            "singleton_factory",
            mock_service_factory,
            singleton=True
        )
        assert result.registered is True
        assert result.singleton is True


class TestServiceOverride:
    """Test service override."""

    def test_override_service(self, locator):
        """Test overriding a service."""
        locator.register_service("service", MockService, mock_service_factory)

        result = locator.override_service("service", mock_service_a_factory)
        assert result.overridden is True

    def test_override_nonexistent_service(self, locator):
        """Test overriding non-existent service."""
        result = locator.override_service("nonexistent", mock_service_factory)
        assert result.overridden is False

    def test_override_disabled(self):
        """Test override when disabled."""
        config = LocatorConfig(allow_override=False)
        locator = ServiceLocatorFSA(config)

        locator.register_service("service", MockService, mock_service_factory)
        result = locator.override_service("service", mock_service_a_factory)

        assert result.overridden is False


class TestServiceCloning:
    """Test service cloning."""

    def test_clone_service(self, configured_locator):
        """Test cloning a service registration."""
        result = configured_locator.clone_service("test_service", "cloned_service")
        assert result.cloned is True
        assert result.source == "test_service"
        assert result.target == "cloned_service"

    def test_clone_nonexistent_service(self, locator):
        """Test cloning non-existent service."""
        result = locator.clone_service("nonexistent", "target")
        assert result.cloned is False


class TestExecuteMethod:
    """Test execute method."""

    def test_execute_operations(self, locator):
        """Test executing service locator operations."""
        ops = [
            LocatorOp(
                operation="register",
                service_name="new_service",
                service_type=MockService,
                factory=mock_service_factory,
            ),
        ]

        result = locator.execute(ops)
        assert isinstance(result, LocatorResult)

    def test_execute_get_operation(self, configured_locator):
        """Test executing get operation."""
        ops = [
            LocatorOp(
                operation="get",
                service_name="test_service",
            ),
        ]

        result = configured_locator.execute(ops)
        assert result.success is True


class TestEdgeCases:
    """Test edge cases and error scenarios."""

    def test_register_with_invalid_factory(self, locator):
        """Test registering with invalid factory."""
        result = locator.register_service(
            "invalid",
            MockService,
            "not_a_callable"
        )
        # Validation is permissive by default unless enabled
        assert isinstance(result, RegisterResult)

    def test_multiple_services_same_type(self, locator):
        """Test registering multiple services of same type."""
        locator.register_service("service1", MockService, mock_service_factory)
        locator.register_service("service2", MockService, mock_service_factory)

        # Both should be registered
        assert "service1" in locator.services
        assert "service2" in locator.services


class TestThreadSafety:
    """Test thread safety."""

    def test_thread_safe_locator(self):
        """Test thread-safe locator creation."""
        config = LocatorConfig(thread_safe=True)
        locator = ServiceLocatorFSA(config)

        assert locator._lock is not None

    def test_non_thread_safe_locator(self):
        """Test non-thread-safe locator."""
        config = LocatorConfig(thread_safe=False)
        locator = ServiceLocatorFSA(config)

        assert locator._lock is None

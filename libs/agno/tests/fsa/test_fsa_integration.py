"""
Comprehensive Integration Tests for FSA Framework

Tests end-to-end workflows, load testing, error scenarios,
performance benchmarking, and memory leak detection.
"""

import asyncio
import gc
import logging
import pytest
import time
import tracemalloc
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List

from agno.fsa.registry import (
    FSARegistry,
    FSAModule,
    FSAHealth,
    FSAHealthStatus,
    get_registry,
    reset_registry,
)
from agno.fsa.pipeline_manager import (
    FSAPipeline,
    FSAPipelineManager,
    PipelineExecutionResult,
    PipelineStageStatus,
)
from agno.fsa.cli import FSACLIHandler, create_parser
from agno.config.fsa_production_config import (
    FSAProductionConfig,
    Environment,
    get_fsa_config,
    reset_config,
)


# Mock FSA Components for Testing
class MockMultiStepBuilder:
    """Mock multi-step builder FSA"""

    def __init__(self, **kwargs):
        self.dependencies = kwargs.get('dependencies', {})
        self.call_count = 0

    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute mock builder"""
        self.call_count += 1
        time.sleep(0.01)  # Simulate work
        return {
            "steps": ["step1", "step2", "step3"],
            "count": self.call_count,
            "input": kwargs,
        }

    def health_check(self) -> bool:
        """Health check"""
        return True


class MockRSIOptimizer:
    """Mock RSI optimizer FSA"""

    def __init__(self, **kwargs):
        self.dependencies = kwargs.get('dependencies', {})
        self.call_count = 0

    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute mock optimizer"""
        self.call_count += 1
        time.sleep(0.015)  # Simulate work
        return {
            "optimized": True,
            "score": 0.95,
            "count": self.call_count,
        }

    def health_check(self) -> Dict[str, Any]:
        """Health check with metadata"""
        return {
            "status": "healthy",
            "message": "Optimizer operational",
        }


class MockMetaOrchestrator:
    """Mock meta-orchestrator FSA"""

    def __init__(self, **kwargs):
        self.dependencies = kwargs.get('dependencies', {})
        self.call_count = 0
        self.should_fail = kwargs.get('should_fail', False)

    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute mock orchestrator"""
        self.call_count += 1

        if self.should_fail and self.call_count == 1:
            raise ValueError("Simulated orchestrator failure")

        time.sleep(0.02)  # Simulate work
        return {
            "orchestrated": True,
            "modules": ["builder", "optimizer"],
            "count": self.call_count,
        }

    def health_check(self) -> bool:
        """Health check"""
        return not self.should_fail


# Fixtures
@pytest.fixture(autouse=True)
def reset_global_state():
    """Reset global state before each test"""
    reset_registry()
    reset_config()
    yield
    reset_registry()
    reset_config()


@pytest.fixture
def registry():
    """Create a fresh registry for testing"""
    return FSARegistry()


@pytest.fixture
def pipeline_manager(registry):
    """Create a pipeline manager with registry"""
    return FSAPipelineManager(registry=registry, max_workers=4)


@pytest.fixture
def sample_registry(registry):
    """Create registry with sample modules"""
    registry.register(
        name="multi_step_builder",
        version="1.0.0",
        module_class=MockMultiStepBuilder,
        lazy_load=False,
    )
    registry.register(
        name="rsi_optimizer",
        version="1.0.0",
        module_class=MockRSIOptimizer,
        dependencies=["multi_step_builder"],
        lazy_load=False,
    )
    registry.register(
        name="meta_orchestrator",
        version="1.0.0",
        module_class=MockMetaOrchestrator,
        dependencies=["multi_step_builder", "rsi_optimizer"],
        lazy_load=False,
    )
    return registry


# Registry Tests
class TestFSARegistry:
    """Test FSA Registry functionality"""

    def test_module_registration(self, registry):
        """Test basic module registration"""
        registry.register(
            name="test_module",
            version="1.0.0",
            module_class=MockMultiStepBuilder,
        )

        assert "test_module" in registry._modules
        modules = registry.list_modules()
        assert len(modules) == 1
        assert modules[0]["name"] == "test_module"

    def test_duplicate_registration_fails(self, registry):
        """Test that duplicate registration fails without override"""
        registry.register(
            name="test_module",
            version="1.0.0",
            module_class=MockMultiStepBuilder,
        )

        with pytest.raises(ValueError, match="already registered"):
            registry.register(
                name="test_module",
                version="2.0.0",
                module_class=MockMultiStepBuilder,
            )

    def test_override_registration(self, registry):
        """Test registration override"""
        registry.register(
            name="test_module",
            version="1.0.0",
            module_class=MockMultiStepBuilder,
        )

        registry.register(
            name="test_module",
            version="2.0.0",
            module_class=MockRSIOptimizer,
            override=True,
        )

        modules = registry.list_modules()
        assert modules[0]["version"] == "2.0.0"

    def test_dependency_resolution(self, sample_registry):
        """Test dependency injection and resolution"""
        orchestrator = sample_registry.get("meta_orchestrator")

        assert orchestrator is not None
        assert "multi_step_builder" in orchestrator.dependencies
        assert "rsi_optimizer" in orchestrator.dependencies

    def test_circular_dependency_detection(self, registry):
        """Test detection of circular dependencies"""
        registry.register(
            name="module_a",
            version="1.0.0",
            module_class=MockMultiStepBuilder,
            dependencies=["module_b"],
        )

        registry.register(
            name="module_b",
            version="1.0.0",
            module_class=MockRSIOptimizer,
            dependencies=["module_a"],
        )

        # Should raise error when computing initialization order
        with pytest.raises(ValueError, match="Circular dependency"):
            registry._topological_sort()

    def test_health_check(self, sample_registry):
        """Test health checking functionality"""
        health = sample_registry.health_check("multi_step_builder", force=True)

        assert health.status == FSAHealthStatus.HEALTHY
        assert health.is_healthy()

    def test_health_check_all(self, sample_registry):
        """Test health check on all modules"""
        health_results = sample_registry.health_check_all()

        assert len(health_results) == 3
        assert all(h.is_healthy() for h in health_results.values())

    def test_module_unregistration(self, registry):
        """Test module unregistration"""
        registry.register(
            name="test_module",
            version="1.0.0",
            module_class=MockMultiStepBuilder,
        )

        registry.unregister("test_module")

        assert "test_module" not in registry._modules

    def test_unregister_with_dependents_fails(self, sample_registry):
        """Test that unregistering a module with dependents fails"""
        with pytest.raises(ValueError, match="depended on by"):
            sample_registry.unregister("multi_step_builder")

    def test_lazy_loading(self, registry):
        """Test lazy loading of modules"""
        registry.register(
            name="lazy_module",
            version="1.0.0",
            module_class=MockMultiStepBuilder,
            lazy_load=True,
        )

        modules = registry.list_modules()
        assert not modules[0]["instantiated"]

        # Get the module (should instantiate)
        instance = registry.get("lazy_module")
        assert instance is not None

        modules = registry.list_modules()
        assert modules[0]["instantiated"]


# Pipeline Manager Tests
class TestFSAPipelineManager:
    """Test FSA Pipeline Manager functionality"""

    def test_simple_pipeline_execution(self, sample_registry, pipeline_manager):
        """Test execution of a simple pipeline"""
        pipeline = FSAPipeline(name="test_pipeline", registry=sample_registry)

        pipeline.add_stage(
            name="build",
            fsa_module_name="multi_step_builder",
            inputs={"data": "test"},
        )

        result = pipeline_manager.execute_pipeline(pipeline)

        assert result.is_successful()
        assert result.status == "success"
        assert len(result.stage_results) == 1
        assert result.stage_results[0].status == PipelineStageStatus.COMPLETED

    def test_multi_stage_pipeline(self, sample_registry, pipeline_manager):
        """Test multi-stage pipeline with dependencies"""
        pipeline = FSAPipeline(name="multi_stage", registry=sample_registry)

        pipeline.add_stage(
            name="build",
            fsa_module_name="multi_step_builder",
        )
        pipeline.add_stage(
            name="optimize",
            fsa_module_name="rsi_optimizer",
            depends_on=["build"],
        )
        pipeline.add_stage(
            name="orchestrate",
            fsa_module_name="meta_orchestrator",
            depends_on=["build", "optimize"],
        )

        result = pipeline_manager.execute_pipeline(pipeline)

        assert result.is_successful()
        assert len(result.stage_results) == 3

        # Check execution order
        build_result = result.get_stage_result("build")
        optimize_result = result.get_stage_result("optimize")
        orchestrate_result = result.get_stage_result("orchestrate")

        assert all(r.is_successful() for r in [build_result, optimize_result, orchestrate_result])

    def test_parallel_execution(self, sample_registry, pipeline_manager):
        """Test parallel execution of independent stages"""
        pipeline = FSAPipeline(name="parallel_test", registry=sample_registry)

        # Two independent stages
        pipeline.add_stage(name="build1", fsa_module_name="multi_step_builder")
        pipeline.add_stage(name="build2", fsa_module_name="multi_step_builder")

        # Dependent stage
        pipeline.add_stage(
            name="optimize",
            fsa_module_name="rsi_optimizer",
            depends_on=["build1", "build2"],
        )

        start_time = time.time()
        result = pipeline_manager.execute_pipeline(pipeline)
        duration = time.time() - start_time

        assert result.is_successful()

        # Parallel execution should be faster than sequential
        # (2 * 10ms parallel + 15ms sequential) < (2 * 10ms + 15ms sequential)
        # This is a rough check
        assert duration < 0.1  # Should complete in less than 100ms

    def test_error_recovery_with_retry(self, registry, pipeline_manager):
        """Test error recovery and retry logic"""
        registry.register(
            name="failing_module",
            version="1.0.0",
            module_class=MockMetaOrchestrator,
            lazy_load=False,
        )

        # Get instance and configure to fail once then succeed
        instance = registry.get("failing_module", should_fail=False)
        instance.should_fail = True

        pipeline = FSAPipeline(name="retry_test", registry=registry)
        pipeline.add_stage(
            name="failing_stage",
            fsa_module_name="failing_module",
            retry_config={"max_retries": 3},
        )

        # First execution will fail, retry will succeed
        instance.should_fail = True
        result = pipeline_manager.execute_pipeline(pipeline, use_cache=False)

        # Should fail after all retries
        assert not result.is_successful()

    def test_pipeline_caching(self, sample_registry, pipeline_manager):
        """Test pipeline result caching"""
        pipeline = FSAPipeline(name="cache_test", registry=sample_registry)
        pipeline.add_stage(name="build", fsa_module_name="multi_step_builder")

        # First execution
        result1 = pipeline_manager.execute_pipeline(pipeline)
        assert result1.is_successful()

        # Second execution (should use cache)
        result2 = pipeline_manager.execute_pipeline(pipeline, use_cache=True)
        assert result2.is_successful()

        # Results should be identical (same instance from cache)
        assert result1.pipeline_id == result2.pipeline_id

    def test_performance_metrics(self, sample_registry, pipeline_manager):
        """Test performance metrics collection"""
        pipeline = FSAPipeline(name="metrics_test", registry=sample_registry)
        pipeline.add_stage(name="build", fsa_module_name="multi_step_builder")

        # Execute multiple times
        for _ in range(5):
            pipeline_manager.execute_pipeline(pipeline, use_cache=False)

        metrics = pipeline_manager.get_metrics("metrics_test")

        assert metrics["execution_count"] == 5
        assert "avg_duration_ms" in metrics
        assert "min_duration_ms" in metrics
        assert "max_duration_ms" in metrics
        assert "p95_duration_ms" in metrics

    def test_stage_timeout(self, registry, pipeline_manager):
        """Test stage timeout handling"""
        # Note: Current implementation doesn't have timeout enforcement
        # This test is a placeholder for when that's implemented
        pass

    def test_custom_function_stage(self, registry, pipeline_manager):
        """Test pipeline stage with custom function"""

        def custom_function(data: str) -> Dict[str, Any]:
            return {"processed": data.upper(), "length": len(data)}

        pipeline = FSAPipeline(name="custom_func", registry=registry)
        pipeline.add_stage(
            name="process",
            function=custom_function,
            inputs={"data": "hello world"},
        )

        result = pipeline_manager.execute_pipeline(pipeline)

        assert result.is_successful()
        assert result.stage_results[0].output["processed"] == "HELLO WORLD"


# Load Testing
class TestFSALoadTesting:
    """Load testing with multiple concurrent FSA executions"""

    def test_concurrent_pipeline_executions(self, sample_registry):
        """Test multiple concurrent pipeline executions"""
        pipeline_manager = FSAPipelineManager(
            registry=sample_registry,
            max_workers=8,
        )

        pipeline = FSAPipeline(name="load_test", registry=sample_registry)
        pipeline.add_stage(name="build", fsa_module_name="multi_step_builder")
        pipeline.add_stage(
            name="optimize",
            fsa_module_name="rsi_optimizer",
            depends_on=["build"],
        )

        # Execute 20 pipelines concurrently
        num_executions = 20
        results = []

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(
                    pipeline_manager.execute_pipeline,
                    pipeline,
                    {"run": i},
                    False,  # use_cache
                )
                for i in range(num_executions)
            ]

            for future in as_completed(futures):
                result = future.result()
                results.append(result)

        # All should succeed
        assert len(results) == num_executions
        assert all(r.is_successful() for r in results)

        # Check metrics
        metrics = pipeline_manager.get_metrics("load_test")
        assert metrics["execution_count"] == num_executions

    def test_registry_thread_safety(self, registry):
        """Test registry thread safety with concurrent access"""

        def register_and_get(i):
            module_name = f"module_{i}"
            registry.register(
                name=module_name,
                version="1.0.0",
                module_class=MockMultiStepBuilder,
            )
            return registry.get(module_name)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(register_and_get, i) for i in range(50)]
            results = [f.result() for f in as_completed(futures)]

        assert len(results) == 50
        assert len(registry.list_modules()) == 50


# Memory Leak Detection
class TestMemoryLeaks:
    """Test for memory leaks in FSA framework"""

    def test_pipeline_memory_leak(self, sample_registry, pipeline_manager):
        """Test for memory leaks in pipeline execution"""
        tracemalloc.start()

        pipeline = FSAPipeline(name="memory_test", registry=sample_registry)
        pipeline.add_stage(name="build", fsa_module_name="multi_step_builder")
        pipeline.add_stage(
            name="optimize",
            fsa_module_name="rsi_optimizer",
            depends_on=["build"],
        )

        # Get initial memory
        gc.collect()
        snapshot1 = tracemalloc.take_snapshot()

        # Execute many times
        for i in range(100):
            pipeline_manager.execute_pipeline(pipeline, use_cache=False)

        # Force garbage collection
        gc.collect()
        snapshot2 = tracemalloc.take_snapshot()

        # Check memory growth
        top_stats = snapshot2.compare_to(snapshot1, 'lineno')

        # Get total memory difference
        total_diff = sum(stat.size_diff for stat in top_stats)

        tracemalloc.stop()

        # Memory growth should be reasonable (less than 10MB for 100 executions)
        assert total_diff < 10 * 1024 * 1024  # 10 MB

    def test_registry_instance_cleanup(self, registry):
        """Test that cleared instances are properly garbage collected"""
        registry.register(
            name="test_module",
            version="1.0.0",
            module_class=MockMultiStepBuilder,
        )

        # Create instance
        instance = registry.get("test_module")
        instance_id = id(instance)

        # Clear instance
        registry.clear_instances("test_module")

        # Force garbage collection
        del instance
        gc.collect()

        # Get new instance (should be different)
        new_instance = registry.get("test_module")
        assert id(new_instance) != instance_id


# Configuration Tests
class TestFSAConfiguration:
    """Test FSA production configuration"""

    def test_development_config(self):
        """Test development configuration"""
        config = FSAProductionConfig.from_environment("development")

        assert config.environment == Environment.DEVELOPMENT
        assert not config.rate_limiting.enabled
        assert config.logging.level == "DEBUG"
        assert not config.security.api_key_required

    def test_production_config(self):
        """Test production configuration"""
        config = FSAProductionConfig.from_environment("production")

        assert config.environment == Environment.PRODUCTION
        assert config.rate_limiting.enabled
        assert config.logging.level == "WARNING"
        assert config.security.api_key_required
        assert config.monitoring.enabled

    def test_config_to_dict(self):
        """Test configuration serialization"""
        config = FSAProductionConfig.from_environment("test")
        config_dict = config.to_dict()

        assert "environment" in config_dict
        assert config_dict["environment"] == "test"
        assert "rate_limiting" in config_dict
        assert "logging" in config_dict

    def test_rate_limit_per_module(self):
        """Test per-module rate limiting"""
        config = FSAProductionConfig.from_environment("production")

        assert config.rate_limiting.get_module_limit("multi_step_builder") == 50
        assert config.rate_limiting.get_module_limit("unknown_module") == 100  # Default


# CLI Tests
class TestFSACLI:
    """Test FSA CLI functionality"""

    def test_cli_parser_creation(self):
        """Test CLI argument parser creation"""
        parser = create_parser()
        assert parser is not None

        # Test parsing
        args = parser.parse_args(["init"])
        assert args.command == "init"

    def test_cli_init_command(self, tmp_path):
        """Test CLI init command"""
        import os

        config_path = str(tmp_path / ".fsarc.json")
        handler = FSACLIHandler(config_path=config_path)

        parser = create_parser()
        args = parser.parse_args(["init"])

        result = handler.init(args)

        assert result == 0
        assert os.path.exists(config_path)

    def test_cli_list_modules(self, sample_registry):
        """Test CLI list modules command"""
        handler = FSACLIHandler()
        handler.registry = sample_registry

        parser = create_parser()
        args = parser.parse_args(["list"])

        result = handler.list_modules(args)
        assert result == 0

    def test_cli_health_check(self, sample_registry):
        """Test CLI health check command"""
        handler = FSACLIHandler()
        handler.registry = sample_registry

        parser = create_parser()
        args = parser.parse_args(["health", "--module", "multi_step_builder"])

        result = handler.health_check(args)
        assert result == 0


# Benchmark Tests
class TestPerformanceBenchmarks:
    """Performance benchmarking tests"""

    def test_registry_lookup_performance(self, sample_registry):
        """Test registry lookup performance"""
        iterations = 10000

        start_time = time.time()
        for _ in range(iterations):
            sample_registry.get("multi_step_builder")
        duration = time.time() - start_time

        avg_time_ms = (duration / iterations) * 1000

        # Should be very fast (< 1ms per lookup)
        assert avg_time_ms < 1.0

    def test_pipeline_overhead(self, sample_registry, pipeline_manager):
        """Test pipeline execution overhead"""
        pipeline = FSAPipeline(name="overhead_test", registry=sample_registry)
        pipeline.add_stage(name="build", fsa_module_name="multi_step_builder")

        # Measure pipeline execution time
        iterations = 100
        start_time = time.time()
        for _ in range(iterations):
            pipeline_manager.execute_pipeline(pipeline, use_cache=False)
        total_duration = time.time() - start_time

        avg_duration_ms = (total_duration / iterations) * 1000

        # Pipeline overhead should be < 10ms per execution
        # (excluding the actual FSA execution time of ~10ms)
        assert avg_duration_ms < 30.0  # 10ms FSA + 10ms overhead + margin

    def test_health_check_performance(self, sample_registry):
        """Test health check performance"""
        iterations = 1000

        start_time = time.time()
        for _ in range(iterations):
            sample_registry.health_check("multi_step_builder", force=True)
        duration = time.time() - start_time

        avg_time_ms = (duration / iterations) * 1000

        # Health checks should be fast (< 5ms each)
        assert avg_time_ms < 5.0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

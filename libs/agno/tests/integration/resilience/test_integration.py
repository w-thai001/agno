"""
Integration tests for Circuit Breaker with real-world scenarios

Tests integration with:
- Agent model provider calls
- Tool execution
- Multi-threaded environments
- Cascading failures
"""

import pytest
import asyncio
import time
import random
from unittest.mock import Mock, patch

from agno.resilience import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    CircuitBreakerOpenError,
    resilient,
    RetryConfig,
    BulkheadConfig,
)
from agno.resilience.configuration import (
    external_api_config,
    database_config,
    microservice_config,
)


class MockAPIService:
    """Mock external API service with configurable failure behavior"""

    def __init__(self, failure_rate: float = 0.0, latency_ms: float = 10.0):
        self.failure_rate = failure_rate
        self.latency_ms = latency_ms
        self.call_count = 0

    def call(self, data: str = "test"):
        """Simulate API call"""
        self.call_count += 1
        time.sleep(self.latency_ms / 1000.0)

        if random.random() < self.failure_rate:
            raise Exception(f"API call failed (simulated)")

        return {"status": "success", "data": data}

    async def call_async(self, data: str = "test"):
        """Simulate async API call"""
        self.call_count += 1
        await asyncio.sleep(self.latency_ms / 1000.0)

        if random.random() < self.failure_rate:
            raise Exception(f"API call failed (simulated)")

        return {"status": "success", "data": data}


class TestRealWorldScenarios:
    """Integration tests for real-world scenarios"""

    def test_external_api_with_circuit_breaker(self):
        """Test circuit breaker protecting external API calls"""
        # Create unstable API (50% failure rate)
        api = MockAPIService(failure_rate=0.5, latency_ms=10)

        cb = CircuitBreaker(
            name="external_api",
            config=external_api_config(max_concurrent=10)
        )

        successes = 0
        failures = 0
        circuit_open_rejections = 0

        # Make 100 API calls
        for i in range(100):
            try:
                result = cb.call(lambda: api.call(f"request_{i}"))
                successes += 1
            except CircuitBreakerOpenError:
                circuit_open_rejections += 1
            except Exception:
                failures += 1

        # Circuit should have opened to protect the system
        assert circuit_open_rejections > 0
        print(f"Successes: {successes}, Failures: {failures}, Circuit rejections: {circuit_open_rejections}")

    @pytest.mark.asyncio
    async def test_async_external_api_with_circuit_breaker(self):
        """Test async circuit breaker with external API"""
        api = MockAPIService(failure_rate=0.3, latency_ms=5)

        cb = CircuitBreaker(
            name="async_api",
            config=external_api_config(max_concurrent=20)
        )

        async def make_request(i):
            try:
                result = await cb.call_async(lambda: api.call_async(f"async_request_{i}"))
                return "success"
            except CircuitBreakerOpenError:
                return "rejected"
            except Exception:
                return "failed"

        # Make 50 concurrent requests
        results = await asyncio.gather(*[make_request(i) for i in range(50)])

        successes = results.count("success")
        rejections = results.count("rejected")
        failures = results.count("failed")

        assert successes > 0
        print(f"Async results - Successes: {successes}, Rejections: {rejections}, Failures: {failures}")

    def test_database_connection_pool_protection(self):
        """Test circuit breaker protecting database connection pool"""
        # Simulate database with limited connections
        db = MockAPIService(failure_rate=0.1, latency_ms=20)

        cb = CircuitBreaker(
            name="database",
            config=database_config(max_concurrent=5)
        )

        successful_queries = 0
        failed_queries = 0

        def run_query():
            nonlocal successful_queries, failed_queries
            try:
                result = cb.call(lambda: db.call("SELECT * FROM users"))
                successful_queries += 1
            except Exception:
                failed_queries += 1

        # Simulate concurrent database queries
        import threading
        threads = [threading.Thread(target=run_query) for _ in range(20)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert successful_queries > 0
        print(f"DB queries - Successes: {successful_queries}, Failures: {failed_queries}")

    def test_microservice_mesh_communication(self):
        """Test circuit breakers in microservice architecture"""
        # Simulate 3 microservices
        user_service = MockAPIService(failure_rate=0.1, latency_ms=10)
        product_service = MockAPIService(failure_rate=0.3, latency_ms=15)
        order_service = MockAPIService(failure_rate=0.05, latency_ms=20)

        # Create circuit breakers for each service
        user_cb = CircuitBreaker(name="user_service", config=microservice_config("user", max_concurrent=50))
        product_cb = CircuitBreaker(name="product_service", config=microservice_config("product", max_concurrent=50))
        order_cb = CircuitBreaker(name="order_service", config=microservice_config("order", max_concurrent=50))

        # Simulate orchestration - order creation needs all services
        def create_order(user_id: int, product_id: int):
            try:
                # Call user service
                user = user_cb.call(lambda: user_service.call(f"user_{user_id}"))

                # Call product service
                product = product_cb.call(lambda: product_service.call(f"product_{product_id}"))

                # Call order service
                order = order_cb.call(lambda: order_service.call(f"order_{user_id}_{product_id}"))

                return "order_created"
            except CircuitBreakerOpenError as e:
                return f"service_unavailable: {e.circuit_name}"
            except Exception:
                return "order_failed"

        # Simulate 50 order creations
        results = [create_order(i, i % 10) for i in range(50)]

        successful_orders = results.count("order_created")
        service_unavailable = sum(1 for r in results if r.startswith("service_unavailable"))

        print(f"Orders - Successful: {successful_orders}, Service unavailable: {service_unavailable}")
        assert successful_orders + service_unavailable > 0


class TestCascadingFailuresPrevention:
    """Test prevention of cascading failures"""

    def test_prevent_cascading_failures_across_services(self):
        """Circuit breakers should prevent cascading failures"""
        # Service A depends on Service B
        service_b = MockAPIService(failure_rate=1.0, latency_ms=5)  # Completely failing
        service_a = MockAPIService(failure_rate=0.0, latency_ms=5)  # Healthy

        cb_b = CircuitBreaker(
            name="service_b",
            config=CircuitBreakerConfig(failure_threshold=3, recovery_timeout=0.5)
        )

        def service_a_calls_b():
            try:
                # Service A tries to call Service B
                result_b = cb_b.call(lambda: service_b.call())
                return service_a.call()  # Only call A if B succeeds
            except CircuitBreakerOpenError:
                # Circuit open - use fallback
                return {"status": "degraded", "reason": "service_b_unavailable"}
            except Exception:
                raise

        # Make calls - circuit should open quickly for B
        results = []
        for i in range(20):
            try:
                result = service_a_calls_b()
                results.append(result.get("status", "success"))
            except Exception:
                results.append("failed")

        degraded_responses = results.count("degraded")

        # Should have degraded responses (circuit open) instead of failures
        assert degraded_responses > 10
        print(f"Degraded responses: {degraded_responses} (circuit prevented cascading failures)")


class TestResilientDecorator:
    """Test the composite resilient decorator"""

    def test_resilient_decorator_with_retry_and_circuit_breaker(self):
        """Test resilient decorator combining patterns"""
        api = MockAPIService(failure_rate=0.3)

        @resilient(
            circuit_breaker_config=CircuitBreakerConfig(failure_threshold=5),
            retry_config=RetryConfig(max_attempts=3, delay_seconds=0.01),
            name="resilient_api"
        )
        def call_api(data):
            return api.call(data)

        successes = 0
        failures = 0

        for i in range(30):
            try:
                result = call_api(f"request_{i}")
                successes += 1
            except Exception:
                failures += 1

        # With retry, should have more successes
        assert successes > failures
        print(f"Resilient decorator - Successes: {successes}, Failures: {failures}")

    @pytest.mark.asyncio
    async def test_resilient_decorator_async(self):
        """Test resilient decorator with async functions"""
        api = MockAPIService(failure_rate=0.2)

        @resilient(
            circuit_breaker_config=CircuitBreakerConfig(failure_threshold=5),
            bulkhead_config=BulkheadConfig(max_concurrent=10),
            name="async_resilient_api"
        )
        async def call_api_async(data):
            return await api.call_async(data)

        async def make_call(i):
            try:
                result = await call_api_async(f"async_request_{i}")
                return "success"
            except Exception:
                return "failed"

        results = await asyncio.gather(*[make_call(i) for i in range(20)])

        successes = results.count("success")
        assert successes > 0
        print(f"Async resilient decorator - Successes: {successes}")


class TestMetricsCollection:
    """Test metrics collection in integration scenarios"""

    def test_metrics_across_multiple_circuits(self):
        """Test metrics collection across multiple circuit breakers"""
        from agno.resilience.metrics import get_global_collector

        # Create multiple services
        api1 = MockAPIService(failure_rate=0.2)
        api2 = MockAPIService(failure_rate=0.5)

        cb1 = CircuitBreaker(name="api1", config=CircuitBreakerConfig(enable_metrics=True))
        cb2 = CircuitBreaker(name="api2", config=CircuitBreakerConfig(enable_metrics=True))

        # Make calls
        for i in range(20):
            try:
                cb1.call(lambda: api1.call())
            except:
                pass

            try:
                cb2.call(lambda: api2.call())
            except:
                pass

        # Get global metrics
        collector = get_global_collector()
        summary = collector.get_summary()

        assert summary['total_circuits'] >= 2
        assert summary['aggregate_metrics']['total_requests'] >= 40

        print(f"Metrics summary: {summary}")


class TestLoadScenarios:
    """Test under load conditions"""

    @pytest.mark.asyncio
    async def test_high_concurrency_async(self):
        """Test circuit breaker under high concurrency"""
        api = MockAPIService(failure_rate=0.1, latency_ms=10)

        cb = CircuitBreaker(
            name="high_load_api",
            config=CircuitBreakerConfig(
                max_concurrent_calls=50,
                failure_threshold=20,
                enable_metrics=True
            )
        )

        async def make_request(i):
            try:
                result = await cb.call_async(lambda: api.call_async(f"request_{i}"))
                return "success"
            except Exception:
                return "failed"

        # Make 200 concurrent requests
        results = await asyncio.gather(*[make_request(i) for i in range(200)])

        successes = results.count("success")
        failures = results.count("failed")

        # Should handle high load gracefully
        assert successes + failures == 200

        metrics = cb.get_metrics()
        print(f"High load metrics - Total: {metrics.total_requests}, Success rate: {metrics.current_success_rate:.2%}")

    def test_stress_test_with_recovery(self):
        """Test circuit breaker under stress with recovery cycles"""
        api = MockAPIService(failure_rate=0.6, latency_ms=5)

        cb = CircuitBreaker(
            name="stress_test",
            config=CircuitBreakerConfig(
                failure_threshold=10,
                recovery_timeout=0.2,
                enable_metrics=True
            )
        )

        for cycle in range(5):
            # Make requests until circuit opens
            while cb.get_state() != CircuitState.OPEN:
                try:
                    cb.call(lambda: api.call())
                except:
                    pass

            print(f"Cycle {cycle + 1}: Circuit opened")

            # Wait for recovery
            time.sleep(0.3)

            # Reduce failure rate for recovery
            api.failure_rate = 0.1

            # Try to recover
            for i in range(5):
                try:
                    cb.call(lambda: api.call())
                except:
                    pass

            # Increase failure rate again
            api.failure_rate = 0.6

        metrics = cb.get_metrics()
        assert metrics.times_opened >= 3
        print(f"Stress test complete - Circuit opened {metrics.times_opened} times")

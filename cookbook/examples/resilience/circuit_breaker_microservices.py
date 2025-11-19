"""
Circuit Breaker Pattern for Microservices with Agno

This example demonstrates how to use circuit breakers to build resilient
agent-based microservices that can handle failures gracefully.

Scenario: E-commerce system with multiple microservices
- User Service: Manages user data
- Product Service: Manages product catalog
- Inventory Service: Manages stock levels
- Order Service: Orchestrates order creation

Each service is protected by circuit breakers to prevent cascading failures.
"""

import asyncio
import random
from typing import Optional, Dict, Any

from agno.resilience import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
    resilient,
    RetryConfig,
    BulkheadConfig,
)
from agno.resilience.configuration import (
    microservice_config,
    external_api_config,
    database_config,
    apply_environment,
    production_env,
)
from agno.resilience.metrics import get_global_collector


# ====================
# Mock Services (simulate real microservices)
# ====================

class UserService:
    """User microservice"""

    def __init__(self, failure_rate: float = 0.0):
        self.failure_rate = failure_rate
        self._circuit = CircuitBreaker(
            name="user_service",
            config=microservice_config("user", max_concurrent=100, failure_threshold=5)
        )

    def get_user(self, user_id: int) -> Dict[str, Any]:
        """Get user by ID with circuit breaker protection"""
        def _get_user():
            if random.random() < self.failure_rate:
                raise Exception("User service unavailable")
            return {
                "id": user_id,
                "name": f"User {user_id}",
                "email": f"user{user_id}@example.com"
            }

        return self._circuit.call(_get_user)


class ProductService:
    """Product microservice"""

    def __init__(self, failure_rate: float = 0.0):
        self.failure_rate = failure_rate
        self._circuit = CircuitBreaker(
            name="product_service",
            config=microservice_config("product", max_concurrent=100)
        )

    def get_product(self, product_id: int) -> Dict[str, Any]:
        """Get product by ID with circuit breaker protection"""
        def _get_product():
            if random.random() < self.failure_rate:
                raise Exception("Product service unavailable")
            return {
                "id": product_id,
                "name": f"Product {product_id}",
                "price": random.uniform(10, 1000)
            }

        return self._circuit.call(_get_product)


class InventoryService:
    """Inventory microservice"""

    def __init__(self, failure_rate: float = 0.0):
        self.failure_rate = failure_rate
        self._circuit = CircuitBreaker(
            name="inventory_service",
            config=microservice_config("inventory", max_concurrent=50)
        )

    def check_availability(self, product_id: int, quantity: int) -> bool:
        """Check if product is in stock with circuit breaker protection"""
        def _check_availability():
            if random.random() < self.failure_rate:
                raise Exception("Inventory service unavailable")
            return random.choice([True, True, True, False])  # 75% chance in stock

        return self._circuit.call(_check_availability)

    def reserve_inventory(self, product_id: int, quantity: int) -> bool:
        """Reserve inventory with circuit breaker protection"""
        def _reserve():
            if random.random() < self.failure_rate:
                raise Exception("Inventory service unavailable")
            return True

        return self._circuit.call(_reserve)


class OrderService:
    """Order service (orchestrator)"""

    def __init__(
        self,
        user_service: UserService,
        product_service: ProductService,
        inventory_service: InventoryService
    ):
        self.user_service = user_service
        self.product_service = product_service
        self.inventory_service = inventory_service

        # Circuit breaker for database operations
        self._db_circuit = CircuitBreaker(
            name="order_database",
            config=database_config(max_concurrent=20)
        )

    def create_order(
        self,
        user_id: int,
        product_id: int,
        quantity: int = 1
    ) -> Dict[str, Any]:
        """
        Create order with circuit breaker protection for all dependencies.

        This demonstrates graceful degradation when services are unavailable.
        """
        order_data = {
            "user_id": user_id,
            "product_id": product_id,
            "quantity": quantity,
            "status": "pending"
        }

        try:
            # Step 1: Get user details
            try:
                user = self.user_service.get_user(user_id)
                order_data["user_email"] = user["email"]
            except CircuitBreakerOpenError:
                print(f"⚠️  User service circuit open, proceeding without user details")
                order_data["user_email"] = None

            # Step 2: Get product details
            try:
                product = self.product_service.get_product(product_id)
                order_data["product_name"] = product["name"]
                order_data["price"] = product["price"]
            except CircuitBreakerOpenError:
                print(f"⚠️  Product service circuit open, using cached data")
                order_data["product_name"] = f"Product {product_id}"
                order_data["price"] = 0.0

            # Step 3: Check inventory
            try:
                available = self.inventory_service.check_availability(product_id, quantity)
                if not available:
                    order_data["status"] = "out_of_stock"
                    return order_data

                # Reserve inventory
                self.inventory_service.reserve_inventory(product_id, quantity)
            except CircuitBreakerOpenError:
                print(f"⚠️  Inventory service circuit open, creating pending order")
                order_data["status"] = "pending_inventory_check"
                return order_data

            # Step 4: Save to database
            try:
                self._save_order_to_db(order_data)
                order_data["status"] = "confirmed"
            except CircuitBreakerOpenError:
                print(f"⚠️  Database circuit open, order queued for later")
                order_data["status"] = "queued"

            return order_data

        except Exception as e:
            order_data["status"] = "failed"
            order_data["error"] = str(e)
            return order_data

    def _save_order_to_db(self, order_data: Dict[str, Any]) -> None:
        """Save order to database with circuit breaker protection"""
        def _save():
            # Simulate database operation
            if random.random() < 0.05:  # 5% failure rate
                raise Exception("Database connection error")
            return True

        self._db_circuit.call(_save)


# ====================
# Example 1: Basic Circuit Breaker Usage
# ====================

def example_basic_usage():
    """Demonstrate basic circuit breaker usage"""
    print("\n" + "="*60)
    print("Example 1: Basic Circuit Breaker Usage")
    print("="*60)

    # Create services with 20% failure rate
    user_service = UserService(failure_rate=0.2)
    product_service = ProductService(failure_rate=0.2)
    inventory_service = InventoryService(failure_rate=0.2)

    order_service = OrderService(user_service, product_service, inventory_service)

    # Create 20 orders
    successful_orders = 0
    failed_orders = 0

    for i in range(20):
        order = order_service.create_order(
            user_id=i % 5,
            product_id=i % 10,
            quantity=random.randint(1, 3)
        )

        if order["status"] == "confirmed":
            successful_orders += 1
        else:
            failed_orders += 1

        print(f"Order {i + 1}: {order['status']}")

    print(f"\n✅ Successful orders: {successful_orders}")
    print(f"❌ Failed/degraded orders: {failed_orders}")


# ====================
# Example 2: Resilient Decorator
# ====================

def example_resilient_decorator():
    """Demonstrate using @resilient decorator"""
    print("\n" + "="*60)
    print("Example 2: Resilient Decorator with Retry")
    print("="*60)

    @resilient(
        circuit_breaker_config=CircuitBreakerConfig(failure_threshold=5),
        retry_config=RetryConfig(max_attempts=3, delay_seconds=0.1),
        bulkhead_config=BulkheadConfig(max_concurrent=10),
        name="payment_api"
    )
    def process_payment(amount: float) -> Dict[str, Any]:
        """Process payment with full resilience stack"""
        if random.random() < 0.3:  # 30% failure rate
            raise Exception("Payment gateway timeout")

        return {
            "status": "success",
            "amount": amount,
            "transaction_id": f"TXN-{random.randint(1000, 9999)}"
        }

    # Process 15 payments
    successful_payments = 0
    failed_payments = 0

    for i in range(15):
        try:
            result = process_payment(amount=random.uniform(10, 500))
            successful_payments += 1
            print(f"💳 Payment {i + 1}: {result['status']} - ${result['amount']:.2f}")
        except Exception as e:
            failed_payments += 1
            print(f"💳 Payment {i + 1}: Failed - {str(e)}")

    print(f"\n✅ Successful payments: {successful_payments}")
    print(f"❌ Failed payments: {failed_payments}")


# ====================
# Example 3: Async Microservices
# ====================

async def example_async_microservices():
    """Demonstrate async circuit breakers for high-throughput services"""
    print("\n" + "="*60)
    print("Example 3: Async Microservices with Circuit Breakers")
    print("="*60)

    # Async external API call
    cb = CircuitBreaker(
        name="async_external_api",
        config=external_api_config(max_concurrent=50)
    )

    async def fetch_exchange_rate(currency: str) -> float:
        """Fetch exchange rate from external API"""
        async def _fetch():
            await asyncio.sleep(0.01)  # Simulate API latency
            if random.random() < 0.2:  # 20% failure rate
                raise Exception("API rate limit exceeded")
            return random.uniform(0.8, 1.2)

        return await cb.call_async(_fetch)

    # Make 50 concurrent API calls
    currencies = ["USD", "EUR", "GBP", "JPY", "AUD"]
    tasks = [
        fetch_exchange_rate(random.choice(currencies))
        for _ in range(50)
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    successful = sum(1 for r in results if not isinstance(r, Exception))
    failed = sum(1 for r in results if isinstance(r, Exception))

    print(f"\n✅ Successful API calls: {successful}")
    print(f"❌ Failed API calls: {failed}")

    # Show circuit state
    print(f"📊 Circuit state: {cb.get_state().value}")


# ====================
# Example 4: Metrics and Monitoring
# ====================

def example_metrics_monitoring():
    """Demonstrate metrics collection and monitoring"""
    print("\n" + "="*60)
    print("Example 4: Metrics and Monitoring")
    print("="*60)

    # Create services
    user_service = UserService(failure_rate=0.3)
    product_service = ProductService(failure_rate=0.1)
    inventory_service = InventoryService(failure_rate=0.5)

    order_service = OrderService(user_service, product_service, inventory_service)

    # Create orders
    for i in range(30):
        order_service.create_order(
            user_id=i % 5,
            product_id=i % 10,
            quantity=1
        )

    # Get global metrics
    collector = get_global_collector()
    summary = collector.get_summary()

    print("\n📊 Global Metrics Summary:")
    print(f"  Total circuits: {summary['total_circuits']}")
    print(f"  Total requests: {summary['aggregate_metrics']['total_requests']}")
    print(f"  Total failures: {summary['aggregate_metrics']['total_failures']}")
    print(f"  Overall failure rate: {summary['aggregate_metrics']['overall_failure_rate']:.2%}")

    print("\n🔴 Unhealthy circuits:")
    for circuit_name in summary['unhealthy_circuits']:
        print(f"  - {circuit_name}")

    # Individual circuit metrics
    print("\n📈 Individual Circuit Metrics:")
    for name, metrics in collector.get_all_metrics().items():
        print(f"\n  {name}:")
        print(f"    State: {metrics.current_state.value}")
        print(f"    Requests: {metrics.total_requests}")
        print(f"    Success rate: {metrics.current_success_rate:.2%}")
        print(f"    Times opened: {metrics.times_opened}")


# ====================
# Example 5: Configuration Templates
# ====================

def example_configuration_templates():
    """Demonstrate using configuration templates"""
    print("\n" + "="*60)
    print("Example 5: Configuration Templates")
    print("="*60)

    from agno.resilience.configuration import (
        critical_service_config,
        external_api_config,
        unstable_service_config,
        ml_model_config,
    )

    # Critical service (payment gateway)
    payment_cb = CircuitBreaker(
        name="payment_gateway",
        config=critical_service_config()
    )

    # External API (third-party service)
    weather_cb = CircuitBreaker(
        name="weather_api",
        config=external_api_config(max_concurrent=20)
    )

    # Unstable beta service
    beta_cb = CircuitBreaker(
        name="beta_feature",
        config=unstable_service_config()
    )

    # ML model inference
    ml_cb = CircuitBreaker(
        name="gpt4_inference",
        config=ml_model_config(max_concurrent=3)
    )

    print("✅ Created circuit breakers with templates:")
    print(f"  - Payment Gateway: {payment_cb.config.failure_threshold} failures to open")
    print(f"  - Weather API: {weather_cb.config.max_concurrent_calls} max concurrent")
    print(f"  - Beta Feature: {beta_cb.config.failure_threshold} failures (tolerant)")
    print(f"  - ML Inference: {ml_cb.config.max_concurrent_calls} max concurrent (GPU limit)")


# ====================
# Example 6: State Transition Hooks
# ====================

def example_state_hooks():
    """Demonstrate state transition hooks for monitoring"""
    print("\n" + "="*60)
    print("Example 6: State Transition Hooks")
    print("="*60)

    def on_circuit_open(state):
        print(f"🔴 ALERT: Circuit opened! Failure rate: {state.get_failure_rate():.2%}")

    def on_circuit_close(state):
        print(f"🟢 Circuit recovered and closed. Success rate: {state.get_success_rate():.2%}")

    def on_circuit_half_open(state):
        print(f"🟡 Circuit half-open. Testing recovery...")

    cb = CircuitBreaker(
        name="monitored_service",
        config=CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=1.0,
            on_open=on_circuit_open,
            on_close=on_circuit_close,
            on_half_open=on_circuit_half_open,
            verbose=True
        )
    )

    # Simulate failures to open circuit
    print("\nSimulating failures...")
    for i in range(5):
        try:
            cb.call(lambda: (_ for _ in ()).throw(Exception("Service error")))
        except Exception:
            pass

    # Wait for recovery
    print("\nWaiting for recovery timeout...")
    import time
    time.sleep(1.2)

    # Successful calls to close circuit
    print("\nAttempting recovery...")
    for i in range(3):
        cb.call(lambda: "success")


# ====================
# Main execution
# ====================

def main():
    """Run all examples"""
    print("\n" + "="*60)
    print("Circuit Breaker Pattern for Microservices")
    print("="*60)

    # Run sync examples
    example_basic_usage()
    example_resilient_decorator()
    example_configuration_templates()
    example_metrics_monitoring()
    example_state_hooks()

    # Run async example
    print("\nRunning async examples...")
    asyncio.run(example_async_microservices())

    print("\n" + "="*60)
    print("✅ All examples completed!")
    print("="*60)


if __name__ == "__main__":
    main()

"""
Order Processing Workflow - Real-world FSM Workflow Engine Example

This example demonstrates a production-ready order processing workflow using
the Agno Workflow Engine FSA. It showcases:

- Conditional branching based on order value and inventory
- Error handling and retries
- Progress tracking
- State callbacks
- Real-world business logic

Run: python cookbook/workflows/workflow_engine_order_processing.py
"""

from agno.utils.log import logger
from agno.workflow.engine import (
    State,
    TransitionCondition,
    WorkflowEngine,
    WorkflowEngineConfig,
)


def validate_order(ctx):
    """Validate order details."""
    logger.info("Validating order...")

    order_id = ctx.get("order_id")
    amount = ctx.get("amount", 0)

    # Simulate validation
    if not order_id:
        raise ValueError("Order ID is required")

    if amount <= 0:
        raise ValueError("Order amount must be positive")

    ctx.set("validated", True)
    logger.info(f"Order {order_id} validated successfully")
    return {"status": "validated", "amount": amount}


def check_inventory(ctx):
    """Check inventory availability."""
    logger.info("Checking inventory...")

    # Simulate inventory check
    import random

    in_stock = random.choice([True, True, True, False])  # 75% success rate

    ctx.set("in_stock", in_stock)

    if not in_stock:
        logger.warning("Item out of stock")
    else:
        logger.info("Item in stock")

    return {"in_stock": in_stock}


def process_standard_order(ctx):
    """Process standard order (amount <= 1000)."""
    logger.info("Processing standard order...")

    order_id = ctx.get("order_id")
    amount = ctx.get("amount")

    # Simulate processing
    ctx.set("processed", True)
    ctx.set("processing_fee", amount * 0.02)

    logger.info(f"Standard order {order_id} processed")
    return {"type": "standard", "fee": amount * 0.02}


def process_premium_order(ctx):
    """Process premium order (amount > 1000)."""
    logger.info("Processing premium order with priority...")

    order_id = ctx.get("order_id")
    amount = ctx.get("amount")

    # Simulate premium processing
    ctx.set("processed", True)
    ctx.set("priority", True)
    ctx.set("processing_fee", amount * 0.01)  # Lower fee for premium

    logger.info(f"Premium order {order_id} processed with priority")
    return {"type": "premium", "fee": amount * 0.01}


def notify_customer(ctx):
    """Send notification to customer."""
    logger.info("Sending customer notification...")

    order_id = ctx.get("order_id")
    in_stock = ctx.get("in_stock")

    if in_stock:
        message = f"Order {order_id} is being processed"
    else:
        message = f"Order {order_id} - Item currently out of stock"

    ctx.set("notification_sent", True)
    logger.info(f"Notification sent: {message}")
    return {"message": message}


def handle_out_of_stock(ctx):
    """Handle out of stock scenario."""
    logger.info("Handling out of stock...")

    order_id = ctx.get("order_id")

    # Simulate backorder creation
    ctx.set("backorder_created", True)
    ctx.set("estimated_days", 7)

    logger.info(f"Backorder created for {order_id}, estimated 7 days")
    return {"backorder": True, "estimated_days": 7}


def complete_order(ctx):
    """Complete the order."""
    logger.info("Completing order...")

    order_id = ctx.get("order_id")
    amount = ctx.get("amount")
    processing_fee = ctx.get("processing_fee", 0)

    logger.info(f"Order {order_id} completed - Amount: ${amount}, Fee: ${processing_fee}")

    return {
        "order_id": order_id,
        "amount": amount,
        "fee": processing_fee,
        "status": "completed",
    }


def create_order_workflow():
    """Create and configure the order processing workflow."""

    # Configure engine
    config = WorkflowEngineConfig(
        name="order_processing_engine",
        max_parallel_tasks=5,
        default_timeout_seconds=30,
        enable_progress_tracking=True,
        retry_delay_seconds=2.0,
    )

    # Create engine
    engine = WorkflowEngine(name="order_processing", config=config)

    # Define states
    validate = State(
        name="validate",
        description="Validate order details",
        is_initial=True,
        retry_count=2,  # Retry validation up to 2 times
    )

    check_inv = State(
        name="check_inventory",
        description="Check inventory availability",
        retry_count=1,  # Retry inventory check once
    )

    process_std = State(
        name="process_standard", description="Process standard order"
    )

    process_prem = State(
        name="process_premium", description="Process premium order"
    )

    notify = State(name="notify", description="Notify customer")

    out_of_stock = State(
        name="out_of_stock", description="Handle out of stock scenario"
    )

    complete = State(
        name="complete", description="Complete order", is_final=True
    )

    # Define transitions with conditions

    # After validation, check inventory
    validate.add_transition("check_inventory")

    # After inventory check, branch based on stock availability
    in_stock_condition = TransitionCondition(
        condition="in_stock == True",
        target_state="process_standard",
        description="Item is in stock",
    )

    # If in stock, branch based on order amount
    standard_condition = TransitionCondition(
        condition="in_stock == True and amount <= 1000",
        target_state="process_standard",
        description="Standard order in stock",
    )

    premium_condition = TransitionCondition(
        condition="in_stock == True and amount > 1000",
        target_state="process_premium",
        description="Premium order in stock",
    )

    out_of_stock_condition = TransitionCondition(
        condition="in_stock == False",
        target_state="out_of_stock",
        description="Item out of stock",
    )

    check_inv.add_transition("process_standard", conditions=[standard_condition])
    check_inv.add_transition("process_premium", conditions=[premium_condition])
    check_inv.add_transition("out_of_stock", conditions=[out_of_stock_condition])

    # After processing, notify customer
    process_std.add_transition("notify")
    process_prem.add_transition("notify")
    out_of_stock.add_transition("notify")

    # After notification, complete
    notify.add_transition("complete")

    # Add states to engine
    engine.add_state(validate, handler=validate_order)
    engine.add_state(check_inv, handler=check_inventory)
    engine.add_state(process_std, handler=process_standard_order)
    engine.add_state(process_prem, handler=process_premium_order)
    engine.add_state(notify, handler=notify_customer)
    engine.add_state(out_of_stock, handler=handle_out_of_stock)
    engine.add_state(complete, handler=complete_order)

    return engine


def main():
    """Run the order processing workflow examples."""

    print("\n" + "=" * 60)
    print("Order Processing Workflow - FSM Engine Demo")
    print("=" * 60)

    # Example 1: Standard order
    print("\n📦 Example 1: Standard Order ($500)")
    print("-" * 60)

    engine = create_order_workflow()

    for response in engine.run(order_id="ORD-001", amount=500, customer_id="CUST-123"):
        if hasattr(response, "content") and isinstance(response.content, dict):
            status = response.content.get("status")
            if status in ["state_completed", "completed"]:
                print(f"✓ {response.content}")

    # Example 2: Premium order
    print("\n💎 Example 2: Premium Order ($2500)")
    print("-" * 60)

    engine = create_order_workflow()

    for response in engine.run(order_id="ORD-002", amount=2500, customer_id="CUST-456"):
        if hasattr(response, "content") and isinstance(response.content, dict):
            status = response.content.get("status")
            if status in ["state_completed", "completed"]:
                print(f"✓ {response.content}")

    # Example 3: Get execution statistics
    print("\n📊 Workflow Statistics:")
    print("-" * 60)

    ctx = engine.get_execution_context()
    if ctx:
        stats = ctx.get_state_statistics()
        for state_name, state_stats in stats.items():
            print(f"\nState: {state_name}")
            print(f"  Executions: {state_stats['total_executions']}")
            print(f"  Successful: {state_stats['successful']}")
            print(f"  Failed: {state_stats['failed']}")
            print(f"  Avg Duration: {state_stats['avg_duration_ms']:.2f}ms")

        print(f"\nTotal Workflow Duration: {ctx.get_total_duration_ms():.2f}ms")
        print(f"Execution Path: {' → '.join(ctx.get_execution_path())}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()

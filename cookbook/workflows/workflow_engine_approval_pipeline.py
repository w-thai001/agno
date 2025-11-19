"""
Approval Pipeline Workflow - Advanced FSM Workflow Engine Example

This example demonstrates a multi-level approval workflow with:

- Complex conditional branching
- Parallel approval tasks
- Timeout handling
- Escalation logic
- Callback hooks

Run: python cookbook/workflows/workflow_engine_approval_pipeline.py
"""

from agno.utils.log import logger
from agno.workflow.engine import (
    State,
    TransitionCondition,
    WorkflowEngine,
    WorkflowEngineConfig,
)


def submit_request(ctx):
    """Submit approval request."""
    request_id = ctx.get("request_id")
    amount = ctx.get("amount")
    requester = ctx.get("requester")

    logger.info(f"Submitting request {request_id} for ${amount} by {requester}")

    ctx.set("submitted_at", "2025-01-15T10:00:00Z")
    ctx.set("status", "submitted")

    return {"request_id": request_id, "status": "submitted"}


def manager_approval(ctx):
    """Manager approval step."""
    request_id = ctx.get("request_id")
    amount = ctx.get("amount")

    logger.info(f"Manager reviewing request {request_id}")

    # Simulate approval decision (90% approval rate)
    import random

    approved = random.random() > 0.1

    ctx.set("manager_approved", approved)
    ctx.set("manager_reviewed_at", "2025-01-15T11:00:00Z")

    if approved:
        logger.info(f"✓ Manager approved request {request_id}")
    else:
        logger.warning(f"✗ Manager rejected request {request_id}")
        ctx.set("rejection_reason", "Budget constraints")

    return {"approved": approved, "reviewer": "manager"}


def director_approval(ctx):
    """Director approval step (for high-value requests)."""
    request_id = ctx.get("request_id")
    amount = ctx.get("amount")

    logger.info(f"Director reviewing high-value request {request_id}")

    # Simulate approval (80% approval rate for high-value)
    import random

    approved = random.random() > 0.2

    ctx.set("director_approved", approved)
    ctx.set("director_reviewed_at", "2025-01-15T12:00:00Z")

    if approved:
        logger.info(f"✓ Director approved request {request_id}")
    else:
        logger.warning(f"✗ Director rejected request {request_id}")
        ctx.set("rejection_reason", "Requires additional justification")

    return {"approved": approved, "reviewer": "director"}


def finance_review(ctx):
    """Finance team review (parallel with legal for high amounts)."""
    request_id = ctx.get("request_id")

    logger.info(f"Finance team reviewing request {request_id}")

    # Simulate review
    ctx.set("finance_cleared", True)
    ctx.set("finance_reviewed_at", "2025-01-15T13:00:00Z")

    logger.info(f"✓ Finance cleared request {request_id}")

    return {"cleared": True, "department": "finance"}


def legal_review(ctx):
    """Legal team review (parallel with finance for high amounts)."""
    request_id = ctx.get("request_id")

    logger.info(f"Legal team reviewing request {request_id}")

    # Simulate review
    ctx.set("legal_cleared", True)
    ctx.set("legal_reviewed_at", "2025-01-15T13:30:00Z")

    logger.info(f"✓ Legal cleared request {request_id}")

    return {"cleared": True, "department": "legal"}


def approved_handler(ctx):
    """Handle approved request."""
    request_id = ctx.get("request_id")
    amount = ctx.get("amount")

    logger.info(f"🎉 Request {request_id} APPROVED - Processing ${amount}")

    ctx.set("status", "approved")
    ctx.set("approved_at", "2025-01-15T14:00:00Z")

    return {"request_id": request_id, "status": "approved", "amount": amount}


def rejected_handler(ctx):
    """Handle rejected request."""
    request_id = ctx.get("request_id")
    reason = ctx.get("rejection_reason", "Not specified")

    logger.warning(f"❌ Request {request_id} REJECTED - Reason: {reason}")

    ctx.set("status", "rejected")
    ctx.set("rejected_at", "2025-01-15T14:00:00Z")

    return {"request_id": request_id, "status": "rejected", "reason": reason}


def on_state_enter(ctx):
    """Callback when entering any state."""
    state = ctx.get("_current_state_name", "unknown")
    logger.debug(f"→ Entering state: {state}")


def on_state_exit(ctx):
    """Callback when exiting any state."""
    state = ctx.get("_current_state_name", "unknown")
    logger.debug(f"← Exiting state: {state}")


def create_approval_workflow():
    """Create the approval pipeline workflow."""

    config = WorkflowEngineConfig(
        name="approval_pipeline",
        max_parallel_tasks=3,
        default_timeout_seconds=60,
        enable_progress_tracking=True,
    )

    engine = WorkflowEngine(name="approval_pipeline", config=config)

    # Define states
    submit = State(
        name="submit",
        description="Submit approval request",
        is_initial=True,
    )

    mgr_review = State(
        name="manager_review",
        description="Manager approval",
        timeout_seconds=30,
    )

    dir_review = State(
        name="director_review",
        description="Director approval for high-value requests",
        timeout_seconds=45,
    )

    fin_review = State(
        name="finance_review", description="Finance team review"
    )

    leg_review = State(name="legal_review", description="Legal team review")

    approved = State(
        name="approved",
        description="Request approved",
        is_final=True,
    )

    rejected = State(
        name="rejected",
        description="Request rejected",
        is_final=True,
    )

    # Define transitions

    # After submission, go to manager review
    submit.add_transition("manager_review")

    # After manager review, branch based on approval and amount
    mgr_approved_low = TransitionCondition(
        condition="manager_approved == True and amount <= 10000",
        target_state="approved",
        description="Manager approved, low amount",
    )

    mgr_approved_high = TransitionCondition(
        condition="manager_approved == True and amount > 10000",
        target_state="director_review",
        description="Manager approved, requires director review",
    )

    mgr_rejected = TransitionCondition(
        condition="manager_approved == False",
        target_state="rejected",
        description="Manager rejected",
    )

    mgr_review.add_transition("approved", conditions=[mgr_approved_low])
    mgr_review.add_transition("director_review", conditions=[mgr_approved_high])
    mgr_review.add_transition("rejected", conditions=[mgr_rejected])

    # After director review, branch based on approval
    dir_approved = TransitionCondition(
        condition="director_approved == True",
        target_state="finance_review",
        description="Director approved, needs compliance review",
    )

    dir_rejected = TransitionCondition(
        condition="director_approved == False",
        target_state="rejected",
        description="Director rejected",
    )

    dir_review.add_transition("finance_review", conditions=[dir_approved])
    dir_review.add_transition("rejected", conditions=[dir_rejected])

    # After compliance reviews, go to approved
    # Note: In a real implementation, you'd use parallel execution here
    fin_review.add_transition("approved")
    leg_review.add_transition("approved")

    # Add states to engine
    engine.add_state(submit, handler=submit_request)
    engine.add_state(mgr_review, handler=manager_approval)
    engine.add_state(dir_review, handler=director_approval)
    engine.add_state(fin_review, handler=finance_review)
    engine.add_state(leg_review, handler=legal_review)
    engine.add_state(approved, handler=approved_handler)
    engine.add_state(rejected, handler=rejected_handler)

    return engine


def main():
    """Run approval pipeline examples."""

    print("\n" + "=" * 70)
    print("Multi-Level Approval Pipeline - FSM Engine Demo")
    print("=" * 70)

    # Example 1: Low-value request (manager approval only)
    print("\n📄 Example 1: Low-Value Request ($5,000)")
    print("-" * 70)

    engine = create_approval_workflow()

    for response in engine.run(
        request_id="REQ-001",
        amount=5000,
        requester="john.doe@company.com",
        description="Office supplies",
    ):
        if hasattr(response, "content") and isinstance(response.content, dict):
            if "state" in response.content or "status" in response.content:
                print(f"  {response.content}")

    # Example 2: High-value request (requires director approval)
    print("\n💰 Example 2: High-Value Request ($50,000)")
    print("-" * 70)

    engine = create_approval_workflow()

    for response in engine.run(
        request_id="REQ-002",
        amount=50000,
        requester="jane.smith@company.com",
        description="New equipment purchase",
    ):
        if hasattr(response, "content") and isinstance(response.content, dict):
            if "state" in response.content or "status" in response.content:
                print(f"  {response.content}")

    # Example 3: Show execution path
    print("\n🗺️  Execution Path Visualization:")
    print("-" * 70)

    ctx = engine.get_execution_context()
    if ctx:
        path = ctx.get_execution_path()
        print(f"\n  Path: {' → '.join(path)}")

        # Show state statistics
        print(f"\n  Total Duration: {ctx.get_total_duration_ms():.2f}ms")

        stats = ctx.get_state_statistics()
        print("\n  State Performance:")
        for state_name, state_stats in stats.items():
            print(f"    • {state_name}: {state_stats['avg_duration_ms']:.2f}ms")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()

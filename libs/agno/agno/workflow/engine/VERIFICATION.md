# Workflow Engine FSA - Verification Guide

## Installation

Before using the workflow engine, ensure dependencies are installed:

```bash
# Install agno with dependencies
pip install -e libs/agno

# Or install from requirements
pip install pydantic typing-extensions
```

## Quick Verification

Run this script to verify the installation:

```python
#!/usr/bin/env python
"""Verify Workflow Engine FSA installation."""

try:
    from agno.workflow.engine import (
        WorkflowEngine,
        WorkflowEngineConfig,
        State,
        StateTransition,
        TransitionCondition,
        ExecutionContext,
    )

    print("✓ All core imports successful")

    # Create a simple workflow
    engine = WorkflowEngine(name="verification")

    def test_handler(ctx):
        ctx.set("verified", True)
        return "success"

    start = State(name="start", is_initial=True, is_final=True)
    engine.add_state(start, handler=test_handler)

    # Validate
    errors = engine.validate()
    if errors:
        print(f"✗ Validation failed: {errors}")
    else:
        print("✓ Workflow validation passed")

    # Execute
    results = list(engine.run())

    if any(r.content.get("status") == "completed" for r in results if isinstance(r.content, dict)):
        print("✓ Workflow execution successful")
        print("\n🎉 Workflow Engine FSA is working correctly!")
    else:
        print("✗ Workflow execution failed")

except ImportError as e:
    print(f"✗ Import error: {e}")
    print("\nPlease install dependencies:")
    print("  pip install -e libs/agno")
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
```

## Run Tests

```bash
# Run all workflow engine tests
pytest libs/agno/tests/unit/workflow/test_fsm_engine.py -v

# Run specific test
pytest libs/agno/tests/unit/workflow/test_fsm_engine.py::test_simple_workflow_execution -v

# Run with coverage
pytest libs/agno/tests/unit/workflow/ --cov=agno.workflow.engine --cov-report=html
```

## Run Examples

```bash
# Order processing workflow
python cookbook/workflows/workflow_engine_order_processing.py

# Approval pipeline workflow
python cookbook/workflows/workflow_engine_approval_pipeline.py
```

## Expected Output

When running examples, you should see:

```
==============================================================
Order Processing Workflow - FSM Engine Demo
==============================================================

📦 Example 1: Standard Order ($500)
--------------------------------------------------------------
Validating order...
Order ORD-001 validated successfully
Checking inventory...
Item in stock
Processing standard order...
Standard order ORD-001 processed
Sending customer notification...
Notification sent: Order ORD-001 is being processed
Completing order...
Order ORD-001 completed - Amount: $500, Fee: $10.0
✓ {'status': 'state_completed', 'state': 'validate', ...}
...
```

## Troubleshooting

### Import Errors

If you see import errors, ensure agno is installed:

```bash
pip install -e libs/agno
```

### Missing Dependencies

If pydantic or other dependencies are missing:

```bash
pip install pydantic typing-extensions
```

### Test Failures

Run tests in verbose mode to see details:

```bash
pytest libs/agno/tests/unit/workflow/test_fsm_engine.py -vv
```

## Code Structure Verification

Verify all files are in place:

```bash
tree libs/agno/agno/workflow/engine/
```

Expected structure:
```
libs/agno/agno/workflow/engine/
├── __init__.py
├── context.py
├── fsm_engine.py
├── state.py
└── VERIFICATION.md
```

## Line Count Verification

```bash
wc -l libs/agno/agno/workflow/engine/*.py
wc -l libs/agno/tests/unit/workflow/test_fsm_engine.py
wc -l cookbook/workflows/workflow_engine_*.py
```

Expected totals:
- Implementation: ~600 lines
- Tests: ~400 lines
- Examples: ~250 lines
- Total: ~1250 lines (code only)

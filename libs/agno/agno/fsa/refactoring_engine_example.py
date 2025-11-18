"""
Example usage of the Refactoring Engine FSA.

This example demonstrates various refactoring operations including:
- Extract method
- Rename symbol
- Inline method/variable
- Remove dead code
- Preview and safety analysis
- Undo/redo functionality
"""

from agno.fsa.refactoring_engine import (
    RefactoringEngine,
    RefactoringOperation,
    RefactoringOperationType,
    Scope,
)


def example_extract_method():
    """Demonstrate extract method refactoring."""
    print("\n=== Extract Method Example ===")

    code = '''
class DataProcessor:
    def process_data(self, data):
        # Data validation
        if not data:
            return None
        if not isinstance(data, list):
            return None

        # Process the data
        result = []
        for item in data:
            result.append(item * 2)
        return result
'''

    engine = RefactoringEngine()

    # Extract validation logic into separate method
    refactored = engine.extract_method(code, 4, 7, 'validate_data')

    print("Original code:")
    print(code)
    print("\nRefactored code:")
    print(refactored)


def example_rename_symbol():
    """Demonstrate symbol renaming."""
    print("\n=== Rename Symbol Example ===")

    code = '''
class Calculator:
    def calc(self, x, y):
        temp = x + y
        result = temp * 2
        return result

calculator = Calculator()
answer = calculator.calc(10, 20)
'''

    engine = RefactoringEngine()

    # Rename method from 'calc' to 'calculate'
    refactored = engine.rename_symbol(code, 'calc', 'calculate', Scope.MODULE)

    print("Original code:")
    print(code)
    print("\nRefactored code (renamed 'calc' to 'calculate'):")
    print(refactored)


def example_inline_variable():
    """Demonstrate inline variable refactoring."""
    print("\n=== Inline Variable Example ===")

    code = '''
def calculate_price(base_price, tax_rate):
    tax = base_price * tax_rate
    total = base_price + tax
    return total
'''

    engine = RefactoringEngine()

    # Inline the 'tax' variable
    refactored = engine.inline_variable(code, 'tax')

    print("Original code:")
    print(code)
    print("\nRefactored code (inlined 'tax' variable):")
    print(refactored)


def example_remove_dead_code():
    """Demonstrate dead code removal."""
    print("\n=== Remove Dead Code Example ===")

    code = '''
def process_order(order):
    if order.is_valid():
        order.process()
        return True
    else:
        return False

    # This code is unreachable
    print("Order processed")
    log_order(order)
'''

    engine = RefactoringEngine()

    # Remove dead code
    refactored = engine.remove_dead_code(code)

    print("Original code:")
    print(code)
    print("\nRefactored code (dead code removed):")
    print(refactored)


def example_preview_and_safety():
    """Demonstrate preview and safety analysis."""
    print("\n=== Preview and Safety Analysis Example ===")

    code = '''
class UserManager:
    def get_user(self, user_id):
        return database.query(user_id)

    def delete_user(self, user_id):
        user = self.get_user(user_id)
        if user:
            database.delete(user)
'''

    engine = RefactoringEngine()

    # Create refactoring operation
    operation = RefactoringOperation(
        operation_type=RefactoringOperationType.RENAME_SYMBOL,
        parameters={'old_name': 'get_user', 'new_name': 'fetch_user'}
    )

    # Preview the refactoring
    preview = engine.preview_refactoring(code, operation)

    print("Original code:")
    print(preview.original_code)
    print("\nRefactored code preview:")
    print(preview.refactored_code)
    print("\nSafety score:", preview.safety_score)
    print("Changes:", preview.changes_description)

    # Analyze safety
    safety = engine.analyze_refactoring_safety(code, operation)
    print("\nSafety Analysis:")
    print(f"  Risk level: {safety.risk_level}")
    print(f"  Safety score: {safety.safety_score}")
    print(f"  Breaking changes: {safety.breaking_changes or 'None'}")


def example_undo_redo():
    """Demonstrate undo/redo functionality."""
    print("\n=== Undo/Redo Example ===")

    code = '''
x = 10
y = x + 5
print(y)
'''

    engine = RefactoringEngine()

    print("Original code:")
    print(code)

    # First refactoring: rename x to value
    operation1 = RefactoringOperation(
        operation_type=RefactoringOperationType.RENAME_SYMBOL,
        parameters={'old_name': 'x', 'new_name': 'value'}
    )
    result1 = engine.refactor(code, operation1)

    print("\nAfter first refactoring (x -> value):")
    print(result1.refactored_code)

    # Second refactoring: rename y to result
    operation2 = RefactoringOperation(
        operation_type=RefactoringOperationType.RENAME_SYMBOL,
        parameters={'old_name': 'y', 'new_name': 'result'}
    )
    result2 = engine.refactor(result1.refactored_code, operation2)

    print("\nAfter second refactoring (y -> result):")
    print(result2.refactored_code)

    # Undo last refactoring
    undone = engine.undo_refactoring()
    print("\nAfter undo:")
    print(undone)

    # Redo the refactoring
    redone = engine.redo_refactoring()
    print("\nAfter redo:")
    print(redone)


def example_complex_workflow():
    """Demonstrate a complex refactoring workflow."""
    print("\n=== Complex Refactoring Workflow ===")

    code = '''
class OrderProcessor:
    def process(self, order):
        # Validate order
        if not order:
            return False
        if not order.items:
            return False
        if not order.customer:
            return False

        # Calculate total
        total = 0
        for item in order.items:
            total = total + item.price

        # Apply discount
        if total > 100:
            total = total * 0.9

        order.total = total
        return True
'''

    engine = RefactoringEngine()

    print("Step 1: Extract validation logic")
    step1 = engine.extract_method(code, 4, 9, 'validate_order')
    print(step1)

    print("\n\nStep 2: Extract variable for discount calculation")
    operation = RefactoringOperation(
        operation_type=RefactoringOperationType.EXTRACT_VARIABLE,
        parameters={'expression': '0.9', 'variable_name': 'DISCOUNT_RATE'}
    )
    result = engine.refactor(step1, operation)
    print(result.refactored_code)

    print("\n\nStep 3: Rename 'process' to 'process_order'")
    step3 = engine.rename_symbol(result.refactored_code, 'process', 'process_order')
    print(step3)


def example_validation():
    """Demonstrate refactoring validation."""
    print("\n=== Refactoring Validation Example ===")

    original = '''
def calculate(a, b):
    return a + b

result = calculate(10, 20)
'''

    refactored = '''
def compute(a, b):
    return a + b

result = compute(10, 20)
'''

    engine = RefactoringEngine()

    # Validate the refactoring
    validation = engine.validate_refactoring(original, refactored)

    print("Original code:")
    print(original)
    print("\nRefactored code:")
    print(refactored)
    print("\nValidation result:")
    print(f"  Valid: {validation.is_valid}")
    print(f"  Errors: {validation.errors or 'None'}")
    print(f"  Warnings: {validation.warnings or 'None'}")
    print(f"  Suggestions: {validation.suggestions or 'None'}")


def main():
    """Run all examples."""
    print("=" * 70)
    print("REFACTORING ENGINE FSA - EXAMPLE USAGE")
    print("=" * 70)

    example_extract_method()
    example_rename_symbol()
    example_inline_variable()
    example_remove_dead_code()
    example_preview_and_safety()
    example_undo_redo()
    example_complex_workflow()
    example_validation()

    print("\n" + "=" * 70)
    print("All examples completed!")
    print("=" * 70)


if __name__ == "__main__":
    main()

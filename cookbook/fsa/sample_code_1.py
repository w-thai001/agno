"""Sample code file 1 - Simple calculator with moderate complexity."""


def add(a, b):
    """Add two numbers."""
    return a + b


def subtract(a, b):
    """Subtract b from a."""
    return a - b


def multiply(a, b):
    """Multiply two numbers."""
    return a * b


def divide(a, b):
    """Divide a by b with error handling."""
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b


def calculate(operation, a, b):
    """
    Perform a calculation based on the operation.

    Args:
        operation: The operation to perform (+, -, *, /)
        a: First operand
        b: Second operand

    Returns:
        Result of the calculation
    """
    if operation == "+":
        return add(a, b)
    elif operation == "-":
        return subtract(a, b)
    elif operation == "*":
        return multiply(a, b)
    elif operation == "/":
        return divide(a, b)
    else:
        raise ValueError(f"Unknown operation: {operation}")


class Calculator:
    """A simple calculator class."""

    def __init__(self):
        self.history = []

    def calculate(self, operation, a, b):
        """Calculate and store in history."""
        result = calculate(operation, a, b)
        self.history.append(f"{a} {operation} {b} = {result}")
        return result

    def get_history(self):
        """Get calculation history."""
        return self.history

    def clear_history(self):
        """Clear calculation history."""
        self.history = []

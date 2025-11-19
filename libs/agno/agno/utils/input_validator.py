"""Input Validator FSA (Finite State Automaton)

A simple validation FSA with string, number, email, and URL validators.
"""

import re
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union


class ValidationState(Enum):
    """States for the validation FSA."""

    INITIAL = "initial"
    VALIDATING = "validating"
    VALID = "valid"
    INVALID = "invalid"


class ValidatorType(Enum):
    """Types of validators available."""

    STRING = "string"
    NUMBER = "number"
    EMAIL = "email"
    URL = "url"


class ValidationResult:
    """Result of a validation operation."""

    def __init__(self, is_valid: bool, value: Any, errors: Optional[List[str]] = None):
        self.is_valid = is_valid
        self.value = value
        self.errors = errors or []

    def __bool__(self) -> bool:
        return self.is_valid

    def __repr__(self) -> str:
        return f"ValidationResult(is_valid={self.is_valid}, value={self.value}, errors={self.errors})"


class ValidatorFSA:
    """Finite State Automaton for input validation."""

    # Email regex pattern (simplified but covers most cases)
    EMAIL_PATTERN = re.compile(
        r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    )

    # URL regex pattern (simplified)
    URL_PATTERN = re.compile(
        r"^https?://"  # http:// or https://
        r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # domain...
        r"localhost|"  # localhost...
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ...or ip
        r"(?::\d+)?"  # optional port
        r"(?:/?|[/?]\S+)$",
        re.IGNORECASE
    )

    def __init__(self):
        self.state = ValidationState.INITIAL
        self.validators: Dict[str, Callable] = {
            ValidatorType.STRING.value: self._validate_string,
            ValidatorType.NUMBER.value: self._validate_number,
            ValidatorType.EMAIL.value: self._validate_email,
            ValidatorType.URL.value: self._validate_url,
        }

    def _transition(self, new_state: ValidationState) -> None:
        """Transition to a new state."""
        self.state = new_state

    def _validate_string(
        self,
        value: Any,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        pattern: Optional[str] = None,
    ) -> ValidationResult:
        """Validate string input."""
        errors = []

        if not isinstance(value, str):
            return ValidationResult(False, value, ["Value must be a string"])

        if min_length is not None and len(value) < min_length:
            errors.append(f"String must be at least {min_length} characters long")

        if max_length is not None and len(value) > max_length:
            errors.append(f"String must be at most {max_length} characters long")

        if pattern is not None:
            if not re.match(pattern, value):
                errors.append(f"String must match pattern: {pattern}")

        is_valid = len(errors) == 0
        return ValidationResult(is_valid, value, errors)

    def _validate_number(
        self,
        value: Any,
        min_value: Optional[Union[int, float]] = None,
        max_value: Optional[Union[int, float]] = None,
        integer_only: bool = False,
    ) -> ValidationResult:
        """Validate number input."""
        errors = []

        # Try to convert to number if it's a string
        if isinstance(value, str):
            try:
                value = int(value) if integer_only else float(value)
            except ValueError:
                return ValidationResult(False, value, ["Value must be a valid number"])

        if not isinstance(value, (int, float)):
            return ValidationResult(False, value, ["Value must be a number"])

        if integer_only and not isinstance(value, int) and value != int(value):
            errors.append("Value must be an integer")

        if min_value is not None and value < min_value:
            errors.append(f"Number must be at least {min_value}")

        if max_value is not None and value > max_value:
            errors.append(f"Number must be at most {max_value}")

        is_valid = len(errors) == 0
        return ValidationResult(is_valid, value, errors)

    def _validate_email(self, value: Any) -> ValidationResult:
        """Validate email input."""
        if not isinstance(value, str):
            return ValidationResult(False, value, ["Email must be a string"])

        if not self.EMAIL_PATTERN.match(value):
            return ValidationResult(False, value, ["Invalid email format"])

        return ValidationResult(True, value)

    def _validate_url(self, value: Any, require_https: bool = False) -> ValidationResult:
        """Validate URL input."""
        if not isinstance(value, str):
            return ValidationResult(False, value, ["URL must be a string"])

        if not self.URL_PATTERN.match(value):
            return ValidationResult(False, value, ["Invalid URL format"])

        if require_https and not value.startswith("https://"):
            return ValidationResult(False, value, ["URL must use HTTPS"])

        return ValidationResult(True, value)

    def validate(
        self,
        value: Any,
        validator_type: Union[ValidatorType, str],
        **options
    ) -> ValidationResult:
        """
        Validate input using the specified validator.

        Args:
            value: The value to validate
            validator_type: Type of validator to use
            **options: Additional options for the validator

        Returns:
            ValidationResult with validation status and errors
        """
        # Transition to validating state
        self._transition(ValidationState.VALIDATING)

        # Get validator type
        if isinstance(validator_type, ValidatorType):
            validator_type = validator_type.value

        # Get validator function
        validator = self.validators.get(validator_type)
        if validator is None:
            self._transition(ValidationState.INVALID)
            return ValidationResult(
                False,
                value,
                [f"Unknown validator type: {validator_type}"]
            )

        # Run validation
        result = validator(value, **options)

        # Transition to appropriate state
        if result.is_valid:
            self._transition(ValidationState.VALID)
        else:
            self._transition(ValidationState.INVALID)

        return result

    def validate_multiple(
        self,
        values: Dict[str, Any],
        schemas: Dict[str, Dict[str, Any]]
    ) -> Dict[str, ValidationResult]:
        """
        Validate multiple values against their schemas.

        Args:
            values: Dictionary of values to validate
            schemas: Dictionary of validation schemas

        Returns:
            Dictionary of validation results
        """
        results = {}

        for key, value in values.items():
            schema = schemas.get(key)
            if schema is None:
                results[key] = ValidationResult(
                    False,
                    value,
                    [f"No validation schema found for key: {key}"]
                )
                continue

            validator_type = schema.get("type")
            options = {k: v for k, v in schema.items() if k != "type"}

            results[key] = self.validate(value, validator_type, **options)

        return results

    def reset(self) -> None:
        """Reset the FSA to initial state."""
        self._transition(ValidationState.INITIAL)


# Convenience functions for quick validation
def validate_string(
    value: Any,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    pattern: Optional[str] = None,
) -> ValidationResult:
    """Quick string validation."""
    fsa = ValidatorFSA()
    return fsa.validate(
        value,
        ValidatorType.STRING,
        min_length=min_length,
        max_length=max_length,
        pattern=pattern,
    )


def validate_number(
    value: Any,
    min_value: Optional[Union[int, float]] = None,
    max_value: Optional[Union[int, float]] = None,
    integer_only: bool = False,
) -> ValidationResult:
    """Quick number validation."""
    fsa = ValidatorFSA()
    return fsa.validate(
        value,
        ValidatorType.NUMBER,
        min_value=min_value,
        max_value=max_value,
        integer_only=integer_only,
    )


def validate_email(value: Any) -> ValidationResult:
    """Quick email validation."""
    fsa = ValidatorFSA()
    return fsa.validate(value, ValidatorType.EMAIL)


def validate_url(value: Any, require_https: bool = False) -> ValidationResult:
    """Quick URL validation."""
    fsa = ValidatorFSA()
    return fsa.validate(value, ValidatorType.URL, require_https=require_https)

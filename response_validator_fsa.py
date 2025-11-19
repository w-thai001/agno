"""Response Validator FSA - Validates HTTP responses using finite state automaton."""
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union
from dataclasses import dataclass

class State(Enum):
    """FSA states for response validation."""
    INIT = "init"
    VALIDATING_STATUS = "validating_status"
    VALIDATING_CONTENT_TYPE = "validating_content_type"
    VALIDATING_BODY = "validating_body"
    VALID = "valid"
    INVALID = "invalid"

@dataclass
class ValidationResult:
    """Result of validation process."""
    is_valid: bool
    state: State
    errors: List[str]


class ResponseValidatorFSA:
    """Finite State Automaton for HTTP response validation."""

    def __init__(
        self,
        valid_status_codes: Optional[Set[int]] = None,
        valid_content_types: Optional[Set[str]] = None,
        required_body_fields: Optional[List[str]] = None,
    ):
        self.valid_status_codes = valid_status_codes or {200, 201, 202, 204}
        self.valid_content_types = valid_content_types or {"application/json"}
        self.required_body_fields = required_body_fields or []
        self.state = State.INIT
        self.errors: List[str] = []

    def reset(self) -> None:
        """Reset FSA to initial state."""
        self.state = State.INIT
        self.errors = []

    def validate(
        self,
        status_code: int,
        content_type: Optional[str] = None,
        body: Optional[Union[Dict[str, Any], List, str]] = None,
    ) -> ValidationResult:
        """Validate HTTP response through FSA state transitions."""
        self.reset()

        # State transition: INIT -> VALIDATING_STATUS
        self.state = State.VALIDATING_STATUS
        if not self._validate_status_code(status_code):
            self.state = State.INVALID
            return self._build_result()

        # State transition: VALIDATING_STATUS -> VALIDATING_CONTENT_TYPE
        self.state = State.VALIDATING_CONTENT_TYPE
        if content_type is not None and not self._validate_content_type(content_type):
            self.state = State.INVALID
            return self._build_result()

        # State transition: VALIDATING_CONTENT_TYPE -> VALIDATING_BODY
        self.state = State.VALIDATING_BODY
        if body is not None and not self._validate_body(body):
            self.state = State.INVALID
            return self._build_result()

        # State transition: VALIDATING_BODY -> VALID
        self.state = State.VALID
        return self._build_result()

    def _validate_status_code(self, status_code: int) -> bool:
        """Validate HTTP status code."""
        if status_code not in self.valid_status_codes:
            self.errors.append(
                f"Invalid status code: {status_code}. "
                f"Expected one of: {sorted(self.valid_status_codes)}"
            )
            return False
        return True

    def _validate_content_type(self, content_type: str) -> bool:
        """Validate Content-Type header."""
        # Extract base content type (ignore charset, boundary, etc.)
        base_type = content_type.split(";")[0].strip().lower()

        if base_type not in self.valid_content_types:
            self.errors.append(
                f"Invalid content type: {content_type}. "
                f"Expected one of: {sorted(self.valid_content_types)}"
            )
            return False
        return True

    def _validate_body(self, body: Union[Dict[str, Any], List, str]) -> bool:
        """Validate response body structure."""
        if not self.required_body_fields:
            return True

        if not isinstance(body, dict):
            self.errors.append(
                f"Body must be a dictionary to validate required fields. "
                f"Got: {type(body).__name__}"
            )
            return False

        missing_fields = [
            field for field in self.required_body_fields
            if field not in body
        ]

        if missing_fields:
            self.errors.append(
                f"Missing required body fields: {missing_fields}"
            )
            return False

        return True

    def _build_result(self) -> ValidationResult:
        """Build validation result from current state."""
        return ValidationResult(
            is_valid=self.state == State.VALID,
            state=self.state,
            errors=self.errors.copy(),
        )


# Example usage and convenience functions
def validate_json_response(
    status_code: int,
    content_type: str,
    body: Dict[str, Any],
    required_fields: Optional[List[str]] = None,
) -> ValidationResult:
    """Convenience function to validate JSON responses."""
    validator = ResponseValidatorFSA(
        valid_status_codes={200, 201},
        valid_content_types={"application/json"},
        required_body_fields=required_fields,
    )
    return validator.validate(status_code, content_type, body)

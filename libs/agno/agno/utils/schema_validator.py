"""Schema Validator FSA - Finite State Automaton for JSON/XML validation."""

import json
import xml.etree.ElementTree as ET
from enum import Enum
from typing import Any, Dict, Optional, Union


class ValidationState(Enum):
    """FSA states for schema validation."""
    INIT = "init"
    VALIDATING = "validating"
    VALID = "valid"
    INVALID = "invalid"


class SchemaValidatorFSA:
    """Finite State Automaton for validating JSON and XML schemas."""

    def __init__(self):
        """Initialize FSA in INIT state."""
        self.state = ValidationState.INIT
        self.error: Optional[str] = None
        self.data: Optional[Union[Dict, ET.Element]] = None

    def validate_json(self, content: str, schema: Optional[Dict[str, Any]] = None) -> bool:
        """Validate JSON content with optional schema."""
        self.state = ValidationState.VALIDATING
        try:
            self.data = json.loads(content)
            if schema:
                self._validate_json_schema(self.data, schema)
            self.state = ValidationState.VALID
            return True
        except (json.JSONDecodeError, ValueError) as e:
            self.error = f"JSON validation failed: {str(e)}"
            self.state = ValidationState.INVALID
            return False

    def validate_xml(self, content: str, schema: Optional[str] = None) -> bool:
        """Validate XML content with optional XSD schema."""
        self.state = ValidationState.VALIDATING
        try:
            self.data = ET.fromstring(content)
            if schema:
                schema_root = ET.fromstring(schema)
                self._validate_xml_structure(self.data, schema_root)
            self.state = ValidationState.VALID
            return True
        except ET.ParseError as e:
            self.error = f"XML validation failed: {str(e)}"
            self.state = ValidationState.INVALID
            return False

    def _validate_json_schema(self, data: Any, schema: Dict[str, Any]) -> None:
        """Basic JSON schema validation."""
        if "type" in schema:
            expected_type = schema["type"]
            type_map = {"object": dict, "array": list, "string": str, "number": (int, float), "boolean": bool}
            if expected_type in type_map and not isinstance(data, type_map[expected_type]):
                raise ValueError(f"Expected type {expected_type}, got {type(data).__name__}")
        if "properties" in schema and isinstance(data, dict):
            for key, value_schema in schema["properties"].items():
                if key in data:
                    self._validate_json_schema(data[key], value_schema)
        if "required" in schema and isinstance(data, dict):
            for required_key in schema["required"]:
                if required_key not in data:
                    raise ValueError(f"Required field '{required_key}' missing")

    def _validate_xml_structure(self, element: ET.Element, schema: ET.Element) -> None:
        """Basic XML structure validation."""
        if element.tag != schema.tag:
            raise ValueError(f"Tag mismatch: expected {schema.tag}, got {element.tag}")

    def reset(self) -> None:
        """Reset FSA to INIT state."""
        self.state = ValidationState.INIT
        self.error = None
        self.data = None

"""
Data Transformer FSA - Schema Management

This module implements schema registry, inference, migration, validation,
mapping, and compatibility checking.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from .exceptions import SchemaCompatibilityError, SchemaValidationError
from .types import (
    FieldDefinition,
    Schema,
    SchemaMapping,
    TransformationRule,
    TransformationType,
    ValidationResult,
)


class SchemaRegistry:
    """Stores and versions schemas."""

    def __init__(self):
        self.schemas: Dict[str, Dict[str, Schema]] = {}  # name -> version -> schema
        self.latest_versions: Dict[str, str] = {}  # name -> latest version

    def register(self, schema: Schema) -> None:
        """
        Register a schema.

        Args:
            schema: Schema to register
        """
        if schema.name not in self.schemas:
            self.schemas[schema.name] = {}

        self.schemas[schema.name][schema.version] = schema
        self.latest_versions[schema.name] = schema.version

    def get(self, name: str, version: Optional[str] = None) -> Optional[Schema]:
        """
        Get a schema by name and optionally version.

        Args:
            name: Schema name
            version: Schema version (None = latest)

        Returns:
            Schema or None if not found
        """
        if name not in self.schemas:
            return None

        if version is None:
            version = self.latest_versions.get(name)

        return self.schemas[name].get(version)

    def get_all_versions(self, name: str) -> List[Schema]:
        """
        Get all versions of a schema.

        Args:
            name: Schema name

        Returns:
            List of schemas sorted by version
        """
        if name not in self.schemas:
            return []

        return sorted(
            self.schemas[name].values(),
            key=lambda s: s.created_at,
        )

    def delete(self, name: str, version: Optional[str] = None) -> bool:
        """
        Delete a schema or specific version.

        Args:
            name: Schema name
            version: Schema version (None = delete all versions)

        Returns:
            True if deleted, False if not found
        """
        if name not in self.schemas:
            return False

        if version is None:
            del self.schemas[name]
            if name in self.latest_versions:
                del self.latest_versions[name]
            return True
        else:
            if version in self.schemas[name]:
                del self.schemas[name][version]
                # Update latest version
                if self.schemas[name]:
                    latest = max(
                        self.schemas[name].values(),
                        key=lambda s: s.created_at,
                    )
                    self.latest_versions[name] = latest.version
                else:
                    del self.latest_versions[name]
                return True

        return False

    def list_schemas(self) -> List[str]:
        """
        List all schema names.

        Returns:
            List of schema names
        """
        return list(self.schemas.keys())


class SchemaInferrer:
    """Auto-detects schema from data."""

    @staticmethod
    def infer_from_data(data: Any, schema_name: str = "inferred") -> Schema:
        """
        Infer schema from data.

        Args:
            data: Input data (dict or list of dicts)
            schema_name: Name for the inferred schema

        Returns:
            Inferred schema
        """
        if isinstance(data, list):
            if not data:
                return Schema(name=schema_name, fields={})
            # Infer from all records
            return SchemaInferrer._infer_from_list(data, schema_name)
        elif isinstance(data, dict):
            return SchemaInferrer._infer_from_dict(data, schema_name)
        else:
            raise ValueError("Data must be a dict or list of dicts")

    @staticmethod
    def _infer_from_dict(data: Dict, schema_name: str) -> Schema:
        """Infer schema from a single dictionary."""
        fields = {}

        for key, value in data.items():
            field_type = SchemaInferrer._infer_type(value)
            fields[key] = FieldDefinition(
                name=key,
                type=field_type,
                required=value is not None,
                nullable=value is None,
            )

        return Schema(name=schema_name, fields=fields)

    @staticmethod
    def _infer_from_list(data: List[Dict], schema_name: str) -> Schema:
        """Infer schema from a list of dictionaries."""
        if not data:
            return Schema(name=schema_name, fields={})

        # Collect all field names
        all_fields: Set[str] = set()
        for record in data:
            if isinstance(record, dict):
                all_fields.update(record.keys())

        # Analyze each field across all records
        fields = {}
        for field_name in all_fields:
            values = [
                record.get(field_name)
                for record in data
                if isinstance(record, dict)
            ]

            # Determine if field is required
            non_null_values = [v for v in values if v is not None]
            required = len(non_null_values) == len(values)
            nullable = len(non_null_values) < len(values)

            # Infer type from non-null values
            if non_null_values:
                types = set(SchemaInferrer._infer_type(v) for v in non_null_values)
                # If multiple types, use the most general
                field_type = SchemaInferrer._resolve_types(types)
            else:
                field_type = "string"

            fields[field_name] = FieldDefinition(
                name=field_name,
                type=field_type,
                required=required,
                nullable=nullable,
            )

        return Schema(name=schema_name, fields=fields)

    @staticmethod
    def _infer_type(value: Any) -> str:
        """Infer type of a value."""
        if value is None:
            return "null"
        elif isinstance(value, bool):
            return "boolean"
        elif isinstance(value, int):
            return "integer"
        elif isinstance(value, float):
            return "float"
        elif isinstance(value, str):
            return "string"
        elif isinstance(value, list):
            return "array"
        elif isinstance(value, dict):
            return "object"
        elif isinstance(value, datetime):
            return "datetime"
        else:
            return "string"

    @staticmethod
    def _resolve_types(types: Set[str]) -> str:
        """Resolve multiple types to a single type."""
        if len(types) == 1:
            return types.pop()

        # Type hierarchy: string > float > integer > boolean
        if "string" in types:
            return "string"
        elif "float" in types:
            return "float"
        elif "integer" in types:
            return "integer"
        elif "boolean" in types:
            return "boolean"
        else:
            return "string"


class SchemaMigrator:
    """Migrates data between schema versions."""

    def __init__(self, registry: SchemaRegistry):
        self.registry = registry

    def migrate(
        self,
        data: Dict,
        from_schema: str,
        to_schema: str,
        from_version: Optional[str] = None,
        to_version: Optional[str] = None,
    ) -> Dict:
        """
        Migrate data from one schema version to another.

        Args:
            data: Input data
            from_schema: Source schema name
            to_schema: Target schema name
            from_version: Source schema version (None = latest)
            to_version: Target schema version (None = latest)

        Returns:
            Migrated data

        Raises:
            ValueError: If schemas not found
        """
        source = self.registry.get(from_schema, from_version)
        target = self.registry.get(to_schema, to_version)

        if source is None:
            raise ValueError(f"Source schema '{from_schema}' not found")
        if target is None:
            raise ValueError(f"Target schema '{to_schema}' not found")

        return self._migrate_data(data, source, target)

    def _migrate_data(self, data: Dict, source: Schema, target: Schema) -> Dict:
        """Migrate data between schemas."""
        result = {}

        # Copy fields that exist in both schemas
        for field_name, target_field in target.fields.items():
            if field_name in source.fields:
                # Field exists in both schemas
                source_field = source.fields[field_name]

                if source_field.type == target_field.type:
                    # Same type, direct copy
                    result[field_name] = data.get(field_name)
                else:
                    # Different type, attempt conversion
                    result[field_name] = self._convert_value(
                        data.get(field_name),
                        source_field.type,
                        target_field.type,
                    )
            else:
                # New field in target schema
                if target_field.default is not None:
                    result[field_name] = target_field.default
                elif not target_field.required:
                    result[field_name] = None
                # If required and no default, leave it out (validation will catch)

        return result

    @staticmethod
    def _convert_value(value: Any, from_type: str, to_type: str) -> Any:
        """Convert value from one type to another."""
        if value is None:
            return None

        try:
            if to_type == "string":
                return str(value)
            elif to_type == "integer":
                return int(float(value))
            elif to_type == "float":
                return float(value)
            elif to_type == "boolean":
                if isinstance(value, bool):
                    return value
                elif isinstance(value, str):
                    return value.lower() in ("true", "yes", "1")
                else:
                    return bool(value)
            else:
                return value
        except (ValueError, TypeError):
            return None


class SchemaValidator:
    """Validates data against schemas."""

    @staticmethod
    def validate(data: Any, schema: Schema) -> ValidationResult:
        """
        Validate data against a schema.

        Args:
            data: Data to validate
            schema: Schema to validate against

        Returns:
            ValidationResult
        """
        errors = []
        warnings = []
        field_errors: Dict[str, List[str]] = {}

        if isinstance(data, list):
            # Validate each record
            for i, record in enumerate(data):
                if not isinstance(record, dict):
                    errors.append(f"Record {i} is not a dictionary")
                    continue

                record_errors = SchemaValidator._validate_record(record, schema)
                if record_errors:
                    for field, field_errs in record_errors.items():
                        key = f"record[{i}].{field}"
                        field_errors[key] = field_errs
                        errors.extend([f"{key}: {err}" for err in field_errs])
        elif isinstance(data, dict):
            # Validate single record
            record_errors = SchemaValidator._validate_record(data, schema)
            if record_errors:
                field_errors.update(record_errors)
                for field, field_errs in record_errors.items():
                    errors.extend([f"{field}: {err}" for err in field_errs])
        else:
            errors.append("Data must be a dict or list of dicts")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            validated_data=data if len(errors) == 0 else None,
            field_errors=field_errors,
        )

    @staticmethod
    def _validate_record(data: Dict, schema: Schema) -> Dict[str, List[str]]:
        """Validate a single record against schema."""
        errors: Dict[str, List[str]] = {}

        # Check required fields
        for field_name, field_def in schema.fields.items():
            if field_def.required:
                if field_name not in data:
                    if field_name not in errors:
                        errors[field_name] = []
                    errors[field_name].append("Required field is missing")
                elif data[field_name] is None and not field_def.nullable:
                    if field_name not in errors:
                        errors[field_name] = []
                    errors[field_name].append("Field cannot be null")

        # Validate field types
        for field_name, value in data.items():
            if field_name in schema.fields:
                field_def = schema.fields[field_name]

                # Skip null values if nullable
                if value is None:
                    if not field_def.nullable:
                        if field_name not in errors:
                            errors[field_name] = []
                        errors[field_name].append("Field cannot be null")
                    continue

                # Validate type
                if not SchemaValidator._validate_type(value, field_def.type):
                    if field_name not in errors:
                        errors[field_name] = []
                    errors[field_name].append(
                        f"Expected type {field_def.type}, got {type(value).__name__}"
                    )

                # Validate constraints
                constraint_errors = SchemaValidator._validate_constraints(
                    value, field_def.constraints
                )
                if constraint_errors:
                    if field_name not in errors:
                        errors[field_name] = []
                    errors[field_name].extend(constraint_errors)

        return errors

    @staticmethod
    def _validate_type(value: Any, expected_type: str) -> bool:
        """Validate value type."""
        type_map = {
            "string": str,
            "integer": int,
            "float": (int, float),
            "boolean": bool,
            "array": list,
            "object": dict,
            "datetime": datetime,
        }

        expected = type_map.get(expected_type)
        if expected is None:
            return True  # Unknown type, pass validation

        return isinstance(value, expected)

    @staticmethod
    def _validate_constraints(value: Any, constraints: Dict[str, Any]) -> List[str]:
        """Validate value against constraints."""
        errors = []

        if "min" in constraints and value < constraints["min"]:
            errors.append(f"Value {value} is less than minimum {constraints['min']}")

        if "max" in constraints and value > constraints["max"]:
            errors.append(f"Value {value} exceeds maximum {constraints['max']}")

        if "min_length" in constraints and len(value) < constraints["min_length"]:
            errors.append(
                f"Length {len(value)} is less than minimum {constraints['min_length']}"
            )

        if "max_length" in constraints and len(value) > constraints["max_length"]:
            errors.append(
                f"Length {len(value)} exceeds maximum {constraints['max_length']}"
            )

        if "pattern" in constraints:
            import re

            if not re.match(constraints["pattern"], str(value)):
                errors.append(f"Value does not match pattern {constraints['pattern']}")

        if "enum" in constraints and value not in constraints["enum"]:
            errors.append(f"Value {value} not in allowed values {constraints['enum']}")

        return errors


class SchemaMapper:
    """Maps fields between schemas."""

    @staticmethod
    def create_mapping(
        source_schema: Schema,
        target_schema: Schema,
        auto_map: bool = True,
    ) -> SchemaMapping:
        """
        Create a schema mapping.

        Args:
            source_schema: Source schema
            target_schema: Target schema
            auto_map: Automatically map fields with same names

        Returns:
            SchemaMapping
        """
        mapping = SchemaMapping(
            source_schema=source_schema,
            target_schema=target_schema,
        )

        if auto_map:
            # Auto-map fields with same names
            for field_name in source_schema.fields.keys():
                if field_name in target_schema.fields:
                    mapping.add_field_mapping(field_name, field_name)

        return mapping

    @staticmethod
    def apply_mapping(data: Dict, mapping: SchemaMapping) -> Dict:
        """
        Apply schema mapping to data.

        Args:
            data: Input data
            mapping: Schema mapping

        Returns:
            Mapped data
        """
        result = {}

        # Apply field mappings
        for source_field, target_field in mapping.field_mappings.items():
            if source_field in data:
                result[target_field] = data[source_field]

        # Apply transformations
        for transformation in mapping.transformations:
            if transformation.source_field and transformation.source_field in data:
                # Apply transformation logic here
                # This is simplified - full implementation would use transformation engines
                result[transformation.target_field] = data[transformation.source_field]

        return result


class CompatibilityChecker:
    """Validates schema compatibility."""

    @staticmethod
    def check_compatibility(
        source_schema: Schema,
        target_schema: Schema,
    ) -> Tuple[bool, List[str]]:
        """
        Check if schemas are compatible.

        Args:
            source_schema: Source schema
            target_schema: Target schema

        Returns:
            Tuple of (is_compatible, list of compatibility issues)
        """
        issues = []

        # Check for missing required fields
        for field_name, target_field in target_schema.fields.items():
            if target_field.required:
                if field_name not in source_schema.fields:
                    if target_field.default is None:
                        issues.append(
                            f"Required field '{field_name}' missing in source schema "
                            f"and has no default value"
                        )

        # Check for type incompatibilities
        for field_name in source_schema.fields.keys():
            if field_name in target_schema.fields:
                source_type = source_schema.fields[field_name].type
                target_type = target_schema.fields[field_name].type

                if not CompatibilityChecker._types_compatible(source_type, target_type):
                    issues.append(
                        f"Type incompatibility for field '{field_name}': "
                        f"{source_type} -> {target_type}"
                    )

        return len(issues) == 0, issues

    @staticmethod
    def _types_compatible(source_type: str, target_type: str) -> bool:
        """Check if two types are compatible."""
        # Same type is always compatible
        if source_type == target_type:
            return True

        # String can accept anything
        if target_type == "string":
            return True

        # Float can accept integer
        if target_type == "float" and source_type == "integer":
            return True

        # Integer cannot accept float
        if target_type == "integer" and source_type == "float":
            return False

        return False

    @staticmethod
    def is_backward_compatible(
        old_schema: Schema,
        new_schema: Schema,
    ) -> Tuple[bool, List[str]]:
        """
        Check if new schema is backward compatible with old schema.

        Backward compatible means:
        - No required fields removed
        - No required fields added without defaults
        - No incompatible type changes

        Args:
            old_schema: Old schema version
            new_schema: New schema version

        Returns:
            Tuple of (is_compatible, list of issues)
        """
        issues = []

        # Check for removed required fields
        for field_name, old_field in old_schema.fields.items():
            if old_field.required and field_name not in new_schema.fields:
                issues.append(f"Required field '{field_name}' was removed")

        # Check for new required fields without defaults
        for field_name, new_field in new_schema.fields.items():
            if new_field.required and field_name not in old_schema.fields:
                if new_field.default is None:
                    issues.append(
                        f"New required field '{field_name}' added without default"
                    )

        # Check for type changes
        for field_name in old_schema.fields.keys():
            if field_name in new_schema.fields:
                old_type = old_schema.fields[field_name].type
                new_type = new_schema.fields[field_name].type

                if old_type != new_type:
                    if not CompatibilityChecker._types_compatible(old_type, new_type):
                        issues.append(
                            f"Incompatible type change for '{field_name}': "
                            f"{old_type} -> {new_type}"
                        )

        return len(issues) == 0, issues

    @staticmethod
    def is_forward_compatible(
        old_schema: Schema,
        new_schema: Schema,
    ) -> Tuple[bool, List[str]]:
        """
        Check if old schema is forward compatible with new schema.

        Forward compatible means old data can be read by new schema.

        Args:
            old_schema: Old schema version
            new_schema: New schema version

        Returns:
            Tuple of (is_compatible, list of issues)
        """
        issues = []

        # New schema should be able to handle old data
        # Check that new required fields have defaults
        for field_name, new_field in new_schema.fields.items():
            if new_field.required and field_name not in old_schema.fields:
                if new_field.default is None:
                    issues.append(
                        f"New required field '{field_name}' has no default, "
                        f"old data will fail validation"
                    )

        return len(issues) == 0, issues

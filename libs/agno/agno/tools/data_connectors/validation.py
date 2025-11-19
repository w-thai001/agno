"""
Data validation and schema mapping utilities.

Provides:
- Schema validation using Pydantic
- Type conversion and coercion
- Data quality checks
- Schema mapping and transformation
"""

import re
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set, Type, Union

from pydantic import BaseModel, Field, ValidationError, create_model
from agno.utils.log import logger


class DataValidator:
    """Validator for data quality and schema compliance."""

    def __init__(self, schema: Optional[Type[BaseModel]] = None, strict: bool = False):
        """
        Initialize data validator.

        Args:
            schema: Pydantic model for validation
            strict: Whether to use strict validation
        """
        self.schema = schema
        self.strict = strict
        self._validation_errors: List[Dict[str, Any]] = []

    def validate(
        self, data: Union[Dict[str, Any], List[Dict[str, Any]]], raise_on_error: bool = True
    ) -> bool:
        """
        Validate data against schema.

        Args:
            data: Data to validate
            raise_on_error: Whether to raise exception on validation error

        Returns:
            True if valid, False otherwise

        Raises:
            ValidationError: If raise_on_error is True and validation fails
        """
        self._validation_errors = []

        if not self.schema:
            logger.warning("No schema defined, skipping validation")
            return True

        try:
            if isinstance(data, list):
                for idx, item in enumerate(data):
                    try:
                        self.schema(**item)
                    except ValidationError as e:
                        self._validation_errors.append({"index": idx, "errors": e.errors()})
            else:
                self.schema(**data)

            if self._validation_errors:
                if raise_on_error:
                    raise ValidationError(
                        f"Validation failed with {len(self._validation_errors)} errors",
                        model=self.schema,
                    )
                return False

            return True

        except ValidationError as e:
            logger.error(f"Validation error: {e}")
            if raise_on_error:
                raise
            return False

    def get_errors(self) -> List[Dict[str, Any]]:
        """Get validation errors from last validation."""
        return self._validation_errors

    def check_completeness(self, data: Dict[str, Any], required_fields: Set[str]) -> Dict[str, Any]:
        """
        Check data completeness.

        Args:
            data: Data to check
            required_fields: Set of required field names

        Returns:
            Dictionary with completeness metrics
        """
        present_fields = set(data.keys())
        missing_fields = required_fields - present_fields
        extra_fields = present_fields - required_fields

        completeness = {
            "total_required": len(required_fields),
            "present": len(present_fields & required_fields),
            "missing": list(missing_fields),
            "extra": list(extra_fields),
            "completeness_ratio": len(present_fields & required_fields) / len(required_fields)
            if required_fields
            else 1.0,
        }

        return completeness

    def check_nulls(self, data: Union[Dict[str, Any], List[Dict[str, Any]]]) -> Dict[str, Any]:
        """
        Check for null/missing values.

        Args:
            data: Data to check

        Returns:
            Dictionary with null statistics
        """
        if isinstance(data, dict):
            data = [data]

        total_records = len(data)
        field_nulls: Dict[str, int] = {}

        for record in data:
            for field, value in record.items():
                if value is None or value == "":
                    field_nulls[field] = field_nulls.get(field, 0) + 1

        null_stats = {
            "total_records": total_records,
            "fields_with_nulls": {
                field: {"count": count, "percentage": (count / total_records) * 100}
                for field, count in field_nulls.items()
            },
        }

        return null_stats

    def check_uniqueness(
        self, data: List[Dict[str, Any]], key_fields: List[str]
    ) -> Dict[str, Any]:
        """
        Check uniqueness of records based on key fields.

        Args:
            data: List of records
            key_fields: Fields that should be unique together

        Returns:
            Dictionary with uniqueness statistics
        """
        seen_keys: Set[tuple] = set()
        duplicates: List[Dict[str, Any]] = []

        for idx, record in enumerate(data):
            key = tuple(record.get(field) for field in key_fields)

            if key in seen_keys:
                duplicates.append({"index": idx, "key": dict(zip(key_fields, key))})
            else:
                seen_keys.add(key)

        uniqueness = {
            "total_records": len(data),
            "unique_records": len(seen_keys),
            "duplicate_count": len(duplicates),
            "duplicates": duplicates[:100],  # Limit to first 100 duplicates
        }

        return uniqueness

    def check_data_types(
        self, data: List[Dict[str, Any]], expected_types: Dict[str, type]
    ) -> Dict[str, Any]:
        """
        Check if data types match expectations.

        Args:
            data: List of records
            expected_types: Dictionary mapping field names to expected types

        Returns:
            Dictionary with type checking results
        """
        type_mismatches: Dict[str, List[Dict[str, Any]]] = {}

        for idx, record in enumerate(data):
            for field, expected_type in expected_types.items():
                if field in record and record[field] is not None:
                    actual_type = type(record[field])

                    if not isinstance(record[field], expected_type):
                        if field not in type_mismatches:
                            type_mismatches[field] = []

                        type_mismatches[field].append(
                            {
                                "index": idx,
                                "expected": expected_type.__name__,
                                "actual": actual_type.__name__,
                                "value": str(record[field])[:50],
                            }
                        )

        type_check = {
            "fields_checked": len(expected_types),
            "fields_with_mismatches": len(type_mismatches),
            "mismatches": {
                field: {"count": len(errors), "examples": errors[:5]}
                for field, errors in type_mismatches.items()
            },
        }

        return type_check


class SchemaMapper:
    """Schema mapper for transforming data between different schemas."""

    def __init__(self, mapping: Optional[Dict[str, Union[str, Callable]]] = None):
        """
        Initialize schema mapper.

        Args:
            mapping: Dictionary mapping source fields to target fields or transform functions
        """
        self.mapping = mapping or {}
        self._custom_transforms: Dict[str, Callable] = {}

    def add_field_mapping(self, source_field: str, target_field: Union[str, Callable]):
        """
        Add field mapping.

        Args:
            source_field: Source field name
            target_field: Target field name or transformation function
        """
        self.mapping[source_field] = target_field

    def add_transform(self, field: str, transform_func: Callable[[Any], Any]):
        """
        Add custom transformation function for a field.

        Args:
            field: Field name
            transform_func: Transformation function
        """
        self._custom_transforms[field] = transform_func

    def map(
        self, data: Union[Dict[str, Any], List[Dict[str, Any]]], strict: bool = False
    ) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Map data from source schema to target schema.

        Args:
            data: Source data
            strict: If True, only include mapped fields; if False, include unmapped fields

        Returns:
            Mapped data
        """
        if isinstance(data, list):
            return [self._map_record(record, strict) for record in data]
        else:
            return self._map_record(data, strict)

    def _map_record(self, record: Dict[str, Any], strict: bool) -> Dict[str, Any]:
        """Map a single record."""
        mapped = {}

        # Apply mappings
        for source_field, target in self.mapping.items():
            if source_field in record:
                value = record[source_field]

                # Apply custom transform if exists
                if source_field in self._custom_transforms:
                    try:
                        value = self._custom_transforms[source_field](value)
                    except Exception as e:
                        logger.error(f"Error transforming field {source_field}: {e}")
                        continue

                # Map to target field
                if callable(target):
                    try:
                        result = target(value)
                        if isinstance(result, dict):
                            mapped.update(result)
                        else:
                            mapped[source_field] = result
                    except Exception as e:
                        logger.error(f"Error in mapping function for {source_field}: {e}")
                else:
                    mapped[target] = value

        # Include unmapped fields if not strict
        if not strict:
            for field, value in record.items():
                if field not in self.mapping and field not in mapped:
                    mapped[field] = value

        return mapped

    @staticmethod
    def create_from_example(
        source_example: Dict[str, Any], target_example: Dict[str, Any]
    ) -> "SchemaMapper":
        """
        Create mapper by inferring mappings from example records.

        Args:
            source_example: Example source record
            target_example: Example target record

        Returns:
            SchemaMapper instance
        """
        mapping = {}

        # Try to match fields by name (case-insensitive)
        source_fields_lower = {k.lower(): k for k in source_example.keys()}
        target_fields_lower = {k.lower(): k for k in target_example.keys()}

        for target_lower, target_field in target_fields_lower.items():
            if target_lower in source_fields_lower:
                source_field = source_fields_lower[target_lower]
                mapping[source_field] = target_field

        return SchemaMapper(mapping)


class TypeConverter:
    """Utility for converting data types."""

    @staticmethod
    def to_int(value: Any, default: Optional[int] = None) -> Optional[int]:
        """Convert value to integer."""
        try:
            if value is None or value == "":
                return default
            return int(float(value))
        except (ValueError, TypeError):
            logger.warning(f"Cannot convert {value} to int")
            return default

    @staticmethod
    def to_float(value: Any, default: Optional[float] = None) -> Optional[float]:
        """Convert value to float."""
        try:
            if value is None or value == "":
                return default
            return float(value)
        except (ValueError, TypeError):
            logger.warning(f"Cannot convert {value} to float")
            return default

    @staticmethod
    def to_bool(value: Any, default: Optional[bool] = None) -> Optional[bool]:
        """Convert value to boolean."""
        if value is None or value == "":
            return default

        if isinstance(value, bool):
            return value

        if isinstance(value, str):
            value_lower = value.lower()
            if value_lower in ["true", "yes", "1", "y", "t"]:
                return True
            elif value_lower in ["false", "no", "0", "n", "f"]:
                return False

        if isinstance(value, (int, float)):
            return bool(value)

        logger.warning(f"Cannot convert {value} to bool")
        return default

    @staticmethod
    def to_datetime(
        value: Any, format: Optional[str] = None, default: Optional[datetime] = None
    ) -> Optional[datetime]:
        """Convert value to datetime."""
        if value is None or value == "":
            return default

        if isinstance(value, datetime):
            return value

        try:
            if format:
                return datetime.strptime(str(value), format)
            else:
                # Try common formats
                common_formats = [
                    "%Y-%m-%d %H:%M:%S",
                    "%Y-%m-%d",
                    "%Y/%m/%d",
                    "%d-%m-%Y",
                    "%d/%m/%Y",
                    "%Y-%m-%dT%H:%M:%S",
                    "%Y-%m-%dT%H:%M:%SZ",
                    "%Y-%m-%dT%H:%M:%S.%f",
                ]

                for fmt in common_formats:
                    try:
                        return datetime.strptime(str(value), fmt)
                    except ValueError:
                        continue

                # Try ISO format
                from datetime import datetime as dt
                return dt.fromisoformat(str(value).replace("Z", "+00:00"))

        except (ValueError, TypeError) as e:
            logger.warning(f"Cannot convert {value} to datetime: {e}")
            return default

    @staticmethod
    def to_string(value: Any, default: str = "") -> str:
        """Convert value to string."""
        if value is None:
            return default
        return str(value)

    @staticmethod
    def clean_string(
        value: str, strip: bool = True, lower: bool = False, upper: bool = False
    ) -> str:
        """Clean string value."""
        if not isinstance(value, str):
            value = str(value)

        if strip:
            value = value.strip()

        if lower:
            value = value.lower()

        if upper:
            value = value.upper()

        return value

    @staticmethod
    def parse_list(
        value: Any, separator: str = ",", item_type: Optional[type] = None
    ) -> List[Any]:
        """Parse string or value to list."""
        if isinstance(value, list):
            items = value
        elif isinstance(value, str):
            items = [item.strip() for item in value.split(separator)]
        else:
            items = [value]

        if item_type:
            converter_map = {
                int: TypeConverter.to_int,
                float: TypeConverter.to_float,
                bool: TypeConverter.to_bool,
                str: TypeConverter.to_string,
            }

            converter = converter_map.get(item_type)
            if converter:
                items = [converter(item) for item in items]

        return items


def create_dynamic_model(
    model_name: str, fields: Dict[str, tuple]
) -> Type[BaseModel]:
    """
    Create a dynamic Pydantic model from field definitions.

    Args:
        model_name: Name for the model
        fields: Dictionary mapping field names to (type, default) tuples

    Returns:
        Pydantic model class

    Example:
        >>> UserModel = create_dynamic_model(
        ...     "User",
        ...     {
        ...         "id": (int, ...),
        ...         "name": (str, ...),
        ...         "email": (str, None),
        ...     }
        ... )
    """
    return create_model(model_name, **fields)  # type: ignore

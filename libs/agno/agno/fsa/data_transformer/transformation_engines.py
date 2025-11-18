"""
Data Transformer FSA - Transformation Engines

This module implements various transformation engines for field mapping, type conversion,
value normalization, validation, enrichment, aggregation, and filtering.
"""

import re
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Union

from .exceptions import TypeConversionError, ValidationError
from .types import AggregationConfig, Enricher, ValidationConstraint


class FieldMapper:
    """Engine for field mapping operations: rename, nest, flatten, split, merge."""

    @staticmethod
    def rename_field(data: Dict, old_name: str, new_name: str) -> Dict:
        """
        Rename a field.

        Args:
            data: Input dictionary
            old_name: Current field name
            new_name: New field name

        Returns:
            Dictionary with renamed field
        """
        if old_name in data:
            data[new_name] = data.pop(old_name)
        return data

    @staticmethod
    def rename_fields(data: Dict, field_map: Dict[str, str]) -> Dict:
        """
        Rename multiple fields.

        Args:
            data: Input dictionary
            field_map: Mapping of old names to new names

        Returns:
            Dictionary with renamed fields
        """
        result = data.copy()
        for old_name, new_name in field_map.items():
            if old_name in result:
                result[new_name] = result.pop(old_name)
        return result

    @staticmethod
    def nest_fields(data: Dict, fields: List[str], nested_name: str) -> Dict:
        """
        Nest multiple fields under a single parent field.

        Args:
            data: Input dictionary
            fields: List of field names to nest
            nested_name: Name of parent field

        Returns:
            Dictionary with nested fields
        """
        result = data.copy()
        nested_data = {}

        for field in fields:
            if field in result:
                nested_data[field] = result.pop(field)

        result[nested_name] = nested_data
        return result

    @staticmethod
    def flatten_fields(data: Dict, nested_name: str, separator: str = "_") -> Dict:
        """
        Flatten nested fields to top level.

        Args:
            data: Input dictionary
            nested_name: Name of nested field to flatten
            separator: Separator for flattened field names

        Returns:
            Dictionary with flattened fields
        """
        result = data.copy()

        if nested_name in result and isinstance(result[nested_name], dict):
            nested_data = result.pop(nested_name)
            for key, value in nested_data.items():
                new_key = f"{nested_name}{separator}{key}"
                result[new_key] = value

        return result

    @staticmethod
    def split_field(
        data: Dict, field_name: str, separator: str, new_fields: List[str]
    ) -> Dict:
        """
        Split a field into multiple fields.

        Args:
            data: Input dictionary
            field_name: Field to split
            separator: Separator to use for splitting
            new_fields: Names for new fields

        Returns:
            Dictionary with split fields
        """
        result = data.copy()

        if field_name in result:
            value = str(result[field_name])
            parts = value.split(separator)

            for i, new_field in enumerate(new_fields):
                if i < len(parts):
                    result[new_field] = parts[i]
                else:
                    result[new_field] = None

            result.pop(field_name)

        return result

    @staticmethod
    def merge_fields(
        data: Dict, fields: List[str], merged_name: str, separator: str = " "
    ) -> Dict:
        """
        Merge multiple fields into one.

        Args:
            data: Input dictionary
            fields: Fields to merge
            merged_name: Name of merged field
            separator: Separator for merged values

        Returns:
            Dictionary with merged field
        """
        result = data.copy()
        values = []

        for field in fields:
            if field in result:
                value = result.pop(field)
                if value is not None:
                    values.append(str(value))

        result[merged_name] = separator.join(values)
        return result

    @staticmethod
    def select_fields(data: Dict, fields: List[str]) -> Dict:
        """
        Select only specified fields.

        Args:
            data: Input dictionary
            fields: Fields to keep

        Returns:
            Dictionary with only selected fields
        """
        return {k: v for k, v in data.items() if k in fields}

    @staticmethod
    def exclude_fields(data: Dict, fields: List[str]) -> Dict:
        """
        Exclude specified fields.

        Args:
            data: Input dictionary
            fields: Fields to remove

        Returns:
            Dictionary without excluded fields
        """
        return {k: v for k, v in data.items() if k not in fields}

    @staticmethod
    def copy_field(data: Dict, source_field: str, target_field: str) -> Dict:
        """
        Copy a field to a new field.

        Args:
            data: Input dictionary
            source_field: Field to copy from
            target_field: Field to copy to

        Returns:
            Dictionary with copied field
        """
        result = data.copy()
        if source_field in result:
            result[target_field] = result[source_field]
        return result


class TypeConverter:
    """Engine for type conversion: string/int/float/datetime/boolean conversions."""

    @staticmethod
    def to_string(value: Any) -> str:
        """Convert value to string."""
        if value is None:
            return ""
        return str(value)

    @staticmethod
    def to_int(value: Any, default: Optional[int] = None) -> Optional[int]:
        """
        Convert value to integer.

        Args:
            value: Value to convert
            default: Default value if conversion fails

        Returns:
            Integer value or default

        Raises:
            TypeConversionError: If conversion fails and no default provided
        """
        if value is None:
            return default

        try:
            # Handle string representations
            if isinstance(value, str):
                # Remove common formatting
                value = value.replace(",", "").replace(" ", "").strip()
                if not value:
                    return default

            return int(float(value))
        except (ValueError, TypeError) as e:
            if default is not None:
                return default
            raise TypeConversionError(value, type(value).__name__, "int", str(e))

    @staticmethod
    def to_float(value: Any, default: Optional[float] = None) -> Optional[float]:
        """
        Convert value to float.

        Args:
            value: Value to convert
            default: Default value if conversion fails

        Returns:
            Float value or default

        Raises:
            TypeConversionError: If conversion fails and no default provided
        """
        if value is None:
            return default

        try:
            # Handle string representations
            if isinstance(value, str):
                # Remove common formatting
                value = value.replace(",", "").replace(" ", "").strip()
                if not value:
                    return default

            return float(value)
        except (ValueError, TypeError) as e:
            if default is not None:
                return default
            raise TypeConversionError(value, type(value).__name__, "float", str(e))

    @staticmethod
    def to_bool(value: Any, default: Optional[bool] = None) -> Optional[bool]:
        """
        Convert value to boolean.

        Args:
            value: Value to convert
            default: Default value if conversion fails

        Returns:
            Boolean value or default
        """
        if value is None:
            return default

        if isinstance(value, bool):
            return value

        if isinstance(value, (int, float)):
            return bool(value)

        if isinstance(value, str):
            value_lower = value.lower().strip()
            if value_lower in ("true", "yes", "1", "on", "t", "y"):
                return True
            elif value_lower in ("false", "no", "0", "off", "f", "n"):
                return False

        return default

    @staticmethod
    def to_datetime(
        value: Any,
        format: Optional[str] = None,
        default: Optional[datetime] = None,
    ) -> Optional[datetime]:
        """
        Convert value to datetime.

        Args:
            value: Value to convert
            format: Expected datetime format
            default: Default value if conversion fails

        Returns:
            Datetime value or default

        Raises:
            TypeConversionError: If conversion fails and no default provided
        """
        if value is None:
            return default

        if isinstance(value, datetime):
            return value

        try:
            if format:
                return datetime.strptime(str(value), format)
            else:
                # Try common formats
                formats = [
                    "%Y-%m-%d %H:%M:%S",
                    "%Y-%m-%d",
                    "%Y/%m/%d",
                    "%d/%m/%Y",
                    "%m/%d/%Y",
                    "%Y-%m-%dT%H:%M:%S",
                    "%Y-%m-%dT%H:%M:%SZ",
                    "%Y-%m-%dT%H:%M:%S.%f",
                ]
                for fmt in formats:
                    try:
                        return datetime.strptime(str(value), fmt)
                    except ValueError:
                        continue

                raise ValueError("No matching datetime format found")
        except (ValueError, TypeError) as e:
            if default is not None:
                return default
            raise TypeConversionError(value, type(value).__name__, "datetime", str(e))

    @staticmethod
    def convert_field(
        data: Dict, field: str, target_type: str, **kwargs
    ) -> Dict:
        """
        Convert a field to a target type.

        Args:
            data: Input dictionary
            field: Field name to convert
            target_type: Target type ('string', 'int', 'float', 'bool', 'datetime')
            **kwargs: Additional arguments for conversion

        Returns:
            Dictionary with converted field
        """
        result = data.copy()

        if field not in result:
            return result

        converters = {
            "string": TypeConverter.to_string,
            "int": TypeConverter.to_int,
            "float": TypeConverter.to_float,
            "bool": TypeConverter.to_bool,
            "datetime": TypeConverter.to_datetime,
        }

        converter = converters.get(target_type.lower())
        if converter:
            result[field] = converter(result[field], **kwargs)

        return result


class ValueNormalizer:
    """Engine for value normalization: standardize formats, trim, case conversion."""

    @staticmethod
    def trim(value: Any) -> Any:
        """Trim whitespace from string values."""
        if isinstance(value, str):
            return value.strip()
        return value

    @staticmethod
    def uppercase(value: Any) -> Any:
        """Convert string to uppercase."""
        if isinstance(value, str):
            return value.upper()
        return value

    @staticmethod
    def lowercase(value: Any) -> Any:
        """Convert string to lowercase."""
        if isinstance(value, str):
            return value.lower()
        return value

    @staticmethod
    def titlecase(value: Any) -> Any:
        """Convert string to title case."""
        if isinstance(value, str):
            return value.title()
        return value

    @staticmethod
    def replace(value: Any, pattern: str, replacement: str, regex: bool = False) -> Any:
        """
        Replace pattern in string.

        Args:
            value: Input value
            pattern: Pattern to find
            replacement: Replacement string
            regex: Whether pattern is a regex

        Returns:
            Modified value
        """
        if isinstance(value, str):
            if regex:
                return re.sub(pattern, replacement, value)
            else:
                return value.replace(pattern, replacement)
        return value

    @staticmethod
    def normalize_phone(value: Any, format: str = "international") -> str:
        """
        Normalize phone number.

        Args:
            value: Phone number
            format: Output format ('international', 'national', 'digits')

        Returns:
            Normalized phone number
        """
        if not value:
            return ""

        # Remove all non-digit characters
        digits = re.sub(r"\D", "", str(value))

        if format == "digits":
            return digits
        elif format == "national":
            # Format as (XXX) XXX-XXXX for US numbers
            if len(digits) == 10:
                return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
            elif len(digits) == 11 and digits[0] == "1":
                return f"({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
        elif format == "international":
            # Format as +X-XXX-XXX-XXXX
            if len(digits) == 10:
                return f"+1-{digits[:3]}-{digits[3:6]}-{digits[6:]}"
            elif len(digits) == 11 and digits[0] == "1":
                return f"+{digits[0]}-{digits[1:4]}-{digits[4:7]}-{digits[7:]}"

        return digits

    @staticmethod
    def normalize_date(value: Any, input_format: Optional[str] = None, output_format: str = "%Y-%m-%d") -> str:
        """
        Normalize date format.

        Args:
            value: Date value
            input_format: Input date format
            output_format: Output date format

        Returns:
            Normalized date string
        """
        dt = TypeConverter.to_datetime(value, format=input_format)
        if dt:
            return dt.strftime(output_format)
        return str(value)

    @staticmethod
    def normalize_whitespace(value: Any) -> Any:
        """Normalize whitespace in string (collapse multiple spaces)."""
        if isinstance(value, str):
            return " ".join(value.split())
        return value

    @staticmethod
    def remove_special_chars(value: Any, keep: str = "") -> Any:
        """
        Remove special characters from string.

        Args:
            value: Input value
            keep: Characters to keep

        Returns:
            String with special characters removed
        """
        if isinstance(value, str):
            pattern = f"[^a-zA-Z0-9\\s{re.escape(keep)}]"
            return re.sub(pattern, "", value)
        return value

    @staticmethod
    def normalize_field(data: Dict, field: str, normalizer: str, **kwargs) -> Dict:
        """
        Apply normalization to a field.

        Args:
            data: Input dictionary
            field: Field name
            normalizer: Normalization function name
            **kwargs: Additional arguments

        Returns:
            Dictionary with normalized field
        """
        result = data.copy()

        if field not in result:
            return result

        normalizers = {
            "trim": ValueNormalizer.trim,
            "uppercase": ValueNormalizer.uppercase,
            "lowercase": ValueNormalizer.lowercase,
            "titlecase": ValueNormalizer.titlecase,
            "normalize_whitespace": ValueNormalizer.normalize_whitespace,
        }

        normalizer_func = normalizers.get(normalizer)
        if normalizer_func:
            result[field] = normalizer_func(result[field], **kwargs)

        return result


class DataValidator:
    """Engine for data validation: required fields, regex, range checks."""

    @staticmethod
    def validate_required(data: Dict, required_fields: List[str]) -> List[str]:
        """
        Validate that required fields are present.

        Args:
            data: Input dictionary
            required_fields: List of required field names

        Returns:
            List of missing fields
        """
        missing = []
        for field in required_fields:
            if field not in data or data[field] is None or data[field] == "":
                missing.append(field)
        return missing

    @staticmethod
    def validate_type(data: Dict, field: str, expected_type: type) -> bool:
        """
        Validate field type.

        Args:
            data: Input dictionary
            field: Field name
            expected_type: Expected type

        Returns:
            True if valid, False otherwise
        """
        if field not in data:
            return False
        return isinstance(data[field], expected_type)

    @staticmethod
    def validate_regex(data: Dict, field: str, pattern: str) -> bool:
        """
        Validate field against regex pattern.

        Args:
            data: Input dictionary
            field: Field name
            pattern: Regex pattern

        Returns:
            True if valid, False otherwise
        """
        if field not in data:
            return False

        value = str(data[field])
        return bool(re.match(pattern, value))

    @staticmethod
    def validate_range(
        data: Dict, field: str, min_value: Optional[Any] = None, max_value: Optional[Any] = None
    ) -> bool:
        """
        Validate field is within range.

        Args:
            data: Input dictionary
            field: Field name
            min_value: Minimum value
            max_value: Maximum value

        Returns:
            True if valid, False otherwise
        """
        if field not in data:
            return False

        value = data[field]

        if min_value is not None and value < min_value:
            return False

        if max_value is not None and value > max_value:
            return False

        return True

    @staticmethod
    def validate_length(
        data: Dict, field: str, min_length: Optional[int] = None, max_length: Optional[int] = None
    ) -> bool:
        """
        Validate field length.

        Args:
            data: Input dictionary
            field: Field name
            min_length: Minimum length
            max_length: Maximum length

        Returns:
            True if valid, False otherwise
        """
        if field not in data:
            return False

        value = data[field]
        length = len(value) if hasattr(value, "__len__") else 0

        if min_length is not None and length < min_length:
            return False

        if max_length is not None and length > max_length:
            return False

        return True

    @staticmethod
    def validate_enum(data: Dict, field: str, allowed_values: List[Any]) -> bool:
        """
        Validate field is in allowed values.

        Args:
            data: Input dictionary
            field: Field name
            allowed_values: List of allowed values

        Returns:
            True if valid, False otherwise
        """
        if field not in data:
            return False

        return data[field] in allowed_values

    @staticmethod
    def validate_email(data: Dict, field: str) -> bool:
        """
        Validate email format.

        Args:
            data: Input dictionary
            field: Field name

        Returns:
            True if valid email, False otherwise
        """
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return DataValidator.validate_regex(data, field, email_pattern)

    @staticmethod
    def validate_url(data: Dict, field: str) -> bool:
        """
        Validate URL format.

        Args:
            data: Input dictionary
            field: Field name

        Returns:
            True if valid URL, False otherwise
        """
        url_pattern = r"^https?://[^\s/$.?#].[^\s]*$"
        return DataValidator.validate_regex(data, field, url_pattern)


class DataEnricher:
    """Engine for data enrichment: lookup tables, API calls, computed fields."""

    def __init__(self):
        self.lookup_tables: Dict[str, Dict] = {}
        self.cache: Dict[str, Any] = {}

    def add_lookup_table(self, name: str, table: Dict):
        """
        Add a lookup table.

        Args:
            name: Table name
            table: Dictionary for lookups
        """
        self.lookup_tables[name] = table

    def lookup_enrich(
        self, data: Dict, source_field: str, target_field: str, lookup_table: str, default: Any = None
    ) -> Dict:
        """
        Enrich data using a lookup table.

        Args:
            data: Input dictionary
            source_field: Field to use for lookup
            target_field: Field to store result
            lookup_table: Name of lookup table
            default: Default value if lookup fails

        Returns:
            Enriched dictionary
        """
        result = data.copy()

        if source_field in result and lookup_table in self.lookup_tables:
            lookup_key = result[source_field]
            table = self.lookup_tables[lookup_table]
            result[target_field] = table.get(lookup_key, default)

        return result

    def computed_field(
        self, data: Dict, target_field: str, compute_function: Callable, source_fields: List[str]
    ) -> Dict:
        """
        Add computed field.

        Args:
            data: Input dictionary
            target_field: Field to store result
            compute_function: Function to compute value
            source_fields: Fields to pass to function

        Returns:
            Dictionary with computed field
        """
        result = data.copy()

        # Extract source field values
        values = [result.get(field) for field in source_fields]

        # Compute new value
        try:
            result[target_field] = compute_function(*values)
        except Exception:
            result[target_field] = None

        return result

    def enrich_with_function(
        self, data: Dict, enricher: Enricher
    ) -> Dict:
        """
        Enrich data using an enricher function.

        Args:
            data: Input dictionary
            enricher: Enricher configuration

        Returns:
            Enriched dictionary
        """
        result = data.copy()

        # Check cache if enabled
        cache_key = None
        if enricher.cache_enabled:
            cache_key = f"{enricher.name}:{':'.join([str(data.get(f)) for f in enricher.source_fields])}"
            if cache_key in self.cache:
                for i, target_field in enumerate(enricher.target_fields):
                    result[target_field] = self.cache[cache_key][i]
                return result

        # Extract source values
        source_values = {field: data.get(field) for field in enricher.source_fields}

        # Call enricher function
        try:
            enriched_values = enricher.enricher_function(source_values, **enricher.parameters)

            # Store results
            if isinstance(enriched_values, dict):
                for target_field in enricher.target_fields:
                    if target_field in enriched_values:
                        result[target_field] = enriched_values[target_field]
            elif isinstance(enriched_values, (list, tuple)):
                for i, target_field in enumerate(enricher.target_fields):
                    if i < len(enriched_values):
                        result[target_field] = enriched_values[i]
            else:
                # Single value
                if enricher.target_fields:
                    result[enricher.target_fields[0]] = enriched_values

            # Cache results
            if enricher.cache_enabled and cache_key:
                self.cache[cache_key] = [result.get(f) for f in enricher.target_fields]

        except Exception:
            # Set target fields to None on error
            for target_field in enricher.target_fields:
                result[target_field] = None

        return result


class AggregationEngine:
    """Engine for data aggregation: sum, avg, count, group by."""

    @staticmethod
    def group_by(data: List[Dict], keys: List[str]) -> Dict[tuple, List[Dict]]:
        """
        Group data by keys.

        Args:
            data: List of dictionaries
            keys: Fields to group by

        Returns:
            Dictionary mapping group keys to records
        """
        groups: Dict[tuple, List[Dict]] = {}

        for record in data:
            group_key = tuple(record.get(key) for key in keys)
            if group_key not in groups:
                groups[group_key] = []
            groups[group_key].append(record)

        return groups

    @staticmethod
    def aggregate(
        data: List[Dict], group_by_fields: List[str], aggregations: Dict[str, List[str]]
    ) -> List[Dict]:
        """
        Aggregate data with grouping.

        Args:
            data: List of dictionaries
            group_by_fields: Fields to group by
            aggregations: Dict mapping fields to aggregation functions
                         e.g., {'amount': ['sum', 'avg'], 'count': ['count']}

        Returns:
            List of aggregated records
        """
        groups = AggregationEngine.group_by(data, group_by_fields)
        results = []

        for group_key, records in groups.items():
            result = {}

            # Add group keys
            for i, field in enumerate(group_by_fields):
                result[field] = group_key[i]

            # Compute aggregations
            for field, funcs in aggregations.items():
                for func in funcs:
                    agg_key = f"{field}_{func}"

                    if func == "sum":
                        values = [r.get(field, 0) for r in records if r.get(field) is not None]
                        result[agg_key] = sum(values) if values else 0
                    elif func == "avg":
                        values = [r.get(field, 0) for r in records if r.get(field) is not None]
                        result[agg_key] = sum(values) / len(values) if values else 0
                    elif func == "count":
                        result[agg_key] = len(records)
                    elif func == "min":
                        values = [r.get(field) for r in records if r.get(field) is not None]
                        result[agg_key] = min(values) if values else None
                    elif func == "max":
                        values = [r.get(field) for r in records if r.get(field) is not None]
                        result[agg_key] = max(values) if values else None
                    elif func == "first":
                        result[agg_key] = records[0].get(field) if records else None
                    elif func == "last":
                        result[agg_key] = records[-1].get(field) if records else None

            results.append(result)

        return results


class FilterEngine:
    """Engine for filtering: conditional field inclusion/exclusion."""

    @staticmethod
    def filter_records(data: List[Dict], condition: Callable[[Dict], bool]) -> List[Dict]:
        """
        Filter records based on a condition.

        Args:
            data: List of dictionaries
            condition: Function that returns True for records to keep

        Returns:
            Filtered list of dictionaries
        """
        return [record for record in data if condition(record)]

    @staticmethod
    def filter_by_value(data: List[Dict], field: str, value: Any) -> List[Dict]:
        """
        Filter records where field equals value.

        Args:
            data: List of dictionaries
            field: Field name
            value: Value to match

        Returns:
            Filtered list
        """
        return [record for record in data if record.get(field) == value]

    @staticmethod
    def filter_by_range(
        data: List[Dict], field: str, min_value: Optional[Any] = None, max_value: Optional[Any] = None
    ) -> List[Dict]:
        """
        Filter records where field is within range.

        Args:
            data: List of dictionaries
            field: Field name
            min_value: Minimum value
            max_value: Maximum value

        Returns:
            Filtered list
        """

        def in_range(record):
            value = record.get(field)
            if value is None:
                return False
            if min_value is not None and value < min_value:
                return False
            if max_value is not None and value > max_value:
                return False
            return True

        return [record for record in data if in_range(record)]

    @staticmethod
    def filter_by_regex(data: List[Dict], field: str, pattern: str) -> List[Dict]:
        """
        Filter records where field matches regex.

        Args:
            data: List of dictionaries
            field: Field name
            pattern: Regex pattern

        Returns:
            Filtered list
        """
        compiled_pattern = re.compile(pattern)
        return [
            record
            for record in data
            if record.get(field) and compiled_pattern.match(str(record[field]))
        ]

    @staticmethod
    def filter_nulls(data: List[Dict], fields: Optional[List[str]] = None) -> List[Dict]:
        """
        Filter out records with null values.

        Args:
            data: List of dictionaries
            fields: Specific fields to check (None = check all)

        Returns:
            Filtered list
        """
        if fields is None:
            return [record for record in data if all(v is not None for v in record.values())]
        else:
            return [
                record
                for record in data
                if all(record.get(field) is not None for field in fields)
            ]

    @staticmethod
    def filter_duplicates(data: List[Dict], keys: List[str]) -> List[Dict]:
        """
        Remove duplicate records based on keys.

        Args:
            data: List of dictionaries
            keys: Fields to use for uniqueness check

        Returns:
            List without duplicates
        """
        seen = set()
        result = []

        for record in data:
            key = tuple(record.get(k) for k in keys)
            if key not in seen:
                seen.add(key)
                result.append(record)

        return result

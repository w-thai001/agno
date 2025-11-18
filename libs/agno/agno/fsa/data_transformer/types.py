"""
Data Transformer FSA - Type Definitions

This module defines all data classes and type definitions for the Data Transformer FSA.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, Iterator, List, Optional, Union


class DataFormat(Enum):
    """Supported data formats."""

    JSON = "json"
    XML = "xml"
    CSV = "csv"
    PARQUET = "parquet"
    AVRO = "avro"
    PROTOBUF = "protobuf"
    YAML = "yaml"
    CUSTOM = "custom"


class TransformationType(Enum):
    """Types of transformations."""

    FIELD_MAPPING = "field_mapping"
    TYPE_CONVERSION = "type_conversion"
    VALUE_TRANSFORMATION = "value_transformation"
    AGGREGATION = "aggregation"
    FILTERING = "filtering"
    ENRICHMENT = "enrichment"
    VALIDATION = "validation"
    NORMALIZATION = "normalization"


class ErrorStrategy(Enum):
    """Error handling strategies."""

    RAISE = "raise"  # Raise exception on error
    SKIP = "skip"  # Skip failed records
    RETRY = "retry"  # Retry failed operations
    FALLBACK = "fallback"  # Use fallback value
    LOG = "log"  # Log error and continue


class ValidationConstraint(Enum):
    """Data validation constraints."""

    REQUIRED = "required"
    TYPE = "type"
    RANGE = "range"
    REGEX = "regex"
    LENGTH = "length"
    CUSTOM = "custom"


@dataclass
class Schema:
    """Data schema definition."""

    name: str
    version: str = "1.0.0"
    fields: Dict[str, "FieldDefinition"] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """Convert field dicts to FieldDefinition objects if needed."""
        for field_name, field_def in self.fields.items():
            if isinstance(field_def, dict):
                self.fields[field_name] = FieldDefinition(**field_def)


@dataclass
class FieldDefinition:
    """Field definition in a schema."""

    name: str
    type: str
    required: bool = False
    default: Any = None
    description: str = ""
    constraints: Dict[str, Any] = field(default_factory=dict)
    nullable: bool = True


@dataclass
class TransformationRule:
    """Single transformation rule."""

    name: str
    type: TransformationType
    source_field: Optional[str] = None
    target_field: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    condition: Optional[Callable] = None
    error_strategy: ErrorStrategy = ErrorStrategy.RAISE


@dataclass
class TransformationRules:
    """Collection of transformation rules."""

    rules: List[TransformationRule] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_rule(self, rule: TransformationRule) -> None:
        """Add a transformation rule."""
        self.rules.append(rule)

    def get_rules_by_type(self, rule_type: TransformationType) -> List[TransformationRule]:
        """Get all rules of a specific type."""
        return [rule for rule in self.rules if rule.type == rule_type]


@dataclass
class TransformedData:
    """Result of a data transformation."""

    data: Any
    format: DataFormat
    schema: Optional[Schema] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    transformation_time: float = 0.0
    record_count: int = 0


@dataclass
class ValidationResult:
    """Result of data validation."""

    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    validated_data: Optional[Any] = None
    field_errors: Dict[str, List[str]] = field(default_factory=dict)


@dataclass
class SchemaMapping:
    """Mapping between source and target schemas."""

    source_schema: Schema
    target_schema: Schema
    field_mappings: Dict[str, str] = field(default_factory=dict)  # source -> target
    transformations: List[TransformationRule] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_field_mapping(self, source_field: str, target_field: str) -> None:
        """Add a field mapping."""
        self.field_mappings[source_field] = target_field

    def add_transformation(self, transformation: TransformationRule) -> None:
        """Add a transformation rule."""
        self.transformations.append(transformation)


@dataclass
class Enricher:
    """Data enrichment configuration."""

    name: str
    enricher_function: Callable
    source_fields: List[str] = field(default_factory=list)
    target_fields: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    cache_enabled: bool = True
    cache_ttl: int = 3600  # seconds


@dataclass
class Transformation:
    """Single transformation step in a pipeline."""

    name: str
    function: Callable
    parameters: Dict[str, Any] = field(default_factory=dict)
    error_strategy: ErrorStrategy = ErrorStrategy.RAISE
    retry_count: int = 0
    retry_delay: float = 1.0
    condition: Optional[Callable] = None


@dataclass
class Pipeline:
    """Transformation pipeline."""

    name: str
    transformations: List[Transformation] = field(default_factory=list)
    error_strategy: ErrorStrategy = ErrorStrategy.RAISE
    parallel_execution: bool = False
    max_workers: int = 4
    metadata: Dict[str, Any] = field(default_factory=dict)
    version: str = "1.0.0"

    def add_transformation(self, transformation: Transformation) -> None:
        """Add a transformation to the pipeline."""
        self.transformations.append(transformation)

    def remove_transformation(self, name: str) -> bool:
        """Remove a transformation by name."""
        original_length = len(self.transformations)
        self.transformations = [t for t in self.transformations if t.name != name]
        return len(self.transformations) < original_length


@dataclass
class PipelineExecutionResult:
    """Result of pipeline execution."""

    pipeline_name: str
    success: bool
    data: Any
    execution_time: float
    step_results: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class FormatConversionConfig:
    """Configuration for format conversion."""

    source_format: DataFormat
    target_format: DataFormat
    preserve_metadata: bool = True
    strict_mode: bool = False
    custom_options: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AggregationConfig:
    """Configuration for data aggregation."""

    group_by: List[str] = field(default_factory=list)
    aggregations: Dict[str, List[str]] = field(default_factory=dict)  # field -> [func1, func2]
    filters: List[Callable] = field(default_factory=list)


@dataclass
class CSVConfig:
    """CSV format configuration."""

    delimiter: str = ","
    quote_char: str = '"'
    escape_char: str = "\\"
    has_header: bool = True
    encoding: str = "utf-8"
    skip_rows: int = 0
    null_values: List[str] = field(default_factory=lambda: ["", "NULL", "null", "None"])


@dataclass
class XMLConfig:
    """XML format configuration."""

    root_element: str = "root"
    row_element: str = "row"
    namespaces: Dict[str, str] = field(default_factory=dict)
    encoding: str = "utf-8"
    pretty_print: bool = True


@dataclass
class ParquetConfig:
    """Parquet format configuration."""

    compression: str = "snappy"
    row_group_size: int = 100000
    version: str = "2.6"
    use_dictionary: bool = True


@dataclass
class AvroConfig:
    """Avro format configuration."""

    codec: str = "deflate"
    sync_interval: int = 16000
    metadata: Dict[str, str] = field(default_factory=dict)


# Type aliases for better readability
DataType = Union[Dict, List, str, int, float, bool, bytes, None]
TransformerFunction = Callable[[Any], Any]
ValidatorFunction = Callable[[Any], bool]
EnricherFunction = Callable[[Any], Any]

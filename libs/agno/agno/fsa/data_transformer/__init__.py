"""
Data Transformer FSA

Universal data transformation engine for converting, validating, enriching,
and normalizing data between formats, schemas, and protocols.
"""

from .core import DataTransformerFSA
from .exceptions import (
    DataTransformerError,
    EnrichmentFailedError,
    InvalidFormatError,
    PipelineExecutionError,
    SchemaCompatibilityError,
    SchemaValidationError,
    TransformationFailedError,
    TypeConversionError,
    UnsupportedFormatError,
    ValidationError,
)
from .format_handlers import (
    AvroTransformer,
    CSVTransformer,
    FormatHandlerRegistry,
    JSONTransformer,
    ParquetTransformer,
    XMLTransformer,
    YAMLTransformer,
)
from .pipeline import (
    BatchPipelineExecutor,
    ConditionalBranching,
    PipelineBuilder,
    PipelineComposer,
    PipelineOptimizer,
    PipelineValidator,
    StreamPipelineExecutor,
    TransformationPipeline,
)
from .schema import (
    CompatibilityChecker,
    SchemaInferrer,
    SchemaMigrator,
    SchemaMapper,
    SchemaRegistry,
    SchemaValidator,
)
from .transformation_engines import (
    AggregationEngine,
    DataEnricher,
    DataValidator,
    FieldMapper,
    FilterEngine,
    TypeConverter,
    ValueNormalizer,
)
from .types import (
    AggregationConfig,
    AvroConfig,
    CSVConfig,
    DataFormat,
    Enricher,
    ErrorStrategy,
    FieldDefinition,
    FormatConversionConfig,
    ParquetConfig,
    Pipeline,
    PipelineExecutionResult,
    Schema,
    SchemaMapping,
    Transformation,
    TransformationRule,
    TransformationRules,
    TransformationType,
    TransformedData,
    ValidationConstraint,
    ValidationResult,
    XMLConfig,
)

__version__ = "1.0.0"

__all__ = [
    # Core
    "DataTransformerFSA",
    # Exceptions
    "DataTransformerError",
    "EnrichmentFailedError",
    "InvalidFormatError",
    "PipelineExecutionError",
    "SchemaCompatibilityError",
    "SchemaValidationError",
    "TransformationFailedError",
    "TypeConversionError",
    "UnsupportedFormatError",
    "ValidationError",
    # Format Handlers
    "AvroTransformer",
    "CSVTransformer",
    "FormatHandlerRegistry",
    "JSONTransformer",
    "ParquetTransformer",
    "XMLTransformer",
    "YAMLTransformer",
    # Pipeline
    "BatchPipelineExecutor",
    "ConditionalBranching",
    "PipelineBuilder",
    "PipelineComposer",
    "PipelineOptimizer",
    "PipelineValidator",
    "StreamPipelineExecutor",
    "TransformationPipeline",
    # Schema
    "CompatibilityChecker",
    "SchemaInferrer",
    "SchemaMigrator",
    "SchemaMapper",
    "SchemaRegistry",
    "SchemaValidator",
    # Transformation Engines
    "AggregationEngine",
    "DataEnricher",
    "DataValidator",
    "FieldMapper",
    "FilterEngine",
    "TypeConverter",
    "ValueNormalizer",
    # Types
    "AggregationConfig",
    "AvroConfig",
    "CSVConfig",
    "DataFormat",
    "Enricher",
    "ErrorStrategy",
    "FieldDefinition",
    "FormatConversionConfig",
    "ParquetConfig",
    "Pipeline",
    "PipelineExecutionResult",
    "Schema",
    "SchemaMapping",
    "Transformation",
    "TransformationRule",
    "TransformationRules",
    "TransformationType",
    "TransformedData",
    "ValidationConstraint",
    "ValidationResult",
    "XMLConfig",
]

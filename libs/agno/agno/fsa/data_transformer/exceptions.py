"""
Data Transformer FSA - Custom Exceptions

This module defines custom exceptions for the Data Transformer FSA.
"""


class DataTransformerError(Exception):
    """Base exception for all data transformer errors."""

    pass


class InvalidFormatError(DataTransformerError):
    """Raised when an invalid or unsupported format is encountered."""

    def __init__(self, format_name: str, message: str = ""):
        self.format_name = format_name
        self.message = message or f"Invalid format: {format_name}"
        super().__init__(self.message)


class SchemaValidationError(DataTransformerError):
    """Raised when data fails schema validation."""

    def __init__(self, errors: list, message: str = ""):
        self.errors = errors
        self.message = message or f"Schema validation failed with {len(errors)} error(s)"
        super().__init__(self.message)


class TransformationFailedError(DataTransformerError):
    """Raised when a transformation operation fails."""

    def __init__(self, transformation: str, reason: str):
        self.transformation = transformation
        self.reason = reason
        self.message = f"Transformation '{transformation}' failed: {reason}"
        super().__init__(self.message)


class UnsupportedFormatError(DataTransformerError):
    """Raised when attempting to use an unsupported format."""

    def __init__(self, format_name: str, supported_formats: list):
        self.format_name = format_name
        self.supported_formats = supported_formats
        self.message = (
            f"Format '{format_name}' is not supported. "
            f"Supported formats: {', '.join(supported_formats)}"
        )
        super().__init__(self.message)


class EnrichmentFailedError(DataTransformerError):
    """Raised when data enrichment fails."""

    def __init__(self, enricher: str, reason: str):
        self.enricher = enricher
        self.reason = reason
        self.message = f"Enrichment with '{enricher}' failed: {reason}"
        super().__init__(self.message)


class PipelineExecutionError(DataTransformerError):
    """Raised when pipeline execution fails."""

    def __init__(self, pipeline_name: str, step: str, reason: str):
        self.pipeline_name = pipeline_name
        self.step = step
        self.reason = reason
        self.message = f"Pipeline '{pipeline_name}' failed at step '{step}': {reason}"
        super().__init__(self.message)


class SchemaCompatibilityError(DataTransformerError):
    """Raised when schemas are incompatible."""

    def __init__(self, source_schema: str, target_schema: str, reason: str):
        self.source_schema = source_schema
        self.target_schema = target_schema
        self.reason = reason
        self.message = f"Schemas incompatible: {source_schema} -> {target_schema}: {reason}"
        super().__init__(self.message)


class TypeConversionError(DataTransformerError):
    """Raised when type conversion fails."""

    def __init__(self, value: any, from_type: str, to_type: str, reason: str = ""):
        self.value = value
        self.from_type = from_type
        self.to_type = to_type
        self.message = f"Cannot convert '{value}' from {from_type} to {to_type}"
        if reason:
            self.message += f": {reason}"
        super().__init__(self.message)


class ValidationError(DataTransformerError):
    """Raised when data validation fails."""

    def __init__(self, field: str, value: any, constraint: str):
        self.field = field
        self.value = value
        self.constraint = constraint
        self.message = f"Field '{field}' with value '{value}' failed validation: {constraint}"
        super().__init__(self.message)

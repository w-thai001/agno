"""
Data Transformer FSA - Production-ready ETL pipeline with state machine pattern.

This module provides a comprehensive Finite State Automaton for data transformation
operations including ETL pipelines, format conversion, schema validation, and more.

Features:
- ETL pipeline support (Extract, Transform, Load)
- Multiple data format conversion (JSON, XML, CSV, Parquet, Avro)
- Schema validation and transformation
- Data type conversion and normalization
- Field mapping and renaming
- Data aggregation and grouping
- Filtering and projection operations
- Data enrichment with external sources
- Batch and streaming transformation support
- Pipeline composition with chainable transforms
- Error handling and data quality validation
- Performance optimization with parallel processing
- Integration with Database Connector FSA
- Caching for expensive transformations
- Transform versioning and rollback
- Comprehensive metrics and monitoring
"""

from __future__ import annotations

import asyncio
import csv
import hashlib
import io
import json
import logging
import re
import time
import xml.etree.ElementTree as ET
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from copy import deepcopy
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from functools import lru_cache, wraps
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
    Union,
    Iterator,
    AsyncIterator,
    Generic,
    TypeVar,
)
from uuid import uuid4

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

try:
    import pyarrow as pa
    import pyarrow.parquet as pq
    HAS_PYARROW = True
except ImportError:
    HAS_PYARROW = False

try:
    import fastavro
    HAS_AVRO = True
except ImportError:
    HAS_AVRO = False

try:
    from jsonschema import validate, ValidationError as JsonSchemaValidationError
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False

from pydantic import BaseModel, Field, validator

# Type variables for generic operations
T = TypeVar('T')
S = TypeVar('S')

# Configure logging
logger = logging.getLogger(__name__)


# ============================================================================
# Enums and Constants
# ============================================================================

class TransformationState(str, Enum):
    """States in the data transformation lifecycle."""
    IDLE = "idle"
    VALIDATING = "validating"
    EXTRACTING = "extracting"
    TRANSFORMING = "transforming"
    LOADING = "loading"
    ENRICHING = "enriching"
    AGGREGATING = "aggregating"
    FILTERING = "filtering"
    CACHING = "caching"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class TransformationType(str, Enum):
    """Types of transformations supported."""
    MAP = "map"
    FILTER = "filter"
    AGGREGATE = "aggregate"
    JOIN = "join"
    PIVOT = "pivot"
    UNPIVOT = "unpivot"
    NORMALIZE = "normalize"
    DENORMALIZE = "denormalize"
    ENRICH = "enrich"
    VALIDATE = "validate"
    CONVERT = "convert"
    CUSTOM = "custom"


class DataFormat(str, Enum):
    """Supported data formats."""
    JSON = "json"
    XML = "xml"
    CSV = "csv"
    PARQUET = "parquet"
    AVRO = "avro"
    DICT = "dict"
    DATAFRAME = "dataframe"


class AggregationFunction(str, Enum):
    """Aggregation functions for data grouping."""
    SUM = "sum"
    AVG = "avg"
    COUNT = "count"
    MIN = "min"
    MAX = "max"
    MEDIAN = "median"
    STD = "std"
    VAR = "var"
    FIRST = "first"
    LAST = "last"
    CONCAT = "concat"


class DataQualityRule(str, Enum):
    """Data quality validation rules."""
    NOT_NULL = "not_null"
    UNIQUE = "unique"
    RANGE = "range"
    REGEX = "regex"
    TYPE_CHECK = "type_check"
    CUSTOM = "custom"


# ============================================================================
# Exceptions
# ============================================================================

class TransformationError(Exception):
    """Base exception for transformation errors."""
    pass


class SchemaValidationError(TransformationError):
    """Exception raised when schema validation fails."""
    pass


class FormatConversionError(TransformationError):
    """Exception raised when format conversion fails."""
    pass


class DataQualityError(TransformationError):
    """Exception raised when data quality validation fails."""
    pass


class StateTransitionError(TransformationError):
    """Exception raised when invalid state transition is attempted."""
    pass


class EnrichmentError(TransformationError):
    """Exception raised when data enrichment fails."""
    pass


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class TransformMetrics:
    """Metrics for transformation operations."""
    transform_id: str
    operation: str
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    duration_seconds: Optional[float] = None
    records_processed: int = 0
    records_failed: int = 0
    records_filtered: int = 0
    bytes_processed: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def complete(self) -> None:
        """Mark the transformation as complete and calculate duration."""
        self.end_time = time.time()
        self.duration_seconds = self.end_time - self.start_time

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return asdict(self)


@dataclass
class SchemaField:
    """Schema field definition."""
    name: str
    type: str
    required: bool = False
    nullable: bool = True
    default: Any = None
    description: Optional[str] = None
    constraints: Dict[str, Any] = field(default_factory=dict)
    transformations: List[str] = field(default_factory=list)


@dataclass
class DataSchema:
    """Schema definition for data validation."""
    name: str
    version: str
    fields: List[SchemaField]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def validate_record(self, record: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate a single record against the schema.

        Args:
            record: Record to validate

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        for field_def in self.fields:
            field_name = field_def.name
            field_value = record.get(field_name)

            # Check required fields
            if field_def.required and field_value is None:
                errors.append(f"Required field '{field_name}' is missing")
                continue

            # Check nullable constraint
            if not field_def.nullable and field_value is None:
                errors.append(f"Field '{field_name}' cannot be null")
                continue

            # Skip validation if field is None and nullable
            if field_value is None and field_def.nullable:
                continue

            # Type validation
            type_valid, type_error = self._validate_type(field_name, field_value, field_def.type)
            if not type_valid:
                errors.append(type_error)

            # Constraint validation
            for constraint_name, constraint_value in field_def.constraints.items():
                constraint_valid, constraint_error = self._validate_constraint(
                    field_name, field_value, constraint_name, constraint_value
                )
                if not constraint_valid:
                    errors.append(constraint_error)

        return len(errors) == 0, errors

    def _validate_type(self, field_name: str, value: Any, expected_type: str) -> Tuple[bool, str]:
        """Validate field type."""
        type_mapping = {
            'string': str,
            'integer': int,
            'float': (int, float),
            'boolean': bool,
            'array': list,
            'object': dict,
        }

        expected_python_type = type_mapping.get(expected_type)
        if expected_python_type is None:
            return True, ""

        if not isinstance(value, expected_python_type):
            return False, f"Field '{field_name}' expected type '{expected_type}', got '{type(value).__name__}'"

        return True, ""

    def _validate_constraint(
        self, field_name: str, value: Any, constraint_name: str, constraint_value: Any
    ) -> Tuple[bool, str]:
        """Validate field constraint."""
        if constraint_name == "min_length" and isinstance(value, (str, list)):
            if len(value) < constraint_value:
                return False, f"Field '{field_name}' length must be >= {constraint_value}"

        elif constraint_name == "max_length" and isinstance(value, (str, list)):
            if len(value) > constraint_value:
                return False, f"Field '{field_name}' length must be <= {constraint_value}"

        elif constraint_name == "min" and isinstance(value, (int, float)):
            if value < constraint_value:
                return False, f"Field '{field_name}' must be >= {constraint_value}"

        elif constraint_name == "max" and isinstance(value, (int, float)):
            if value > constraint_value:
                return False, f"Field '{field_name}' must be <= {constraint_value}"

        elif constraint_name == "pattern" and isinstance(value, str):
            if not re.match(constraint_value, value):
                return False, f"Field '{field_name}' does not match pattern '{constraint_value}'"

        elif constraint_name == "enum":
            if value not in constraint_value:
                return False, f"Field '{field_name}' must be one of {constraint_value}"

        return True, ""


@dataclass
class FieldMapping:
    """Field mapping configuration for transformations."""
    source_field: str
    target_field: str
    transformation: Optional[Callable[[Any], Any]] = None
    default_value: Any = None
    required: bool = True


@dataclass
class TransformConfig:
    """Configuration for a transformation operation."""
    transform_id: str
    transform_type: TransformationType
    source_format: DataFormat
    target_format: DataFormat
    field_mappings: List[FieldMapping] = field(default_factory=list)
    filters: List[Callable[[Dict[str, Any]], bool]] = field(default_factory=list)
    aggregations: Dict[str, AggregationFunction] = field(default_factory=dict)
    schema: Optional[DataSchema] = None
    enable_cache: bool = True
    batch_size: int = 1000
    parallel: bool = True
    max_workers: int = 4
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TransformVersion:
    """Version information for transformations."""
    version_id: str
    transform_id: str
    config: TransformConfig
    created_at: datetime
    created_by: Optional[str] = None
    checkpoint_data: Optional[Any] = None
    metrics: Optional[TransformMetrics] = None


class TransformPipeline:
    """
    Composable transformation pipeline for chaining multiple transforms.

    Example:
        pipeline = TransformPipeline()
        pipeline.add_transform(json_to_dict_transform)
        pipeline.add_transform(field_mapping_transform)
        pipeline.add_transform(validation_transform)
        result = pipeline.execute(data)
    """

    def __init__(self, name: str, description: Optional[str] = None):
        """
        Initialize transform pipeline.

        Args:
            name: Pipeline name
            description: Pipeline description
        """
        self.name = name
        self.description = description
        self.transforms: List[Callable] = []
        self.metrics_history: List[TransformMetrics] = []

    def add_transform(
        self,
        transform_func: Callable[[Any], Any],
        name: Optional[str] = None
    ) -> TransformPipeline:
        """
        Add a transform function to the pipeline.

        Args:
            transform_func: Transform function to add
            name: Optional name for the transform

        Returns:
            Self for chaining
        """
        self.transforms.append(transform_func)
        return self

    def execute(self, data: Any, collect_metrics: bool = True) -> Any:
        """
        Execute the pipeline on input data.

        Args:
            data: Input data
            collect_metrics: Whether to collect metrics

        Returns:
            Transformed data
        """
        result = data

        for idx, transform_func in enumerate(self.transforms):
            if collect_metrics:
                metrics = TransformMetrics(
                    transform_id=f"{self.name}_step_{idx}",
                    operation=transform_func.__name__
                )

            try:
                result = transform_func(result)

                if collect_metrics:
                    metrics.complete()
                    self.metrics_history.append(metrics)

            except Exception as e:
                if collect_metrics:
                    metrics.errors.append(str(e))
                    metrics.complete()
                    self.metrics_history.append(metrics)
                raise

        return result

    async def execute_async(self, data: Any) -> Any:
        """
        Execute the pipeline asynchronously.

        Args:
            data: Input data

        Returns:
            Transformed data
        """
        result = data

        for transform_func in self.transforms:
            if asyncio.iscoroutinefunction(transform_func):
                result = await transform_func(result)
            else:
                result = transform_func(result)

        return result


# ============================================================================
# Cache Manager
# ============================================================================

class CacheManager:
    """
    Cache manager for expensive transformations.

    Supports TTL-based expiration and size limits.
    """

    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        """
        Initialize cache manager.

        Args:
            max_size: Maximum number of cached items
            default_ttl: Default TTL in seconds
        """
        self.cache: Dict[str, Tuple[Any, float]] = {}
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Optional[Any]:
        """Get item from cache."""
        if key in self.cache:
            value, expiry = self.cache[key]
            if time.time() < expiry:
                self.hits += 1
                return value
            else:
                del self.cache[key]

        self.misses += 1
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set item in cache."""
        if len(self.cache) >= self.max_size:
            # Remove oldest item
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k][1])
            del self.cache[oldest_key]

        ttl = ttl or self.default_ttl
        expiry = time.time() + ttl
        self.cache[key] = (value, expiry)

    def invalidate(self, key: str) -> None:
        """Invalidate cache entry."""
        if key in self.cache:
            del self.cache[key]

    def clear(self) -> None:
        """Clear all cache entries."""
        self.cache.clear()
        self.hits = 0
        self.misses = 0

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.hits + self.misses
        hit_rate = self.hits / total_requests if total_requests > 0 else 0

        return {
            "hits": self.hits,
            "misses": self.misses,
            "total_requests": total_requests,
            "hit_rate": hit_rate,
            "cache_size": len(self.cache),
            "max_size": self.max_size,
        }


# ============================================================================
# Data Transformer FSA
# ============================================================================

class DataTransformerFSA:
    """
    Production-ready Data Transformer Finite State Automaton.

    This FSA implements a comprehensive ETL pipeline with support for:
    - Multiple data format conversions
    - Schema validation and transformation
    - Field mapping and data normalization
    - Aggregation and filtering
    - Data enrichment
    - Batch and streaming processing
    - Pipeline composition
    - Caching and performance optimization
    - Metrics and monitoring
    - Transform versioning and rollback

    Example:
        fsa = DataTransformerFSA()

        # Configure schema
        schema = DataSchema(
            name="user_schema",
            version="1.0",
            fields=[
                SchemaField(name="id", type="integer", required=True),
                SchemaField(name="email", type="string", required=True),
            ]
        )

        # Configure transformation
        config = TransformConfig(
            transform_id="user_transform",
            transform_type=TransformationType.MAP,
            source_format=DataFormat.JSON,
            target_format=DataFormat.CSV,
            schema=schema
        )

        # Execute transformation
        result = fsa.transform(json_data, config)
    """

    def __init__(
        self,
        enable_cache: bool = True,
        cache_size: int = 1000,
        max_workers: int = 4,
        enable_metrics: bool = True,
    ):
        """
        Initialize Data Transformer FSA.

        Args:
            enable_cache: Enable transformation caching
            cache_size: Maximum cache size
            max_workers: Maximum parallel workers
            enable_metrics: Enable metrics collection
        """
        self.state = TransformationState.IDLE
        self.enable_cache = enable_cache
        self.max_workers = max_workers
        self.enable_metrics = enable_metrics

        # Initialize components
        self.cache = CacheManager(max_size=cache_size) if enable_cache else None
        self.metrics_store: Dict[str, TransformMetrics] = {}
        self.version_history: Dict[str, List[TransformVersion]] = defaultdict(list)
        self.enrichment_sources: Dict[str, Callable] = {}

        # State transition rules
        self.valid_transitions = {
            TransformationState.IDLE: {
                TransformationState.VALIDATING,
                TransformationState.EXTRACTING,
            },
            TransformationState.VALIDATING: {
                TransformationState.EXTRACTING,
                TransformationState.TRANSFORMING,
                TransformationState.FAILED,
            },
            TransformationState.EXTRACTING: {
                TransformationState.TRANSFORMING,
                TransformationState.VALIDATING,
                TransformationState.FAILED,
            },
            TransformationState.TRANSFORMING: {
                TransformationState.FILTERING,
                TransformationState.AGGREGATING,
                TransformationState.ENRICHING,
                TransformationState.LOADING,
                TransformationState.FAILED,
            },
            TransformationState.FILTERING: {
                TransformationState.TRANSFORMING,
                TransformationState.AGGREGATING,
                TransformationState.LOADING,
                TransformationState.FAILED,
            },
            TransformationState.AGGREGATING: {
                TransformationState.TRANSFORMING,
                TransformationState.LOADING,
                TransformationState.FAILED,
            },
            TransformationState.ENRICHING: {
                TransformationState.TRANSFORMING,
                TransformationState.LOADING,
                TransformationState.FAILED,
            },
            TransformationState.LOADING: {
                TransformationState.CACHING,
                TransformationState.COMPLETED,
                TransformationState.FAILED,
            },
            TransformationState.CACHING: {
                TransformationState.COMPLETED,
                TransformationState.FAILED,
            },
            TransformationState.COMPLETED: {
                TransformationState.IDLE,
            },
            TransformationState.FAILED: {
                TransformationState.IDLE,
                TransformationState.ROLLED_BACK,
            },
            TransformationState.ROLLED_BACK: {
                TransformationState.IDLE,
            },
        }

        logger.info(f"DataTransformerFSA initialized in state: {self.state}")

    def transition_to(self, new_state: TransformationState) -> None:
        """
        Transition to a new state.

        Args:
            new_state: Target state

        Raises:
            StateTransitionError: If transition is invalid
        """
        if new_state not in self.valid_transitions.get(self.state, set()):
            raise StateTransitionError(
                f"Invalid state transition from {self.state} to {new_state}"
            )

        old_state = self.state
        self.state = new_state
        logger.debug(f"State transition: {old_state} -> {new_state}")

    def transform(
        self,
        data: Any,
        config: TransformConfig,
        validate: bool = True,
    ) -> Any:
        """
        Execute a data transformation.

        Args:
            data: Input data
            config: Transformation configuration
            validate: Whether to validate schema

        Returns:
            Transformed data

        Raises:
            TransformationError: If transformation fails
        """
        metrics = None
        if self.enable_metrics:
            metrics = TransformMetrics(
                transform_id=config.transform_id,
                operation=config.transform_type.value
            )

        try:
            # Check cache
            if config.enable_cache and self.cache:
                cache_key = self._generate_cache_key(data, config)
                cached_result = self.cache.get(cache_key)
                if cached_result is not None:
                    if metrics:
                        metrics.cache_hits += 1
                        metrics.complete()
                        self.metrics_store[config.transform_id] = metrics
                    return cached_result
                if metrics:
                    metrics.cache_misses += 1

            # Validate schema if required
            if validate and config.schema:
                self.transition_to(TransformationState.VALIDATING)
                self._validate_data(data, config.schema, metrics)

            # Extract and normalize data
            self.transition_to(TransformationState.EXTRACTING)
            normalized_data = self._extract_and_normalize(data, config, metrics)

            # Apply transformations
            self.transition_to(TransformationState.TRANSFORMING)
            transformed_data = self._apply_transformations(normalized_data, config, metrics)

            # Apply filters
            if config.filters:
                self.transition_to(TransformationState.FILTERING)
                transformed_data = self._apply_filters(transformed_data, config.filters, metrics)

            # Apply aggregations
            if config.aggregations:
                self.transition_to(TransformationState.AGGREGATING)
                transformed_data = self._apply_aggregations(
                    transformed_data, config.aggregations, metrics
                )

            # Convert to target format
            self.transition_to(TransformationState.LOADING)
            result = self._convert_format(transformed_data, config.target_format, metrics)

            # Cache result
            if config.enable_cache and self.cache:
                self.transition_to(TransformationState.CACHING)
                self.cache.set(cache_key, result)

            # Complete
            self.transition_to(TransformationState.COMPLETED)

            if metrics:
                metrics.complete()
                self.metrics_store[config.transform_id] = metrics

            # Reset to idle
            self.transition_to(TransformationState.IDLE)

            return result

        except Exception as e:
            self.transition_to(TransformationState.FAILED)
            if metrics:
                metrics.errors.append(str(e))
                metrics.complete()
                self.metrics_store[config.transform_id] = metrics

            logger.error(f"Transformation failed: {e}", exc_info=True)
            self.transition_to(TransformationState.IDLE)
            raise TransformationError(f"Transformation failed: {e}") from e

    async def transform_async(
        self,
        data: Any,
        config: TransformConfig,
        validate: bool = True,
    ) -> Any:
        """
        Execute a data transformation asynchronously.

        Args:
            data: Input data
            config: Transformation configuration
            validate: Whether to validate schema

        Returns:
            Transformed data
        """
        # For async operations, we can run in executor
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.transform,
            data,
            config,
            validate
        )

    def transform_batch(
        self,
        data_list: List[Any],
        config: TransformConfig,
        parallel: bool = True,
    ) -> List[Any]:
        """
        Transform multiple data items in batch.

        Args:
            data_list: List of data items to transform
            config: Transformation configuration
            parallel: Whether to process in parallel

        Returns:
            List of transformed data items
        """
        if not parallel or len(data_list) < 2:
            return [self.transform(data, config) for data in data_list]

        results = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [
                executor.submit(self.transform, data, config)
                for data in data_list
            ]

            for future in as_completed(futures):
                try:
                    results.append(future.result())
                except Exception as e:
                    logger.error(f"Batch transform failed: {e}")
                    results.append(None)

        return results

    def transform_stream(
        self,
        data_stream: Iterator[Any],
        config: TransformConfig,
        batch_size: int = 100,
    ) -> Iterator[Any]:
        """
        Transform a stream of data items.

        Args:
            data_stream: Iterator of data items
            config: Transformation configuration
            batch_size: Number of items to process in each batch

        Yields:
            Transformed data items
        """
        batch = []

        for data in data_stream:
            batch.append(data)

            if len(batch) >= batch_size:
                results = self.transform_batch(batch, config, parallel=True)
                for result in results:
                    if result is not None:
                        yield result
                batch = []

        # Process remaining items
        if batch:
            results = self.transform_batch(batch, config, parallel=True)
            for result in results:
                if result is not None:
                    yield result

    async def transform_stream_async(
        self,
        data_stream: AsyncIterator[Any],
        config: TransformConfig,
    ) -> AsyncIterator[Any]:
        """
        Transform an async stream of data items.

        Args:
            data_stream: Async iterator of data items
            config: Transformation configuration

        Yields:
            Transformed data items
        """
        async for data in data_stream:
            try:
                result = await self.transform_async(data, config)
                yield result
            except Exception as e:
                logger.error(f"Stream transform failed: {e}")

    def create_pipeline(
        self,
        name: str,
        transforms: List[TransformConfig],
        description: Optional[str] = None,
    ) -> TransformPipeline:
        """
        Create a transformation pipeline.

        Args:
            name: Pipeline name
            transforms: List of transform configurations
            description: Pipeline description

        Returns:
            Transform pipeline
        """
        pipeline = TransformPipeline(name=name, description=description)

        for config in transforms:
            transform_func = lambda data, cfg=config: self.transform(data, cfg)
            pipeline.add_transform(transform_func, name=config.transform_id)

        return pipeline

    def map_fields(
        self,
        data: Union[Dict[str, Any], List[Dict[str, Any]]],
        field_mappings: List[FieldMapping],
    ) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Map fields from source to target format.

        Args:
            data: Input data (single record or list of records)
            field_mappings: List of field mapping configurations

        Returns:
            Data with mapped fields
        """
        def map_record(record: Dict[str, Any]) -> Dict[str, Any]:
            result = {}
            for mapping in field_mappings:
                source_value = record.get(mapping.source_field)

                if source_value is None:
                    if mapping.required and mapping.default_value is None:
                        raise TransformationError(
                            f"Required field '{mapping.source_field}' is missing"
                        )
                    source_value = mapping.default_value

                # Apply transformation if provided
                if mapping.transformation and source_value is not None:
                    try:
                        target_value = mapping.transformation(source_value)
                    except Exception as e:
                        raise TransformationError(
                            f"Field transformation failed for '{mapping.source_field}': {e}"
                        )
                else:
                    target_value = source_value

                result[mapping.target_field] = target_value

            return result

        if isinstance(data, list):
            return [map_record(record) for record in data]
        else:
            return map_record(data)

    def aggregate(
        self,
        data: List[Dict[str, Any]],
        group_by: List[str],
        aggregations: Dict[str, AggregationFunction],
    ) -> List[Dict[str, Any]]:
        """
        Aggregate data by grouping fields.

        Args:
            data: List of data records
            group_by: Fields to group by
            aggregations: Aggregation functions for each field

        Returns:
            Aggregated data
        """
        if not HAS_PANDAS:
            return self._aggregate_native(data, group_by, aggregations)

        # Use pandas for efficient aggregation
        df = pd.DataFrame(data)

        # Build aggregation dict for pandas
        agg_dict = {}
        for field, func in aggregations.items():
            if func == AggregationFunction.SUM:
                agg_dict[field] = 'sum'
            elif func == AggregationFunction.AVG:
                agg_dict[field] = 'mean'
            elif func == AggregationFunction.COUNT:
                agg_dict[field] = 'count'
            elif func == AggregationFunction.MIN:
                agg_dict[field] = 'min'
            elif func == AggregationFunction.MAX:
                agg_dict[field] = 'max'
            elif func == AggregationFunction.MEDIAN:
                agg_dict[field] = 'median'
            elif func == AggregationFunction.STD:
                agg_dict[field] = 'std'
            elif func == AggregationFunction.FIRST:
                agg_dict[field] = 'first'
            elif func == AggregationFunction.LAST:
                agg_dict[field] = 'last'

        grouped = df.groupby(group_by).agg(agg_dict).reset_index()
        return grouped.to_dict('records')

    def _aggregate_native(
        self,
        data: List[Dict[str, Any]],
        group_by: List[str],
        aggregations: Dict[str, AggregationFunction],
    ) -> List[Dict[str, Any]]:
        """Native Python aggregation without pandas."""
        groups: Dict[Tuple, Dict[str, List]] = defaultdict(lambda: defaultdict(list))

        # Group data
        for record in data:
            key = tuple(record.get(field) for field in group_by)
            for agg_field in aggregations.keys():
                if agg_field in record:
                    groups[key][agg_field].append(record[agg_field])

        # Apply aggregations
        results = []
        for key, group_data in groups.items():
            result = dict(zip(group_by, key))

            for field, func in aggregations.items():
                values = group_data.get(field, [])
                if not values:
                    result[field] = None
                    continue

                if func == AggregationFunction.SUM:
                    result[field] = sum(values)
                elif func == AggregationFunction.AVG:
                    result[field] = sum(values) / len(values)
                elif func == AggregationFunction.COUNT:
                    result[field] = len(values)
                elif func == AggregationFunction.MIN:
                    result[field] = min(values)
                elif func == AggregationFunction.MAX:
                    result[field] = max(values)
                elif func == AggregationFunction.MEDIAN:
                    sorted_values = sorted(values)
                    mid = len(sorted_values) // 2
                    if len(sorted_values) % 2 == 0:
                        result[field] = (sorted_values[mid - 1] + sorted_values[mid]) / 2
                    else:
                        result[field] = sorted_values[mid]
                elif func == AggregationFunction.FIRST:
                    result[field] = values[0]
                elif func == AggregationFunction.LAST:
                    result[field] = values[-1]

            results.append(result)

        return results

    def filter_data(
        self,
        data: List[Dict[str, Any]],
        filters: List[Callable[[Dict[str, Any]], bool]],
    ) -> List[Dict[str, Any]]:
        """
        Filter data based on predicates.

        Args:
            data: List of data records
            filters: List of filter functions

        Returns:
            Filtered data
        """
        result = data
        for filter_func in filters:
            result = [record for record in result if filter_func(record)]
        return result

    def enrich_data(
        self,
        data: Union[Dict[str, Any], List[Dict[str, Any]]],
        enrichment_source: str,
        key_field: str,
        enrich_fields: Optional[List[str]] = None,
    ) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Enrich data with external sources.

        Args:
            data: Input data
            enrichment_source: Name of enrichment source
            key_field: Field to use as lookup key
            enrich_fields: Fields to enrich (None for all)

        Returns:
            Enriched data
        """
        if enrichment_source not in self.enrichment_sources:
            raise EnrichmentError(f"Enrichment source '{enrichment_source}' not registered")

        enrichment_func = self.enrichment_sources[enrichment_source]

        def enrich_record(record: Dict[str, Any]) -> Dict[str, Any]:
            key_value = record.get(key_field)
            if key_value is None:
                return record

            try:
                enrichment_data = enrichment_func(key_value)
                if enrichment_data:
                    if enrich_fields:
                        for field in enrich_fields:
                            if field in enrichment_data:
                                record[field] = enrichment_data[field]
                    else:
                        record.update(enrichment_data)
            except Exception as e:
                logger.warning(f"Enrichment failed for key '{key_value}': {e}")

            return record

        if isinstance(data, list):
            return [enrich_record(record) for record in data]
        else:
            return enrich_record(data)

    def register_enrichment_source(
        self,
        name: str,
        enrichment_func: Callable[[Any], Optional[Dict[str, Any]]],
    ) -> None:
        """
        Register an enrichment data source.

        Args:
            name: Source name
            enrichment_func: Function that takes a key and returns enrichment data
        """
        self.enrichment_sources[name] = enrichment_func
        logger.info(f"Registered enrichment source: {name}")

    def validate_data_quality(
        self,
        data: List[Dict[str, Any]],
        rules: Dict[str, List[Tuple[DataQualityRule, Any]]],
    ) -> Tuple[bool, List[str]]:
        """
        Validate data quality based on rules.

        Args:
            data: Data to validate
            rules: Quality rules for each field

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        for field, field_rules in rules.items():
            for rule, rule_config in field_rules:
                if rule == DataQualityRule.NOT_NULL:
                    null_count = sum(1 for record in data if record.get(field) is None)
                    if null_count > 0:
                        errors.append(f"Field '{field}' has {null_count} null values")

                elif rule == DataQualityRule.UNIQUE:
                    values = [record.get(field) for record in data if record.get(field) is not None]
                    if len(values) != len(set(values)):
                        errors.append(f"Field '{field}' contains duplicate values")

                elif rule == DataQualityRule.RANGE:
                    min_val, max_val = rule_config
                    for record in data:
                        value = record.get(field)
                        if value is not None and not (min_val <= value <= max_val):
                            errors.append(
                                f"Field '{field}' value {value} not in range [{min_val}, {max_val}]"
                            )

                elif rule == DataQualityRule.REGEX:
                    pattern = rule_config
                    for record in data:
                        value = record.get(field)
                        if value is not None and not re.match(pattern, str(value)):
                            errors.append(
                                f"Field '{field}' value '{value}' does not match pattern '{pattern}'"
                            )

                elif rule == DataQualityRule.TYPE_CHECK:
                    expected_type = rule_config
                    for record in data:
                        value = record.get(field)
                        if value is not None and not isinstance(value, expected_type):
                            errors.append(
                                f"Field '{field}' expected type {expected_type.__name__}, "
                                f"got {type(value).__name__}"
                            )

        return len(errors) == 0, errors

    def create_version(
        self,
        transform_id: str,
        config: TransformConfig,
        checkpoint_data: Optional[Any] = None,
        created_by: Optional[str] = None,
    ) -> TransformVersion:
        """
        Create a version checkpoint for a transformation.

        Args:
            transform_id: Transform identifier
            config: Transform configuration
            checkpoint_data: Data to checkpoint
            created_by: User who created the version

        Returns:
            Transform version
        """
        version = TransformVersion(
            version_id=str(uuid4()),
            transform_id=transform_id,
            config=deepcopy(config),
            created_at=datetime.now(),
            created_by=created_by,
            checkpoint_data=checkpoint_data,
            metrics=self.metrics_store.get(transform_id),
        )

        self.version_history[transform_id].append(version)
        logger.info(f"Created version {version.version_id} for transform {transform_id}")

        return version

    def rollback_to_version(
        self,
        transform_id: str,
        version_id: str,
    ) -> Optional[TransformVersion]:
        """
        Rollback to a previous version.

        Args:
            transform_id: Transform identifier
            version_id: Version to rollback to

        Returns:
            Version that was rolled back to, or None if not found
        """
        versions = self.version_history.get(transform_id, [])

        for version in versions:
            if version.version_id == version_id:
                self.transition_to(TransformationState.ROLLED_BACK)
                logger.info(f"Rolled back transform {transform_id} to version {version_id}")
                self.transition_to(TransformationState.IDLE)
                return version

        logger.warning(f"Version {version_id} not found for transform {transform_id}")
        return None

    def get_metrics(self, transform_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get transformation metrics.

        Args:
            transform_id: Specific transform ID (None for all)

        Returns:
            Metrics dictionary
        """
        if transform_id:
            metrics = self.metrics_store.get(transform_id)
            return metrics.to_dict() if metrics else {}

        return {
            tid: metrics.to_dict()
            for tid, metrics in self.metrics_store.items()
        }

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        if self.cache:
            return self.cache.get_stats()
        return {}

    def clear_cache(self) -> None:
        """Clear transformation cache."""
        if self.cache:
            self.cache.clear()
            logger.info("Cache cleared")

    # ========================================================================
    # Format Conversion Methods
    # ========================================================================

    def json_to_dict(self, json_data: Union[str, bytes]) -> Union[Dict, List]:
        """Convert JSON to Python dict."""
        try:
            if isinstance(json_data, bytes):
                json_data = json_data.decode('utf-8')
            return json.loads(json_data)
        except json.JSONDecodeError as e:
            raise FormatConversionError(f"JSON parsing failed: {e}")

    def dict_to_json(self, data: Union[Dict, List], pretty: bool = False) -> str:
        """Convert Python dict to JSON."""
        try:
            if pretty:
                return json.dumps(data, indent=2, ensure_ascii=False)
            return json.dumps(data, ensure_ascii=False)
        except Exception as e:
            raise FormatConversionError(f"JSON serialization failed: {e}")

    def xml_to_dict(self, xml_data: Union[str, bytes]) -> Dict[str, Any]:
        """Convert XML to Python dict."""
        try:
            if isinstance(xml_data, bytes):
                xml_data = xml_data.decode('utf-8')

            root = ET.fromstring(xml_data)
            return self._xml_element_to_dict(root)
        except ET.ParseError as e:
            raise FormatConversionError(f"XML parsing failed: {e}")

    def dict_to_xml(self, data: Dict[str, Any], root_tag: str = "root") -> str:
        """Convert Python dict to XML."""
        try:
            root = ET.Element(root_tag)
            self._dict_to_xml_element(data, root)
            return ET.tostring(root, encoding='unicode')
        except Exception as e:
            raise FormatConversionError(f"XML serialization failed: {e}")

    def csv_to_dict(self, csv_data: Union[str, bytes], delimiter: str = ',') -> List[Dict[str, Any]]:
        """Convert CSV to list of dicts."""
        try:
            if isinstance(csv_data, bytes):
                csv_data = csv_data.decode('utf-8')

            reader = csv.DictReader(io.StringIO(csv_data), delimiter=delimiter)
            return list(reader)
        except Exception as e:
            raise FormatConversionError(f"CSV parsing failed: {e}")

    def dict_to_csv(
        self,
        data: List[Dict[str, Any]],
        delimiter: str = ',',
        include_header: bool = True,
    ) -> str:
        """Convert list of dicts to CSV."""
        try:
            if not data:
                return ""

            output = io.StringIO()
            fieldnames = list(data[0].keys())
            writer = csv.DictWriter(output, fieldnames=fieldnames, delimiter=delimiter)

            if include_header:
                writer.writeheader()
            writer.writerows(data)

            return output.getvalue()
        except Exception as e:
            raise FormatConversionError(f"CSV serialization failed: {e}")

    def parquet_to_dict(self, parquet_data: bytes) -> List[Dict[str, Any]]:
        """Convert Parquet to list of dicts."""
        if not HAS_PYARROW:
            raise FormatConversionError("PyArrow not installed. Install with: pip install pyarrow")

        try:
            table = pq.read_table(io.BytesIO(parquet_data))
            return table.to_pylist()
        except Exception as e:
            raise FormatConversionError(f"Parquet parsing failed: {e}")

    def dict_to_parquet(self, data: List[Dict[str, Any]]) -> bytes:
        """Convert list of dicts to Parquet."""
        if not HAS_PYARROW:
            raise FormatConversionError("PyArrow not installed. Install with: pip install pyarrow")

        try:
            table = pa.Table.from_pylist(data)
            output = io.BytesIO()
            pq.write_table(table, output)
            return output.getvalue()
        except Exception as e:
            raise FormatConversionError(f"Parquet serialization failed: {e}")

    def avro_to_dict(self, avro_data: bytes, schema: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert Avro to list of dicts."""
        if not HAS_AVRO:
            raise FormatConversionError("fastavro not installed. Install with: pip install fastavro")

        try:
            bytes_reader = io.BytesIO(avro_data)
            reader = fastavro.reader(bytes_reader, reader_schema=schema)
            return list(reader)
        except Exception as e:
            raise FormatConversionError(f"Avro parsing failed: {e}")

    def dict_to_avro(self, data: List[Dict[str, Any]], schema: Dict[str, Any]) -> bytes:
        """Convert list of dicts to Avro."""
        if not HAS_AVRO:
            raise FormatConversionError("fastavro not installed. Install with: pip install fastavro")

        try:
            output = io.BytesIO()
            fastavro.writer(output, schema, data)
            return output.getvalue()
        except Exception as e:
            raise FormatConversionError(f"Avro serialization failed: {e}")

    # ========================================================================
    # Internal Helper Methods
    # ========================================================================

    def _generate_cache_key(self, data: Any, config: TransformConfig) -> str:
        """Generate cache key for data and config."""
        data_str = json.dumps(data, sort_keys=True, default=str)
        config_str = f"{config.transform_id}:{config.transform_type}:{config.source_format}:{config.target_format}"
        combined = f"{data_str}:{config_str}"
        return hashlib.sha256(combined.encode()).hexdigest()

    def _validate_data(
        self,
        data: Any,
        schema: DataSchema,
        metrics: Optional[TransformMetrics] = None,
    ) -> None:
        """Validate data against schema."""
        records = data if isinstance(data, list) else [data]

        for idx, record in enumerate(records):
            is_valid, errors = schema.validate_record(record)
            if not is_valid:
                if metrics:
                    metrics.records_failed += 1
                    metrics.errors.extend(errors)
                raise SchemaValidationError(
                    f"Record {idx} validation failed: {', '.join(errors)}"
                )
            if metrics:
                metrics.records_processed += 1

    def _extract_and_normalize(
        self,
        data: Any,
        config: TransformConfig,
        metrics: Optional[TransformMetrics] = None,
    ) -> Any:
        """Extract and normalize data from source format."""
        if config.source_format == DataFormat.JSON:
            if isinstance(data, str) or isinstance(data, bytes):
                return self.json_to_dict(data)
            return data

        elif config.source_format == DataFormat.XML:
            return self.xml_to_dict(data)

        elif config.source_format == DataFormat.CSV:
            return self.csv_to_dict(data)

        elif config.source_format == DataFormat.PARQUET:
            return self.parquet_to_dict(data)

        elif config.source_format == DataFormat.DICT:
            return data

        else:
            return data

    def _apply_transformations(
        self,
        data: Any,
        config: TransformConfig,
        metrics: Optional[TransformMetrics] = None,
    ) -> Any:
        """Apply configured transformations."""
        if config.field_mappings:
            data = self.map_fields(data, config.field_mappings)

        if metrics:
            records = data if isinstance(data, list) else [data]
            metrics.records_processed += len(records)

        return data

    def _apply_filters(
        self,
        data: Any,
        filters: List[Callable],
        metrics: Optional[TransformMetrics] = None,
    ) -> Any:
        """Apply filter functions."""
        if not isinstance(data, list):
            data = [data]

        original_count = len(data)
        filtered_data = self.filter_data(data, filters)

        if metrics:
            metrics.records_filtered = original_count - len(filtered_data)

        return filtered_data

    def _apply_aggregations(
        self,
        data: Any,
        aggregations: Dict[str, AggregationFunction],
        metrics: Optional[TransformMetrics] = None,
    ) -> Any:
        """Apply aggregation functions."""
        # Aggregation requires a list of records
        if not isinstance(data, list):
            return data

        # For now, aggregate without grouping (return single record)
        result = {}
        for field, func in aggregations.items():
            values = [record.get(field) for record in data if field in record]

            if func == AggregationFunction.SUM:
                result[field] = sum(values)
            elif func == AggregationFunction.AVG:
                result[field] = sum(values) / len(values) if values else 0
            elif func == AggregationFunction.COUNT:
                result[field] = len(values)
            elif func == AggregationFunction.MIN:
                result[field] = min(values) if values else None
            elif func == AggregationFunction.MAX:
                result[field] = max(values) if values else None

        return result

    def _convert_format(
        self,
        data: Any,
        target_format: DataFormat,
        metrics: Optional[TransformMetrics] = None,
    ) -> Any:
        """Convert data to target format."""
        if target_format == DataFormat.JSON:
            return self.dict_to_json(data)

        elif target_format == DataFormat.XML:
            if isinstance(data, list):
                return self.dict_to_xml({"items": data}, root_tag="root")
            return self.dict_to_xml(data)

        elif target_format == DataFormat.CSV:
            if not isinstance(data, list):
                data = [data]
            return self.dict_to_csv(data)

        elif target_format == DataFormat.PARQUET:
            if not isinstance(data, list):
                data = [data]
            return self.dict_to_parquet(data)

        elif target_format == DataFormat.DICT:
            return data

        else:
            return data

    def _xml_element_to_dict(self, element: ET.Element) -> Dict[str, Any]:
        """Convert XML element to dict recursively."""
        result: Dict[str, Any] = {}

        # Add attributes
        if element.attrib:
            result.update({f"@{k}": v for k, v in element.attrib.items()})

        # Process children
        children = list(element)
        if children:
            child_dict: Dict[str, Any] = defaultdict(list)
            for child in children:
                child_data = self._xml_element_to_dict(child)
                child_dict[child.tag].append(child_data)

            for tag, values in child_dict.items():
                result[tag] = values[0] if len(values) == 1 else values

        # Add text content
        if element.text and element.text.strip():
            if result:
                result["#text"] = element.text.strip()
            else:
                return element.text.strip()

        return result

    def _dict_to_xml_element(self, data: Dict[str, Any], parent: ET.Element) -> None:
        """Convert dict to XML element recursively."""
        for key, value in data.items():
            if key.startswith('@'):
                # Attribute
                parent.set(key[1:], str(value))
            elif key == '#text':
                # Text content
                parent.text = str(value)
            elif isinstance(value, dict):
                # Nested element
                child = ET.SubElement(parent, key)
                self._dict_to_xml_element(value, child)
            elif isinstance(value, list):
                # Multiple elements with same tag
                for item in value:
                    child = ET.SubElement(parent, key)
                    if isinstance(item, dict):
                        self._dict_to_xml_element(item, child)
                    else:
                        child.text = str(item)
            else:
                # Simple element
                child = ET.SubElement(parent, key)
                child.text = str(value)


# ============================================================================
# Utility Functions
# ============================================================================

def create_field_mapping(
    source: str,
    target: str,
    transform: Optional[Callable] = None,
    default: Any = None,
    required: bool = True,
) -> FieldMapping:
    """
    Utility function to create field mapping.

    Args:
        source: Source field name
        target: Target field name
        transform: Optional transformation function
        default: Default value if field is missing
        required: Whether field is required

    Returns:
        FieldMapping instance
    """
    return FieldMapping(
        source_field=source,
        target_field=target,
        transformation=transform,
        default_value=default,
        required=required,
    )


def create_simple_schema(
    name: str,
    fields: Dict[str, str],
    required_fields: Optional[List[str]] = None,
) -> DataSchema:
    """
    Utility function to create simple schema.

    Args:
        name: Schema name
        fields: Dict of field_name: field_type
        required_fields: List of required field names

    Returns:
        DataSchema instance
    """
    required_fields = required_fields or []
    schema_fields = [
        SchemaField(
            name=field_name,
            type=field_type,
            required=field_name in required_fields,
        )
        for field_name, field_type in fields.items()
    ]

    return DataSchema(
        name=name,
        version="1.0",
        fields=schema_fields,
    )

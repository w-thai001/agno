"""
Data Transformer FSA - Core Module

This module implements the main DataTransformerFSA class that provides a unified interface
for data transformation operations.
"""

import time
from typing import Any, Callable, Dict, Iterator, List, Optional, Union

from .exceptions import (
    EnrichmentFailedError,
    InvalidFormatError,
    SchemaValidationError,
    TransformationFailedError,
    UnsupportedFormatError,
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
    PipelineBuilder,
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
    DataFormat,
    Enricher,
    ErrorStrategy,
    Pipeline,
    Schema,
    SchemaMapping,
    TransformedData,
    Transformation,
    TransformationRule,
    TransformationRules,
    TransformationType,
    ValidationResult,
)


class DataTransformerFSA:
    """
    Universal data transformation engine for converting, validating, enriching,
    and normalizing data between formats, schemas, and protocols.

    This FSA (Finite State Automaton) provides comprehensive data transformation
    capabilities with support for multiple formats, schema management, pipeline
    composition, and error recovery.

    Example:
        >>> transformer = DataTransformerFSA()
        >>> # Transform JSON to CSV
        >>> result = transformer.convert_format(
        ...     data='{"name": "Alice", "age": 30}',
        ...     from_format="json",
        ...     to_format="csv"
        ... )
        >>> # Create and execute a pipeline
        >>> pipeline = transformer.create_pipeline("data_cleanup")
        >>> pipeline_builder = PipelineBuilder("cleanup")
        >>> pipeline_builder.add_transformation(
        ...     "normalize_names",
        ...     lambda data: {...}
        ... )
        >>> result = transformer.execute_pipeline(data, pipeline_builder.build())
    """

    def __init__(self):
        """Initialize the Data Transformer FSA."""
        # Initialize format handlers
        self.format_registry = FormatHandlerRegistry()

        # Initialize schema management
        self.schema_registry = SchemaRegistry()
        self.schema_inferrer = SchemaInferrer()
        self.schema_migrator = SchemaMigrator(self.schema_registry)
        self.schema_validator = SchemaValidator()
        self.schema_mapper = SchemaMapper()
        self.compatibility_checker = CompatibilityChecker()

        # Initialize transformation engines
        self.field_mapper = FieldMapper()
        self.type_converter = TypeConverter()
        self.value_normalizer = ValueNormalizer()
        self.data_validator = DataValidator()
        self.data_enricher = DataEnricher()
        self.aggregation_engine = AggregationEngine()
        self.filter_engine = FilterEngine()

        # Initialize pipeline management
        self.pipelines: Dict[str, Pipeline] = {}
        self.pipeline_optimizer = PipelineOptimizer()
        self.pipeline_validator = PipelineValidator()

        # Custom transformers registry
        self.custom_transformers: Dict[str, Callable] = {}

        # Transformation history
        self.history: List[Dict] = []

    # ========================================================================
    # Format Conversion Methods
    # ========================================================================

    def convert_format(
        self,
        data: Union[str, bytes, Dict, List],
        from_format: str,
        to_format: str,
        **kwargs,
    ) -> Any:
        """
        Convert data from one format to another.

        Args:
            data: Input data
            from_format: Source format (json, xml, csv, parquet, avro, yaml)
            to_format: Target format
            **kwargs: Format-specific options

        Returns:
            Converted data

        Raises:
            UnsupportedFormatError: If format is not supported
            InvalidFormatError: If data is malformed

        Example:
            >>> transformer = DataTransformerFSA()
            >>> csv_data = transformer.convert_format(
            ...     data='{"name": "Alice"}',
            ...     from_format="json",
            ...     to_format="csv"
            ... )
        """
        start_time = time.time()

        try:
            # Get format handlers
            source_format = DataFormat(from_format.lower())
            target_format = DataFormat(to_format.lower())

            source_handler = self.format_registry.get_handler(source_format)
            target_handler = self.format_registry.get_handler(target_format)

            # Read source data
            parsed_data = source_handler.read(data, **kwargs.get("read_options", {}))

            # Write to target format
            result = target_handler.write(parsed_data, **kwargs.get("write_options", {}))

            # Record transformation
            self._record_transformation(
                operation="convert_format",
                source_format=from_format,
                target_format=to_format,
                execution_time=time.time() - start_time,
                success=True,
            )

            return result

        except Exception as e:
            self._record_transformation(
                operation="convert_format",
                source_format=from_format,
                target_format=to_format,
                execution_time=time.time() - start_time,
                success=False,
                error=str(e),
            )
            raise

    # ========================================================================
    # Data Transformation Methods
    # ========================================================================

    def transform(
        self,
        data: Any,
        target_format: str,
        rules: Optional[TransformationRules] = None,
        **kwargs,
    ) -> TransformedData:
        """
        Transform data using specified rules.

        Args:
            data: Input data
            target_format: Target format
            rules: Transformation rules to apply
            **kwargs: Additional options

        Returns:
            TransformedData with results and metadata

        Example:
            >>> rules = TransformationRules()
            >>> rules.add_rule(TransformationRule(
            ...     name="uppercase_name",
            ...     type=TransformationType.VALUE_TRANSFORMATION,
            ...     source_field="name",
            ...     target_field="name",
            ...     parameters={"normalizer": "uppercase"}
            ... ))
            >>> result = transformer.transform(data, "json", rules)
        """
        start_time = time.time()
        errors = []
        warnings = []

        try:
            current_data = data
            target_fmt = DataFormat(target_format.lower())

            # Apply transformation rules if provided
            if rules:
                for rule in rules.rules:
                    try:
                        current_data = self._apply_transformation_rule(current_data, rule)
                    except Exception as e:
                        error_msg = f"Rule '{rule.name}' failed: {str(e)}"
                        errors.append(error_msg)

                        if rule.error_strategy == ErrorStrategy.RAISE:
                            raise TransformationFailedError(rule.name, str(e))
                        elif rule.error_strategy == ErrorStrategy.SKIP:
                            warnings.append(f"Skipped rule: {rule.name}")
                        elif rule.error_strategy == ErrorStrategy.LOG:
                            warnings.append(error_msg)

            # Format output
            handler = self.format_registry.get_handler(target_fmt)
            formatted_data = handler.write(current_data) if hasattr(handler, "write") else current_data

            # Count records
            record_count = len(current_data) if isinstance(current_data, list) else 1

            return TransformedData(
                data=formatted_data,
                format=target_fmt,
                metadata=kwargs.get("metadata", {}),
                errors=errors,
                warnings=warnings,
                transformation_time=time.time() - start_time,
                record_count=record_count,
            )

        except Exception as e:
            self._record_transformation(
                operation="transform",
                execution_time=time.time() - start_time,
                success=False,
                error=str(e),
            )
            raise

    def _apply_transformation_rule(self, data: Any, rule: TransformationRule) -> Any:
        """Apply a single transformation rule to data."""
        if rule.type == TransformationType.FIELD_MAPPING:
            return self._apply_field_mapping(data, rule)
        elif rule.type == TransformationType.TYPE_CONVERSION:
            return self._apply_type_conversion(data, rule)
        elif rule.type == TransformationType.VALUE_TRANSFORMATION:
            return self._apply_value_transformation(data, rule)
        elif rule.type == TransformationType.VALIDATION:
            return self._apply_validation(data, rule)
        elif rule.type == TransformationType.NORMALIZATION:
            return self._apply_normalization(data, rule)
        else:
            return data

    def _apply_field_mapping(self, data: Any, rule: TransformationRule) -> Any:
        """Apply field mapping transformation."""
        if isinstance(data, dict):
            operation = rule.parameters.get("operation", "rename")
            if operation == "rename" and rule.source_field and rule.target_field:
                return self.field_mapper.rename_field(data, rule.source_field, rule.target_field)
        elif isinstance(data, list):
            return [self._apply_field_mapping(item, rule) for item in data]
        return data

    def _apply_type_conversion(self, data: Any, rule: TransformationRule) -> Any:
        """Apply type conversion transformation."""
        if isinstance(data, dict) and rule.source_field:
            target_type = rule.parameters.get("target_type", "string")
            return self.type_converter.convert_field(
                data, rule.source_field, target_type, **rule.parameters
            )
        elif isinstance(data, list):
            return [self._apply_type_conversion(item, rule) for item in data]
        return data

    def _apply_value_transformation(self, data: Any, rule: TransformationRule) -> Any:
        """Apply value transformation."""
        if isinstance(data, dict) and rule.source_field:
            normalizer = rule.parameters.get("normalizer", "trim")
            return self.value_normalizer.normalize_field(
                data, rule.source_field, normalizer, **rule.parameters
            )
        elif isinstance(data, list):
            return [self._apply_value_transformation(item, rule) for item in data]
        return data

    def _apply_validation(self, data: Any, rule: TransformationRule) -> Any:
        """Apply validation."""
        # Validation doesn't modify data, just validates it
        return data

    def _apply_normalization(self, data: Any, rule: TransformationRule) -> Any:
        """Apply normalization."""
        return self._apply_value_transformation(data, rule)

    # ========================================================================
    # Pipeline Methods
    # ========================================================================

    def create_pipeline(
        self,
        name: str,
        transformations: Optional[List[Transformation]] = None,
    ) -> Pipeline:
        """
        Create a transformation pipeline.

        Args:
            name: Pipeline name
            transformations: List of transformations

        Returns:
            Created pipeline

        Example:
            >>> pipeline = transformer.create_pipeline(
            ...     "data_cleanup",
            ...     [Transformation(name="trim", function=lambda x: x.strip())]
            ... )
        """
        pipeline = Pipeline(name=name, transformations=transformations or [])
        self.pipelines[name] = pipeline
        return pipeline

    def execute_pipeline(self, data: Any, pipeline: Union[str, Pipeline]) -> TransformedData:
        """
        Execute a transformation pipeline.

        Args:
            data: Input data
            pipeline: Pipeline name or Pipeline object

        Returns:
            TransformedData with results

        Raises:
            ValueError: If pipeline not found

        Example:
            >>> result = transformer.execute_pipeline(data, "data_cleanup")
        """
        if isinstance(pipeline, str):
            if pipeline not in self.pipelines:
                raise ValueError(f"Pipeline '{pipeline}' not found")
            pipeline = self.pipelines[pipeline]

        executor = TransformationPipeline(pipeline)
        result = executor.execute(data)

        return TransformedData(
            data=result.data,
            format=DataFormat.JSON,  # Default format
            metadata={"pipeline": pipeline.name},
            errors=result.errors,
            warnings=result.warnings,
            transformation_time=result.execution_time,
        )

    def batch_transform(
        self,
        data_list: List[Any],
        pipeline: Union[str, Pipeline],
        parallel: bool = False,
        max_workers: int = 4,
    ) -> List[TransformedData]:
        """
        Execute pipeline on a batch of data.

        Args:
            data_list: List of data items
            pipeline: Pipeline to execute
            parallel: Execute in parallel
            max_workers: Number of parallel workers

        Returns:
            List of TransformedData results

        Example:
            >>> results = transformer.batch_transform(
            ...     [data1, data2, data3],
            ...     "cleanup_pipeline",
            ...     parallel=True
            ... )
        """
        if isinstance(pipeline, str):
            if pipeline not in self.pipelines:
                raise ValueError(f"Pipeline '{pipeline}' not found")
            pipeline = self.pipelines[pipeline]

        executor = BatchPipelineExecutor(pipeline)

        if parallel:
            transformed_data = executor.execute_batch_parallel(data_list, max_workers)
        else:
            transformed_data = executor.execute_batch(data_list)

        return [
            TransformedData(
                data=data,
                format=DataFormat.JSON,
                metadata={"pipeline": pipeline.name, "batch": True},
            )
            for data in transformed_data
        ]

    def stream_transform(
        self,
        data_stream: Iterator,
        pipeline: Union[str, Pipeline],
    ) -> Iterator[Any]:
        """
        Execute pipeline on streaming data.

        Args:
            data_stream: Iterator of data items
            pipeline: Pipeline to execute

        Yields:
            Transformed data items

        Example:
            >>> def data_generator():
            ...     for i in range(100):
            ...         yield {"id": i, "value": i * 2}
            >>>
            >>> for result in transformer.stream_transform(
            ...     data_generator(),
            ...     "cleanup_pipeline"
            ... ):
            ...     print(result)
        """
        if isinstance(pipeline, str):
            if pipeline not in self.pipelines:
                raise ValueError(f"Pipeline '{pipeline}' not found")
            pipeline = self.pipelines[pipeline]

        executor = StreamPipelineExecutor(pipeline)
        return executor.execute_stream(data_stream)

    def optimize_pipeline(self, pipeline: Union[str, Pipeline]) -> Pipeline:
        """
        Optimize a pipeline for better performance.

        Args:
            pipeline: Pipeline to optimize

        Returns:
            Optimized pipeline

        Example:
            >>> optimized = transformer.optimize_pipeline("my_pipeline")
        """
        if isinstance(pipeline, str):
            if pipeline not in self.pipelines:
                raise ValueError(f"Pipeline '{pipeline}' not found")
            pipeline = self.pipelines[pipeline]

        return self.pipeline_optimizer.optimize(pipeline)

    # ========================================================================
    # Schema Management Methods
    # ========================================================================

    def register_schema(self, schema: Schema) -> None:
        """
        Register a schema.

        Args:
            schema: Schema to register

        Example:
            >>> schema = Schema(
            ...     name="user",
            ...     version="1.0.0",
            ...     fields={
            ...         "name": FieldDefinition(name="name", type="string", required=True),
            ...         "age": FieldDefinition(name="age", type="integer", required=False)
            ...     }
            ... )
            >>> transformer.register_schema(schema)
        """
        self.schema_registry.register(schema)

    def infer_schema(self, data: Any, schema_name: str = "inferred") -> Schema:
        """
        Infer schema from data.

        Args:
            data: Data to analyze
            schema_name: Name for inferred schema

        Returns:
            Inferred schema

        Example:
            >>> data = [
            ...     {"name": "Alice", "age": 30},
            ...     {"name": "Bob", "age": 25}
            ... ]
            >>> schema = transformer.infer_schema(data, "users")
        """
        return self.schema_inferrer.infer_from_data(data, schema_name)

    def validate_data(self, data: Any, schema: Union[str, Schema]) -> ValidationResult:
        """
        Validate data against a schema.

        Args:
            data: Data to validate
            schema: Schema name or Schema object

        Returns:
            ValidationResult

        Raises:
            ValueError: If schema not found

        Example:
            >>> result = transformer.validate_data(data, "user")
            >>> if not result.is_valid:
            ...     print("Validation errors:", result.errors)
        """
        if isinstance(schema, str):
            schema_obj = self.schema_registry.get(schema)
            if schema_obj is None:
                raise ValueError(f"Schema '{schema}' not found")
            schema = schema_obj

        return self.schema_validator.validate(data, schema)

    def map_schema(
        self,
        source_schema: Union[str, Schema],
        target_schema: Union[str, Schema],
        auto_map: bool = True,
    ) -> SchemaMapping:
        """
        Create a mapping between two schemas.

        Args:
            source_schema: Source schema name or object
            target_schema: Target schema name or object
            auto_map: Automatically map fields with same names

        Returns:
            SchemaMapping

        Example:
            >>> mapping = transformer.map_schema("user_v1", "user_v2")
            >>> mapping.add_field_mapping("first_name", "firstName")
        """
        if isinstance(source_schema, str):
            source_schema = self.schema_registry.get(source_schema)
            if source_schema is None:
                raise ValueError(f"Source schema not found")

        if isinstance(target_schema, str):
            target_schema = self.schema_registry.get(target_schema)
            if target_schema is None:
                raise ValueError(f"Target schema not found")

        return self.schema_mapper.create_mapping(source_schema, target_schema, auto_map)

    def migrate_schema(
        self,
        data: Dict,
        from_schema: str,
        to_schema: str,
        from_version: Optional[str] = None,
        to_version: Optional[str] = None,
    ) -> Dict:
        """
        Migrate data between schema versions.

        Args:
            data: Data to migrate
            from_schema: Source schema name
            to_schema: Target schema name
            from_version: Source schema version (None = latest)
            to_version: Target schema version (None = latest)

        Returns:
            Migrated data

        Example:
            >>> migrated = transformer.migrate_schema(
            ...     data,
            ...     from_schema="user",
            ...     to_schema="user",
            ...     from_version="1.0.0",
            ...     to_version="2.0.0"
            ... )
        """
        return self.schema_migrator.migrate(data, from_schema, to_schema, from_version, to_version)

    # ========================================================================
    # Data Enrichment Methods
    # ========================================================================

    def enrich_data(
        self,
        data: Union[Dict, List[Dict]],
        enrichers: List[Enricher],
    ) -> Union[Dict, List[Dict]]:
        """
        Enrich data using enricher functions.

        Args:
            data: Data to enrich (dict or list of dicts)
            enrichers: List of enrichers to apply

        Returns:
            Enriched data

        Example:
            >>> def add_full_name(source_fields):
            ...     return {"full_name": f"{source_fields['first']} {source_fields['last']}"}
            >>>
            >>> enricher = Enricher(
            ...     name="full_name",
            ...     enricher_function=add_full_name,
            ...     source_fields=["first", "last"],
            ...     target_fields=["full_name"]
            ... )
            >>> enriched = transformer.enrich_data(data, [enricher])
        """
        if isinstance(data, dict):
            result = data.copy()
            for enricher in enrichers:
                result = self.data_enricher.enrich_with_function(result, enricher)
            return result
        elif isinstance(data, list):
            return [self.enrich_data(item, enrichers) for item in data]
        else:
            return data

    def add_lookup_table(self, name: str, table: Dict) -> None:
        """
        Add a lookup table for enrichment.

        Args:
            name: Table name
            table: Lookup dictionary

        Example:
            >>> transformer.add_lookup_table(
            ...     "countries",
            ...     {"US": "United States", "UK": "United Kingdom"}
            ... )
        """
        self.data_enricher.add_lookup_table(name, table)

    # ========================================================================
    # Aggregation and Filtering Methods
    # ========================================================================

    def aggregate_data(
        self,
        data: List[Dict],
        config: AggregationConfig,
    ) -> List[Dict]:
        """
        Aggregate data with grouping.

        Args:
            data: List of dictionaries to aggregate
            config: Aggregation configuration

        Returns:
            Aggregated data

        Example:
            >>> config = AggregationConfig(
            ...     group_by=["category"],
            ...     aggregations={"amount": ["sum", "avg"], "count": ["count"]}
            ... )
            >>> result = transformer.aggregate_data(sales_data, config)
        """
        return self.aggregation_engine.aggregate(
            data,
            config.group_by,
            config.aggregations,
        )

    def filter_data(
        self,
        data: List[Dict],
        condition: Callable[[Dict], bool],
    ) -> List[Dict]:
        """
        Filter data based on a condition.

        Args:
            data: List of dictionaries to filter
            condition: Filter function

        Returns:
            Filtered data

        Example:
            >>> filtered = transformer.filter_data(
            ...     data,
            ...     lambda x: x.get("age", 0) > 18
            ... )
        """
        return self.filter_engine.filter_records(data, condition)

    # ========================================================================
    # Custom Transformer Registration
    # ========================================================================

    def register_custom_transformer(
        self,
        name: str,
        transformer: Callable,
    ) -> None:
        """
        Register a custom transformer function.

        Args:
            name: Transformer name
            transformer: Transformation function

        Example:
            >>> def custom_transform(data):
            ...     # Custom transformation logic
            ...     return modified_data
            >>>
            >>> transformer.register_custom_transformer("my_transform", custom_transform)
        """
        self.custom_transformers[name] = transformer

    def get_custom_transformer(self, name: str) -> Optional[Callable]:
        """
        Get a custom transformer by name.

        Args:
            name: Transformer name

        Returns:
            Transformer function or None
        """
        return self.custom_transformers.get(name)

    # ========================================================================
    # Utility Methods
    # ========================================================================

    def get_supported_formats(self) -> List[str]:
        """
        Get list of supported data formats.

        Returns:
            List of format names

        Example:
            >>> formats = transformer.get_supported_formats()
            >>> print(formats)  # ['json', 'xml', 'csv', 'parquet', 'avro', 'yaml']
        """
        return [fmt.value for fmt in self.format_registry.get_supported_formats()]

    def get_transformation_history(self) -> List[Dict]:
        """
        Get transformation history.

        Returns:
            List of transformation records

        Example:
            >>> history = transformer.get_transformation_history()
            >>> for record in history:
            ...     print(f"{record['operation']}: {record['success']}")
        """
        return self.history.copy()

    def clear_history(self) -> None:
        """Clear transformation history."""
        self.history.clear()

    def _record_transformation(self, **kwargs) -> None:
        """Record a transformation in history."""
        record = {
            "timestamp": time.time(),
            **kwargs,
        }
        self.history.append(record)

    def get_pipeline(self, name: str) -> Optional[Pipeline]:
        """
        Get a pipeline by name.

        Args:
            name: Pipeline name

        Returns:
            Pipeline or None
        """
        return self.pipelines.get(name)

    def list_pipelines(self) -> List[str]:
        """
        List all registered pipelines.

        Returns:
            List of pipeline names
        """
        return list(self.pipelines.keys())

    def list_schemas(self) -> List[str]:
        """
        List all registered schemas.

        Returns:
            List of schema names
        """
        return self.schema_registry.list_schemas()

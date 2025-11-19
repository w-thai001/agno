"""
Data transformation pipeline system.

Provides composable transformation operations for data processing.
"""

from typing import Any, Callable, Dict, List, Optional, Union
from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import reduce

from agno.utils.log import logger


class TransformationStep(ABC):
    """Base class for transformation steps."""

    def __init__(self, name: Optional[str] = None):
        """Initialize transformation step."""
        self.name = name or self.__class__.__name__
        self._stats = {"processed": 0, "errors": 0}

    @abstractmethod
    def transform(self, data: Any) -> Any:
        """
        Transform data.

        Args:
            data: Input data

        Returns:
            Transformed data
        """
        pass

    def __call__(self, data: Any) -> Any:
        """Make step callable."""
        try:
            result = self.transform(data)
            self._stats["processed"] += 1
            return result
        except Exception as e:
            self._stats["errors"] += 1
            logger.error(f"Error in transformation step {self.name}: {e}")
            raise

    def get_stats(self) -> Dict[str, int]:
        """Get transformation statistics."""
        return self._stats.copy()


class FilterStep(TransformationStep):
    """Filter records based on condition."""

    def __init__(self, condition: Callable[[Any], bool], name: Optional[str] = None):
        """
        Initialize filter step.

        Args:
            condition: Function that returns True for records to keep
            name: Optional name for the step
        """
        super().__init__(name or "Filter")
        self.condition = condition
        self._stats["filtered_out"] = 0

    def transform(self, data: Union[List[Dict], Dict]) -> Union[List[Dict], Dict]:
        """Apply filter to data."""
        if isinstance(data, list):
            original_count = len(data)
            filtered = [item for item in data if self.condition(item)]
            self._stats["filtered_out"] += original_count - len(filtered)
            return filtered
        else:
            # Single record
            return data if self.condition(data) else {}


class MapStep(TransformationStep):
    """Map transformation function over records."""

    def __init__(self, mapper: Callable[[Any], Any], name: Optional[str] = None):
        """
        Initialize map step.

        Args:
            mapper: Function to apply to each record
            name: Optional name for the step
        """
        super().__init__(name or "Map")
        self.mapper = mapper

    def transform(self, data: Union[List[Dict], Dict]) -> Union[List[Dict], Dict]:
        """Apply mapping function."""
        if isinstance(data, list):
            return [self.mapper(item) for item in data]
        else:
            return self.mapper(data)


class SelectFieldsStep(TransformationStep):
    """Select specific fields from records."""

    def __init__(self, fields: List[str], name: Optional[str] = None):
        """
        Initialize select fields step.

        Args:
            fields: List of field names to keep
            name: Optional name for the step
        """
        super().__init__(name or "SelectFields")
        self.fields = fields

    def transform(self, data: Union[List[Dict], Dict]) -> Union[List[Dict], Dict]:
        """Select fields."""
        def select_fields(record: Dict) -> Dict:
            return {field: record.get(field) for field in self.fields if field in record}

        if isinstance(data, list):
            return [select_fields(item) for item in data]
        else:
            return select_fields(data)


class RenameFieldsStep(TransformationStep):
    """Rename fields in records."""

    def __init__(self, mapping: Dict[str, str], name: Optional[str] = None):
        """
        Initialize rename fields step.

        Args:
            mapping: Dictionary mapping old field names to new names
            name: Optional name for the step
        """
        super().__init__(name or "RenameFields")
        self.mapping = mapping

    def transform(self, data: Union[List[Dict], Dict]) -> Union[List[Dict], Dict]:
        """Rename fields."""
        def rename_fields(record: Dict) -> Dict:
            result = {}
            for key, value in record.items():
                new_key = self.mapping.get(key, key)
                result[new_key] = value
            return result

        if isinstance(data, list):
            return [rename_fields(item) for item in data]
        else:
            return rename_fields(data)


class AddFieldStep(TransformationStep):
    """Add new field to records."""

    def __init__(
        self,
        field_name: str,
        value_func: Callable[[Dict], Any],
        name: Optional[str] = None,
    ):
        """
        Initialize add field step.

        Args:
            field_name: Name of field to add
            value_func: Function that computes field value from record
            name: Optional name for the step
        """
        super().__init__(name or f"AddField_{field_name}")
        self.field_name = field_name
        self.value_func = value_func

    def transform(self, data: Union[List[Dict], Dict]) -> Union[List[Dict], Dict]:
        """Add field to records."""
        def add_field(record: Dict) -> Dict:
            result = record.copy()
            result[self.field_name] = self.value_func(record)
            return result

        if isinstance(data, list):
            return [add_field(item) for item in data]
        else:
            return add_field(data)


class SortStep(TransformationStep):
    """Sort records."""

    def __init__(
        self,
        key: Union[str, Callable],
        reverse: bool = False,
        name: Optional[str] = None,
    ):
        """
        Initialize sort step.

        Args:
            key: Field name or key function for sorting
            reverse: Sort in descending order
            name: Optional name for the step
        """
        super().__init__(name or "Sort")
        if isinstance(key, str):
            self.key_func = lambda x: x.get(key)
        else:
            self.key_func = key
        self.reverse = reverse

    def transform(self, data: Union[List[Dict], Dict]) -> Union[List[Dict], Dict]:
        """Sort data."""
        if isinstance(data, list):
            return sorted(data, key=self.key_func, reverse=self.reverse)
        else:
            return data


class GroupByStep(TransformationStep):
    """Group records by field value."""

    def __init__(self, key: Union[str, Callable], name: Optional[str] = None):
        """
        Initialize group by step.

        Args:
            key: Field name or key function for grouping
            name: Optional name for the step
        """
        super().__init__(name or "GroupBy")
        if isinstance(key, str):
            self.key_func = lambda x: x.get(key)
        else:
            self.key_func = key

    def transform(self, data: List[Dict]) -> Dict[Any, List[Dict]]:
        """Group data."""
        if not isinstance(data, list):
            raise ValueError("GroupBy requires list input")

        groups: Dict[Any, List[Dict]] = {}
        for item in data:
            key = self.key_func(item)
            if key not in groups:
                groups[key] = []
            groups[key].append(item)

        return groups


class AggregateStep(TransformationStep):
    """Aggregate records."""

    def __init__(
        self,
        aggregations: Dict[str, Callable[[List], Any]],
        name: Optional[str] = None,
    ):
        """
        Initialize aggregate step.

        Args:
            aggregations: Dictionary mapping field names to aggregation functions
            name: Optional name for the step
        """
        super().__init__(name or "Aggregate")
        self.aggregations = aggregations

    def transform(self, data: Union[List[Dict], Dict[Any, List[Dict]]]) -> Dict[str, Any]:
        """Aggregate data."""
        if isinstance(data, dict):
            # Already grouped data
            results = {}
            for group_key, items in data.items():
                results[group_key] = self._aggregate_items(items)
            return results
        elif isinstance(data, list):
            # Single group
            return self._aggregate_items(data)
        else:
            raise ValueError("Aggregate requires list or grouped dict input")

    def _aggregate_items(self, items: List[Dict]) -> Dict[str, Any]:
        """Aggregate a list of items."""
        result = {}
        for field, agg_func in self.aggregations.items():
            values = [item.get(field) for item in items if field in item]
            result[field] = agg_func(values) if values else None
        return result


class DeduplicateStep(TransformationStep):
    """Remove duplicate records."""

    def __init__(
        self,
        key_fields: Optional[List[str]] = None,
        keep: str = "first",
        name: Optional[str] = None,
    ):
        """
        Initialize deduplicate step.

        Args:
            key_fields: Fields to use for identifying duplicates (None = all fields)
            keep: Which duplicate to keep ('first' or 'last')
            name: Optional name for the step
        """
        super().__init__(name or "Deduplicate")
        self.key_fields = key_fields
        self.keep = keep
        self._stats["duplicates_removed"] = 0

    def transform(self, data: List[Dict]) -> List[Dict]:
        """Remove duplicates."""
        if not isinstance(data, list):
            raise ValueError("Deduplicate requires list input")

        seen = set()
        result = []

        if self.keep == "last":
            data = reversed(data)

        for item in data:
            # Create key for duplicate detection
            if self.key_fields:
                key = tuple(item.get(field) for field in self.key_fields)
            else:
                key = tuple(sorted(item.items()))

            if key not in seen:
                seen.add(key)
                result.append(item)
            else:
                self._stats["duplicates_removed"] += 1

        if self.keep == "last":
            result.reverse()

        return result


class FlattenStep(TransformationStep):
    """Flatten nested structures."""

    def __init__(self, separator: str = ".", name: Optional[str] = None):
        """
        Initialize flatten step.

        Args:
            separator: Separator for nested field names
            name: Optional name for the step
        """
        super().__init__(name or "Flatten")
        self.separator = separator

    def transform(self, data: Union[List[Dict], Dict]) -> Union[List[Dict], Dict]:
        """Flatten nested dictionaries."""
        if isinstance(data, list):
            return [self._flatten_dict(item) for item in data]
        else:
            return self._flatten_dict(data)

    def _flatten_dict(self, d: Dict, parent_key: str = "") -> Dict:
        """Recursively flatten dictionary."""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{self.separator}{k}" if parent_key else k

            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key).items())
            elif isinstance(v, list) and v and isinstance(v[0], dict):
                # Flatten list of dicts
                for i, item in enumerate(v):
                    items.extend(self._flatten_dict(item, f"{new_key}[{i}]").items())
            else:
                items.append((new_key, v))

        return dict(items)


class TransformationPipeline:
    """Pipeline for composing multiple transformation steps."""

    def __init__(self, name: str = "Pipeline"):
        """
        Initialize transformation pipeline.

        Args:
            name: Pipeline name
        """
        self.name = name
        self.steps: List[TransformationStep] = []
        self._execution_stats: List[Dict[str, Any]] = []

    def add_step(self, step: TransformationStep) -> "TransformationPipeline":
        """
        Add transformation step to pipeline.

        Args:
            step: Transformation step to add

        Returns:
            Self for method chaining
        """
        self.steps.append(step)
        return self

    def add_filter(self, condition: Callable[[Any], bool]) -> "TransformationPipeline":
        """Add filter step."""
        return self.add_step(FilterStep(condition))

    def add_map(self, mapper: Callable[[Any], Any]) -> "TransformationPipeline":
        """Add map step."""
        return self.add_step(MapStep(mapper))

    def add_select_fields(self, fields: List[str]) -> "TransformationPipeline":
        """Add select fields step."""
        return self.add_step(SelectFieldsStep(fields))

    def add_rename_fields(self, mapping: Dict[str, str]) -> "TransformationPipeline":
        """Add rename fields step."""
        return self.add_step(RenameFieldsStep(mapping))

    def add_field(
        self, field_name: str, value_func: Callable[[Dict], Any]
    ) -> "TransformationPipeline":
        """Add new field step."""
        return self.add_step(AddFieldStep(field_name, value_func))

    def add_sort(
        self, key: Union[str, Callable], reverse: bool = False
    ) -> "TransformationPipeline":
        """Add sort step."""
        return self.add_step(SortStep(key, reverse))

    def add_group_by(self, key: Union[str, Callable]) -> "TransformationPipeline":
        """Add group by step."""
        return self.add_step(GroupByStep(key))

    def add_aggregate(
        self, aggregations: Dict[str, Callable[[List], Any]]
    ) -> "TransformationPipeline":
        """Add aggregate step."""
        return self.add_step(AggregateStep(aggregations))

    def add_deduplicate(
        self, key_fields: Optional[List[str]] = None, keep: str = "first"
    ) -> "TransformationPipeline":
        """Add deduplicate step."""
        return self.add_step(DeduplicateStep(key_fields, keep))

    def add_flatten(self, separator: str = ".") -> "TransformationPipeline":
        """Add flatten step."""
        return self.add_step(FlattenStep(separator))

    def execute(self, data: Any) -> Any:
        """
        Execute pipeline on data.

        Args:
            data: Input data

        Returns:
            Transformed data
        """
        self._execution_stats = []
        result = data

        for step in self.steps:
            try:
                logger.debug(f"Executing step: {step.name}")
                result = step(result)
                self._execution_stats.append(
                    {"step": step.name, "stats": step.get_stats(), "success": True}
                )
            except Exception as e:
                logger.error(f"Pipeline failed at step {step.name}: {e}")
                self._execution_stats.append(
                    {"step": step.name, "error": str(e), "success": False}
                )
                raise

        logger.info(f"Pipeline {self.name} completed successfully")
        return result

    def get_execution_stats(self) -> List[Dict[str, Any]]:
        """Get statistics from last pipeline execution."""
        return self._execution_stats

    def __call__(self, data: Any) -> Any:
        """Make pipeline callable."""
        return self.execute(data)


# Common aggregation functions
def sum_agg(values: List[Union[int, float]]) -> Union[int, float]:
    """Sum aggregation."""
    return sum(values) if values else 0


def avg_agg(values: List[Union[int, float]]) -> float:
    """Average aggregation."""
    return sum(values) / len(values) if values else 0.0


def min_agg(values: List[Any]) -> Any:
    """Minimum aggregation."""
    return min(values) if values else None


def max_agg(values: List[Any]) -> Any:
    """Maximum aggregation."""
    return max(values) if values else None


def count_agg(values: List[Any]) -> int:
    """Count aggregation."""
    return len(values)


def first_agg(values: List[Any]) -> Any:
    """First value aggregation."""
    return values[0] if values else None


def last_agg(values: List[Any]) -> Any:
    """Last value aggregation."""
    return values[-1] if values else None

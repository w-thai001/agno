"""
FSA-3: RSI Data Aggregator

A production-ready data aggregation system for collecting, validating, and analyzing
RSI (Reflective Self-Improvement) data from multiple sources including logs, metrics,
and execution traces.

Features:
- Multi-source data collection (logs, metrics, execution traces)
- Comprehensive data validation and normalization
- Statistical analysis and aggregation engine
- Trend analysis and correlation detection
- Outlier detection and data quality scoring
- PowerShell subprocess integration for file operations
- Robust error handling with timeout support
- Full type hints and documentation
"""

import json
import subprocess
import sys
import statistics
import platform
from typing import Dict, List, Tuple, Any, Optional, Set, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from collections import defaultdict
import re
import math


class DataSourceType(Enum):
    """Types of data sources for aggregation."""
    EXECUTION_LOGS = "execution_logs"
    PERFORMANCE_METRICS = "performance_metrics"
    ERROR_TRACES = "error_traces"
    QUALITY_METRICS = "quality_metrics"
    SUCCESS_RATES = "success_rates"


class AggregationType(Enum):
    """Types of aggregation operations."""
    MEAN = "mean"
    MEDIAN = "median"
    STD_DEV = "std_dev"
    MIN = "min"
    MAX = "max"
    SUM = "sum"
    COUNT = "count"
    PERCENTILE_95 = "percentile_95"
    PERCENTILE_99 = "percentile_99"


class DataQuality(Enum):
    """Data quality levels."""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    INVALID = "invalid"


@dataclass
class ExecutionLog:
    """Represents a single execution log entry."""
    timestamp: str
    task_id: str
    status: str  # success, failure, error
    duration: float  # in seconds
    message: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    error_trace: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict) -> 'ExecutionLog':
        """Create from dictionary."""
        return ExecutionLog(**data)


@dataclass
class PerformanceMetric:
    """Represents performance metrics."""
    timestamp: str
    task_id: str
    cpu_usage: float  # percentage
    memory_usage: float  # MB
    disk_io: float  # MB/s
    network_io: float  # MB/s
    execution_time: float  # seconds
    throughput: float  # items/second
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict) -> 'PerformanceMetric':
        """Create from dictionary."""
        return PerformanceMetric(**data)


@dataclass
class QualityMetric:
    """Represents quality and LQ score metrics."""
    timestamp: str
    task_id: str
    lq_score: float  # Learning Quality score (0-100)
    accuracy: float  # percentage
    precision: float  # percentage
    recall: float  # percentage
    f1_score: float
    confidence: float  # percentage
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict) -> 'QualityMetric':
        """Create from dictionary."""
        return QualityMetric(**data)


@dataclass
class StatisticalSummary:
    """Statistical summary of a dataset."""
    mean: float
    median: float
    std_dev: float
    min_value: float
    max_value: float
    count: int
    sum_value: float
    percentile_25: float
    percentile_75: float
    percentile_95: float
    percentile_99: float
    variance: float

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class TrendAnalysis:
    """Trend analysis results."""
    metric_name: str
    time_period: str
    trend_direction: str  # increasing, decreasing, stable
    trend_strength: float  # 0-1
    slope: float
    correlation: float
    data_points: int
    start_value: float
    end_value: float
    change_percentage: float

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class OutlierDetection:
    """Outlier detection results."""
    metric_name: str
    outliers: List[Dict[str, Any]]
    outlier_count: int
    outlier_percentage: float
    threshold_lower: float
    threshold_upper: float
    method: str  # iqr, z_score, mad

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class CorrelationResult:
    """Correlation analysis result."""
    metric_x: str
    metric_y: str
    correlation_coefficient: float
    correlation_strength: str  # weak, moderate, strong
    p_value: Optional[float] = None
    sample_size: int = 0

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class DataQualityReport:
    """Data quality assessment report."""
    source_type: str
    quality_score: float  # 0-100
    quality_level: str
    completeness: float  # percentage
    accuracy: float  # percentage
    consistency: float  # percentage
    timeliness: float  # percentage
    issues: List[str]
    recommendations: List[str]

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class AggregatedData:
    """Complete aggregated data structure."""
    timestamp: str
    time_period: str
    data_sources: List[str]
    total_records: int
    statistical_summaries: Dict[str, Dict]
    trend_analyses: List[Dict]
    correlations: List[Dict]
    outliers: List[Dict]
    quality_reports: List[Dict]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)


class DataValidator:
    """
    Validates and normalizes data from various sources.
    """

    @staticmethod
    def validate_execution_log(data: Dict) -> Tuple[bool, List[str]]:
        """
        Validate execution log data.

        Args:
            data: Raw execution log data

        Returns:
            Tuple of (is_valid, list of errors)
        """
        errors = []
        required_fields = ['timestamp', 'task_id', 'status', 'duration', 'message']

        for field in required_fields:
            if field not in data:
                errors.append(f"Missing required field: {field}")

        if 'status' in data and data['status'] not in ['success', 'failure', 'error']:
            errors.append(f"Invalid status: {data['status']}")

        if 'duration' in data:
            try:
                duration = float(data['duration'])
                if duration < 0:
                    errors.append("Duration cannot be negative")
            except (ValueError, TypeError):
                errors.append("Duration must be a number")

        if 'timestamp' in data:
            try:
                datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                errors.append("Invalid timestamp format")

        return len(errors) == 0, errors

    @staticmethod
    def validate_performance_metric(data: Dict) -> Tuple[bool, List[str]]:
        """
        Validate performance metric data.

        Args:
            data: Raw performance metric data

        Returns:
            Tuple of (is_valid, list of errors)
        """
        errors = []
        required_fields = ['timestamp', 'task_id', 'cpu_usage', 'memory_usage', 'execution_time']

        for field in required_fields:
            if field not in data:
                errors.append(f"Missing required field: {field}")

        # Validate numeric ranges
        numeric_checks = {
            'cpu_usage': (0, 100),
            'memory_usage': (0, float('inf')),
            'execution_time': (0, float('inf'))
        }

        for field, (min_val, max_val) in numeric_checks.items():
            if field in data:
                try:
                    value = float(data[field])
                    if value < min_val or value > max_val:
                        errors.append(f"{field} out of valid range ({min_val}-{max_val})")
                except (ValueError, TypeError):
                    errors.append(f"{field} must be a number")

        return len(errors) == 0, errors

    @staticmethod
    def validate_quality_metric(data: Dict) -> Tuple[bool, List[str]]:
        """
        Validate quality metric data.

        Args:
            data: Raw quality metric data

        Returns:
            Tuple of (is_valid, list of errors)
        """
        errors = []
        required_fields = ['timestamp', 'task_id', 'lq_score']

        for field in required_fields:
            if field not in data:
                errors.append(f"Missing required field: {field}")

        # Validate score ranges
        score_fields = ['lq_score', 'accuracy', 'precision', 'recall', 'confidence']
        for field in score_fields:
            if field in data:
                try:
                    value = float(data[field])
                    if value < 0 or value > 100:
                        errors.append(f"{field} must be between 0 and 100")
                except (ValueError, TypeError):
                    errors.append(f"{field} must be a number")

        if 'f1_score' in data:
            try:
                f1 = float(data['f1_score'])
                if f1 < 0 or f1 > 1:
                    errors.append("f1_score must be between 0 and 1")
            except (ValueError, TypeError):
                errors.append("f1_score must be a number")

        return len(errors) == 0, errors

    @staticmethod
    def normalize_data(data: Dict, source_type: DataSourceType) -> Dict:
        """
        Normalize data based on source type.

        Args:
            data: Raw data dictionary
            source_type: Type of data source

        Returns:
            Normalized data dictionary
        """
        normalized = data.copy()

        # Ensure timestamp is in ISO format
        if 'timestamp' in normalized:
            try:
                dt = datetime.fromisoformat(normalized['timestamp'].replace('Z', '+00:00'))
                normalized['timestamp'] = dt.isoformat()
            except:
                normalized['timestamp'] = datetime.now().isoformat()

        # Ensure numeric fields are properly typed
        numeric_fields = [
            'duration', 'cpu_usage', 'memory_usage', 'disk_io', 'network_io',
            'execution_time', 'throughput', 'lq_score', 'accuracy', 'precision',
            'recall', 'f1_score', 'confidence'
        ]

        for field in numeric_fields:
            if field in normalized:
                try:
                    normalized[field] = float(normalized[field])
                except (ValueError, TypeError):
                    normalized[field] = 0.0

        # Ensure metadata exists
        if 'metadata' not in normalized:
            normalized['metadata'] = {}

        return normalized


class StatisticalEngine:
    """
    Statistical analysis engine for data aggregation.
    """

    @staticmethod
    def calculate_summary(values: List[float]) -> Optional[StatisticalSummary]:
        """
        Calculate comprehensive statistical summary.

        Args:
            values: List of numeric values

        Returns:
            StatisticalSummary or None if insufficient data
        """
        if not values or len(values) == 0:
            return None

        try:
            sorted_values = sorted(values)
            n = len(sorted_values)

            summary = StatisticalSummary(
                mean=statistics.mean(values),
                median=statistics.median(values),
                std_dev=statistics.stdev(values) if n > 1 else 0.0,
                min_value=min(values),
                max_value=max(values),
                count=n,
                sum_value=sum(values),
                percentile_25=StatisticalEngine._percentile(sorted_values, 25),
                percentile_75=StatisticalEngine._percentile(sorted_values, 75),
                percentile_95=StatisticalEngine._percentile(sorted_values, 95),
                percentile_99=StatisticalEngine._percentile(sorted_values, 99),
                variance=statistics.variance(values) if n > 1 else 0.0
            )

            return summary
        except Exception as e:
            print(f"Error calculating statistical summary: {e}", file=sys.stderr)
            return None

    @staticmethod
    def _percentile(sorted_values: List[float], percentile: float) -> float:
        """Calculate percentile from sorted values."""
        if not sorted_values:
            return 0.0

        n = len(sorted_values)
        k = (n - 1) * percentile / 100
        f = math.floor(k)
        c = math.ceil(k)

        if f == c:
            return sorted_values[int(k)]

        d0 = sorted_values[int(f)] * (c - k)
        d1 = sorted_values[int(c)] * (k - f)
        return d0 + d1

    @staticmethod
    def detect_outliers_iqr(values: List[float]) -> Tuple[List[int], float, float]:
        """
        Detect outliers using Interquartile Range (IQR) method.

        Args:
            values: List of numeric values

        Returns:
            Tuple of (outlier_indices, lower_threshold, upper_threshold)
        """
        if len(values) < 4:
            return [], 0.0, 0.0

        sorted_values = sorted(values)
        q1 = StatisticalEngine._percentile(sorted_values, 25)
        q3 = StatisticalEngine._percentile(sorted_values, 75)
        iqr = q3 - q1

        lower_threshold = q1 - 1.5 * iqr
        upper_threshold = q3 + 1.5 * iqr

        outlier_indices = [
            i for i, v in enumerate(values)
            if v < lower_threshold or v > upper_threshold
        ]

        return outlier_indices, lower_threshold, upper_threshold

    @staticmethod
    def detect_outliers_zscore(values: List[float], threshold: float = 3.0) -> List[int]:
        """
        Detect outliers using Z-score method.

        Args:
            values: List of numeric values
            threshold: Z-score threshold (default: 3.0)

        Returns:
            List of outlier indices
        """
        if len(values) < 2:
            return []

        try:
            mean = statistics.mean(values)
            std_dev = statistics.stdev(values)

            if std_dev == 0:
                return []

            outlier_indices = [
                i for i, v in enumerate(values)
                if abs((v - mean) / std_dev) > threshold
            ]

            return outlier_indices
        except Exception:
            return []

    @staticmethod
    def calculate_correlation(x_values: List[float], y_values: List[float]) -> Optional[float]:
        """
        Calculate Pearson correlation coefficient.

        Args:
            x_values: First set of values
            y_values: Second set of values

        Returns:
            Correlation coefficient or None if calculation fails
        """
        if len(x_values) != len(y_values) or len(x_values) < 2:
            return None

        try:
            n = len(x_values)
            mean_x = statistics.mean(x_values)
            mean_y = statistics.mean(y_values)

            # Calculate covariance
            covariance = sum((x_values[i] - mean_x) * (y_values[i] - mean_y) for i in range(n)) / n

            # Calculate standard deviations
            std_x = statistics.stdev(x_values)
            std_y = statistics.stdev(y_values)

            if std_x == 0 or std_y == 0:
                return None

            # Correlation coefficient
            correlation = covariance / (std_x * std_y)

            return max(-1.0, min(1.0, correlation))  # Clamp to [-1, 1]
        except Exception:
            return None

    @staticmethod
    def analyze_trend(values: List[float], timestamps: Optional[List[str]] = None) -> Optional[Dict]:
        """
        Analyze trend in time series data.

        Args:
            values: List of numeric values
            timestamps: Optional list of timestamps

        Returns:
            Dictionary with trend analysis or None
        """
        if len(values) < 2:
            return None

        try:
            # Simple linear regression for trend
            n = len(values)
            x = list(range(n))
            y = values

            mean_x = statistics.mean(x)
            mean_y = statistics.mean(y)

            # Calculate slope
            numerator = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
            denominator = sum((x[i] - mean_x) ** 2 for i in range(n))

            slope = numerator / denominator if denominator != 0 else 0

            # Determine trend direction
            if abs(slope) < 0.01 * statistics.stdev(y) if statistics.stdev(y) > 0 else 0:
                direction = "stable"
            elif slope > 0:
                direction = "increasing"
            else:
                direction = "decreasing"

            # Calculate trend strength (R-squared approximation)
            predicted = [mean_y + slope * (i - mean_x) for i in x]
            ss_res = sum((y[i] - predicted[i]) ** 2 for i in range(n))
            ss_tot = sum((y[i] - mean_y) ** 2 for i in range(n))
            r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0

            # Calculate change percentage
            start_value = values[0]
            end_value = values[-1]
            change_pct = ((end_value - start_value) / start_value * 100) if start_value != 0 else 0

            return {
                'slope': slope,
                'direction': direction,
                'strength': max(0, min(1, r_squared)),
                'start_value': start_value,
                'end_value': end_value,
                'change_percentage': change_pct
            }
        except Exception as e:
            print(f"Error analyzing trend: {e}", file=sys.stderr)
            return None


class RSIDataAggregator:
    """
    Main RSI Data Aggregator class for collecting, validating, and analyzing
    reflective self-improvement data.
    """

    def __init__(self):
        """Initialize the data aggregator."""
        self.execution_logs: List[ExecutionLog] = []
        self.performance_metrics: List[PerformanceMetric] = []
        self.quality_metrics: List[QualityMetric] = []
        self.validator = DataValidator()
        self.stats_engine = StatisticalEngine()
        self.aggregated_data: Optional[AggregatedData] = None
        self.is_windows = platform.system() == 'Windows'

    def _get_shell_command(self, operation: str, file_path: str, content: str = "") -> Tuple[List[str], str]:
        """
        Get platform-specific shell command for file operations.

        Args:
            operation: 'read' or 'write'
            file_path: Path to file
            content: Content to write (for write operations)

        Returns:
            Tuple of (command_list, command_string)
        """
        if self.is_windows:
            # Use PowerShell on Windows
            if operation == 'read':
                cmd = f"Get-Content -Path '{file_path}' -Raw"
                return ["powershell", "-Command", cmd], cmd
            else:  # write
                cmd = f"""
$content = @'
{content}
'@
$content | Out-File -FilePath '{file_path}' -Encoding UTF8
"""
                return ["powershell", "-Command", cmd], cmd
        else:
            # Use bash on Linux/Unix
            if operation == 'read':
                cmd = f"cat '{file_path}'"
                return ["bash", "-c", cmd], cmd
            else:  # write
                # Escape single quotes in content for bash
                escaped_content = content.replace("'", "'\\''")
                cmd = f"printf '%s' '{escaped_content}' > '{file_path}'"
                return ["bash", "-c", cmd], cmd

    def load_data_from_json(
        self,
        file_path: str,
        source_type: DataSourceType,
        timeout: int = 30
    ) -> Tuple[int, List[str]]:
        """
        Load data from JSON file using subprocess (PowerShell on Windows, bash on Linux).

        Args:
            file_path: Path to JSON file
            source_type: Type of data source
            timeout: Timeout in seconds for file operation

        Returns:
            Tuple of (records_loaded, list of errors)
        """
        errors = []
        records_loaded = 0

        try:
            # Get platform-specific shell command
            shell_cmd, cmd_str = self._get_shell_command('read', file_path)

            result = subprocess.run(
                shell_cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=True
            )

            if result.returncode != 0:
                errors.append(f"Shell error: {result.stderr}")
                return 0, errors

            # Parse JSON content
            content = result.stdout.strip()
            if not content:
                errors.append("File is empty")
                return 0, errors

            data = json.loads(content)

            # Handle both single object and array
            if isinstance(data, dict):
                data = [data]
            elif not isinstance(data, list):
                errors.append("Invalid JSON format: expected object or array")
                return 0, errors

            # Process each record
            for record in data:
                success = self._process_record(record, source_type, errors)
                if success:
                    records_loaded += 1

        except subprocess.TimeoutExpired:
            errors.append(f"File read operation timed out after {timeout} seconds")
        except subprocess.CalledProcessError as e:
            errors.append(f"Shell error: {e.stderr}")
        except json.JSONDecodeError as e:
            errors.append(f"JSON parse error: {str(e)}")
        except Exception as e:
            errors.append(f"Unexpected error loading data: {str(e)}")

        return records_loaded, errors

    def _process_record(
        self,
        record: Dict,
        source_type: DataSourceType,
        errors: List[str]
    ) -> bool:
        """
        Process a single data record.

        Args:
            record: Data record dictionary
            source_type: Type of data source
            errors: List to append errors to

        Returns:
            True if record was successfully processed
        """
        try:
            # Validate based on source type
            if source_type == DataSourceType.EXECUTION_LOGS:
                is_valid, validation_errors = self.validator.validate_execution_log(record)
                if is_valid:
                    normalized = self.validator.normalize_data(record, source_type)
                    log = ExecutionLog.from_dict(normalized)
                    self.execution_logs.append(log)
                    return True
                else:
                    errors.extend(validation_errors)

            elif source_type == DataSourceType.PERFORMANCE_METRICS:
                is_valid, validation_errors = self.validator.validate_performance_metric(record)
                if is_valid:
                    normalized = self.validator.normalize_data(record, source_type)
                    metric = PerformanceMetric.from_dict(normalized)
                    self.performance_metrics.append(metric)
                    return True
                else:
                    errors.extend(validation_errors)

            elif source_type == DataSourceType.QUALITY_METRICS:
                is_valid, validation_errors = self.validator.validate_quality_metric(record)
                if is_valid:
                    normalized = self.validator.normalize_data(record, source_type)
                    metric = QualityMetric.from_dict(normalized)
                    self.quality_metrics.append(metric)
                    return True
                else:
                    errors.extend(validation_errors)

        except Exception as e:
            errors.append(f"Error processing record: {str(e)}")

        return False

    def add_execution_log(self, log: ExecutionLog) -> None:
        """Add an execution log entry."""
        self.execution_logs.append(log)

    def add_performance_metric(self, metric: PerformanceMetric) -> None:
        """Add a performance metric entry."""
        self.performance_metrics.append(metric)

    def add_quality_metric(self, metric: QualityMetric) -> None:
        """Add a quality metric entry."""
        self.quality_metrics.append(metric)

    def aggregate_data(self, time_period: str = "all") -> AggregatedData:
        """
        Aggregate all collected data with comprehensive analysis.

        Args:
            time_period: Time period for aggregation (e.g., "all", "last_24h")

        Returns:
            AggregatedData object with complete analysis
        """
        timestamp = datetime.now().isoformat()
        data_sources = []
        statistical_summaries = {}
        trend_analyses = []
        correlations = []
        outliers = []
        quality_reports = []

        # Track data sources
        if self.execution_logs:
            data_sources.append("execution_logs")
        if self.performance_metrics:
            data_sources.append("performance_metrics")
        if self.quality_metrics:
            data_sources.append("quality_metrics")

        total_records = (
            len(self.execution_logs) +
            len(self.performance_metrics) +
            len(self.quality_metrics)
        )

        # Statistical summaries for execution logs
        if self.execution_logs:
            durations = [log.duration for log in self.execution_logs]
            duration_summary = self.stats_engine.calculate_summary(durations)
            if duration_summary:
                statistical_summaries['execution_duration'] = duration_summary.to_dict()

            # Success rate
            success_count = sum(1 for log in self.execution_logs if log.status == 'success')
            statistical_summaries['success_rate'] = {
                'value': (success_count / len(self.execution_logs) * 100) if self.execution_logs else 0,
                'total': len(self.execution_logs),
                'successful': success_count,
                'failed': len(self.execution_logs) - success_count
            }

        # Statistical summaries for performance metrics
        if self.performance_metrics:
            cpu_values = [m.cpu_usage for m in self.performance_metrics]
            memory_values = [m.memory_usage for m in self.performance_metrics]
            exec_time_values = [m.execution_time for m in self.performance_metrics]

            cpu_summary = self.stats_engine.calculate_summary(cpu_values)
            if cpu_summary:
                statistical_summaries['cpu_usage'] = cpu_summary.to_dict()

            memory_summary = self.stats_engine.calculate_summary(memory_values)
            if memory_summary:
                statistical_summaries['memory_usage'] = memory_summary.to_dict()

            exec_summary = self.stats_engine.calculate_summary(exec_time_values)
            if exec_summary:
                statistical_summaries['performance_execution_time'] = exec_summary.to_dict()

        # Statistical summaries for quality metrics
        if self.quality_metrics:
            lq_scores = [m.lq_score for m in self.quality_metrics]
            lq_summary = self.stats_engine.calculate_summary(lq_scores)
            if lq_summary:
                statistical_summaries['lq_score'] = lq_summary.to_dict()

            # F1 scores if available
            f1_scores = [m.f1_score for m in self.quality_metrics if m.f1_score > 0]
            if f1_scores:
                f1_summary = self.stats_engine.calculate_summary(f1_scores)
                if f1_summary:
                    statistical_summaries['f1_score'] = f1_summary.to_dict()

        # Trend analysis
        if len(self.execution_logs) >= 2:
            durations = [log.duration for log in self.execution_logs]
            timestamps = [log.timestamp for log in self.execution_logs]
            trend = self.stats_engine.analyze_trend(durations, timestamps)
            if trend:
                trend_analyses.append(TrendAnalysis(
                    metric_name='execution_duration',
                    time_period=time_period,
                    trend_direction=trend['direction'],
                    trend_strength=trend['strength'],
                    slope=trend['slope'],
                    correlation=trend['strength'],
                    data_points=len(durations),
                    start_value=trend['start_value'],
                    end_value=trend['end_value'],
                    change_percentage=trend['change_percentage']
                ).to_dict())

        if len(self.quality_metrics) >= 2:
            lq_scores = [m.lq_score for m in self.quality_metrics]
            timestamps = [m.timestamp for m in self.quality_metrics]
            trend = self.stats_engine.analyze_trend(lq_scores, timestamps)
            if trend:
                trend_analyses.append(TrendAnalysis(
                    metric_name='lq_score',
                    time_period=time_period,
                    trend_direction=trend['direction'],
                    trend_strength=trend['strength'],
                    slope=trend['slope'],
                    correlation=trend['strength'],
                    data_points=len(lq_scores),
                    start_value=trend['start_value'],
                    end_value=trend['end_value'],
                    change_percentage=trend['change_percentage']
                ).to_dict())

        # Correlation analysis
        if len(self.performance_metrics) >= 2:
            cpu_values = [m.cpu_usage for m in self.performance_metrics]
            exec_time_values = [m.execution_time for m in self.performance_metrics]

            corr = self.stats_engine.calculate_correlation(cpu_values, exec_time_values)
            if corr is not None:
                strength = self._correlation_strength(abs(corr))
                correlations.append(CorrelationResult(
                    metric_x='cpu_usage',
                    metric_y='execution_time',
                    correlation_coefficient=corr,
                    correlation_strength=strength,
                    sample_size=len(cpu_values)
                ).to_dict())

        if len(self.quality_metrics) >= 2 and len(self.execution_logs) >= 2:
            # Match by task_id and compare LQ scores with execution duration
            matched_pairs = []
            for qm in self.quality_metrics:
                for log in self.execution_logs:
                    if qm.task_id == log.task_id:
                        matched_pairs.append((qm.lq_score, log.duration))

            if len(matched_pairs) >= 2:
                lq_vals, dur_vals = zip(*matched_pairs)
                corr = self.stats_engine.calculate_correlation(list(lq_vals), list(dur_vals))
                if corr is not None:
                    strength = self._correlation_strength(abs(corr))
                    correlations.append(CorrelationResult(
                        metric_x='lq_score',
                        metric_y='execution_duration',
                        correlation_coefficient=corr,
                        correlation_strength=strength,
                        sample_size=len(matched_pairs)
                    ).to_dict())

        # Outlier detection
        if self.execution_logs:
            durations = [log.duration for log in self.execution_logs]
            outlier_indices, lower, upper = self.stats_engine.detect_outliers_iqr(durations)

            if outlier_indices:
                outlier_data = [
                    {
                        'index': i,
                        'task_id': self.execution_logs[i].task_id,
                        'value': durations[i],
                        'timestamp': self.execution_logs[i].timestamp
                    }
                    for i in outlier_indices
                ]

                outliers.append(OutlierDetection(
                    metric_name='execution_duration',
                    outliers=outlier_data,
                    outlier_count=len(outlier_indices),
                    outlier_percentage=(len(outlier_indices) / len(durations) * 100),
                    threshold_lower=lower,
                    threshold_upper=upper,
                    method='iqr'
                ).to_dict())

        if self.performance_metrics:
            cpu_values = [m.cpu_usage for m in self.performance_metrics]
            outlier_indices = self.stats_engine.detect_outliers_zscore(cpu_values)

            if outlier_indices:
                outlier_data = [
                    {
                        'index': i,
                        'task_id': self.performance_metrics[i].task_id,
                        'value': cpu_values[i],
                        'timestamp': self.performance_metrics[i].timestamp
                    }
                    for i in outlier_indices
                ]

                outliers.append(OutlierDetection(
                    metric_name='cpu_usage',
                    outliers=outlier_data,
                    outlier_count=len(outlier_indices),
                    outlier_percentage=(len(outlier_indices) / len(cpu_values) * 100),
                    threshold_lower=0,
                    threshold_upper=0,
                    method='z_score'
                ).to_dict())

        # Data quality reports
        if self.execution_logs:
            quality_reports.append(self._assess_data_quality(
                DataSourceType.EXECUTION_LOGS,
                len(self.execution_logs)
            ).to_dict())

        if self.performance_metrics:
            quality_reports.append(self._assess_data_quality(
                DataSourceType.PERFORMANCE_METRICS,
                len(self.performance_metrics)
            ).to_dict())

        if self.quality_metrics:
            quality_reports.append(self._assess_data_quality(
                DataSourceType.QUALITY_METRICS,
                len(self.quality_metrics)
            ).to_dict())

        # Create aggregated data
        self.aggregated_data = AggregatedData(
            timestamp=timestamp,
            time_period=time_period,
            data_sources=data_sources,
            total_records=total_records,
            statistical_summaries=statistical_summaries,
            trend_analyses=trend_analyses,
            correlations=correlations,
            outliers=outliers,
            quality_reports=quality_reports,
            metadata={
                'aggregator_version': '1.0.0',
                'generated_at': timestamp
            }
        )

        return self.aggregated_data

    def _correlation_strength(self, abs_corr: float) -> str:
        """Determine correlation strength from coefficient."""
        if abs_corr < 0.3:
            return "weak"
        elif abs_corr < 0.7:
            return "moderate"
        else:
            return "strong"

    def _assess_data_quality(
        self,
        source_type: DataSourceType,
        record_count: int
    ) -> DataQualityReport:
        """
        Assess data quality for a specific source.

        Args:
            source_type: Type of data source
            record_count: Number of records

        Returns:
            DataQualityReport
        """
        issues = []
        recommendations = []

        # Completeness assessment
        completeness = 100.0  # Start optimistic
        if record_count == 0:
            completeness = 0.0
            issues.append("No data available")
        elif record_count < 10:
            completeness = 50.0
            issues.append("Insufficient data for reliable analysis")
            recommendations.append("Collect more data samples")

        # Accuracy assessment (based on validation)
        accuracy = 100.0  # Assume high accuracy if data passed validation

        # Consistency assessment
        consistency = 100.0
        if source_type == DataSourceType.EXECUTION_LOGS:
            # Check for timestamp consistency
            if self.execution_logs:
                timestamps = [log.timestamp for log in self.execution_logs]
                # Simple check: ensure timestamps are not all the same
                if len(set(timestamps)) == 1 and len(timestamps) > 1:
                    consistency = 70.0
                    issues.append("All timestamps are identical")

        # Timeliness assessment
        timeliness = 100.0
        if source_type == DataSourceType.EXECUTION_LOGS and self.execution_logs:
            try:
                latest_timestamp = max(
                    datetime.fromisoformat(log.timestamp.replace('Z', '+00:00'))
                    for log in self.execution_logs
                )
                age = datetime.now(latest_timestamp.tzinfo) - latest_timestamp
                if age > timedelta(days=7):
                    timeliness = 60.0
                    issues.append("Data is more than 7 days old")
                    recommendations.append("Update with recent data")
            except Exception:
                pass

        # Calculate overall quality score
        quality_score = (completeness + accuracy + consistency + timeliness) / 4

        # Determine quality level
        if quality_score >= 90:
            quality_level = DataQuality.EXCELLENT.value
        elif quality_score >= 75:
            quality_level = DataQuality.GOOD.value
        elif quality_score >= 60:
            quality_level = DataQuality.FAIR.value
        elif quality_score >= 40:
            quality_level = DataQuality.POOR.value
        else:
            quality_level = DataQuality.INVALID.value

        return DataQualityReport(
            source_type=source_type.value,
            quality_score=quality_score,
            quality_level=quality_level,
            completeness=completeness,
            accuracy=accuracy,
            consistency=consistency,
            timeliness=timeliness,
            issues=issues,
            recommendations=recommendations
        )

    def export_to_json(
        self,
        output_path: str,
        data: Optional[Dict] = None,
        timeout: int = 30
    ) -> bool:
        """
        Export aggregated data to JSON file using subprocess (PowerShell on Windows, bash on Linux).

        Args:
            output_path: Path where JSON should be saved
            data: Optional data to export (defaults to aggregated_data)
            timeout: Timeout in seconds for file operation

        Returns:
            True if export successful, False otherwise
        """
        try:
            # Use aggregated data if no data provided
            if data is None:
                if self.aggregated_data is None:
                    print("No aggregated data available to export", file=sys.stderr)
                    return False
                data = self.aggregated_data.to_dict()

            # Convert to JSON
            json_content = json.dumps(data, indent=2)

            # Get platform-specific shell command
            shell_cmd, cmd_str = self._get_shell_command('write', output_path, json_content)

            result = subprocess.run(
                shell_cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=True
            )

            if result.returncode == 0:
                print(f"Data exported successfully to: {output_path}")
                return True
            else:
                print(f"Shell export failed: {result.stderr}", file=sys.stderr)
                return False

        except subprocess.TimeoutExpired:
            print(f"File write operation timed out after {timeout} seconds", file=sys.stderr)
            return False
        except subprocess.CalledProcessError as e:
            print(f"Shell error during export: {e.stderr}", file=sys.stderr)
            return False
        except Exception as e:
            print(f"Unexpected error during export: {str(e)}", file=sys.stderr)
            return False

    def generate_summary_report(self) -> str:
        """
        Generate a human-readable summary report.

        Returns:
            Formatted summary report string
        """
        if not self.aggregated_data:
            return "No aggregated data available. Run aggregate_data() first."

        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("RSI DATA AGGREGATION SUMMARY REPORT")
        report_lines.append("=" * 80)
        report_lines.append(f"Generated: {self.aggregated_data.timestamp}")
        report_lines.append(f"Time Period: {self.aggregated_data.time_period}")
        report_lines.append(f"Total Records: {self.aggregated_data.total_records}")
        report_lines.append(f"Data Sources: {', '.join(self.aggregated_data.data_sources)}")
        report_lines.append("")

        # Statistical Summaries
        if self.aggregated_data.statistical_summaries:
            report_lines.append("-" * 80)
            report_lines.append("STATISTICAL SUMMARIES")
            report_lines.append("-" * 80)

            for metric_name, summary in self.aggregated_data.statistical_summaries.items():
                report_lines.append(f"\n{metric_name.upper().replace('_', ' ')}:")
                if 'mean' in summary:
                    report_lines.append(f"  Mean: {summary['mean']:.2f}")
                    report_lines.append(f"  Median: {summary['median']:.2f}")
                    report_lines.append(f"  Std Dev: {summary['std_dev']:.2f}")
                    report_lines.append(f"  Min: {summary['min_value']:.2f}")
                    report_lines.append(f"  Max: {summary['max_value']:.2f}")
                    report_lines.append(f"  Count: {summary['count']}")
                elif 'value' in summary:
                    report_lines.append(f"  Rate: {summary['value']:.2f}%")
                    report_lines.append(f"  Total: {summary['total']}")
                    if 'successful' in summary:
                        report_lines.append(f"  Successful: {summary['successful']}")
                        report_lines.append(f"  Failed: {summary['failed']}")

        # Trend Analyses
        if self.aggregated_data.trend_analyses:
            report_lines.append("")
            report_lines.append("-" * 80)
            report_lines.append("TREND ANALYSES")
            report_lines.append("-" * 80)

            for trend in self.aggregated_data.trend_analyses:
                report_lines.append(f"\n{trend['metric_name'].upper().replace('_', ' ')}:")
                report_lines.append(f"  Direction: {trend['trend_direction'].upper()}")
                report_lines.append(f"  Strength: {trend['trend_strength']:.2f}")
                report_lines.append(f"  Change: {trend['change_percentage']:+.2f}%")
                report_lines.append(f"  Start Value: {trend['start_value']:.2f}")
                report_lines.append(f"  End Value: {trend['end_value']:.2f}")
                report_lines.append(f"  Data Points: {trend['data_points']}")

        # Correlations
        if self.aggregated_data.correlations:
            report_lines.append("")
            report_lines.append("-" * 80)
            report_lines.append("CORRELATION ANALYSES")
            report_lines.append("-" * 80)

            for corr in self.aggregated_data.correlations:
                report_lines.append(
                    f"\n{corr['metric_x']} vs {corr['metric_y']}:"
                )
                report_lines.append(f"  Coefficient: {corr['correlation_coefficient']:.3f}")
                report_lines.append(f"  Strength: {corr['correlation_strength'].upper()}")
                report_lines.append(f"  Sample Size: {corr['sample_size']}")

        # Outliers
        if self.aggregated_data.outliers:
            report_lines.append("")
            report_lines.append("-" * 80)
            report_lines.append("OUTLIER DETECTION")
            report_lines.append("-" * 80)

            for outlier_set in self.aggregated_data.outliers:
                report_lines.append(f"\n{outlier_set['metric_name'].upper().replace('_', ' ')}:")
                report_lines.append(f"  Method: {outlier_set['method'].upper()}")
                report_lines.append(f"  Outliers Found: {outlier_set['outlier_count']}")
                report_lines.append(f"  Percentage: {outlier_set['outlier_percentage']:.2f}%")
                if outlier_set['method'] == 'iqr':
                    report_lines.append(f"  Lower Threshold: {outlier_set['threshold_lower']:.2f}")
                    report_lines.append(f"  Upper Threshold: {outlier_set['threshold_upper']:.2f}")

        # Data Quality
        if self.aggregated_data.quality_reports:
            report_lines.append("")
            report_lines.append("-" * 80)
            report_lines.append("DATA QUALITY REPORTS")
            report_lines.append("-" * 80)

            for quality in self.aggregated_data.quality_reports:
                report_lines.append(f"\n{quality['source_type'].upper().replace('_', ' ')}:")
                report_lines.append(f"  Quality Level: {quality['quality_level'].upper()}")
                report_lines.append(f"  Quality Score: {quality['quality_score']:.2f}/100")
                report_lines.append(f"  Completeness: {quality['completeness']:.2f}%")
                report_lines.append(f"  Accuracy: {quality['accuracy']:.2f}%")
                report_lines.append(f"  Consistency: {quality['consistency']:.2f}%")
                report_lines.append(f"  Timeliness: {quality['timeliness']:.2f}%")

                if quality['issues']:
                    report_lines.append("  Issues:")
                    for issue in quality['issues']:
                        report_lines.append(f"    - {issue}")

                if quality['recommendations']:
                    report_lines.append("  Recommendations:")
                    for rec in quality['recommendations']:
                        report_lines.append(f"    - {rec}")

        report_lines.append("")
        report_lines.append("=" * 80)

        return "\n".join(report_lines)

    def generate_visualization_data(self) -> Dict:
        """
        Generate data suitable for visualization (not rendered).

        Returns:
            Dictionary containing visualization-ready data
        """
        if not self.aggregated_data:
            return {}

        viz_data = {
            'time_series': {},
            'distributions': {},
            'scatter_plots': {},
            'bar_charts': {}
        }

        # Time series data
        if self.execution_logs:
            viz_data['time_series']['execution_duration'] = [
                {'timestamp': log.timestamp, 'value': log.duration}
                for log in self.execution_logs
            ]

        if self.quality_metrics:
            viz_data['time_series']['lq_score'] = [
                {'timestamp': m.timestamp, 'value': m.lq_score}
                for m in self.quality_metrics
            ]

        if self.performance_metrics:
            viz_data['time_series']['cpu_usage'] = [
                {'timestamp': m.timestamp, 'value': m.cpu_usage}
                for m in self.performance_metrics
            ]

        # Distribution data
        if self.execution_logs:
            durations = [log.duration for log in self.execution_logs]
            viz_data['distributions']['execution_duration'] = {
                'values': durations,
                'bins': 10
            }

        # Scatter plot data
        if self.performance_metrics:
            viz_data['scatter_plots']['cpu_vs_execution_time'] = [
                {'x': m.cpu_usage, 'y': m.execution_time}
                for m in self.performance_metrics
            ]

        # Bar chart data
        if self.execution_logs:
            status_counts = defaultdict(int)
            for log in self.execution_logs:
                status_counts[log.status] += 1

            viz_data['bar_charts']['execution_status'] = [
                {'label': status, 'value': count}
                for status, count in status_counts.items()
            ]

        return viz_data

    def clear_data(self) -> None:
        """Clear all collected data."""
        self.execution_logs.clear()
        self.performance_metrics.clear()
        self.quality_metrics.clear()
        self.aggregated_data = None


def run_aggregator() -> Dict:
    """
    Orchestrate the complete data aggregation pipeline.

    This is the main entry point demonstrating full FSA-3 capabilities.

    Returns:
        Dictionary containing aggregation results
    """
    print("=" * 80)
    print("FSA-3: RSI Data Aggregator")
    print("=" * 80)
    print()

    aggregator = RSIDataAggregator()
    results = {
        'success': False,
        'outputs': [],
        'errors': []
    }

    try:
        # Example 1: Generate and aggregate sample execution logs
        print("Example 1: Execution Logs Aggregation")
        print("-" * 80)

        # Generate sample data
        sample_logs = []
        base_time = datetime.now()
        for i in range(20):
            log = ExecutionLog(
                timestamp=(base_time - timedelta(hours=i)).isoformat(),
                task_id=f"task_{i:03d}",
                status='success' if i % 4 != 0 else 'failure',
                duration=5.0 + (i * 0.3) + (i % 5) * 2.0,
                message=f"Execution {i} completed",
                metadata={'iteration': i}
            )
            sample_logs.append(log)
            aggregator.add_execution_log(log)

        print(f"✓ Added {len(sample_logs)} execution log entries")

        # Example 2: Generate and aggregate performance metrics
        print("\nExample 2: Performance Metrics Aggregation")
        print("-" * 80)

        sample_metrics = []
        for i in range(20):
            metric = PerformanceMetric(
                timestamp=(base_time - timedelta(hours=i)).isoformat(),
                task_id=f"task_{i:03d}",
                cpu_usage=45.0 + (i % 10) * 5.0,
                memory_usage=1024.0 + (i * 50.0),
                disk_io=10.0 + (i % 5) * 2.0,
                network_io=5.0 + (i % 3) * 1.5,
                execution_time=5.0 + (i * 0.3),
                throughput=100.0 - (i * 2.0),
                metadata={'iteration': i}
            )
            sample_metrics.append(metric)
            aggregator.add_performance_metric(metric)

        print(f"✓ Added {len(sample_metrics)} performance metric entries")

        # Example 3: Generate and aggregate quality metrics
        print("\nExample 3: Quality Metrics Aggregation")
        print("-" * 80)

        sample_quality = []
        for i in range(20):
            metric = QualityMetric(
                timestamp=(base_time - timedelta(hours=i)).isoformat(),
                task_id=f"task_{i:03d}",
                lq_score=75.0 + (i * 0.5) + (i % 7) * 2.0,
                accuracy=85.0 + (i % 5) * 2.0,
                precision=80.0 + (i % 6) * 2.5,
                recall=82.0 + (i % 4) * 3.0,
                f1_score=0.83 + (i % 10) * 0.01,
                confidence=90.0 + (i % 8) * 1.0,
                metadata={'iteration': i}
            )
            sample_quality.append(metric)
            aggregator.add_quality_metric(metric)

        print(f"✓ Added {len(sample_quality)} quality metric entries")

        # Perform aggregation
        print("\nAggregating all data...")
        print("-" * 80)

        aggregated = aggregator.aggregate_data(time_period="last_20_hours")

        print(f"✓ Aggregation completed")
        print(f"  Total records processed: {aggregated.total_records}")
        print(f"  Data sources: {len(aggregated.data_sources)}")
        print(f"  Statistical summaries: {len(aggregated.statistical_summaries)}")
        print(f"  Trend analyses: {len(aggregated.trend_analyses)}")
        print(f"  Correlations: {len(aggregated.correlations)}")
        print(f"  Outlier sets: {len(aggregated.outliers)}")
        print(f"  Quality reports: {len(aggregated.quality_reports)}")

        # Export aggregated data
        print("\nExporting aggregated data...")
        print("-" * 80)

        output_path = "/home/user/agno/rsi_aggregated_data.json"
        export_success = aggregator.export_to_json(output_path)

        if export_success:
            results['outputs'].append({
                'type': 'aggregated_data',
                'file': output_path
            })

        # Generate summary report
        print("\nGenerating summary report...")
        print("-" * 80)

        summary = aggregator.generate_summary_report()
        print(summary)

        # Export summary report
        summary_path = "/home/user/agno/rsi_summary_report.txt"

        # Get platform-specific shell command
        shell_cmd, cmd_str = aggregator._get_shell_command('write', summary_path, summary)

        try:
            subprocess.run(
                shell_cmd,
                capture_output=True,
                text=True,
                timeout=30,
                check=True
            )

            print(f"\n✓ Summary report saved to: {summary_path}")
            results['outputs'].append({
                'type': 'summary_report',
                'file': summary_path
            })
        except Exception as e:
            print(f"Warning: Could not save summary report: {e}", file=sys.stderr)

        # Generate visualization data
        print("\nGenerating visualization data...")
        print("-" * 80)

        viz_data = aggregator.generate_visualization_data()
        viz_path = "/home/user/agno/rsi_visualization_data.json"

        viz_export_success = aggregator.export_to_json(viz_path, viz_data)

        if viz_export_success:
            print(f"✓ Visualization data saved to: {viz_path}")
            results['outputs'].append({
                'type': 'visualization_data',
                'file': viz_path
            })

        # Final summary
        print("\n" + "=" * 80)
        print("AGGREGATION SUMMARY")
        print("=" * 80)
        print(f"✓ Successfully aggregated {aggregated.total_records} records")
        print(f"✓ Generated {len(results['outputs'])} output files:")
        for output in results['outputs']:
            print(f"  - {output['type']}: {output['file']}")

        results['success'] = True

    except Exception as e:
        error_msg = f"Error in data aggregation: {str(e)}"
        print(f"\n✗ {error_msg}", file=sys.stderr)
        results['errors'].append(error_msg)
        import traceback
        traceback.print_exc()

    return results


if __name__ == "__main__":
    """Main execution entry point."""
    try:
        results = run_aggregator()

        if results['success']:
            print("\n✓ FSA-3 RSI Data Aggregator completed successfully!")
            sys.exit(0)
        else:
            print("\n✗ FSA-3 RSI Data Aggregator encountered errors")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\n✗ Data aggregation interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n✗ Fatal error: {e}", file=sys.stderr)
        sys.exit(1)

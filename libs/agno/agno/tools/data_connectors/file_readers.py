"""
File system readers for various formats.

Supports:
- CSV
- JSON (including JSON Lines/NDJSON)
- XML
- Parquet
- Excel (XLSX/XLS)
"""

import csv
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Union

from agno.tools.data_connectors.base import DataConnectorBase, DataConnectorConfig, with_retry
from agno.utils.log import logger


class CSVReader(DataConnectorBase):
    """CSV file reader with streaming support."""

    def __init__(
        self,
        file_path: Union[str, Path],
        config: Optional[DataConnectorConfig] = None,
        delimiter: str = ",",
        encoding: str = "utf-8",
        skip_header: bool = False,
        **csv_kwargs,
    ):
        """
        Initialize CSV reader.

        Args:
            file_path: Path to CSV file
            config: Connector configuration
            delimiter: CSV delimiter
            encoding: File encoding
            skip_header: Whether to skip header row
            **csv_kwargs: Additional csv.DictReader parameters
        """
        super().__init__(config)
        self.file_path = Path(file_path)
        self.delimiter = delimiter
        self.encoding = encoding
        self.skip_header = skip_header
        self.csv_kwargs = csv_kwargs
        self._file_handle = None

    def connect(self) -> None:
        """Open CSV file."""
        if not self.file_path.exists():
            raise FileNotFoundError(f"CSV file not found: {self.file_path}")

        self._is_connected = True
        logger.info(f"CSV reader ready for {self.file_path}")

    def disconnect(self) -> None:
        """Close file handle if open."""
        if self._file_handle:
            self._file_handle.close()
            self._file_handle = None
        self._is_connected = False

    def read(
        self, query: Optional[int] = None, chunk_size: Optional[int] = None, **kwargs
    ) -> Union[List[Dict[str, Any]], Iterator[List[Dict[str, Any]]]]:
        """
        Read CSV file.

        Args:
            query: Number of rows to read (None for all)
            chunk_size: If specified, return iterator of chunks
            **kwargs: Additional parameters

        Returns:
            List of dictionaries or iterator of chunks
        """
        try:
            if chunk_size:
                return self._read_chunks(chunk_size, query)
            else:
                return self._read_all(query)
        except Exception as e:
            logger.error(f"Error reading CSV: {e}")
            self._record_metric("errors")
            raise

    def _read_all(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Read entire CSV or up to limit."""
        with open(self.file_path, "r", encoding=self.encoding) as f:
            reader = csv.DictReader(f, delimiter=self.delimiter, **self.csv_kwargs)

            if self.skip_header:
                next(reader, None)

            if limit:
                data = [row for i, row in enumerate(reader) if i < limit]
            else:
                data = list(reader)

        self._record_metric("reads")
        logger.info(f"Read {len(data)} rows from {self.file_path}")
        return data

    def _read_chunks(self, chunk_size: int, limit: Optional[int] = None) -> Iterator[List[Dict[str, Any]]]:
        """Read CSV in chunks."""
        with open(self.file_path, "r", encoding=self.encoding) as f:
            reader = csv.DictReader(f, delimiter=self.delimiter, **self.csv_kwargs)

            if self.skip_header:
                next(reader, None)

            chunk = []
            total_read = 0

            for row in reader:
                chunk.append(row)
                total_read += 1

                if len(chunk) >= chunk_size:
                    yield chunk
                    self._record_metric("reads")
                    chunk = []

                if limit and total_read >= limit:
                    break

            if chunk:
                yield chunk
                self._record_metric("reads")

    def write(self, data: List[Dict[str, Any]], target: str, mode: str = "w", **kwargs) -> None:
        """
        Write data to CSV file.

        Args:
            data: List of dictionaries to write
            target: Target file path
            mode: Write mode ('w' or 'a')
            **kwargs: Additional csv.DictWriter parameters
        """
        if not data:
            return

        target_path = Path(target)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        fieldnames = list(data[0].keys())

        with open(target_path, mode, encoding=self.encoding, newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=self.delimiter, **kwargs)

            if mode == "w" or not target_path.exists():
                writer.writeheader()

            writer.writerows(data)

        self._record_metric("writes", len(data))
        logger.info(f"Wrote {len(data)} rows to {target_path}")


class JSONReader(DataConnectorBase):
    """JSON and NDJSON file reader."""

    def __init__(
        self,
        file_path: Union[str, Path],
        config: Optional[DataConnectorConfig] = None,
        is_ndjson: bool = False,
        encoding: str = "utf-8",
    ):
        """
        Initialize JSON reader.

        Args:
            file_path: Path to JSON file
            config: Connector configuration
            is_ndjson: Whether file is NDJSON (JSON Lines) format
            encoding: File encoding
        """
        super().__init__(config)
        self.file_path = Path(file_path)
        self.is_ndjson = is_ndjson
        self.encoding = encoding

    def connect(self) -> None:
        """Verify JSON file exists."""
        if not self.file_path.exists():
            raise FileNotFoundError(f"JSON file not found: {self.file_path}")

        self._is_connected = True
        logger.info(f"JSON reader ready for {self.file_path}")

    def disconnect(self) -> None:
        """No-op for JSON files."""
        self._is_connected = False

    def read(self, query: Optional[str] = None, **kwargs) -> Any:
        """
        Read JSON file.

        Args:
            query: JSONPath query (if supported, otherwise None for full file)
            **kwargs: Additional parameters

        Returns:
            Parsed JSON data
        """
        try:
            with open(self.file_path, "r", encoding=self.encoding) as f:
                if self.is_ndjson:
                    data = [json.loads(line) for line in f if line.strip()]
                else:
                    data = json.load(f)

            self._record_metric("reads")
            logger.info(f"Read JSON from {self.file_path}")
            return data
        except Exception as e:
            logger.error(f"Error reading JSON: {e}")
            self._record_metric("errors")
            raise

    def write(self, data: Any, target: str, indent: int = 2, **kwargs) -> None:
        """
        Write data to JSON file.

        Args:
            data: Data to write
            target: Target file path
            indent: JSON indentation
            **kwargs: Additional json.dump parameters
        """
        target_path = Path(target)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        with open(target_path, "w", encoding=self.encoding) as f:
            if self.is_ndjson and isinstance(data, list):
                for item in data:
                    f.write(json.dumps(item, **kwargs) + "\n")
            else:
                json.dump(data, f, indent=indent, **kwargs)

        self._record_metric("writes")
        logger.info(f"Wrote JSON to {target_path}")


class XMLReader(DataConnectorBase):
    """XML file reader."""

    def __init__(
        self,
        file_path: Union[str, Path],
        config: Optional[DataConnectorConfig] = None,
        encoding: str = "utf-8",
    ):
        """
        Initialize XML reader.

        Args:
            file_path: Path to XML file
            config: Connector configuration
            encoding: File encoding
        """
        super().__init__(config)
        self.file_path = Path(file_path)
        self.encoding = encoding
        self._tree = None

    def connect(self) -> None:
        """Parse XML file."""
        if not self.file_path.exists():
            raise FileNotFoundError(f"XML file not found: {self.file_path}")

        try:
            self._tree = ET.parse(self.file_path)
            self._is_connected = True
            logger.info(f"Parsed XML from {self.file_path}")
        except Exception as e:
            logger.error(f"Error parsing XML: {e}")
            raise

    def disconnect(self) -> None:
        """Clear XML tree."""
        self._tree = None
        self._is_connected = False

    def read(self, query: Optional[str] = None, **kwargs) -> Union[ET.Element, List[ET.Element]]:
        """
        Read XML data.

        Args:
            query: XPath query (None for root element)
            **kwargs: Additional parameters

        Returns:
            XML Element or list of Elements
        """
        if not self._tree:
            self.connect()

        try:
            if query:
                results = self._tree.findall(query)
                self._record_metric("reads")
                return results
            else:
                self._record_metric("reads")
                return self._tree.getroot()
        except Exception as e:
            logger.error(f"Error reading XML: {e}")
            self._record_metric("errors")
            raise

    def to_dict(self, element: Optional[ET.Element] = None) -> Dict[str, Any]:
        """
        Convert XML element to dictionary.

        Args:
            element: XML element (None for root)

        Returns:
            Dictionary representation
        """
        if element is None:
            if not self._tree:
                self.connect()
            element = self._tree.getroot()

        result = {
            "tag": element.tag,
            "attributes": element.attrib,
            "text": element.text.strip() if element.text else None,
            "children": [self.to_dict(child) for child in element],
        }
        return result


class ParquetReader(DataConnectorBase):
    """Parquet file reader using PyArrow."""

    def __init__(
        self,
        file_path: Union[str, Path],
        config: Optional[DataConnectorConfig] = None,
        **parquet_kwargs,
    ):
        """
        Initialize Parquet reader.

        Args:
            file_path: Path to Parquet file
            config: Connector configuration
            **parquet_kwargs: Additional PyArrow parameters
        """
        super().__init__(config)
        self.file_path = Path(file_path)
        self.parquet_kwargs = parquet_kwargs

    def connect(self) -> None:
        """Verify Parquet file exists."""
        try:
            import pyarrow.parquet as pq  # noqa: F401
        except ImportError:
            raise ImportError("pyarrow not installed. Install with: pip install pyarrow")

        if not self.file_path.exists():
            raise FileNotFoundError(f"Parquet file not found: {self.file_path}")

        self._is_connected = True
        logger.info(f"Parquet reader ready for {self.file_path}")

    def disconnect(self) -> None:
        """No-op for Parquet files."""
        self._is_connected = False

    def read(
        self, query: Optional[List[str]] = None, use_pandas: bool = True, **kwargs
    ) -> Any:
        """
        Read Parquet file.

        Args:
            query: Column names to read (None for all)
            use_pandas: Whether to return pandas DataFrame
            **kwargs: Additional read parameters

        Returns:
            DataFrame or PyArrow Table
        """
        try:
            import pyarrow.parquet as pq

            table = pq.read_table(self.file_path, columns=query, **self.parquet_kwargs)

            self._record_metric("reads")

            if use_pandas:
                return table.to_pandas()
            else:
                return table

        except Exception as e:
            logger.error(f"Error reading Parquet: {e}")
            self._record_metric("errors")
            raise

    def write(self, data: Any, target: str, **kwargs) -> None:
        """
        Write data to Parquet file.

        Args:
            data: DataFrame or PyArrow Table
            target: Target file path
            **kwargs: Additional write parameters
        """
        try:
            import pyarrow as pa
            import pyarrow.parquet as pq

            target_path = Path(target)
            target_path.parent.mkdir(parents=True, exist_ok=True)

            # Convert to PyArrow Table if needed
            if hasattr(data, "to_arrow"):
                table = data.to_arrow()
            elif not isinstance(data, pa.Table):
                table = pa.Table.from_pandas(data)
            else:
                table = data

            pq.write_table(table, target_path, **kwargs)

            self._record_metric("writes")
            logger.info(f"Wrote Parquet to {target_path}")

        except Exception as e:
            logger.error(f"Error writing Parquet: {e}")
            self._record_metric("errors")
            raise


class FileReaderConnector(DataConnectorBase):
    """Unified file reader supporting multiple formats."""

    def __init__(
        self,
        file_path: Union[str, Path],
        file_format: Optional[str] = None,
        config: Optional[DataConnectorConfig] = None,
        **format_kwargs,
    ):
        """
        Initialize file reader.

        Args:
            file_path: Path to file
            file_format: File format (csv, json, xml, parquet) - auto-detected if None
            config: Connector configuration
            **format_kwargs: Format-specific parameters
        """
        super().__init__(config)
        self.file_path = Path(file_path)
        self.format_kwargs = format_kwargs

        # Auto-detect format
        if file_format is None:
            suffix = self.file_path.suffix.lower()
            format_map = {
                ".csv": "csv",
                ".json": "json",
                ".jsonl": "ndjson",
                ".ndjson": "ndjson",
                ".xml": "xml",
                ".parquet": "parquet",
                ".pq": "parquet",
            }
            file_format = format_map.get(suffix)

            if file_format is None:
                raise ValueError(f"Cannot auto-detect format for {self.file_path}")

        self.file_format = file_format.lower()

        # Create appropriate reader
        if self.file_format == "csv":
            self._reader = CSVReader(file_path, config, **format_kwargs)
        elif self.file_format in ["json", "ndjson"]:
            self._reader = JSONReader(
                file_path, config, is_ndjson=(self.file_format == "ndjson"), **format_kwargs
            )
        elif self.file_format == "xml":
            self._reader = XMLReader(file_path, config, **format_kwargs)
        elif self.file_format == "parquet":
            self._reader = ParquetReader(file_path, config, **format_kwargs)
        else:
            raise ValueError(f"Unsupported file format: {file_format}")

    def connect(self) -> None:
        """Initialize file reader."""
        self._reader.connect()
        self._is_connected = self._reader._is_connected

    def disconnect(self) -> None:
        """Close file reader."""
        self._reader.disconnect()
        self._is_connected = False

    def read(self, query: Any = None, **kwargs) -> Any:
        """Read data from file."""
        return self._reader.read(query, **kwargs)

    def write(self, data: Any, target: str, **kwargs) -> None:
        """Write data to file."""
        self._reader.write(data, target, **kwargs)

    def get_metrics(self) -> Dict[str, Any]:
        """Get reader metrics."""
        return self._reader.get_metrics()

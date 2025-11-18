"""
Data Transformer FSA - Format Handlers

This module implements handlers for different data formats including JSON, XML, CSV,
Parquet, Avro, Protocol Buffers, and YAML.
"""

import csv
import io
import json
import re
from typing import Any, Dict, Iterator, List, Optional, Union

try:
    import yaml
except ImportError:
    yaml = None

try:
    from lxml import etree
except ImportError:
    try:
        import xml.etree.ElementTree as etree
    except ImportError:
        etree = None

try:
    import pandas as pd
except ImportError:
    pd = None

try:
    import pyarrow as pa
    import pyarrow.parquet as pq
except ImportError:
    pa = None
    pq = None

try:
    import avro.schema
    import avro.io
    import avro.datafile
except ImportError:
    avro = None

from .exceptions import InvalidFormatError, UnsupportedFormatError
from .types import (
    AvroConfig,
    CSVConfig,
    DataFormat,
    ParquetConfig,
    XMLConfig,
)


class BaseFormatHandler:
    """Base class for all format handlers."""

    def __init__(self, format_type: DataFormat):
        self.format_type = format_type

    def read(self, data: Union[str, bytes], **kwargs) -> Any:
        """Read data from the format."""
        raise NotImplementedError("Subclasses must implement read()")

    def write(self, data: Any, **kwargs) -> Union[str, bytes]:
        """Write data to the format."""
        raise NotImplementedError("Subclasses must implement write()")

    def validate(self, data: Union[str, bytes]) -> bool:
        """Validate if data is in the correct format."""
        raise NotImplementedError("Subclasses must implement validate()")


class JSONTransformer(BaseFormatHandler):
    """Handler for JSON format with nested object manipulation and JSONPath queries."""

    def __init__(self):
        super().__init__(DataFormat.JSON)

    def read(self, data: Union[str, bytes], **kwargs) -> Any:
        """
        Read JSON data.

        Args:
            data: JSON string or bytes
            **kwargs: Additional options (e.g., strict, object_hook)

        Returns:
            Parsed JSON object (dict, list, or primitive)

        Raises:
            InvalidFormatError: If JSON is malformed
        """
        try:
            if isinstance(data, bytes):
                data = data.decode("utf-8")
            return json.loads(data, **kwargs)
        except json.JSONDecodeError as e:
            raise InvalidFormatError("json", f"Invalid JSON: {str(e)}")

    def write(self, data: Any, **kwargs) -> str:
        """
        Write data to JSON format.

        Args:
            data: Python object to serialize
            **kwargs: Additional options (e.g., indent, ensure_ascii)

        Returns:
            JSON string
        """
        indent = kwargs.pop("indent", 2)
        ensure_ascii = kwargs.pop("ensure_ascii", False)
        return json.dumps(data, indent=indent, ensure_ascii=ensure_ascii, **kwargs)

    def validate(self, data: Union[str, bytes]) -> bool:
        """Validate JSON format."""
        try:
            self.read(data)
            return True
        except InvalidFormatError:
            return False

    def query(self, data: Any, path: str) -> List[Any]:
        """
        Query JSON using JSONPath-like syntax.

        Simplified JSONPath implementation supporting:
        - $.field - root field access
        - $.field.nested - nested field access
        - $[0] - array index access
        - $.field[*] - array wildcard

        Args:
            data: JSON data structure
            path: JSONPath query string

        Returns:
            List of matching values
        """
        if not path.startswith("$"):
            path = "$." + path

        current = [data]
        parts = path[1:].split(".") if path.startswith("$.") else [path[1:]]

        for part in parts:
            if not part:
                continue

            next_values = []
            for value in current:
                # Handle array index or wildcard
                if "[" in part:
                    field, index_part = part.split("[", 1)
                    index_part = index_part.rstrip("]")

                    # Get field first if specified
                    if field:
                        if isinstance(value, dict) and field in value:
                            value = value[field]
                        else:
                            continue

                    # Handle array access
                    if isinstance(value, list):
                        if index_part == "*":
                            next_values.extend(value)
                        else:
                            try:
                                idx = int(index_part)
                                if -len(value) <= idx < len(value):
                                    next_values.append(value[idx])
                            except (ValueError, IndexError):
                                pass
                else:
                    # Simple field access
                    if isinstance(value, dict) and part in value:
                        next_values.append(value[part])

            current = next_values

        return current

    def set_value(self, data: Dict, path: str, value: Any) -> Dict:
        """
        Set a value at a JSONPath.

        Args:
            data: JSON data structure
            path: JSONPath to set
            value: Value to set

        Returns:
            Modified data structure
        """
        if not path.startswith("$"):
            path = "$." + path

        parts = path[1:].split(".") if path.startswith("$.") else [path[1:]]
        parts = [p for p in parts if p]

        current = data
        for i, part in enumerate(parts[:-1]):
            if part not in current:
                current[part] = {}
            current = current[part]

        current[parts[-1]] = value
        return data

    def flatten(self, data: Dict, parent_key: str = "", separator: str = ".") -> Dict:
        """
        Flatten nested JSON structure.

        Args:
            data: Nested dictionary
            parent_key: Parent key prefix
            separator: Separator for flattened keys

        Returns:
            Flattened dictionary
        """
        items = []
        for key, value in data.items():
            new_key = f"{parent_key}{separator}{key}" if parent_key else key
            if isinstance(value, dict):
                items.extend(self.flatten(value, new_key, separator).items())
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        items.extend(self.flatten(item, f"{new_key}[{i}]", separator).items())
                    else:
                        items.append((f"{new_key}[{i}]", item))
            else:
                items.append((new_key, value))
        return dict(items)

    def unflatten(self, data: Dict, separator: str = ".") -> Dict:
        """
        Unflatten a flattened JSON structure.

        Args:
            data: Flattened dictionary
            separator: Separator used in flattened keys

        Returns:
            Nested dictionary
        """
        result = {}
        for key, value in data.items():
            parts = key.split(separator)
            current = result
            for part in parts[:-1]:
                # Handle array indices
                if "[" in part:
                    field, index = part.split("[", 1)
                    index = int(index.rstrip("]"))
                    if field not in current:
                        current[field] = []
                    while len(current[field]) <= index:
                        current[field].append({})
                    current = current[field][index]
                else:
                    if part not in current:
                        current[part] = {}
                    current = current[part]

            current[parts[-1]] = value
        return result


class XMLTransformer(BaseFormatHandler):
    """Handler for XML format with XPath support."""

    def __init__(self, config: Optional[XMLConfig] = None):
        super().__init__(DataFormat.XML)
        self.config = config or XMLConfig()

        if etree is None:
            raise UnsupportedFormatError("xml", ["json", "csv", "yaml"])

    def read(self, data: Union[str, bytes], **kwargs) -> Dict:
        """
        Read XML data and convert to dictionary.

        Args:
            data: XML string or bytes

        Returns:
            Dictionary representation of XML

        Raises:
            InvalidFormatError: If XML is malformed
        """
        try:
            if isinstance(data, str):
                data = data.encode(self.config.encoding)

            root = etree.fromstring(data)
            return self._element_to_dict(root)
        except etree.XMLSyntaxError as e:
            raise InvalidFormatError("xml", f"Invalid XML: {str(e)}")

    def write(self, data: Any, **kwargs) -> str:
        """
        Write data to XML format.

        Args:
            data: Dictionary or list to convert to XML

        Returns:
            XML string
        """
        root_name = kwargs.get("root_element", self.config.root_element)
        root = self._dict_to_element(data, root_name)

        return etree.tostring(
            root,
            encoding=self.config.encoding,
            pretty_print=self.config.pretty_print,
        ).decode(self.config.encoding)

    def validate(self, data: Union[str, bytes]) -> bool:
        """Validate XML format."""
        try:
            self.read(data)
            return True
        except InvalidFormatError:
            return False

    def _element_to_dict(self, element) -> Dict:
        """Convert XML element to dictionary."""
        result = {}

        # Add attributes
        if element.attrib:
            result["@attributes"] = dict(element.attrib)

        # Add text content
        if element.text and element.text.strip():
            if len(element) == 0:  # No children, just text
                return element.text.strip()
            result["@text"] = element.text.strip()

        # Add children
        for child in element:
            child_data = self._element_to_dict(child)
            tag = child.tag

            if tag in result:
                # Convert to list if multiple children with same tag
                if not isinstance(result[tag], list):
                    result[tag] = [result[tag]]
                result[tag].append(child_data)
            else:
                result[tag] = child_data

        return result if result else element.text

    def _dict_to_element(self, data: Any, tag: str) -> Any:
        """Convert dictionary to XML element."""
        element = etree.Element(tag)

        if isinstance(data, dict):
            # Handle attributes
            if "@attributes" in data:
                for key, value in data["@attributes"].items():
                    element.set(key, str(value))

            # Handle text content
            if "@text" in data:
                element.text = str(data["@text"])

            # Handle children
            for key, value in data.items():
                if key.startswith("@"):
                    continue

                if isinstance(value, list):
                    for item in value:
                        child = self._dict_to_element(item, key)
                        element.append(child)
                else:
                    child = self._dict_to_element(value, key)
                    element.append(child)
        else:
            element.text = str(data)

        return element

    def xpath_query(self, data: Union[str, bytes], xpath: str) -> List[Any]:
        """
        Query XML using XPath.

        Args:
            data: XML data
            xpath: XPath query string

        Returns:
            List of matching elements as dictionaries
        """
        if isinstance(data, str):
            data = data.encode(self.config.encoding)

        root = etree.fromstring(data)
        results = root.xpath(xpath, namespaces=self.config.namespaces)

        return [
            self._element_to_dict(elem) if hasattr(elem, "tag") else elem for elem in results
        ]


class CSVTransformer(BaseFormatHandler):
    """Handler for CSV format with delimiter handling and header detection."""

    def __init__(self, config: Optional[CSVConfig] = None):
        super().__init__(DataFormat.CSV)
        self.config = config or CSVConfig()

    def read(self, data: Union[str, bytes], **kwargs) -> List[Dict]:
        """
        Read CSV data.

        Args:
            data: CSV string or bytes

        Returns:
            List of dictionaries representing rows

        Raises:
            InvalidFormatError: If CSV is malformed
        """
        try:
            if isinstance(data, bytes):
                data = data.decode(self.config.encoding)

            # Skip initial rows if configured
            lines = data.split("\n")
            if self.config.skip_rows > 0:
                lines = lines[self.config.skip_rows :]
                data = "\n".join(lines)

            reader = csv.DictReader(
                io.StringIO(data),
                delimiter=self.config.delimiter,
                quotechar=self.config.quote_char,
                escapechar=self.config.escape_char,
            )

            result = []
            for row in reader:
                # Convert null values
                processed_row = {}
                for key, value in row.items():
                    if value in self.config.null_values:
                        processed_row[key] = None
                    else:
                        processed_row[key] = value
                result.append(processed_row)

            return result
        except csv.Error as e:
            raise InvalidFormatError("csv", f"Invalid CSV: {str(e)}")

    def write(self, data: List[Dict], **kwargs) -> str:
        """
        Write data to CSV format.

        Args:
            data: List of dictionaries

        Returns:
            CSV string
        """
        if not data:
            return ""

        output = io.StringIO()
        fieldnames = kwargs.get("fieldnames", list(data[0].keys()))

        writer = csv.DictWriter(
            output,
            fieldnames=fieldnames,
            delimiter=self.config.delimiter,
            quotechar=self.config.quote_char,
            escapechar=self.config.escape_char,
        )

        if self.config.has_header:
            writer.writeheader()

        writer.writerows(data)
        return output.getvalue()

    def validate(self, data: Union[str, bytes]) -> bool:
        """Validate CSV format."""
        try:
            self.read(data)
            return True
        except InvalidFormatError:
            return False

    def detect_delimiter(self, data: str, sample_size: int = 1024) -> str:
        """
        Auto-detect CSV delimiter.

        Args:
            data: CSV string
            sample_size: Number of bytes to sample

        Returns:
            Detected delimiter
        """
        sample = data[:sample_size]
        sniffer = csv.Sniffer()
        try:
            dialect = sniffer.sniff(sample)
            return dialect.delimiter
        except csv.Error:
            return self.config.delimiter

    def infer_types(self, data: List[Dict]) -> Dict[str, type]:
        """
        Infer column types from data.

        Args:
            data: List of dictionaries

        Returns:
            Dictionary mapping column names to inferred types
        """
        if not data:
            return {}

        type_map = {}
        for key in data[0].keys():
            values = [row.get(key) for row in data if row.get(key) is not None]

            if not values:
                type_map[key] = str
                continue

            # Try to infer type
            all_int = all(self._is_int(v) for v in values)
            all_float = all(self._is_float(v) for v in values)
            all_bool = all(self._is_bool(v) for v in values)

            if all_bool:
                type_map[key] = bool
            elif all_int:
                type_map[key] = int
            elif all_float:
                type_map[key] = float
            else:
                type_map[key] = str

        return type_map

    @staticmethod
    def _is_int(value: Any) -> bool:
        """Check if value can be converted to int."""
        try:
            int(value)
            return "." not in str(value)
        except (ValueError, TypeError):
            return False

    @staticmethod
    def _is_float(value: Any) -> bool:
        """Check if value can be converted to float."""
        try:
            float(value)
            return True
        except (ValueError, TypeError):
            return False

    @staticmethod
    def _is_bool(value: Any) -> bool:
        """Check if value represents a boolean."""
        return str(value).lower() in ("true", "false", "yes", "no", "1", "0")


class ParquetTransformer(BaseFormatHandler):
    """Handler for Parquet format with columnar operations."""

    def __init__(self, config: Optional[ParquetConfig] = None):
        super().__init__(DataFormat.PARQUET)
        self.config = config or ParquetConfig()

        if pa is None or pq is None:
            raise UnsupportedFormatError("parquet", ["json", "csv"])

    def read(self, data: bytes, **kwargs) -> List[Dict]:
        """
        Read Parquet data.

        Args:
            data: Parquet bytes

        Returns:
            List of dictionaries

        Raises:
            InvalidFormatError: If Parquet is malformed
        """
        try:
            table = pq.read_table(io.BytesIO(data))
            return table.to_pydict()
        except Exception as e:
            raise InvalidFormatError("parquet", f"Invalid Parquet: {str(e)}")

    def write(self, data: Union[List[Dict], Dict], **kwargs) -> bytes:
        """
        Write data to Parquet format.

        Args:
            data: List of dictionaries or dict of lists

        Returns:
            Parquet bytes
        """
        # Convert list of dicts to dict of lists if needed
        if isinstance(data, list) and data:
            dict_data = {}
            keys = data[0].keys()
            for key in keys:
                dict_data[key] = [row.get(key) for row in data]
            data = dict_data

        table = pa.Table.from_pydict(data)

        output = io.BytesIO()
        pq.write_table(
            table,
            output,
            compression=self.config.compression,
            version=self.config.version,
            use_dictionary=self.config.use_dictionary,
        )

        return output.getvalue()

    def validate(self, data: bytes) -> bool:
        """Validate Parquet format."""
        try:
            self.read(data)
            return True
        except InvalidFormatError:
            return False


class AvroTransformer(BaseFormatHandler):
    """Handler for Avro format with schema evolution."""

    def __init__(self, config: Optional[AvroConfig] = None):
        super().__init__(DataFormat.AVRO)
        self.config = config or AvroConfig()

        if avro is None:
            raise UnsupportedFormatError("avro", ["json", "csv"])

    def read(self, data: bytes, schema: Optional[Dict] = None, **kwargs) -> List[Dict]:
        """
        Read Avro data.

        Args:
            data: Avro bytes
            schema: Optional Avro schema

        Returns:
            List of dictionaries

        Raises:
            InvalidFormatError: If Avro is malformed
        """
        try:
            bytes_reader = io.BytesIO(data)
            decoder = avro.io.BinaryDecoder(bytes_reader)

            if schema:
                reader_schema = avro.schema.parse(json.dumps(schema))
                reader = avro.io.DatumReader(reader_schema)
            else:
                # Try to read with datafile (includes schema)
                bytes_reader.seek(0)
                datafile_reader = avro.datafile.DataFileReader(bytes_reader, avro.io.DatumReader())
                return list(datafile_reader)

            records = []
            while True:
                try:
                    record = reader.read(decoder)
                    records.append(record)
                except:
                    break

            return records
        except Exception as e:
            raise InvalidFormatError("avro", f"Invalid Avro: {str(e)}")

    def write(self, data: List[Dict], schema: Dict, **kwargs) -> bytes:
        """
        Write data to Avro format.

        Args:
            data: List of dictionaries
            schema: Avro schema

        Returns:
            Avro bytes
        """
        output = io.BytesIO()
        avro_schema = avro.schema.parse(json.dumps(schema))

        writer = avro.datafile.DataFileWriter(
            output, avro.io.DatumWriter(), avro_schema, codec=self.config.codec
        )

        for record in data:
            writer.append(record)

        writer.close()
        return output.getvalue()

    def validate(self, data: bytes) -> bool:
        """Validate Avro format."""
        try:
            self.read(data)
            return True
        except InvalidFormatError:
            return False


class YAMLTransformer(BaseFormatHandler):
    """Handler for YAML format."""

    def __init__(self):
        super().__init__(DataFormat.YAML)

        if yaml is None:
            raise UnsupportedFormatError("yaml", ["json", "csv"])

    def read(self, data: Union[str, bytes], **kwargs) -> Any:
        """
        Read YAML data.

        Args:
            data: YAML string or bytes

        Returns:
            Parsed YAML object

        Raises:
            InvalidFormatError: If YAML is malformed
        """
        try:
            if isinstance(data, bytes):
                data = data.decode("utf-8")
            return yaml.safe_load(data)
        except yaml.YAMLError as e:
            raise InvalidFormatError("yaml", f"Invalid YAML: {str(e)}")

    def write(self, data: Any, **kwargs) -> str:
        """
        Write data to YAML format.

        Args:
            data: Python object to serialize

        Returns:
            YAML string
        """
        return yaml.dump(data, default_flow_style=False, allow_unicode=True, **kwargs)

    def validate(self, data: Union[str, bytes]) -> bool:
        """Validate YAML format."""
        try:
            self.read(data)
            return True
        except InvalidFormatError:
            return False


class FormatHandlerRegistry:
    """Registry for format handlers."""

    def __init__(self):
        self._handlers: Dict[DataFormat, BaseFormatHandler] = {}
        self._register_default_handlers()

    def _register_default_handlers(self):
        """Register default format handlers."""
        self.register(DataFormat.JSON, JSONTransformer())

        try:
            self.register(DataFormat.XML, XMLTransformer())
        except UnsupportedFormatError:
            pass

        self.register(DataFormat.CSV, CSVTransformer())

        try:
            self.register(DataFormat.PARQUET, ParquetTransformer())
        except UnsupportedFormatError:
            pass

        try:
            self.register(DataFormat.AVRO, AvroTransformer())
        except UnsupportedFormatError:
            pass

        try:
            self.register(DataFormat.YAML, YAMLTransformer())
        except UnsupportedFormatError:
            pass

    def register(self, format_type: DataFormat, handler: BaseFormatHandler):
        """Register a format handler."""
        self._handlers[format_type] = handler

    def get_handler(self, format_type: DataFormat) -> BaseFormatHandler:
        """Get a format handler."""
        if format_type not in self._handlers:
            raise UnsupportedFormatError(
                format_type.value, [f.value for f in self._handlers.keys()]
            )
        return self._handlers[format_type]

    def get_supported_formats(self) -> List[DataFormat]:
        """Get list of supported formats."""
        return list(self._handlers.keys())

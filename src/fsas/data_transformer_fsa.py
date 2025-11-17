"""
Data Transformer FSA - Handles data transformation and format conversion between FSAs.

Supports transformations between JSON, CSV, XML, YAML, strings, bytes, and FSA formats.
"""

from typing import Any, Callable, Dict, List, Optional, Tuple, Union
import json
import csv
import io
import xml.etree.ElementTree as ET
from xml.dom import minidom
import yaml


class DataTransformerFSA:
    """FSA for transforming data between different formats with validation and chaining support."""

    def __init__(self):
        """Initialize the DataTransformerFSA with built-in transformers."""
        self._transformers: Dict[Tuple[str, str], Callable] = {}
        self._register_builtin_transformers()

    def _register_builtin_transformers(self):
        """Register all built-in format transformers."""
        # JSON transformations
        self.register_transformer("json", "dict", self._json_to_dict)
        self.register_transformer("dict", "json", self._dict_to_json)

        # CSV transformations
        self.register_transformer("csv", "list", self._csv_to_list)
        self.register_transformer("list", "csv", self._list_to_csv)

        # XML transformations
        self.register_transformer("xml", "dict", self._xml_to_dict)
        self.register_transformer("dict", "xml", self._dict_to_xml)

        # YAML transformations
        self.register_transformer("yaml", "dict", self._yaml_to_dict)
        self.register_transformer("dict", "yaml", self._dict_to_yaml)

        # String/Bytes transformations
        self.register_transformer("string", "bytes", self._string_to_bytes)
        self.register_transformer("bytes", "string", self._bytes_to_string)

        # FSA format transformations
        self.register_transformer("fsa_output", "fsa_input", self._fsa_output_to_input)
        self.register_transformer("fsa_input", "fsa_output", self._fsa_input_to_output)

    def transform_data(
        self,
        source_data: Any,
        source_format: str,
        target_format: str,
        transformation_rules: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Transform data from source format to target format.

        Args:
            source_data: The data to transform
            source_format: Format of the source data (e.g., 'json', 'csv', 'xml')
            target_format: Desired target format
            transformation_rules: Optional rules to apply during transformation

        Returns:
            Transformed data in target format

        Raises:
            ValueError: If transformation is not supported or data is invalid
        """
        if transformation_rules is None:
            transformation_rules = {}

        # Normalize format names
        source_format = source_format.lower()
        target_format = target_format.lower()

        # Check if direct transformation exists
        transformer_key = (source_format, target_format)
        if transformer_key not in self._transformers:
            raise ValueError(
                f"No transformer registered for {source_format} -> {target_format}. "
                f"Available transformations: {self.get_available_transformations()}"
            )

        try:
            transformer = self._transformers[transformer_key]
            return transformer(source_data, transformation_rules)
        except Exception as e:
            raise ValueError(
                f"Transformation failed from {source_format} to {target_format}: {str(e)}"
            ) from e

    def register_transformer(
        self,
        source_format: str,
        target_format: str,
        transformer_func: Callable[[Any, Dict[str, Any]], Any]
    ):
        """
        Register a custom transformer function.

        Args:
            source_format: Source format identifier
            target_format: Target format identifier
            transformer_func: Function that transforms data, signature: (data, rules) -> transformed_data
        """
        source_format = source_format.lower()
        target_format = target_format.lower()

        if not callable(transformer_func):
            raise ValueError("transformer_func must be callable")

        self._transformers[(source_format, target_format)] = transformer_func

    def validate_format(self, data: Any, format_spec: Dict[str, Any]) -> bool:
        """
        Validate data against a format specification.

        Args:
            data: Data to validate
            format_spec: Specification defining the expected format
                Example: {"type": "dict", "required_keys": ["name", "age"]}

        Returns:
            True if data matches format specification, False otherwise
        """
        try:
            data_type = format_spec.get("type")

            if data_type == "dict":
                if not isinstance(data, dict):
                    return False
                required_keys = format_spec.get("required_keys", [])
                return all(key in data for key in required_keys)

            elif data_type == "list":
                if not isinstance(data, list):
                    return False
                if "min_length" in format_spec and len(data) < format_spec["min_length"]:
                    return False
                if "max_length" in format_spec and len(data) > format_spec["max_length"]:
                    return False
                return True

            elif data_type == "string":
                if not isinstance(data, str):
                    return False
                if "pattern" in format_spec:
                    import re
                    return bool(re.match(format_spec["pattern"], data))
                return True

            elif data_type == "json":
                try:
                    if isinstance(data, str):
                        json.loads(data)
                    return True
                except:
                    return False

            elif data_type == "xml":
                if isinstance(data, str):
                    try:
                        ET.fromstring(data)
                        return True
                    except:
                        return False
                return isinstance(data, ET.Element)

            elif data_type == "csv":
                if isinstance(data, str):
                    try:
                        csv.reader(io.StringIO(data))
                        return True
                    except:
                        return False
                return True

            else:
                # Generic type checking
                expected_type = format_spec.get("python_type")
                if expected_type:
                    return isinstance(data, expected_type)

            return True

        except Exception:
            return False

    def chain_transformations(
        self,
        data: Any,
        transformation_pipeline: List[Tuple[str, str, Optional[Dict[str, Any]]]]
    ) -> Any:
        """
        Chain multiple transformations in sequence.

        Args:
            data: Initial data to transform
            transformation_pipeline: List of (source_format, target_format, rules) tuples

        Returns:
            Final transformed data after all pipeline steps

        Raises:
            ValueError: If any transformation in the pipeline fails
        """
        if not transformation_pipeline:
            return data

        current_data = data

        for i, step in enumerate(transformation_pipeline):
            if len(step) == 2:
                source_format, target_format = step
                rules = None
            elif len(step) == 3:
                source_format, target_format, rules = step
            else:
                raise ValueError(
                    f"Invalid pipeline step {i}: expected (source, target) or "
                    f"(source, target, rules), got {step}"
                )

            try:
                current_data = self.transform_data(
                    current_data, source_format, target_format, rules
                )
            except Exception as e:
                raise ValueError(
                    f"Pipeline failed at step {i} ({source_format} -> {target_format}): {str(e)}"
                ) from e

        return current_data

    def get_available_transformations(self) -> List[Tuple[str, str]]:
        """
        Get list of all available format transformations.

        Returns:
            List of (source_format, target_format) tuples
        """
        return sorted(list(self._transformers.keys()))

    # Built-in transformer implementations

    def _json_to_dict(self, data: Any, rules: Dict[str, Any]) -> Dict:
        """Transform JSON string to dictionary."""
        if isinstance(data, dict):
            return data
        if isinstance(data, str):
            return json.loads(data)
        raise ValueError(f"Cannot convert {type(data)} to dict from JSON")

    def _dict_to_json(self, data: Dict, rules: Dict[str, Any]) -> str:
        """Transform dictionary to JSON string."""
        indent = rules.get("indent", 2)
        return json.dumps(data, indent=indent)

    def _csv_to_list(self, data: Any, rules: Dict[str, Any]) -> List[Dict]:
        """Transform CSV string to list of dictionaries."""
        if isinstance(data, list):
            return data

        delimiter = rules.get("delimiter", ",")
        has_header = rules.get("has_header", True)

        if isinstance(data, str):
            reader = csv.DictReader(io.StringIO(data), delimiter=delimiter)
            if has_header:
                return list(reader)
            else:
                # If no header, create generic keys
                lines = data.strip().split('\n')
                result = []
                for line in lines:
                    values = line.split(delimiter)
                    result.append({f"col_{i}": val for i, val in enumerate(values)})
                return result

        raise ValueError(f"Cannot convert {type(data)} to list from CSV")

    def _list_to_csv(self, data: List[Dict], rules: Dict[str, Any]) -> str:
        """Transform list of dictionaries to CSV string."""
        if not data:
            return ""

        delimiter = rules.get("delimiter", ",")
        include_header = rules.get("include_header", True)

        output = io.StringIO()

        if isinstance(data[0], dict):
            fieldnames = rules.get("fieldnames", list(data[0].keys()))
            writer = csv.DictWriter(output, fieldnames=fieldnames, delimiter=delimiter)

            if include_header:
                writer.writeheader()

            for row in data:
                writer.writerow(row)
        else:
            writer = csv.writer(output, delimiter=delimiter)
            for row in data:
                writer.writerow(row if isinstance(row, (list, tuple)) else [row])

        return output.getvalue()

    def _xml_to_dict(self, data: Any, rules: Dict[str, Any]) -> Dict:
        """Transform XML string/element to dictionary."""
        if isinstance(data, dict):
            return data

        if isinstance(data, str):
            root = ET.fromstring(data)
        elif isinstance(data, ET.Element):
            root = data
        else:
            raise ValueError(f"Cannot convert {type(data)} to dict from XML")

        def element_to_dict(element):
            result = {}

            # Add attributes
            if element.attrib:
                result["@attributes"] = element.attrib

            # Add text content
            if element.text and element.text.strip():
                result["@text"] = element.text.strip()

            # Add children
            for child in element:
                child_dict = element_to_dict(child)
                if child.tag in result:
                    # Multiple children with same tag -> convert to list
                    if not isinstance(result[child.tag], list):
                        result[child.tag] = [result[child.tag]]
                    result[child.tag].append(child_dict)
                else:
                    result[child.tag] = child_dict

            # If only text, return text directly
            if len(result) == 1 and "@text" in result:
                return result["@text"]

            return result

        return {root.tag: element_to_dict(root)}

    def _dict_to_xml(self, data: Dict, rules: Dict[str, Any]) -> str:
        """Transform dictionary to XML string."""
        root_tag = rules.get("root_tag", "root")
        pretty_print = rules.get("pretty_print", True)

        def dict_to_element(tag, value):
            elem = ET.Element(tag)

            if isinstance(value, dict):
                # Handle attributes
                if "@attributes" in value:
                    elem.attrib.update(value["@attributes"])

                # Handle text content
                if "@text" in value:
                    elem.text = str(value["@text"])

                # Handle child elements
                for key, val in value.items():
                    if key not in ["@attributes", "@text"]:
                        if isinstance(val, list):
                            for item in val:
                                elem.append(dict_to_element(key, item))
                        else:
                            elem.append(dict_to_element(key, val))
            else:
                elem.text = str(value)

            return elem

        # Handle single root or wrapped data
        if len(data) == 1:
            tag, value = list(data.items())[0]
            root = dict_to_element(tag, value)
        else:
            root = dict_to_element(root_tag, data)

        xml_str = ET.tostring(root, encoding='unicode')

        if pretty_print:
            dom = minidom.parseString(xml_str)
            return dom.toprettyxml(indent="  ")

        return xml_str

    def _yaml_to_dict(self, data: Any, rules: Dict[str, Any]) -> Dict:
        """Transform YAML string to dictionary."""
        if isinstance(data, dict):
            return data
        if isinstance(data, str):
            return yaml.safe_load(data)
        raise ValueError(f"Cannot convert {type(data)} to dict from YAML")

    def _dict_to_yaml(self, data: Dict, rules: Dict[str, Any]) -> str:
        """Transform dictionary to YAML string."""
        return yaml.dump(data, default_flow_style=False)

    def _string_to_bytes(self, data: Any, rules: Dict[str, Any]) -> bytes:
        """Transform string to bytes."""
        if isinstance(data, bytes):
            return data
        encoding = rules.get("encoding", "utf-8")
        return data.encode(encoding)

    def _bytes_to_string(self, data: Any, rules: Dict[str, Any]) -> str:
        """Transform bytes to string."""
        if isinstance(data, str):
            return data
        encoding = rules.get("encoding", "utf-8")
        return data.decode(encoding)

    def _fsa_output_to_input(self, data: Any, rules: Dict[str, Any]) -> Dict:
        """Transform FSA output format to FSA input format."""
        if isinstance(data, dict) and "result" in data:
            # Extract result and metadata
            return {
                "data": data.get("result"),
                "metadata": {
                    "source_fsa": data.get("fsa_name", "unknown"),
                    "timestamp": data.get("timestamp"),
                    "status": data.get("status", "completed")
                }
            }
        return {"data": data, "metadata": {}}

    def _fsa_input_to_output(self, data: Any, rules: Dict[str, Any]) -> Dict:
        """Transform FSA input format to FSA output format."""
        fsa_name = rules.get("fsa_name", "data_transformer")

        if isinstance(data, dict) and "data" in data:
            return {
                "result": data["data"],
                "fsa_name": fsa_name,
                "status": "completed",
                "metadata": data.get("metadata", {})
            }

        return {
            "result": data,
            "fsa_name": fsa_name,
            "status": "completed"
        }

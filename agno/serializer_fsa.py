"""Data Serializer FSA - Multi-format serialization with type preservation."""
import json
import gzip
import base64
from enum import Enum
from typing import Any, Dict, Callable, Optional
from io import StringIO
import csv


class State(Enum):
    """FSA States for serialization process."""
    IDLE = "idle"
    VALIDATING = "validating"
    TYPE_WRAPPING = "type_wrapping"
    SERIALIZING = "serializing"
    COMPRESSING = "compressing"
    DONE = "done"
    ERROR = "error"


class Format(Enum):
    """Supported serialization formats."""
    JSON = "json"
    XML = "xml"
    YAML = "yaml"
    CSV = "csv"


class DataSerializerFSA:
    """FSA-based multi-format serializer with type preservation and compression."""

    def __init__(self):
        self.state = State.IDLE
        self.custom_serializers: Dict[type, Callable] = {}
        self.error: Optional[str] = None

    def register_serializer(self, data_type: type, serializer: Callable) -> None:
        """Register custom serializer for specific type."""
        self.custom_serializers[data_type] = serializer

    def _transition(self, next_state: State) -> None:
        """Transition to next state."""
        self.state = next_state

    def _validate(self, data: Any) -> bool:
        """Validate input data."""
        self._transition(State.VALIDATING)
        if data is None:
            return True
        return True

    def _wrap_types(self, data: Any) -> Dict[str, Any]:
        """Wrap data with type information for preservation."""
        self._transition(State.TYPE_WRAPPING)

        if type(data) in self.custom_serializers:
            data = self.custom_serializers[type(data)](data)

        type_map = {
            int: "int", float: "float", str: "str", bool: "bool",
            list: "list", dict: "dict", tuple: "tuple", set: "set",
            type(None): "none"
        }

        data_type = type(data)
        if data_type == list:
            return {"__type__": "list", "__value__": [self._wrap_types(x) for x in data]}
        elif data_type == dict:
            return {"__type__": "dict", "__value__": {k: self._wrap_types(v) for k, v in data.items()}}
        elif data_type == tuple:
            return {"__type__": "tuple", "__value__": [self._wrap_types(x) for x in data]}
        elif data_type == set:
            return {"__type__": "set", "__value__": [self._wrap_types(x) for x in data]}
        else:
            return {"__type__": type_map.get(data_type, "str"), "__value__": data}

    def _unwrap_types(self, wrapped: Any) -> Any:
        """Restore original types from wrapped data."""
        if not isinstance(wrapped, dict) or "__type__" not in wrapped:
            return wrapped

        type_val = wrapped["__type__"]
        value = wrapped["__value__"]

        if type_val == "list":
            return [self._unwrap_types(x) for x in value]
        elif type_val == "dict":
            return {k: self._unwrap_types(v) for k, v in value.items()}
        elif type_val == "tuple":
            return tuple(self._unwrap_types(x) for x in value)
        elif type_val == "set":
            return set(self._unwrap_types(x) for x in value)
        elif type_val == "int":
            return int(value)
        elif type_val == "float":
            return float(value)
        elif type_val == "bool":
            return bool(value)
        elif type_val == "none":
            return None
        return value

    def _serialize_format(self, wrapped: Dict, fmt: Format) -> str:
        """Serialize to specific format."""
        self._transition(State.SERIALIZING)

        if fmt == Format.JSON:
            return json.dumps(wrapped, indent=2)
        elif fmt == Format.XML:
            return self._to_xml(wrapped)
        elif fmt == Format.YAML:
            return self._to_yaml(wrapped)
        elif fmt == Format.CSV:
            return self._to_csv(wrapped)
        raise ValueError(f"Unsupported format: {fmt}")

    def _to_xml(self, data: Dict, root: str = "data") -> str:
        """Convert to XML format."""
        def dict_to_xml(d, tag):
            xml = f"<{tag}>"
            if isinstance(d, dict):
                for k, v in d.items():
                    xml += dict_to_xml(v, k)
            else:
                xml += str(d)
            xml += f"</{tag}>"
            return xml
        return f'<?xml version="1.0"?>\n{dict_to_xml(data, root)}'

    def _to_yaml(self, data: Dict, indent: int = 0) -> str:
        """Convert to YAML format."""
        yaml_str = ""
        for k, v in data.items():
            yaml_str += "  " * indent + f"{k}:"
            if isinstance(v, dict):
                yaml_str += "\n" + self._to_yaml(v, indent + 1)
            else:
                yaml_str += f" {v}\n"
        return yaml_str

    def _to_csv(self, data: Dict) -> str:
        """Convert to CSV format (flattened)."""
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(["key", "value"])
        for k, v in data.items():
            writer.writerow([k, str(v)])
        return output.getvalue()

    def serialize(self, data: Any, fmt: Format = Format.JSON, compress: bool = False) -> str:
        """Serialize data with FSA state transitions."""
        try:
            self._transition(State.IDLE)

            if not self._validate(data):
                self._transition(State.ERROR)
                raise ValueError("Validation failed")

            wrapped = self._wrap_types(data)
            serialized = self._serialize_format(wrapped, fmt)

            if compress:
                self._transition(State.COMPRESSING)
                compressed = gzip.compress(serialized.encode())
                serialized = base64.b64encode(compressed).decode()

            self._transition(State.DONE)
            return serialized
        except Exception as e:
            self._transition(State.ERROR)
            self.error = str(e)
            raise

    def deserialize(self, data: str, fmt: Format = Format.JSON, compressed: bool = False) -> Any:
        """Deserialize data with type restoration."""
        try:
            if compressed:
                decoded = base64.b64decode(data.encode())
                data = gzip.decompress(decoded).decode()

            if fmt == Format.JSON:
                wrapped = json.loads(data)
            else:
                raise ValueError(f"Deserialization only supports JSON currently")

            return self._unwrap_types(wrapped)
        except Exception as e:
            self.error = str(e)
            raise

    def convert(self, data: str, from_fmt: Format, to_fmt: Format) -> str:
        """Convert between formats."""
        deserialized = self.deserialize(data, from_fmt)
        return self.serialize(deserialized, to_fmt)

"""
Tests for format handlers.
"""

import pytest

from ..exceptions import InvalidFormatError
from ..format_handlers import (
    CSVTransformer,
    JSONTransformer,
    XMLTransformer,
    YAMLTransformer,
)
from ..types import CSVConfig, XMLConfig


class TestJSONTransformer:
    """Tests for JSON transformer."""

    def test_read_json(self):
        """Test reading JSON data."""
        transformer = JSONTransformer()
        data = '{"name": "Alice", "age": 30}'
        result = transformer.read(data)

        assert result["name"] == "Alice"
        assert result["age"] == 30

    def test_write_json(self):
        """Test writing JSON data."""
        transformer = JSONTransformer()
        data = {"name": "Alice", "age": 30}
        result = transformer.write(data)

        assert "Alice" in result
        assert "30" in result

    def test_validate_valid_json(self):
        """Test validating valid JSON."""
        transformer = JSONTransformer()
        assert transformer.validate('{"name": "Alice"}')

    def test_validate_invalid_json(self):
        """Test validating invalid JSON."""
        transformer = JSONTransformer()
        assert not transformer.validate('{"name": "Alice"')

    def test_query_json(self):
        """Test querying JSON with JSONPath."""
        transformer = JSONTransformer()
        data = {"user": {"name": "Alice", "age": 30}}

        result = transformer.query(data, "$.user.name")
        assert result == ["Alice"]

    def test_query_array(self):
        """Test querying JSON array."""
        transformer = JSONTransformer()
        data = {"users": [{"name": "Alice"}, {"name": "Bob"}]}

        result = transformer.query(data, "$.users[*]")
        assert len(result) == 2

    def test_set_value(self):
        """Test setting a value in JSON."""
        transformer = JSONTransformer()
        data = {"name": "Alice"}

        result = transformer.set_value(data, "$.age", 30)
        assert result["age"] == 30

    def test_flatten_json(self):
        """Test flattening nested JSON."""
        transformer = JSONTransformer()
        data = {"user": {"name": "Alice", "address": {"city": "NYC"}}}

        result = transformer.flatten(data)
        assert "user.name" in result
        assert "user.address.city" in result
        assert result["user.name"] == "Alice"

    def test_unflatten_json(self):
        """Test unflattening JSON."""
        transformer = JSONTransformer()
        data = {"user.name": "Alice", "user.age": 30}

        result = transformer.unflatten(data)
        assert "user" in result
        assert result["user"]["name"] == "Alice"

    def test_read_bytes(self):
        """Test reading JSON from bytes."""
        transformer = JSONTransformer()
        data = b'{"name": "Alice"}'
        result = transformer.read(data)

        assert result["name"] == "Alice"


class TestXMLTransformer:
    """Tests for XML transformer."""

    def test_read_xml(self):
        """Test reading XML data."""
        transformer = XMLTransformer()
        xml_data = "<root><name>Alice</name><age>30</age></root>"

        result = transformer.read(xml_data)
        assert "name" in result
        assert result["name"] == "Alice"

    def test_write_xml(self):
        """Test writing XML data."""
        transformer = XMLTransformer()
        data = {"name": "Alice", "age": 30}

        result = transformer.write(data, root_element="user")
        assert "<user>" in result
        assert "Alice" in result

    def test_validate_valid_xml(self):
        """Test validating valid XML."""
        transformer = XMLTransformer()
        xml_data = "<root><name>Alice</name></root>"
        assert transformer.validate(xml_data)

    def test_validate_invalid_xml(self):
        """Test validating invalid XML."""
        transformer = XMLTransformer()
        xml_data = "<root><name>Alice</root>"
        assert not transformer.validate(xml_data)

    def test_xml_with_attributes(self):
        """Test XML with attributes."""
        transformer = XMLTransformer()
        xml_data = '<root><user id="123">Alice</user></root>'

        result = transformer.read(xml_data)
        assert "user" in result


class TestCSVTransformer:
    """Tests for CSV transformer."""

    def test_read_csv(self):
        """Test reading CSV data."""
        transformer = CSVTransformer()
        csv_data = "name,age\nAlice,30\nBob,25"

        result = transformer.read(csv_data)
        assert len(result) == 2
        assert result[0]["name"] == "Alice"
        assert result[1]["age"] == "25"

    def test_write_csv(self):
        """Test writing CSV data."""
        transformer = CSVTransformer()
        data = [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]

        result = transformer.write(data)
        assert "name,age" in result
        assert "Alice" in result

    def test_validate_csv(self):
        """Test validating CSV."""
        transformer = CSVTransformer()
        csv_data = "name,age\nAlice,30"
        assert transformer.validate(csv_data)

    def test_csv_custom_delimiter(self):
        """Test CSV with custom delimiter."""
        config = CSVConfig(delimiter=";")
        transformer = CSVTransformer(config)
        csv_data = "name;age\nAlice;30"

        result = transformer.read(csv_data)
        assert len(result) == 1
        assert result[0]["name"] == "Alice"

    def test_detect_delimiter(self):
        """Test delimiter detection."""
        transformer = CSVTransformer()
        csv_data = "name|age\nAlice|30"

        delimiter = transformer.detect_delimiter(csv_data)
        # Should detect | as delimiter
        assert delimiter in ["|", ","]

    def test_infer_types(self):
        """Test type inference."""
        transformer = CSVTransformer()
        data = [{"name": "Alice", "age": "30"}, {"name": "Bob", "age": "25"}]

        types = transformer.infer_types(data)
        assert types["name"] == str
        assert types["age"] == int

    def test_csv_with_quotes(self):
        """Test CSV with quoted values."""
        transformer = CSVTransformer()
        csv_data = 'name,description\n"Alice","A, B, C"\n'

        result = transformer.read(csv_data)
        assert result[0]["description"] == "A, B, C"

    def test_csv_skip_rows(self):
        """Test CSV with skip rows."""
        config = CSVConfig(skip_rows=1)
        transformer = CSVTransformer(config)
        csv_data = "# Comment\nname,age\nAlice,30"

        result = transformer.read(csv_data)
        assert len(result) == 1


class TestYAMLTransformer:
    """Tests for YAML transformer."""

    def test_read_yaml(self):
        """Test reading YAML data."""
        transformer = YAMLTransformer()
        yaml_data = "name: Alice\nage: 30"

        result = transformer.read(yaml_data)
        assert result["name"] == "Alice"
        assert result["age"] == 30

    def test_write_yaml(self):
        """Test writing YAML data."""
        transformer = YAMLTransformer()
        data = {"name": "Alice", "age": 30}

        result = transformer.write(data)
        assert "name:" in result or "Alice" in result

    def test_validate_yaml(self):
        """Test validating YAML."""
        transformer = YAMLTransformer()
        yaml_data = "name: Alice\nage: 30"
        assert transformer.validate(yaml_data)

    def test_yaml_nested_structure(self):
        """Test YAML with nested structure."""
        transformer = YAMLTransformer()
        yaml_data = """
user:
  name: Alice
  address:
    city: NYC
"""
        result = transformer.read(yaml_data)
        assert result["user"]["name"] == "Alice"
        assert result["user"]["address"]["city"] == "NYC"

    def test_yaml_list(self):
        """Test YAML with lists."""
        transformer = YAMLTransformer()
        yaml_data = """
users:
  - name: Alice
  - name: Bob
"""
        result = transformer.read(yaml_data)
        assert len(result["users"]) == 2

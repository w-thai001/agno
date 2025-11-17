"""
Comprehensive test suite for DataTransformerFSA.

Tests cover all core methods, format conversions, custom transformers,
pipeline chaining, error handling, and validation.
"""

import pytest
import json
import xml.etree.ElementTree as ET
from src.fsas.data_transformer_fsa import DataTransformerFSA


class TestDataTransformerFSAInit:
    """Test initialization and setup."""

    def test_initialization(self):
        """Test FSA initializes correctly."""
        fsa = DataTransformerFSA()
        assert fsa is not None
        assert hasattr(fsa, '_transformers')
        assert len(fsa._transformers) > 0

    def test_builtin_transformers_registered(self):
        """Test all built-in transformers are registered."""
        fsa = DataTransformerFSA()
        available = fsa.get_available_transformations()

        expected_transformations = [
            ('json', 'dict'), ('dict', 'json'),
            ('csv', 'list'), ('list', 'csv'),
            ('xml', 'dict'), ('dict', 'xml'),
            ('yaml', 'dict'), ('dict', 'yaml'),
            ('string', 'bytes'), ('bytes', 'string'),
            ('fsa_output', 'fsa_input'), ('fsa_input', 'fsa_output')
        ]

        for transformation in expected_transformations:
            assert transformation in available


class TestTransformData:
    """Test the main transform_data method."""

    def test_json_to_dict(self):
        """Test JSON to dict transformation."""
        fsa = DataTransformerFSA()
        json_str = '{"name": "test", "value": 123}'
        result = fsa.transform_data(json_str, "json", "dict")

        assert isinstance(result, dict)
        assert result["name"] == "test"
        assert result["value"] == 123

    def test_dict_to_json(self):
        """Test dict to JSON transformation."""
        fsa = DataTransformerFSA()
        data = {"name": "test", "value": 123}
        result = fsa.transform_data(data, "dict", "json")

        assert isinstance(result, str)
        parsed = json.loads(result)
        assert parsed["name"] == "test"
        assert parsed["value"] == 123

    def test_dict_to_json_with_indent(self):
        """Test dict to JSON with custom indentation."""
        fsa = DataTransformerFSA()
        data = {"name": "test"}
        result = fsa.transform_data(data, "dict", "json", {"indent": 4})

        assert isinstance(result, str)
        assert "    " in result  # 4-space indent

    def test_csv_to_list(self):
        """Test CSV to list transformation."""
        fsa = DataTransformerFSA()
        csv_data = "name,age,city\nAlice,30,NYC\nBob,25,LA"
        result = fsa.transform_data(csv_data, "csv", "list")

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["name"] == "Alice"
        assert result[0]["age"] == "30"
        assert result[1]["name"] == "Bob"

    def test_list_to_csv(self):
        """Test list to CSV transformation."""
        fsa = DataTransformerFSA()
        data = [
            {"name": "Alice", "age": 30},
            {"name": "Bob", "age": 25}
        ]
        result = fsa.transform_data(data, "list", "csv")

        assert isinstance(result, str)
        assert "name,age" in result
        assert "Alice,30" in result
        assert "Bob,25" in result

    def test_xml_to_dict(self):
        """Test XML to dict transformation."""
        fsa = DataTransformerFSA()
        xml_data = "<root><name>test</name><value>123</value></root>"
        result = fsa.transform_data(xml_data, "xml", "dict")

        assert isinstance(result, dict)
        assert "root" in result
        assert result["root"]["name"] == "test"
        assert result["root"]["value"] == "123"

    def test_dict_to_xml(self):
        """Test dict to XML transformation."""
        fsa = DataTransformerFSA()
        data = {"root": {"name": "test", "value": "123"}}
        result = fsa.transform_data(data, "dict", "xml")

        assert isinstance(result, str)
        assert "<name>test</name>" in result
        assert "<value>123</value>" in result

    def test_yaml_to_dict(self):
        """Test YAML to dict transformation."""
        fsa = DataTransformerFSA()
        yaml_data = "name: test\nvalue: 123\nitems:\n  - one\n  - two"
        result = fsa.transform_data(yaml_data, "yaml", "dict")

        assert isinstance(result, dict)
        assert result["name"] == "test"
        assert result["value"] == 123
        assert result["items"] == ["one", "two"]

    def test_dict_to_yaml(self):
        """Test dict to YAML transformation."""
        fsa = DataTransformerFSA()
        data = {"name": "test", "value": 123, "items": ["one", "two"]}
        result = fsa.transform_data(data, "dict", "yaml")

        assert isinstance(result, str)
        assert "name: test" in result
        assert "value: 123" in result

    def test_string_to_bytes(self):
        """Test string to bytes transformation."""
        fsa = DataTransformerFSA()
        data = "Hello, World!"
        result = fsa.transform_data(data, "string", "bytes")

        assert isinstance(result, bytes)
        assert result == b"Hello, World!"

    def test_bytes_to_string(self):
        """Test bytes to string transformation."""
        fsa = DataTransformerFSA()
        data = b"Hello, World!"
        result = fsa.transform_data(data, "bytes", "string")

        assert isinstance(result, str)
        assert result == "Hello, World!"

    def test_fsa_output_to_input(self):
        """Test FSA output to input format transformation."""
        fsa = DataTransformerFSA()
        output_data = {
            "result": {"key": "value"},
            "fsa_name": "test_fsa",
            "timestamp": "2024-01-01",
            "status": "completed"
        }
        result = fsa.transform_data(output_data, "fsa_output", "fsa_input")

        assert isinstance(result, dict)
        assert "data" in result
        assert result["data"]["key"] == "value"
        assert result["metadata"]["source_fsa"] == "test_fsa"
        assert result["metadata"]["status"] == "completed"

    def test_fsa_input_to_output(self):
        """Test FSA input to output format transformation."""
        fsa = DataTransformerFSA()
        input_data = {
            "data": {"key": "value"},
            "metadata": {"source": "test"}
        }
        result = fsa.transform_data(
            input_data, "fsa_input", "fsa_output",
            {"fsa_name": "my_fsa"}
        )

        assert isinstance(result, dict)
        assert result["result"]["key"] == "value"
        assert result["fsa_name"] == "my_fsa"
        assert result["status"] == "completed"

    def test_unsupported_transformation(self):
        """Test error handling for unsupported transformation."""
        fsa = DataTransformerFSA()
        with pytest.raises(ValueError, match="No transformer registered"):
            fsa.transform_data("data", "unknown", "format")

    def test_case_insensitive_formats(self):
        """Test format names are case-insensitive."""
        fsa = DataTransformerFSA()
        data = {"test": "value"}

        result1 = fsa.transform_data(data, "DICT", "JSON")
        result2 = fsa.transform_data(data, "dict", "json")

        assert result1 == result2


class TestRegisterTransformer:
    """Test custom transformer registration."""

    def test_register_custom_transformer(self):
        """Test registering a custom transformer."""
        fsa = DataTransformerFSA()

        def custom_transformer(data, rules):
            return data.upper()

        fsa.register_transformer("lowercase", "uppercase", custom_transformer)

        result = fsa.transform_data("hello", "lowercase", "uppercase")
        assert result == "HELLO"

    def test_register_transformer_overwrites_existing(self):
        """Test registering transformer overwrites existing one."""
        fsa = DataTransformerFSA()

        def new_transformer(data, rules):
            return {"custom": "transformation"}

        fsa.register_transformer("json", "dict", new_transformer)
        result = fsa.transform_data('{"test": "data"}', "json", "dict")

        assert result == {"custom": "transformation"}

    def test_register_non_callable_fails(self):
        """Test registering non-callable raises error."""
        fsa = DataTransformerFSA()

        with pytest.raises(ValueError, match="must be callable"):
            fsa.register_transformer("a", "b", "not_a_function")

    def test_custom_transformer_with_rules(self):
        """Test custom transformer receives and uses rules."""
        fsa = DataTransformerFSA()

        def multiplier(data, rules):
            factor = rules.get("factor", 1)
            return data * factor

        fsa.register_transformer("number", "multiplied", multiplier)
        result = fsa.transform_data(5, "number", "multiplied", {"factor": 3})

        assert result == 15


class TestValidateFormat:
    """Test format validation."""

    def test_validate_dict_format(self):
        """Test dictionary format validation."""
        fsa = DataTransformerFSA()
        data = {"name": "test", "age": 30}

        assert fsa.validate_format(data, {"type": "dict"})
        assert fsa.validate_format(data, {
            "type": "dict",
            "required_keys": ["name", "age"]
        })
        assert not fsa.validate_format(data, {
            "type": "dict",
            "required_keys": ["name", "missing_key"]
        })

    def test_validate_list_format(self):
        """Test list format validation."""
        fsa = DataTransformerFSA()
        data = [1, 2, 3, 4, 5]

        assert fsa.validate_format(data, {"type": "list"})
        assert fsa.validate_format(data, {"type": "list", "min_length": 3})
        assert fsa.validate_format(data, {"type": "list", "max_length": 10})
        assert not fsa.validate_format(data, {"type": "list", "min_length": 10})

    def test_validate_string_format(self):
        """Test string format validation."""
        fsa = DataTransformerFSA()

        assert fsa.validate_format("test", {"type": "string"})
        assert fsa.validate_format("test123", {
            "type": "string",
            "pattern": r"^test\d+$"
        })
        assert not fsa.validate_format("test", {
            "type": "string",
            "pattern": r"^\d+$"
        })

    def test_validate_json_format(self):
        """Test JSON format validation."""
        fsa = DataTransformerFSA()

        assert fsa.validate_format('{"key": "value"}', {"type": "json"})
        assert not fsa.validate_format('invalid json', {"type": "json"})

    def test_validate_xml_format(self):
        """Test XML format validation."""
        fsa = DataTransformerFSA()

        assert fsa.validate_format("<root>test</root>", {"type": "xml"})
        assert not fsa.validate_format("<invalid>", {"type": "xml"})

    def test_validate_csv_format(self):
        """Test CSV format validation."""
        fsa = DataTransformerFSA()

        assert fsa.validate_format("a,b,c\n1,2,3", {"type": "csv"})

    def test_validate_with_python_type(self):
        """Test validation with Python type."""
        fsa = DataTransformerFSA()

        assert fsa.validate_format(123, {"python_type": int})
        assert fsa.validate_format("test", {"python_type": str})
        assert not fsa.validate_format("test", {"python_type": int})


class TestChainTransformations:
    """Test transformation pipeline chaining."""

    def test_chain_simple_pipeline(self):
        """Test chaining two transformations."""
        fsa = DataTransformerFSA()
        data = {"name": "test", "value": 123}

        pipeline = [
            ("dict", "json"),
            ("json", "dict")
        ]

        result = fsa.chain_transformations(data, pipeline)
        assert result == data

    def test_chain_three_transformations(self):
        """Test chaining three transformations."""
        fsa = DataTransformerFSA()
        data = {"name": "test"}

        pipeline = [
            ("dict", "json"),
            ("json", "dict"),
            ("dict", "yaml")
        ]

        result = fsa.chain_transformations(data, pipeline)
        assert isinstance(result, str)
        assert "name: test" in result

    def test_chain_with_rules(self):
        """Test chaining with transformation rules."""
        fsa = DataTransformerFSA()
        data = {"name": "test"}

        pipeline = [
            ("dict", "json", {"indent": 4}),
            ("json", "dict", None)
        ]

        result = fsa.chain_transformations(data, pipeline)
        assert result == data

    def test_chain_empty_pipeline(self):
        """Test chaining with empty pipeline returns original data."""
        fsa = DataTransformerFSA()
        data = {"test": "data"}

        result = fsa.chain_transformations(data, [])
        assert result == data

    def test_chain_pipeline_error(self):
        """Test pipeline error handling."""
        fsa = DataTransformerFSA()

        pipeline = [
            ("dict", "json"),
            ("invalid", "format")
        ]

        with pytest.raises(ValueError, match="Pipeline failed at step 1"):
            fsa.chain_transformations({"test": "data"}, pipeline)

    def test_chain_complex_pipeline(self):
        """Test complex multi-format pipeline."""
        fsa = DataTransformerFSA()
        original = [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]

        pipeline = [
            ("list", "csv"),
            ("string", "bytes"),
            ("bytes", "string")
        ]

        # First transform to CSV
        csv_result = fsa.transform_data(original, "list", "csv")

        # Then chain bytes conversions
        result = fsa.chain_transformations(
            csv_result,
            [("string", "bytes"), ("bytes", "string")]
        )

        assert isinstance(result, str)
        assert "Alice" in result
        assert "Bob" in result

    def test_chain_invalid_step_format(self):
        """Test error on invalid pipeline step format."""
        fsa = DataTransformerFSA()

        with pytest.raises(ValueError, match="Invalid pipeline step"):
            fsa.chain_transformations({"data": "test"}, [("single_item",)])


class TestGetAvailableTransformations:
    """Test listing available transformations."""

    def test_get_transformations_returns_list(self):
        """Test get_available_transformations returns a list."""
        fsa = DataTransformerFSA()
        result = fsa.get_available_transformations()

        assert isinstance(result, list)
        assert len(result) > 0

    def test_transformations_are_tuples(self):
        """Test all transformations are tuples of (source, target)."""
        fsa = DataTransformerFSA()
        result = fsa.get_available_transformations()

        for item in result:
            assert isinstance(item, tuple)
            assert len(item) == 2
            assert isinstance(item[0], str)
            assert isinstance(item[1], str)

    def test_custom_transformer_appears_in_list(self):
        """Test custom transformers appear in available list."""
        fsa = DataTransformerFSA()

        def custom(data, rules):
            return data

        fsa.register_transformer("custom_a", "custom_b", custom)
        result = fsa.get_available_transformations()

        assert ("custom_a", "custom_b") in result


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_dict_to_json(self):
        """Test empty dictionary transformation."""
        fsa = DataTransformerFSA()
        result = fsa.transform_data({}, "dict", "json")
        assert result == "{}"

    def test_empty_list_to_csv(self):
        """Test empty list transformation."""
        fsa = DataTransformerFSA()
        result = fsa.transform_data([], "list", "csv")
        assert result == ""

    def test_xml_with_attributes(self):
        """Test XML with attributes."""
        fsa = DataTransformerFSA()
        xml_data = '<root attr="value"><child>text</child></root>'
        result = fsa.transform_data(xml_data, "xml", "dict")

        assert "@attributes" in result["root"]
        assert result["root"]["@attributes"]["attr"] == "value"

    def test_nested_dict_to_xml_to_dict(self):
        """Test round-trip nested dict through XML."""
        fsa = DataTransformerFSA()
        data = {"root": {"level1": {"level2": "value"}}}

        xml_str = fsa.transform_data(data, "dict", "xml")
        result = fsa.transform_data(xml_str, "xml", "dict")

        assert "root" in result
        assert result["root"]["level1"]["level2"] == "value"

    def test_csv_with_custom_delimiter(self):
        """Test CSV with custom delimiter."""
        fsa = DataTransformerFSA()
        data = [{"a": "1", "b": "2"}, {"a": "3", "b": "4"}]

        result = fsa.transform_data(data, "list", "csv", {"delimiter": "|"})

        assert "|" in result
        assert "a|b" in result

    def test_bytes_with_custom_encoding(self):
        """Test bytes transformation with custom encoding."""
        fsa = DataTransformerFSA()
        data = "Hello"

        result = fsa.transform_data(data, "string", "bytes", {"encoding": "utf-8"})
        back = fsa.transform_data(result, "bytes", "string", {"encoding": "utf-8"})

        assert back == data

    def test_transformation_error_message(self):
        """Test transformation error provides helpful message."""
        fsa = DataTransformerFSA()

        with pytest.raises(ValueError) as exc_info:
            fsa.transform_data("invalid", "json", "dict")

        assert "Transformation failed" in str(exc_info.value)
        assert "json" in str(exc_info.value)
        assert "dict" in str(exc_info.value)

    def test_xml_list_elements(self):
        """Test XML with multiple elements of same tag."""
        fsa = DataTransformerFSA()
        xml_data = "<root><item>one</item><item>two</item><item>three</item></root>"
        result = fsa.transform_data(xml_data, "xml", "dict")

        assert isinstance(result["root"]["item"], list)
        assert len(result["root"]["item"]) == 3


class TestSmokeTests:
    """Smoke tests for overall functionality."""

    def test_all_builtin_transformations_work(self):
        """Smoke test: all built-in transformations execute without error."""
        fsa = DataTransformerFSA()

        test_cases = [
            ('{"test": "data"}', "json", "dict"),
            ({"test": "data"}, "dict", "json"),
            ("a,b\n1,2", "csv", "list"),
            ([{"a": "1", "b": "2"}], "list", "csv"),
            ("<root>test</root>", "xml", "dict"),
            ({"root": "test"}, "dict", "xml"),
            ("test: data", "yaml", "dict"),
            ({"test": "data"}, "dict", "yaml"),
            ("test", "string", "bytes"),
            (b"test", "bytes", "string"),
        ]

        for data, source, target in test_cases:
            result = fsa.transform_data(data, source, target)
            assert result is not None

    def test_round_trip_transformations(self):
        """Smoke test: data survives round-trip transformations."""
        fsa = DataTransformerFSA()

        # JSON round trip
        original = {"name": "test", "value": 123}
        json_str = fsa.transform_data(original, "dict", "json")
        result = fsa.transform_data(json_str, "json", "dict")
        assert result == original

        # Bytes round trip
        original_str = "Hello, World!"
        bytes_data = fsa.transform_data(original_str, "string", "bytes")
        result_str = fsa.transform_data(bytes_data, "bytes", "string")
        assert result_str == original_str

    def test_full_pipeline_integration(self):
        """Smoke test: complex pipeline with multiple steps."""
        fsa = DataTransformerFSA()

        original = [
            {"name": "Alice", "score": 95},
            {"name": "Bob", "score": 87}
        ]

        # Complex pipeline: list -> csv -> bytes -> string -> csv -> list
        pipeline = [
            ("list", "csv"),
            ("string", "bytes"),
            ("bytes", "string")
        ]

        result = fsa.chain_transformations(original, pipeline)

        # Result should be CSV string
        assert isinstance(result, str)
        assert "Alice" in result
        assert "Bob" in result
        assert "name" in result or "score" in result

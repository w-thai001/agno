"""
Quick smoke test script for DataTransformerFSA.
"""

import sys
sys.path.insert(0, '/home/user/agno')

from src.fsas.data_transformer_fsa import DataTransformerFSA


def test_initialization():
    """Test basic initialization."""
    fsa = DataTransformerFSA()
    print("✓ Initialization test passed")
    return True


def test_json_dict_conversion():
    """Test JSON to dict and back."""
    fsa = DataTransformerFSA()

    # Test JSON to dict
    json_str = '{"name": "test", "value": 123}'
    result = fsa.transform_data(json_str, "json", "dict")
    assert isinstance(result, dict)
    assert result["name"] == "test"
    assert result["value"] == 123

    # Test dict to JSON
    data = {"name": "test", "value": 123}
    result = fsa.transform_data(data, "dict", "json")
    assert isinstance(result, str)
    assert "test" in result

    print("✓ JSON/Dict conversion test passed")
    return True


def test_csv_list_conversion():
    """Test CSV to list conversion."""
    fsa = DataTransformerFSA()

    csv_data = "name,age,city\nAlice,30,NYC\nBob,25,LA"
    result = fsa.transform_data(csv_data, "csv", "list")

    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0]["name"] == "Alice"

    # Test list to CSV
    data = [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]
    result = fsa.transform_data(data, "list", "csv")
    assert isinstance(result, str)
    assert "Alice" in result

    print("✓ CSV/List conversion test passed")
    return True


def test_xml_dict_conversion():
    """Test XML to dict conversion."""
    fsa = DataTransformerFSA()

    xml_data = "<root><name>test</name><value>123</value></root>"
    result = fsa.transform_data(xml_data, "xml", "dict")

    assert isinstance(result, dict)
    assert "root" in result

    print("✓ XML/Dict conversion test passed")
    return True


def test_yaml_dict_conversion():
    """Test YAML to dict conversion."""
    fsa = DataTransformerFSA()

    yaml_data = "name: test\nvalue: 123"
    result = fsa.transform_data(yaml_data, "yaml", "dict")

    assert isinstance(result, dict)
    assert result["name"] == "test"

    print("✓ YAML/Dict conversion test passed")
    return True


def test_string_bytes_conversion():
    """Test string to bytes conversion."""
    fsa = DataTransformerFSA()

    data = "Hello, World!"
    result = fsa.transform_data(data, "string", "bytes")
    assert isinstance(result, bytes)

    back = fsa.transform_data(result, "bytes", "string")
    assert back == data

    print("✓ String/Bytes conversion test passed")
    return True


def test_custom_transformer():
    """Test custom transformer registration."""
    fsa = DataTransformerFSA()

    def uppercase_transformer(data, rules):
        return data.upper()

    fsa.register_transformer("lowercase", "uppercase", uppercase_transformer)
    result = fsa.transform_data("hello", "lowercase", "uppercase")
    assert result == "HELLO"

    print("✓ Custom transformer test passed")
    return True


def test_validation():
    """Test format validation."""
    fsa = DataTransformerFSA()

    # Test dict validation
    data = {"name": "test", "age": 30}
    assert fsa.validate_format(data, {"type": "dict"})
    assert fsa.validate_format(data, {"type": "dict", "required_keys": ["name"]})
    assert not fsa.validate_format(data, {"type": "dict", "required_keys": ["missing"]})

    # Test list validation
    list_data = [1, 2, 3]
    assert fsa.validate_format(list_data, {"type": "list", "min_length": 2})
    assert not fsa.validate_format(list_data, {"type": "list", "min_length": 5})

    print("✓ Validation test passed")
    return True


def test_pipeline():
    """Test transformation pipeline."""
    fsa = DataTransformerFSA()

    data = {"name": "test", "value": 123}
    pipeline = [
        ("dict", "json"),
        ("json", "dict"),
        ("dict", "yaml")
    ]

    result = fsa.chain_transformations(data, pipeline)
    assert isinstance(result, str)
    assert "name: test" in result

    print("✓ Pipeline test passed")
    return True


def test_fsa_formats():
    """Test FSA input/output format conversions."""
    fsa = DataTransformerFSA()

    # Test FSA output to input
    output_data = {
        "result": {"key": "value"},
        "fsa_name": "test_fsa",
        "status": "completed"
    }
    result = fsa.transform_data(output_data, "fsa_output", "fsa_input")
    assert "data" in result
    assert result["data"]["key"] == "value"

    # Test FSA input to output
    input_data = {"data": {"key": "value"}}
    result = fsa.transform_data(input_data, "fsa_input", "fsa_output", {"fsa_name": "my_fsa"})
    assert result["fsa_name"] == "my_fsa"
    assert result["result"]["key"] == "value"

    print("✓ FSA format conversion test passed")
    return True


def test_available_transformations():
    """Test getting available transformations."""
    fsa = DataTransformerFSA()

    transformations = fsa.get_available_transformations()
    assert isinstance(transformations, list)
    assert len(transformations) >= 12  # At least 12 built-in transformations

    # Check some expected transformations
    assert ("json", "dict") in transformations
    assert ("csv", "list") in transformations
    assert ("xml", "dict") in transformations

    print("✓ Available transformations test passed")
    return True


def test_error_handling():
    """Test error handling."""
    fsa = DataTransformerFSA()

    # Test unsupported transformation
    try:
        fsa.transform_data("data", "unknown", "format")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "No transformer registered" in str(e)

    # Test invalid JSON
    try:
        fsa.transform_data("invalid json", "json", "dict")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Transformation failed" in str(e)

    print("✓ Error handling test passed")
    return True


def run_all_tests():
    """Run all smoke tests."""
    print("=" * 60)
    print("Running DataTransformerFSA Smoke Tests")
    print("=" * 60)

    tests = [
        test_initialization,
        test_json_dict_conversion,
        test_csv_list_conversion,
        test_xml_dict_conversion,
        test_yaml_dict_conversion,
        test_string_bytes_conversion,
        test_custom_transformer,
        test_validation,
        test_pipeline,
        test_fsa_formats,
        test_available_transformations,
        test_error_handling,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"✗ {test.__name__} failed: {e}")
            failed += 1

    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)} tests")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

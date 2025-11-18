"""
Format Conversion Examples

This example demonstrates format conversion capabilities between different
data formats (JSON, XML, CSV, YAML).
"""

from agno.fsa import DataTransformerFSA


def main():
    transformer = DataTransformerFSA()

    print("=" * 80)
    print("Data Transformer FSA - Format Conversion Examples")
    print("=" * 80)

    # Example 1: JSON to CSV
    print("\n1. JSON to CSV Conversion")
    print("-" * 80)

    json_data = """[
        {"name": "Alice", "age": 30, "city": "NYC"},
        {"name": "Bob", "age": 25, "city": "SF"},
        {"name": "Charlie", "age": 35, "city": "LA"}
    ]"""

    csv_result = transformer.convert_format(json_data, "json", "csv")

    print("Input (JSON):")
    print(json_data)
    print("\nOutput (CSV):")
    print(csv_result)

    # Example 2: CSV to JSON
    print("\n\n2. CSV to JSON Conversion")
    print("-" * 80)

    csv_data = """name,age,city
Alice,30,NYC
Bob,25,SF
Charlie,35,LA"""

    json_result = transformer.convert_format(csv_data, "csv", "json")

    print("Input (CSV):")
    print(csv_data)
    print("\nOutput (JSON):")
    print(json_result)

    # Example 3: JSON to XML
    print("\n\n3. JSON to XML Conversion")
    print("-" * 80)

    json_data = """{
        "user": {
            "name": "Alice",
            "age": 30,
            "email": "alice@example.com"
        }
    }"""

    xml_result = transformer.convert_format(json_data, "json", "xml")

    print("Input (JSON):")
    print(json_data)
    print("\nOutput (XML):")
    print(xml_result)

    # Example 4: XML to JSON
    print("\n\n4. XML to JSON Conversion")
    print("-" * 80)

    xml_data = """<root>
        <user>
            <name>Alice</name>
            <age>30</age>
            <email>alice@example.com</email>
        </user>
    </root>"""

    json_result = transformer.convert_format(xml_data, "xml", "json")

    print("Input (XML):")
    print(xml_data)
    print("\nOutput (JSON):")
    print(json_result)

    # Example 5: JSON to YAML
    print("\n\n5. JSON to YAML Conversion")
    print("-" * 80)

    json_data = """{
        "application": "web_app",
        "version": "1.0.0",
        "settings": {
            "debug": true,
            "max_connections": 100
        }
    }"""

    yaml_result = transformer.convert_format(json_data, "json", "yaml")

    print("Input (JSON):")
    print(json_data)
    print("\nOutput (YAML):")
    print(yaml_result)

    # Example 6: YAML to JSON
    print("\n\n6. YAML to JSON Conversion")
    print("-" * 80)

    yaml_data = """application: web_app
version: 1.0.0
settings:
  debug: true
  max_connections: 100
"""

    json_result = transformer.convert_format(yaml_data, "yaml", "json")

    print("Input (YAML):")
    print(yaml_data)
    print("\nOutput (JSON):")
    print(json_result)

    # Example 7: Round-trip Conversion (JSON → CSV → JSON)
    print("\n\n7. Round-trip Conversion: JSON → CSV → JSON")
    print("-" * 80)

    original_json = '[{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]'

    print("Original JSON:")
    print(original_json)

    # Convert to CSV
    csv_intermediate = transformer.convert_format(original_json, "json", "csv")
    print("\nIntermediate CSV:")
    print(csv_intermediate)

    # Convert back to JSON
    final_json = transformer.convert_format(csv_intermediate, "csv", "json")
    print("\nFinal JSON:")
    print(final_json)

    # Example 8: Working with Supported Formats
    print("\n\n8. Supported Formats")
    print("-" * 80)

    supported = transformer.get_supported_formats()
    print("Supported formats:")
    for fmt in supported:
        print(f"  - {fmt}")

    print("\n" + "=" * 80)
    print("Format conversion examples completed successfully!")
    print("=" * 80)


if __name__ == "__main__":
    main()

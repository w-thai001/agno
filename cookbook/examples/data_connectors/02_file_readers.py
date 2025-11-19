"""
Example 2: File Readers

Demonstrates how to read and process various file formats:
- CSV files
- JSON and NDJSON
- XML files
- Parquet files
"""

from pathlib import Path
from agno.tools.data_connectors import FileReaderConnector
from agno.tools.data_connectors.transformation import TransformationPipeline
from agno.tools.data_connectors.validation import DataValidator, SchemaMapper


# Example 1: Reading CSV Files
def example_csv_reader():
    """Read and process CSV files."""
    print("=== Example 1: CSV File Reading ===\n")

    # Create sample CSV file
    sample_csv = Path("/tmp/sample_data.csv")
    sample_csv.write_text("""id,name,email,age,city
1,John Doe,john@example.com,30,New York
2,Jane Smith,jane@example.com,25,Los Angeles
3,Bob Wilson,bob@example.com,35,Chicago
4,Alice Brown,alice@example.com,28,Houston
5,Charlie Davis,charlie@example.com,42,Phoenix
""")

    # Read CSV
    reader = FileReaderConnector(sample_csv, file_format="csv")
    reader.connect()

    # Read all data
    data = reader.read()
    print(f"Read {len(data)} records from CSV")
    print(f"First record: {data[0]}")

    # Read with limit
    limited_data = reader.read(query=3)
    print(f"\nLimited read (3 records): {len(limited_data)} records")

    # Read in chunks
    print("\nReading in chunks:")
    for chunk in reader.read(chunk_size=2):
        print(f"  Chunk: {len(chunk)} records")

    reader.disconnect()

    # Transform CSV data
    pipeline = TransformationPipeline("CSVTransform")
    pipeline.add_filter(lambda x: int(x["age"]) > 25)
    pipeline.add_select_fields(["name", "email", "city"])
    pipeline.add_sort("age", reverse=True)

    transformed = pipeline.execute(data)
    print(f"\nTransformed data (age > 25):")
    for record in transformed:
        print(f"  {record}")


# Example 2: Reading JSON and NDJSON
def example_json_reader():
    """Read JSON and NDJSON files."""
    print("\n=== Example 2: JSON File Reading ===\n")

    # Create sample JSON file
    import json

    sample_json = Path("/tmp/sample_data.json")
    json_data = {
        "users": [
            {"id": 1, "name": "John", "roles": ["admin", "user"]},
            {"id": 2, "name": "Jane", "roles": ["user"]},
            {"id": 3, "name": "Bob", "roles": ["moderator", "user"]},
        ],
        "metadata": {"created": "2024-01-01", "version": "1.0"},
    }
    sample_json.write_text(json.dumps(json_data, indent=2))

    # Read JSON
    reader = FileReaderConnector(sample_json, file_format="json")
    reader.connect()

    data = reader.read()
    print(f"JSON data keys: {data.keys()}")
    print(f"Users: {len(data['users'])} users")

    reader.disconnect()

    # Create and read NDJSON
    sample_ndjson = Path("/tmp/sample_data.jsonl")
    ndjson_content = "\n".join(
        json.dumps(user) for user in [
            {"id": 1, "event": "login", "timestamp": "2024-01-01T10:00:00"},
            {"id": 2, "event": "purchase", "timestamp": "2024-01-01T11:30:00"},
            {"id": 1, "event": "logout", "timestamp": "2024-01-01T12:00:00"},
        ]
    )
    sample_ndjson.write_text(ndjson_content)

    # Read NDJSON
    ndjson_reader = FileReaderConnector(sample_ndjson, file_format="ndjson")
    ndjson_reader.connect()

    events = ndjson_reader.read()
    print(f"\nNDJSON events: {len(events)} events")
    for event in events:
        print(f"  User {event['id']}: {event['event']} at {event['timestamp']}")

    ndjson_reader.disconnect()


# Example 3: Reading XML Files
def example_xml_reader():
    """Read and parse XML files."""
    print("\n=== Example 3: XML File Reading ===\n")

    # Create sample XML file
    sample_xml = Path("/tmp/sample_data.xml")
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<catalog>
    <book id="1">
        <title>Python Programming</title>
        <author>John Doe</author>
        <price>29.99</price>
        <year>2023</year>
    </book>
    <book id="2">
        <title>Data Science Handbook</title>
        <author>Jane Smith</author>
        <price>39.99</price>
        <year>2024</year>
    </book>
    <book id="3">
        <title>Machine Learning Basics</title>
        <author>Bob Wilson</author>
        <price>34.99</price>
        <year>2023</year>
    </book>
</catalog>
"""
    sample_xml.write_text(xml_content)

    # Read XML
    reader = FileReaderConnector(sample_xml, file_format="xml")
    reader.connect()

    # Get root element
    root = reader.read()
    print(f"Root tag: {root.tag}")

    # Query specific elements
    books = reader.read(query=".//book")
    print(f"\nFound {len(books)} books:")

    for book in books:
        title = book.find("title").text
        author = book.find("author").text
        price = book.find("price").text
        print(f"  - {title} by {author} (${price})")

    # Convert to dict
    root_dict = reader.to_dict()
    print(f"\nXML as dict structure: {root_dict['tag']}")

    reader.disconnect()


# Example 4: Reading Parquet Files
def example_parquet_reader():
    """Read Parquet files (requires pyarrow)."""
    print("\n=== Example 4: Parquet File Reading ===\n")

    try:
        import pandas as pd
        import pyarrow as pa
        import pyarrow.parquet as pq

        # Create sample Parquet file
        sample_parquet = Path("/tmp/sample_data.parquet")

        df = pd.DataFrame(
            {
                "id": [1, 2, 3, 4, 5],
                "product": ["Laptop", "Mouse", "Keyboard", "Monitor", "Headphones"],
                "price": [999.99, 29.99, 79.99, 299.99, 149.99],
                "quantity": [5, 100, 50, 20, 30],
                "category": ["Electronics", "Accessories", "Accessories", "Electronics", "Accessories"],
            }
        )

        df.to_parquet(sample_parquet, index=False)

        # Read Parquet
        reader = FileReaderConnector(sample_parquet, file_format="parquet")
        reader.connect()

        # Read all columns
        data = reader.read(use_pandas=True)
        print(f"Read Parquet with {len(data)} rows and {len(data.columns)} columns")
        print(f"Columns: {list(data.columns)}")
        print(f"\nFirst 3 rows:\n{data.head(3)}")

        # Read specific columns
        subset = reader.read(query=["product", "price", "quantity"], use_pandas=True)
        print(f"\nSubset with selected columns:\n{subset.head(3)}")

        # Calculate total value
        data["total_value"] = data["price"] * data["quantity"]
        print(f"\nTotal inventory value: ${data['total_value'].sum():,.2f}")

        reader.disconnect()

    except ImportError:
        print("⚠️  PyArrow not installed. Install with: pip install pyarrow")


# Example 5: Multi-Format Data Integration
def example_multi_format_integration():
    """Integrate data from multiple file formats."""
    print("\n=== Example 5: Multi-Format Integration ===\n")

    # Prepare sample data files
    csv_path = Path("/tmp/sales_q1.csv")
    json_path = Path("/tmp/sales_q2.json")

    csv_path.write_text("""date,product,amount,region
2024-01-15,Laptop,999.99,North
2024-01-20,Mouse,29.99,South
2024-02-10,Keyboard,79.99,East
""")

    import json
    json_path.write_text(
        json.dumps(
            [
                {"date": "2024-04-05", "product": "Monitor", "amount": 299.99, "region": "West"},
                {"date": "2024-05-12", "product": "Headphones", "amount": 149.99, "region": "North"},
            ]
        )
    )

    # Read both files
    csv_reader = FileReaderConnector(csv_path)
    json_reader = FileReaderConnector(json_path)

    csv_reader.connect()
    json_reader.connect()

    q1_data = csv_reader.read()
    q2_data = json_reader.read()

    csv_reader.disconnect()
    json_reader.disconnect()

    # Combine data
    all_sales = q1_data + q2_data

    print(f"Combined sales data: {len(all_sales)} records")

    # Analyze using transformation pipeline
    from agno.tools.data_connectors.transformation import sum_agg, count_agg

    pipeline = TransformationPipeline("SalesAnalysis")
    pipeline.add_group_by("region")
    pipeline.add_aggregate({"amount": lambda x: {"total": sum_agg(x), "count": count_agg(x)}})

    analysis = pipeline.execute(all_sales)

    print("\nSales by Region:")
    for region, stats in analysis.items():
        print(f"  {region}: ${stats['amount']['total']:,.2f} ({stats['amount']['count']} sales)")


# Example 6: Schema Mapping Between Formats
def example_schema_mapping():
    """Map data between different schemas."""
    print("\n=== Example 6: Schema Mapping ===\n")

    # Source data (legacy format)
    source_data = [
        {"user_id": 1, "full_name": "John Doe", "email_addr": "john@example.com", "acc_status": "active"},
        {"user_id": 2, "full_name": "Jane Smith", "email_addr": "jane@example.com", "acc_status": "inactive"},
    ]

    # Define mapping to new format
    mapping = {
        "user_id": "id",
        "full_name": "name",
        "email_addr": "email",
        "acc_status": "status",
    }

    mapper = SchemaMapper(mapping)
    mapped_data = mapper.map(source_data)

    print("Original data:")
    print(f"  {source_data[0]}")

    print("\nMapped data:")
    print(f"  {mapped_data[0]}")

    # Write to different format
    output_json = Path("/tmp/mapped_users.json")
    import json
    output_json.write_text(json.dumps(mapped_data, indent=2))

    print(f"\n✅ Mapped data written to {output_json}")


if __name__ == "__main__":
    print("🚀 Data Connector - File Reader Examples\n")
    print("=" * 60)

    example_csv_reader()
    example_json_reader()
    example_xml_reader()
    example_parquet_reader()
    example_multi_format_integration()
    example_schema_mapping()

    print("\n" + "=" * 60)
    print("✅ Examples completed!")

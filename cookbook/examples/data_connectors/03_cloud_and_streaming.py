"""
Example 3: Cloud Storage and Streaming

Demonstrates:
- AWS S3 integration
- Google Cloud Storage
- Azure Blob Storage
- Kafka streaming
- RabbitMQ messaging
- Redis Streams
"""

from agno.tools.data_connectors import CloudStorageConnector, CloudStorageConfig
from agno.tools.data_connectors import StreamingConnector, StreamingConfig
from agno.tools.data_connectors.toolkit import DataConnectorToolkit
from agno.agent import Agent
from agno.models.openai import OpenAIChat


# Example 1: AWS S3 Integration
def example_s3_connector():
    """Working with AWS S3."""
    print("=== Example 1: AWS S3 Connector ===\n")

    # Configure S3 connection
    config = CloudStorageConfig(
        bucket_name="my-data-bucket",
        access_key="YOUR_ACCESS_KEY",
        secret_key="YOUR_SECRET_KEY",
        region="us-east-1",
    )

    connector = CloudStorageConnector(provider="s3", bucket_name="my-data-bucket", config=config)

    try:
        connector.connect()

        # List objects
        # objects = connector._connector.list_objects(prefix="data/", max_keys=10)
        # print(f"Found {len(objects)} objects in S3")

        # Read object
        # content = connector.read("data/sample.json")
        # print(f"Read object content: {content[:100]}...")

        # Write object
        # sample_data = '{"message": "Hello from Data Connector!", "timestamp": "2024-01-01T12:00:00"}'
        # connector.write(sample_data, "output/result.json", metadata={"source": "data_connector"})
        # print("✅ Wrote data to S3")

        connector.disconnect()

    except Exception as e:
        print(f"⚠️  S3 example requires valid AWS credentials: {e}")
        print("   Configure your AWS credentials to run this example")


# Example 2: Google Cloud Storage
def example_gcs_connector():
    """Working with Google Cloud Storage."""
    print("\n=== Example 2: Google Cloud Storage ===\n")

    config = CloudStorageConfig(
        bucket_name="my-gcs-bucket",
        project_id="my-project-id",
        credentials_path="/path/to/credentials.json",
    )

    connector = CloudStorageConnector(provider="gcs", bucket_name="my-gcs-bucket", config=config)

    try:
        connector.connect()

        # List blobs
        # blobs = connector._connector.list_blobs(prefix="datasets/", max_results=10)
        # print(f"Found {len(blobs)} blobs in GCS")

        # Read blob
        # content = connector.read("datasets/sample.csv")
        # print(f"Read blob content: {content[:100]}...")

        # Write blob
        # connector.write("Sample data", "output/data.txt", metadata={"type": "text"})
        # print("✅ Wrote data to GCS")

        connector.disconnect()

    except Exception as e:
        print(f"⚠️  GCS example requires valid credentials: {e}")
        print("   Configure your GCP credentials to run this example")


# Example 3: Azure Blob Storage
def example_azure_connector():
    """Working with Azure Blob Storage."""
    print("\n=== Example 3: Azure Blob Storage ===\n")

    config = CloudStorageConfig(
        account_name="mystorageaccount",
        account_key="YOUR_ACCOUNT_KEY",
    )

    connector = CloudStorageConnector(
        provider="azure", bucket_name="my-container", config=config
    )

    try:
        connector.connect()

        # List blobs
        # blobs = connector._connector.list_blobs(name_starts_with="data/")
        # print(f"Found {len(blobs)} blobs in Azure")

        # Read/write operations similar to S3/GCS
        # connector.read("data/input.json")
        # connector.write("data", "data/output.json")

        connector.disconnect()

    except Exception as e:
        print(f"⚠️  Azure example requires valid credentials: {e}")
        print("   Configure your Azure credentials to run this example")


# Example 4: Kafka Streaming
def example_kafka_streaming():
    """Working with Apache Kafka."""
    print("\n=== Example 4: Kafka Streaming ===\n")

    config = StreamingConfig(
        bootstrap_servers=["localhost:9092"],
        topic="events",
        group_id="data-connector-consumer",
        auto_offset_reset="earliest",
    )

    connector = StreamingConnector(stream_type="kafka", config=config)

    try:
        connector.connect()

        # Produce messages
        # events = [
        #     {"event": "user_login", "user_id": 123, "timestamp": "2024-01-01T10:00:00"},
        #     {"event": "page_view", "user_id": 123, "page": "/home", "timestamp": "2024-01-01T10:01:00"},
        # ]
        # connector.write(events, "events")
        # print(f"✅ Produced {len(events)} events to Kafka")

        # Consume messages
        # print("\nConsuming messages:")
        # for message in connector.read(query=5):  # Read 5 messages
        #     print(f"  Topic: {message['topic']}, Offset: {message['offset']}")
        #     print(f"  Value: {message['value']}")

        connector.disconnect()

    except Exception as e:
        print(f"⚠️  Kafka example requires running Kafka cluster: {e}")
        print("   Start Kafka locally to run this example")


# Example 5: RabbitMQ Messaging
def example_rabbitmq():
    """Working with RabbitMQ."""
    print("\n=== Example 5: RabbitMQ Messaging ===\n")

    connector = StreamingConnector(
        stream_type="rabbitmq",
        host="localhost",
        port=5672,
        username="guest",
        password="guest",
    )

    try:
        connector.connect()

        # Publish messages
        # messages = [
        #     {"order_id": 1, "product": "Laptop", "quantity": 1},
        #     {"order_id": 2, "product": "Mouse", "quantity": 2},
        # ]
        # connector.write(messages, target="orders_queue")
        # print(f"✅ Published {len(messages)} messages to RabbitMQ")

        # Consume messages
        # print("\nConsuming messages:")
        # for message in connector.read("orders_queue", max_messages=5):
        #     print(f"  Order: {message['body']}")

        connector.disconnect()

    except Exception as e:
        print(f"⚠️  RabbitMQ example requires running RabbitMQ server: {e}")
        print("   Start RabbitMQ locally to run this example")


# Example 6: Redis Streams
def example_redis_streams():
    """Working with Redis Streams."""
    print("\n=== Example 6: Redis Streams ===\n")

    connector = StreamingConnector(stream_type="redis", host="localhost", port=6379, db=0)

    try:
        connector.connect()

        # Write to stream
        # events = [
        #     {"sensor_id": "temp_01", "value": 23.5, "unit": "celsius"},
        #     {"sensor_id": "temp_02", "value": 22.1, "unit": "celsius"},
        # ]
        # connector.write(events, target="sensor_readings", maxlen=1000)
        # print(f"✅ Wrote {len(events)} events to Redis stream")

        # Read from stream
        # messages = connector.read(
        #     query="sensor_readings",
        #     count=10,
        # )
        # print(f"\nRead {len(messages)} messages from Redis stream")
        # for msg in messages[:3]:
        #     print(f"  ID: {msg['id']}, Data: {msg['data']}")

        connector.disconnect()

    except Exception as e:
        print(f"⚠️  Redis example requires running Redis server: {e}")
        print("   Start Redis locally to run this example")


# Example 7: Agent with Cloud Storage Tools
def example_agent_cloud_tools():
    """Using cloud storage with Agno agent."""
    print("\n=== Example 7: Agent with Cloud Storage ===\n")

    try:
        # Create toolkit with cloud storage
        toolkit = DataConnectorToolkit(
            enable_database=False,
            enable_file_readers=True,
            enable_cloud_storage=True,
            enable_streaming=False,
        )

        # Create agent
        agent = Agent(
            name="CloudDataAgent",
            model=OpenAIChat(id="gpt-4"),
            tools=[toolkit],
            instructions=[
                "You are a cloud data specialist.",
                "You can work with S3, GCS, and Azure storage.",
                "Help users manage and analyze cloud-stored data.",
            ],
            show_tool_calls=True,
            markdown=True,
        )

        # Example interaction
        print("Sample queries the agent can handle:")
        print("  - 'Connect to my S3 bucket and list all CSV files'")
        print("  - 'Read the latest data file from GCS'")
        print("  - 'Upload processed results to Azure Blob Storage'")

    except Exception as e:
        print(f"⚠️  Agent example requires OpenAI API key: {e}")


# Example 8: Real-time Data Pipeline
def example_realtime_pipeline():
    """Build a real-time data processing pipeline."""
    print("\n=== Example 8: Real-time Data Pipeline ===\n")

    from agno.tools.data_connectors.transformation import TransformationPipeline
    from agno.tools.data_connectors.validation import DataValidator

    print("Real-time Pipeline Architecture:")
    print("  1. Consume from Kafka → Validate → Transform → Store in S3")
    print("  2. Consume from RabbitMQ → Enrich → Write to Database")
    print("  3. Read from Redis Stream → Aggregate → Push to monitoring")

    # Simulated streaming data
    stream_data = [
        {"timestamp": "2024-01-01T10:00:00", "sensor": "temp_01", "value": 23.5, "unit": "C"},
        {"timestamp": "2024-01-01T10:01:00", "sensor": "temp_01", "value": 24.1, "unit": "C"},
        {"timestamp": "2024-01-01T10:02:00", "sensor": "temp_01", "value": 23.8, "unit": "C"},
    ]

    # Build transformation pipeline
    pipeline = TransformationPipeline("SensorDataPipeline")

    # Add enrichment
    pipeline.add_field(
        "fahrenheit", lambda x: round(float(x["value"]) * 9 / 5 + 32, 2) if x.get("unit") == "C" else x["value"]
    )

    # Add filtering
    pipeline.add_filter(lambda x: float(x["value"]) < 25.0)

    # Execute
    processed = pipeline.execute(stream_data)

    print(f"\nProcessed {len(processed)} records:")
    for record in processed:
        print(f"  {record['timestamp']}: {record['value']}°C = {record['fahrenheit']}°F")

    print("\n✅ Pipeline execution complete")


# Example 9: Multi-Cloud Data Sync
def example_multi_cloud_sync():
    """Synchronize data across multiple cloud providers."""
    print("\n=== Example 9: Multi-Cloud Data Synchronization ===\n")

    print("Multi-Cloud Sync Strategy:")
    print("  1. Read from S3 source bucket")
    print("  2. Transform/validate data")
    print("  3. Write to GCS and Azure for redundancy")
    print("  4. Update metadata in database")

    # Pseudo-code for multi-cloud sync
    print("\nExample workflow:")
    print("""
    # Source: S3
    s3_conn = CloudStorageConnector('s3', 'source-bucket')
    data = s3_conn.read('data/input.json')

    # Transform
    pipeline = TransformationPipeline()
    processed = pipeline.execute(data)

    # Destination: GCS
    gcs_conn = CloudStorageConnector('gcs', 'backup-bucket')
    gcs_conn.write(processed, 'backup/data.json')

    # Destination: Azure
    azure_conn = CloudStorageConnector('azure', 'archive-container')
    azure_conn.write(processed, 'archive/data.json')

    print('✅ Data synchronized across clouds')
    """)


if __name__ == "__main__":
    print("🚀 Data Connector - Cloud & Streaming Examples\n")
    print("=" * 60)

    # Cloud storage examples (require credentials)
    example_s3_connector()
    example_gcs_connector()
    example_azure_connector()

    # Streaming examples (require running services)
    example_kafka_streaming()
    example_rabbitmq()
    example_redis_streams()

    # Advanced examples
    example_agent_cloud_tools()
    example_realtime_pipeline()
    example_multi_cloud_sync()

    print("\n" + "=" * 60)
    print("✅ Examples completed!")
    print("\n💡 Note: Some examples require running services or credentials.")
    print("   Configure your environment to run all examples.")

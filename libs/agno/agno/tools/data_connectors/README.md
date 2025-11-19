# Data Connector Toolkit for Agno Framework

A comprehensive, production-ready data connector system for the Agno Framework, enabling seamless integration with databases, file systems, cloud storage, and streaming data sources.

## 🚀 Features

### **Database Connectors**
- **SQL Databases**: PostgreSQL, MySQL, SQLite, SQL Server
- **NoSQL Databases**: MongoDB, Redis
- Connection pooling with automatic health checks
- Transaction support
- Query result pagination

### **File System Readers**
- **CSV**: Stream large files, custom delimiters
- **JSON**: Standard JSON and NDJSON (JSON Lines)
- **XML**: XPath queries, element-to-dict conversion
- **Parquet**: Column-based reading with PyArrow
- **Excel**: XLSX/XLS support (via pandas)

### **Cloud Storage Integration**
- **AWS S3**: Multipart uploads, presigned URLs
- **Google Cloud Storage (GCS)**: Blob operations
- **Azure Blob Storage**: Container management
- Unified API across all providers
- Automatic retry with exponential backoff

### **Streaming Data Sources**
- **Apache Kafka**: Producer/Consumer with offset management
- **RabbitMQ**: Queue management, dead letter queues
- **Redis Streams**: Consumer groups, message acknowledgment
- Batch processing and real-time streaming

### **Data Quality & Transformation**
- **Schema Validation**: Pydantic-based validation
- **Data Quality Checks**: Nulls, duplicates, type checking
- **Schema Mapping**: Transform between different schemas
- **Transformation Pipelines**: Filter, map, aggregate, sort, deduplicate
- **Type Conversion**: Automatic type coercion

### **Production Features**
- Connection pooling for optimal resource usage
- Retry logic with exponential backoff
- Comprehensive error handling
- Metrics and monitoring
- Thread-safe operations
- Context managers for automatic cleanup

## 📦 Installation

### Basic Installation

```bash
# Core data connector (included with Agno)
pip install agno
```

### Optional Dependencies

Install additional packages based on your needs:

```bash
# Database connectors
pip install psycopg2-binary  # PostgreSQL
pip install pymysql          # MySQL
pip install pymongo          # MongoDB
pip install pymssql          # SQL Server

# File formats
pip install pyarrow          # Parquet files
pip install pandas           # Excel files

# Cloud storage
pip install boto3                    # AWS S3
pip install google-cloud-storage     # Google Cloud Storage
pip install azure-storage-blob       # Azure Blob Storage

# Streaming
pip install kafka-python     # Apache Kafka
pip install pika            # RabbitMQ
pip install redis           # Redis Streams
```

## 🎯 Quick Start

### 1. Using Database Connector

```python
from agno.tools.data_connectors import DatabaseConnector, DatabaseConfig

# Configure database
config = DatabaseConfig(
    host="localhost",
    port=5432,
    database="mydb",
    username="user",
    password="password",
    pool_size=5,  # Connection pooling
)

# Create connector
connector = DatabaseConnector(db_type="postgresql", config=config)

# Use context manager for automatic cleanup
with connector:
    # Query data
    results = connector.read("SELECT * FROM users WHERE active = true LIMIT 10")

    # Write data
    new_users = [
        {"name": "John Doe", "email": "john@example.com"},
        {"name": "Jane Smith", "email": "jane@example.com"},
    ]
    connector.write(new_users, target="users")

    # Get metrics
    metrics = connector.get_metrics()
    print(f"Queries executed: {metrics['reads']}")
```

### 2. Reading Files

```python
from agno.tools.data_connectors import FileReaderConnector

# Auto-detect format from extension
connector = FileReaderConnector("data/sales.csv")

with connector:
    # Read all data
    data = connector.read()

    # Read with limit
    sample = connector.read(query=100)

    # Read in chunks (memory-efficient for large files)
    for chunk in connector.read(chunk_size=1000):
        process_chunk(chunk)
```

### 3. Cloud Storage

```python
from agno.tools.data_connectors import CloudStorageConnector, CloudStorageConfig

# Configure S3
config = CloudStorageConfig(
    bucket_name="my-bucket",
    access_key="YOUR_ACCESS_KEY",
    secret_key="YOUR_SECRET_KEY",
    region="us-east-1",
)

connector = CloudStorageConnector(provider="s3", bucket_name="my-bucket", config=config)

with connector:
    # Read object
    content = connector.read("data/input.json")

    # Write object
    connector.write('{"result": "success"}', "output/result.json")

    # List objects
    objects = connector._connector.list_objects(prefix="data/", max_keys=100)
```

### 4. Streaming Data

```python
from agno.tools.data_connectors import StreamingConnector, StreamingConfig

# Configure Kafka
config = StreamingConfig(
    bootstrap_servers=["localhost:9092"],
    topic="events",
    group_id="my-consumer",
)

connector = StreamingConnector(stream_type="kafka", config=config)

with connector:
    # Produce messages
    events = [
        {"event": "user_login", "user_id": 123},
        {"event": "page_view", "user_id": 123, "page": "/home"},
    ]
    connector.write(events, "events")

    # Consume messages
    for message in connector.read(query=10):  # Read 10 messages
        print(f"Event: {message['value']}")
```

### 5. Using with Agno Agent

```python
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.data_connectors.toolkit import DataConnectorToolkit

# Create toolkit
toolkit = DataConnectorToolkit(
    enable_database=True,
    enable_file_readers=True,
    enable_cloud_storage=True,
    enable_streaming=True,
)

# Create agent with data tools
agent = Agent(
    name="DataAnalyst",
    model=OpenAIChat(id="gpt-4"),
    tools=[toolkit],
    instructions=[
        "You are a data analyst with access to various data sources.",
        "You can query databases, read files, and access cloud storage.",
    ],
)

# Agent can now use data connector tools
response = agent.run("Connect to PostgreSQL and show me the top 10 customers by revenue")
print(response.content)
```

## 🔧 Advanced Usage

### Data Validation

```python
from agno.tools.data_connectors.validation import DataValidator
from pydantic import BaseModel, Field

# Define schema
class UserSchema(BaseModel):
    id: int
    name: str
    email: str
    age: int = Field(ge=0, le=150)

# Validate data
validator = DataValidator(schema=UserSchema)
is_valid = validator.validate(data, raise_on_error=False)

if not is_valid:
    errors = validator.get_errors()
    print(f"Validation errors: {errors}")

# Data quality checks
null_stats = validator.check_nulls(data)
uniqueness = validator.check_uniqueness(data, key_fields=["id"])
```

### Schema Mapping

```python
from agno.tools.data_connectors.validation import SchemaMapper

# Define field mapping
mapping = {
    "user_id": "id",
    "full_name": "name",
    "email_addr": "email",
}

mapper = SchemaMapper(mapping)
mapped_data = mapper.map(source_data, strict=True)
```

### Transformation Pipelines

```python
from agno.tools.data_connectors.transformation import TransformationPipeline

# Build pipeline
pipeline = TransformationPipeline("DataCleaning")

# Add operations
pipeline.add_filter(lambda x: x["age"] > 18)  # Filter adults
pipeline.add_select_fields(["name", "email", "age"])  # Select fields
pipeline.add_rename_fields({"name": "full_name"})  # Rename
pipeline.add_sort("age", reverse=True)  # Sort by age
pipeline.add_deduplicate(key_fields=["email"])  # Remove duplicates

# Execute pipeline
result = pipeline.execute(data)

# Get statistics
stats = pipeline.get_execution_stats()
```

### Aggregation Pipeline

```python
from agno.tools.data_connectors.transformation import (
    TransformationPipeline,
    sum_agg,
    avg_agg,
    count_agg,
)

pipeline = TransformationPipeline("SalesAnalysis")

# Group by region
pipeline.add_group_by("region")

# Aggregate metrics
pipeline.add_aggregate({
    "revenue": lambda x: {
        "total": sum_agg(x),
        "average": avg_agg(x),
        "count": count_agg(x),
    }
})

result = pipeline.execute(sales_data)
# Result: {"North": {"revenue": {"total": 10000, "average": 250, "count": 40}}, ...}
```

### Custom Transformation Steps

```python
from agno.tools.data_connectors.transformation import TransformationStep

class EnrichmentStep(TransformationStep):
    def __init__(self, lookup_table):
        super().__init__("Enrichment")
        self.lookup = lookup_table

    def transform(self, data):
        for record in data:
            record["category"] = self.lookup.get(record["product_id"], "Unknown")
        return data

# Use in pipeline
pipeline = TransformationPipeline()
pipeline.add_step(EnrichmentStep(product_categories))
```

### Connection Pooling

```python
from agno.tools.data_connectors.base import ConnectionPool

# Define connection factory
def create_db_connection():
    import psycopg2
    return psycopg2.connect(
        host="localhost",
        database="mydb",
        user="user",
        password="password"
    )

# Create pool
pool = ConnectionPool(
    factory=create_db_connection,
    max_size=10,
    timeout=30,
    health_check=lambda conn: conn.closed == 0,
)

# Use connections
with pool.acquire() as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    results = cursor.fetchall()

# Get pool metrics
metrics = pool.get_metrics()
print(f"Pool size: {metrics['current_size']}/{metrics['max_size']}")
```

### Retry Logic

```python
from agno.tools.data_connectors.base import with_retry, RetryConfig

# Configure retry behavior
retry_config = RetryConfig(
    max_retries=3,
    initial_delay=1.0,
    max_delay=60.0,
    exponential_base=2.0,
    jitter=True,
)

# Wrap function with retry
@with_retry
def fetch_data_from_api(url):
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.json()

# Or use decorator-style
retrying_fetch = with_retry(fetch_data_from_api, retry_config)
data = retrying_fetch("https://api.example.com/data")
```

## 📊 Architecture

### Component Overview

```
DataConnectorToolkit
├── Database Connectors
│   ├── SQLConnector (PostgreSQL, MySQL, SQLite, MSSQL)
│   ├── MongoDBConnector
│   └── DatabaseConnector (Unified Interface)
│
├── File Readers
│   ├── CSVReader
│   ├── JSONReader (JSON/NDJSON)
│   ├── XMLReader
│   ├── ParquetReader
│   └── FileReaderConnector (Auto-detect)
│
├── Cloud Storage
│   ├── S3Connector
│   ├── GCSConnector
│   ├── AzureBlobConnector
│   └── CloudStorageConnector (Unified Interface)
│
├── Streaming
│   ├── KafkaConnector
│   ├── RabbitMQConnector
│   ├── RedisStreamConnector
│   └── StreamingConnector (Unified Interface)
│
├── Validation & Quality
│   ├── DataValidator
│   ├── SchemaMapper
│   └── TypeConverter
│
└── Transformation
    ├── TransformationPipeline
    ├── FilterStep, MapStep, SortStep
    ├── AggregateStep, GroupByStep
    └── Custom Steps
```

### Base Classes

All connectors extend `DataConnectorBase` which provides:
- Connection lifecycle management
- Metrics collection
- Context manager support
- Error handling
- Read/Write interfaces

## 🔐 Security Best Practices

### 1. Credentials Management

```python
import os
from dotenv import load_dotenv

# Load from environment
load_dotenv()

config = DatabaseConfig(
    host=os.getenv("DB_HOST"),
    database=os.getenv("DB_NAME"),
    username=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
)
```

### 2. Read-Only Connections

```python
# PostgreSQL read-only session
connector._connection.set_session(readonly=True)

# Or disable write operations in toolkit
toolkit = DataConnectorToolkit(
    enable_database=True,
    enable_write_operations=False,  # Disable all writes
)
```

### 3. File Path Restrictions

```python
toolkit = DataConnectorToolkit(
    enable_file_readers=True,
    allowed_file_paths=[
        "/data/*.csv",
        "/uploads/*/processed/*.json",
    ],
)
```

## 📈 Performance Optimization

### 1. Connection Pooling

Use connection pools for high-throughput applications:

```python
config = DatabaseConfig(pool_size=20)  # Increase pool size
connector = DatabaseConnector(db_type="postgresql", config=config, use_pool=True)
```

### 2. Batch Operations

```python
# Batch writes
batch_size = 1000
for i in range(0, len(data), batch_size):
    batch = data[i:i + batch_size]
    connector.write(batch, "users")
```

### 3. Streaming Large Files

```python
# Stream large CSV files in chunks
for chunk in reader.read(chunk_size=10000):
    process_chunk(chunk)
    # Memory-efficient: only one chunk in memory at a time
```

## 🐛 Error Handling

```python
from agno.tools.data_connectors.base import DataConnectorBase

try:
    with connector:
        data = connector.read("SELECT * FROM users")
except ConnectionError as e:
    logger.error(f"Connection failed: {e}")
    # Retry logic or fallback
except TimeoutError as e:
    logger.error(f"Query timeout: {e}")
    # Handle timeout
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    # General error handling
finally:
    # Cleanup always happens with context manager
    pass
```

## 📝 Examples

See the `cookbook/examples/data_connectors/` directory for comprehensive examples:

- `01_database_connector.py` - Database operations, validation, pipelines
- `02_file_readers.py` - CSV, JSON, XML, Parquet file handling
- `03_cloud_and_streaming.py` - Cloud storage and streaming sources

## 🧪 Testing

```python
# Test connection
connector = DatabaseConnector(db_type="postgresql", config=config)
is_healthy = connector.test_connection()

if is_healthy:
    print("✅ Connection successful")
else:
    print("❌ Connection failed")

# Get metrics
metrics = connector.get_metrics()
print(f"Connections: {metrics['connections']}")
print(f"Reads: {metrics['reads']}")
print(f"Writes: {metrics['writes']}")
print(f"Errors: {metrics['errors']}")
```

## 🤝 Contributing

Contributions are welcome! Please:

1. Add tests for new features
2. Update documentation
3. Follow existing code style
4. Add examples for complex features

## 📄 License

This data connector toolkit is part of the Agno Framework and follows the same license.

## 🆘 Support

- Documentation: https://docs.agno.com
- Issues: https://github.com/agno/agno/issues
- Community: https://discord.gg/agno

## 🗺️ Roadmap

- [ ] Additional database support (Cassandra, DynamoDB)
- [ ] GraphQL data sources
- [ ] REST API connector
- [ ] Data lineage tracking
- [ ] Query optimization hints
- [ ] Async/await support
- [ ] Distributed caching layer

---

Built with ❤️ for the Agno Framework

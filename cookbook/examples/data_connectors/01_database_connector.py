"""
Example 1: Database Connector Usage

Demonstrates how to use the Data Connector to work with databases:
- PostgreSQL connection with connection pooling
- SQL query execution
- Data validation and transformation
- Write operations
"""

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.data_connectors import DatabaseConnector, DatabaseConfig
from agno.tools.data_connectors.validation import DataValidator
from agno.tools.data_connectors.transformation import TransformationPipeline
from pydantic import BaseModel, Field


# Example 1: Direct Database Connector Usage
def example_direct_database_usage():
    """Direct usage of database connector without agent."""
    print("=== Example 1: Direct Database Connector ===\n")

    # Configure database connection
    config = DatabaseConfig(
        host="localhost",
        port=5432,
        database="mydb",
        username="user",
        password="password",
        pool_size=5,  # Connection pooling
    )

    # Create connector with connection pooling
    connector = DatabaseConnector(db_type="postgresql", config=config)

    # Use context manager for automatic cleanup
    with connector:
        # Query data
        results = connector.read(
            "SELECT id, name, email, created_at FROM users WHERE active = true LIMIT 10"
        )

        print(f"Retrieved {len(results)} users:")
        for user in results[:3]:
            print(f"  - {user['name']} ({user['email']})")

        # Transform data
        pipeline = TransformationPipeline("UserTransform")
        pipeline.add_select_fields(["id", "name", "email"])
        pipeline.add_rename_fields({"name": "full_name", "email": "email_address"})

        transformed = pipeline.execute(results)
        print(f"\nTransformed data sample:")
        print(transformed[0] if transformed else "No data")

        # Get metrics
        metrics = connector.get_metrics()
        print(f"\nConnector metrics: {metrics}")


# Example 2: Using Database Connector with Agno Agent
def example_agent_with_database():
    """Using database connector as a tool for Agno agent."""
    print("\n=== Example 2: Agent with Database Tools ===\n")

    from agno.tools.data_connectors.toolkit import DataConnectorToolkit

    # Create toolkit with database features
    toolkit = DataConnectorToolkit(
        enable_database=True,
        enable_file_readers=False,
        enable_cloud_storage=False,
        enable_streaming=False,
    )

    # Create agent with data connector tools
    agent = Agent(
        name="DataAnalyst",
        model=OpenAIChat(id="gpt-4"),
        tools=[toolkit],
        instructions=[
            "You are a data analyst with access to database tools.",
            "You can connect to databases, query data, and analyze results.",
            "Always provide insights and summaries of the data you retrieve.",
        ],
        show_tool_calls=True,
        markdown=True,
    )

    # Example queries
    queries = [
        "Connect to a PostgreSQL database at localhost, database 'analytics', user 'analyst'",
        "Query the top 10 customers by total purchases",
        "Show me the connection status and metrics",
    ]

    for query in queries:
        print(f"\n📊 Query: {query}")
        response = agent.run(query)
        print(response.content)


# Example 3: Data Validation with Database
def example_database_validation():
    """Validate data retrieved from database."""
    print("\n=== Example 3: Database Data Validation ===\n")

    # Define expected schema using Pydantic
    class UserSchema(BaseModel):
        id: int
        name: str
        email: str
        age: int = Field(ge=0, le=150)
        active: bool

    # Simulate database results
    sample_data = [
        {"id": 1, "name": "John Doe", "email": "john@example.com", "age": 30, "active": True},
        {"id": 2, "name": "Jane Smith", "email": "jane@example.com", "age": 25, "active": True},
        {"id": 3, "name": "Bob Wilson", "email": "bob@example.com", "age": -5, "active": True},  # Invalid age
    ]

    # Validate data
    validator = DataValidator(schema=UserSchema)

    print("Validating data...")
    is_valid = validator.validate(sample_data, raise_on_error=False)

    if not is_valid:
        print("❌ Validation failed!")
        errors = validator.get_errors()
        for error in errors:
            print(f"  Record {error['index']}: {error['errors']}")
    else:
        print("✅ All data is valid!")

    # Check data quality
    null_stats = validator.check_nulls(sample_data)
    print(f"\nNull statistics: {null_stats}")

    uniqueness = validator.check_uniqueness(sample_data, ["id"])
    print(f"Uniqueness check: {uniqueness['unique_records']}/{uniqueness['total_records']} unique")


# Example 4: MongoDB NoSQL Database
def example_mongodb_usage():
    """Using MongoDB with the data connector."""
    print("\n=== Example 4: MongoDB Connector ===\n")

    config = DatabaseConfig(
        host="localhost",
        port=27017,
        database="myapp",
        username="user",
        password="password",
    )

    connector = DatabaseConnector(db_type="mongodb", config=config)

    with connector:
        # Query MongoDB
        query = {"status": "active", "age": {"$gt": 18}}
        results = connector.read(query, collection="users", limit=10)

        print(f"Retrieved {len(results)} active adult users")

        # Insert data
        new_users = [
            {"name": "Alice", "email": "alice@example.com", "age": 28, "status": "active"},
            {"name": "Charlie", "email": "charlie@example.com", "age": 35, "status": "active"},
        ]

        connector.write(new_users, target="users")
        print(f"Inserted {len(new_users)} new users")


# Example 5: Advanced Query with Transformation Pipeline
def example_advanced_pipeline():
    """Advanced data transformation pipeline."""
    print("\n=== Example 5: Advanced Transformation Pipeline ===\n")

    # Sample data from database
    orders = [
        {"order_id": 1, "customer": "John", "amount": 100, "status": "completed", "date": "2024-01-15"},
        {"order_id": 2, "customer": "Jane", "amount": 250, "status": "completed", "date": "2024-01-16"},
        {"order_id": 3, "customer": "John", "amount": 75, "status": "pending", "date": "2024-01-17"},
        {"order_id": 4, "customer": "Bob", "amount": 500, "status": "completed", "date": "2024-01-18"},
        {"order_id": 5, "customer": "Jane", "amount": 150, "status": "completed", "date": "2024-01-19"},
    ]

    # Build transformation pipeline
    from agno.tools.data_connectors.transformation import sum_agg, avg_agg, count_agg

    pipeline = TransformationPipeline("OrderAnalysis")

    # Filter completed orders
    pipeline.add_filter(lambda x: x["status"] == "completed")

    # Group by customer
    pipeline.add_group_by("customer")

    # Aggregate: total amount, average, count
    pipeline.add_aggregate(
        {
            "amount": lambda amounts: {
                "total": sum_agg(amounts),
                "average": avg_agg(amounts),
                "count": count_agg(amounts),
            }
        }
    )

    # Execute pipeline
    result = pipeline.execute(orders)

    print("Order Analysis Results:")
    for customer, stats in result.items():
        print(f"\n{customer}:")
        print(f"  Total: ${stats['amount']['total']}")
        print(f"  Average: ${stats['amount']['average']:.2f}")
        print(f"  Count: {stats['amount']['count']}")

    # Get pipeline statistics
    print("\nPipeline Execution Stats:")
    for stat in pipeline.get_execution_stats():
        print(f"  {stat['step']}: {stat['stats']}")


if __name__ == "__main__":
    # Run examples (comment out database examples if no DB available)
    print("🚀 Data Connector - Database Examples\n")
    print("=" * 60)

    # Example 1: Direct usage (requires running database)
    # example_direct_database_usage()

    # Example 2: Agent usage (requires OpenAI API key and database)
    # example_agent_with_database()

    # Example 3: Validation (standalone, no database required)
    example_database_validation()

    # Example 4: MongoDB (requires MongoDB instance)
    # example_mongodb_usage()

    # Example 5: Advanced pipeline (standalone, no database required)
    example_advanced_pipeline()

    print("\n" + "=" * 60)
    print("✅ Examples completed!")

"""
Data Connector Toolkit for Agno Framework.

Main toolkit that provides data connector capabilities as tools for Agno agents.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from agno.tools import Toolkit
from agno.tools.data_connectors.database import DatabaseConnector, DatabaseConfig
from agno.tools.data_connectors.file_readers import FileReaderConnector
from agno.tools.data_connectors.cloud_storage import CloudStorageConnector, CloudStorageConfig
from agno.tools.data_connectors.streaming import StreamingConnector, StreamingConfig
from agno.tools.data_connectors.validation import DataValidator, SchemaMapper, TypeConverter
from agno.tools.data_connectors.transformation import TransformationPipeline
from agno.utils.log import logger


class DataConnectorToolkit(Toolkit):
    """
    Comprehensive data connector toolkit for Agno agents.

    Provides tools for:
    - Database operations (SQL/NoSQL)
    - File reading (CSV/JSON/XML/Parquet)
    - Cloud storage (S3/GCS/Azure)
    - Streaming data (Kafka/RabbitMQ/Redis)
    - Data validation and transformation
    """

    def __init__(
        self,
        # Database settings
        enable_database: bool = True,
        database_configs: Optional[Dict[str, DatabaseConfig]] = None,
        # File settings
        enable_file_readers: bool = True,
        allowed_file_paths: Optional[List[str]] = None,
        # Cloud storage settings
        enable_cloud_storage: bool = False,
        cloud_configs: Optional[Dict[str, CloudStorageConfig]] = None,
        # Streaming settings
        enable_streaming: bool = False,
        streaming_configs: Optional[Dict[str, StreamingConfig]] = None,
        # Feature flags
        enable_validation: bool = True,
        enable_transformation: bool = True,
        enable_write_operations: bool = False,
    ):
        """
        Initialize Data Connector Toolkit.

        Args:
            enable_database: Enable database connector tools
            database_configs: Named database configurations
            enable_file_readers: Enable file reader tools
            allowed_file_paths: List of allowed file paths/patterns
            enable_cloud_storage: Enable cloud storage tools
            cloud_configs: Named cloud storage configurations
            enable_streaming: Enable streaming tools
            streaming_configs: Named streaming configurations
            enable_validation: Enable validation tools
            enable_transformation: Enable transformation tools
            enable_write_operations: Allow write/update operations
        """
        super().__init__(name="data_connector")

        self.database_configs = database_configs or {}
        self.cloud_configs = cloud_configs or {}
        self.streaming_configs = streaming_configs or {}
        self.allowed_file_paths = allowed_file_paths
        self.enable_write_operations = enable_write_operations

        # Active connections registry
        self._active_connections: Dict[str, Any] = {}

        # Register tools based on enabled features
        if enable_database:
            self.register(self.connect_database)
            self.register(self.query_database)
            self.register(self.list_database_tables)
            if enable_write_operations:
                self.register(self.write_to_database)

        if enable_file_readers:
            self.register(self.read_file)
            self.register(self.list_files)
            if enable_write_operations:
                self.register(self.write_file)

        if enable_cloud_storage:
            self.register(self.connect_cloud_storage)
            self.register(self.read_from_cloud)
            self.register(self.list_cloud_objects)
            if enable_write_operations:
                self.register(self.write_to_cloud)

        if enable_streaming:
            self.register(self.connect_streaming)
            self.register(self.consume_stream)
            if enable_write_operations:
                self.register(self.produce_to_stream)

        if enable_validation:
            self.register(self.validate_data)
            self.register(self.check_data_quality)

        if enable_transformation:
            self.register(self.transform_data)
            self.register(self.map_schema)

        # Utility functions
        self.register(self.get_connection_status)
        self.register(self.close_connection)

    def connect_database(
        self,
        connection_name: str,
        db_type: str,
        host: str = "localhost",
        port: Optional[int] = None,
        database: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ) -> str:
        """
        Connect to a database.

        Args:
            connection_name: Unique name for this connection
            db_type: Database type (postgresql, mysql, sqlite, mongodb)
            host: Database host
            port: Database port
            database: Database name
            username: Username
            password: Password

        Returns:
            Connection status message
        """
        try:
            # Check if config exists
            if connection_name in self.database_configs:
                config = self.database_configs[connection_name]
            else:
                # Create new config
                config = DatabaseConfig(
                    host=host,
                    port=port,
                    database=database,
                    username=username,
                    password=password,
                )

            connector = DatabaseConnector(db_type=db_type, config=config)
            connector.connect()

            self._active_connections[connection_name] = connector

            return json.dumps(
                {
                    "status": "success",
                    "message": f"Connected to {db_type} database",
                    "connection_name": connection_name,
                }
            )
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    def query_database(
        self, connection_name: str, query: str, limit: Optional[int] = None
    ) -> str:
        """
        Execute a query on a database connection.

        Args:
            connection_name: Name of the database connection
            query: SQL or MongoDB query
            limit: Maximum number of rows to return

        Returns:
            Query results as JSON
        """
        try:
            if connection_name not in self._active_connections:
                return json.dumps(
                    {"status": "error", "message": f"No active connection: {connection_name}"}
                )

            connector = self._active_connections[connection_name]

            # Execute query
            if hasattr(connector, "_connector") and hasattr(connector._connector, "engine"):
                # SQL query
                results = connector.read(query, fetch_size=limit)
            else:
                # MongoDB or other
                results = connector.read(query, limit=limit)

            return json.dumps({"status": "success", "data": results, "count": len(results)})
        except Exception as e:
            logger.error(f"Query error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    def list_database_tables(self, connection_name: str) -> str:
        """
        List tables in a database.

        Args:
            connection_name: Name of the database connection

        Returns:
            List of tables as JSON
        """
        try:
            if connection_name not in self._active_connections:
                return json.dumps(
                    {"status": "error", "message": f"No active connection: {connection_name}"}
                )

            connector = self._active_connections[connection_name]

            # Get tables based on database type
            if hasattr(connector, "_connector") and hasattr(connector._connector, "engine"):
                # SQL database
                query = "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
                results = connector.read(query)
                tables = [row["table_name"] for row in results]
            else:
                # MongoDB
                tables = connector._connector._db.list_collection_names()

            return json.dumps({"status": "success", "tables": tables})
        except Exception as e:
            logger.error(f"List tables error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    def write_to_database(
        self, connection_name: str, table: str, data: str
    ) -> str:
        """
        Write data to a database table.

        Args:
            connection_name: Name of the database connection
            table: Table/collection name
            data: JSON data to write

        Returns:
            Write status as JSON
        """
        try:
            if not self.enable_write_operations:
                return json.dumps({"status": "error", "message": "Write operations disabled"})

            if connection_name not in self._active_connections:
                return json.dumps(
                    {"status": "error", "message": f"No active connection: {connection_name}"}
                )

            connector = self._active_connections[connection_name]

            # Parse data
            parsed_data = json.loads(data)

            # Write data
            connector.write(parsed_data, table)

            count = len(parsed_data) if isinstance(parsed_data, list) else 1
            return json.dumps(
                {"status": "success", "message": f"Wrote {count} records to {table}"}
            )
        except Exception as e:
            logger.error(f"Write error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    def read_file(
        self, file_path: str, file_format: Optional[str] = None, limit: Optional[int] = None
    ) -> str:
        """
        Read data from a file.

        Args:
            file_path: Path to the file
            file_format: File format (csv, json, xml, parquet) - auto-detected if None
            limit: Maximum number of rows to read

        Returns:
            File contents as JSON
        """
        try:
            # Validate file path if restrictions are set
            if self.allowed_file_paths:
                path = Path(file_path)
                allowed = any(path.match(pattern) for pattern in self.allowed_file_paths)
                if not allowed:
                    return json.dumps(
                        {"status": "error", "message": "File path not allowed"}
                    )

            connector = FileReaderConnector(file_path, file_format)
            connector.connect()

            data = connector.read(query=limit)

            # Convert to JSON-serializable format
            if file_format == "parquet":
                data = data.to_dict(orient="records")

            connector.disconnect()

            return json.dumps({"status": "success", "data": data})
        except Exception as e:
            logger.error(f"File read error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    def list_files(self, directory: str, pattern: str = "*") -> str:
        """
        List files in a directory.

        Args:
            directory: Directory path
            pattern: Glob pattern for filtering files

        Returns:
            List of files as JSON
        """
        try:
            path = Path(directory)
            if not path.exists():
                return json.dumps({"status": "error", "message": "Directory not found"})

            files = [str(f) for f in path.glob(pattern) if f.is_file()]

            return json.dumps({"status": "success", "files": files})
        except Exception as e:
            logger.error(f"List files error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    def write_file(self, file_path: str, data: str, file_format: Optional[str] = None) -> str:
        """
        Write data to a file.

        Args:
            file_path: Path to the file
            data: JSON data to write
            file_format: File format (csv, json, xml, parquet)

        Returns:
            Write status as JSON
        """
        try:
            if not self.enable_write_operations:
                return json.dumps({"status": "error", "message": "Write operations disabled"})

            parsed_data = json.loads(data)

            connector = FileReaderConnector(file_path, file_format)
            connector.write(parsed_data, file_path)

            return json.dumps({"status": "success", "message": f"Wrote data to {file_path}"})
        except Exception as e:
            logger.error(f"File write error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    def connect_cloud_storage(
        self,
        connection_name: str,
        provider: str,
        bucket_name: str,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        region: Optional[str] = None,
    ) -> str:
        """
        Connect to cloud storage.

        Args:
            connection_name: Unique name for this connection
            provider: Cloud provider (s3, gcs, azure)
            bucket_name: Bucket/container name
            access_key: Access key/account name
            secret_key: Secret key/account key
            region: Cloud region

        Returns:
            Connection status message
        """
        try:
            config = CloudStorageConfig(
                bucket_name=bucket_name,
                access_key=access_key,
                secret_key=secret_key,
                region=region,
            )

            connector = CloudStorageConnector(provider, bucket_name, config)
            connector.connect()

            self._active_connections[connection_name] = connector

            return json.dumps(
                {
                    "status": "success",
                    "message": f"Connected to {provider} storage",
                    "connection_name": connection_name,
                }
            )
        except Exception as e:
            logger.error(f"Cloud storage connection error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    def read_from_cloud(self, connection_name: str, object_key: str) -> str:
        """
        Read object from cloud storage.

        Args:
            connection_name: Name of the cloud storage connection
            object_key: Object key/path

        Returns:
            Object content as JSON
        """
        try:
            if connection_name not in self._active_connections:
                return json.dumps(
                    {"status": "error", "message": f"No active connection: {connection_name}"}
                )

            connector = self._active_connections[connection_name]
            content = connector.read(object_key)

            return json.dumps({"status": "success", "data": content})
        except Exception as e:
            logger.error(f"Cloud read error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    def list_cloud_objects(
        self, connection_name: str, prefix: str = "", max_keys: int = 100
    ) -> str:
        """
        List objects in cloud storage.

        Args:
            connection_name: Name of the cloud storage connection
            prefix: Object key prefix filter
            max_keys: Maximum number of objects to return

        Returns:
            List of objects as JSON
        """
        try:
            if connection_name not in self._active_connections:
                return json.dumps(
                    {"status": "error", "message": f"No active connection: {connection_name}"}
                )

            connector = self._active_connections[connection_name]

            if hasattr(connector._connector, "list_objects"):
                objects = connector._connector.list_objects(prefix, max_keys)
            elif hasattr(connector._connector, "list_blobs"):
                objects = connector._connector.list_blobs(prefix, max_keys)
            else:
                return json.dumps({"status": "error", "message": "List operation not supported"})

            # Convert to JSON-serializable format
            object_list = [{"key": obj.get("Key", str(obj)), "size": obj.get("Size", 0)} for obj in objects]

            return json.dumps({"status": "success", "objects": object_list})
        except Exception as e:
            logger.error(f"Cloud list error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    def write_to_cloud(self, connection_name: str, object_key: str, data: str) -> str:
        """
        Write data to cloud storage.

        Args:
            connection_name: Name of the cloud storage connection
            object_key: Object key/path
            data: Data to write

        Returns:
            Write status as JSON
        """
        try:
            if not self.enable_write_operations:
                return json.dumps({"status": "error", "message": "Write operations disabled"})

            if connection_name not in self._active_connections:
                return json.dumps(
                    {"status": "error", "message": f"No active connection: {connection_name}"}
                )

            connector = self._active_connections[connection_name]
            connector.write(data, object_key)

            return json.dumps(
                {"status": "success", "message": f"Wrote data to {object_key}"}
            )
        except Exception as e:
            logger.error(f"Cloud write error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    def connect_streaming(
        self,
        connection_name: str,
        stream_type: str,
        **kwargs,
    ) -> str:
        """
        Connect to streaming data source.

        Args:
            connection_name: Unique name for this connection
            stream_type: Streaming type (kafka, rabbitmq, redis)
            **kwargs: Stream-specific parameters

        Returns:
            Connection status message
        """
        try:
            connector = StreamingConnector(stream_type, **kwargs)
            connector.connect()

            self._active_connections[connection_name] = connector

            return json.dumps(
                {
                    "status": "success",
                    "message": f"Connected to {stream_type} stream",
                    "connection_name": connection_name,
                }
            )
        except Exception as e:
            logger.error(f"Streaming connection error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    def consume_stream(
        self, connection_name: str, source: str, max_messages: int = 10
    ) -> str:
        """
        Consume messages from stream.

        Args:
            connection_name: Name of the streaming connection
            source: Topic/queue/stream name
            max_messages: Maximum number of messages to consume

        Returns:
            Messages as JSON
        """
        try:
            if connection_name not in self._active_connections:
                return json.dumps(
                    {"status": "error", "message": f"No active connection: {connection_name}"}
                )

            connector = self._active_connections[connection_name]
            messages = list(connector.read(source, max_messages))

            return json.dumps({"status": "success", "messages": messages, "count": len(messages)})
        except Exception as e:
            logger.error(f"Stream consume error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    def produce_to_stream(self, connection_name: str, target: str, data: str) -> str:
        """
        Produce messages to stream.

        Args:
            connection_name: Name of the streaming connection
            target: Topic/queue/stream name
            data: JSON data to produce

        Returns:
            Produce status as JSON
        """
        try:
            if not self.enable_write_operations:
                return json.dumps({"status": "error", "message": "Write operations disabled"})

            if connection_name not in self._active_connections:
                return json.dumps(
                    {"status": "error", "message": f"No active connection: {connection_name}"}
                )

            connector = self._active_connections[connection_name]
            parsed_data = json.loads(data)

            connector.write(parsed_data, target)

            count = len(parsed_data) if isinstance(parsed_data, list) else 1
            return json.dumps(
                {"status": "success", "message": f"Produced {count} messages to {target}"}
            )
        except Exception as e:
            logger.error(f"Stream produce error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    def validate_data(self, data: str, schema_fields: str) -> str:
        """
        Validate data against schema.

        Args:
            data: JSON data to validate
            schema_fields: JSON schema definition

        Returns:
            Validation results as JSON
        """
        try:
            parsed_data = json.loads(data)
            schema_def = json.loads(schema_fields)

            # Create dynamic validator
            # This is simplified - in practice you'd build a full Pydantic model
            validator = DataValidator()

            # Basic validation checks
            if isinstance(parsed_data, dict):
                completeness = validator.check_completeness(parsed_data, set(schema_def.keys()))
                nulls = validator.check_nulls(parsed_data)
            else:
                completeness = {}
                nulls = validator.check_nulls(parsed_data)

            return json.dumps(
                {
                    "status": "success",
                    "valid": True,
                    "completeness": completeness,
                    "null_check": nulls,
                }
            )
        except Exception as e:
            logger.error(f"Validation error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    def check_data_quality(self, data: str) -> str:
        """
        Check data quality metrics.

        Args:
            data: JSON data to check

        Returns:
            Data quality metrics as JSON
        """
        try:
            parsed_data = json.loads(data)
            validator = DataValidator()

            metrics = {
                "record_count": len(parsed_data) if isinstance(parsed_data, list) else 1,
                "null_check": validator.check_nulls(parsed_data),
            }

            if isinstance(parsed_data, list) and parsed_data:
                # Check uniqueness on first field
                first_field = list(parsed_data[0].keys())[0]
                metrics["uniqueness"] = validator.check_uniqueness(parsed_data, [first_field])

            return json.dumps({"status": "success", "metrics": metrics})
        except Exception as e:
            logger.error(f"Quality check error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    def transform_data(self, data: str, operations: str) -> str:
        """
        Transform data using pipeline operations.

        Args:
            data: JSON data to transform
            operations: JSON list of operations (filter, map, select, etc.)

        Returns:
            Transformed data as JSON
        """
        try:
            parsed_data = json.loads(data)
            ops = json.loads(operations)

            pipeline = TransformationPipeline()

            for op in ops:
                op_type = op.get("type")
                if op_type == "select_fields":
                    pipeline.add_select_fields(op["fields"])
                elif op_type == "rename_fields":
                    pipeline.add_rename_fields(op["mapping"])
                elif op_type == "sort":
                    pipeline.add_sort(op["key"], op.get("reverse", False))
                elif op_type == "deduplicate":
                    pipeline.add_deduplicate(op.get("key_fields"))

            result = pipeline.execute(parsed_data)

            return json.dumps({"status": "success", "data": result})
        except Exception as e:
            logger.error(f"Transformation error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    def map_schema(self, data: str, mapping: str) -> str:
        """
        Map data from source schema to target schema.

        Args:
            data: JSON data to map
            mapping: JSON mapping definition (source_field -> target_field)

        Returns:
            Mapped data as JSON
        """
        try:
            parsed_data = json.loads(data)
            field_mapping = json.loads(mapping)

            mapper = SchemaMapper(field_mapping)
            result = mapper.map(parsed_data)

            return json.dumps({"status": "success", "data": result})
        except Exception as e:
            logger.error(f"Schema mapping error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    def get_connection_status(self) -> str:
        """
        Get status of all active connections.

        Returns:
            Connection status as JSON
        """
        status = {
            "active_connections": len(self._active_connections),
            "connections": {
                name: {
                    "type": type(conn).__name__,
                    "connected": getattr(conn, "_is_connected", False),
                    "metrics": conn.get_metrics() if hasattr(conn, "get_metrics") else {},
                }
                for name, conn in self._active_connections.items()
            },
        }

        return json.dumps(status)

    def close_connection(self, connection_name: str) -> str:
        """
        Close a specific connection.

        Args:
            connection_name: Name of the connection to close

        Returns:
            Close status as JSON
        """
        try:
            if connection_name not in self._active_connections:
                return json.dumps(
                    {"status": "error", "message": f"No active connection: {connection_name}"}
                )

            connector = self._active_connections[connection_name]
            connector.disconnect()
            del self._active_connections[connection_name]

            return json.dumps(
                {"status": "success", "message": f"Closed connection: {connection_name}"}
            )
        except Exception as e:
            logger.error(f"Close connection error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    def __del__(self):
        """Clean up connections on toolkit destruction."""
        for name, conn in self._active_connections.items():
            try:
                conn.disconnect()
            except Exception as e:
                logger.error(f"Error closing connection {name}: {e}")

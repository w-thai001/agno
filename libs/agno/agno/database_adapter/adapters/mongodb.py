"""
MongoDB Database Adapter

Provides MongoDB-specific implementation with connection pooling,
query execution, and transaction support (for replica sets).
"""

from typing import Any, Dict, List, Optional

from agno.database_adapter.base import DatabaseAdapter
from agno.database_adapter.exceptions import ConnectionError, QueryError, UnsupportedOperation
from agno.database_adapter.retry import RetryConfig
from agno.utils.log import logger

try:
    from pymongo import MongoClient
    from pymongo.database import Database
    from pymongo.errors import PyMongoError
except ImportError:
    raise ImportError("MongoDB adapter requires pymongo. " "Install with: pip install pymongo")


class MongoDBAdapter(DatabaseAdapter):
    """
    MongoDB database adapter with FSA state management.

    Features:
    - Connection pooling using PyMongo
    - Automatic reconnection with retry logic
    - Transaction support (requires replica sets)
    - Document-based operations
    - Schema migrations (collection-based)

    Note:
        Transactions require MongoDB 4.0+ and a replica set configuration.
    """

    def __init__(
        self,
        connection_string: str,
        database_name: str,
        pool_size: int = 5,
        max_idle_time_ms: int = 60000,
        retry_config: Optional[RetryConfig] = None,
        auto_connect: bool = True,
    ):
        """
        Initialize MongoDB adapter.

        Args:
            connection_string: MongoDB connection string
                              (e.g., 'mongodb://localhost:27017/')
            database_name: Name of the database to use
            pool_size: Maximum number of connections in pool (default: 5)
            max_idle_time_ms: Maximum idle time for connections in ms (default: 60000)
            retry_config: Configuration for retry logic (uses default if None)
            auto_connect: Automatically connect on initialization (default: True)
        """
        self.database_name = database_name
        self.max_idle_time_ms = max_idle_time_ms
        self._client: Optional[MongoClient] = None
        self._database: Optional[Database] = None

        super().__init__(
            connection_string=connection_string,
            pool_size=pool_size,
            max_overflow=0,  # MongoDB handles this internally
            pool_timeout=30,
            retry_config=retry_config,
            auto_connect=auto_connect,
        )

    @property
    def db_type(self) -> str:
        """Return the database type identifier."""
        return "mongodb"

    def _create_pool(self) -> Any:
        """
        Create and return a MongoDB client with connection pooling.

        Returns:
            MongoClient instance

        Raises:
            ConnectionError: If client creation fails
        """
        try:
            # Create MongoClient with connection pooling
            self._client = MongoClient(
                self.connection_string,
                maxPoolSize=self.pool_size,
                minPoolSize=1,
                maxIdleTimeMS=self.max_idle_time_ms,
                serverSelectionTimeoutMS=self.pool_timeout * 1000,
                retryWrites=True,
                retryReads=True,
            )

            # Get database
            self._database = self._client[self.database_name]

            # Verify connection
            self._client.admin.command("ping")

            logger.debug(f"[MongoDB] Client created with pool_size={self.pool_size}")
            return self._client

        except Exception as e:
            raise ConnectionError(f"Failed to create MongoDB client: {str(e)}") from e

    def _get_connection_from_pool(self) -> Any:
        """
        Get a database connection (returns database object).

        Returns:
            MongoDB Database object

        Raises:
            ConnectionError: If connection cannot be obtained
        """
        try:
            if not self._database:
                raise ConnectionError("Database not initialized")

            logger.debug("[MongoDB] Database connection acquired")
            return self._database

        except Exception as e:
            raise ConnectionError(f"Failed to get database connection: {str(e)}") from e

    def _return_connection_to_pool(self, connection: Any) -> None:
        """
        Return a connection to the pool (no-op for MongoDB).

        MongoDB manages connections automatically through the client pool.

        Args:
            connection: MongoDB Database object
        """
        # MongoDB handles connection pooling automatically
        logger.debug("[MongoDB] Connection returned (automatic pooling)")

    def _close_pool(self) -> None:
        """Close the MongoDB client and all connections."""
        try:
            if self._client:
                self._client.close()
                logger.debug("[MongoDB] Client closed")

        except Exception as e:
            logger.warning(f"Error closing MongoDB client: {e}")

    def execute_query(self, query: Dict[str, Any], params: Optional[Dict[str, Any]] = None) -> Any:
        """
        Execute a MongoDB operation.

        Args:
            query: Query dict with structure:
                   {
                       "collection": "collection_name",
                       "operation": "find|insert_one|update_many|delete_many|...",
                       "filter": {...},
                       "document": {...},
                       "update": {...},
                       ...
                   }
            params: Additional parameters (merged with query)

        Returns:
            Operation result (cursor, inserted_id, update result, etc.)

        Raises:
            QueryError: If query execution fails
        """
        try:
            if not self._database:
                raise QueryError("No active database connection")

            # Merge params if provided
            if params:
                query = {**query, **params}

            # Get collection
            collection_name = query.get("collection")
            if not collection_name:
                raise QueryError("Collection name not specified in query")

            collection = self._database[collection_name]

            # Execute operation
            operation = query.get("operation", "find")

            if operation == "find":
                # Find documents
                filter_doc = query.get("filter", {})
                projection = query.get("projection")
                sort = query.get("sort")
                limit = query.get("limit")
                skip = query.get("skip")

                cursor = collection.find(filter_doc, projection)

                if sort:
                    cursor = cursor.sort(sort)
                if skip:
                    cursor = cursor.skip(skip)
                if limit:
                    cursor = cursor.limit(limit)

                # Convert cursor to list for easier handling
                result = list(cursor)
                logger.debug(f"[MongoDB] find executed on {collection_name}, found {len(result)} documents")
                return result

            elif operation == "find_one":
                filter_doc = query.get("filter", {})
                projection = query.get("projection")

                result = collection.find_one(filter_doc, projection)
                logger.debug(f"[MongoDB] find_one executed on {collection_name}")
                return result

            elif operation == "insert_one":
                document = query.get("document")
                if not document:
                    raise QueryError("Document not specified for insert_one")

                result = collection.insert_one(document)
                logger.debug(f"[MongoDB] insert_one executed on {collection_name}, id={result.inserted_id}")
                return result

            elif operation == "insert_many":
                documents = query.get("documents")
                if not documents:
                    raise QueryError("Documents not specified for insert_many")

                result = collection.insert_many(documents)
                logger.debug(f"[MongoDB] insert_many executed on {collection_name}, count={len(result.inserted_ids)}")
                return result

            elif operation == "update_one":
                filter_doc = query.get("filter", {})
                update_doc = query.get("update")
                if not update_doc:
                    raise QueryError("Update document not specified for update_one")

                result = collection.update_one(filter_doc, update_doc)
                logger.debug(f"[MongoDB] update_one executed on {collection_name}, modified={result.modified_count}")
                return result

            elif operation == "update_many":
                filter_doc = query.get("filter", {})
                update_doc = query.get("update")
                if not update_doc:
                    raise QueryError("Update document not specified for update_many")

                result = collection.update_many(filter_doc, update_doc)
                logger.debug(f"[MongoDB] update_many executed on {collection_name}, modified={result.modified_count}")
                return result

            elif operation == "delete_one":
                filter_doc = query.get("filter", {})
                result = collection.delete_one(filter_doc)
                logger.debug(f"[MongoDB] delete_one executed on {collection_name}, deleted={result.deleted_count}")
                return result

            elif operation == "delete_many":
                filter_doc = query.get("filter", {})
                result = collection.delete_many(filter_doc)
                logger.debug(f"[MongoDB] delete_many executed on {collection_name}, deleted={result.deleted_count}")
                return result

            elif operation == "count":
                filter_doc = query.get("filter", {})
                result = collection.count_documents(filter_doc)
                logger.debug(f"[MongoDB] count executed on {collection_name}, count={result}")
                return result

            elif operation == "aggregate":
                pipeline = query.get("pipeline", [])
                result = list(collection.aggregate(pipeline))
                logger.debug(f"[MongoDB] aggregate executed on {collection_name}, results={len(result)}")
                return result

            else:
                raise QueryError(f"Unsupported operation: {operation}")

        except PyMongoError as e:
            raise QueryError(f"MongoDB query failed: {str(e)}") from e
        except Exception as e:
            raise QueryError(f"Failed to execute query: {str(e)}") from e

    def get_collection_names(self) -> List[str]:
        """
        Get list of all collection names in the database.

        Returns:
            List of collection names

        Raises:
            QueryError: If query fails
        """
        try:
            if not self._database:
                raise QueryError("No active database connection")

            return self._database.list_collection_names()

        except Exception as e:
            raise QueryError(f"Failed to get collection names: {str(e)}") from e

    def collection_exists(self, collection_name: str) -> bool:
        """
        Check if a collection exists.

        Args:
            collection_name: Name of the collection

        Returns:
            True if collection exists, False otherwise
        """
        return collection_name in self.get_collection_names()

    def create_collection(self, collection_name: str, **options: Any) -> None:
        """
        Create a collection.

        Args:
            collection_name: Name of the collection
            **options: Collection options (e.g., capped, size, max)

        Example:
            adapter.create_collection("users")
            adapter.create_collection("logs", capped=True, size=100000)
        """
        try:
            if not self._database:
                raise QueryError("No active database connection")

            self._database.create_collection(collection_name, **options)
            logger.info(f"[MongoDB] Created collection: {collection_name}")

        except Exception as e:
            raise QueryError(f"Failed to create collection: {str(e)}") from e

    def drop_collection(self, collection_name: str) -> None:
        """
        Drop a collection.

        Args:
            collection_name: Name of the collection
        """
        try:
            if not self._database:
                raise QueryError("No active database connection")

            self._database.drop_collection(collection_name)
            logger.info(f"[MongoDB] Dropped collection: {collection_name}")

        except Exception as e:
            raise QueryError(f"Failed to drop collection: {str(e)}") from e

    def create_index(self, collection_name: str, keys: List[tuple], **options: Any) -> str:
        """
        Create an index on a collection.

        Args:
            collection_name: Name of the collection
            keys: List of (field, direction) tuples
            **options: Index options (e.g., unique, sparse, name)

        Returns:
            Name of the created index

        Example:
            adapter.create_index("users", [("email", 1)], unique=True)
            adapter.create_index("posts", [("user_id", 1), ("created_at", -1)])
        """
        try:
            if not self._database:
                raise QueryError("No active database connection")

            collection = self._database[collection_name]
            index_name = collection.create_index(keys, **options)
            logger.info(f"[MongoDB] Created index on {collection_name}: {index_name}")
            return index_name

        except Exception as e:
            raise QueryError(f"Failed to create index: {str(e)}") from e

    def get_database(self) -> Optional[Database]:
        """
        Get the underlying PyMongo Database object.

        Returns:
            PyMongo Database or None
        """
        return self._database

    def get_client(self) -> Optional[MongoClient]:
        """
        Get the underlying PyMongo MongoClient.

        Returns:
            PyMongo MongoClient or None
        """
        return self._client

"""
Database Adapter Exceptions

Custom exceptions for the Database Adapter FSA module.
"""


class DatabaseAdapterError(Exception):
    """Base exception for all database adapter errors."""

    pass


class ConnectionError(DatabaseAdapterError):
    """Raised when database connection fails."""

    pass


class ConnectionPoolExhausted(DatabaseAdapterError):
    """Raised when connection pool has no available connections."""

    pass


class TransactionError(DatabaseAdapterError):
    """Raised when transaction operations fail."""

    pass


class QueryError(DatabaseAdapterError):
    """Raised when query execution fails."""

    pass


class MigrationError(DatabaseAdapterError):
    """Raised when schema migration fails."""

    pass


class InvalidStateTransition(DatabaseAdapterError):
    """Raised when an invalid FSA state transition is attempted."""

    pass


class ConfigurationError(DatabaseAdapterError):
    """Raised when adapter configuration is invalid."""

    pass


class RetryExhausted(DatabaseAdapterError):
    """Raised when retry attempts are exhausted."""

    pass


class UnsupportedOperation(DatabaseAdapterError):
    """Raised when an operation is not supported by the database type."""

    pass

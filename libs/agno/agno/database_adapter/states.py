"""
Database Adapter FSA States

Finite State Automaton states for database connection lifecycle.
"""

from enum import Enum, auto


class ConnectionState(Enum):
    """
    FSA states for database connection lifecycle.

    State transitions:
    DISCONNECTED -> CONNECTING -> CONNECTED
    CONNECTED -> IN_TRANSACTION -> CONNECTED
    CONNECTED -> DISCONNECTED
    * -> ERROR -> RECONNECTING -> CONNECTING
    """

    DISCONNECTED = auto()
    """No active connection to the database."""

    CONNECTING = auto()
    """Attempting to establish a connection."""

    CONNECTED = auto()
    """Successfully connected and ready for operations."""

    IN_TRANSACTION = auto()
    """Currently in an active transaction."""

    RECONNECTING = auto()
    """Attempting to reconnect after a connection failure."""

    ERROR = auto()
    """Connection is in an error state."""

    CLOSED = auto()
    """Connection pool has been closed and cannot be reused."""


class TransactionState(Enum):
    """States for transaction lifecycle."""

    IDLE = auto()
    """No active transaction."""

    ACTIVE = auto()
    """Transaction is active and accepting operations."""

    COMMITTING = auto()
    """Transaction is being committed."""

    ROLLING_BACK = auto()
    """Transaction is being rolled back."""

    COMMITTED = auto()
    """Transaction has been successfully committed."""

    ROLLED_BACK = auto()
    """Transaction has been rolled back."""

    ERROR = auto()
    """Transaction encountered an error."""


# Valid state transitions for connection FSA
VALID_CONNECTION_TRANSITIONS = {
    ConnectionState.DISCONNECTED: {ConnectionState.CONNECTING},
    ConnectionState.CONNECTING: {ConnectionState.CONNECTED, ConnectionState.ERROR},
    ConnectionState.CONNECTED: {ConnectionState.IN_TRANSACTION, ConnectionState.DISCONNECTED, ConnectionState.ERROR},
    ConnectionState.IN_TRANSACTION: {ConnectionState.CONNECTED, ConnectionState.ERROR},
    ConnectionState.ERROR: {ConnectionState.RECONNECTING, ConnectionState.DISCONNECTED, ConnectionState.CLOSED},
    ConnectionState.RECONNECTING: {ConnectionState.CONNECTING, ConnectionState.ERROR, ConnectionState.CLOSED},
    ConnectionState.CLOSED: set(),  # Terminal state
}

# Valid state transitions for transaction FSA
VALID_TRANSACTION_TRANSITIONS = {
    TransactionState.IDLE: {TransactionState.ACTIVE},
    TransactionState.ACTIVE: {TransactionState.COMMITTING, TransactionState.ROLLING_BACK, TransactionState.ERROR},
    TransactionState.COMMITTING: {TransactionState.COMMITTED, TransactionState.ERROR},
    TransactionState.ROLLING_BACK: {TransactionState.ROLLED_BACK, TransactionState.ERROR},
    TransactionState.COMMITTED: {TransactionState.IDLE},
    TransactionState.ROLLED_BACK: {TransactionState.IDLE},
    TransactionState.ERROR: {TransactionState.IDLE, TransactionState.ROLLING_BACK},
}

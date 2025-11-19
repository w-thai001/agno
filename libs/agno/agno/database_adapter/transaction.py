"""
Transaction Management

Provides ACID transaction support for database operations.
"""

from contextlib import contextmanager
from typing import Any, Generator, Optional

from agno.database_adapter.exceptions import TransactionError
from agno.database_adapter.states import TransactionState, VALID_TRANSACTION_TRANSITIONS
from agno.utils.log import logger


class Transaction:
    """
    Transaction manager for database operations.

    Supports both SQL transactions and MongoDB sessions.
    """

    def __init__(self, connection: Any, db_type: str):
        """
        Initialize transaction manager.

        Args:
            connection: Database connection object
            db_type: Type of database ('postgres', 'mysql', 'sqlite', 'mongodb')
        """
        self.connection = connection
        self.db_type = db_type.lower()
        self.state = TransactionState.IDLE
        self._transaction_obj: Optional[Any] = None
        self._savepoints: list = []

    def _transition_state(self, new_state: TransactionState) -> None:
        """
        Transition to a new state if valid.

        Args:
            new_state: Target state

        Raises:
            TransactionError: If transition is invalid
        """
        if new_state not in VALID_TRANSACTION_TRANSITIONS.get(self.state, set()):
            raise TransactionError(f"Invalid transaction state transition: {self.state} -> {new_state}")

        logger.debug(f"Transaction state transition: {self.state} -> {new_state}")
        self.state = new_state

    def begin(self) -> None:
        """
        Begin a new transaction.

        Raises:
            TransactionError: If transaction cannot be started
        """
        try:
            self._transition_state(TransactionState.ACTIVE)

            if self.db_type == "mongodb":
                # MongoDB uses sessions
                self._transaction_obj = self.connection.start_session()
                self._transaction_obj.start_transaction()
            else:
                # SQL databases
                if hasattr(self.connection, "begin"):
                    self._transaction_obj = self.connection.begin()
                else:
                    # For raw connections
                    self.connection.execute("BEGIN")

            logger.debug("Transaction started")

        except Exception as e:
            self._transition_state(TransactionState.ERROR)
            raise TransactionError(f"Failed to begin transaction: {str(e)}") from e

    def commit(self) -> None:
        """
        Commit the current transaction.

        Raises:
            TransactionError: If commit fails
        """
        try:
            self._transition_state(TransactionState.COMMITTING)

            if self.db_type == "mongodb":
                if self._transaction_obj:
                    self._transaction_obj.commit_transaction()
            else:
                if self._transaction_obj and hasattr(self._transaction_obj, "commit"):
                    self._transaction_obj.commit()
                else:
                    self.connection.execute("COMMIT")

            self._transition_state(TransactionState.COMMITTED)
            logger.debug("Transaction committed")

            # Reset to idle state
            self._transition_state(TransactionState.IDLE)
            self._transaction_obj = None

        except Exception as e:
            self._transition_state(TransactionState.ERROR)
            raise TransactionError(f"Failed to commit transaction: {str(e)}") from e

    def rollback(self) -> None:
        """
        Rollback the current transaction.

        Raises:
            TransactionError: If rollback fails
        """
        try:
            self._transition_state(TransactionState.ROLLING_BACK)

            if self.db_type == "mongodb":
                if self._transaction_obj:
                    self._transaction_obj.abort_transaction()
            else:
                if self._transaction_obj and hasattr(self._transaction_obj, "rollback"):
                    self._transaction_obj.rollback()
                else:
                    self.connection.execute("ROLLBACK")

            self._transition_state(TransactionState.ROLLED_BACK)
            logger.debug("Transaction rolled back")

            # Reset to idle state
            self._transition_state(TransactionState.IDLE)
            self._transaction_obj = None

        except Exception as e:
            self._transition_state(TransactionState.ERROR)
            raise TransactionError(f"Failed to rollback transaction: {str(e)}") from e

    def savepoint(self, name: str) -> None:
        """
        Create a savepoint within the transaction (SQL only).

        Args:
            name: Name of the savepoint

        Raises:
            TransactionError: If savepoint creation fails
        """
        if self.db_type == "mongodb":
            raise TransactionError("Savepoints are not supported in MongoDB")

        if self.state != TransactionState.ACTIVE:
            raise TransactionError("Cannot create savepoint outside of active transaction")

        try:
            self.connection.execute(f"SAVEPOINT {name}")
            self._savepoints.append(name)
            logger.debug(f"Savepoint created: {name}")

        except Exception as e:
            raise TransactionError(f"Failed to create savepoint: {str(e)}") from e

    def rollback_to_savepoint(self, name: str) -> None:
        """
        Rollback to a specific savepoint (SQL only).

        Args:
            name: Name of the savepoint

        Raises:
            TransactionError: If rollback to savepoint fails
        """
        if self.db_type == "mongodb":
            raise TransactionError("Savepoints are not supported in MongoDB")

        if name not in self._savepoints:
            raise TransactionError(f"Savepoint not found: {name}")

        try:
            self.connection.execute(f"ROLLBACK TO SAVEPOINT {name}")
            logger.debug(f"Rolled back to savepoint: {name}")

        except Exception as e:
            raise TransactionError(f"Failed to rollback to savepoint: {str(e)}") from e

    def release_savepoint(self, name: str) -> None:
        """
        Release a savepoint (SQL only).

        Args:
            name: Name of the savepoint

        Raises:
            TransactionError: If release fails
        """
        if self.db_type == "mongodb":
            raise TransactionError("Savepoints are not supported in MongoDB")

        if name not in self._savepoints:
            raise TransactionError(f"Savepoint not found: {name}")

        try:
            self.connection.execute(f"RELEASE SAVEPOINT {name}")
            self._savepoints.remove(name)
            logger.debug(f"Savepoint released: {name}")

        except Exception as e:
            raise TransactionError(f"Failed to release savepoint: {str(e)}") from e

    def is_active(self) -> bool:
        """Check if transaction is currently active."""
        return self.state == TransactionState.ACTIVE

    def __enter__(self) -> "Transaction":
        """Context manager entry - begin transaction."""
        self.begin()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        """Context manager exit - commit or rollback."""
        if exc_type is None:
            # No exception, commit
            self.commit()
        else:
            # Exception occurred, rollback
            logger.warning(f"Transaction rolled back due to exception: {exc_val}")
            try:
                self.rollback()
            except Exception as rollback_error:
                logger.error(f"Failed to rollback transaction: {rollback_error}")

        return False  # Propagate exception if any


@contextmanager
def transaction(connection: Any, db_type: str) -> Generator[Transaction, None, None]:
    """
    Context manager for database transactions.

    Args:
        connection: Database connection
        db_type: Type of database

    Yields:
        Transaction object

    Example:
        with transaction(conn, 'postgres') as txn:
            # Perform operations
            conn.execute("INSERT INTO ...")
            # Auto-commit on success, auto-rollback on exception
    """
    txn = Transaction(connection, db_type)
    try:
        txn.begin()
        yield txn
        txn.commit()
    except Exception as e:
        logger.error(f"Transaction failed: {e}")
        try:
            txn.rollback()
        except Exception as rollback_error:
            logger.error(f"Failed to rollback transaction: {rollback_error}")
        raise

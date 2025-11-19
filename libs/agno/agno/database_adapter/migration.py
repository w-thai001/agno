"""
Schema Migration Support

Provides automatic schema migration and versioning for database schemas.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from agno.database_adapter.exceptions import MigrationError
from agno.utils.log import logger


class Migration(ABC):
    """Base class for database migrations."""

    def __init__(self, version: int, description: str):
        """
        Initialize migration.

        Args:
            version: Migration version number
            description: Description of the migration
        """
        self.version = version
        self.description = description
        self.applied_at: Optional[datetime] = None

    @abstractmethod
    def up(self, connection: Any) -> None:
        """
        Apply the migration.

        Args:
            connection: Database connection

        Raises:
            MigrationError: If migration fails
        """
        raise NotImplementedError

    @abstractmethod
    def down(self, connection: Any) -> None:
        """
        Revert the migration.

        Args:
            connection: Database connection

        Raises:
            MigrationError: If rollback fails
        """
        raise NotImplementedError


class MigrationManager:
    """
    Manages database schema migrations.

    Tracks applied migrations and applies pending ones in order.
    """

    def __init__(self, connection: Any, db_type: str, migrations_table: str = "schema_migrations"):
        """
        Initialize migration manager.

        Args:
            connection: Database connection
            db_type: Type of database ('postgres', 'mysql', 'sqlite', 'mongodb')
            migrations_table: Name of the table to track migrations
        """
        self.connection = connection
        self.db_type = db_type.lower()
        self.migrations_table = migrations_table
        self.migrations: List[Migration] = []

    def register(self, migration: Migration) -> None:
        """
        Register a migration.

        Args:
            migration: Migration instance to register
        """
        self.migrations.append(migration)
        # Keep migrations sorted by version
        self.migrations.sort(key=lambda m: m.version)
        logger.debug(f"Registered migration v{migration.version}: {migration.description}")

    def _create_migrations_table(self) -> None:
        """Create the migrations tracking table if it doesn't exist."""
        try:
            if self.db_type == "mongodb":
                # MongoDB doesn't need a special table, we'll use a collection
                pass
            else:
                # SQL databases
                if self.db_type == "postgres":
                    sql = f"""
                    CREATE TABLE IF NOT EXISTS {self.migrations_table} (
                        version INTEGER PRIMARY KEY,
                        description TEXT NOT NULL,
                        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                elif self.db_type == "mysql":
                    sql = f"""
                    CREATE TABLE IF NOT EXISTS {self.migrations_table} (
                        version INT PRIMARY KEY,
                        description TEXT NOT NULL,
                        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                else:  # sqlite
                    sql = f"""
                    CREATE TABLE IF NOT EXISTS {self.migrations_table} (
                        version INTEGER PRIMARY KEY,
                        description TEXT NOT NULL,
                        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """

                if hasattr(self.connection, "execute"):
                    self.connection.execute(sql)
                    if hasattr(self.connection, "commit"):
                        self.connection.commit()

            logger.debug(f"Migrations table '{self.migrations_table}' ready")

        except Exception as e:
            raise MigrationError(f"Failed to create migrations table: {str(e)}") from e

    def _get_applied_versions(self) -> List[int]:
        """
        Get list of applied migration versions.

        Returns:
            List of applied version numbers
        """
        try:
            if self.db_type == "mongodb":
                # MongoDB implementation
                db = self.connection
                collection = db[self.migrations_table]
                results = collection.find({}, {"version": 1})
                return [r["version"] for r in results]
            else:
                # SQL implementation
                sql = f"SELECT version FROM {self.migrations_table} ORDER BY version"
                if hasattr(self.connection, "execute"):
                    result = self.connection.execute(sql)
                    return [row[0] for row in result.fetchall()]
                return []

        except Exception as e:
            # If table doesn't exist, return empty list
            logger.debug(f"Error getting applied versions: {e}")
            return []

    def _mark_migration_applied(self, migration: Migration) -> None:
        """
        Mark a migration as applied.

        Args:
            migration: Migration that was applied
        """
        try:
            if self.db_type == "mongodb":
                db = self.connection
                collection = db[self.migrations_table]
                collection.insert_one(
                    {"version": migration.version, "description": migration.description, "applied_at": datetime.now()}
                )
            else:
                sql = f"INSERT INTO {self.migrations_table} (version, description) VALUES (?, ?)"
                if self.db_type == "postgres":
                    sql = f"INSERT INTO {self.migrations_table} (version, description) VALUES (%s, %s)"

                if hasattr(self.connection, "execute"):
                    self.connection.execute(sql, (migration.version, migration.description))
                    if hasattr(self.connection, "commit"):
                        self.connection.commit()

            logger.info(f"Marked migration v{migration.version} as applied")

        except Exception as e:
            raise MigrationError(f"Failed to mark migration as applied: {str(e)}") from e

    def _mark_migration_reverted(self, version: int) -> None:
        """
        Remove a migration from applied list.

        Args:
            version: Version number to remove
        """
        try:
            if self.db_type == "mongodb":
                db = self.connection
                collection = db[self.migrations_table]
                collection.delete_one({"version": version})
            else:
                sql = f"DELETE FROM {self.migrations_table} WHERE version = ?"
                if self.db_type == "postgres":
                    sql = f"DELETE FROM {self.migrations_table} WHERE version = %s"

                if hasattr(self.connection, "execute"):
                    self.connection.execute(sql, (version,))
                    if hasattr(self.connection, "commit"):
                        self.connection.commit()

            logger.info(f"Marked migration v{version} as reverted")

        except Exception as e:
            raise MigrationError(f"Failed to mark migration as reverted: {str(e)}") from e

    def migrate(self, target_version: Optional[int] = None) -> None:
        """
        Apply pending migrations up to target version.

        Args:
            target_version: Target version to migrate to (None = latest)

        Raises:
            MigrationError: If migration fails
        """
        try:
            # Ensure migrations table exists
            self._create_migrations_table()

            # Get applied versions
            applied_versions = self._get_applied_versions()

            # Determine which migrations to apply
            pending_migrations = [m for m in self.migrations if m.version not in applied_versions]

            if target_version is not None:
                pending_migrations = [m for m in pending_migrations if m.version <= target_version]

            if not pending_migrations:
                logger.info("No pending migrations to apply")
                return

            logger.info(f"Applying {len(pending_migrations)} pending migration(s)")

            # Apply each migration
            for migration in pending_migrations:
                logger.info(f"Applying migration v{migration.version}: {migration.description}")
                try:
                    migration.up(self.connection)
                    self._mark_migration_applied(migration)
                    logger.info(f"Successfully applied migration v{migration.version}")
                except Exception as e:
                    raise MigrationError(f"Failed to apply migration v{migration.version}: {str(e)}") from e

            logger.info("All migrations applied successfully")

        except Exception as e:
            raise MigrationError(f"Migration failed: {str(e)}") from e

    def rollback(self, target_version: Optional[int] = None, steps: int = 1) -> None:
        """
        Rollback migrations.

        Args:
            target_version: Target version to rollback to (None = use steps)
            steps: Number of migrations to rollback (default: 1)

        Raises:
            MigrationError: If rollback fails
        """
        try:
            # Get applied versions
            applied_versions = sorted(self._get_applied_versions(), reverse=True)

            if not applied_versions:
                logger.info("No migrations to rollback")
                return

            # Determine which migrations to rollback
            if target_version is not None:
                versions_to_rollback = [v for v in applied_versions if v > target_version]
            else:
                versions_to_rollback = applied_versions[:steps]

            if not versions_to_rollback:
                logger.info("No migrations to rollback")
                return

            logger.info(f"Rolling back {len(versions_to_rollback)} migration(s)")

            # Rollback each migration
            for version in versions_to_rollback:
                migration = next((m for m in self.migrations if m.version == version), None)
                if not migration:
                    raise MigrationError(f"Migration v{version} not found")

                logger.info(f"Rolling back migration v{version}: {migration.description}")
                try:
                    migration.down(self.connection)
                    self._mark_migration_reverted(version)
                    logger.info(f"Successfully rolled back migration v{version}")
                except Exception as e:
                    raise MigrationError(f"Failed to rollback migration v{version}: {str(e)}") from e

            logger.info("Rollback completed successfully")

        except Exception as e:
            raise MigrationError(f"Rollback failed: {str(e)}") from e

    def get_current_version(self) -> Optional[int]:
        """
        Get the current schema version.

        Returns:
            Current version number or None if no migrations applied
        """
        applied_versions = self._get_applied_versions()
        return max(applied_versions) if applied_versions else None

    def get_pending_migrations(self) -> List[Migration]:
        """
        Get list of pending migrations.

        Returns:
            List of pending Migration objects
        """
        applied_versions = self._get_applied_versions()
        return [m for m in self.migrations if m.version not in applied_versions]

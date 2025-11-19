"""
Database Adapter FSA - Schema Migrations

This example demonstrates schema migration support with versioning
and automatic migration management.
"""

from agno.database_adapter import Migration, SQLiteAdapter
from agno.utils.log import logger


# Define migrations
class CreateUsersTable(Migration):
    """Migration v1: Create users table."""

    def __init__(self):
        super().__init__(version=1, description="Create users table")

    def up(self, connection):
        """Apply migration."""
        logger.info("Applying migration v1: Create users table")
        connection.execute(
            """
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )
        logger.info("Users table created")

    def down(self, connection):
        """Rollback migration."""
        logger.info("Rolling back migration v1: Drop users table")
        connection.execute("DROP TABLE IF EXISTS users")
        logger.info("Users table dropped")


class AddUserProfiles(Migration):
    """Migration v2: Add user profiles table."""

    def __init__(self):
        super().__init__(version=2, description="Add user profiles table")

    def up(self, connection):
        """Apply migration."""
        logger.info("Applying migration v2: Create profiles table")
        connection.execute(
            """
            CREATE TABLE profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                bio TEXT,
                avatar_url TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """
        )
        logger.info("Profiles table created")

    def down(self, connection):
        """Rollback migration."""
        logger.info("Rolling back migration v2: Drop profiles table")
        connection.execute("DROP TABLE IF EXISTS profiles")
        logger.info("Profiles table dropped")


class AddUserAgeColumn(Migration):
    """Migration v3: Add age column to users table."""

    def __init__(self):
        super().__init__(version=3, description="Add age column to users table")

    def up(self, connection):
        """Apply migration."""
        logger.info("Applying migration v3: Add age column")
        connection.execute("ALTER TABLE users ADD COLUMN age INTEGER")
        logger.info("Age column added")

    def down(self, connection):
        """Rollback migration."""
        logger.info("Rolling back migration v3: Remove age column")
        # SQLite doesn't support DROP COLUMN directly, need to recreate table
        connection.execute(
            """
            CREATE TABLE users_backup (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )
        connection.execute("INSERT INTO users_backup SELECT id, username, email, created_at FROM users")
        connection.execute("DROP TABLE users")
        connection.execute("ALTER TABLE users_backup RENAME TO users")
        logger.info("Age column removed")


class CreatePostsTable(Migration):
    """Migration v4: Create posts table."""

    def __init__(self):
        super().__init__(version=4, description="Create posts table")

    def up(self, connection):
        """Apply migration."""
        logger.info("Applying migration v4: Create posts table")
        connection.execute(
            """
            CREATE TABLE posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                content TEXT,
                published BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """
        )
        logger.info("Posts table created")

    def down(self, connection):
        """Rollback migration."""
        logger.info("Rolling back migration v4: Drop posts table")
        connection.execute("DROP TABLE IF EXISTS posts")
        logger.info("Posts table dropped")


def migration_example():
    """Example demonstrating schema migrations."""
    logger.info("=== Schema Migration Example ===\n")

    # Create adapter with in-memory database
    adapter = SQLiteAdapter(database_path=":memory:")

    # Get migration manager
    migration_mgr = adapter.get_migration_manager()

    # Register all migrations
    logger.info("Registering migrations...")
    migration_mgr.register(CreateUsersTable())
    migration_mgr.register(AddUserProfiles())
    migration_mgr.register(AddUserAgeColumn())
    migration_mgr.register(CreatePostsTable())
    logger.info(f"Registered {len(migration_mgr.migrations)} migrations\n")

    # Check current version
    current_version = migration_mgr.get_current_version()
    logger.info(f"Current schema version: {current_version}\n")

    # Get pending migrations
    pending = migration_mgr.get_pending_migrations()
    logger.info(f"Pending migrations: {len(pending)}")
    for mig in pending:
        logger.info(f"  - v{mig.version}: {mig.description}")
    logger.info("")

    # Apply all migrations
    logger.info("=== Applying Migrations ===")
    migration_mgr.migrate()
    logger.info("")

    # Check version after migration
    current_version = migration_mgr.get_current_version()
    logger.info(f"Schema version after migration: {current_version}\n")

    # Verify tables were created
    tables = adapter.get_table_names()
    logger.info(f"Tables in database: {tables}\n")

    # Insert some test data
    logger.info("=== Inserting Test Data ===")
    adapter.execute(
        "INSERT INTO users (username, email, age) VALUES (:username, :email, :age)",
        {"username": "alice", "email": "alice@example.com", "age": 30},
    )

    adapter.execute(
        "INSERT INTO users (username, email, age) VALUES (:username, :email, :age)",
        {"username": "bob", "email": "bob@example.com", "age": 25},
    )

    logger.info("Inserted 2 users")

    # Query data
    users = adapter.fetch_all("SELECT * FROM users")
    logger.info(f"Users in database: {len(users)}")
    for user in users:
        logger.info(f"  - {user['username']} ({user['email']}) - Age: {user['age']}")
    logger.info("")

    # Rollback last migration
    logger.info("=== Rolling Back Last Migration ===")
    migration_mgr.rollback(steps=1)
    logger.info("")

    # Check version after rollback
    current_version = migration_mgr.get_current_version()
    logger.info(f"Schema version after rollback: {current_version}\n")

    # Verify table was dropped
    tables = adapter.get_table_names()
    logger.info(f"Tables after rollback: {tables}\n")
    assert "posts" not in tables, "Posts table should have been dropped"

    # Rollback to specific version
    logger.info("=== Rolling Back to Version 1 ===")
    migration_mgr.rollback(target_version=1)
    logger.info("")

    # Check final version
    current_version = migration_mgr.get_current_version()
    logger.info(f"Final schema version: {current_version}\n")

    # Verify only users table remains
    tables = adapter.get_table_names()
    logger.info(f"Tables after rollback to v1: {tables}\n")

    # Re-apply migrations to version 3
    logger.info("=== Migrating to Version 3 ===")
    migration_mgr.migrate(target_version=3)
    logger.info("")

    current_version = migration_mgr.get_current_version()
    logger.info(f"Schema version: {current_version}")

    tables = adapter.get_table_names()
    logger.info(f"Tables: {tables}\n")

    # Cleanup
    adapter.close()
    logger.info("=== Migration Example Completed ===")


if __name__ == "__main__":
    migration_example()

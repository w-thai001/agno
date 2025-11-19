"""Bad controller with architecture violations."""

import sqlalchemy  # VIOLATION: Direct database import in presentation layer
from repositories.user_repository import UserRepository  # Should go through service layer


class BadController:
    """Example of poor architecture - direct database access."""

    def __init__(self):
        # VIOLATION: Presentation layer directly accessing repository
        self.user_repo = UserRepository()
        self.db_engine = sqlalchemy.create_engine("sqlite:///:memory:")

    def get_user(self, user_id: int):
        """Get user directly from database."""
        # VIOLATION: SQL in presentation layer
        query = f"SELECT * FROM users WHERE id = {user_id}"
        return self.db_engine.execute(query)

    def create_user(self, data: dict):
        """Create user with direct DB access."""
        return self.user_repo.save(data)

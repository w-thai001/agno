"""User service - Business logic layer."""

from repositories.user_repository import UserRepository


class UserService:
    """Business logic for user operations."""

    def __init__(self):
        self.repository = UserRepository()

    def get_user(self, user_id: int):
        """Get user with business logic."""
        user = self.repository.find_by_id(user_id)
        if user:
            return self._format_user(user)
        return None

    def create_user(self, data: dict):
        """Create user with validation."""
        if not self._validate_user_data(data):
            raise ValueError("Invalid user data")
        return self.repository.save(data)

    def update_user(self, user_id: int, data: dict):
        """Update user with validation."""
        if not self._validate_user_data(data):
            raise ValueError("Invalid user data")
        return self.repository.update(user_id, data)

    def delete_user(self, user_id: int):
        """Delete user with business rules."""
        user = self.repository.find_by_id(user_id)
        if user and user.get("is_active"):
            raise ValueError("Cannot delete active user")
        return self.repository.delete(user_id)

    def _validate_user_data(self, data: dict) -> bool:
        """Validate user data."""
        return "name" in data and "email" in data

    def _format_user(self, user: dict) -> dict:
        """Format user data for presentation."""
        return {
            "id": user.get("id"),
            "name": user.get("name"),
            "email": user.get("email"),
        }

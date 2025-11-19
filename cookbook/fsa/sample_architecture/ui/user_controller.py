"""User controller - Presentation layer."""

from services.user_service import UserService


class UserController:
    """Handles user-related HTTP requests."""

    def __init__(self):
        self.user_service = UserService()

    def get_user(self, user_id: int):
        """Get user by ID."""
        return self.user_service.get_user(user_id)

    def create_user(self, data: dict):
        """Create a new user."""
        return self.user_service.create_user(data)

    def update_user(self, user_id: int, data: dict):
        """Update user information."""
        return self.user_service.update_user(user_id, data)

    def delete_user(self, user_id: int):
        """Delete a user."""
        return self.user_service.delete_user(user_id)

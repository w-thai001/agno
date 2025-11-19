"""User repository - Data access layer."""


class UserRepository:
    """Handles user data persistence."""

    def __init__(self):
        self.users = {}
        self.next_id = 1

    def find_by_id(self, user_id: int):
        """Find user by ID."""
        return self.users.get(user_id)

    def find_all(self):
        """Get all users."""
        return list(self.users.values())

    def save(self, user_data: dict):
        """Save new user."""
        user_id = self.next_id
        self.next_id += 1
        user_data["id"] = user_id
        self.users[user_id] = user_data
        return user_data

    def update(self, user_id: int, user_data: dict):
        """Update existing user."""
        if user_id in self.users:
            self.users[user_id].update(user_data)
            return self.users[user_id]
        return None

    def delete(self, user_id: int):
        """Delete user."""
        if user_id in self.users:
            del self.users[user_id]
            return True
        return False

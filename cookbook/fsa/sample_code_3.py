"""Sample code file 3 - String utilities with duplication."""


class StringUtils:
    """Utility functions for string manipulation."""

    @staticmethod
    def reverse_string(s: str) -> str:
        """Reverse a string."""
        if not isinstance(s, str):
            raise TypeError("Input must be a string")
        return s[::-1]

    @staticmethod
    def is_palindrome(s: str) -> bool:
        """Check if a string is a palindrome."""
        if not isinstance(s, str):
            raise TypeError("Input must be a string")
        cleaned = s.lower().replace(" ", "")
        return cleaned == cleaned[::-1]

    @staticmethod
    def count_vowels(s: str) -> int:
        """Count vowels in a string."""
        if not isinstance(s, str):
            raise TypeError("Input must be a string")
        vowels = "aeiouAEIOU"
        count = 0
        for char in s:
            if char in vowels:
                count += 1
        return count

    @staticmethod
    def count_consonants(s: str) -> int:
        """Count consonants in a string."""
        if not isinstance(s, str):
            raise TypeError("Input must be a string")
        consonants = "bcdfghjklmnpqrstvwxyzBCDFGHJKLMNPQRSTVWXYZ"
        count = 0
        for char in s:
            if char in consonants:
                count += 1
        return count

    @staticmethod
    def to_title_case(s: str) -> str:
        """Convert string to title case."""
        if not isinstance(s, str):
            raise TypeError("Input must be a string")
        words = s.split()
        return " ".join(word.capitalize() for word in words)

    @staticmethod
    def remove_duplicates(s: str) -> str:
        """Remove duplicate characters from string."""
        if not isinstance(s, str):
            raise TypeError("Input must be a string")
        seen = set()
        result = []
        for char in s:
            if char not in seen:
                seen.add(char)
                result.append(char)
        return "".join(result)


# Intentional duplication for demonstration
def validate_string_input(value):
    """Validate string input."""
    if not isinstance(value, str):
        raise TypeError("Input must be a string")
    return True


def process_string(value):
    """Process a string value."""
    if not isinstance(value, str):
        raise TypeError("Input must be a string")
    return value.strip().lower()

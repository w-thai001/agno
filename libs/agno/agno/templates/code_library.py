"""
FSA-1.2: Code Template Library

Provides a library of reusable code templates for common patterns,
best practices, and validation test cases.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional


class TemplateCategory(Enum):
    """Categories of code templates."""

    API_ENDPOINT = "api_endpoint"
    DATABASE_QUERY = "database_query"
    ERROR_HANDLING = "error_handling"
    AUTHENTICATION = "authentication"
    DATA_VALIDATION = "data_validation"
    ASYNC_OPERATIONS = "async_operations"
    UTILITIES = "utilities"
    SECURITY = "security"
    PERFORMANCE = "performance"
    TESTING = "testing"


class QualityLevel(Enum):
    """Quality levels for templates."""

    EXCELLENT = "excellent"  # 90-100
    GOOD = "good"  # 70-89
    FAIR = "fair"  # 50-69
    POOR = "poor"  # <50


@dataclass
class CodeTemplate:
    """A reusable code template."""

    id: str
    name: str
    description: str
    language: str
    category: TemplateCategory
    code: str
    quality_level: QualityLevel
    tags: List[str] = field(default_factory=list)
    best_practices: List[str] = field(default_factory=list)
    security_notes: List[str] = field(default_factory=list)
    performance_notes: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict = field(default_factory=dict)


class CodeTemplateLibrary:
    """
    Library for storing and retrieving code templates.

    Provides templates for common patterns, best practices examples,
    and test cases for validation.
    """

    def __init__(self):
        """Initialize the code template library with built-in templates."""
        self.templates: Dict[str, CodeTemplate] = {}
        self._initialize_builtin_templates()

    def _initialize_builtin_templates(self):
        """Initialize library with built-in templates."""

        # Python Templates
        self.add_template(
            CodeTemplate(
                id="py_api_good",
                name="Python API Endpoint (Good)",
                description="Well-structured Flask API endpoint with error handling",
                language="python",
                category=TemplateCategory.API_ENDPOINT,
                quality_level=QualityLevel.GOOD,
                code='''from flask import Flask, jsonify, request
from typing import Dict, Any
import logging

app = Flask(__name__)
logger = logging.getLogger(__name__)

@app.route('/api/users/<int:user_id>', methods=['GET'])
def get_user(user_id: int) -> Dict[str, Any]:
    """
    Retrieve user information by ID.

    Args:
        user_id: The ID of the user to retrieve

    Returns:
        JSON response with user data
    """
    try:
        # Validate input
        if user_id <= 0:
            return jsonify({"error": "Invalid user ID"}), 400

        # Fetch user (simplified)
        user = {"id": user_id, "name": "John Doe", "email": "john@example.com"}

        return jsonify({"success": True, "data": user}), 200

    except Exception as e:
        logger.error(f"Error fetching user {user_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
''',
                tags=["flask", "api", "error-handling"],
                best_practices=[
                    "Type hints for parameters and return values",
                    "Comprehensive error handling",
                    "Input validation",
                    "Proper HTTP status codes",
                    "Logging for debugging",
                ],
                security_notes=["Input validation prevents injection", "Error messages don't leak sensitive info"],
            )
        )

        self.add_template(
            CodeTemplate(
                id="py_api_poor",
                name="Python API Endpoint (Poor)",
                description="Poorly written API endpoint with security issues",
                language="python",
                category=TemplateCategory.API_ENDPOINT,
                quality_level=QualityLevel.POOR,
                code='''from flask import Flask, jsonify
app = Flask(__name__)

@app.route('/api/users/<user_id>')
def get_user(user_id):
    # No error handling, no validation
    user = eval("get_user_from_db(" + user_id + ")")
    return jsonify(user)
''',
                tags=["flask", "api", "anti-pattern"],
                security_notes=[
                    "CRITICAL: Uses eval() - code injection vulnerability",
                    "No input validation",
                    "No error handling",
                    "Missing type hints",
                ],
            )
        )

        self.add_template(
            CodeTemplate(
                id="py_db_query_good",
                name="Python Database Query (Good)",
                description="Secure database query with parameterization",
                language="python",
                category=TemplateCategory.DATABASE_QUERY,
                quality_level=QualityLevel.EXCELLENT,
                code='''import sqlite3
from typing import Optional, Dict, Any
from contextlib import contextmanager

@contextmanager
def get_db_connection():
    """Context manager for database connections."""
    conn = sqlite3.connect('database.db')
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """
    Fetch user by email address.

    Args:
        email: User's email address

    Returns:
        User data dict or None if not found
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Use parameterized query to prevent SQL injection
        cursor.execute(
            "SELECT id, name, email FROM users WHERE email = ?",
            (email,)
        )
        row = cursor.fetchone()

        if row:
            return {
                "id": row[0],
                "name": row[1],
                "email": row[2]
            }
        return None
''',
                tags=["database", "sql", "security"],
                best_practices=[
                    "Parameterized queries prevent SQL injection",
                    "Context manager for connection handling",
                    "Type hints for clarity",
                    "Proper resource cleanup",
                    "Transaction management",
                ],
                security_notes=["Parameterized queries are safe from SQL injection"],
            )
        )

        self.add_template(
            CodeTemplate(
                id="py_db_query_poor",
                name="Python Database Query (Poor)",
                description="Insecure database query with SQL injection vulnerability",
                language="python",
                category=TemplateCategory.DATABASE_QUERY,
                quality_level=QualityLevel.POOR,
                code='''import sqlite3

def get_user_by_email(email):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    # SQL injection vulnerability!
    query = "SELECT * FROM users WHERE email = '" + email + "'"
    cursor.execute(query)
    return cursor.fetchone()
''',
                tags=["database", "sql", "anti-pattern", "security-issue"],
                security_notes=[
                    "CRITICAL: SQL injection vulnerability",
                    "String concatenation in SQL queries is dangerous",
                    "No input sanitization",
                    "Connection not properly closed",
                ],
            )
        )

        # JavaScript Templates
        self.add_template(
            CodeTemplate(
                id="js_async_good",
                name="JavaScript Async Operation (Good)",
                description="Proper async/await with error handling",
                language="javascript",
                category=TemplateCategory.ASYNC_OPERATIONS,
                quality_level=QualityLevel.EXCELLENT,
                code='''/**
 * Fetch user data from API
 * @param {number} userId - The user ID to fetch
 * @returns {Promise<Object>} User data object
 * @throws {Error} If the request fails
 */
async function fetchUserData(userId) {
    try {
        // Validate input
        if (!userId || userId <= 0) {
            throw new Error('Invalid user ID');
        }

        const response = await fetch(`/api/users/${userId}`);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        return data;

    } catch (error) {
        console.error('Error fetching user data:', error);
        throw error;
    }
}

// Usage example
async function displayUser() {
    try {
        const user = await fetchUserData(123);
        console.log('User:', user);
    } catch (error) {
        console.error('Failed to display user:', error.message);
    }
}
''',
                tags=["async", "fetch", "error-handling"],
                best_practices=[
                    "Async/await for clean asynchronous code",
                    "Comprehensive error handling",
                    "Input validation",
                    "JSDoc documentation",
                    "Proper error propagation",
                ],
            )
        )

        self.add_template(
            CodeTemplate(
                id="js_async_poor",
                name="JavaScript Async Operation (Poor)",
                description="Poor async handling with callback hell",
                language="javascript",
                category=TemplateCategory.ASYNC_OPERATIONS,
                quality_level=QualityLevel.POOR,
                code='''function fetchUserData(userId, callback) {
    fetch('/api/users/' + userId).then(response => {
        response.json().then(data => {
            callback(data);
        });
    });
}

// No error handling, callback hell
fetchUserData(123, function(user) {
    console.log(user);
});
''',
                tags=["async", "anti-pattern", "callback-hell"],
                best_practices=[],
                security_notes=["No error handling", "Callback hell pattern", "No input validation"],
            )
        )

        self.add_template(
            CodeTemplate(
                id="js_xss_vulnerable",
                name="JavaScript XSS Vulnerable Code",
                description="Code vulnerable to XSS attacks",
                language="javascript",
                category=TemplateCategory.SECURITY,
                quality_level=QualityLevel.POOR,
                code='''function displayUserInput(input) {
    // XSS vulnerability - directly inserting user input into DOM
    document.getElementById('output').innerHTML = input;
}

// This allows malicious scripts to execute
const userInput = '<script>alert("XSS")</script>';
displayUserInput(userInput);
''',
                tags=["xss", "security-issue", "anti-pattern"],
                security_notes=[
                    "CRITICAL: XSS vulnerability",
                    "Never use innerHTML with user input",
                    "Use textContent or sanitize input",
                ],
            )
        )

        self.add_template(
            CodeTemplate(
                id="py_error_handling_good",
                name="Python Error Handling (Good)",
                description="Comprehensive error handling pattern",
                language="python",
                category=TemplateCategory.ERROR_HANDLING,
                quality_level=QualityLevel.EXCELLENT,
                code='''import logging
from typing import Optional, Dict, Any
from functools import wraps

logger = logging.getLogger(__name__)

class APIError(Exception):
    """Base exception for API errors."""
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

class ValidationError(APIError):
    """Exception for validation errors."""
    def __init__(self, message: str):
        super().__init__(message, status_code=400)

def handle_errors(func):
    """Decorator for consistent error handling."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValidationError as e:
            logger.warning(f"Validation error in {func.__name__}: {e.message}")
            return {"error": e.message, "status": e.status_code}
        except APIError as e:
            logger.error(f"API error in {func.__name__}: {e.message}")
            return {"error": e.message, "status": e.status_code}
        except Exception as e:
            logger.exception(f"Unexpected error in {func.__name__}")
            return {"error": "Internal server error", "status": 500}
    return wrapper

@handle_errors
def process_user_data(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process user data with error handling."""
    if not user_data.get('email'):
        raise ValidationError("Email is required")

    # Process data...
    return {"success": True, "data": user_data}
''',
                tags=["error-handling", "exceptions", "decorator"],
                best_practices=[
                    "Custom exception hierarchy",
                    "Decorator for consistent error handling",
                    "Appropriate logging levels",
                    "Type hints throughout",
                    "Clear error messages",
                ],
            )
        )

    def add_template(self, template: CodeTemplate):
        """
        Add a template to the library.

        Args:
            template: The CodeTemplate to add
        """
        self.templates[template.id] = template

    def get_template(self, template_id: str) -> Optional[CodeTemplate]:
        """
        Retrieve a template by ID.

        Args:
            template_id: The ID of the template to retrieve

        Returns:
            CodeTemplate if found, None otherwise
        """
        return self.templates.get(template_id)

    def get_templates_by_language(self, language: str) -> List[CodeTemplate]:
        """
        Get all templates for a specific language.

        Args:
            language: Programming language (python, javascript, etc.)

        Returns:
            List of templates for the specified language
        """
        return [t for t in self.templates.values() if t.language.lower() == language.lower()]

    def get_templates_by_category(self, category: TemplateCategory) -> List[CodeTemplate]:
        """
        Get all templates in a specific category.

        Args:
            category: The template category

        Returns:
            List of templates in the category
        """
        return [t for t in self.templates.values() if t.category == category]

    def get_templates_by_quality(self, quality_level: QualityLevel) -> List[CodeTemplate]:
        """
        Get all templates with a specific quality level.

        Args:
            quality_level: The quality level to filter by

        Returns:
            List of templates with the specified quality level
        """
        return [t for t in self.templates.values() if t.quality_level == quality_level]

    def get_all_templates(self) -> List[CodeTemplate]:
        """
        Get all templates in the library.

        Returns:
            List of all templates
        """
        return list(self.templates.values())

    def search_templates(self, query: str, language: Optional[str] = None) -> List[CodeTemplate]:
        """
        Search templates by name, description, or tags.

        Args:
            query: Search query string
            language: Optional language filter

        Returns:
            List of matching templates
        """
        query_lower = query.lower()
        results = []

        for template in self.templates.values():
            # Filter by language if specified
            if language and template.language.lower() != language.lower():
                continue

            # Search in name, description, and tags
            if (
                query_lower in template.name.lower()
                or query_lower in template.description.lower()
                or any(query_lower in tag.lower() for tag in template.tags)
            ):
                results.append(template)

        return results

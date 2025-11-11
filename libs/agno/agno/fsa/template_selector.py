"""
FSA-1.2: TemplateSelector

Selects appropriate code templates based on task requirements.
Maintains a library of code patterns and templates for different
types of implementations.
"""

from typing import Dict, List, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field
from agno.utils.log import logger


class TemplateType(str, Enum):
    """Types of code templates"""
    API_SERVER = "api_server"
    DATABASE_LAYER = "database_layer"
    AUTHENTICATION = "authentication"
    ERROR_HANDLING = "error_handling"
    MIDDLEWARE = "middleware"
    ROUTING = "routing"
    VALIDATION = "validation"
    LOGGING = "logging"
    TESTING = "testing"
    CONFIGURATION = "configuration"


class CodeTemplate(BaseModel):
    """A code template with metadata"""
    name: str = Field(..., description="Template name")
    type: TemplateType = Field(..., description="Template type")
    description: str = Field(..., description="Template description")
    pattern: str = Field(..., description="Code pattern/template")
    dependencies: List[str] = Field(default_factory=list, description="Required dependencies")
    best_practices: List[str] = Field(default_factory=list, description="Best practices")
    tags: List[str] = Field(default_factory=list, description="Template tags")


class TemplateSelection(BaseModel):
    """Result of template selection"""
    selected_templates: List[CodeTemplate] = Field(..., description="Selected templates")
    rationale: str = Field(..., description="Selection rationale")
    confidence: float = Field(0.0, description="Confidence score (0-1)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class TemplateSelector:
    """
    FSA-1.2: TemplateSelector

    Selects appropriate code templates by:
    - Analyzing task requirements
    - Matching requirements to template patterns
    - Recommending best-fit templates
    - Providing template composition strategies
    """

    def __init__(self, debug: bool = False):
        self.debug = debug
        self.templates = self._initialize_templates()
        logger.info("FSA-1.2: TemplateSelector initialized")

    def _initialize_templates(self) -> List[CodeTemplate]:
        """Initialize the template library"""
        return [
            # API Server Templates
            CodeTemplate(
                name="REST API Server",
                type=TemplateType.API_SERVER,
                description="RESTful API server with routing and middleware support",
                pattern="""
class APIServer:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.routes = {}
        self.middleware = []

    def route(self, path: str, method: str):
        def decorator(handler):
            self.routes[(path, method)] = handler
            return handler
        return decorator

    def use_middleware(self, middleware):
        self.middleware.append(middleware)

    def start(self):
        # Server startup logic
        pass
""",
                dependencies=["fastapi", "uvicorn", "pydantic"],
                best_practices=[
                    "Use async handlers for better performance",
                    "Implement proper error handling",
                    "Add request validation",
                    "Include API documentation"
                ],
                tags=["api", "server", "rest", "web"]
            ),
            # Database Layer Templates
            CodeTemplate(
                name="Database Connection Manager",
                type=TemplateType.DATABASE_LAYER,
                description="Database connection and query management",
                pattern="""
class DatabaseManager:
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.connection = None

    async def connect(self):
        # Connection logic
        pass

    async def disconnect(self):
        # Disconnection logic
        pass

    async def query(self, sql: str, params: dict = None):
        # Query execution
        pass

    async def execute(self, sql: str, params: dict = None):
        # Execute command
        pass
""",
                dependencies=["sqlalchemy", "asyncpg", "databases"],
                best_practices=[
                    "Use connection pooling",
                    "Implement proper transaction management",
                    "Add query logging",
                    "Handle connection errors gracefully"
                ],
                tags=["database", "sql", "orm", "persistence"]
            ),
            # Authentication Templates
            CodeTemplate(
                name="JWT Authentication",
                type=TemplateType.AUTHENTICATION,
                description="JWT-based authentication system",
                pattern="""
class AuthenticationManager:
    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm

    def create_token(self, user_id: str, expires_in: int = 3600) -> str:
        # Token creation logic
        pass

    def verify_token(self, token: str) -> dict:
        # Token verification logic
        pass

    def hash_password(self, password: str) -> str:
        # Password hashing
        pass

    def verify_password(self, password: str, hashed: str) -> bool:
        # Password verification
        pass
""",
                dependencies=["pyjwt", "bcrypt", "passlib"],
                best_practices=[
                    "Use secure hashing algorithms",
                    "Implement token expiration",
                    "Add refresh token support",
                    "Store secrets securely"
                ],
                tags=["auth", "jwt", "security", "tokens"]
            ),
            # Error Handling Templates
            CodeTemplate(
                name="Error Handler Middleware",
                type=TemplateType.ERROR_HANDLING,
                description="Comprehensive error handling middleware",
                pattern="""
class ErrorHandler:
    def __init__(self, debug: bool = False):
        self.debug = debug

    async def handle_error(self, error: Exception, context: dict):
        error_response = {
            "error": type(error).__name__,
            "message": str(error),
            "status_code": self._get_status_code(error)
        }

        if self.debug:
            error_response["traceback"] = self._format_traceback(error)

        return error_response

    def _get_status_code(self, error: Exception) -> int:
        # Map exceptions to status codes
        pass

    def _format_traceback(self, error: Exception) -> str:
        # Format traceback
        pass
""",
                dependencies=[],
                best_practices=[
                    "Log all errors",
                    "Don't expose sensitive information",
                    "Provide meaningful error messages",
                    "Use proper HTTP status codes"
                ],
                tags=["error", "exception", "middleware", "logging"]
            ),
            # Middleware Templates
            CodeTemplate(
                name="Request Logger Middleware",
                type=TemplateType.MIDDLEWARE,
                description="Request/response logging middleware",
                pattern="""
class LoggerMiddleware:
    def __init__(self, logger):
        self.logger = logger

    async def process_request(self, request):
        self.logger.info(f"Incoming request: {request.method} {request.path}")
        request.start_time = time.time()
        return request

    async def process_response(self, request, response):
        duration = time.time() - request.start_time
        self.logger.info(f"Response: {response.status_code} ({duration:.3f}s)")
        return response
""",
                dependencies=[],
                best_practices=[
                    "Log request/response times",
                    "Include correlation IDs",
                    "Don't log sensitive data",
                    "Use structured logging"
                ],
                tags=["middleware", "logging", "monitoring"]
            ),
            # Validation Templates
            CodeTemplate(
                name="Request Validator",
                type=TemplateType.VALIDATION,
                description="Input validation and sanitization",
                pattern="""
class RequestValidator:
    def __init__(self, schema):
        self.schema = schema

    def validate(self, data: dict) -> tuple[bool, dict]:
        errors = {}
        validated_data = {}

        for field, rules in self.schema.items():
            if not self._validate_field(data.get(field), rules):
                errors[field] = f"Validation failed for {field}"
            else:
                validated_data[field] = data.get(field)

        return len(errors) == 0, errors or validated_data

    def _validate_field(self, value, rules) -> bool:
        # Field validation logic
        pass
""",
                dependencies=["pydantic"],
                best_practices=[
                    "Validate all inputs",
                    "Sanitize user data",
                    "Provide clear validation messages",
                    "Use schemas for consistency"
                ],
                tags=["validation", "security", "input"]
            ),
        ]

    def select_templates(
        self,
        task_description: str,
        requirements: Optional[Dict[str, Any]] = None
    ) -> TemplateSelection:
        """
        Select appropriate templates for a task

        Args:
            task_description: Description of the task
            requirements: Additional requirements

        Returns:
            TemplateSelection with matched templates
        """
        if self.debug:
            logger.debug(f"Selecting templates for: {task_description[:100]}...")

        requirements = requirements or {}

        # Analyze task to determine needed template types
        needed_types = self._analyze_task_requirements(task_description, requirements)

        # Select templates matching needed types
        selected = []
        for template_type in needed_types:
            matching_templates = [
                t for t in self.templates
                if t.type == template_type
            ]
            if matching_templates:
                # Select the best matching template (for now, just take the first)
                selected.append(matching_templates[0])

        # Generate rationale
        rationale = self._generate_rationale(task_description, selected)

        # Calculate confidence
        confidence = self._calculate_confidence(task_description, selected)

        result = TemplateSelection(
            selected_templates=selected,
            rationale=rationale,
            confidence=confidence,
            metadata={
                "task_description": task_description,
                "requirements": requirements,
                "needed_types": [t.value for t in needed_types]
            }
        )

        if self.debug:
            logger.debug(f"Selected {len(selected)} templates with confidence {confidence:.2f}")

        return result

    def _analyze_task_requirements(
        self,
        task_description: str,
        requirements: Dict[str, Any]
    ) -> List[TemplateType]:
        """Analyze task to determine needed template types"""
        needed = []
        task_lower = task_description.lower()

        # API Server detection
        if any(word in task_lower for word in ["api", "server", "rest", "endpoint"]):
            needed.append(TemplateType.API_SERVER)
            needed.append(TemplateType.ROUTING)
            needed.append(TemplateType.MIDDLEWARE)

        # Database detection
        if any(word in task_lower for word in ["database", "db", "data", "storage", "persistence"]):
            needed.append(TemplateType.DATABASE_LAYER)

        # Authentication detection
        if any(word in task_lower for word in ["auth", "login", "user", "token", "jwt"]):
            needed.append(TemplateType.AUTHENTICATION)

        # Error handling detection
        if any(word in task_lower for word in ["error", "exception", "handling"]):
            needed.append(TemplateType.ERROR_HANDLING)

        # Validation detection
        if any(word in task_lower for word in ["validation", "validate", "input"]):
            needed.append(TemplateType.VALIDATION)

        # Logging detection
        if any(word in task_lower for word in ["log", "logging", "monitor"]):
            needed.append(TemplateType.LOGGING)

        # Always include error handling and logging for production code
        if TemplateType.ERROR_HANDLING not in needed:
            needed.append(TemplateType.ERROR_HANDLING)

        return needed

    def _generate_rationale(
        self,
        task_description: str,
        selected: List[CodeTemplate]
    ) -> str:
        """Generate rationale for template selection"""
        if not selected:
            return "No templates selected - task may be too simple or unclear"

        rationale_parts = [
            f"Selected {len(selected)} templates based on task analysis:",
        ]

        for template in selected:
            rationale_parts.append(
                f"- {template.name} ({template.type.value}): {template.description}"
            )

        return "\n".join(rationale_parts)

    def _calculate_confidence(
        self,
        task_description: str,
        selected: List[CodeTemplate]
    ) -> float:
        """Calculate confidence in template selection"""
        if not selected:
            return 0.3

        # Base confidence on clarity of task and number of matched templates
        base_confidence = 0.6

        # Increase confidence if task is clear
        if len(task_description.split()) > 10:
            base_confidence += 0.1

        # Increase confidence based on number of templates
        template_bonus = min(0.2, len(selected) * 0.05)

        return min(0.95, base_confidence + template_bonus)

    def get_template_by_type(self, template_type: TemplateType) -> Optional[CodeTemplate]:
        """Get a template by type"""
        for template in self.templates:
            if template.type == template_type:
                return template
        return None

    def get_all_templates(self) -> List[CodeTemplate]:
        """Get all available templates"""
        return self.templates.copy()

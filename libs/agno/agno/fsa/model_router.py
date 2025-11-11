"""
FSA-2.2: ModelRouter

Routes tasks to appropriate AI models based on:
- Task complexity
- Required capabilities
- Performance requirements
- Cost considerations
"""

from typing import Dict, List, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field
from agno.utils.log import logger


class ModelCapability(str, Enum):
    """Model capabilities"""
    CODE_GENERATION = "code_generation"
    CODE_ANALYSIS = "code_analysis"
    REASONING = "reasoning"
    OPTIMIZATION = "optimization"
    DEBUGGING = "debugging"
    DOCUMENTATION = "documentation"


class TaskComplexity(str, Enum):
    """Task complexity levels"""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    EXPERT = "expert"


class ModelProfile(BaseModel):
    """AI Model profile"""
    name: str = Field(..., description="Model name")
    provider: str = Field(..., description="Model provider")
    capabilities: List[ModelCapability] = Field(..., description="Model capabilities")
    complexity_rating: int = Field(..., description="Complexity rating (1-10)")
    speed_rating: int = Field(..., description="Speed rating (1-10)")
    cost_rating: int = Field(..., description="Cost rating (1-10, higher is more expensive)")
    max_tokens: int = Field(..., description="Maximum token limit")


class RoutingDecision(BaseModel):
    """Model routing decision"""
    selected_model: ModelProfile = Field(..., description="Selected model")
    rationale: str = Field(..., description="Selection rationale")
    confidence: float = Field(0.0, description="Confidence score (0-1)")
    alternatives: List[ModelProfile] = Field(default_factory=list, description="Alternative models")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ModelRouter:
    """
    FSA-2.2: ModelRouter

    Routes tasks to appropriate models by:
    - Analyzing task requirements
    - Matching requirements to model capabilities
    - Considering performance and cost tradeoffs
    - Providing fallback options
    """

    def __init__(self, debug: bool = False):
        self.debug = debug
        self.models = self._initialize_models()
        logger.info("FSA-2.2: ModelRouter initialized")

    def _initialize_models(self) -> List[ModelProfile]:
        """Initialize available models"""
        return [
            # GPT Models
            ModelProfile(
                name="gpt-4",
                provider="openai",
                capabilities=[
                    ModelCapability.CODE_GENERATION,
                    ModelCapability.CODE_ANALYSIS,
                    ModelCapability.REASONING,
                    ModelCapability.OPTIMIZATION,
                    ModelCapability.DEBUGGING,
                    ModelCapability.DOCUMENTATION,
                ],
                complexity_rating=10,
                speed_rating=6,
                cost_rating=9,
                max_tokens=8192
            ),
            ModelProfile(
                name="gpt-3.5-turbo",
                provider="openai",
                capabilities=[
                    ModelCapability.CODE_GENERATION,
                    ModelCapability.CODE_ANALYSIS,
                    ModelCapability.DOCUMENTATION,
                ],
                complexity_rating=6,
                speed_rating=9,
                cost_rating=3,
                max_tokens=4096
            ),
            # Claude Models
            ModelProfile(
                name="claude-3-opus",
                provider="anthropic",
                capabilities=[
                    ModelCapability.CODE_GENERATION,
                    ModelCapability.CODE_ANALYSIS,
                    ModelCapability.REASONING,
                    ModelCapability.OPTIMIZATION,
                    ModelCapability.DEBUGGING,
                    ModelCapability.DOCUMENTATION,
                ],
                complexity_rating=10,
                speed_rating=7,
                cost_rating=8,
                max_tokens=200000
            ),
            ModelProfile(
                name="claude-3-sonnet",
                provider="anthropic",
                capabilities=[
                    ModelCapability.CODE_GENERATION,
                    ModelCapability.CODE_ANALYSIS,
                    ModelCapability.REASONING,
                    ModelCapability.DOCUMENTATION,
                ],
                complexity_rating=8,
                speed_rating=8,
                cost_rating=5,
                max_tokens=200000
            ),
            ModelProfile(
                name="claude-3-haiku",
                provider="anthropic",
                capabilities=[
                    ModelCapability.CODE_GENERATION,
                    ModelCapability.CODE_ANALYSIS,
                ],
                complexity_rating=5,
                speed_rating=10,
                cost_rating=2,
                max_tokens=200000
            ),
            # Specialized Models
            ModelProfile(
                name="codellama-34b",
                provider="meta",
                capabilities=[
                    ModelCapability.CODE_GENERATION,
                    ModelCapability.CODE_ANALYSIS,
                ],
                complexity_rating=7,
                speed_rating=7,
                cost_rating=4,
                max_tokens=16384
            ),
        ]

    def route(
        self,
        task_description: str,
        required_capabilities: Optional[List[ModelCapability]] = None,
        complexity: Optional[TaskComplexity] = None,
        constraints: Optional[Dict[str, Any]] = None
    ) -> RoutingDecision:
        """
        Route task to appropriate model

        Args:
            task_description: Description of the task
            required_capabilities: Required model capabilities
            complexity: Task complexity level
            constraints: Additional constraints (cost, speed, etc.)

        Returns:
            RoutingDecision with selected model
        """
        if self.debug:
            logger.debug(f"Routing task: {task_description[:100]}...")

        constraints = constraints or {}

        # Analyze task if complexity not provided
        if complexity is None:
            complexity = self._analyze_task_complexity(task_description)

        # Determine required capabilities if not provided
        if required_capabilities is None:
            required_capabilities = self._determine_required_capabilities(task_description)

        # Filter models by capabilities
        capable_models = [
            m for m in self.models
            if all(cap in m.capabilities for cap in required_capabilities)
        ]

        if not capable_models:
            logger.warning("No models found with all required capabilities")
            capable_models = self.models  # Fallback to all models

        # Score models
        scored_models = []
        for model in capable_models:
            score = self._score_model(model, complexity, constraints)
            scored_models.append((score, model))

        # Sort by score (descending)
        scored_models.sort(reverse=True, key=lambda x: x[0])

        # Select best model
        selected_model = scored_models[0][1]
        alternatives = [m[1] for m in scored_models[1:4]]  # Top 3 alternatives

        # Generate rationale
        rationale = self._generate_rationale(
            selected_model,
            task_description,
            complexity,
            required_capabilities
        )

        # Calculate confidence
        confidence = self._calculate_confidence(scored_models)

        result = RoutingDecision(
            selected_model=selected_model,
            rationale=rationale,
            confidence=confidence,
            alternatives=alternatives,
            metadata={
                "task_description": task_description,
                "complexity": complexity.value,
                "required_capabilities": [c.value for c in required_capabilities],
                "constraints": constraints,
                "scores": {m.name: score for score, m in scored_models[:5]}
            }
        )

        if self.debug:
            logger.debug(f"Selected model: {selected_model.name} (confidence: {confidence:.2f})")

        return result

    def _analyze_task_complexity(self, task_description: str) -> TaskComplexity:
        """Analyze task to determine complexity"""
        task_lower = task_description.lower()

        # Simple heuristics for complexity detection
        complexity_indicators = {
            TaskComplexity.EXPERT: [
                "distributed", "scalable", "high-performance",
                "concurrent", "parallel", "optimization",
                "machine learning", "ai", "algorithm"
            ],
            TaskComplexity.COMPLEX: [
                "authentication", "authorization", "security",
                "database", "api", "integration", "microservice"
            ],
            TaskComplexity.MODERATE: [
                "class", "function", "module", "package",
                "interface", "abstract"
            ],
            TaskComplexity.SIMPLE: [
                "simple", "basic", "helper", "utility"
            ]
        }

        # Count indicators for each complexity level
        for complexity, indicators in complexity_indicators.items():
            if any(indicator in task_lower for indicator in indicators):
                return complexity

        # Default to moderate if unclear
        return TaskComplexity.MODERATE

    def _determine_required_capabilities(
        self,
        task_description: str
    ) -> List[ModelCapability]:
        """Determine required capabilities from task description"""
        required = []
        task_lower = task_description.lower()

        # Code generation
        if any(word in task_lower for word in ["build", "create", "implement", "generate"]):
            required.append(ModelCapability.CODE_GENERATION)

        # Code analysis
        if any(word in task_lower for word in ["analyze", "review", "understand", "explain"]):
            required.append(ModelCapability.CODE_ANALYSIS)

        # Reasoning
        if any(word in task_lower for word in ["design", "architect", "plan", "strategy"]):
            required.append(ModelCapability.REASONING)

        # Optimization
        if any(word in task_lower for word in ["optimize", "improve", "performance", "refactor"]):
            required.append(ModelCapability.OPTIMIZATION)

        # Debugging
        if any(word in task_lower for word in ["debug", "fix", "error", "bug"]):
            required.append(ModelCapability.DEBUGGING)

        # Documentation
        if any(word in task_lower for word in ["document", "comment", "docstring"]):
            required.append(ModelCapability.DOCUMENTATION)

        # Default to code generation if nothing detected
        if not required:
            required.append(ModelCapability.CODE_GENERATION)

        return required

    def _score_model(
        self,
        model: ModelProfile,
        complexity: TaskComplexity,
        constraints: Dict[str, Any]
    ) -> float:
        """Score a model for the given task"""
        score = 0.0

        # Complexity match (40% of score)
        complexity_map = {
            TaskComplexity.SIMPLE: 3,
            TaskComplexity.MODERATE: 5,
            TaskComplexity.COMPLEX: 7,
            TaskComplexity.EXPERT: 9,
        }
        required_rating = complexity_map[complexity]
        complexity_diff = abs(model.complexity_rating - required_rating)
        complexity_score = max(0, 40 - (complexity_diff * 5))
        score += complexity_score

        # Speed consideration (30% of score)
        if constraints.get("prioritize_speed", False):
            score += model.speed_rating * 3
        else:
            score += model.speed_rating * 1.5

        # Cost consideration (30% of score)
        if constraints.get("prioritize_cost", False):
            score += (10 - model.cost_rating) * 3
        else:
            score += (10 - model.cost_rating) * 1.5

        return score

    def _generate_rationale(
        self,
        model: ModelProfile,
        task_description: str,
        complexity: TaskComplexity,
        capabilities: List[ModelCapability]
    ) -> str:
        """Generate rationale for model selection"""
        rationale_parts = [
            f"Selected {model.name} from {model.provider}",
            f"Task complexity: {complexity.value}",
            f"Required capabilities: {', '.join(c.value for c in capabilities)}",
            f"Model ratings - Complexity: {model.complexity_rating}/10, "
            f"Speed: {model.speed_rating}/10, Cost: {model.cost_rating}/10"
        ]

        return "\n".join(rationale_parts)

    def _calculate_confidence(self, scored_models: List[tuple]) -> float:
        """Calculate confidence in routing decision"""
        if len(scored_models) < 2:
            return 0.7

        # Calculate confidence based on score separation
        best_score = scored_models[0][0]
        second_score = scored_models[1][0] if len(scored_models) > 1 else 0

        score_diff = best_score - second_score
        confidence = 0.6 + min(0.35, score_diff / 100)

        return confidence

    def get_available_models(self) -> List[ModelProfile]:
        """Get all available models"""
        return self.models.copy()

    def get_model_by_name(self, name: str) -> Optional[ModelProfile]:
        """Get a model by name"""
        for model in self.models:
            if model.name == name:
                return model
        return None

"""
FSA-1.1: PromptOptimizer

Enhances and optimizes prompts for better code generation results.
Applies various optimization strategies including clarity enhancement,
context enrichment, and constraint specification.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from agno.utils.log import logger


class OptimizationStrategy(BaseModel):
    """Strategy for prompt optimization"""
    name: str = Field(..., description="Strategy name")
    description: str = Field(..., description="Strategy description")
    weight: float = Field(1.0, description="Strategy weight/priority")


class OptimizedPrompt(BaseModel):
    """Result of prompt optimization"""
    original_prompt: str = Field(..., description="Original input prompt")
    optimized_prompt: str = Field(..., description="Optimized output prompt")
    strategies_applied: List[str] = Field(default_factory=list, description="Applied strategies")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    confidence: float = Field(0.0, description="Confidence score (0-1)")


class PromptOptimizer:
    """
    FSA-1.1: PromptOptimizer

    Optimizes prompts for code generation by:
    - Clarifying ambiguous requirements
    - Adding technical context
    - Specifying constraints and best practices
    - Structuring the prompt for better results
    """

    def __init__(self, debug: bool = False):
        self.debug = debug
        self.strategies = self._initialize_strategies()
        logger.info("FSA-1.1: PromptOptimizer initialized")

    def _initialize_strategies(self) -> List[OptimizationStrategy]:
        """Initialize optimization strategies"""
        return [
            OptimizationStrategy(
                name="clarity_enhancement",
                description="Improve clarity and remove ambiguity",
                weight=1.0
            ),
            OptimizationStrategy(
                name="context_enrichment",
                description="Add relevant technical context",
                weight=0.9
            ),
            OptimizationStrategy(
                name="constraint_specification",
                description="Specify technical constraints and requirements",
                weight=0.8
            ),
            OptimizationStrategy(
                name="structure_optimization",
                description="Improve prompt structure and organization",
                weight=0.7
            ),
            OptimizationStrategy(
                name="best_practices",
                description="Add best practices and standards",
                weight=0.6
            ),
        ]

    def optimize(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> OptimizedPrompt:
        """
        Optimize a prompt for code generation

        Args:
            prompt: Original prompt to optimize
            context: Additional context for optimization

        Returns:
            OptimizedPrompt with enhanced version
        """
        if self.debug:
            logger.debug(f"Optimizing prompt: {prompt[:100]}...")

        context = context or {}
        optimized_parts = []
        applied_strategies = []

        # Apply clarity enhancement
        if self._should_apply_strategy("clarity_enhancement", context):
            clarity_enhanced = self._enhance_clarity(prompt, context)
            optimized_parts.append(clarity_enhanced)
            applied_strategies.append("clarity_enhancement")

        # Apply context enrichment
        if self._should_apply_strategy("context_enrichment", context):
            context_enriched = self._enrich_context(prompt, context)
            optimized_parts.append(context_enriched)
            applied_strategies.append("context_enrichment")

        # Apply constraint specification
        if self._should_apply_strategy("constraint_specification", context):
            constraints = self._specify_constraints(prompt, context)
            optimized_parts.append(constraints)
            applied_strategies.append("constraint_specification")

        # Build optimized prompt
        optimized_text = self._build_optimized_prompt(prompt, optimized_parts, context)

        # Calculate confidence
        confidence = self._calculate_confidence(applied_strategies)

        result = OptimizedPrompt(
            original_prompt=prompt,
            optimized_prompt=optimized_text,
            strategies_applied=applied_strategies,
            metadata={
                "context": context,
                "optimization_count": len(applied_strategies)
            },
            confidence=confidence
        )

        if self.debug:
            logger.debug(f"Optimization complete. Applied {len(applied_strategies)} strategies")

        return result

    def _should_apply_strategy(self, strategy_name: str, context: Dict[str, Any]) -> bool:
        """Determine if a strategy should be applied"""
        # Allow context to override strategy application
        if "disabled_strategies" in context:
            if strategy_name in context["disabled_strategies"]:
                return False
        return True

    def _enhance_clarity(self, prompt: str, context: Dict[str, Any]) -> str:
        """Enhance prompt clarity"""
        enhancements = []

        # Add explicit objectives
        if "objective" not in prompt.lower():
            enhancements.append("Objective: Create production-ready code that follows best practices")

        # Add output format specification
        if "format" not in prompt.lower() and "output" not in prompt.lower():
            enhancements.append("Output Format: Well-structured, documented code with clear interfaces")

        return "\n".join(enhancements)

    def _enrich_context(self, prompt: str, context: Dict[str, Any]) -> str:
        """Enrich prompt with technical context"""
        enrichments = []

        # Add language/framework context
        if "language" in context:
            enrichments.append(f"Programming Language: {context['language']}")

        if "framework" in context:
            enrichments.append(f"Framework: {context['framework']}")

        # Add architectural context
        if "architecture" in context:
            enrichments.append(f"Architecture: {context['architecture']}")

        # Add technology stack
        if "stack" in context:
            enrichments.append(f"Technology Stack: {', '.join(context['stack'])}")

        return "\n".join(enrichments)

    def _specify_constraints(self, prompt: str, context: Dict[str, Any]) -> str:
        """Specify technical constraints"""
        constraints = []

        # Add quality constraints
        constraints.append("Quality Requirements:")
        constraints.append("- Follow SOLID principles")
        constraints.append("- Include error handling")
        constraints.append("- Add appropriate logging")
        constraints.append("- Write maintainable, testable code")

        # Add specific constraints from context
        if "constraints" in context:
            constraints.append("\nAdditional Constraints:")
            for constraint in context["constraints"]:
                constraints.append(f"- {constraint}")

        return "\n".join(constraints)

    def _build_optimized_prompt(
        self,
        original: str,
        optimized_parts: List[str],
        context: Dict[str, Any]
    ) -> str:
        """Build the final optimized prompt"""
        parts = [original]

        if optimized_parts:
            parts.append("\n\n--- Enhanced Requirements ---")
            parts.extend(optimized_parts)

        return "\n".join(parts)

    def _calculate_confidence(self, applied_strategies: List[str]) -> float:
        """Calculate confidence score based on applied strategies"""
        if not applied_strategies:
            return 0.5

        # Base confidence on number and type of strategies
        total_weight = sum(
            s.weight for s in self.strategies
            if s.name in applied_strategies
        )
        max_weight = sum(s.weight for s in self.strategies)

        return min(0.95, 0.5 + (total_weight / max_weight) * 0.45)

    def get_strategies(self) -> List[OptimizationStrategy]:
        """Get available optimization strategies"""
        return self.strategies.copy()

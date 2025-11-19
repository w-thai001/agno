"""
CCMF Meta-Learning Architecture (MLA) - SESSION 1
==================================================

This module implements the Meta-Learning Architecture for the CCMF framework.
It provides advanced learning capabilities including:
- Pattern learning and optimization
- Performance prediction
- Transfer learning
- Meta-leverage quotient calculations

The MLA enables the system to learn from past experiences and apply
that knowledge to improve future performance.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from enum import Enum
import statistics
import json


class LearningMode(Enum):
    """Modes of meta-learning."""
    SUPERVISED = "supervised"
    UNSUPERVISED = "unsupervised"
    REINFORCEMENT = "reinforcement"
    TRANSFER = "transfer"


@dataclass
class LearningExample:
    """Represents a learning example from past operations."""
    example_id: str
    timestamp: datetime
    pattern_used: str
    context: Dict[str, Any]
    outcome: Dict[str, Any]
    performance_metrics: Dict[str, float]
    success: bool

    def to_dict(self) -> Dict[str, Any]:
        """Convert example to dictionary."""
        return {
            'example_id': self.example_id,
            'timestamp': self.timestamp.isoformat(),
            'pattern_used': self.pattern_used,
            'context': self.context,
            'outcome': self.outcome,
            'performance_metrics': self.performance_metrics,
            'success': self.success
        }


@dataclass
class MLALeverageQuotient:
    """
    Meta-Learning Architecture Leverage Quotient.

    Measures how effectively the system leverages learned knowledge
    to improve performance on new tasks.
    """
    total_examples: int
    successful_examples: int
    patterns_learned: int
    average_performance_gain: float
    transfer_learning_effectiveness: float
    knowledge_reuse_rate: float
    overall_quotient: float
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert quotient to dictionary."""
        return {
            'total_examples': self.total_examples,
            'successful_examples': self.successful_examples,
            'patterns_learned': self.patterns_learned,
            'average_performance_gain': self.average_performance_gain,
            'transfer_learning_effectiveness': self.transfer_learning_effectiveness,
            'knowledge_reuse_rate': self.knowledge_reuse_rate,
            'overall_quotient': self.overall_quotient,
            'timestamp': self.timestamp.isoformat()
        }

    def get_grade(self) -> str:
        """Get a grade based on the overall quotient."""
        if self.overall_quotient >= 0.9:
            return "A+ (Exceptional)"
        elif self.overall_quotient >= 0.8:
            return "A (Excellent)"
        elif self.overall_quotient >= 0.7:
            return "B (Good)"
        elif self.overall_quotient >= 0.6:
            return "C (Fair)"
        elif self.overall_quotient >= 0.5:
            return "D (Needs Improvement)"
        else:
            return "F (Poor)"


@dataclass
class PatternKnowledge:
    """Knowledge accumulated about a specific pattern."""
    pattern_name: str
    usage_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    average_execution_time: float = 0.0
    best_contexts: List[Dict[str, Any]] = field(default_factory=list)
    failure_contexts: List[Dict[str, Any]] = field(default_factory=list)
    learned_optimizations: List[Dict[str, Any]] = field(default_factory=list)

    def get_success_rate(self) -> float:
        """Calculate success rate."""
        if self.usage_count == 0:
            return 0.0
        return self.success_count / self.usage_count

    def to_dict(self) -> Dict[str, Any]:
        """Convert knowledge to dictionary."""
        return {
            'pattern_name': self.pattern_name,
            'usage_count': self.usage_count,
            'success_rate': self.get_success_rate(),
            'average_execution_time': self.average_execution_time,
            'best_contexts_count': len(self.best_contexts),
            'failure_contexts_count': len(self.failure_contexts),
            'optimizations_count': len(self.learned_optimizations)
        }


class MetaLearningArchitecture:
    """
    Meta-Learning Architecture (MLA) for CCMF.

    The MLA learns from past operations to:
    1. Optimize pattern selection
    2. Predict performance
    3. Transfer knowledge across contexts
    4. Calculate leverage quotients
    """

    def __init__(self, knowledge_base_path: Optional[str] = None):
        """
        Initialize the MLA.

        Args:
            knowledge_base_path: Optional path to persist knowledge base
        """
        self.knowledge_base_path = knowledge_base_path
        self.learning_examples: List[LearningExample] = []
        self.pattern_knowledge: Dict[str, PatternKnowledge] = {}
        self.leverage_quotient_history: List[MLALeverageQuotient] = []

        # Performance baselines
        self.baseline_performance: Dict[str, float] = {}

        # Load knowledge base if path provided
        if knowledge_base_path:
            self._load_knowledge_base()

    def record_example(
        self,
        pattern_name: str,
        context: Dict[str, Any],
        outcome: Dict[str, Any],
        performance_metrics: Dict[str, float],
        success: bool
    ):
        """
        Record a learning example from an operation.

        Args:
            pattern_name: Name of the pattern used
            context: Context in which the pattern was used
            outcome: Outcome of the operation
            performance_metrics: Performance metrics
            success: Whether the operation succeeded
        """
        example = LearningExample(
            example_id=f"ex_{len(self.learning_examples) + 1}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            timestamp=datetime.now(),
            pattern_used=pattern_name,
            context=context,
            outcome=outcome,
            performance_metrics=performance_metrics,
            success=success
        )

        self.learning_examples.append(example)

        # Update pattern knowledge
        if pattern_name not in self.pattern_knowledge:
            self.pattern_knowledge[pattern_name] = PatternKnowledge(
                pattern_name=pattern_name
            )

        knowledge = self.pattern_knowledge[pattern_name]
        knowledge.usage_count += 1

        if success:
            knowledge.success_count += 1
            # Store best contexts (top 10)
            if len(knowledge.best_contexts) < 10:
                knowledge.best_contexts.append(context)
        else:
            knowledge.failure_count += 1
            # Store failure contexts (top 10)
            if len(knowledge.failure_contexts) < 10:
                knowledge.failure_contexts.append(context)

        # Update average execution time
        if 'execution_time' in performance_metrics:
            current_avg = knowledge.average_execution_time
            new_time = performance_metrics['execution_time']
            knowledge.average_execution_time = (
                (current_avg * (knowledge.usage_count - 1) + new_time) /
                knowledge.usage_count
            )

    def predict_performance(
        self,
        pattern_name: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Predict performance for a pattern in a given context.

        Args:
            pattern_name: Name of the pattern
            context: Context for prediction

        Returns:
            Dictionary with predictions
        """
        if pattern_name not in self.pattern_knowledge:
            return {
                'has_prediction': False,
                'reason': 'No knowledge available for this pattern'
            }

        knowledge = self.pattern_knowledge[pattern_name]

        # Basic predictions based on historical data
        prediction = {
            'has_prediction': True,
            'predicted_success_rate': knowledge.get_success_rate(),
            'predicted_execution_time': knowledge.average_execution_time,
            'confidence': min(1.0, knowledge.usage_count / 100.0),  # Confidence increases with usage
            'recommendation': 'use' if knowledge.get_success_rate() > 0.7 else 'consider_alternative'
        }

        # Context similarity analysis
        if knowledge.best_contexts:
            similarity_scores = [
                self._calculate_context_similarity(context, best_ctx)
                for best_ctx in knowledge.best_contexts
            ]
            max_similarity = max(similarity_scores)
            prediction['context_similarity'] = max_similarity
            prediction['context_match'] = 'high' if max_similarity > 0.7 else 'medium' if max_similarity > 0.4 else 'low'

        return prediction

    def _calculate_context_similarity(
        self,
        context1: Dict[str, Any],
        context2: Dict[str, Any]
    ) -> float:
        """
        Calculate similarity between two contexts.

        Args:
            context1: First context
            context2: Second context

        Returns:
            Similarity score (0.0 to 1.0)
        """
        # Simple similarity based on matching keys and values
        keys1 = set(context1.keys())
        keys2 = set(context2.keys())

        if not keys1 and not keys2:
            return 1.0
        if not keys1 or not keys2:
            return 0.0

        # Key overlap
        key_overlap = len(keys1 & keys2) / len(keys1 | keys2)

        # Value similarity for common keys
        common_keys = keys1 & keys2
        if common_keys:
            value_matches = sum(
                1 for k in common_keys
                if context1.get(k) == context2.get(k)
            )
            value_similarity = value_matches / len(common_keys)
        else:
            value_similarity = 0.0

        # Weighted average
        similarity = (key_overlap * 0.5 + value_similarity * 0.5)
        return similarity

    def recommend_pattern(
        self,
        context: Dict[str, Any],
        available_patterns: List[str]
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Recommend the best pattern for a given context.

        Args:
            context: Context for the operation
            available_patterns: List of available pattern names

        Returns:
            Tuple of (recommended_pattern_name, reasoning)
        """
        if not available_patterns:
            return "", {'error': 'No patterns available'}

        # Score each pattern
        pattern_scores = {}
        for pattern_name in available_patterns:
            if pattern_name not in self.pattern_knowledge:
                # Unknown pattern, give neutral score
                pattern_scores[pattern_name] = {
                    'score': 0.5,
                    'reason': 'No historical data'
                }
                continue

            knowledge = self.pattern_knowledge[pattern_name]
            prediction = self.predict_performance(pattern_name, context)

            # Calculate score
            score = (
                prediction['predicted_success_rate'] * 0.5 +
                prediction['confidence'] * 0.2 +
                (1.0 - min(1.0, knowledge.average_execution_time / 10.0)) * 0.2 +
                prediction.get('context_similarity', 0.5) * 0.1
            )

            pattern_scores[pattern_name] = {
                'score': score,
                'prediction': prediction,
                'knowledge': knowledge.to_dict()
            }

        # Find best pattern
        best_pattern = max(pattern_scores.keys(), key=lambda p: pattern_scores[p]['score'])

        return best_pattern, pattern_scores[best_pattern]

    def calculate_leverage_quotient(self) -> MLALeverageQuotient:
        """
        Calculate the Meta-Learning Architecture Leverage Quotient.

        The MLA Leverage Quotient measures how effectively the system
        uses learned knowledge to improve performance.

        Returns:
            MLALeverageQuotient with calculated metrics
        """
        if not self.learning_examples:
            return MLALeverageQuotient(
                total_examples=0,
                successful_examples=0,
                patterns_learned=0,
                average_performance_gain=0.0,
                transfer_learning_effectiveness=0.0,
                knowledge_reuse_rate=0.0,
                overall_quotient=0.0
            )

        # Basic metrics
        total_examples = len(self.learning_examples)
        successful_examples = sum(1 for ex in self.learning_examples if ex.success)
        patterns_learned = len(self.pattern_knowledge)

        # Calculate performance gain
        performance_gains = []
        for pattern_name, knowledge in self.pattern_knowledge.items():
            if knowledge.usage_count > 1:
                # Compare recent performance to early performance
                pattern_examples = [
                    ex for ex in self.learning_examples
                    if ex.pattern_used == pattern_name
                ]
                if len(pattern_examples) >= 2:
                    early_success_rate = sum(
                        1 for ex in pattern_examples[:len(pattern_examples)//2] if ex.success
                    ) / (len(pattern_examples)//2)

                    late_success_rate = sum(
                        1 for ex in pattern_examples[len(pattern_examples)//2:] if ex.success
                    ) / (len(pattern_examples) - len(pattern_examples)//2)

                    gain = late_success_rate - early_success_rate
                    performance_gains.append(gain)

        average_performance_gain = (
            statistics.mean(performance_gains) if performance_gains else 0.0
        )

        # Transfer learning effectiveness
        # Measure how well knowledge transfers across patterns
        if patterns_learned > 1:
            # Calculate average success rate for patterns after first use
            transfer_scores = []
            for pattern_name, knowledge in self.pattern_knowledge.items():
                if knowledge.usage_count > 1:
                    pattern_examples = [
                        ex for ex in self.learning_examples
                        if ex.pattern_used == pattern_name
                    ]
                    if len(pattern_examples) >= 2:
                        # Success rate from second use onwards (benefiting from learning)
                        later_success = sum(
                            1 for ex in pattern_examples[1:] if ex.success
                        ) / (len(pattern_examples) - 1)
                        transfer_scores.append(later_success)

            transfer_learning_effectiveness = (
                statistics.mean(transfer_scores) if transfer_scores else 0.5
            )
        else:
            transfer_learning_effectiveness = 0.5

        # Knowledge reuse rate
        # Measure how often learned patterns are reused successfully
        patterns_with_reuse = sum(
            1 for knowledge in self.pattern_knowledge.values()
            if knowledge.usage_count > 1 and knowledge.get_success_rate() > 0.7
        )
        knowledge_reuse_rate = (
            patterns_with_reuse / patterns_learned if patterns_learned > 0 else 0.0
        )

        # Calculate overall quotient
        success_rate = successful_examples / total_examples if total_examples > 0 else 0.0

        overall_quotient = (
            success_rate * 0.3 +
            (average_performance_gain + 1.0) / 2.0 * 0.2 +  # Normalize gain to 0-1
            transfer_learning_effectiveness * 0.25 +
            knowledge_reuse_rate * 0.25
        )

        quotient = MLALeverageQuotient(
            total_examples=total_examples,
            successful_examples=successful_examples,
            patterns_learned=patterns_learned,
            average_performance_gain=average_performance_gain,
            transfer_learning_effectiveness=transfer_learning_effectiveness,
            knowledge_reuse_rate=knowledge_reuse_rate,
            overall_quotient=overall_quotient
        )

        self.leverage_quotient_history.append(quotient)
        return quotient

    def get_learning_insights(self) -> Dict[str, Any]:
        """
        Get insights from the learning process.

        Returns:
            Dictionary with learning insights
        """
        if not self.learning_examples:
            return {'message': 'No learning data available'}

        insights = {
            'total_examples': len(self.learning_examples),
            'patterns_learned': len(self.pattern_knowledge),
            'top_performing_patterns': [],
            'patterns_needing_improvement': [],
            'learning_trends': {}
        }

        # Top performing patterns
        top_patterns = sorted(
            self.pattern_knowledge.values(),
            key=lambda k: k.get_success_rate(),
            reverse=True
        )[:5]

        insights['top_performing_patterns'] = [
            {
                'name': p.pattern_name,
                'success_rate': p.get_success_rate(),
                'usage_count': p.usage_count
            }
            for p in top_patterns
        ]

        # Patterns needing improvement
        poor_patterns = [
            p for p in self.pattern_knowledge.values()
            if p.usage_count >= 5 and p.get_success_rate() < 0.7
        ]
        insights['patterns_needing_improvement'] = [
            {
                'name': p.pattern_name,
                'success_rate': p.get_success_rate(),
                'usage_count': p.usage_count
            }
            for p in poor_patterns
        ]

        # Learning trends
        if len(self.leverage_quotient_history) >= 2:
            first_quotient = self.leverage_quotient_history[0]
            latest_quotient = self.leverage_quotient_history[-1]

            insights['learning_trends'] = {
                'quotient_improvement': (
                    latest_quotient.overall_quotient - first_quotient.overall_quotient
                ),
                'knowledge_reuse_improvement': (
                    latest_quotient.knowledge_reuse_rate - first_quotient.knowledge_reuse_rate
                ),
                'transfer_learning_improvement': (
                    latest_quotient.transfer_learning_effectiveness -
                    first_quotient.transfer_learning_effectiveness
                )
            }

        return insights

    def _load_knowledge_base(self):
        """Load knowledge base from file."""
        if not self.knowledge_base_path:
            return

        try:
            from pathlib import Path
            kb_path = Path(self.knowledge_base_path)
            if kb_path.exists():
                with open(kb_path, 'r') as f:
                    data = json.load(f)
                    # Load pattern knowledge
                    # (Implementation would deserialize stored data)
                    pass
        except Exception as e:
            print(f"Warning: Could not load knowledge base: {e}")

    def save_knowledge_base(self):
        """Save knowledge base to file."""
        if not self.knowledge_base_path:
            return

        try:
            from pathlib import Path
            kb_path = Path(self.knowledge_base_path)
            kb_path.parent.mkdir(parents=True, exist_ok=True)

            data = {
                'pattern_knowledge': {
                    name: knowledge.to_dict()
                    for name, knowledge in self.pattern_knowledge.items()
                },
                'total_examples': len(self.learning_examples),
                'last_updated': datetime.now().isoformat()
            }

            with open(kb_path, 'w') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            print(f"Warning: Could not save knowledge base: {e}")


if __name__ == "__main__":
    # Example usage
    print("CCMF Meta-Learning Architecture - Example Usage")
    print("=" * 60)

    # Create MLA
    mla = MetaLearningArchitecture()

    # Simulate learning examples
    print("\nSimulating learning examples...")
    import random

    patterns = ['PatternA', 'PatternB', 'PatternC']
    contexts = [
        {'type': 'file_access', 'size': 'small'},
        {'type': 'file_access', 'size': 'large'},
        {'type': 'search', 'scope': 'local'},
        {'type': 'search', 'scope': 'global'}
    ]

    for i in range(30):
        pattern = random.choice(patterns)
        context = random.choice(contexts)
        success = random.random() > 0.3  # 70% success rate

        mla.record_example(
            pattern_name=pattern,
            context=context,
            outcome={'result': 'completed' if success else 'failed'},
            performance_metrics={
                'execution_time': random.uniform(0.1, 2.0),
                'quality': random.uniform(0.6, 1.0) if success else random.uniform(0.2, 0.5)
            },
            success=success
        )

    # Calculate leverage quotient
    print("\nCalculating MLA Leverage Quotient...")
    quotient = mla.calculate_leverage_quotient()

    print(f"\nMLA Leverage Quotient:")
    print(f"  Overall Quotient: {quotient.overall_quotient:.4f}")
    print(f"  Grade: {quotient.get_grade()}")
    print(f"  Total Examples: {quotient.total_examples}")
    print(f"  Successful Examples: {quotient.successful_examples}")
    print(f"  Patterns Learned: {quotient.patterns_learned}")
    print(f"  Avg Performance Gain: {quotient.average_performance_gain:.4f}")
    print(f"  Transfer Learning Effectiveness: {quotient.transfer_learning_effectiveness:.4f}")
    print(f"  Knowledge Reuse Rate: {quotient.knowledge_reuse_rate:.4f}")

    # Get learning insights
    print("\n" + "-" * 60)
    print("\nLearning Insights:")
    insights = mla.get_learning_insights()

    print(f"\nTop Performing Patterns:")
    for pattern in insights['top_performing_patterns']:
        print(f"  - {pattern['name']}: {pattern['success_rate']:.2%} ({pattern['usage_count']} uses)")

    # Recommend pattern
    print("\n" + "-" * 60)
    test_context = {'type': 'file_access', 'size': 'small'}
    recommended, reasoning = mla.recommend_pattern(test_context, patterns)
    print(f"\nPattern Recommendation for {test_context}:")
    print(f"  Recommended: {recommended}")
    print(f"  Score: {reasoning['score']:.4f}")
    if 'prediction' in reasoning:
        print(f"  Predicted Success Rate: {reasoning['prediction']['predicted_success_rate']:.2%}")

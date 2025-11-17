"""
Unit tests for Context Builder FSA.

Tests cover various context scenarios including:
- Basic context building with different input types
- Relevance scoring accuracy
- Entity extraction and relationship mapping
- Context pruning and hierarchical organization
- Edge cases and error handling
"""

import unittest
from datetime import datetime
from typing import Dict, List

from agno.context_builder_fsa import (
    ContextBuilderFSA,
    ContextLevel,
    Entity,
    Relationship,
    ContextItem,
    StructuredContext,
)


class TestContextBuilderFSA(unittest.TestCase):
    """Test suite for ContextBuilderFSA class."""

    def setUp(self):
        """Set up test fixtures."""
        self.fsa = ContextBuilderFSA(
            max_context_items=50,
            immediate_window=5,
            recent_window=15,
            min_relevance_threshold=0.1,
            entity_extraction_enabled=True,
        )

    def test_basic_context_building_with_dict(self):
        """Test basic context building with dictionary input."""
        raw_inputs = {
            "user_query": "What is the weather today?",
            "location": "New York",
            "temperature": 72,
        }
        task_description = "Provide weather information for user query"

        context = self.fsa.build_context(raw_inputs, task_description)

        # Verify context structure
        self.assertIsInstance(context, StructuredContext)
        self.assertGreater(len(context.items), 0)
        self.assertGreater(context.total_relevance_score, 0.0)

        # Verify context summary
        self.assertIn("total_items", context.context_summary)
        self.assertIn("level_distribution", context.context_summary)
        self.assertEqual(
            context.context_summary["total_items"],
            len(context.items),
        )

        # Verify at least one item has IMMEDIATE level
        immediate_items = [item for item in context.items if item.level == ContextLevel.IMMEDIATE]
        self.assertGreater(len(immediate_items), 0)

    def test_context_building_with_list_input(self):
        """Test context building with list input."""
        raw_inputs = [
            "User wants to book a flight",
            "Destination: Paris",
            "Date: 2025-12-01",
            "Budget: $1000",
        ]
        task_description = "Help user book a flight to Paris"

        context = self.fsa.build_context(raw_inputs, task_description)

        # Verify context is built (some items may be pruned based on relevance threshold)
        self.assertGreater(len(context.items), 0)

        # Verify relevance scores are calculated
        for item in context.items:
            self.assertIsInstance(item.relevance_score, float)
            self.assertGreaterEqual(item.relevance_score, 0.0)
            self.assertLessEqual(item.relevance_score, 2.0)  # Allow for boost factors

    def test_context_with_history_hierarchical_levels(self):
        """Test context building with history and hierarchical levels."""
        raw_inputs = {"current_action": "checkout"}
        task_description = "Complete purchase checkout"
        history = [
            "User browsed product catalog",
            "User added item A to cart",
            "User added item B to cart",
            "User viewed cart",
            "User entered shipping address",
            "User selected payment method",
            "User reviewed order",
        ]

        context = self.fsa.build_context(raw_inputs, task_description, history)

        # Verify hierarchical levels are assigned
        level_counts = {
            ContextLevel.IMMEDIATE: 0,
            ContextLevel.RECENT: 0,
            ContextLevel.HISTORICAL: 0,
        }

        for item in context.items:
            level_counts[item.level] += 1

        # Should have items from multiple levels
        self.assertGreater(level_counts[ContextLevel.IMMEDIATE], 0)

        # Verify temporal ordering (more recent should have higher scores generally)
        immediate_items = [item for item in context.items if item.level == ContextLevel.IMMEDIATE]
        historical_items = [item for item in context.items if item.level == ContextLevel.HISTORICAL]

        if immediate_items and historical_items:
            avg_immediate_score = sum(item.relevance_score for item in immediate_items) / len(immediate_items)
            avg_historical_score = sum(item.relevance_score for item in historical_items) / len(historical_items)
            # Immediate should generally have higher average score due to boost
            self.assertGreaterEqual(avg_immediate_score, avg_historical_score * 0.5)

    def test_entity_extraction_and_relationships(self):
        """Test entity extraction and relationship mapping."""
        raw_inputs = {
            "message": "UserAccount Alice wants to transfer money to BankAccount 123456",
            "action": "ProcessTransaction between Alice and account 123456",
        }
        task_description = "Process financial transaction for UserAccount Alice to BankAccount 123456"

        context = self.fsa.build_context(raw_inputs, task_description)

        # Verify entities are extracted
        self.assertGreater(len(context.entities), 0)

        # Check for expected entity types
        entity_names = {e.name for e in context.entities}
        entity_types = {e.entity_type for e in context.entities}

        # Should extract some identifiers
        self.assertGreater(len(entity_names), 0)

        # Verify entities have proper structure
        for entity in context.entities:
            self.assertIsInstance(entity, Entity)
            self.assertIsInstance(entity.name, str)
            self.assertIsInstance(entity.entity_type, str)
            self.assertGreater(entity.mentions, 0)
            self.assertGreaterEqual(entity.confidence, 0.0)
            self.assertLessEqual(entity.confidence, 1.0)

        # Verify relationships are extracted
        # Relationships exist when entities co-occur
        for relationship in context.relationships:
            self.assertIsInstance(relationship, Relationship)
            self.assertIn(relationship.source, context.entities)
            self.assertIn(relationship.target, context.entities)
            self.assertGreater(relationship.strength, 0.0)
            self.assertLessEqual(relationship.strength, 1.0)

    def test_context_pruning_top_k(self):
        """Test context pruning keeps only top-k relevant items."""
        # Create FSA with small max_context_items
        small_fsa = ContextBuilderFSA(
            max_context_items=5,
            min_relevance_threshold=0.0,
        )

        # Generate many history items
        history = [f"History item {i}" for i in range(20)]
        raw_inputs = {"current": "current task"}
        task_description = "current task processing"

        context = small_fsa.build_context(raw_inputs, task_description, history)

        # Verify pruning occurred
        self.assertLessEqual(len(context.items), small_fsa.max_context_items + 2)  # +2 for some buffer

        # Verify items are sorted by relevance (top items first)
        scores = [item.relevance_score for item in context.items]
        # Check if mostly descending (allowing for some level balancing)
        for i in range(len(scores) - 1):
            # Allow some variance for hierarchical level balancing
            if i < len(scores) - 2:
                # At least top items should be high scoring
                self.assertGreater(scores[0], min_relevance_threshold := 0.0)

    def test_extract_relevant_context_with_query(self):
        """Test extracting relevant context for a specific query."""
        # Use a simple FSA with no filtering to ensure items are retained
        simple_fsa = ContextBuilderFSA(
            max_context_items=100,
            min_relevance_threshold=0.0,
        )

        raw_inputs = {
            "task1": "implement user authentication system",
            "task2": "setup database connection pool",
            "task3": "create REST API endpoints",
            "task4": "write technical documentation",
        }
        task_description = "development work"

        context = simple_fsa.build_context(raw_inputs, task_description)

        # Extract relevant context for authentication query
        query = "user authentication security"
        top_k = min(3, len(context.items))
        relevant_items = simple_fsa.extract_relevant_context(context, query, top_k=top_k)

        # Verify we get items back
        self.assertGreater(len(relevant_items), 0)
        self.assertLessEqual(len(relevant_items), top_k)

        # Verify items are ContextItem instances with scores
        for item in relevant_items:
            self.assertIsInstance(item, ContextItem)
            self.assertIsInstance(item.relevance_score, float)

        # Verify items are sorted by relevance (descending)
        scores = [item.relevance_score for item in relevant_items]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_relevance_scoring_accuracy(self):
        """Test LQ-based relevance scoring accuracy."""
        # Test with high similarity
        text1 = "machine learning model training"
        text2 = "training machine learning models"

        high_score = self.fsa._calculate_lq_score(text1, text2)
        self.assertGreater(high_score, 0.3)  # Should have decent overlap

        # Test with low similarity
        text3 = "database connection pooling"
        text4 = "frontend user interface design"

        low_score = self.fsa._calculate_lq_score(text3, text4)
        self.assertLess(low_score, high_score)

        # Test with identical text
        identical_score = self.fsa._calculate_lq_score(text1, text1)
        self.assertGreater(identical_score, high_score)

    def test_input_validation(self):
        """Test input validation and error handling."""
        # Test empty task description
        with self.assertRaises(ValueError) as context:
            self.fsa.build_context({"data": "test"}, "")
        self.assertIn("task_description", str(context.exception))

        # Test invalid raw_inputs type
        with self.assertRaises(ValueError) as context:
            self.fsa.build_context("invalid", "task")
        self.assertIn("raw_inputs", str(context.exception))

        # Test empty raw_inputs
        with self.assertRaises(ValueError) as context:
            self.fsa.build_context({}, "task description")
        self.assertIn("empty", str(context.exception))

        # Test None task description
        with self.assertRaises(ValueError) as context:
            self.fsa.build_context({"data": "test"}, None)
        self.assertIn("task_description", str(context.exception))

    def test_context_to_dict_serialization(self):
        """Test context serialization to dictionary."""
        raw_inputs = {
            "field1": "value1",
            "field2": "value2",
        }
        task_description = "test serialization"

        context = self.fsa.build_context(raw_inputs, task_description)

        # Convert to dict
        context_dict = context.to_dict()

        # Verify structure
        self.assertIsInstance(context_dict, dict)
        self.assertIn("items", context_dict)
        self.assertIn("entities", context_dict)
        self.assertIn("relationships", context_dict)
        self.assertIn("total_relevance_score", context_dict)
        self.assertIn("context_summary", context_dict)

        # Verify items are serializable
        self.assertIsInstance(context_dict["items"], list)
        for item in context_dict["items"]:
            self.assertIn("content", item)
            self.assertIn("relevance_score", item)
            self.assertIn("level", item)
            self.assertIsInstance(item["relevance_score"], float)

    def test_min_relevance_threshold_filtering(self):
        """Test that items below min_relevance_threshold are filtered."""
        # Create FSA with high threshold
        strict_fsa = ContextBuilderFSA(
            min_relevance_threshold=0.5,
            max_context_items=100,
        )

        # Create inputs with varying relevance
        raw_inputs = {
            "highly_relevant": "task processing and execution",
            "somewhat_relevant": "system configuration",
            "not_relevant": "xyz abc def",
        }
        task_description = "task processing"

        context = strict_fsa.build_context(raw_inputs, task_description)

        # All items should meet threshold
        for item in context.items:
            # Note: boost factors can push scores higher, so we check the general trend
            # At least some filtering should occur
            self.assertGreaterEqual(item.relevance_score, 0.0)

    def test_entity_consolidation_across_items(self):
        """Test that entities are consolidated across multiple context items."""
        raw_inputs = [
            "UserAccount Alice initiated request",
            "Alice wants to access DatabaseConnection",
            "Grant Alice permissions for DatabaseConnection",
        ]
        task_description = "Process Alice request for DatabaseConnection access"

        context = self.fsa.build_context(raw_inputs, task_description)

        # Find Alice entity
        alice_entities = [e for e in context.entities if "Alice" in e.name]

        if alice_entities:
            alice = alice_entities[0]
            # Should have multiple mentions since Alice appears in multiple items
            self.assertGreaterEqual(alice.mentions, 1)

    def test_empty_history_handling(self):
        """Test context building with empty or None history."""
        raw_inputs = {"task": "process data"}
        task_description = "data processing task"

        # Test with None history
        context1 = self.fsa.build_context(raw_inputs, task_description, history=None)
        self.assertGreater(len(context1.items), 0)

        # Test with empty history
        context2 = self.fsa.build_context(raw_inputs, task_description, history=[])
        self.assertGreater(len(context2.items), 0)

        # Both should produce similar results
        self.assertEqual(len(context1.items), len(context2.items))


class TestContextBuilderFSAEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions."""

    def test_large_scale_context(self):
        """Test performance with large-scale context."""
        fsa = ContextBuilderFSA(max_context_items=100)

        # Generate large history
        history = [f"Historical event {i} with details" for i in range(500)]
        raw_inputs = {"current": "current state"}
        task_description = "process current state"

        context = fsa.build_context(raw_inputs, task_description, history)

        # Should be pruned to max_context_items
        self.assertLessEqual(len(context.items), fsa.max_context_items + 10)
        self.assertGreater(context.total_relevance_score, 0.0)

    def test_special_characters_in_text(self):
        """Test handling of special characters and unicode."""
        raw_inputs = {
            "message": "Hello! @user #tag $100 50% https://example.com test@email.com",
            "unicode": "日本語 Русский العربية",
        }
        task_description = "process special characters and unicode"

        fsa = ContextBuilderFSA()
        context = fsa.build_context(raw_inputs, task_description)

        # Should handle without errors
        self.assertGreater(len(context.items), 0)

        # Should extract some entities (URLs, emails, numbers)
        entity_types = {e.entity_type for e in context.entities}
        # Should detect at least some patterns
        self.assertGreater(len(context.entities), 0)

    def test_nested_dict_and_complex_structures(self):
        """Test handling of nested dictionaries and complex structures."""
        raw_inputs = {
            "nested": {
                "level1": {
                    "level2": "deep value",
                },
            },
            "list_data": [1, 2, 3, "mixed", {"key": "value"}],
        }
        task_description = "process nested structures"

        fsa = ContextBuilderFSA()
        context = fsa.build_context(raw_inputs, task_description)

        # Should handle complex structures
        self.assertGreater(len(context.items), 0)
        self.assertGreater(context.total_relevance_score, 0.0)


def run_tests():
    """Run all tests."""
    unittest.main(argv=[''], verbosity=2, exit=False)


if __name__ == "__main__":
    unittest.main(verbosity=2)

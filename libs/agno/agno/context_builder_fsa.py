"""
Context Builder FSA (Finite State Automaton) for intelligent context management.

This module provides a production-ready implementation for building, scoring, and
managing contextual information with support for entity extraction, relationship
mapping, and hierarchical context organization.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import re
import math
from collections import defaultdict, Counter
from datetime import datetime


class ContextLevel(Enum):
    """Hierarchical context levels."""
    IMMEDIATE = "immediate"  # Most recent/current context
    RECENT = "recent"  # Recent history
    HISTORICAL = "historical"  # Older historical context


@dataclass
class Entity:
    """Represents an extracted entity from context."""
    name: str
    entity_type: str
    mentions: int = 1
    confidence: float = 1.0
    contexts: List[str] = field(default_factory=list)

    def __hash__(self):
        return hash((self.name, self.entity_type))

    def __eq__(self, other):
        if not isinstance(other, Entity):
            return False
        return self.name == other.name and self.entity_type == other.entity_type


@dataclass
class Relationship:
    """Represents a relationship between entities."""
    source: Entity
    target: Entity
    relationship_type: str
    strength: float = 1.0

    def __hash__(self):
        return hash((self.source, self.target, self.relationship_type))


@dataclass
class ContextItem:
    """Represents a single context item with metadata."""
    content: Any
    relevance_score: float
    level: ContextLevel
    timestamp: Optional[datetime] = None
    entities: Set[Entity] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __lt__(self, other):
        """Enable sorting by relevance score."""
        return self.relevance_score < other.relevance_score


@dataclass
class StructuredContext:
    """Structured context output with all metadata."""
    items: List[ContextItem]
    entities: Set[Entity]
    relationships: Set[Relationship]
    total_relevance_score: float
    context_summary: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "items": [
                {
                    "content": item.content,
                    "relevance_score": item.relevance_score,
                    "level": item.level.value,
                    "timestamp": item.timestamp.isoformat() if item.timestamp else None,
                    "entities": [{"name": e.name, "type": e.entity_type} for e in item.entities],
                    "metadata": item.metadata,
                }
                for item in self.items
            ],
            "entities": [
                {
                    "name": e.name,
                    "type": e.entity_type,
                    "mentions": e.mentions,
                    "confidence": e.confidence,
                }
                for e in self.entities
            ],
            "relationships": [
                {
                    "source": r.source.name,
                    "target": r.target.name,
                    "type": r.relationship_type,
                    "strength": r.strength,
                }
                for r in self.relationships
            ],
            "total_relevance_score": self.total_relevance_score,
            "context_summary": self.context_summary,
        }


class ContextBuilderFSA:
    """
    Finite State Automaton for building and managing contextual information.

    This class implements intelligent context building with:
    - LQ-based relevance scoring
    - Entity extraction and relationship mapping
    - Context pruning and hierarchical organization
    - Efficient algorithms for large-scale context processing

    Args:
        max_context_items: Maximum number of context items to retain (default: 50)
        immediate_window: Number of most recent items for immediate context (default: 5)
        recent_window: Number of items for recent context (default: 15)
        min_relevance_threshold: Minimum relevance score to include (default: 0.1)
        entity_extraction_enabled: Whether to extract entities (default: True)
    """

    def __init__(
        self,
        max_context_items: int = 50,
        immediate_window: int = 5,
        recent_window: int = 15,
        min_relevance_threshold: float = 0.1,
        entity_extraction_enabled: bool = True,
    ):
        """Initialize the Context Builder FSA."""
        self.max_context_items = max_context_items
        self.immediate_window = immediate_window
        self.recent_window = recent_window
        self.min_relevance_threshold = min_relevance_threshold
        self.entity_extraction_enabled = entity_extraction_enabled

        # Entity patterns for extraction
        self._entity_patterns = {
            "identifier": re.compile(r'\b[A-Z][a-zA-Z0-9_]{2,}\b'),
            "variable": re.compile(r'\b[a-z_][a-z0-9_]*\b'),
            "number": re.compile(r'\b\d+(?:\.\d+)?\b'),
            "url": re.compile(r'https?://[^\s]+'),
            "email": re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
        }

    def build_context(
        self,
        raw_inputs: Union[Dict[str, Any], List[Any]],
        task_description: str,
        history: Optional[List[Any]] = None,
    ) -> StructuredContext:
        """
        Build structured context from raw inputs, task description, and history.

        Args:
            raw_inputs: Raw input data (dict or list)
            task_description: Description of the task
            history: Optional historical context

        Returns:
            StructuredContext: Structured context with relevance scores and metadata

        Raises:
            ValueError: If inputs are invalid
        """
        # Validate inputs
        self._validate_inputs(raw_inputs, task_description)

        # Initialize context items
        context_items: List[ContextItem] = []

        # Process raw inputs
        if isinstance(raw_inputs, dict):
            for key, value in raw_inputs.items():
                item = self._create_context_item(
                    content={key: value},
                    level=ContextLevel.IMMEDIATE,
                    reference_text=task_description,
                )
                context_items.append(item)
        elif isinstance(raw_inputs, list):
            for idx, value in enumerate(raw_inputs):
                item = self._create_context_item(
                    content=value,
                    level=ContextLevel.IMMEDIATE,
                    reference_text=task_description,
                )
                context_items.append(item)

        # Process task description as immediate context
        task_item = self._create_context_item(
            content={"task": task_description},
            level=ContextLevel.IMMEDIATE,
            reference_text=task_description,
            boost_factor=1.5,  # Boost task description relevance
        )
        context_items.append(task_item)

        # Process history with hierarchical levels
        if history:
            history_items = self._process_history(history, task_description)
            context_items.extend(history_items)

        # Prune context to top-k items
        pruned_items = self._prune_context(context_items)

        # Extract entities and relationships
        entities = set()
        relationships = set()

        if self.entity_extraction_enabled:
            entities = self._extract_entities(pruned_items)
            relationships = self._extract_relationships(entities, pruned_items)

        # Calculate total relevance
        total_relevance = sum(item.relevance_score for item in pruned_items)

        # Build context summary
        summary = self._build_summary(pruned_items, entities, relationships)

        return StructuredContext(
            items=pruned_items,
            entities=entities,
            relationships=relationships,
            total_relevance_score=total_relevance,
            context_summary=summary,
        )

    def extract_relevant_context(
        self,
        structured_context: StructuredContext,
        query: str,
        top_k: Optional[int] = None,
    ) -> List[ContextItem]:
        """
        Extract the most relevant context items for a given query.

        Args:
            structured_context: Previously built structured context
            query: Query string to match against
            top_k: Number of top items to return (default: immediate_window)

        Returns:
            List[ContextItem]: Top-k most relevant context items
        """
        if top_k is None:
            top_k = self.immediate_window

        # Re-score items based on query
        rescored_items = []
        for item in structured_context.items:
            new_score = self._calculate_lq_score(
                self._item_to_text(item.content),
                query,
            )
            # Combine with original score (weighted average)
            combined_score = 0.6 * new_score + 0.4 * item.relevance_score

            rescored_item = ContextItem(
                content=item.content,
                relevance_score=combined_score,
                level=item.level,
                timestamp=item.timestamp,
                entities=item.entities,
                metadata=item.metadata,
            )
            rescored_items.append(rescored_item)

        # Sort by relevance and return top-k
        rescored_items.sort(reverse=True)
        return rescored_items[:top_k]

    def _validate_inputs(
        self,
        raw_inputs: Union[Dict[str, Any], List[Any]],
        task_description: str,
    ) -> None:
        """Validate input parameters."""
        if not task_description or not isinstance(task_description, str):
            raise ValueError("task_description must be a non-empty string")

        if not isinstance(raw_inputs, (dict, list)):
            raise ValueError("raw_inputs must be a dict or list")

        if isinstance(raw_inputs, (dict, list)) and len(raw_inputs) == 0:
            raise ValueError("raw_inputs cannot be empty")

    def _create_context_item(
        self,
        content: Any,
        level: ContextLevel,
        reference_text: str,
        boost_factor: float = 1.0,
    ) -> ContextItem:
        """Create a context item with relevance scoring."""
        content_text = self._item_to_text(content)
        relevance_score = self._calculate_lq_score(content_text, reference_text) * boost_factor

        # Extract entities for this item
        entities = set()
        if self.entity_extraction_enabled:
            entities = self._extract_entities_from_text(content_text)

        return ContextItem(
            content=content,
            relevance_score=max(relevance_score, 0.0),  # Ensure non-negative
            level=level,
            timestamp=datetime.now(),
            entities=entities,
            metadata={"boost_factor": boost_factor},
        )

    def _calculate_lq_score(self, text1: str, text2: str) -> float:
        """
        Calculate LQ-based (Lexical Quality) relevance score between two texts.

        Uses a combination of:
        - Token overlap (Jaccard similarity)
        - TF-IDF-inspired weighting
        - Length normalization

        Args:
            text1: First text
            text2: Second text (reference)

        Returns:
            float: Relevance score between 0 and 1
        """
        # Tokenize and normalize
        tokens1 = self._tokenize(text1.lower())
        tokens2 = self._tokenize(text2.lower())

        if not tokens1 or not tokens2:
            return 0.0

        # Calculate token overlap (Jaccard similarity)
        set1, set2 = set(tokens1), set(tokens2)
        intersection = set1 & set2
        union = set1 | set2
        jaccard = len(intersection) / len(union) if union else 0.0

        # Calculate weighted overlap (TF-IDF inspired)
        counter1 = Counter(tokens1)
        counter2 = Counter(tokens2)

        # Weight tokens by inverse frequency (rare tokens are more important)
        total_tokens = len(tokens1) + len(tokens2)
        weighted_score = 0.0

        for token in intersection:
            tf1 = counter1[token] / len(tokens1)
            tf2 = counter2[token] / len(tokens2)
            # IDF approximation: log(total / frequency)
            idf = math.log(total_tokens / (counter1[token] + counter2[token]))
            weighted_score += (tf1 + tf2) * idf

        # Normalize weighted score
        max_possible_score = sum(
            math.log(total_tokens / (counter1[t] + counter2.get(t, 1)))
            for t in set1
        )
        normalized_weighted = weighted_score / max_possible_score if max_possible_score > 0 else 0.0

        # Combine scores (weighted average)
        final_score = 0.4 * jaccard + 0.6 * normalized_weighted

        return min(final_score, 1.0)  # Cap at 1.0

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into words."""
        # Simple whitespace tokenization with basic preprocessing
        tokens = re.findall(r'\b\w+\b', text)
        # Filter out very short tokens and common stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        return [t for t in tokens if len(t) > 1 and t not in stop_words]

    def _item_to_text(self, item: Any) -> str:
        """Convert item to text representation."""
        if isinstance(item, str):
            return item
        elif isinstance(item, dict):
            return " ".join(f"{k} {v}" for k, v in item.items())
        elif isinstance(item, (list, tuple)):
            return " ".join(str(x) for x in item)
        else:
            return str(item)

    def _process_history(
        self,
        history: List[Any],
        reference_text: str,
    ) -> List[ContextItem]:
        """Process history into hierarchical context items."""
        items = []
        history_len = len(history)

        for idx, hist_item in enumerate(history):
            # Determine context level based on recency
            position_from_end = history_len - idx

            if position_from_end <= self.immediate_window:
                level = ContextLevel.IMMEDIATE
                boost = 1.2
            elif position_from_end <= self.recent_window:
                level = ContextLevel.RECENT
                boost = 1.0
            else:
                level = ContextLevel.HISTORICAL
                boost = 0.8

            # Apply temporal decay
            temporal_decay = math.exp(-0.1 * (history_len - idx))
            boost *= temporal_decay

            item = self._create_context_item(
                content=hist_item,
                level=level,
                reference_text=reference_text,
                boost_factor=boost,
            )
            items.append(item)

        return items

    def _prune_context(self, items: List[ContextItem]) -> List[ContextItem]:
        """
        Prune context to keep only top-k relevant items.

        Uses a combination of relevance score and hierarchical importance.
        """
        # Filter by minimum threshold
        filtered = [item for item in items if item.relevance_score >= self.min_relevance_threshold]

        # Sort by relevance score (descending)
        filtered.sort(reverse=True)

        # Keep top-k items
        pruned = filtered[:self.max_context_items]

        # Ensure we have representation from each level if possible
        level_counts = Counter(item.level for item in pruned)

        # If we're missing a level and have more items, try to include at least one
        for level in ContextLevel:
            if level_counts[level] == 0:
                # Find best item from this level not in pruned
                level_items = [item for item in filtered if item.level == level and item not in pruned]
                if level_items and len(pruned) < self.max_context_items:
                    # Add the best one from this level
                    pruned.append(level_items[0])

        return pruned

    def _extract_entities(self, items: List[ContextItem]) -> Set[Entity]:
        """Extract and consolidate entities from context items."""
        entity_dict: Dict[Tuple[str, str], Entity] = {}

        for item in items:
            for entity in item.entities:
                key = (entity.name, entity.entity_type)
                if key in entity_dict:
                    # Merge: increment mentions, update confidence
                    existing = entity_dict[key]
                    existing.mentions += entity.mentions
                    existing.confidence = max(existing.confidence, entity.confidence)
                    existing.contexts.extend(entity.contexts)
                else:
                    entity_dict[key] = entity

        return set(entity_dict.values())

    def _extract_entities_from_text(self, text: str) -> Set[Entity]:
        """Extract entities from a single text."""
        entities = set()

        for entity_type, pattern in self._entity_patterns.items():
            matches = pattern.findall(text)
            for match in matches:
                # Skip very common/generic terms
                if len(match) > 2:
                    entity = Entity(
                        name=match,
                        entity_type=entity_type,
                        mentions=1,
                        confidence=0.8,  # Base confidence
                        contexts=[text[:100]],  # Store snippet
                    )
                    entities.add(entity)

        return entities

    def _extract_relationships(
        self,
        entities: Set[Entity],
        items: List[ContextItem],
    ) -> Set[Relationship]:
        """Extract relationships between entities based on co-occurrence."""
        relationships = set()
        entity_list = list(entities)

        # For each context item, find entity co-occurrences
        for item in items:
            item_text = self._item_to_text(item.content).lower()

            # Find which entities appear in this item
            present_entities = [e for e in entity_list if e.name.lower() in item_text]

            # Create relationships for co-occurring entities
            for i, entity1 in enumerate(present_entities):
                for entity2 in present_entities[i + 1:]:
                    # Determine relationship type based on proximity
                    idx1 = item_text.index(entity1.name.lower())
                    idx2 = item_text.index(entity2.name.lower())
                    distance = abs(idx1 - idx2)

                    # Closer entities have stronger relationships
                    strength = 1.0 / (1.0 + math.log(1 + distance / 10))

                    # Determine relationship type
                    rel_type = "co-occurs_with"
                    if distance < 20:
                        rel_type = "closely_related"
                    elif distance < 50:
                        rel_type = "related"

                    relationship = Relationship(
                        source=entity1,
                        target=entity2,
                        relationship_type=rel_type,
                        strength=strength,
                    )
                    relationships.add(relationship)

        return relationships

    def _build_summary(
        self,
        items: List[ContextItem],
        entities: Set[Entity],
        relationships: Set[Relationship],
    ) -> Dict[str, Any]:
        """Build a summary of the context."""
        level_distribution = Counter(item.level for item in items)

        return {
            "total_items": len(items),
            "level_distribution": {
                "immediate": level_distribution[ContextLevel.IMMEDIATE],
                "recent": level_distribution[ContextLevel.RECENT],
                "historical": level_distribution[ContextLevel.HISTORICAL],
            },
            "total_entities": len(entities),
            "total_relationships": len(relationships),
            "avg_relevance_score": sum(item.relevance_score for item in items) / len(items) if items else 0.0,
            "top_entities": [
                {"name": e.name, "type": e.entity_type, "mentions": e.mentions}
                for e in sorted(entities, key=lambda x: x.mentions, reverse=True)[:5]
            ],
        }

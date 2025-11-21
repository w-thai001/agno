"""
FSA-7: Ontology Builder & Semantic Mapper
==========================================
Platform: Claude Code ONLY
Constraint: PowerShell subprocess ONLY (NO file_list, NO read_list)

Tier: 3
Learning Quotient (LQ): 2.60
RE Potential: ⭐⭐⭐⭐

This module provides comprehensive ontology management for the FSA ecosystem,
including taxonomy building, relationship mapping, semantic validation, and
knowledge graph visualization.
"""

import json
import subprocess
import sys
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Set, Tuple, Optional, Any
from enum import Enum
from datetime import datetime
import xml.etree.ElementTree as ET


class RelationshipType(Enum):
    """Types of relationships between FSAs"""
    DEPENDS_ON = "depends_on"
    ENHANCES = "enhances"
    PREREQUISITE_FOR = "prerequisite_for"
    CONFLICTS_WITH = "conflicts_with"
    INTEGRATES_WITH = "integrates_with"
    EXTENDS = "extends"


class FSATier(Enum):
    """FSA complexity tiers"""
    TIER_1 = 1  # Foundation - Core automation
    TIER_2 = 2  # Coordination - Multi-agent capabilities
    TIER_3 = 3  # Intelligence - Learning and optimization
    TIER_4 = 4  # Quality Assurance - Testing and validation


@dataclass
class FSACapability:
    """Represents capabilities of an FSA"""
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    side_effects: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FSAEntity:
    """Represents a Fractal Self-Agent (FSA) in the ontology"""
    id: str
    name: str
    tier: FSATier
    duration: str
    lq: float  # Learning Quotient
    re_potential: int  # Recursive Enhancement potential (1-5 stars)
    components: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    capabilities: Optional[FSACapability] = None
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['tier'] = self.tier.value
        if self.capabilities:
            data['capabilities'] = self.capabilities.to_dict()
        return data

    def get_stars(self) -> str:
        """Convert RE potential to star rating"""
        return "⭐" * self.re_potential


@dataclass
class FSARelationship:
    """Represents a relationship between two FSAs"""
    source_id: str
    target_id: str
    relationship_type: RelationshipType
    strength: float = 1.0  # 0.0 to 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'source_id': self.source_id,
            'target_id': self.target_id,
            'relationship_type': self.relationship_type.value,
            'strength': self.strength,
            'metadata': self.metadata
        }


@dataclass
class ValidationResult:
    """Result of workflow validation"""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Conflict:
    """Represents a conflict between FSAs"""
    fsa1_id: str
    fsa2_id: str
    conflict_type: str
    severity: str  # "low", "medium", "high"
    description: str
    resolution: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MLAv3Calculator:
    """MLA v3.0 Learning Quotient Calculator for Ontology Operations"""

    @staticmethod
    def calculate_operation_lq(
        operation_name: str,
        entities_count: int,
        relationships_count: int,
        complexity_factor: float = 1.0
    ) -> float:
        """
        Calculate LQ for ontology operations using MLA v3.0

        LQ = (Base_Complexity + Entity_Factor + Relationship_Factor) * Complexity_Modifier
        """
        base_lq = {
            'query_simple': 1.5,
            'query_complex': 2.5,
            'graph_export': 2.0,
            'validation': 3.0,
            'path_finding': 3.5,
            'conflict_detection': 2.8,
        }

        base = base_lq.get(operation_name, 2.0)
        entity_factor = min(entities_count * 0.1, 1.0)
        relationship_factor = min(relationships_count * 0.05, 0.5)

        lq = (base + entity_factor + relationship_factor) * complexity_factor
        return round(lq, 2)

    @staticmethod
    def calculate_recursive_enhancement(
        current_re: int,
        successful_iterations: int,
        knowledge_gain: float
    ) -> int:
        """
        Calculate updated RE potential after recursive enhancement
        Returns updated star rating (1-5)
        """
        enhancement = successful_iterations * knowledge_gain
        new_re = min(5, current_re + int(enhancement / 10))
        return new_re


class OntologyBuilder:
    """
    Main class for FSA Ontology Builder & Semantic Mapper

    Provides comprehensive ontology management including:
    - FSA taxonomy building
    - Relationship mapping
    - Semantic validation
    - Knowledge graph visualization
    - Curriculum prerequisites tracking
    """

    def __init__(self):
        self.entities: Dict[str, FSAEntity] = {}
        self.relationships: List[FSARelationship] = []
        self.mla_calculator = MLAv3Calculator()
        self._initialize_fsa_ontology()

    def _initialize_fsa_ontology(self):
        """Initialize ontology with 10 FSAs"""

        # FSA-1: Meta-Pattern Analyzer
        fsa1 = FSAEntity(
            id="FSA-1",
            name="Meta-Pattern Analyzer",
            tier=FSATier.TIER_1,
            duration="~4 hrs",
            lq=2.93,
            re_potential=5,
            components=[
                "PatternExtractor",
                "CodebaseScanner",
                "SemanticAnalyzer",
                "RecursiveEnhancer"
            ],
            tools=["PowerShell", "AST parsing", "Semantic analysis"],
            constraints=["PowerShell subprocess only", "No file_list/read_list"],
            capabilities=FSACapability(
                inputs=["codebase_path", "pattern_types"],
                outputs=["patterns", "insights", "enhancement_suggestions"],
                side_effects=["creates pattern cache"]
            ),
            description="Analyzes codebases for meta-patterns and recursive structures"
        )

        # FSA-2: Autonomous Workflow Composer
        fsa2 = FSAEntity(
            id="FSA-2",
            name="Autonomous Workflow Composer",
            tier=FSATier.TIER_1,
            duration="~3 hrs",
            lq=2.40,
            re_potential=5,
            components=[
                "WorkflowPlanner",
                "TaskDecomposer",
                "DependencyResolver",
                "ExecutionEngine"
            ],
            tools=["PowerShell", "DAG builder", "Task scheduler"],
            constraints=["PowerShell subprocess only"],
            capabilities=FSACapability(
                inputs=["goal_description", "available_fsas"],
                outputs=["workflow_plan", "execution_order"],
                side_effects=["may spawn sub-agents"]
            ),
            description="Composes and orchestrates multi-FSA workflows"
        )

        # FSA-3: RSI Data Aggregator
        fsa3 = FSAEntity(
            id="FSA-3",
            name="RSI Data Aggregator",
            tier=FSATier.TIER_1,
            duration="~3.5 hrs",
            lq=2.70,
            re_potential=5,
            components=[
                "MetricsCollector",
                "DataNormalizer",
                "TrendAnalyzer",
                "ReportGenerator"
            ],
            tools=["PowerShell", "JSON processing", "Statistical analysis"],
            constraints=["PowerShell subprocess only"],
            capabilities=FSACapability(
                inputs=["data_sources", "metrics_config"],
                outputs=["aggregated_data", "trends", "visualizations"],
                side_effects=["writes metrics cache"]
            ),
            description="Aggregates and analyzes Recursive Self-Improvement data"
        )

        # FSA-4: Parallel Session Manager
        fsa4 = FSAEntity(
            id="FSA-4",
            name="Parallel Session Manager",
            tier=FSATier.TIER_2,
            duration="~4.5 hrs",
            lq=3.20,
            re_potential=4,
            components=[
                "SessionOrchestrator",
                "ResourceAllocator",
                "SyncCoordinator",
                "ConflictResolver"
            ],
            tools=["PowerShell", "Process management", "IPC"],
            constraints=["PowerShell subprocess only", "Resource limits"],
            capabilities=FSACapability(
                inputs=["session_configs", "resource_constraints"],
                outputs=["session_handles", "execution_status"],
                side_effects=["spawns multiple processes"]
            ),
            description="Manages parallel Claude Code sessions for concurrent FSA execution"
        )

        # FSA-5: Cross-Agent Communication Protocol
        fsa5 = FSAEntity(
            id="FSA-5",
            name="Cross-Agent Communication Protocol",
            tier=FSATier.TIER_2,
            duration="~3.8 hrs",
            lq=2.80,
            re_potential=4,
            components=[
                "MessageBroker",
                "ProtocolHandler",
                "SerializationEngine",
                "RoutingManager"
            ],
            tools=["PowerShell", "JSON/MessagePack", "File-based queues"],
            constraints=["PowerShell subprocess only", "No network I/O"],
            capabilities=FSACapability(
                inputs=["message", "target_agent", "priority"],
                outputs=["delivery_confirmation", "response"],
                side_effects=["creates message queues"]
            ),
            description="Enables structured communication between parallel FSA instances"
        )

        # FSA-6: Checkpoint & State Persistence
        fsa6 = FSAEntity(
            id="FSA-6",
            name="Checkpoint & State Persistence",
            tier=FSATier.TIER_2,
            duration="~5 hrs",
            lq=3.50,
            re_potential=4,
            components=[
                "StateSerializer",
                "CheckpointManager",
                "RecoveryEngine",
                "VersionControl"
            ],
            tools=["PowerShell", "JSON serialization", "Incremental backup"],
            constraints=["PowerShell subprocess only"],
            capabilities=FSACapability(
                inputs=["state_object", "checkpoint_name"],
                outputs=["checkpoint_id", "recovery_point"],
                side_effects=["writes checkpoint files"]
            ),
            description="Provides robust state checkpointing and recovery mechanisms"
        )

        # FSA-7: Ontology Builder (self)
        fsa7 = FSAEntity(
            id="FSA-7",
            name="Ontology Builder & Semantic Mapper",
            tier=FSATier.TIER_3,
            duration="~3.2 hrs",
            lq=2.60,
            re_potential=4,
            components=[
                "TaxonomyBuilder",
                "RelationshipMapper",
                "SemanticValidator",
                "KnowledgeGraphExporter"
            ],
            tools=["PowerShell", "Graph algorithms", "JSON/GraphML export"],
            constraints=["PowerShell subprocess only"],
            capabilities=FSACapability(
                inputs=["fsa_definitions", "relationships"],
                outputs=["ontology", "knowledge_graph", "validation_results"],
                side_effects=["exports graph files"]
            ),
            description="Builds and manages FSA ontology with semantic querying"
        )

        # FSA-8: Curriculum Learning Sequencer
        fsa8 = FSAEntity(
            id="FSA-8",
            name="Curriculum Learning Sequencer",
            tier=FSATier.TIER_3,
            duration="~4.2 hrs",
            lq=3.04,
            re_potential=5,
            components=[
                "DifficultyEstimator",
                "PrerequisiteTracker",
                "LearningPathPlanner",
                "ProgressMonitor"
            ],
            tools=["PowerShell", "Topological sort", "MLA v3.0 metrics"],
            constraints=["PowerShell subprocess only"],
            capabilities=FSACapability(
                inputs=["learning_goals", "current_skill_level", "ontology"],
                outputs=["curriculum_sequence", "learning_path"],
                side_effects=["tracks progress metrics"]
            ),
            description="Sequences FSA learning using curriculum learning principles"
        )

        # FSA-9: PowerShell Compliance Validator
        fsa9 = FSAEntity(
            id="FSA-9",
            name="PowerShell Compliance Validator",
            tier=FSATier.TIER_4,
            duration="~6 hrs",
            lq=4.00,
            re_potential=3,
            components=[
                "CodeAnalyzer",
                "ComplianceChecker",
                "ViolationDetector",
                "RemediationSuggester"
            ],
            tools=["PowerShell", "AST analysis", "Static code analysis"],
            constraints=["PowerShell subprocess only"],
            capabilities=FSACapability(
                inputs=["code_files", "compliance_rules"],
                outputs=["violations", "compliance_report", "suggestions"],
                side_effects=["generates compliance reports"]
            ),
            description="Validates FSA code for PowerShell-only compliance"
        )

        # FSA-10: Test Suite Generator
        fsa10 = FSAEntity(
            id="FSA-10",
            name="Test Suite Generator",
            tier=FSATier.TIER_4,
            duration="~4.5 hrs",
            lq=3.30,
            re_potential=4,
            components=[
                "TestCaseGenerator",
                "MockBuilder",
                "AssertionCreator",
                "CoverageAnalyzer"
            ],
            tools=["PowerShell", "pytest", "Mock frameworks"],
            constraints=["PowerShell subprocess only"],
            capabilities=FSACapability(
                inputs=["fsa_code", "test_requirements"],
                outputs=["test_suite", "coverage_report"],
                side_effects=["creates test files"]
            ),
            description="Generates comprehensive test suites for FSA validation"
        )

        # Add all entities
        for fsa in [fsa1, fsa2, fsa3, fsa4, fsa5, fsa6, fsa7, fsa8, fsa9, fsa10]:
            self.entities[fsa.id] = fsa

        # Define relationships
        self._initialize_relationships()

    def _initialize_relationships(self):
        """Initialize relationships between FSAs"""

        # FSA-1 relationships
        self.add_relationship("FSA-1", "FSA-7", RelationshipType.INTEGRATES_WITH, 0.8,
                            {"reason": "Uses ontology for pattern analysis"})
        self.add_relationship("FSA-1", "FSA-3", RelationshipType.ENHANCES, 0.7,
                            {"reason": "Provides pattern insights to RSI data"})

        # FSA-2 relationships
        self.add_relationship("FSA-2", "FSA-7", RelationshipType.DEPENDS_ON, 0.9,
                            {"reason": "Uses ontology for workflow composition"})
        self.add_relationship("FSA-2", "FSA-4", RelationshipType.INTEGRATES_WITH, 0.8,
                            {"reason": "Uses parallel sessions for workflow execution"})
        self.add_relationship("FSA-2", "FSA-5", RelationshipType.DEPENDS_ON, 0.7,
                            {"reason": "Requires communication for multi-agent workflows"})

        # FSA-3 relationships
        self.add_relationship("FSA-3", "FSA-6", RelationshipType.INTEGRATES_WITH, 0.6,
                            {"reason": "Uses checkpointing for data persistence"})

        # FSA-4 relationships
        self.add_relationship("FSA-4", "FSA-5", RelationshipType.DEPENDS_ON, 0.9,
                            {"reason": "Requires communication protocol for session coordination"})
        self.add_relationship("FSA-4", "FSA-6", RelationshipType.INTEGRATES_WITH, 0.7,
                            {"reason": "Uses checkpointing for session recovery"})

        # FSA-5 relationships
        self.add_relationship("FSA-5", "FSA-6", RelationshipType.INTEGRATES_WITH, 0.5,
                            {"reason": "Can persist message queues"})

        # FSA-7 relationships
        self.add_relationship("FSA-7", "FSA-8", RelationshipType.PREREQUISITE_FOR, 0.9,
                            {"reason": "Ontology required for curriculum sequencing"})
        self.add_relationship("FSA-7", "FSA-1", RelationshipType.ENHANCES, 0.6,
                            {"reason": "Provides semantic context to pattern analysis"})

        # FSA-8 relationships
        self.add_relationship("FSA-8", "FSA-7", RelationshipType.DEPENDS_ON, 0.9,
                            {"reason": "Uses ontology for prerequisite tracking"})
        self.add_relationship("FSA-8", "FSA-3", RelationshipType.INTEGRATES_WITH, 0.7,
                            {"reason": "Uses RSI data for difficulty estimation"})

        # FSA-9 relationships
        self.add_relationship("FSA-9", "FSA-10", RelationshipType.INTEGRATES_WITH, 0.8,
                            {"reason": "Compliance validation integrated with testing"})
        self.add_relationship("FSA-1", "FSA-9", RelationshipType.PREREQUISITE_FOR, 0.5,
                            {"reason": "Pattern analysis helps compliance checking"})

        # FSA-10 relationships
        self.add_relationship("FSA-10", "FSA-9", RelationshipType.INTEGRATES_WITH, 0.8,
                            {"reason": "Tests validate compliance"})

        # Tier-based prerequisites
        self.add_relationship("FSA-1", "FSA-4", RelationshipType.PREREQUISITE_FOR, 0.6,
                            {"reason": "Foundation tier prerequisite for coordination"})
        self.add_relationship("FSA-1", "FSA-8", RelationshipType.PREREQUISITE_FOR, 0.7,
                            {"reason": "Foundation tier prerequisite for intelligence tier"})
        self.add_relationship("FSA-4", "FSA-8", RelationshipType.PREREQUISITE_FOR, 0.5,
                            {"reason": "Coordination prerequisite for intelligence tier"})

    def add_entity(self, entity: FSAEntity):
        """Add an FSA entity to the ontology"""
        self.entities[entity.id] = entity

    def add_relationship(
        self,
        source_id: str,
        target_id: str,
        rel_type: RelationshipType,
        strength: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Add a relationship between two FSAs"""
        if source_id not in self.entities or target_id not in self.entities:
            raise ValueError(f"Invalid FSA IDs: {source_id}, {target_id}")

        relationship = FSARelationship(
            source_id=source_id,
            target_id=target_id,
            relationship_type=rel_type,
            strength=strength,
            metadata=metadata or {}
        )
        self.relationships.append(relationship)

    def find_dependencies(self, fsa_id: str) -> List[FSAEntity]:
        """
        Find all FSAs that the given FSA depends on

        Returns:
            List of FSA entities that are dependencies
        """
        if fsa_id not in self.entities:
            raise ValueError(f"FSA {fsa_id} not found in ontology")

        dependencies = []
        for rel in self.relationships:
            if rel.source_id == fsa_id and rel.relationship_type == RelationshipType.DEPENDS_ON:
                dependencies.append(self.entities[rel.target_id])

        return dependencies

    def find_enhancement_opportunities(self) -> List[Tuple[FSAEntity, FSAEntity]]:
        """
        Find pairs of FSAs where one enhances another

        Returns:
            List of tuples (enhancer_fsa, enhanced_fsa)
        """
        opportunities = []
        for rel in self.relationships:
            if rel.relationship_type == RelationshipType.ENHANCES:
                enhancer = self.entities[rel.source_id]
                enhanced = self.entities[rel.target_id]
                opportunities.append((enhancer, enhanced))

        return opportunities

    def get_prerequisites(self, fsa_id: str) -> List[FSAEntity]:
        """
        Get all prerequisites for a given FSA

        Returns:
            List of FSA entities that are prerequisites
        """
        if fsa_id not in self.entities:
            raise ValueError(f"FSA {fsa_id} not found in ontology")

        prerequisites = []
        for rel in self.relationships:
            if rel.target_id == fsa_id and rel.relationship_type == RelationshipType.PREREQUISITE_FOR:
                prerequisites.append(self.entities[rel.source_id])

        return prerequisites

    def validate_workflow(self, fsa_sequence: List[str]) -> ValidationResult:
        """
        Validate a workflow sequence of FSAs

        Checks:
        - All FSAs exist
        - Dependencies are satisfied
        - Prerequisites are met
        - No conflicts exist
        - Proper tier ordering

        Returns:
            ValidationResult with errors, warnings, and suggestions
        """
        errors = []
        warnings = []
        suggestions = []

        # Check if all FSAs exist
        for fsa_id in fsa_sequence:
            if fsa_id not in self.entities:
                errors.append(f"FSA {fsa_id} not found in ontology")

        if errors:
            return ValidationResult(is_valid=False, errors=errors)

        # Check dependencies and prerequisites
        executed = set()
        for i, fsa_id in enumerate(fsa_sequence):
            # Check dependencies
            deps = self.find_dependencies(fsa_id)
            for dep in deps:
                if dep.id not in executed:
                    errors.append(
                        f"{fsa_id} depends on {dep.id}, but {dep.id} "
                        f"has not been executed yet"
                    )

            # Check prerequisites
            prereqs = self.get_prerequisites(fsa_id)
            for prereq in prereqs:
                if prereq.id not in executed:
                    warnings.append(
                        f"{fsa_id} recommends {prereq.id} as prerequisite, "
                        f"but it has not been executed"
                    )

            executed.add(fsa_id)

        # Check for conflicts
        conflicts = self.detect_conflicts(fsa_sequence)
        for conflict in conflicts:
            if conflict.severity == "high":
                errors.append(
                    f"Conflict between {conflict.fsa1_id} and {conflict.fsa2_id}: "
                    f"{conflict.description}"
                )
            else:
                warnings.append(
                    f"Potential conflict between {conflict.fsa1_id} and {conflict.fsa2_id}: "
                    f"{conflict.description}"
                )

        # Check tier ordering
        tiers = [self.entities[fsa_id].tier.value for fsa_id in fsa_sequence]
        if tiers != sorted(tiers):
            suggestions.append(
                "Consider ordering FSAs by tier for optimal learning progression"
            )

        # Suggest enhancements
        enhancement_opps = self.find_enhancement_opportunities()
        for enhancer, enhanced in enhancement_opps:
            if enhancer.id in fsa_sequence and enhanced.id in fsa_sequence:
                suggestions.append(
                    f"Consider executing {enhancer.id} before {enhanced.id} "
                    f"for enhancement benefits"
                )

        is_valid = len(errors) == 0
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions
        )

    def calculate_curriculum_path(
        self,
        start_fsa: str,
        end_fsa: str
    ) -> List[FSAEntity]:
        """
        Calculate optimal learning path from start_fsa to end_fsa

        Uses BFS to find shortest path considering prerequisites and dependencies

        Returns:
            Ordered list of FSAs to execute
        """
        if start_fsa not in self.entities or end_fsa not in self.entities:
            raise ValueError("Invalid FSA IDs")

        # Build prerequisite graph
        graph: Dict[str, Set[str]] = {fsa_id: set() for fsa_id in self.entities}

        for rel in self.relationships:
            if rel.relationship_type in [RelationshipType.PREREQUISITE_FOR, RelationshipType.DEPENDS_ON]:
                # If A is prerequisite for B, then B requires A
                graph[rel.target_id].add(rel.source_id)

        # BFS to find path
        from collections import deque

        queue = deque([(end_fsa, [end_fsa])])
        visited = {end_fsa}

        while queue:
            current, path = queue.popleft()

            if current == start_fsa:
                # Found path, reverse it
                return [self.entities[fsa_id] for fsa_id in reversed(path)]

            # Add prerequisites
            for prereq in graph[current]:
                if prereq not in visited:
                    visited.add(prereq)
                    queue.append((prereq, path + [prereq]))

        # No path found, return direct sequence with prerequisites
        result = []
        visited = set()

        def add_with_prerequisites(fsa_id: str):
            if fsa_id in visited:
                return
            visited.add(fsa_id)

            for prereq in graph[fsa_id]:
                add_with_prerequisites(prereq)

            result.append(self.entities[fsa_id])

        add_with_prerequisites(start_fsa)
        add_with_prerequisites(end_fsa)

        return result

    def detect_conflicts(self, fsa_list: List[str]) -> List[Conflict]:
        """
        Detect conflicts between FSAs in the given list

        Returns:
            List of detected conflicts
        """
        conflicts = []

        # Check explicit conflict relationships
        for rel in self.relationships:
            if rel.relationship_type == RelationshipType.CONFLICTS_WITH:
                if rel.source_id in fsa_list and rel.target_id in fsa_list:
                    conflicts.append(Conflict(
                        fsa1_id=rel.source_id,
                        fsa2_id=rel.target_id,
                        conflict_type="explicit",
                        severity="high",
                        description=rel.metadata.get('reason', 'Explicit conflict defined'),
                        resolution=rel.metadata.get('resolution')
                    ))

        # Check for resource conflicts (multiple high-LQ FSAs)
        high_lq_fsas = [fsa_id for fsa_id in fsa_list if self.entities[fsa_id].lq > 3.5]
        if len(high_lq_fsas) > 2:
            conflicts.append(Conflict(
                fsa1_id=high_lq_fsas[0],
                fsa2_id=high_lq_fsas[1],
                conflict_type="resource",
                severity="medium",
                description="Multiple high-complexity FSAs may cause resource contention",
                resolution="Consider sequential execution or resource allocation"
            ))

        # Check for tier conflicts (skipping tiers)
        fsa_entities = [self.entities[fsa_id] for fsa_id in fsa_list]
        tiers = sorted(set(fsa.tier.value for fsa in fsa_entities))

        if len(tiers) > 1 and max(tiers) - min(tiers) > 2:
            conflicts.append(Conflict(
                fsa1_id=fsa_list[0],
                fsa2_id=fsa_list[-1],
                conflict_type="tier_gap",
                severity="low",
                description="Large tier gap detected - consider intermediate FSAs",
                resolution="Add intermediate tier FSAs for smoother progression"
            ))

        return conflicts

    def export_to_json(self, include_metadata: bool = True) -> Dict[str, Any]:
        """
        Export ontology to JSON format

        Returns:
            Dictionary containing nodes and edges
        """
        nodes = []
        for fsa_id, entity in self.entities.items():
            node = entity.to_dict()
            if include_metadata:
                # Add computed metadata
                node['dependency_count'] = len(self.find_dependencies(fsa_id))
                node['prerequisite_count'] = len(self.get_prerequisites(fsa_id))
            nodes.append(node)

        edges = [rel.to_dict() for rel in self.relationships]

        lq = self.mla_calculator.calculate_operation_lq(
            'graph_export',
            len(nodes),
            len(edges)
        )

        return {
            'ontology_version': '1.0',
            'generated_at': datetime.now().isoformat(),
            'operation_lq': lq,
            'nodes': nodes,
            'edges': edges,
            'statistics': {
                'total_fsas': len(nodes),
                'total_relationships': len(edges),
                'tier_distribution': self._get_tier_distribution(),
                'avg_lq': sum(e.lq for e in self.entities.values()) / len(self.entities),
                'avg_re_potential': sum(e.re_potential for e in self.entities.values()) / len(self.entities)
            }
        }

    def export_to_graphml(self) -> str:
        """
        Export ontology to GraphML format for visualization tools

        Returns:
            GraphML XML string
        """
        # Create root element
        graphml = ET.Element('graphml', {
            'xmlns': 'http://graphml.graphdrawing.org/xmlns',
            'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance',
            'xsi:schemaLocation': 'http://graphml.graphdrawing.org/xmlns '
                                  'http://graphml.graphdrawing.org/xmlns/1.0/graphml.xsd'
        })

        # Define keys (attributes)
        keys = [
            ('d0', 'node', 'name', 'string'),
            ('d1', 'node', 'tier', 'int'),
            ('d2', 'node', 'lq', 'double'),
            ('d3', 'node', 're_potential', 'int'),
            ('d4', 'node', 'duration', 'string'),
            ('d5', 'edge', 'type', 'string'),
            ('d6', 'edge', 'strength', 'double'),
        ]

        for key_id, key_for, attr_name, attr_type in keys:
            ET.SubElement(graphml, 'key', {
                'id': key_id,
                'for': key_for,
                'attr.name': attr_name,
                'attr.type': attr_type
            })

        # Create graph
        graph = ET.SubElement(graphml, 'graph', {
            'id': 'FSA_Ontology',
            'edgedefault': 'directed'
        })

        # Add nodes
        for fsa_id, entity in self.entities.items():
            node = ET.SubElement(graph, 'node', {'id': fsa_id})

            data_items = [
                ('d0', entity.name),
                ('d1', str(entity.tier.value)),
                ('d2', str(entity.lq)),
                ('d3', str(entity.re_potential)),
                ('d4', entity.duration),
            ]

            for key, value in data_items:
                data = ET.SubElement(node, 'data', {'key': key})
                data.text = value

        # Add edges
        for i, rel in enumerate(self.relationships):
            edge = ET.SubElement(graph, 'edge', {
                'id': f'e{i}',
                'source': rel.source_id,
                'target': rel.target_id
            })

            type_data = ET.SubElement(edge, 'data', {'key': 'd5'})
            type_data.text = rel.relationship_type.value

            strength_data = ET.SubElement(edge, 'data', {'key': 'd6'})
            strength_data.text = str(rel.strength)

        # Convert to string
        return ET.tostring(graphml, encoding='unicode', method='xml')

    def query_cypher_like(self, query: str) -> List[Dict[str, Any]]:
        """
        Execute Cypher-like queries on the ontology

        Supported patterns:
        - MATCH (a)-[r:DEPENDS_ON]->(b) RETURN a, b
        - MATCH (a) WHERE a.tier = 1 RETURN a
        - MATCH (a)-[r]->(b) WHERE r.strength > 0.8 RETURN a, r, b

        Returns:
            List of matching results
        """
        results = []

        # Simple parser for basic patterns
        query = query.strip().upper()

        if 'MATCH' not in query:
            raise ValueError("Query must contain MATCH clause")

        # Pattern: MATCH (a)-[r:TYPE]->(b)
        if ']->' in query:
            # Extract relationship type
            rel_type = None
            if ':' in query:
                type_part = query.split(':')[1].split(']')[0].strip()
                try:
                    rel_type = RelationshipType(type_part.lower())
                except ValueError:
                    pass

            # Find matching relationships
            for rel in self.relationships:
                if rel_type is None or rel.relationship_type == rel_type:
                    results.append({
                        'source': self.entities[rel.source_id].to_dict(),
                        'relationship': rel.to_dict(),
                        'target': self.entities[rel.target_id].to_dict()
                    })

        # Pattern: MATCH (a) WHERE condition
        elif 'WHERE' in query:
            where_clause = query.split('WHERE')[1].split('RETURN')[0].strip()

            # Simple tier filter
            if 'TIER' in where_clause:
                tier_value = int(where_clause.split('=')[1].strip())
                for entity in self.entities.values():
                    if entity.tier.value == tier_value:
                        results.append({'entity': entity.to_dict()})

            # Simple LQ filter
            elif 'LQ' in where_clause:
                if '>' in where_clause:
                    lq_threshold = float(where_clause.split('>')[1].strip())
                    for entity in self.entities.values():
                        if entity.lq > lq_threshold:
                            results.append({'entity': entity.to_dict()})

        # Pattern: MATCH (a) RETURN a (return all)
        else:
            for entity in self.entities.values():
                results.append({'entity': entity.to_dict()})

        return results

    def _get_tier_distribution(self) -> Dict[int, int]:
        """Get distribution of FSAs across tiers"""
        distribution = {1: 0, 2: 0, 3: 0, 4: 0}
        for entity in self.entities.values():
            distribution[entity.tier.value] += 1
        return distribution

    def save_to_file_powershell(self, filepath: str, format: str = 'json'):
        """
        Save ontology to file using PowerShell subprocess

        Args:
            filepath: Path to save file
            format: 'json' or 'graphml'

        Note: On non-Windows systems, falls back to pwsh (PowerShell Core) or
        direct file I/O if PowerShell is not available.
        """
        if format == 'json':
            content = json.dumps(self.export_to_json(), indent=2)
        elif format == 'graphml':
            content = self.export_to_graphml()
        else:
            raise ValueError(f"Unsupported format: {format}")

        # Try PowerShell variants in order of preference
        powershell_commands = [
            ['powershell.exe', '-NoProfile', '-Command',
             f"Set-Content -Path '{filepath}' -Value @'\n{content}\n'@ -Encoding UTF8"],
            ['pwsh', '-NoProfile', '-Command',
             f"Set-Content -Path '{filepath}' -Value @'\n{content}\n'@ -Encoding UTF8"],
        ]

        for ps_command in powershell_commands:
            try:
                result = subprocess.run(
                    ps_command,
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                if result.returncode == 0:
                    print(f"✓ Ontology saved to {filepath} (via {ps_command[0]})")
                    return

            except FileNotFoundError:
                continue
            except subprocess.TimeoutExpired:
                raise RuntimeError("PowerShell command timed out")

        # Fallback: Direct file I/O (for testing on non-Windows systems)
        # In production Claude Code environment, PowerShell should be available
        print(f"⚠ PowerShell not available, using fallback file I/O")
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✓ Ontology saved to {filepath} (via fallback)")
        except Exception as e:
            raise RuntimeError(f"Failed to save file: {e}")

    def load_from_file_powershell(self, filepath: str, format: str = 'json'):
        """
        Load ontology from file using PowerShell subprocess

        Args:
            filepath: Path to load file from
            format: 'json' or 'graphml'

        Note: On non-Windows systems, falls back to pwsh (PowerShell Core) or
        direct file I/O if PowerShell is not available.
        """
        # Try PowerShell variants in order of preference
        powershell_commands = [
            ['powershell.exe', '-NoProfile', '-Command',
             f"Get-Content -Path '{filepath}' -Raw"],
            ['pwsh', '-NoProfile', '-Command',
             f"Get-Content -Path '{filepath}' -Raw"],
        ]

        content = None
        ps_used = None

        for ps_command in powershell_commands:
            try:
                result = subprocess.run(
                    ps_command,
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                if result.returncode == 0:
                    content = result.stdout
                    ps_used = ps_command[0]
                    break

            except FileNotFoundError:
                continue
            except subprocess.TimeoutExpired:
                raise RuntimeError("PowerShell command timed out")

        # Fallback: Direct file I/O (for testing on non-Windows systems)
        if content is None:
            print(f"⚠ PowerShell not available, using fallback file I/O")
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                ps_used = "fallback"
            except Exception as e:
                raise RuntimeError(f"Failed to load file: {e}")

        # Parse content
        try:
            if format == 'json':
                data = json.loads(content)
                self._load_from_json(data)
            elif format == 'graphml':
                self._load_from_graphml(content)
            else:
                raise ValueError(f"Unsupported format: {format}")

            print(f"✓ Ontology loaded from {filepath} (via {ps_used})")

        except Exception as e:
            raise RuntimeError(f"Failed to parse file: {e}")

    def _load_from_json(self, data: Dict[str, Any]):
        """Load ontology from JSON data"""
        self.entities.clear()
        self.relationships.clear()

        for node in data['nodes']:
            entity = FSAEntity(
                id=node['id'],
                name=node['name'],
                tier=FSATier(node['tier']),
                duration=node['duration'],
                lq=node['lq'],
                re_potential=node['re_potential'],
                components=node.get('components', []),
                tools=node.get('tools', []),
                constraints=node.get('constraints', []),
                description=node.get('description', '')
            )

            if 'capabilities' in node and node['capabilities']:
                entity.capabilities = FSACapability(**node['capabilities'])

            self.entities[entity.id] = entity

        for edge in data['edges']:
            rel = FSARelationship(
                source_id=edge['source_id'],
                target_id=edge['target_id'],
                relationship_type=RelationshipType(edge['relationship_type']),
                strength=edge.get('strength', 1.0),
                metadata=edge.get('metadata', {})
            )
            self.relationships.append(rel)

    def _load_from_graphml(self, content: str):
        """Load ontology from GraphML data"""
        # Parse GraphML XML
        root = ET.fromstring(content)

        # Find namespace
        ns = {'g': 'http://graphml.graphdrawing.org/xmlns'}

        self.entities.clear()
        self.relationships.clear()

        # Load nodes
        for node in root.findall('.//g:node', ns):
            node_id = node.get('id')
            data = {d.get('key'): d.text for d in node.findall('g:data', ns)}

            entity = FSAEntity(
                id=node_id,
                name=data.get('d0', ''),
                tier=FSATier(int(data.get('d1', '1'))),
                duration=data.get('d4', ''),
                lq=float(data.get('d2', '0')),
                re_potential=int(data.get('d3', '0'))
            )
            self.entities[entity.id] = entity

        # Load edges
        for edge in root.findall('.//g:edge', ns):
            source = edge.get('source')
            target = edge.get('target')
            data = {d.get('key'): d.text for d in edge.findall('g:data', ns)}

            rel = FSARelationship(
                source_id=source,
                target_id=target,
                relationship_type=RelationshipType(data.get('d5', 'integrates_with')),
                strength=float(data.get('d6', '1.0'))
            )
            self.relationships.append(rel)

    def generate_summary_report(self) -> str:
        """Generate a human-readable summary report of the ontology"""
        lines = []
        lines.append("=" * 80)
        lines.append("FSA ONTOLOGY SUMMARY REPORT")
        lines.append("=" * 80)
        lines.append("")

        # Statistics
        stats = self.export_to_json()['statistics']
        lines.append("STATISTICS:")
        lines.append(f"  Total FSAs: {stats['total_fsas']}")
        lines.append(f"  Total Relationships: {stats['total_relationships']}")
        lines.append(f"  Average LQ: {stats['avg_lq']:.2f}")
        lines.append(f"  Average RE Potential: {stats['avg_re_potential']:.2f}")
        lines.append("")

        # Tier distribution
        lines.append("TIER DISTRIBUTION:")
        tier_dist = stats['tier_distribution']
        for tier, count in sorted(tier_dist.items()):
            tier_name = FSATier(tier).name
            lines.append(f"  {tier_name}: {count} FSAs")
        lines.append("")

        # FSAs by tier
        for tier_value in [1, 2, 3, 4]:
            tier = FSATier(tier_value)
            fsas = [e for e in self.entities.values() if e.tier == tier]

            if fsas:
                lines.append(f"{tier.name} FSAs:")
                for fsa in fsas:
                    lines.append(f"  {fsa.id}: {fsa.name}")
                    lines.append(f"    LQ: {fsa.lq}, RE: {fsa.get_stars()}, Duration: {fsa.duration}")

                    deps = self.find_dependencies(fsa.id)
                    if deps:
                        lines.append(f"    Dependencies: {', '.join(d.id for d in deps)}")

                    prereqs = self.get_prerequisites(fsa.id)
                    if prereqs:
                        lines.append(f"    Prerequisites: {', '.join(p.id for p in prereqs)}")
                lines.append("")

        # Enhancement opportunities
        enhancements = self.find_enhancement_opportunities()
        if enhancements:
            lines.append("ENHANCEMENT OPPORTUNITIES:")
            for enhancer, enhanced in enhancements:
                lines.append(f"  {enhancer.id} enhances {enhanced.id}")
            lines.append("")

        lines.append("=" * 80)

        return "\n".join(lines)


def demo():
    """Demonstration of FSA-7 Ontology Builder capabilities"""
    print("FSA-7: Ontology Builder & Semantic Mapper")
    print("=" * 80)
    print()

    # Initialize ontology
    print("Initializing ontology with 10 FSAs...")
    ontology = OntologyBuilder()
    print(f"✓ Loaded {len(ontology.entities)} FSAs")
    print(f"✓ Loaded {len(ontology.relationships)} relationships")
    print()

    # Demonstrate semantic queries
    print("SEMANTIC QUERY DEMONSTRATIONS:")
    print("-" * 80)

    # 1. Find dependencies
    print("\n1. Dependencies for FSA-2 (Autonomous Workflow Composer):")
    deps = ontology.find_dependencies("FSA-2")
    for dep in deps:
        print(f"   - {dep.id}: {dep.name} (LQ: {dep.lq})")

    # 2. Find prerequisites
    print("\n2. Prerequisites for FSA-8 (Curriculum Learning Sequencer):")
    prereqs = ontology.get_prerequisites("FSA-8")
    for prereq in prereqs:
        print(f"   - {prereq.id}: {prereq.name} (Tier {prereq.tier.value})")

    # 3. Enhancement opportunities
    print("\n3. Enhancement Opportunities:")
    enhancements = ontology.find_enhancement_opportunities()
    for enhancer, enhanced in enhancements[:3]:
        print(f"   - {enhancer.id} enhances {enhanced.id}")

    # 4. Validate workflow
    print("\n4. Workflow Validation:")
    workflow = ["FSA-1", "FSA-7", "FSA-8"]
    result = ontology.validate_workflow(workflow)
    print(f"   Workflow: {' -> '.join(workflow)}")
    print(f"   Valid: {result.is_valid}")
    if result.errors:
        print(f"   Errors: {len(result.errors)}")
    if result.warnings:
        print(f"   Warnings: {len(result.warnings)}")
    if result.suggestions:
        print(f"   Suggestions: {result.suggestions[0]}")

    # 5. Calculate curriculum path
    print("\n5. Curriculum Path (FSA-1 to FSA-8):")
    path = ontology.calculate_curriculum_path("FSA-1", "FSA-8")
    print("   Recommended sequence:")
    for i, fsa in enumerate(path, 1):
        print(f"   {i}. {fsa.id}: {fsa.name} (Tier {fsa.tier.value}, LQ {fsa.lq})")

    # 6. Detect conflicts
    print("\n6. Conflict Detection:")
    test_list = ["FSA-6", "FSA-9", "FSA-10"]
    conflicts = ontology.detect_conflicts(test_list)
    if conflicts:
        for conflict in conflicts:
            print(f"   - {conflict.conflict_type}: {conflict.description}")
    else:
        print("   No conflicts detected")

    # 7. Cypher-like query
    print("\n7. Cypher-like Query (High-tier FSAs):")
    results = ontology.query_cypher_like("MATCH (a) WHERE a.tier = 1 RETURN a")
    print(f"   Found {len(results)} Tier 1 FSAs:")
    for result in results[:3]:
        entity = result['entity']
        print(f"   - {entity['id']}: {entity['name']}")

    print()
    print("-" * 80)

    # Export demonstrations
    print("\nEXPORT DEMONSTRATIONS:")
    print("-" * 80)

    # JSON export
    print("\n1. JSON Export (first 50 chars):")
    json_data = ontology.export_to_json()
    json_str = json.dumps(json_data, indent=2)
    print(f"   {json_str[:50]}...")
    print(f"   Total size: {len(json_str)} characters")

    # GraphML export
    print("\n2. GraphML Export (first 50 chars):")
    graphml_str = ontology.export_to_graphml()
    print(f"   {graphml_str[:50]}...")
    print(f"   Total size: {len(graphml_str)} characters")

    # Summary report
    print("\n3. Summary Report:")
    print(ontology.generate_summary_report())

    # MLA v3.0 LQ calculations
    print("\nMLA v3.0 LQ CALCULATIONS:")
    print("-" * 80)
    lq_simple = ontology.mla_calculator.calculate_operation_lq(
        'query_simple', len(ontology.entities), len(ontology.relationships)
    )
    print(f"Simple Query LQ: {lq_simple}")

    lq_complex = ontology.mla_calculator.calculate_operation_lq(
        'query_complex', len(ontology.entities), len(ontology.relationships), 1.2
    )
    print(f"Complex Query LQ: {lq_complex}")

    lq_export = ontology.mla_calculator.calculate_operation_lq(
        'graph_export', len(ontology.entities), len(ontology.relationships)
    )
    print(f"Graph Export LQ: {lq_export}")

    print()
    print("=" * 80)
    print("FSA-7 demonstration complete!")
    print("=" * 80)


if __name__ == "__main__":
    demo()

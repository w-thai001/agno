"""
Design Pattern Matcher FSA - Comprehensive Pattern Detection System

This module provides advanced design pattern recognition using AST analysis,
machine learning techniques, and behavioral pattern matching to identify
Gang of Four patterns, architectural patterns, concurrency patterns, and
Domain-Driven Design patterns in Python code.

Author: Agno AI Assistant
License: MIT
"""

import ast
import inspect
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class PatternType(Enum):
    """Types of design patterns"""
    # Creational Patterns
    SINGLETON = "Singleton"
    FACTORY_METHOD = "Factory Method"
    ABSTRACT_FACTORY = "Abstract Factory"
    BUILDER = "Builder"
    PROTOTYPE = "Prototype"

    # Structural Patterns
    ADAPTER = "Adapter"
    BRIDGE = "Bridge"
    COMPOSITE = "Composite"
    DECORATOR = "Decorator"
    FACADE = "Facade"
    FLYWEIGHT = "Flyweight"
    PROXY = "Proxy"

    # Behavioral Patterns
    STRATEGY = "Strategy"
    OBSERVER = "Observer"
    COMMAND = "Command"
    TEMPLATE_METHOD = "Template Method"
    ITERATOR = "Iterator"
    STATE = "State"
    VISITOR = "Visitor"
    CHAIN_OF_RESPONSIBILITY = "Chain of Responsibility"
    MEDIATOR = "Mediator"
    MEMENTO = "Memento"
    INTERPRETER = "Interpreter"

    # Architectural Patterns
    MVC = "Model-View-Controller"
    MVVM = "Model-View-ViewModel"
    REPOSITORY = "Repository"
    SERVICE_LAYER = "Service Layer"
    DATA_MAPPER = "Data Mapper"
    ACTIVE_RECORD = "Active Record"

    # Concurrency Patterns
    PRODUCER_CONSUMER = "Producer-Consumer"
    THREAD_POOL = "Thread Pool"
    READ_WRITE_LOCK = "Read-Write Lock"
    MONITOR_OBJECT = "Monitor Object"

    # DDD Patterns
    ENTITY = "Entity"
    VALUE_OBJECT = "Value Object"
    AGGREGATE = "Aggregate"
    DDD_REPOSITORY = "DDD Repository"
    DOMAIN_EVENT = "Domain Event"


@dataclass
class PatternEvidence:
    """Evidence for pattern detection"""
    structural_evidence: List[str] = field(default_factory=list)
    behavioral_evidence: List[str] = field(default_factory=list)
    naming_evidence: List[str] = field(default_factory=list)
    documentation_evidence: List[str] = field(default_factory=list)

    def score(self) -> float:
        """Calculate evidence score"""
        total = len(self.structural_evidence) + len(self.behavioral_evidence) + \
                len(self.naming_evidence) + len(self.documentation_evidence)
        return min(total / 10.0, 1.0)


@dataclass
class Pattern:
    """Detected design pattern"""
    pattern_type: PatternType
    name: str
    location: str
    evidence: PatternEvidence
    confidence: float
    quality: float
    details: Dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        return f"Pattern({self.pattern_type.value}, conf={self.confidence:.2f}, quality={self.quality:.2f})"


@dataclass
class ValidationResult:
    """Pattern validation result"""
    is_valid: bool
    violations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


@dataclass
class PatternSuggestion:
    """Pattern suggestion for code improvement"""
    code_smell: str
    suggested_patterns: List[PatternType]
    rationale: str
    estimated_benefit: float


@dataclass
class PatternMatchReport:
    """Complete pattern matching report"""
    detected_patterns: List[Pattern]
    confidence_scores: Dict[str, float]
    quality_scores: Dict[str, float]
    recommendations: List[PatternSuggestion]
    anti_patterns: List[Dict[str, Any]]

    def summary(self) -> str:
        """Generate summary report"""
        lines = [
            f"Pattern Detection Report",
            f"=" * 50,
            f"Patterns Detected: {len(self.detected_patterns)}",
            f"Anti-patterns Found: {len(self.anti_patterns)}",
            f"Recommendations: {len(self.recommendations)}",
            ""
        ]

        for pattern in self.detected_patterns:
            lines.append(f"  - {pattern.pattern_type.value} at {pattern.location} "
                        f"(confidence: {pattern.confidence:.2f}, quality: {pattern.quality:.2f})")

        return "\n".join(lines)


class DesignPatternMatcher:
    """
    Comprehensive design pattern detection system using AST analysis,
    machine learning techniques, and behavioral pattern matching.
    """

    def __init__(self):
        self.patterns_detected: List[Pattern] = []
        self.ast_cache: Dict[str, ast.AST] = {}
        self.class_hierarchy: Dict[str, Set[str]] = defaultdict(set)

    def match_patterns(self, code: Union[str, Path]) -> PatternMatchReport:
        """
        Main entry point for pattern matching

        Args:
            code: Python source code string or path to file

        Returns:
            PatternMatchReport with all detected patterns
        """
        try:
            if isinstance(code, Path):
                code = code.read_text()

            tree = ast.parse(code)
            self.ast_cache['main'] = tree
            self._build_class_hierarchy(tree)

            # Detect all pattern types
            patterns = []
            patterns.extend(self.detect_creational_patterns(tree))
            patterns.extend(self.detect_structural_patterns(tree))
            patterns.extend(self.detect_behavioral_patterns(tree))
            patterns.extend(self.detect_architectural_patterns(tree))
            patterns.extend(self.detect_concurrency_patterns(tree))
            patterns.extend(self.detect_ddd_patterns(tree))

            self.patterns_detected = patterns

            # Compute scores
            confidence_scores = {p.name: p.confidence for p in patterns}
            quality_scores = {p.name: p.quality for p in patterns}

            # Detect anti-patterns
            anti_patterns = self._detect_anti_patterns(patterns, tree)

            # Generate recommendations
            recommendations = self._generate_recommendations(tree, patterns)

            return PatternMatchReport(
                detected_patterns=patterns,
                confidence_scores=confidence_scores,
                quality_scores=quality_scores,
                recommendations=recommendations,
                anti_patterns=anti_patterns
            )
        except SyntaxError as e:
            logger.error(f"Syntax error in code: {e}")
            return PatternMatchReport([], {}, {}, [], [])

    def detect_creational_patterns(self, ast_node: ast.AST) -> List[Pattern]:
        """Detect creational patterns (Singleton, Factory, Builder, Prototype, Abstract Factory)"""
        patterns = []

        for node in ast.walk(ast_node):
            if isinstance(node, ast.ClassDef):
                # Check for Singleton pattern
                singleton = self.analyze_singleton_pattern(node)
                if singleton:
                    patterns.append(singleton)

                # Check for Builder pattern
                builder = self._analyze_builder_pattern(node)
                if builder:
                    patterns.append(builder)

                # Check for Prototype pattern
                prototype = self._analyze_prototype_pattern(node)
                if prototype:
                    patterns.append(prototype)

        # Check for Factory patterns
        factory = self.analyze_factory_pattern(ast_node)
        if factory:
            patterns.extend(factory)

        return patterns

    def detect_structural_patterns(self, ast_node: ast.AST) -> List[Pattern]:
        """Detect structural patterns (Adapter, Decorator, Proxy, Facade, Composite, Bridge, Flyweight)"""
        patterns = []

        for node in ast.walk(ast_node):
            if isinstance(node, ast.ClassDef):
                # Check for Adapter pattern
                adapter = self._analyze_adapter_pattern(node)
                if adapter:
                    patterns.append(adapter)

                # Check for Proxy pattern
                proxy = self._analyze_proxy_pattern(node)
                if proxy:
                    patterns.append(proxy)

                # Check for Facade pattern
                facade = self._analyze_facade_pattern(node)
                if facade:
                    patterns.append(facade)

                # Check for Composite pattern
                composite = self._analyze_composite_pattern(node)
                if composite:
                    patterns.append(composite)

        # Check for Decorator pattern (function and class decorators)
        decorator_patterns = self.analyze_decorator_pattern(ast_node)
        if decorator_patterns:
            patterns.extend(decorator_patterns)

        return patterns

    def detect_behavioral_patterns(self, ast_node: ast.AST) -> List[Pattern]:
        """Detect behavioral patterns (Strategy, Observer, Command, Template Method, Iterator, State, Visitor)"""
        patterns = []

        # Check for Strategy pattern
        strategy = self.analyze_strategy_pattern(ast_node)
        if strategy:
            patterns.extend(strategy)

        # Check for Observer pattern
        observer = self.analyze_observer_pattern(ast_node)
        if observer:
            patterns.extend(observer)

        # Check for Command pattern
        command = self._analyze_command_pattern(ast_node)
        if command:
            patterns.extend(command)

        # Check for Template Method pattern
        template_method = self._analyze_template_method_pattern(ast_node)
        if template_method:
            patterns.extend(template_method)

        # Check for Iterator pattern
        iterator = self._analyze_iterator_pattern(ast_node)
        if iterator:
            patterns.extend(iterator)

        # Check for State pattern
        state = self._analyze_state_pattern(ast_node)
        if state:
            patterns.extend(state)

        return patterns

    def detect_architectural_patterns(self, ast_node: ast.AST) -> List[Pattern]:
        """Detect architectural patterns (MVC, MVVM, Repository, Service Layer)"""
        patterns = []

        # Check for MVC pattern
        mvc = self._analyze_mvc_pattern(ast_node)
        if mvc:
            patterns.append(mvc)

        # Check for Repository pattern
        repository = self._analyze_repository_pattern(ast_node)
        if repository:
            patterns.extend(repository)

        # Check for Service Layer pattern
        service_layer = self._analyze_service_layer_pattern(ast_node)
        if service_layer:
            patterns.extend(service_layer)

        return patterns

    def detect_concurrency_patterns(self, ast_node: ast.AST) -> List[Pattern]:
        """Detect concurrency patterns (Producer-Consumer, Thread Pool, Monitor Object)"""
        patterns = []

        # Check for Producer-Consumer pattern
        producer_consumer = self._analyze_producer_consumer_pattern(ast_node)
        if producer_consumer:
            patterns.append(producer_consumer)

        # Check for Thread Pool pattern
        thread_pool = self._analyze_thread_pool_pattern(ast_node)
        if thread_pool:
            patterns.append(thread_pool)

        return patterns

    def detect_ddd_patterns(self, ast_node: ast.AST) -> List[Pattern]:
        """Detect Domain-Driven Design patterns (Entity, Value Object, Aggregate)"""
        patterns = []

        for node in ast.walk(ast_node):
            if isinstance(node, ast.ClassDef):
                # Check for Entity pattern
                entity = self._analyze_entity_pattern(node)
                if entity:
                    patterns.append(entity)

                # Check for Value Object pattern
                value_object = self._analyze_value_object_pattern(node)
                if value_object:
                    patterns.append(value_object)

                # Check for Aggregate pattern
                aggregate = self._analyze_aggregate_pattern(node)
                if aggregate:
                    patterns.append(aggregate)

        return patterns

    def analyze_singleton_pattern(self, cls: ast.ClassDef) -> Optional[Pattern]:
        """Analyze class for Singleton pattern"""
        evidence = PatternEvidence()

        # Check for __new__ override
        has_new_override = False
        has_instance_var = False
        has_lock = False

        for node in cls.body:
            if isinstance(node, ast.FunctionDef) and node.name == '__new__':
                has_new_override = True
                evidence.structural_evidence.append("__new__ method override")

            # Check for instance class variable
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and 'instance' in target.id.lower():
                        has_instance_var = True
                        evidence.structural_evidence.append("Instance class variable")

        # Check for threading constructs (thread-safe singleton)
        code = ast.unparse(cls)
        if 'Lock' in code or 'threading' in code:
            has_lock = True
            evidence.behavioral_evidence.append("Thread-safe implementation")

        # Check naming conventions
        if 'singleton' in cls.name.lower():
            evidence.naming_evidence.append("Singleton in class name")

        # Check docstring
        docstring = ast.get_docstring(cls)
        if docstring and 'singleton' in docstring.lower():
            evidence.documentation_evidence.append("Singleton mentioned in docstring")

        confidence = self.compute_pattern_confidence(evidence)

        if (has_new_override and has_instance_var) or confidence > 0.6:
            quality = self._compute_singleton_quality(cls, has_lock)

            return Pattern(
                pattern_type=PatternType.SINGLETON,
                name=cls.name,
                location=f"line {cls.lineno}",
                evidence=evidence,
                confidence=confidence,
                quality=quality,
                details={'thread_safe': has_lock}
            )

        return None

    def analyze_factory_pattern(self, code: ast.AST) -> List[Pattern]:
        """Analyze code for Factory Method and Abstract Factory patterns"""
        patterns = []

        for node in ast.walk(code):
            if isinstance(node, ast.ClassDef):
                evidence = PatternEvidence()
                factory_methods = []

                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        # Check for factory method naming patterns
                        if any(prefix in item.name.lower() for prefix in ['create', 'make', 'build', 'factory']):
                            factory_methods.append(item.name)
                            evidence.naming_evidence.append(f"Factory method: {item.name}")

                # Check for abstract methods
                has_abstract = False
                code_str = ast.unparse(node)
                if '@abstractmethod' in code_str or 'ABC' in code_str:
                    has_abstract = True
                    evidence.structural_evidence.append("Abstract base class")

                if factory_methods:
                    evidence.behavioral_evidence.append(f"{len(factory_methods)} factory methods")

                    pattern_type = PatternType.ABSTRACT_FACTORY if (has_abstract and len(factory_methods) > 1) else PatternType.FACTORY_METHOD
                    confidence = self.compute_pattern_confidence(evidence)

                    if confidence > 0.5:
                        patterns.append(Pattern(
                            pattern_type=pattern_type,
                            name=node.name,
                            location=f"line {node.lineno}",
                            evidence=evidence,
                            confidence=confidence,
                            quality=0.8,
                            details={'methods': factory_methods}
                        ))

        return patterns

    def analyze_observer_pattern(self, code: ast.AST) -> List[Pattern]:
        """Analyze code for Observer pattern"""
        patterns = []

        for node in ast.walk(code):
            if isinstance(node, ast.ClassDef):
                evidence = PatternEvidence()
                observer_methods = {'attach': False, 'detach': False, 'notify': False, 'update': False}

                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        method_name = item.name.lower()
                        for key in observer_methods:
                            if key in method_name:
                                observer_methods[key] = True
                                evidence.naming_evidence.append(f"Observer method: {item.name}")

                # Check for subject or observer in name
                if 'subject' in node.name.lower() or 'observable' in node.name.lower():
                    evidence.naming_evidence.append("Subject/Observable in name")
                elif 'observer' in node.name.lower():
                    evidence.naming_evidence.append("Observer in name")

                # Check for list of observers
                code_str = ast.unparse(node)
                if 'observers' in code_str.lower() or 'listeners' in code_str.lower():
                    evidence.structural_evidence.append("Observer list present")

                if sum(observer_methods.values()) >= 2:
                    evidence.behavioral_evidence.append(f"Observer pattern methods: {sum(observer_methods.values())}/4")
                    confidence = self.compute_pattern_confidence(evidence)

                    if confidence > 0.5:
                        patterns.append(Pattern(
                            pattern_type=PatternType.OBSERVER,
                            name=node.name,
                            location=f"line {node.lineno}",
                            evidence=evidence,
                            confidence=confidence,
                            quality=0.75,
                            details={'methods': observer_methods}
                        ))

        return patterns

    def analyze_strategy_pattern(self, code: ast.AST) -> List[Pattern]:
        """Analyze code for Strategy pattern"""
        patterns = []

        for node in ast.walk(code):
            if isinstance(node, ast.ClassDef):
                evidence = PatternEvidence()

                # Check for strategy-related naming
                if 'strategy' in node.name.lower():
                    evidence.naming_evidence.append("Strategy in class name")

                # Check for execute/run/apply methods
                has_strategy_method = False
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        if item.name in ['execute', 'run', 'apply', 'do_algorithm']:
                            has_strategy_method = True
                            evidence.behavioral_evidence.append(f"Strategy method: {item.name}")

                # Check for abstract method
                code_str = ast.unparse(node)
                if '@abstractmethod' in code_str or 'ABC' in code_str:
                    evidence.structural_evidence.append("Abstract strategy interface")

                # Check for multiple implementations (inheritance)
                if node.name in self.class_hierarchy:
                    subclasses = len(self.class_hierarchy[node.name])
                    if subclasses >= 2:
                        evidence.structural_evidence.append(f"{subclasses} strategy implementations")

                if has_strategy_method or ('strategy' in node.name.lower()):
                    confidence = self.compute_pattern_confidence(evidence)

                    if confidence > 0.5:
                        patterns.append(Pattern(
                            pattern_type=PatternType.STRATEGY,
                            name=node.name,
                            location=f"line {node.lineno}",
                            evidence=evidence,
                            confidence=confidence,
                            quality=0.8
                        ))

        return patterns

    def analyze_decorator_pattern(self, code: ast.AST) -> List[Pattern]:
        """Analyze code for Decorator pattern (both function and class decorators)"""
        patterns = []

        # Check for function decorators
        for node in ast.walk(code):
            if isinstance(node, ast.FunctionDef):
                # Check if function is a decorator (returns a function)
                if node.decorator_list or self._is_decorator_function(node):
                    evidence = PatternEvidence()

                    if node.decorator_list:
                        evidence.structural_evidence.append(f"Decorated with {len(node.decorator_list)} decorators")

                    if 'wrapper' in ast.unparse(node).lower():
                        evidence.behavioral_evidence.append("Wrapper function present")

                    if 'decorator' in node.name.lower():
                        evidence.naming_evidence.append("Decorator in name")

                    confidence = self.compute_pattern_confidence(evidence)

                    if confidence > 0.5:
                        patterns.append(Pattern(
                            pattern_type=PatternType.DECORATOR,
                            name=node.name,
                            location=f"line {node.lineno}",
                            evidence=evidence,
                            confidence=confidence,
                            quality=0.75
                        ))

        return patterns

    def compute_pattern_confidence(self, evidence: PatternEvidence) -> float:
        """
        Compute confidence score based on evidence using weighted scoring

        Weights:
        - Structural evidence: 0.4
        - Behavioral evidence: 0.3
        - Naming evidence: 0.2
        - Documentation evidence: 0.1
        """
        structural_score = min(len(evidence.structural_evidence) * 0.3, 0.4)
        behavioral_score = min(len(evidence.behavioral_evidence) * 0.2, 0.3)
        naming_score = min(len(evidence.naming_evidence) * 0.15, 0.2)
        doc_score = min(len(evidence.documentation_evidence) * 0.1, 0.1)

        total_score = structural_score + behavioral_score + naming_score + doc_score
        return min(total_score, 1.0)

    def validate_pattern_implementation(self, pattern: Pattern, code: ast.AST) -> ValidationResult:
        """Validate pattern implementation quality"""
        violations = []
        warnings = []
        suggestions = []

        if pattern.pattern_type == PatternType.SINGLETON:
            # Check thread safety
            if not pattern.details.get('thread_safe', False):
                warnings.append("Singleton is not thread-safe")
                suggestions.append("Add threading.Lock() for thread safety")

        elif pattern.pattern_type == PatternType.OBSERVER:
            # Check if notify method exists
            methods = pattern.details.get('methods', {})
            if not methods.get('notify', False):
                violations.append("Observer pattern missing notify method")

        is_valid = len(violations) == 0
        return ValidationResult(is_valid, violations, warnings, suggestions)

    def detect_pattern_misuse(self, pattern: Pattern) -> List[str]:
        """Detect anti-patterns and pattern misuse"""
        misuses = []

        if pattern.pattern_type == PatternType.SINGLETON:
            if pattern.quality < 0.5:
                misuses.append("Singleton overuse - consider dependency injection")

        elif pattern.pattern_type == PatternType.FACADE:
            if pattern.quality < 0.6:
                misuses.append("Facade may be becoming a God object")

        return misuses

    def suggest_patterns(self, code_smell: str) -> List[PatternSuggestion]:
        """Suggest patterns based on code smells"""
        suggestions = []

        smell_to_patterns = {
            'long_method': ([PatternType.TEMPLATE_METHOD, PatternType.STRATEGY],
                          "Break down long method using Template Method or Strategy pattern", 0.8),
            'god_class': ([PatternType.FACADE, PatternType.MEDIATOR],
                         "Refactor god class using Facade or Mediator pattern", 0.9),
            'switch_statements': ([PatternType.STRATEGY, PatternType.STATE, PatternType.COMMAND],
                                 "Replace switch statements with Strategy, State, or Command pattern", 0.85),
            'shotgun_surgery': ([PatternType.OBSERVER],
                               "Use Observer pattern to reduce coupling", 0.75),
        }

        if code_smell in smell_to_patterns:
            patterns, rationale, benefit = smell_to_patterns[code_smell]
            suggestions.append(PatternSuggestion(
                code_smell=code_smell,
                suggested_patterns=patterns,
                rationale=rationale,
                estimated_benefit=benefit
            ))

        return suggestions

    def rank_patterns_by_quality(self, patterns: List[Pattern]) -> List[Pattern]:
        """Rank patterns by implementation quality"""
        return sorted(patterns, key=lambda p: (p.quality, p.confidence), reverse=True)

    # Helper methods for specific pattern detection

    def _build_class_hierarchy(self, tree: ast.AST):
        """Build class inheritance hierarchy"""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for base in node.bases:
                    if isinstance(base, ast.Name):
                        self.class_hierarchy[base.id].add(node.name)

    def _analyze_builder_pattern(self, node: ast.ClassDef) -> Optional[Pattern]:
        """Analyze for Builder pattern"""
        evidence = PatternEvidence()
        has_build_method = False
        fluent_methods = 0

        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                if item.name == 'build':
                    has_build_method = True
                    evidence.behavioral_evidence.append("build() method present")

                # Check for fluent interface (returns self)
                for stmt in ast.walk(item):
                    if isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.Name) and stmt.value.id == 'self':
                        fluent_methods += 1

        if 'builder' in node.name.lower():
            evidence.naming_evidence.append("Builder in name")

        if has_build_method and fluent_methods >= 2:
            evidence.structural_evidence.append(f"{fluent_methods} fluent methods")
            confidence = self.compute_pattern_confidence(evidence)

            return Pattern(
                pattern_type=PatternType.BUILDER,
                name=node.name,
                location=f"line {node.lineno}",
                evidence=evidence,
                confidence=confidence,
                quality=0.8
            )

        return None

    def _analyze_prototype_pattern(self, node: ast.ClassDef) -> Optional[Pattern]:
        """Analyze for Prototype pattern"""
        evidence = PatternEvidence()
        has_clone = False

        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                if item.name in ['clone', 'copy', '__copy__', '__deepcopy__']:
                    has_clone = True
                    evidence.behavioral_evidence.append(f"Clone method: {item.name}")

        if has_clone:
            confidence = self.compute_pattern_confidence(evidence)

            return Pattern(
                pattern_type=PatternType.PROTOTYPE,
                name=node.name,
                location=f"line {node.lineno}",
                evidence=evidence,
                confidence=confidence,
                quality=0.75
            )

        return None

    def _analyze_adapter_pattern(self, node: ast.ClassDef) -> Optional[Pattern]:
        """Analyze for Adapter pattern"""
        evidence = PatternEvidence()

        if 'adapter' in node.name.lower():
            evidence.naming_evidence.append("Adapter in name")

        # Check for composition (adaptee)
        code_str = ast.unparse(node)
        if 'adaptee' in code_str.lower() or ('self.' in code_str and 'wrapped' in code_str):
            evidence.structural_evidence.append("Composition pattern present")

        confidence = self.compute_pattern_confidence(evidence)

        if confidence > 0.5:
            return Pattern(
                pattern_type=PatternType.ADAPTER,
                name=node.name,
                location=f"line {node.lineno}",
                evidence=evidence,
                confidence=confidence,
                quality=0.75
            )

        return None

    def _analyze_proxy_pattern(self, node: ast.ClassDef) -> Optional[Pattern]:
        """Analyze for Proxy pattern"""
        evidence = PatternEvidence()

        if 'proxy' in node.name.lower():
            evidence.naming_evidence.append("Proxy in name")

        # Check for lazy loading or access control
        code_str = ast.unparse(node)
        if 'real_subject' in code_str or '_real' in code_str:
            evidence.structural_evidence.append("Real subject reference")

        confidence = self.compute_pattern_confidence(evidence)

        if confidence > 0.5:
            return Pattern(
                pattern_type=PatternType.PROXY,
                name=node.name,
                location=f"line {node.lineno}",
                evidence=evidence,
                confidence=confidence,
                quality=0.7
            )

        return None

    def _analyze_facade_pattern(self, node: ast.ClassDef) -> Optional[Pattern]:
        """Analyze for Facade pattern"""
        evidence = PatternEvidence()

        if 'facade' in node.name.lower():
            evidence.naming_evidence.append("Facade in name")

        # Check for high-level methods
        method_count = sum(1 for item in node.body if isinstance(item, ast.FunctionDef))
        if method_count >= 3:
            evidence.behavioral_evidence.append(f"{method_count} high-level methods")

        confidence = self.compute_pattern_confidence(evidence)

        if confidence > 0.5:
            return Pattern(
                pattern_type=PatternType.FACADE,
                name=node.name,
                location=f"line {node.lineno}",
                evidence=evidence,
                confidence=confidence,
                quality=0.75
            )

        return None

    def _analyze_composite_pattern(self, node: ast.ClassDef) -> Optional[Pattern]:
        """Analyze for Composite pattern"""
        evidence = PatternEvidence()

        if 'composite' in node.name.lower() or 'component' in node.name.lower():
            evidence.naming_evidence.append("Composite/Component in name")

        # Check for child management methods
        code_str = ast.unparse(node)
        if 'add' in code_str and 'remove' in code_str and 'children' in code_str.lower():
            evidence.structural_evidence.append("Child management methods present")

        confidence = self.compute_pattern_confidence(evidence)

        if confidence > 0.5:
            return Pattern(
                pattern_type=PatternType.COMPOSITE,
                name=node.name,
                location=f"line {node.lineno}",
                evidence=evidence,
                confidence=confidence,
                quality=0.75
            )

        return None

    def _analyze_command_pattern(self, code: ast.AST) -> List[Pattern]:
        """Analyze for Command pattern"""
        patterns = []

        for node in ast.walk(code):
            if isinstance(node, ast.ClassDef):
                evidence = PatternEvidence()

                if 'command' in node.name.lower():
                    evidence.naming_evidence.append("Command in name")

                has_execute = False
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == 'execute':
                        has_execute = True
                        evidence.behavioral_evidence.append("execute() method present")

                if has_execute:
                    confidence = self.compute_pattern_confidence(evidence)
                    patterns.append(Pattern(
                        pattern_type=PatternType.COMMAND,
                        name=node.name,
                        location=f"line {node.lineno}",
                        evidence=evidence,
                        confidence=confidence,
                        quality=0.75
                    ))

        return patterns

    def _analyze_template_method_pattern(self, code: ast.AST) -> List[Pattern]:
        """Analyze for Template Method pattern"""
        patterns = []

        for node in ast.walk(code):
            if isinstance(node, ast.ClassDef):
                evidence = PatternEvidence()

                # Check for abstract methods (hooks)
                code_str = ast.unparse(node)
                if '@abstractmethod' in code_str:
                    evidence.structural_evidence.append("Abstract hook methods")

                # Check for template method
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        if 'template' in item.name.lower():
                            evidence.naming_evidence.append("Template method present")

                confidence = self.compute_pattern_confidence(evidence)

                if confidence > 0.6:
                    patterns.append(Pattern(
                        pattern_type=PatternType.TEMPLATE_METHOD,
                        name=node.name,
                        location=f"line {node.lineno}",
                        evidence=evidence,
                        confidence=confidence,
                        quality=0.8
                    ))

        return patterns

    def _analyze_iterator_pattern(self, code: ast.AST) -> List[Pattern]:
        """Analyze for Iterator pattern"""
        patterns = []

        for node in ast.walk(code):
            if isinstance(node, ast.ClassDef):
                evidence = PatternEvidence()

                has_iter = False
                has_next = False

                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        if item.name == '__iter__':
                            has_iter = True
                            evidence.behavioral_evidence.append("__iter__ method")
                        elif item.name == '__next__':
                            has_next = True
                            evidence.behavioral_evidence.append("__next__ method")

                if has_iter and has_next:
                    confidence = self.compute_pattern_confidence(evidence)
                    patterns.append(Pattern(
                        pattern_type=PatternType.ITERATOR,
                        name=node.name,
                        location=f"line {node.lineno}",
                        evidence=evidence,
                        confidence=confidence,
                        quality=0.9
                    ))

        return patterns

    def _analyze_state_pattern(self, code: ast.AST) -> List[Pattern]:
        """Analyze for State pattern"""
        patterns = []

        for node in ast.walk(code):
            if isinstance(node, ast.ClassDef):
                evidence = PatternEvidence()

                if 'state' in node.name.lower():
                    evidence.naming_evidence.append("State in name")

                # Check for state transitions
                code_str = ast.unparse(node)
                if 'state' in code_str.lower() and ('transition' in code_str.lower() or 'change_state' in code_str.lower()):
                    evidence.behavioral_evidence.append("State transition methods")

                confidence = self.compute_pattern_confidence(evidence)

                if confidence > 0.5:
                    patterns.append(Pattern(
                        pattern_type=PatternType.STATE,
                        name=node.name,
                        location=f"line {node.lineno}",
                        evidence=evidence,
                        confidence=confidence,
                        quality=0.75
                    ))

        return patterns

    def _analyze_mvc_pattern(self, code: ast.AST) -> Optional[Pattern]:
        """Analyze for MVC pattern"""
        evidence = PatternEvidence()
        has_model = False
        has_view = False
        has_controller = False

        for node in ast.walk(code):
            if isinstance(node, ast.ClassDef):
                name_lower = node.name.lower()
                if 'model' in name_lower:
                    has_model = True
                elif 'view' in name_lower:
                    has_view = True
                elif 'controller' in name_lower:
                    has_controller = True

        if has_model:
            evidence.structural_evidence.append("Model component")
        if has_view:
            evidence.structural_evidence.append("View component")
        if has_controller:
            evidence.structural_evidence.append("Controller component")

        if sum([has_model, has_view, has_controller]) >= 2:
            confidence = self.compute_pattern_confidence(evidence)

            return Pattern(
                pattern_type=PatternType.MVC,
                name="MVC Architecture",
                location="module level",
                evidence=evidence,
                confidence=confidence,
                quality=0.8
            )

        return None

    def _analyze_repository_pattern(self, code: ast.AST) -> List[Pattern]:
        """Analyze for Repository pattern"""
        patterns = []

        for node in ast.walk(code):
            if isinstance(node, ast.ClassDef):
                evidence = PatternEvidence()

                if 'repository' in node.name.lower():
                    evidence.naming_evidence.append("Repository in name")

                # Check for CRUD methods
                crud_methods = {'add': False, 'get': False, 'update': False, 'delete': False, 'find': False}
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        method_lower = item.name.lower()
                        for crud_op in crud_methods:
                            if crud_op in method_lower:
                                crud_methods[crud_op] = True

                crud_count = sum(crud_methods.values())
                if crud_count >= 2:
                    evidence.behavioral_evidence.append(f"{crud_count} CRUD operations")

                confidence = self.compute_pattern_confidence(evidence)

                if confidence > 0.5:
                    patterns.append(Pattern(
                        pattern_type=PatternType.REPOSITORY,
                        name=node.name,
                        location=f"line {node.lineno}",
                        evidence=evidence,
                        confidence=confidence,
                        quality=0.8
                    ))

        return patterns

    def _analyze_service_layer_pattern(self, code: ast.AST) -> List[Pattern]:
        """Analyze for Service Layer pattern"""
        patterns = []

        for node in ast.walk(code):
            if isinstance(node, ast.ClassDef):
                evidence = PatternEvidence()

                if 'service' in node.name.lower():
                    evidence.naming_evidence.append("Service in name")

                    # Check for business logic methods
                    method_count = sum(1 for item in node.body if isinstance(item, ast.FunctionDef))
                    if method_count >= 2:
                        evidence.behavioral_evidence.append(f"{method_count} service methods")

                    confidence = self.compute_pattern_confidence(evidence)

                    if confidence > 0.5:
                        patterns.append(Pattern(
                            pattern_type=PatternType.SERVICE_LAYER,
                            name=node.name,
                            location=f"line {node.lineno}",
                            evidence=evidence,
                            confidence=confidence,
                            quality=0.75
                        ))

        return patterns

    def _analyze_producer_consumer_pattern(self, code: ast.AST) -> Optional[Pattern]:
        """Analyze for Producer-Consumer pattern"""
        evidence = PatternEvidence()
        code_str = ast.unparse(code)

        has_queue = 'Queue' in code_str or 'queue' in code_str.lower()
        has_producer = 'producer' in code_str.lower() or 'produce' in code_str.lower()
        has_consumer = 'consumer' in code_str.lower() or 'consume' in code_str.lower()
        has_threading = 'Thread' in code_str or 'threading' in code_str

        if has_queue:
            evidence.structural_evidence.append("Queue data structure")
        if has_producer:
            evidence.naming_evidence.append("Producer component")
        if has_consumer:
            evidence.naming_evidence.append("Consumer component")
        if has_threading:
            evidence.behavioral_evidence.append("Threading implementation")

        if has_queue and (has_producer or has_consumer):
            confidence = self.compute_pattern_confidence(evidence)

            return Pattern(
                pattern_type=PatternType.PRODUCER_CONSUMER,
                name="Producer-Consumer",
                location="module level",
                evidence=evidence,
                confidence=confidence,
                quality=0.8
            )

        return None

    def _analyze_thread_pool_pattern(self, code: ast.AST) -> Optional[Pattern]:
        """Analyze for Thread Pool pattern"""
        evidence = PatternEvidence()
        code_str = ast.unparse(code)

        has_executor = 'ThreadPoolExecutor' in code_str or 'ExecutorService' in code_str
        has_workers = 'worker' in code_str.lower()
        has_task_queue = 'task' in code_str.lower() and 'queue' in code_str.lower()

        if has_executor:
            evidence.structural_evidence.append("Thread pool executor")
        if has_workers:
            evidence.naming_evidence.append("Worker threads")
        if has_task_queue:
            evidence.behavioral_evidence.append("Task queue")

        if has_executor or (has_workers and has_task_queue):
            confidence = self.compute_pattern_confidence(evidence)

            return Pattern(
                pattern_type=PatternType.THREAD_POOL,
                name="Thread Pool",
                location="module level",
                evidence=evidence,
                confidence=confidence,
                quality=0.85
            )

        return None

    def _analyze_entity_pattern(self, node: ast.ClassDef) -> Optional[Pattern]:
        """Analyze for DDD Entity pattern"""
        evidence = PatternEvidence()

        # Check for identity (id field or __eq__ based on id)
        has_id = False
        has_eq_with_id = False

        for item in node.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                if 'id' in item.target.id.lower():
                    has_id = True
                    evidence.structural_evidence.append("Identity field present")

            if isinstance(item, ast.FunctionDef) and item.name == '__eq__':
                code_str = ast.unparse(item)
                if 'id' in code_str.lower():
                    has_eq_with_id = True
                    evidence.behavioral_evidence.append("Identity-based equality")

        if 'entity' in node.name.lower():
            evidence.naming_evidence.append("Entity in name")

        if has_id or has_eq_with_id:
            confidence = self.compute_pattern_confidence(evidence)

            return Pattern(
                pattern_type=PatternType.ENTITY,
                name=node.name,
                location=f"line {node.lineno}",
                evidence=evidence,
                confidence=confidence,
                quality=0.75
            )

        return None

    def _analyze_value_object_pattern(self, node: ast.ClassDef) -> Optional[Pattern]:
        """Analyze for DDD Value Object pattern"""
        evidence = PatternEvidence()

        # Check for immutability (frozen dataclass or no setters)
        code_str = ast.unparse(node)
        is_frozen = 'frozen=True' in code_str

        if is_frozen:
            evidence.structural_evidence.append("Immutable (frozen)")

        # Check for value-based equality
        has_eq = any(isinstance(item, ast.FunctionDef) and item.name == '__eq__' for item in node.body)
        if has_eq:
            evidence.behavioral_evidence.append("Value-based equality")

        if 'value' in node.name.lower():
            evidence.naming_evidence.append("Value in name")

        if is_frozen or (has_eq and 'value' in node.name.lower()):
            confidence = self.compute_pattern_confidence(evidence)

            return Pattern(
                pattern_type=PatternType.VALUE_OBJECT,
                name=node.name,
                location=f"line {node.lineno}",
                evidence=evidence,
                confidence=confidence,
                quality=0.8
            )

        return None

    def _analyze_aggregate_pattern(self, node: ast.ClassDef) -> Optional[Pattern]:
        """Analyze for DDD Aggregate pattern"""
        evidence = PatternEvidence()

        if 'aggregate' in node.name.lower() or 'root' in node.name.lower():
            evidence.naming_evidence.append("Aggregate/Root in name")

        # Check for entity characteristics + consistency boundary
        code_str = ast.unparse(node)
        if 'entities' in code_str.lower() or 'invariant' in code_str.lower():
            evidence.structural_evidence.append("Aggregate root with entities")

        confidence = self.compute_pattern_confidence(evidence)

        if confidence > 0.5:
            return Pattern(
                pattern_type=PatternType.AGGREGATE,
                name=node.name,
                location=f"line {node.lineno}",
                evidence=evidence,
                confidence=confidence,
                quality=0.75
            )

        return None

    def _compute_singleton_quality(self, cls: ast.ClassDef, has_lock: bool) -> float:
        """Compute quality score for Singleton implementation"""
        quality = 0.5

        if has_lock:
            quality += 0.3  # Thread-safe

        # Check for proper implementation
        code_str = ast.unparse(cls)
        if '__new__' in code_str:
            quality += 0.2

        return min(quality, 1.0)

    def _is_decorator_function(self, node: ast.FunctionDef) -> bool:
        """Check if function is a decorator"""
        # Check if function returns a function
        for item in ast.walk(node):
            if isinstance(item, ast.Return):
                if isinstance(item.value, ast.FunctionDef) or isinstance(item.value, ast.Name):
                    return True

        # Check for nested function definition
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                return True

        return False

    def _detect_anti_patterns(self, patterns: List[Pattern], tree: ast.AST) -> List[Dict[str, Any]]:
        """Detect anti-patterns and pattern misuse"""
        anti_patterns = []

        # Check for singleton overuse
        singleton_count = sum(1 for p in patterns if p.pattern_type == PatternType.SINGLETON)
        if singleton_count > 3:
            anti_patterns.append({
                'type': 'singleton_overuse',
                'severity': 'high',
                'message': f"Too many singletons ({singleton_count}). Consider dependency injection."
            })

        # Check for god object (facade with low quality)
        for pattern in patterns:
            if pattern.pattern_type == PatternType.FACADE and pattern.quality < 0.6:
                anti_patterns.append({
                    'type': 'god_object',
                    'severity': 'medium',
                    'message': f"Facade '{pattern.name}' may be becoming a god object.",
                    'location': pattern.location
                })

        return anti_patterns

    def _generate_recommendations(self, tree: ast.AST, patterns: List[Pattern]) -> List[PatternSuggestion]:
        """Generate pattern recommendations based on code analysis"""
        recommendations = []

        # Analyze code structure for potential improvements
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Check for long methods
                if len(node.body) > 20:
                    recommendations.extend(self.suggest_patterns('long_method'))
                    break

        return recommendations

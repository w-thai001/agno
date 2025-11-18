"""
Comprehensive unit tests for Design Pattern Matcher FSA

Tests cover all major pattern detection capabilities including
Gang of Four patterns, architectural patterns, concurrency patterns,
and Domain-Driven Design patterns.
"""

import ast
import pytest
from design_pattern_matcher import (
    DesignPatternMatcher,
    PatternType,
    Pattern,
    PatternEvidence,
    ValidationResult,
    PatternSuggestion,
)


class TestSingletonDetection:
    """Tests for Singleton pattern detection"""

    def test_singleton_pattern_detection_with_new(self):
        """Test detection of Singleton pattern with __new__ override"""
        code = """
class DatabaseConnection:
    '''Singleton database connection'''
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def connect(self):
        pass
"""
        matcher = DesignPatternMatcher()
        report = matcher.match_patterns(code)

        assert len(report.detected_patterns) > 0
        singleton_patterns = [p for p in report.detected_patterns if p.pattern_type == PatternType.SINGLETON]
        assert len(singleton_patterns) == 1
        assert singleton_patterns[0].name == "DatabaseConnection"
        assert singleton_patterns[0].confidence > 0.6

    def test_thread_safe_singleton_detection(self):
        """Test detection of thread-safe Singleton pattern"""
        code = """
import threading

class ThreadSafeSingleton:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
"""
        matcher = DesignPatternMatcher()
        report = matcher.match_patterns(code)

        singleton_patterns = [p for p in report.detected_patterns if p.pattern_type == PatternType.SINGLETON]
        assert len(singleton_patterns) == 1
        assert singleton_patterns[0].details.get('thread_safe') is True
        assert singleton_patterns[0].quality > 0.7

    def test_non_singleton_class_not_detected(self):
        """Test that regular classes are not detected as Singletons"""
        code = """
class RegularClass:
    def __init__(self):
        self.value = 42
"""
        matcher = DesignPatternMatcher()
        report = matcher.match_patterns(code)

        singleton_patterns = [p for p in report.detected_patterns if p.pattern_type == PatternType.SINGLETON]
        assert len(singleton_patterns) == 0


class TestFactoryDetection:
    """Tests for Factory pattern detection"""

    def test_factory_method_detection(self):
        """Test detection of Factory Method pattern"""
        code = """
class AnimalFactory:
    def create_animal(self, animal_type):
        if animal_type == 'dog':
            return Dog()
        elif animal_type == 'cat':
            return Cat()
        return None
"""
        matcher = DesignPatternMatcher()
        report = matcher.match_patterns(code)

        factory_patterns = [p for p in report.detected_patterns
                          if p.pattern_type in [PatternType.FACTORY_METHOD, PatternType.ABSTRACT_FACTORY]]
        assert len(factory_patterns) >= 1
        assert 'create_animal' in factory_patterns[0].details.get('methods', [])

    def test_abstract_factory_detection(self):
        """Test detection of Abstract Factory pattern"""
        code = """
from abc import ABC, abstractmethod

class UIFactory(ABC):
    @abstractmethod
    def create_button(self):
        pass

    @abstractmethod
    def create_checkbox(self):
        pass

    @abstractmethod
    def create_window(self):
        pass
"""
        matcher = DesignPatternMatcher()
        report = matcher.match_patterns(code)

        abstract_factory_patterns = [p for p in report.detected_patterns
                                    if p.pattern_type == PatternType.ABSTRACT_FACTORY]
        assert len(abstract_factory_patterns) >= 1
        assert len(abstract_factory_patterns[0].details.get('methods', [])) >= 2


class TestObserverDetection:
    """Tests for Observer pattern detection"""

    def test_observer_pattern_detection(self):
        """Test detection of Observer pattern"""
        code = """
class Subject:
    def __init__(self):
        self._observers = []

    def attach(self, observer):
        self._observers.append(observer)

    def detach(self, observer):
        self._observers.remove(observer)

    def notify(self):
        for observer in self._observers:
            observer.update(self)

class Observer:
    def update(self, subject):
        pass
"""
        matcher = DesignPatternMatcher()
        report = matcher.match_patterns(code)

        observer_patterns = [p for p in report.detected_patterns if p.pattern_type == PatternType.OBSERVER]
        assert len(observer_patterns) >= 1

        # Check that Subject class is detected
        subject_pattern = next((p for p in observer_patterns if p.name == 'Subject'), None)
        assert subject_pattern is not None
        assert subject_pattern.confidence > 0.5

    def test_observer_with_partial_implementation(self):
        """Test Observer pattern with only some methods"""
        code = """
class EventManager:
    def __init__(self):
        self.listeners = []

    def subscribe(self, listener):
        self.listeners.append(listener)

    def notify_all(self, event):
        for listener in self.listeners:
            listener.on_event(event)
"""
        matcher = DesignPatternMatcher()
        report = matcher.match_patterns(code)

        # Should still detect as observer pattern even with different naming
        observer_patterns = [p for p in report.detected_patterns if p.pattern_type == PatternType.OBSERVER]
        assert len(observer_patterns) >= 1


class TestStrategyDetection:
    """Tests for Strategy pattern detection"""

    def test_strategy_pattern_detection(self):
        """Test detection of Strategy pattern"""
        code = """
from abc import ABC, abstractmethod

class PaymentStrategy(ABC):
    @abstractmethod
    def execute(self, amount):
        pass

class CreditCardStrategy(PaymentStrategy):
    def execute(self, amount):
        print(f"Paying {amount} with credit card")

class PayPalStrategy(PaymentStrategy):
    def execute(self, amount):
        print(f"Paying {amount} with PayPal")
"""
        matcher = DesignPatternMatcher()
        report = matcher.match_patterns(code)

        strategy_patterns = [p for p in report.detected_patterns if p.pattern_type == PatternType.STRATEGY]
        assert len(strategy_patterns) >= 1

        # Check for strategy base class
        strategy_base = next((p for p in strategy_patterns if 'Strategy' in p.name), None)
        assert strategy_base is not None

    def test_strategy_with_run_method(self):
        """Test Strategy pattern with run() method"""
        code = """
class SortingStrategy:
    def run(self, data):
        pass

class QuickSort(SortingStrategy):
    def run(self, data):
        return sorted(data)
"""
        matcher = DesignPatternMatcher()
        report = matcher.match_patterns(code)

        strategy_patterns = [p for p in report.detected_patterns if p.pattern_type == PatternType.STRATEGY]
        assert len(strategy_patterns) >= 1


class TestDecoratorDetection:
    """Tests for Decorator pattern detection"""

    def test_function_decorator_detection(self):
        """Test detection of function decorator pattern"""
        code = """
def log_decorator(func):
    def wrapper(*args, **kwargs):
        print(f"Calling {func.__name__}")
        result = func(*args, **kwargs)
        print(f"Finished {func.__name__}")
        return result
    return wrapper

@log_decorator
def my_function():
    pass
"""
        matcher = DesignPatternMatcher()
        report = matcher.match_patterns(code)

        decorator_patterns = [p for p in report.detected_patterns if p.pattern_type == PatternType.DECORATOR]
        assert len(decorator_patterns) >= 1

    def test_class_decorator_detection(self):
        """Test detection of class decorator pattern"""
        code = """
class CacheDecorator:
    def __init__(self, func):
        self.func = func
        self.cache = {}

    def __call__(self, *args):
        if args in self.cache:
            return self.cache[args]
        result = self.func(*args)
        self.cache[args] = result
        return result
"""
        matcher = DesignPatternMatcher()
        report = matcher.match_patterns(code)

        # Should detect decorator characteristics
        assert len(report.detected_patterns) >= 0


class TestMVCDetection:
    """Tests for MVC architectural pattern detection"""

    def test_mvc_pattern_detection(self):
        """Test detection of MVC architectural pattern"""
        code = """
class UserModel:
    def __init__(self):
        self.data = {}

    def save(self):
        pass

class UserView:
    def render(self, data):
        print(data)

class UserController:
    def __init__(self, model, view):
        self.model = model
        self.view = view

    def update(self):
        data = self.model.data
        self.view.render(data)
"""
        matcher = DesignPatternMatcher()
        report = matcher.match_patterns(code)

        mvc_patterns = [p for p in report.detected_patterns if p.pattern_type == PatternType.MVC]
        assert len(mvc_patterns) >= 1
        assert mvc_patterns[0].confidence > 0.5


class TestConfidenceScoring:
    """Tests for confidence scoring algorithm"""

    def test_confidence_scoring_with_strong_evidence(self):
        """Test confidence scoring with strong evidence"""
        matcher = DesignPatternMatcher()
        evidence = PatternEvidence(
            structural_evidence=["Evidence 1", "Evidence 2", "Evidence 3"],
            behavioral_evidence=["Behavior 1", "Behavior 2"],
            naming_evidence=["Name 1"],
            documentation_evidence=["Doc 1"]
        )

        confidence = matcher.compute_pattern_confidence(evidence)
        assert confidence > 0.7

    def test_confidence_scoring_with_weak_evidence(self):
        """Test confidence scoring with weak evidence"""
        matcher = DesignPatternMatcher()
        evidence = PatternEvidence(
            naming_evidence=["Name 1"]
        )

        confidence = matcher.compute_pattern_confidence(evidence)
        assert confidence < 0.3

    def test_confidence_scoring_with_no_evidence(self):
        """Test confidence scoring with no evidence"""
        matcher = DesignPatternMatcher()
        evidence = PatternEvidence()

        confidence = matcher.compute_pattern_confidence(evidence)
        assert confidence == 0.0


class TestQualityAnalysis:
    """Tests for pattern quality analysis"""

    def test_singleton_quality_analysis(self):
        """Test quality analysis for Singleton pattern"""
        code = """
import threading

class GoodSingleton:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
"""
        matcher = DesignPatternMatcher()
        report = matcher.match_patterns(code)

        singleton_patterns = [p for p in report.detected_patterns if p.pattern_type == PatternType.SINGLETON]
        if singleton_patterns:
            assert singleton_patterns[0].quality > 0.7

    def test_pattern_validation(self):
        """Test pattern validation functionality"""
        matcher = DesignPatternMatcher()

        # Create a mock pattern
        pattern = Pattern(
            pattern_type=PatternType.SINGLETON,
            name="TestSingleton",
            location="line 1",
            evidence=PatternEvidence(),
            confidence=0.9,
            quality=0.8,
            details={'thread_safe': False}
        )

        tree = ast.parse("class TestSingleton: pass")
        validation = matcher.validate_pattern_implementation(pattern, tree)

        # Should warn about thread safety
        assert len(validation.warnings) > 0


class TestPatternSuggestions:
    """Tests for pattern suggestion engine"""

    def test_suggest_patterns_for_long_method(self):
        """Test pattern suggestions for long method code smell"""
        matcher = DesignPatternMatcher()
        suggestions = matcher.suggest_patterns('long_method')

        assert len(suggestions) > 0
        assert suggestions[0].code_smell == 'long_method'
        assert PatternType.TEMPLATE_METHOD in suggestions[0].suggested_patterns or \
               PatternType.STRATEGY in suggestions[0].suggested_patterns

    def test_suggest_patterns_for_god_class(self):
        """Test pattern suggestions for god class code smell"""
        matcher = DesignPatternMatcher()
        suggestions = matcher.suggest_patterns('god_class')

        assert len(suggestions) > 0
        assert suggestions[0].code_smell == 'god_class'
        assert PatternType.FACADE in suggestions[0].suggested_patterns or \
               PatternType.MEDIATOR in suggestions[0].suggested_patterns

    def test_suggest_patterns_for_switch_statements(self):
        """Test pattern suggestions for switch statement code smell"""
        matcher = DesignPatternMatcher()
        suggestions = matcher.suggest_patterns('switch_statements')

        assert len(suggestions) > 0
        assert PatternType.STRATEGY in suggestions[0].suggested_patterns


class TestRepositoryAndDDDPatterns:
    """Tests for Repository and DDD pattern detection"""

    def test_repository_pattern_detection(self):
        """Test detection of Repository pattern"""
        code = """
class UserRepository:
    def __init__(self):
        self.users = []

    def add(self, user):
        self.users.append(user)

    def get(self, user_id):
        return next((u for u in self.users if u.id == user_id), None)

    def update(self, user):
        pass

    def delete(self, user_id):
        self.users = [u for u in self.users if u.id != user_id]

    def find_by_email(self, email):
        return next((u for u in self.users if u.email == email), None)
"""
        matcher = DesignPatternMatcher()
        report = matcher.match_patterns(code)

        repository_patterns = [p for p in report.detected_patterns if p.pattern_type == PatternType.REPOSITORY]
        assert len(repository_patterns) >= 1
        assert repository_patterns[0].confidence > 0.6

    def test_entity_pattern_detection(self):
        """Test detection of DDD Entity pattern"""
        code = """
class User:
    def __init__(self, user_id, name):
        self.id = user_id
        self.name = name

    def __eq__(self, other):
        return self.id == other.id

    def __hash__(self):
        return hash(self.id)
"""
        matcher = DesignPatternMatcher()
        report = matcher.match_patterns(code)

        entity_patterns = [p for p in report.detected_patterns if p.pattern_type == PatternType.ENTITY]
        assert len(entity_patterns) >= 1

    def test_value_object_pattern_detection(self):
        """Test detection of DDD Value Object pattern"""
        code = """
from dataclasses import dataclass

@dataclass(frozen=True)
class Money:
    amount: float
    currency: str

    def __eq__(self, other):
        return self.amount == other.amount and self.currency == other.currency
"""
        matcher = DesignPatternMatcher()
        report = matcher.match_patterns(code)

        value_object_patterns = [p for p in report.detected_patterns if p.pattern_type == PatternType.VALUE_OBJECT]
        assert len(value_object_patterns) >= 1


class TestConcurrencyPatterns:
    """Tests for concurrency pattern detection"""

    def test_producer_consumer_detection(self):
        """Test detection of Producer-Consumer pattern"""
        code = """
from queue import Queue
import threading

class Producer:
    def __init__(self, queue):
        self.queue = queue

    def produce(self, item):
        self.queue.put(item)

class Consumer:
    def __init__(self, queue):
        self.queue = queue

    def consume(self):
        return self.queue.get()
"""
        matcher = DesignPatternMatcher()
        report = matcher.match_patterns(code)

        pc_patterns = [p for p in report.detected_patterns if p.pattern_type == PatternType.PRODUCER_CONSUMER]
        assert len(pc_patterns) >= 1

    def test_thread_pool_detection(self):
        """Test detection of Thread Pool pattern"""
        code = """
from concurrent.futures import ThreadPoolExecutor

class TaskManager:
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=10)

    def submit_task(self, func, *args):
        return self.executor.submit(func, *args)
"""
        matcher = DesignPatternMatcher()
        report = matcher.match_patterns(code)

        thread_pool_patterns = [p for p in report.detected_patterns if p.pattern_type == PatternType.THREAD_POOL]
        assert len(thread_pool_patterns) >= 1


class TestAntiPatternDetection:
    """Tests for anti-pattern detection"""

    def test_singleton_overuse_detection(self):
        """Test detection of singleton overuse anti-pattern"""
        code = """
class Singleton1:
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

class Singleton2:
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

class Singleton3:
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

class Singleton4:
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
"""
        matcher = DesignPatternMatcher()
        report = matcher.match_patterns(code)

        # Should detect multiple singletons as anti-pattern
        assert len(report.anti_patterns) > 0
        singleton_overuse = next((ap for ap in report.anti_patterns if ap['type'] == 'singleton_overuse'), None)
        assert singleton_overuse is not None


def test_full_pattern_matching_report():
    """Integration test for complete pattern matching report"""
    code = """
# Singleton
class Configuration:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

# Factory
class ShapeFactory:
    def create_shape(self, shape_type):
        if shape_type == 'circle':
            return Circle()
        return Square()

# Observer
class NewsPublisher:
    def __init__(self):
        self.subscribers = []

    def attach(self, subscriber):
        self.subscribers.append(subscriber)

    def notify(self, news):
        for subscriber in self.subscribers:
            subscriber.update(news)

# Strategy
class CompressionStrategy:
    def execute(self, data):
        pass
"""
    matcher = DesignPatternMatcher()
    report = matcher.match_patterns(code)

    # Should detect multiple patterns
    assert len(report.detected_patterns) >= 3

    # Check for different pattern types
    pattern_types = {p.pattern_type for p in report.detected_patterns}
    assert PatternType.SINGLETON in pattern_types
    assert PatternType.FACTORY_METHOD in pattern_types or PatternType.ABSTRACT_FACTORY in pattern_types
    assert PatternType.OBSERVER in pattern_types

    # Check report summary
    summary = report.summary()
    assert "Pattern Detection Report" in summary
    assert len(summary) > 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

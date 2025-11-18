"""
Example usage of Design Pattern Matcher FSA

This script demonstrates how to use the Design Pattern Matcher to detect
various design patterns in Python code, including Gang of Four patterns,
architectural patterns, and Domain-Driven Design patterns.
"""

from design_pattern_matcher import DesignPatternMatcher, PatternType


# Sample code with multiple design patterns
SAMPLE_CODE = """
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass
from queue import Queue

# ============== SINGLETON PATTERN ==============
class DatabaseConnection:
    '''Thread-safe Singleton database connection'''
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def connect(self):
        print("Connecting to database...")


# ============== FACTORY PATTERN ==============
class AnimalFactory:
    '''Factory for creating different animal objects'''

    def create_animal(self, animal_type):
        if animal_type == 'dog':
            return Dog()
        elif animal_type == 'cat':
            return Cat()
        return None

    def make_pet(self, pet_type):
        return self.create_animal(pet_type)


# ============== ABSTRACT FACTORY PATTERN ==============
class UIFactory(ABC):
    '''Abstract factory for creating UI components'''

    @abstractmethod
    def create_button(self):
        pass

    @abstractmethod
    def create_window(self):
        pass

    @abstractmethod
    def create_menu(self):
        pass


# ============== OBSERVER PATTERN ==============
class NewsPublisher:
    '''Subject in Observer pattern - publishes news to subscribers'''

    def __init__(self):
        self._observers = []
        self.latest_news = None

    def attach(self, observer):
        '''Subscribe to news updates'''
        if observer not in self._observers:
            self._observers.append(observer)

    def detach(self, observer):
        '''Unsubscribe from news updates'''
        self._observers.remove(observer)

    def notify(self):
        '''Notify all observers of news update'''
        for observer in self._observers:
            observer.update(self)


class NewsSubscriber:
    '''Observer in Observer pattern'''

    def update(self, subject):
        print(f"Received news update: {subject.latest_news}")


# ============== STRATEGY PATTERN ==============
class PaymentStrategy(ABC):
    '''Abstract strategy for payment processing'''

    @abstractmethod
    def execute(self, amount):
        pass


class CreditCardStrategy(PaymentStrategy):
    '''Concrete strategy for credit card payment'''

    def execute(self, amount):
        print(f"Processing ${amount} via credit card")


class PayPalStrategy(PaymentStrategy):
    '''Concrete strategy for PayPal payment'''

    def execute(self, amount):
        print(f"Processing ${amount} via PayPal")


class CryptoStrategy(PaymentStrategy):
    '''Concrete strategy for cryptocurrency payment'''

    def execute(self, amount):
        print(f"Processing ${amount} via cryptocurrency")


# ============== DECORATOR PATTERN ==============
def timer_decorator(func):
    '''Function decorator that times execution'''
    import time

    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        print(f"{func.__name__} took {end - start:.4f} seconds")
        return result
    return wrapper


def log_decorator(func):
    '''Function decorator that logs function calls'''

    def wrapper(*args, **kwargs):
        print(f"Calling {func.__name__} with args={args}, kwargs={kwargs}")
        result = func(*args, **kwargs)
        print(f"{func.__name__} returned {result}")
        return result
    return wrapper


# ============== BUILDER PATTERN ==============
class QueryBuilder:
    '''Builder pattern for constructing SQL queries'''

    def __init__(self):
        self.query_parts = {}

    def select(self, *fields):
        self.query_parts['select'] = fields
        return self

    def from_table(self, table):
        self.query_parts['from'] = table
        return self

    def where(self, condition):
        self.query_parts['where'] = condition
        return self

    def order_by(self, field):
        self.query_parts['order_by'] = field
        return self

    def build(self):
        '''Build the final query'''
        query = f"SELECT {', '.join(self.query_parts['select'])} "
        query += f"FROM {self.query_parts['from']} "
        if 'where' in self.query_parts:
            query += f"WHERE {self.query_parts['where']} "
        if 'order_by' in self.query_parts:
            query += f"ORDER BY {self.query_parts['order_by']}"
        return query


# ============== MVC PATTERN ==============
class UserModel:
    '''Model component in MVC pattern'''

    def __init__(self):
        self.users = {}

    def add_user(self, user_id, name):
        self.users[user_id] = name

    def get_user(self, user_id):
        return self.users.get(user_id)


class UserView:
    '''View component in MVC pattern'''

    def render_user(self, user_data):
        print(f"Rendering user: {user_data}")

    def render_user_list(self, users):
        print("User List:")
        for user_id, name in users.items():
            print(f"  {user_id}: {name}")


class UserController:
    '''Controller component in MVC pattern'''

    def __init__(self, model, view):
        self.model = model
        self.view = view

    def add_user(self, user_id, name):
        self.model.add_user(user_id, name)

    def show_user(self, user_id):
        user = self.model.get_user(user_id)
        self.view.render_user(user)


# ============== REPOSITORY PATTERN ==============
class UserRepository:
    '''Repository pattern for user data access'''

    def __init__(self):
        self._users = {}

    def add(self, user):
        self._users[user.id] = user

    def get(self, user_id):
        return self._users.get(user_id)

    def update(self, user):
        if user.id in self._users:
            self._users[user.id] = user

    def delete(self, user_id):
        if user_id in self._users:
            del self._users[user_id]

    def find_by_email(self, email):
        return next((u for u in self._users.values() if u.email == email), None)


# ============== DDD ENTITY PATTERN ==============
class Order:
    '''DDD Entity with identity-based equality'''

    def __init__(self, order_id):
        self.id = order_id
        self.items = []
        self.total = 0.0

    def __eq__(self, other):
        return self.id == other.id

    def __hash__(self):
        return hash(self.id)


# ============== DDD VALUE OBJECT PATTERN ==============
@dataclass(frozen=True)
class Money:
    '''DDD Value Object - immutable with value-based equality'''
    amount: float
    currency: str

    def __eq__(self, other):
        return self.amount == other.amount and self.currency == other.currency


# ============== PRODUCER-CONSUMER PATTERN ==============
class Producer:
    '''Producer in Producer-Consumer pattern'''

    def __init__(self, queue):
        self.queue = queue

    def produce(self, item):
        print(f"Producing: {item}")
        self.queue.put(item)


class Consumer:
    '''Consumer in Producer-Consumer pattern'''

    def __init__(self, queue):
        self.queue = queue

    def consume(self):
        item = self.queue.get()
        print(f"Consuming: {item}")
        return item
"""


def main():
    """Main function to demonstrate Design Pattern Matcher"""

    print("=" * 80)
    print("Design Pattern Matcher FSA - Example Usage")
    print("=" * 80)
    print()

    # Create pattern matcher
    matcher = DesignPatternMatcher()

    # Analyze the sample code
    print("Analyzing sample code for design patterns...")
    print()

    report = matcher.match_patterns(SAMPLE_CODE)

    # Display summary
    print(report.summary())
    print()

    # Display detailed pattern information
    print("=" * 80)
    print("Detailed Pattern Analysis")
    print("=" * 80)
    print()

    # Group patterns by type
    patterns_by_type = {}
    for pattern in report.detected_patterns:
        pattern_type = pattern.pattern_type.value
        if pattern_type not in patterns_by_type:
            patterns_by_type[pattern_type] = []
        patterns_by_type[pattern_type].append(pattern)

    # Display patterns grouped by category
    for pattern_type in sorted(patterns_by_type.keys()):
        patterns = patterns_by_type[pattern_type]
        print(f"\n{pattern_type}:")
        print("-" * 60)
        for pattern in patterns:
            print(f"  Class/Function: {pattern.name}")
            print(f"  Location: {pattern.location}")
            print(f"  Confidence: {pattern.confidence:.2%}")
            print(f"  Quality: {pattern.quality:.2%}")

            # Display evidence
            if pattern.evidence.structural_evidence:
                print(f"  Structural Evidence:")
                for evidence in pattern.evidence.structural_evidence:
                    print(f"    • {evidence}")

            if pattern.evidence.behavioral_evidence:
                print(f"  Behavioral Evidence:")
                for evidence in pattern.evidence.behavioral_evidence:
                    print(f"    • {evidence}")

            if pattern.evidence.naming_evidence:
                print(f"  Naming Evidence:")
                for evidence in pattern.evidence.naming_evidence:
                    print(f"    • {evidence}")

            print()

    # Display anti-patterns if found
    if report.anti_patterns:
        print("=" * 80)
        print("Anti-Patterns Detected")
        print("=" * 80)
        print()

        for anti_pattern in report.anti_patterns:
            print(f"Type: {anti_pattern['type']}")
            print(f"Severity: {anti_pattern['severity']}")
            print(f"Message: {anti_pattern['message']}")
            if 'location' in anti_pattern:
                print(f"Location: {anti_pattern['location']}")
            print()

    # Display recommendations
    if report.recommendations:
        print("=" * 80)
        print("Pattern Recommendations")
        print("=" * 80)
        print()

        for rec in report.recommendations:
            print(f"Code Smell: {rec.code_smell}")
            print(f"Suggested Patterns: {', '.join([p.value for p in rec.suggested_patterns])}")
            print(f"Rationale: {rec.rationale}")
            print(f"Estimated Benefit: {rec.estimated_benefit:.2%}")
            print()

    # Display statistics
    print("=" * 80)
    print("Pattern Statistics")
    print("=" * 80)
    print()

    pattern_categories = {
        'Creational': [PatternType.SINGLETON, PatternType.FACTORY_METHOD, PatternType.ABSTRACT_FACTORY,
                      PatternType.BUILDER, PatternType.PROTOTYPE],
        'Structural': [PatternType.ADAPTER, PatternType.BRIDGE, PatternType.COMPOSITE, PatternType.DECORATOR,
                      PatternType.FACADE, PatternType.FLYWEIGHT, PatternType.PROXY],
        'Behavioral': [PatternType.STRATEGY, PatternType.OBSERVER, PatternType.COMMAND, PatternType.TEMPLATE_METHOD,
                      PatternType.ITERATOR, PatternType.STATE, PatternType.VISITOR, PatternType.CHAIN_OF_RESPONSIBILITY,
                      PatternType.MEDIATOR, PatternType.MEMENTO, PatternType.INTERPRETER],
        'Architectural': [PatternType.MVC, PatternType.MVVM, PatternType.REPOSITORY, PatternType.SERVICE_LAYER,
                         PatternType.DATA_MAPPER, PatternType.ACTIVE_RECORD],
        'Concurrency': [PatternType.PRODUCER_CONSUMER, PatternType.THREAD_POOL, PatternType.READ_WRITE_LOCK,
                       PatternType.MONITOR_OBJECT],
        'DDD': [PatternType.ENTITY, PatternType.VALUE_OBJECT, PatternType.AGGREGATE, PatternType.DDD_REPOSITORY,
               PatternType.DOMAIN_EVENT],
    }

    for category, pattern_types in pattern_categories.items():
        count = sum(1 for p in report.detected_patterns if p.pattern_type in pattern_types)
        if count > 0:
            print(f"{category} Patterns: {count}")

    print(f"\nTotal Patterns Detected: {len(report.detected_patterns)}")

    # Rank patterns by quality
    print("\n" + "=" * 80)
    print("Top 5 Highest Quality Pattern Implementations")
    print("=" * 80)
    print()

    ranked_patterns = matcher.rank_patterns_by_quality(report.detected_patterns)
    for i, pattern in enumerate(ranked_patterns[:5], 1):
        print(f"{i}. {pattern.pattern_type.value} ({pattern.name})")
        print(f"   Quality: {pattern.quality:.2%}, Confidence: {pattern.confidence:.2%}")
        print()

    print("=" * 80)
    print("Analysis Complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()

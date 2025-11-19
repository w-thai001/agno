"""
Minimal example of the Design Pattern Matcher FSA.

This script demonstrates how to use the DesignPatternMatcher to detect
common design patterns like Singleton, Factory, Observer, Builder, and Strategy.
"""

import sys
from pathlib import Path

# Add parent directory to path to import agno
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "libs" / "agno"))

from agno.fsa import DesignPatternMatcher, print_pattern_report


def example_singleton_pattern():
    """Example 1: Detect Singleton pattern."""
    print("\n🚀 EXAMPLE 1: Singleton Pattern Detection\n")

    matcher = DesignPatternMatcher()

    code = {
        "path": "singleton.py",
        "content": '''
class DatabaseConnection:
    """Singleton database connection."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def connect(self):
        pass


class Logger:
    """Another singleton example."""

    __instance = None

    @staticmethod
    def get_instance():
        if Logger.__instance is None:
            Logger.__instance = Logger()
        return Logger.__instance

    def log(self, message):
        print(message)
''',
    }

    report = matcher.match([code])
    print_pattern_report(report)


def example_factory_pattern():
    """Example 2: Detect Factory pattern."""
    print("\n🚀 EXAMPLE 2: Factory Pattern Detection\n")

    matcher = DesignPatternMatcher()

    code = {
        "path": "factory.py",
        "content": '''
class ShapeFactory:
    """Factory for creating shapes."""

    @staticmethod
    def create_shape(shape_type):
        if shape_type == "circle":
            return Circle()
        elif shape_type == "square":
            return Square()
        return None

    @staticmethod
    def make_shape(config):
        return Shape(config)


class VehicleFactory:
    """Factory for creating vehicles."""

    def create_car(self):
        return Car()

    def create_truck(self):
        return Truck()

    def build_vehicle(self, vehicle_type):
        if vehicle_type == "car":
            return self.create_car()
        return self.create_truck()
''',
    }

    report = matcher.match([code])
    print_pattern_report(report)


def example_observer_pattern():
    """Example 3: Detect Observer pattern."""
    print("\n🚀 EXAMPLE 3: Observer Pattern Detection\n")

    matcher = DesignPatternMatcher()

    code = {
        "path": "observer.py",
        "content": '''
class Subject:
    """Observable subject."""

    def __init__(self):
        self._observers = []

    def subscribe(self, observer):
        self._observers.append(observer)

    def unsubscribe(self, observer):
        self._observers.remove(observer)

    def notify(self, data):
        for observer in self._observers:
            observer.update(data)


class EventEmitter:
    """Event emitter with observer pattern."""

    def __init__(self):
        self.listeners = {}

    def register_listener(self, event, callback):
        if event not in self.listeners:
            self.listeners[event] = []
        self.listeners[event].append(callback)

    def notify_listeners(self, event, data):
        for callback in self.listeners.get(event, []):
            callback(data)
''',
    }

    report = matcher.match([code])
    print_pattern_report(report)


def example_builder_pattern():
    """Example 4: Detect Builder pattern."""
    print("\n🚀 EXAMPLE 4: Builder Pattern Detection\n")

    matcher = DesignPatternMatcher()

    code = {
        "path": "builder.py",
        "content": '''
class QueryBuilder:
    """SQL query builder with method chaining."""

    def __init__(self):
        self.query = ""

    def select(self, fields):
        self.query += f"SELECT {fields} "
        return self

    def from_table(self, table):
        self.query += f"FROM {table} "
        return self

    def where(self, condition):
        self.query += f"WHERE {condition} "
        return self

    def build(self):
        return self.query


class RequestBuilder:
    """HTTP request builder."""

    def __init__(self):
        self.url = ""
        self.headers = {}
        self.body = None

    def set_url(self, url):
        self.url = url
        return self

    def add_header(self, key, value):
        self.headers[key] = value
        return self

    def set_body(self, body):
        self.body = body
        return self

    def create(self):
        return Request(self.url, self.headers, self.body)
''',
    }

    report = matcher.match([code])
    print_pattern_report(report)


def example_strategy_pattern():
    """Example 5: Detect Strategy pattern."""
    print("\n🚀 EXAMPLE 5: Strategy Pattern Detection\n")

    matcher = DesignPatternMatcher()

    code = {
        "path": "strategy.py",
        "content": '''
from abc import ABC, abstractmethod


class PaymentStrategy(ABC):
    """Abstract payment strategy."""

    @abstractmethod
    def execute(self, amount):
        pass


class CreditCardPayment(PaymentStrategy):
    """Credit card payment strategy."""

    def execute(self, amount):
        print(f"Paying {amount} with credit card")


class PayPalPayment(PaymentStrategy):
    """PayPal payment strategy."""

    def execute(self, amount):
        print(f"Paying {amount} with PayPal")


class SortStrategy(ABC):
    """Abstract sorting strategy."""

    @abstractmethod
    def run(self, data):
        pass
''',
    }

    report = matcher.match([code])
    print_pattern_report(report)


def example_multiple_patterns():
    """Example 6: Detect multiple patterns in one file."""
    print("\n🚀 EXAMPLE 6: Multiple Patterns Detection\n")

    matcher = DesignPatternMatcher()

    code = {
        "path": "mixed_patterns.py",
        "content": '''
# Singleton
class Config:
    _instance = None

    @staticmethod
    def get_instance():
        if Config._instance is None:
            Config._instance = Config()
        return Config._instance


# Factory + Observer
class NotificationFactory:
    """Factory that also uses observer pattern."""

    def __init__(self):
        self.observers = []

    def create_notification(self, notification_type):
        if notification_type == "email":
            return EmailNotification()
        return SMSNotification()

    def subscribe(self, observer):
        self.observers.append(observer)

    def notify(self, message):
        for observer in self.observers:
            observer.update(message)


# Builder
class ConfigBuilder:
    def __init__(self):
        self.config = {}

    def set_option(self, key, value):
        self.config[key] = value
        return self

    def add_plugin(self, plugin):
        self.config.setdefault("plugins", []).append(plugin)
        return self

    def build(self):
        return self.config
''',
    }

    report = matcher.match([code])
    print_pattern_report(report)


def example_fsa_states():
    """Example 7: Observe FSA state transitions."""
    print("\n🚀 EXAMPLE 7: FSA State Transitions\n")

    import logging
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    matcher = DesignPatternMatcher()

    print("Initial State:", matcher.current_state)
    print("\nRunning pattern matching FSA...\n")

    code = {
        "path": "test.py",
        "content": "class Simple: pass\n",
    }

    report = matcher.match([code])

    print("\nFinal State:", matcher.current_state)
    print("State History:", " -> ".join(str(s) for s in matcher.state_history))
    print(f"\nResult: {report.total_patterns} patterns detected")


def main():
    """Run all examples."""
    print("\n" + "=" * 80)
    print("DESIGN PATTERN MATCHER FSA - MINIMAL EXAMPLES")
    print("=" * 80)

    examples = [
        example_singleton_pattern,
        example_factory_pattern,
        example_observer_pattern,
        example_builder_pattern,
        example_strategy_pattern,
        example_multiple_patterns,
        example_fsa_states,
    ]

    for example_func in examples:
        try:
            example_func()
        except Exception as e:
            print(f"\n❌ Error in {example_func.__name__}: {e}\n")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 80)
    print("All examples completed!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()

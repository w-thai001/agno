"""Unit tests for ObserverPatternFSA."""

import pytest
import time
from unittest.mock import Mock

from agno.fsas.observer_pattern_fsa import (
    ObserverPatternFSA,
    Observer,
    ObserverConfig,
    ObserverStatus,
    NotificationMode,
    Event,
    Subject,
    ScheduledNotification,
    ObserverOp,
    ObserverResult,
    ValidationResult,
    AttachResult,
    DetachResult,
    NotifyResult,
    AsyncNotifyResult,
    FilterResult,
    PriorityList,
    WeakObserver,
    CleanupResult,
    EventHistory,
    ClearHistoryResult,
    ScheduleResult,
    CancelResult,
    BatchNotifyResult,
    EventFilter,
    ApplyFilterResult,
    RemoveFilterResult,
    DestroyResult,
)


# ==================== Mock Observers ====================

class MockObserver(Observer):
    """Mock observer for testing."""

    def __init__(self):
        super().__init__()
        self.events_received = []

    def update(self, event: Event):
        """Receive event notification."""
        self.events_received.append(event)


class HighPriorityObserver(Observer):
    """High priority observer."""

    def __init__(self):
        super().__init__()
        self.priority = 10
        self.events_received = []

    def update(self, event: Event):
        """Receive event notification."""
        self.events_received.append(event)


class ErrorObserver(Observer):
    """Observer that raises exceptions."""

    def __init__(self):
        super().__init__()

    def update(self, event: Event):
        """Raise exception on update."""
        raise RuntimeError("Observer error")


# ==================== Fixtures ====================

@pytest.fixture
def observer_pattern():
    """Create observer pattern instance."""
    config = ObserverConfig()
    return ObserverPatternFSA(config)


@pytest.fixture
def configured_pattern():
    """Create pre-configured observer pattern."""
    config = ObserverConfig(
        enable_weak_refs=True,
        enable_async=True,
        enable_history=True,
        thread_safe=True,
    )
    pattern = ObserverPatternFSA(config)

    # Create a subject
    pattern.create_subject("test_subject")

    return pattern


# ==================== Test Classes ====================

class TestObserverPatternBasics:
    """Test basic observer pattern functionality."""

    def test_initialization(self):
        """Test observer pattern initialization."""
        config = ObserverConfig()
        pattern = ObserverPatternFSA(config)
        assert pattern.config == config
        assert pattern.fsa_id is not None

    def test_initialization_with_custom_config(self):
        """Test initialization with custom configuration."""
        config = ObserverConfig(
            enable_async=False,
            enable_history=False,
        )
        pattern = ObserverPatternFSA(config)
        assert pattern.config.enable_async is False
        assert pattern.config.enable_history is False

    def test_validation_success(self, observer_pattern):
        """Test successful configuration validation."""
        config = ObserverConfig(max_observers=500)
        result = observer_pattern.validate(config)
        assert result.valid is True

    def test_validation_failure(self, observer_pattern):
        """Test configuration validation failure."""
        config = ObserverConfig(max_observers=0)
        result = observer_pattern.validate(config)
        assert result.valid is False
        assert len(result.errors) > 0


class TestSubjectCreation:
    """Test subject creation."""

    def test_create_subject(self, observer_pattern):
        """Test creating a subject."""
        subject = observer_pattern.create_subject("my_subject")
        assert subject is not None
        assert subject.subject_id == "my_subject"

    def test_create_duplicate_subject(self, observer_pattern):
        """Test creating duplicate subject."""
        subject1 = observer_pattern.create_subject("dup_subject")
        subject2 = observer_pattern.create_subject("dup_subject")

        # Should return existing subject
        assert subject1 is subject2


class TestObserverAttachment:
    """Test observer attachment."""

    def test_attach_observer(self, configured_pattern):
        """Test attaching an observer."""
        observer = MockObserver()
        result = configured_pattern.attach_observer("test_subject", observer)
        assert result.attached is True

    def test_attach_observer_with_priority(self, configured_pattern):
        """Test attaching observer with priority."""
        observer = MockObserver()
        result = configured_pattern.attach_observer("test_subject", observer, priority=5)
        assert result.attached is True
        assert observer.priority == 5

    def test_attach_to_nonexistent_subject(self, observer_pattern):
        """Test attaching to non-existent subject."""
        observer = MockObserver()
        result = observer_pattern.attach_observer("nonexistent", observer)
        assert result.attached is False

    def test_attach_max_observers(self):
        """Test maximum observers limit."""
        config = ObserverConfig(max_observers=2)
        pattern = ObserverPatternFSA(config)
        pattern.create_subject("limited")

        observer1 = MockObserver()
        observer2 = MockObserver()
        observer3 = MockObserver()

        pattern.attach_observer("limited", observer1)
        pattern.attach_observer("limited", observer2)
        result = pattern.attach_observer("limited", observer3)

        assert result.attached is False


class TestObserverDetachment:
    """Test observer detachment."""

    def test_detach_observer(self, configured_pattern):
        """Test detaching an observer."""
        observer = MockObserver()
        configured_pattern.attach_observer("test_subject", observer)

        result = configured_pattern.detach_observer("test_subject", observer)
        assert result.detached is True

    def test_detach_nonexistent_observer(self, configured_pattern):
        """Test detaching non-existent observer."""
        observer = MockObserver()
        result = configured_pattern.detach_observer("test_subject", observer)
        assert result.detached is False


class TestObserverNotification:
    """Test observer notification."""

    def test_notify_observers(self, configured_pattern):
        """Test notifying observers."""
        observer = MockObserver()
        configured_pattern.attach_observer("test_subject", observer)

        event = Event(event_type="test_event", data={"value": 123})
        result = configured_pattern.notify_observers("test_subject", event)

        assert result.notified is True
        assert result.observers_notified == 1
        assert len(observer.events_received) == 1

    def test_notify_multiple_observers(self, configured_pattern):
        """Test notifying multiple observers."""
        observer1 = MockObserver()
        observer2 = MockObserver()

        configured_pattern.attach_observer("test_subject", observer1)
        configured_pattern.attach_observer("test_subject", observer2)

        event = Event(event_type="test_event")
        result = configured_pattern.notify_observers("test_subject", event)

        assert result.observers_notified == 2
        assert len(observer1.events_received) == 1
        assert len(observer2.events_received) == 1

    def test_notify_with_observer_error(self, configured_pattern):
        """Test notification with observer that raises exception."""
        good_observer = MockObserver()
        error_observer = ErrorObserver()

        configured_pattern.attach_observer("test_subject", good_observer)
        configured_pattern.attach_observer("test_subject", error_observer)

        event = Event(event_type="test_event")
        result = configured_pattern.notify_observers("test_subject", event)

        # Good observer should still be notified
        assert len(good_observer.events_received) == 1
        assert len(result.errors) > 0


class TestAsyncNotification:
    """Test async observer notification."""

    def test_notify_async(self, configured_pattern):
        """Test async notification."""
        observer = MockObserver()
        configured_pattern.attach_observer("test_subject", observer)

        event = Event(event_type="async_event")
        result = configured_pattern.notify_async("test_subject", event)

        assert result.notified is True

        # Wait a bit for async processing
        time.sleep(0.1)
        assert len(observer.events_received) == 1

    def test_notify_async_disabled(self):
        """Test async notification when disabled."""
        config = ObserverConfig(enable_async=False)
        pattern = ObserverPatternFSA(config)
        pattern.create_subject("subject")

        event = Event(event_type="test")
        result = pattern.notify_async("subject", event)

        assert result.notified is False


class TestObserverFiltering:
    """Test observer filtering."""

    def test_filter_observers(self, configured_pattern):
        """Test filtering observers."""
        observer1 = MockObserver()
        observer2 = MockObserver()

        observer1.priority = 1
        observer2.priority = 2

        configured_pattern.attach_observer("test_subject", observer1)
        configured_pattern.attach_observer("test_subject", observer2)

        event = Event(event_type="test")

        # Filter: only notify high priority observers
        def filter_fn(observer):
            return observer.priority > 1

        result = configured_pattern.filter_observers("test_subject", event, filter_fn)

        assert result.filtered is True
        assert result.observers_notified == 1
        assert len(observer2.events_received) == 1
        assert len(observer1.events_received) == 0


class TestObserverQueries:
    """Test observer queries."""

    def test_get_observers(self, configured_pattern):
        """Test getting observers."""
        observer1 = MockObserver()
        observer2 = MockObserver()

        configured_pattern.attach_observer("test_subject", observer1)
        configured_pattern.attach_observer("test_subject", observer2)

        observers = configured_pattern.get_observers("test_subject")
        assert len(observers) == 2

    def test_get_observers_empty(self, configured_pattern):
        """Test getting observers from empty subject."""
        observers = configured_pattern.get_observers("test_subject")
        assert len(observers) == 0


class TestObserverPrioritization:
    """Test observer prioritization."""

    def test_prioritize_observers(self, observer_pattern):
        """Test prioritizing observers."""
        observer1 = MockObserver()
        observer2 = HighPriorityObserver()

        observer1.priority = 1
        observer2.priority = 10

        result = observer_pattern.prioritize_observers([observer1, observer2])

        assert result.observers[0] is observer2
        assert result.observers[1] is observer1

    def test_priority_in_notification_order(self, configured_pattern):
        """Test notification order respects priority."""
        events_order = []

        class TrackingObserver(Observer):
            def __init__(self, name, priority):
                super().__init__()
                self.name = name
                self.priority = priority

            def update(self, event: Event):
                events_order.append(self.name)

        observer_low = TrackingObserver("low", 1)
        observer_high = TrackingObserver("high", 10)

        configured_pattern.attach_observer("test_subject", observer_low)
        configured_pattern.attach_observer("test_subject", observer_high)

        event = Event(event_type="test")
        configured_pattern.notify_observers("test_subject", event)

        assert events_order[0] == "high"
        assert events_order[1] == "low"


class TestWeakObservers:
    """Test weak observer references."""

    def test_create_weak_observer(self, observer_pattern):
        """Test creating weak observer."""
        observer = MockObserver()
        weak_observer = observer_pattern.create_weak_observer(observer)

        assert weak_observer.observer_id == observer.observer_id

    def test_weak_observer_disabled(self):
        """Test weak observers when disabled."""
        config = ObserverConfig(enable_weak_refs=False)
        pattern = ObserverPatternFSA(config)

        observer = MockObserver()
        weak_observer = pattern.create_weak_observer(observer)

        assert weak_observer.weak_ref is None


class TestDeadObserverCleanup:
    """Test dead observer cleanup."""

    def test_remove_dead_observers(self, configured_pattern):
        """Test removing dead observers."""
        result = configured_pattern.remove_dead_observers("test_subject")
        assert result.cleaned is True

    def test_cleanup_nonexistent_subject(self, observer_pattern):
        """Test cleanup on non-existent subject."""
        result = observer_pattern.remove_dead_observers("nonexistent")
        assert result.cleaned is False


class TestEventHistory:
    """Test event history."""

    def test_get_event_history(self, configured_pattern):
        """Test getting event history."""
        event1 = Event(event_type="event1")
        event2 = Event(event_type="event2")

        configured_pattern.notify_observers("test_subject", event1)
        configured_pattern.notify_observers("test_subject", event2)

        history = configured_pattern.get_event_history("test_subject")

        assert len(history.events) == 2
        assert history.total_events == 2

    def test_get_event_history_with_limit(self, configured_pattern):
        """Test getting event history with limit."""
        for i in range(5):
            event = Event(event_type=f"event{i}")
            configured_pattern.notify_observers("test_subject", event)

        history = configured_pattern.get_event_history("test_subject", limit=3)

        assert len(history.events) == 3


class TestEventHistoryClearing:
    """Test event history clearing."""

    def test_clear_event_history(self, configured_pattern):
        """Test clearing event history."""
        event = Event(event_type="test")
        configured_pattern.notify_observers("test_subject", event)

        result = configured_pattern.clear_event_history("test_subject")

        assert result.cleared is True
        assert result.cleared_count == 1

    def test_clear_empty_history(self, configured_pattern):
        """Test clearing empty history."""
        result = configured_pattern.clear_event_history("test_subject")

        assert result.cleared is True
        assert result.cleared_count == 0


class TestEventCreation:
    """Test event creation."""

    def test_create_event(self, observer_pattern):
        """Test creating an event."""
        event = observer_pattern.create_event("my_event", {"key": "value"})

        assert event.event_type == "my_event"
        assert event.data["key"] == "value"

    def test_create_event_no_data(self, observer_pattern):
        """Test creating event without data."""
        event = observer_pattern.create_event("simple_event")

        assert event.event_type == "simple_event"
        assert len(event.data) == 0


class TestScheduledNotification:
    """Test scheduled notification."""

    def test_schedule_notification(self, configured_pattern):
        """Test scheduling a notification."""
        event = Event(event_type="scheduled_event")

        result = configured_pattern.schedule_notification("test_subject", event, delay=0.1)

        assert result.scheduled is True
        assert result.notification_id != ""

    def test_schedule_notification_execution(self, configured_pattern):
        """Test that scheduled notification executes."""
        observer = MockObserver()
        configured_pattern.attach_observer("test_subject", observer)

        event = Event(event_type="scheduled_event")
        configured_pattern.schedule_notification("test_subject", event, delay=0.1)

        # Wait for scheduled execution
        time.sleep(0.2)

        assert len(observer.events_received) == 1


class TestNotificationCancellation:
    """Test notification cancellation."""

    def test_cancel_scheduled_notification(self, configured_pattern):
        """Test cancelling a scheduled notification."""
        event = Event(event_type="test")
        schedule_result = configured_pattern.schedule_notification("test_subject", event, delay=1.0)

        cancel_result = configured_pattern.cancel_scheduled_notification(schedule_result.notification_id)

        assert cancel_result.cancelled is True

    def test_cancel_nonexistent_notification(self, observer_pattern):
        """Test cancelling non-existent notification."""
        result = observer_pattern.cancel_scheduled_notification("nonexistent")

        assert result.cancelled is False


class TestBatchNotification:
    """Test batch notification."""

    def test_batch_notify(self, configured_pattern):
        """Test batch notification."""
        observer = MockObserver()
        configured_pattern.attach_observer("test_subject", observer)

        events = [
            Event(event_type="event1"),
            Event(event_type="event2"),
            Event(event_type="event3"),
        ]

        result = configured_pattern.batch_notify("test_subject", events)

        assert result.notified is True
        assert result.events_sent == 3
        assert len(observer.events_received) == 3


class TestEventFilterCreation:
    """Test event filter creation."""

    def test_create_event_filter(self, observer_pattern):
        """Test creating an event filter."""
        def filter_fn(event):
            return event.event_type == "important"

        event_filter = observer_pattern.create_event_filter(filter_fn, "Important events only")

        assert event_filter.filter_fn is not None
        assert event_filter.description == "Important events only"


class TestFilterApplication:
    """Test filter application."""

    def test_apply_filter(self, configured_pattern):
        """Test applying a filter."""
        def filter_fn(event):
            return event.event_type == "important"

        event_filter = configured_pattern.create_event_filter(filter_fn)
        result = configured_pattern.apply_filter("test_subject", event_filter)

        assert result.applied is True

    def test_apply_filter_disabled(self):
        """Test applying filter when disabled."""
        config = ObserverConfig(enable_filters=False)
        pattern = ObserverPatternFSA(config)
        pattern.create_subject("subject")

        def filter_fn(event):
            return True

        event_filter = pattern.create_event_filter(filter_fn)
        result = pattern.apply_filter("subject", event_filter)

        assert result.applied is False


class TestFilterRemoval:
    """Test filter removal."""

    def test_remove_filter(self, configured_pattern):
        """Test removing a filter."""
        def filter_fn(event):
            return True

        event_filter = configured_pattern.create_event_filter(filter_fn)
        configured_pattern.apply_filter("test_subject", event_filter)

        result = configured_pattern.remove_filter("test_subject", event_filter.filter_id)

        assert result.removed is True

    def test_remove_nonexistent_filter(self, configured_pattern):
        """Test removing non-existent filter."""
        result = configured_pattern.remove_filter("test_subject", "nonexistent")

        assert result.removed is False


class TestObserverCounting:
    """Test observer counting."""

    def test_get_observer_count(self, configured_pattern):
        """Test getting observer count."""
        observer1 = MockObserver()
        observer2 = MockObserver()

        configured_pattern.attach_observer("test_subject", observer1)
        configured_pattern.attach_observer("test_subject", observer2)

        count = configured_pattern.get_observer_count("test_subject")

        assert count == 2

    def test_get_observer_count_empty(self, configured_pattern):
        """Test getting count for empty subject."""
        count = configured_pattern.get_observer_count("test_subject")

        assert count == 0


class TestSubjectDestruction:
    """Test subject destruction."""

    def test_destroy_subject(self, configured_pattern):
        """Test destroying a subject."""
        observer = MockObserver()
        configured_pattern.attach_observer("test_subject", observer)

        result = configured_pattern.destroy_subject("test_subject")

        assert result.destroyed is True
        assert result.observers_detached == 1

    def test_destroy_nonexistent_subject(self, observer_pattern):
        """Test destroying non-existent subject."""
        result = observer_pattern.destroy_subject("nonexistent")

        assert result.destroyed is False


class TestExecuteMethod:
    """Test execute method."""

    def test_execute_operations(self, observer_pattern):
        """Test executing observer pattern operations."""
        ops = [
            ObserverOp(
                operation="create_subject",
                subject_id="new_subject",
            ),
        ]

        result = observer_pattern.execute(ops)
        assert isinstance(result, ObserverResult)

    def test_execute_attach_operation(self, configured_pattern):
        """Test executing attach operation."""
        observer = MockObserver()

        ops = [
            ObserverOp(
                operation="attach",
                subject_id="test_subject",
                observer=observer,
            ),
        ]

        result = configured_pattern.execute(ops)
        assert result.success is True


class TestEdgeCases:
    """Test edge cases and error scenarios."""

    def test_notify_no_observers(self, configured_pattern):
        """Test notification with no observers."""
        event = Event(event_type="test")
        result = configured_pattern.notify_observers("test_subject", event)

        assert result.notified is True
        assert result.observers_notified == 0

    def test_inactive_observer_not_notified(self, configured_pattern):
        """Test that inactive observers are not notified."""
        observer = MockObserver()
        observer.status = ObserverStatus.INACTIVE

        configured_pattern.attach_observer("test_subject", observer)

        event = Event(event_type="test")
        configured_pattern.notify_observers("test_subject", event)

        assert len(observer.events_received) == 0


class TestThreadSafety:
    """Test thread safety."""

    def test_thread_safe_pattern(self):
        """Test thread-safe pattern creation."""
        config = ObserverConfig(thread_safe=True)
        pattern = ObserverPatternFSA(config)

        assert pattern._lock is not None

    def test_non_thread_safe_pattern(self):
        """Test non-thread-safe pattern."""
        config = ObserverConfig(thread_safe=False)
        pattern = ObserverPatternFSA(config)

        assert pattern._lock is None

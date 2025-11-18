"""
Observer Pattern FSA - Event-driven observer pattern implementation.

This module provides a comprehensive observer pattern with support for
subject-observer relationships, event subscription, notification broadcasting,
weak references, async observers, event filtering, and prioritization.
"""

import asyncio
import threading
import weakref
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Deque, Dict, List, Optional, Set
from uuid import uuid4

try:
    from agno.utils.log import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


# ==================== Enums and Constants ====================

class ObserverStatus(Enum):
    """Observer status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DEAD = "dead"


class NotificationMode(Enum):
    """Notification delivery mode."""
    SYNC = "sync"
    ASYNC = "async"
    SCHEDULED = "scheduled"


# ==================== Base Classes ====================

class Observer(ABC):
    """Base observer class."""

    def __init__(self):
        self.observer_id = str(uuid4())
        self.priority = 0
        self.status = ObserverStatus.ACTIVE

    @abstractmethod
    def update(self, event: 'Event'):
        """Receive notification of event."""
        pass


# ==================== Data Classes ====================

@dataclass
class Event:
    """Event object."""
    event_id: str = field(default_factory=lambda: str(uuid4()))
    event_type: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    source_subject: Optional[str] = None


@dataclass
class Subject:
    """Subject that observers subscribe to."""
    subject_id: str = field(default_factory=lambda: str(uuid4()))
    observers: List[Observer] = field(default_factory=list)
    weak_observers: List[weakref.ref] = field(default_factory=list)
    event_history: Deque[Event] = field(default_factory=lambda: deque(maxlen=100))
    filters: Dict[str, Callable] = field(default_factory=dict)


@dataclass
class ScheduledNotification:
    """Scheduled notification."""
    notification_id: str = field(default_factory=lambda: str(uuid4()))
    subject_id: str = ""
    event: Optional[Event] = None
    delay: float = 0.0
    scheduled_at: datetime = field(default_factory=datetime.now)
    timer: Optional[threading.Timer] = None


@dataclass
class ObserverOp:
    """Observer pattern operation."""
    operation: str
    subject_id: Optional[str] = None
    observer: Optional[Observer] = None
    event: Optional[Event] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ObserverResult:
    """Observer pattern pipeline result."""
    success: bool
    operations_count: int = 0
    notifications_sent: int = 0
    errors: List[str] = field(default_factory=list)
    execution_time: float = 0.0


@dataclass
class ValidationResult:
    """Configuration validation result."""
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class AttachResult:
    """Observer attachment result."""
    attached: bool
    observer_id: str = ""
    error: Optional[str] = None


@dataclass
class DetachResult:
    """Observer detachment result."""
    detached: bool
    observer_id: str = ""
    error: Optional[str] = None


@dataclass
class NotifyResult:
    """Notification result."""
    notified: bool
    observers_notified: int = 0
    errors: List[str] = field(default_factory=list)


@dataclass
class AsyncNotifyResult:
    """Async notification result."""
    notified: bool
    observers_notified: int = 0
    errors: List[str] = field(default_factory=list)


@dataclass
class FilterResult:
    """Observer filtering result."""
    filtered: bool
    observers_notified: int = 0
    errors: List[str] = field(default_factory=list)


@dataclass
class PriorityList:
    """Prioritized observer list."""
    observers: List[Observer] = field(default_factory=list)


@dataclass
class WeakObserver:
    """Weak reference observer wrapper."""
    weak_ref: Optional[weakref.ref] = None
    observer_id: str = ""


@dataclass
class CleanupResult:
    """Dead observer cleanup result."""
    cleaned: bool
    removed_count: int = 0


@dataclass
class EventHistory:
    """Event history."""
    subject_id: str
    events: List[Event] = field(default_factory=list)
    total_events: int = 0


@dataclass
class ClearHistoryResult:
    """Event history clearing result."""
    cleared: bool
    cleared_count: int = 0


@dataclass
class ScheduleResult:
    """Notification scheduling result."""
    scheduled: bool
    notification_id: str = ""
    error: Optional[str] = None


@dataclass
class CancelResult:
    """Scheduled notification cancellation result."""
    cancelled: bool
    notification_id: str = ""
    error: Optional[str] = None


@dataclass
class BatchNotifyResult:
    """Batch notification result."""
    notified: bool
    events_sent: int = 0
    observers_notified: int = 0
    errors: List[str] = field(default_factory=list)


@dataclass
class EventFilter:
    """Event filter."""
    filter_id: str = field(default_factory=lambda: str(uuid4()))
    filter_fn: Optional[Callable] = None
    description: str = ""


@dataclass
class ApplyFilterResult:
    """Filter application result."""
    applied: bool
    filter_id: str = ""
    error: Optional[str] = None


@dataclass
class RemoveFilterResult:
    """Filter removal result."""
    removed: bool
    filter_id: str = ""
    error: Optional[str] = None


@dataclass
class DestroyResult:
    """Subject destruction result."""
    destroyed: bool
    subject_id: str = ""
    observers_detached: int = 0
    error: Optional[str] = None


@dataclass
class ObserverConfig:
    """Observer pattern configuration."""
    enable_weak_refs: bool = True
    enable_async: bool = True
    enable_history: bool = True
    history_max_size: int = 100
    enable_priorities: bool = True
    enable_filters: bool = True
    thread_safe: bool = True
    max_observers: int = 1000
    notification_timeout: float = 30.0


# ==================== Main FSA Class ====================

class ObserverPatternFSA:
    """
    Observer Pattern Finite State Automaton.

    Provides event-driven observer pattern with support for subscriptions,
    notifications, filtering, prioritization, and async delivery.
    """

    def __init__(self, config: Optional[ObserverConfig] = None):
        """
        Initialize the observer pattern.

        Args:
            config: Observer configuration
        """
        self.config = config or ObserverConfig()
        self.fsa_id = str(uuid4())

        # Thread safety
        self._lock = threading.RLock() if self.config.thread_safe else None

        # Subject registry
        self.subjects: Dict[str, Subject] = {}

        # Scheduled notifications
        self.scheduled_notifications: Dict[str, ScheduledNotification] = {}

        logger.info(f"Initialized ObserverPatternFSA {self.fsa_id}")

    def _acquire_lock(self):
        """Acquire thread lock if enabled."""
        if self._lock:
            self._lock.acquire()

    def _release_lock(self):
        """Release thread lock if enabled."""
        if self._lock:
            self._lock.release()

    def execute(self, observer_ops: List[ObserverOp]) -> ObserverResult:
        """
        Execute observer pattern pipeline.

        Args:
            observer_ops: List of observer operations

        Returns:
            ObserverResult with execution status
        """
        start_time = datetime.now()
        operations_count = 0
        notifications_sent = 0
        errors = []

        try:
            self._acquire_lock()

            for op in observer_ops:
                try:
                    if op.operation == "create_subject" and op.subject_id:
                        subject = self.create_subject(op.subject_id)
                        if subject:
                            operations_count += 1

                    elif op.operation == "attach" and op.subject_id and op.observer:
                        result = self.attach_observer(op.subject_id, op.observer)
                        if result.attached:
                            operations_count += 1

                    elif op.operation == "notify" and op.subject_id and op.event:
                        result = self.notify_observers(op.subject_id, op.event)
                        if result.notified:
                            operations_count += 1
                            notifications_sent += result.observers_notified

                except Exception as e:
                    errors.append(f"Error in operation {op.operation}: {str(e)}")

            execution_time = (datetime.now() - start_time).total_seconds()

            return ObserverResult(
                success=len(errors) == 0,
                operations_count=operations_count,
                notifications_sent=notifications_sent,
                errors=errors,
                execution_time=execution_time,
            )

        finally:
            self._release_lock()

    def validate(self, observer_config: ObserverConfig) -> ValidationResult:
        """
        Validate observer configuration.

        Args:
            observer_config: Configuration to validate

        Returns:
            ValidationResult with validation status
        """
        errors = []
        warnings = []

        # Validate max observers
        if observer_config.max_observers < 1:
            errors.append("max_observers must be positive")

        # Validate history size
        if observer_config.history_max_size < 0:
            errors.append("history_max_size must be non-negative")

        # Validate timeout
        if observer_config.notification_timeout <= 0:
            errors.append("notification_timeout must be positive")

        # Warnings
        if not observer_config.thread_safe:
            warnings.append("Thread safety is disabled")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def create_subject(self, subject_id: str) -> Optional[Subject]:
        """
        Create a new subject.

        Args:
            subject_id: Subject identifier

        Returns:
            Subject or None
        """
        try:
            self._acquire_lock()

            if subject_id in self.subjects:
                logger.warning(f"Subject {subject_id} already exists")
                return self.subjects[subject_id]

            subject = Subject(subject_id=subject_id)
            self.subjects[subject_id] = subject

            logger.info(f"Created subject: {subject_id}")

            return subject

        except Exception as e:
            logger.error(f"Error creating subject: {e}")
            return None

        finally:
            self._release_lock()

    def attach_observer(
        self,
        subject_id: str,
        observer: Observer,
        priority: int = 0,
    ) -> AttachResult:
        """
        Attach an observer to a subject.

        Args:
            subject_id: Subject identifier
            observer: Observer to attach
            priority: Observer priority (higher = notified first)

        Returns:
            AttachResult with attachment status
        """
        try:
            self._acquire_lock()

            if subject_id not in self.subjects:
                return AttachResult(
                    attached=False,
                    error=f"Subject not found: {subject_id}",
                )

            subject = self.subjects[subject_id]

            # Check max observers
            if len(subject.observers) >= self.config.max_observers:
                return AttachResult(
                    attached=False,
                    error="Maximum observers reached",
                )

            # Set priority if provided (non-zero), otherwise keep observer's existing priority
            if priority != 0:
                observer.priority = priority

            # Add observer
            subject.observers.append(observer)

            # Sort by priority if enabled
            if self.config.enable_priorities:
                subject.observers.sort(key=lambda o: o.priority, reverse=True)

            logger.info(f"Attached observer {observer.observer_id} to subject {subject_id}")

            return AttachResult(
                attached=True,
                observer_id=observer.observer_id,
            )

        except Exception as e:
            return AttachResult(
                attached=False,
                error=str(e),
            )

        finally:
            self._release_lock()

    def detach_observer(
        self,
        subject_id: str,
        observer: Observer,
    ) -> DetachResult:
        """
        Detach an observer from a subject.

        Args:
            subject_id: Subject identifier
            observer: Observer to detach

        Returns:
            DetachResult with detachment status
        """
        try:
            self._acquire_lock()

            if subject_id not in self.subjects:
                return DetachResult(
                    detached=False,
                    error=f"Subject not found: {subject_id}",
                )

            subject = self.subjects[subject_id]

            if observer in subject.observers:
                subject.observers.remove(observer)

                logger.info(f"Detached observer {observer.observer_id} from subject {subject_id}")

                return DetachResult(
                    detached=True,
                    observer_id=observer.observer_id,
                )
            else:
                return DetachResult(
                    detached=False,
                    error="Observer not found",
                )

        except Exception as e:
            return DetachResult(
                detached=False,
                error=str(e),
            )

        finally:
            self._release_lock()

    def notify_observers(
        self,
        subject_id: str,
        event: Event,
    ) -> NotifyResult:
        """
        Notify all observers of an event.

        Args:
            subject_id: Subject identifier
            event: Event to broadcast

        Returns:
            NotifyResult with notification status
        """
        try:
            self._acquire_lock()

            if subject_id not in self.subjects:
                return NotifyResult(
                    notified=False,
                    errors=[f"Subject not found: {subject_id}"],
                )

            subject = self.subjects[subject_id]
            event.source_subject = subject_id

            # Add to history
            if self.config.enable_history:
                subject.event_history.append(event)

            # Apply filters
            observers_to_notify = self._apply_filters(subject, event)

            # Notify observers
            observers_notified = 0
            errors = []

            for observer in observers_to_notify:
                try:
                    if observer.status == ObserverStatus.ACTIVE:
                        observer.update(event)
                        observers_notified += 1
                except Exception as e:
                    errors.append(f"Error notifying observer {observer.observer_id}: {str(e)}")

            return NotifyResult(
                notified=True,
                observers_notified=observers_notified,
                errors=errors,
            )

        except Exception as e:
            return NotifyResult(
                notified=False,
                errors=[str(e)],
            )

        finally:
            self._release_lock()

    def notify_async(
        self,
        subject_id: str,
        event: Event,
    ) -> AsyncNotifyResult:
        """
        Notify observers asynchronously.

        Args:
            subject_id: Subject identifier
            event: Event to broadcast

        Returns:
            AsyncNotifyResult with notification status
        """
        if not self.config.enable_async:
            return AsyncNotifyResult(
                notified=False,
                errors=["Async notifications are disabled"],
            )

        try:
            # Use threading for async notification
            def notify_thread():
                result = self.notify_observers(subject_id, event)
                return result

            thread = threading.Thread(target=notify_thread)
            thread.start()

            return AsyncNotifyResult(
                notified=True,
                observers_notified=0,  # Count not available yet
            )

        except Exception as e:
            return AsyncNotifyResult(
                notified=False,
                errors=[str(e)],
            )

    def filter_observers(
        self,
        subject_id: str,
        event: Event,
        filter_fn: Callable[[Observer], bool],
    ) -> FilterResult:
        """
        Notify observers with filtering.

        Args:
            subject_id: Subject identifier
            event: Event to broadcast
            filter_fn: Function to filter observers

        Returns:
            FilterResult with filtered notification status
        """
        try:
            self._acquire_lock()

            if subject_id not in self.subjects:
                return FilterResult(
                    filtered=False,
                    errors=[f"Subject not found: {subject_id}"],
                )

            subject = self.subjects[subject_id]

            # Filter observers
            filtered_observers = [o for o in subject.observers if filter_fn(o)]

            # Notify filtered observers
            observers_notified = 0
            errors = []

            for observer in filtered_observers:
                try:
                    if observer.status == ObserverStatus.ACTIVE:
                        observer.update(event)
                        observers_notified += 1
                except Exception as e:
                    errors.append(f"Error notifying observer: {str(e)}")

            return FilterResult(
                filtered=True,
                observers_notified=observers_notified,
                errors=errors,
            )

        except Exception as e:
            return FilterResult(
                filtered=False,
                errors=[str(e)],
            )

        finally:
            self._release_lock()

    def _apply_filters(self, subject: Subject, event: Event) -> List[Observer]:
        """
        Apply event filters to get observers to notify.

        Args:
            subject: Subject
            event: Event

        Returns:
            Filtered list of observers
        """
        observers = subject.observers.copy()

        if not self.config.enable_filters:
            return observers

        # Apply all filters
        for filter_fn in subject.filters.values():
            try:
                observers = [o for o in observers if filter_fn(event)]
            except:
                pass

        return observers

    def get_observers(self, subject_id: str) -> List[Observer]:
        """
        Get all observers for a subject.

        Args:
            subject_id: Subject identifier

        Returns:
            List of observers
        """
        try:
            self._acquire_lock()

            if subject_id not in self.subjects:
                return []

            return self.subjects[subject_id].observers.copy()

        finally:
            self._release_lock()

    def prioritize_observers(
        self,
        observers: List[Observer],
    ) -> PriorityList:
        """
        Prioritize observers by priority.

        Args:
            observers: List of observers

        Returns:
            PriorityList with sorted observers
        """
        if not self.config.enable_priorities:
            return PriorityList(observers=observers)

        sorted_observers = sorted(observers, key=lambda o: o.priority, reverse=True)

        return PriorityList(observers=sorted_observers)

    def create_weak_observer(self, observer: Observer) -> WeakObserver:
        """
        Create weak reference to observer.

        Args:
            observer: Observer to create weak reference for

        Returns:
            WeakObserver wrapper
        """
        if not self.config.enable_weak_refs:
            return WeakObserver(observer_id=observer.observer_id)

        weak_ref = weakref.ref(observer)

        return WeakObserver(
            weak_ref=weak_ref,
            observer_id=observer.observer_id,
        )

    def remove_dead_observers(self, subject_id: str) -> CleanupResult:
        """
        Remove garbage-collected weak observers.

        Args:
            subject_id: Subject identifier

        Returns:
            CleanupResult with cleanup status
        """
        try:
            self._acquire_lock()

            if subject_id not in self.subjects:
                return CleanupResult(
                    cleaned=False,
                    removed_count=0,
                )

            subject = self.subjects[subject_id]

            # Remove dead weak observers
            removed_count = 0
            alive_refs = []

            for weak_ref in subject.weak_observers:
                if weak_ref() is None:
                    removed_count += 1
                else:
                    alive_refs.append(weak_ref)

            subject.weak_observers = alive_refs

            return CleanupResult(
                cleaned=True,
                removed_count=removed_count,
            )

        except Exception as e:
            logger.error(f"Error cleaning dead observers: {e}")
            return CleanupResult(
                cleaned=False,
                removed_count=0,
            )

        finally:
            self._release_lock()

    def get_event_history(
        self,
        subject_id: str,
        limit: Optional[int] = None,
    ) -> EventHistory:
        """
        Get event history for a subject.

        Args:
            subject_id: Subject identifier
            limit: Maximum number of events to return

        Returns:
            EventHistory with past events
        """
        try:
            self._acquire_lock()

            if subject_id not in self.subjects:
                return EventHistory(
                    subject_id=subject_id,
                    events=[],
                    total_events=0,
                )

            subject = self.subjects[subject_id]
            events = list(subject.event_history)

            if limit is not None:
                events = events[-limit:]

            return EventHistory(
                subject_id=subject_id,
                events=events,
                total_events=len(subject.event_history),
            )

        finally:
            self._release_lock()

    def clear_event_history(self, subject_id: str) -> ClearHistoryResult:
        """
        Clear event history for a subject.

        Args:
            subject_id: Subject identifier

        Returns:
            ClearHistoryResult with clearing status
        """
        try:
            self._acquire_lock()

            if subject_id not in self.subjects:
                return ClearHistoryResult(
                    cleared=False,
                    cleared_count=0,
                )

            subject = self.subjects[subject_id]
            cleared_count = len(subject.event_history)
            subject.event_history.clear()

            return ClearHistoryResult(
                cleared=True,
                cleared_count=cleared_count,
            )

        except Exception as e:
            logger.error(f"Error clearing history: {e}")
            return ClearHistoryResult(
                cleared=False,
                cleared_count=0,
            )

        finally:
            self._release_lock()

    def create_event(
        self,
        event_type: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> Event:
        """
        Create an event.

        Args:
            event_type: Event type
            data: Event data

        Returns:
            Event object
        """
        return Event(
            event_type=event_type,
            data=data or {},
        )

    def schedule_notification(
        self,
        subject_id: str,
        event: Event,
        delay: float,
    ) -> ScheduleResult:
        """
        Schedule a delayed notification.

        Args:
            subject_id: Subject identifier
            event: Event to send
            delay: Delay in seconds

        Returns:
            ScheduleResult with scheduling status
        """
        try:
            if subject_id not in self.subjects:
                return ScheduleResult(
                    scheduled=False,
                    error=f"Subject not found: {subject_id}",
                )

            def notify_callback():
                self.notify_observers(subject_id, event)
                # Remove from scheduled list
                if scheduled.notification_id in self.scheduled_notifications:
                    del self.scheduled_notifications[scheduled.notification_id]

            timer = threading.Timer(delay, notify_callback)

            scheduled = ScheduledNotification(
                subject_id=subject_id,
                event=event,
                delay=delay,
                timer=timer,
            )

            self.scheduled_notifications[scheduled.notification_id] = scheduled

            timer.start()

            return ScheduleResult(
                scheduled=True,
                notification_id=scheduled.notification_id,
            )

        except Exception as e:
            return ScheduleResult(
                scheduled=False,
                error=str(e),
            )

    def cancel_scheduled_notification(
        self,
        notification_id: str,
    ) -> CancelResult:
        """
        Cancel a scheduled notification.

        Args:
            notification_id: Notification identifier

        Returns:
            CancelResult with cancellation status
        """
        try:
            if notification_id not in self.scheduled_notifications:
                return CancelResult(
                    cancelled=False,
                    error="Notification not found",
                )

            scheduled = self.scheduled_notifications[notification_id]

            if scheduled.timer:
                scheduled.timer.cancel()

            del self.scheduled_notifications[notification_id]

            return CancelResult(
                cancelled=True,
                notification_id=notification_id,
            )

        except Exception as e:
            return CancelResult(
                cancelled=False,
                error=str(e),
            )

    def batch_notify(
        self,
        subject_id: str,
        events: List[Event],
    ) -> BatchNotifyResult:
        """
        Send multiple events in batch.

        Args:
            subject_id: Subject identifier
            events: List of events

        Returns:
            BatchNotifyResult with batch notification status
        """
        try:
            self._acquire_lock()

            if subject_id not in self.subjects:
                return BatchNotifyResult(
                    notified=False,
                    errors=[f"Subject not found: {subject_id}"],
                )

            events_sent = 0
            total_observers_notified = 0
            errors = []

            for event in events:
                result = self.notify_observers(subject_id, event)
                if result.notified:
                    events_sent += 1
                    total_observers_notified += result.observers_notified
                errors.extend(result.errors)

            return BatchNotifyResult(
                notified=True,
                events_sent=events_sent,
                observers_notified=total_observers_notified,
                errors=errors,
            )

        except Exception as e:
            return BatchNotifyResult(
                notified=False,
                errors=[str(e)],
            )

        finally:
            self._release_lock()

    def create_event_filter(
        self,
        filter_fn: Callable[[Event], bool],
        description: str = "",
    ) -> EventFilter:
        """
        Create an event filter.

        Args:
            filter_fn: Filter function
            description: Filter description

        Returns:
            EventFilter object
        """
        return EventFilter(
            filter_fn=filter_fn,
            description=description,
        )

    def apply_filter(
        self,
        subject_id: str,
        event_filter: EventFilter,
    ) -> ApplyFilterResult:
        """
        Apply a filter to a subject.

        Args:
            subject_id: Subject identifier
            event_filter: Event filter

        Returns:
            ApplyFilterResult with application status
        """
        try:
            self._acquire_lock()

            if not self.config.enable_filters:
                return ApplyFilterResult(
                    applied=False,
                    error="Filters are disabled",
                )

            if subject_id not in self.subjects:
                return ApplyFilterResult(
                    applied=False,
                    error=f"Subject not found: {subject_id}",
                )

            subject = self.subjects[subject_id]
            subject.filters[event_filter.filter_id] = event_filter.filter_fn

            return ApplyFilterResult(
                applied=True,
                filter_id=event_filter.filter_id,
            )

        except Exception as e:
            return ApplyFilterResult(
                applied=False,
                error=str(e),
            )

        finally:
            self._release_lock()

    def remove_filter(
        self,
        subject_id: str,
        filter_id: str,
    ) -> RemoveFilterResult:
        """
        Remove a filter from a subject.

        Args:
            subject_id: Subject identifier
            filter_id: Filter identifier

        Returns:
            RemoveFilterResult with removal status
        """
        try:
            self._acquire_lock()

            if subject_id not in self.subjects:
                return RemoveFilterResult(
                    removed=False,
                    error=f"Subject not found: {subject_id}",
                )

            subject = self.subjects[subject_id]

            if filter_id in subject.filters:
                del subject.filters[filter_id]

                return RemoveFilterResult(
                    removed=True,
                    filter_id=filter_id,
                )
            else:
                return RemoveFilterResult(
                    removed=False,
                    error="Filter not found",
                )

        except Exception as e:
            return RemoveFilterResult(
                removed=False,
                error=str(e),
            )

        finally:
            self._release_lock()

    def get_observer_count(self, subject_id: str) -> int:
        """
        Get number of observers for a subject.

        Args:
            subject_id: Subject identifier

        Returns:
            Number of observers
        """
        try:
            self._acquire_lock()

            if subject_id not in self.subjects:
                return 0

            return len(self.subjects[subject_id].observers)

        finally:
            self._release_lock()

    def destroy_subject(self, subject_id: str) -> DestroyResult:
        """
        Destroy a subject and detach all observers.

        Args:
            subject_id: Subject identifier

        Returns:
            DestroyResult with destruction status
        """
        try:
            self._acquire_lock()

            if subject_id not in self.subjects:
                return DestroyResult(
                    destroyed=False,
                    error=f"Subject not found: {subject_id}",
                )

            subject = self.subjects[subject_id]
            observers_count = len(subject.observers)

            # Clear observers
            subject.observers.clear()
            subject.weak_observers.clear()
            subject.event_history.clear()
            subject.filters.clear()

            # Remove subject
            del self.subjects[subject_id]

            logger.info(f"Destroyed subject: {subject_id}")

            return DestroyResult(
                destroyed=True,
                subject_id=subject_id,
                observers_detached=observers_count,
            )

        except Exception as e:
            return DestroyResult(
                destroyed=False,
                error=str(e),
            )

        finally:
            self._release_lock()

    def __del__(self):
        """Cleanup on destruction."""
        try:
            # Cancel all scheduled notifications
            for notification in list(self.scheduled_notifications.values()):
                if notification.timer:
                    notification.timer.cancel()
            self.scheduled_notifications.clear()
        except:
            pass

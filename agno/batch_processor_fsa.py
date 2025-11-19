"""Batch Processor Finite State Automaton for batch processing with parallel execution."""

import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, List, Optional

logger = logging.getLogger(__name__)


class State(Enum):
    """FSA states for batch processing."""
    IDLE = "idle"
    BATCHING = "batching"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class BatchResult:
    """Result of processing a batch."""
    batch_id: int
    items: List[Any]
    success: bool
    result: Any = None
    error: Optional[Exception] = None


@dataclass
class ProcessingContext:
    """Context for batch processing."""
    items: List[Any]
    batch_size: int
    batches: List[List[Any]] = field(default_factory=list)
    results: List[BatchResult] = field(default_factory=list)
    total_items: int = 0
    processed_items: int = 0
    failed_batches: int = 0


class BatchProcessorFSA:
    """Finite State Automaton for batch processing."""

    def __init__(self, batch_size: int = 10, max_workers: Optional[int] = None):
        self.batch_size = batch_size
        self.max_workers = max_workers or 4
        self.state = State.IDLE
        self.context: Optional[ProcessingContext] = None
        self._lock = threading.Lock()

    def process(
        self,
        items: List[Any],
        processor: Callable[[List[Any]], Any],
        batch_size: Optional[int] = None,
        parallel: bool = False,
        on_batch_complete: Optional[Callable[[BatchResult], None]] = None,
        on_batch_error: Optional[Callable[[BatchResult], None]] = None
    ) -> List[BatchResult]:
        """Process items in batches."""
        with self._lock:
            if self.state != State.IDLE:
                raise RuntimeError(f"Processor busy in state: {self.state.value}")

            batch_size = batch_size or self.batch_size
            self.context = ProcessingContext(
                items=items,
                batch_size=batch_size,
                total_items=len(items)
            )
            self._transition(State.IDLE, State.BATCHING)

        logger.info(f"Processing {len(items)} items in batches of {batch_size}")

        # Create batches
        self._create_batches()

        # Process batches
        self._transition(State.BATCHING, State.PROCESSING)

        if parallel:
            self._process_parallel(processor, on_batch_complete, on_batch_error)
        else:
            self._process_sequential(processor, on_batch_complete, on_batch_error)

        # Finalize
        self._finalize()
        return self.context.results

    def get_progress(self) -> dict:
        """Get current processing progress."""
        if not self.context:
            return {"state": self.state.value, "progress": 0.0}

        progress = (
            self.context.processed_items / self.context.total_items * 100
            if self.context.total_items > 0 else 0.0
        )

        return {
            "state": self.state.value,
            "total_items": self.context.total_items,
            "processed_items": self.context.processed_items,
            "total_batches": len(self.context.batches),
            "failed_batches": self.context.failed_batches,
            "progress": progress
        }

    def reset(self):
        """Reset processor to IDLE state."""
        with self._lock:
            self._transition(self.state, State.IDLE)
            self.context = None

    def _create_batches(self):
        """Group items into batches."""
        items = self.context.items
        batch_size = self.context.batch_size

        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            self.context.batches.append(batch)

        logger.info(f"Created {len(self.context.batches)} batches")

    def _process_sequential(
        self,
        processor: Callable,
        on_complete: Optional[Callable],
        on_error: Optional[Callable]
    ):
        """Process batches sequentially."""
        for batch_id, batch in enumerate(self.context.batches):
            result = self._process_batch(batch_id, batch, processor)
            self.context.results.append(result)
            self.context.processed_items += len(batch)

            if result.success:
                logger.debug(f"Batch {batch_id} completed ({len(batch)} items)")
                if on_complete:
                    on_complete(result)
            else:
                logger.error(f"Batch {batch_id} failed: {result.error}")
                self.context.failed_batches += 1
                if on_error:
                    on_error(result)

    def _process_parallel(
        self,
        processor: Callable,
        on_complete: Optional[Callable],
        on_error: Optional[Callable]
    ):
        """Process batches in parallel."""
        futures = {}

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            for batch_id, batch in enumerate(self.context.batches):
                future = executor.submit(self._process_batch, batch_id, batch, processor)
                futures[future] = (batch_id, batch)

            for future in as_completed(futures):
                batch_id, batch = futures[future]
                result = future.result()
                self.context.results.append(result)
                self.context.processed_items += len(batch)

                if result.success:
                    logger.debug(f"Batch {batch_id} completed ({len(batch)} items)")
                    if on_complete:
                        on_complete(result)
                else:
                    logger.error(f"Batch {batch_id} failed: {result.error}")
                    self.context.failed_batches += 1
                    if on_error:
                        on_error(result)

        # Sort results by batch_id
        self.context.results.sort(key=lambda r: r.batch_id)

    def _process_batch(self, batch_id: int, batch: List[Any], processor: Callable) -> BatchResult:
        """Process a single batch."""
        try:
            result = processor(batch)
            return BatchResult(
                batch_id=batch_id,
                items=batch,
                success=True,
                result=result
            )
        except Exception as e:
            logger.error(f"Error processing batch {batch_id}: {e}")
            return BatchResult(
                batch_id=batch_id,
                items=batch,
                success=False,
                error=e
            )

    def _finalize(self):
        """Finalize processing and transition to final state."""
        if self.context.failed_batches > 0:
            logger.warning(
                f"Processing completed with {self.context.failed_batches} failed batches"
            )
            self._transition(State.PROCESSING, State.FAILED)
        else:
            logger.info(f"Successfully processed all {self.context.processed_items} items")
            self._transition(State.PROCESSING, State.COMPLETED)

    def _transition(self, from_state: State, to_state: State):
        """Transition between states."""
        logger.debug(f"State transition: {from_state.value} -> {to_state.value}")
        self.state = to_state

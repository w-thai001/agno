"""Thread Pool Manager with FSA-based worker lifecycle management."""
import threading
import queue
import time
from enum import Enum
from typing import Callable, Optional
from dataclasses import dataclass, field


class WorkerState(Enum):
    IDLE = "idle"
    RUNNING = "running"
    BUSY = "busy"
    UNHEALTHY = "unhealthy"
    TERMINATED = "terminated"


@dataclass(order=True)
class Task:
    priority: int
    task_id: str = field(compare=False)
    func: Callable = field(compare=False)
    args: tuple = field(default_factory=tuple, compare=False)
    kwargs: dict = field(default_factory=dict, compare=False)
    cancelled: bool = field(default=False, compare=False)


class Worker:
    def __init__(self, worker_id: int, pool: 'ThreadPoolManager'):
        self.worker_id, self.pool, self.state = worker_id, pool, WorkerState.IDLE
        self.thread, self.last_heartbeat = None, time.time()
        self.task_count, self.error_count, self.lock = 0, 0, threading.Lock()

    def start(self):
        with self.lock:
            self.state = WorkerState.RUNNING
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self):
        while self.state != WorkerState.TERMINATED:
            try:
                task = self.pool.task_queue.get(timeout=1)
                if task.cancelled:
                    continue
                with self.lock:
                    self.state, self.last_heartbeat = WorkerState.BUSY, time.time()
                try:
                    task.func(*task.args, **task.kwargs)
                    self.task_count += 1
                except Exception:
                    self.error_count += 1
                    if self.error_count > 3:
                        with self.lock:
                            self.state = WorkerState.UNHEALTHY
                with self.lock:
                    self.state, self.last_heartbeat = WorkerState.IDLE, time.time()
            except queue.Empty:
                with self.lock:
                    self.last_heartbeat = time.time()

    def terminate(self):
        with self.lock:
            self.state = WorkerState.TERMINATED

    def is_healthy(self) -> bool:
        with self.lock:
            return (self.state not in [WorkerState.UNHEALTHY, WorkerState.TERMINATED] and
                    time.time() - self.last_heartbeat < 30)


class ThreadPoolManager:
    def __init__(self, min_workers: int = 2, max_workers: int = 10):
        self.min_workers, self.max_workers = min_workers, max_workers
        self.task_queue = queue.PriorityQueue()
        self.workers, self.lock, self.running = [], threading.Lock(), False
        self.task_registry, self.monitor_thread = {}, None

    def start(self):
        self.running = True
        for i in range(self.min_workers):
            self._add_worker(i)
        self.monitor_thread = threading.Thread(target=self._monitor, daemon=True)
        self.monitor_thread.start()

    def _add_worker(self, worker_id: int):
        worker = Worker(worker_id, self)
        with self.lock:
            self.workers.append(worker)
        worker.start()

    def submit(self, func: Callable, priority: int = 5, task_id: Optional[str] = None,
               *args, **kwargs) -> str:
        task_id = task_id or f"task_{time.time()}_{id(func)}"
        task = Task(priority=priority, task_id=task_id, func=func, args=args, kwargs=kwargs)
        with self.lock:
            self.task_registry[task_id] = task
        self.task_queue.put(task)
        return task_id

    def cancel(self, task_id: str) -> bool:
        with self.lock:
            if task_id in self.task_registry:
                self.task_registry[task_id].cancelled = True
                return True
        return False

    def _monitor(self):
        while self.running:
            time.sleep(2)
            self._health_check()
            self._scale_pool()

    def _health_check(self):
        with self.lock:
            for worker in [w for w in self.workers if not w.is_healthy()]:
                worker.terminate()
                self.workers.remove(worker)
                new_worker = Worker(worker.worker_id, self)
                self.workers.append(new_worker)
                new_worker.start()

    def _scale_pool(self):
        queue_size = self.task_queue.qsize()
        with self.lock:
            active, total = len([w for w in self.workers if w.state == WorkerState.BUSY]), len(self.workers)
            if queue_size > total and total < self.max_workers:
                self._add_worker(max([w.worker_id for w in self.workers], default=-1) + 1)
            elif active < self.min_workers and total > self.min_workers:
                idle = [w for w in self.workers if w.state == WorkerState.IDLE]
                if idle:
                    idle[0].terminate()
                    self.workers.remove(idle[0])

    def shutdown(self, wait: bool = True):
        self.running = False
        with self.lock:
            for worker in self.workers:
                worker.terminate()
        if wait and self.monitor_thread:
            self.monitor_thread.join(timeout=5)

    def get_stats(self) -> dict:
        with self.lock:
            return {"total_workers": len(self.workers), "idle": len([w for w in self.workers if w.state == WorkerState.IDLE]),
                    "busy": len([w for w in self.workers if w.state == WorkerState.BUSY]), "queue_size": self.task_queue.qsize()}

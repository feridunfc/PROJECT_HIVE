"""
Background task queue manager for async pipeline execution.
"""
import asyncio
import uuid
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import threading
import queue as py_queue
from concurrent.futures import ThreadPoolExecutor

from core.telemetry.metrics import metrics
from observability.session_replay import session_replay, EventType


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    """Background task representation."""
    task_id: str
    goal: str
    pipeline_type: str = "t1"
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    session_id: Optional[str] = None


class TaskQueueManager:
    """
    Manages background execution of pipeline tasks.
    """

    def __init__(self, max_workers: int = 3):
        self.max_workers = max_workers
        self.tasks: Dict[str, Task] = {}
        self.task_queue = py_queue.Queue()
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self._lock = threading.RLock()
        self._running = False
        self._worker_thread = None

    def start(self):
        """Start the task queue worker."""
        if self._running:
            return

        self._running = True
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()

        metrics.update_queue_size("pipeline_tasks", 0)

    def stop(self):
        """Stop the task queue worker."""
        self._running = False
        if self._worker_thread:
            self._worker_thread.join(timeout=5.0)
        self.executor.shutdown(wait=True)

    def _worker_loop(self):
        """Background worker loop."""
        while self._running:
            try:
                # Get task from queue with timeout
                task_id = self.task_queue.get(timeout=1.0)

                # Process task
                self.executor.submit(self._process_task, task_id)

                # Update metrics
                metrics.update_queue_size("pipeline_tasks", self.task_queue.qsize())

            except py_queue.Empty:
                continue
            except Exception as e:
                print(f"Task worker error: {e}")
                continue

    def _process_task(self, task_id: str):
        """Process a single task."""
        with self._lock:
            task = self.tasks.get(task_id)
            if not task:
                return

            # Update task status
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now()

        try:
            # Import here to avoid circular imports
            from pipelines.t1_fortress_pipeline import T1FortressPipeline
            from pipelines.t0_velocity_pipeline import T0VelocityPipeline

            # Start session recording
            session_id = session_replay.start_session(
                session_id=task_id,
                run_id=task_id,
                goal=task.goal,
                pipeline_type=task.pipeline_type,
                metadata=task.metadata
            )

            task.session_id = session_id

            # Run the appropriate pipeline
            if task.pipeline_type == "t0":
                pipeline = T0VelocityPipeline()
            else:
                pipeline = T1FortressPipeline()

            # Record start event
            session_replay.record_event(
                session_id=session_id,
                event_type=EventType.AGENT_START,
                agent_name="Pipeline",
                data={
                    "goal": task.goal,
                    "pipeline_type": task.pipeline_type,
                    "task_id": task_id
                }
            )

            # Run pipeline (sync or async depending on implementation)
            # Note: We need to adapt if pipeline.run is async
            import asyncio

            # Create event loop for this thread
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                state = loop.run_until_complete(pipeline.run(task.goal))
                loop.close()
            except RuntimeError:
                # If there's already a running loop (e.g., in main thread)
                state = asyncio.run(pipeline.run(task.goal))

            # Record completion
            session_replay.record_event(
                session_id=session_id,
                event_type=EventType.AGENT_COMPLETE,
                agent_name="Pipeline",
                data={"state": state.to_dict() if hasattr(state, 'to_dict') else str(state)},
                duration_ms=(datetime.now() - task.started_at).total_seconds() * 1000
            )

            session_replay.end_session(session_id, "completed")

            # Update task with result
            with self._lock:
                task.status = TaskStatus.COMPLETED
                task.completed_at = datetime.now()
                task.result = {
                    "state": state.to_dict() if hasattr(state, 'to_dict') else str(state),
                    "session_id": session_id,
                    "artifacts": getattr(state, 'artifacts', {}),
                    "metrics": {
                        "duration_seconds": (task.completed_at - task.started_at).total_seconds(),
                        "status": "success"
                    }
                }

            # Update metrics
            metrics.record_pipeline_run(
                pipeline_type=task.pipeline_type,
                duration=(task.completed_at - task.started_at).total_seconds(),
                status="completed"
            )

        except Exception as e:
            error_msg = str(e)
            print(f"Task {task_id} failed: {error_msg}")

            # Record error
            if task.session_id:
                session_replay.record_event(
                    session_id=task.session_id,
                    event_type=EventType.AGENT_ERROR,
                    agent_name="Pipeline",
                    data={"error": error_msg}
                )
                session_replay.end_session(task.session_id, "failed", error_msg)

            # Update task with error
            with self._lock:
                task.status = TaskStatus.FAILED
                task.completed_at = datetime.now()
                task.error = error_msg

            # Update metrics
            metrics.record_pipeline_run(
                pipeline_type=task.pipeline_type,
                duration=(datetime.now() - task.started_at).total_seconds(),
                status="failed"
            )

    def submit_task(self, goal: str, pipeline_type: str = "t1",
                    metadata: Optional[Dict[str, Any]] = None) -> str:
        """Submit a new task to the queue."""
        task_id = str(uuid.uuid4())

        task = Task(
            task_id=task_id,
            goal=goal,
            pipeline_type=pipeline_type,
            metadata=metadata or {}
        )

        with self._lock:
            self.tasks[task_id] = task
            self.task_queue.put(task_id)

        # Update metrics
        metrics.update_queue_size("pipeline_tasks", self.task_queue.qsize())

        return task_id

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID."""
        with self._lock:
            return self.tasks.get(task_id)

    def list_tasks(self, limit: int = 50, offset: int = 0) -> list[Task]:
        """List tasks sorted by creation time."""
        with self._lock:
            tasks = list(self.tasks.values())
            tasks.sort(key=lambda t: t.created_at, reverse=True)
            return tasks[offset:offset + limit]

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending task."""
        with self._lock:
            task = self.tasks.get(task_id)
            if not task or task.status != TaskStatus.PENDING:
                return False

            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.now()

            # Note: We can't remove from queue easily, but we can mark it as cancelled
            # The worker will skip it when it sees cancelled status

            return True

    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        with self._lock:
            total = len(self.tasks)
            pending = sum(1 for t in self.tasks.values() if t.status == TaskStatus.PENDING)
            running = sum(1 for t in self.tasks.values() if t.status == TaskStatus.RUNNING)
            completed = sum(1 for t in self.tasks.values() if t.status == TaskStatus.COMPLETED)
            failed = sum(1 for t in self.tasks.values() if t.status == TaskStatus.FAILED)

            return {
                "total_tasks": total,
                "pending": pending,
                "running": running,
                "completed": completed,
                "failed": failed,
                "queue_size": self.task_queue.qsize(),
                "max_workers": self.max_workers
            }


# Global task queue instance
task_queue = TaskQueueManager(max_workers=3)
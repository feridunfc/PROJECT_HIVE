"""
Worker for processing background tasks.
"""
import asyncio
import threading
from typing import Dict, Any

from .manager import TaskQueueManager


class TaskWorker:
    """Worker for processing pipeline tasks."""

    def __init__(self, task_queue: TaskQueueManager):
        self.task_queue = task_queue
        self._stop_event = threading.Event()
        self._worker_thread = None

    def start(self):
        """Start the worker."""
        if self._worker_thread and self._worker_thread.is_alive():
            return

        self._stop_event.clear()
        self._worker_thread = threading.Thread(target=self._run, daemon=True)
        self._worker_thread.start()

    def stop(self):
        """Stop the worker."""
        self._stop_event.set()
        if self._worker_thread:
            self._worker_thread.join(timeout=5.0)

    def _run(self):
        """Main worker loop."""
        while not self._stop_event.is_set():
            # Process tasks
            self.task_queue.start()

            # Sleep to prevent busy waiting
            self._stop_event.wait(timeout=0.1)
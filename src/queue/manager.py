"""
In-memory print queue manager.

Per spec: Simple queue, no persistence required.
Each printer gets its own queue.
"""

import asyncio
import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Callable, Awaitable

from src.printers.base import PrintJob, PrintResult

logger = logging.getLogger(__name__)


class JobStatus(Enum):
    QUEUED = "queued"
    PRINTING = "printing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class QueuedJob:
    job: PrintJob
    status: JobStatus = JobStatus.QUEUED
    queued_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[PrintResult] = None
    error: Optional[str] = None


class PrintQueue:
    """
    In-memory print queue for a single printer.

    Jobs are processed sequentially in FIFO order.
    """

    def __init__(
        self,
        printer_id: str,
        print_handler: Callable[[PrintJob], Awaitable[PrintResult]],
        max_queue_size: int = 100
    ):
        self.printer_id = printer_id
        self._print_handler = print_handler
        self._max_queue_size = max_queue_size

        self._queue: deque[QueuedJob] = deque()
        self._current_job: Optional[QueuedJob] = None
        self._history: deque[QueuedJob] = deque(maxlen=50)  # Keep last 50 completed jobs
        self._processing = False
        self._lock = asyncio.Lock()

    async def add(self, job: PrintJob) -> QueuedJob:
        """Add a job to the queue."""
        async with self._lock:
            if len(self._queue) >= self._max_queue_size:
                raise QueueFullError(f"Queue full (max {self._max_queue_size} jobs)")

            queued = QueuedJob(job=job)
            self._queue.append(queued)
            logger.info(f"Job {job.id} added to queue for {self.printer_id}")

            # Start processing if not already running
            if not self._processing:
                asyncio.create_task(self._process_queue())

            return queued

    async def _process_queue(self):
        """Process jobs from the queue."""
        self._processing = True

        try:
            while True:
                async with self._lock:
                    if not self._queue:
                        self._processing = False
                        return

                    self._current_job = self._queue.popleft()
                    self._current_job.status = JobStatus.PRINTING
                    self._current_job.started_at = datetime.now()

                job = self._current_job

                try:
                    logger.info(f"Processing job {job.job.id}")
                    result = await self._print_handler(job.job)

                    job.result = result
                    job.completed_at = datetime.now()

                    if result.success:
                        job.status = JobStatus.COMPLETED
                        logger.info(f"Job {job.job.id} completed successfully")
                    else:
                        job.status = JobStatus.FAILED
                        job.error = result.message
                        logger.warning(f"Job {job.job.id} failed: {result.message}")

                except Exception as e:
                    job.status = JobStatus.FAILED
                    job.error = str(e)
                    job.completed_at = datetime.now()
                    logger.error(f"Job {job.job.id} failed with exception: {e}")

                finally:
                    self._history.append(job)
                    self._current_job = None

        except Exception as e:
            logger.error(f"Queue processing error: {e}")
            self._processing = False

    def get_status(self) -> dict:
        """Get queue status."""
        return {
            "printer_id": self.printer_id,
            "queued": len(self._queue),
            "processing": self._current_job is not None,
            "current_job": self._current_job.job.id if self._current_job else None,
        }

    def get_queue(self) -> list[dict]:
        """Get list of queued jobs."""
        jobs = []

        if self._current_job:
            jobs.append(_job_to_dict(self._current_job))

        for queued in self._queue:
            jobs.append(_job_to_dict(queued))

        return jobs

    def get_history(self, limit: int = 10) -> list[dict]:
        """Get recent job history."""
        return [_job_to_dict(j) for j in list(self._history)[-limit:]]

    def get_job(self, job_id: str) -> Optional[QueuedJob]:
        """Get a specific job by ID."""
        if self._current_job and self._current_job.job.id == job_id:
            return self._current_job

        for queued in self._queue:
            if queued.job.id == job_id:
                return queued

        for completed in self._history:
            if completed.job.id == job_id:
                return completed

        return None

    async def cancel(self, job_id: str) -> bool:
        """Cancel a queued job (cannot cancel if already printing)."""
        async with self._lock:
            for queued in self._queue:
                if queued.job.id == job_id:
                    queued.status = JobStatus.CANCELLED
                    queued.completed_at = datetime.now()
                    self._queue.remove(queued)
                    self._history.append(queued)
                    logger.info(f"Job {job_id} cancelled")
                    return True

        return False


class QueueFullError(Exception):
    """Raised when queue capacity is reached."""
    pass


def _job_to_dict(queued: QueuedJob) -> dict:
    """Convert QueuedJob to API response dict."""
    return {
        "id": queued.job.id,
        "printer_id": queued.job.printer_id,
        "filename": queued.job.filename,
        "status": queued.status.value,
        "queued_at": queued.queued_at.isoformat(),
        "started_at": queued.started_at.isoformat() if queued.started_at else None,
        "completed_at": queued.completed_at.isoformat() if queued.completed_at else None,
        "error": queued.error,
    }

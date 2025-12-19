"""
In-memory print queue manager with offline support.

Per spec: Simple queue, no persistence required.
Each printer gets its own queue.

Resilience features:
- Offline job queuing when printer unavailable
- Job expiration after configurable timeout
- Automatic processing when printer comes back online
"""

import asyncio
import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Awaitable, Callable, Optional

from src.printers.base import PrintJob, PrintResult

logger = logging.getLogger(__name__)


class JobStatus(Enum):
    QUEUED = "queued"
    QUEUED_OFFLINE = "queued_offline"  # Held while printer offline
    PRINTING = "printing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"  # Timed out while waiting for offline printer


@dataclass
class QueuedJob:
    job: PrintJob
    status: JobStatus = JobStatus.QUEUED
    queued_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None  # For offline jobs
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[PrintResult] = None
    error: Optional[str] = None


class PrintQueue:
    """
    In-memory print queue for a single printer.

    Jobs are processed sequentially in FIFO order.
    Supports offline queuing with configurable expiration.
    """

    def __init__(
        self,
        printer_id: str,
        print_handler: Callable[[PrintJob], Awaitable[PrintResult]],
        max_queue_size: int = 100,
        offline_queue_timeout_sec: float = 600.0  # 10 minutes default
    ):
        self.printer_id = printer_id
        self._print_handler = print_handler
        self._max_queue_size = max_queue_size
        self._offline_queue_timeout_sec = offline_queue_timeout_sec

        self._queue: deque[QueuedJob] = deque()
        self._current_job: Optional[QueuedJob] = None
        self._history: deque[QueuedJob] = deque(maxlen=50)  # Keep last 50 completed jobs
        self._processing = False
        self._lock = asyncio.Lock()

        # Offline state tracking
        self._printer_online = True
        self._expiry_task: Optional[asyncio.Task] = None

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

    async def add_offline(self, job: PrintJob) -> QueuedJob:
        """
        Add job when printer is offline.

        Job will have QUEUED_OFFLINE status and an expiration time.
        """
        async with self._lock:
            if len(self._queue) >= self._max_queue_size:
                raise QueueFullError(f"Queue full (max {self._max_queue_size} jobs)")

            expires_at = datetime.now() + timedelta(seconds=self._offline_queue_timeout_sec)
            queued = QueuedJob(
                job=job,
                status=JobStatus.QUEUED_OFFLINE,
                expires_at=expires_at
            )
            self._queue.append(queued)

            logger.info(
                f"[JOB_QUEUED_OFFLINE] Job {job.id} queued offline for {self.printer_id}, "
                f"expires at {expires_at.isoformat()}"
            )

            # Start expiry checker if not running
            if self._expiry_task is None or self._expiry_task.done():
                self._expiry_task = asyncio.create_task(self._check_expired_jobs())

            return queued

    async def on_printer_online(self) -> int:
        """
        Called when printer comes back online.

        Promotes QUEUED_OFFLINE jobs to QUEUED and starts processing.
        Returns number of jobs promoted.
        """
        self._printer_online = True
        promoted_count = 0

        async with self._lock:
            for job in self._queue:
                if job.status == JobStatus.QUEUED_OFFLINE:
                    job.status = JobStatus.QUEUED
                    job.expires_at = None  # No longer expires
                    promoted_count += 1
                    logger.info(f"Job {job.job.id} promoted from offline queue")

        if promoted_count > 0:
            logger.info(
                f"[PRINTER_ONLINE] {self.printer_id}: {promoted_count} jobs promoted from offline queue"
            )

        # Trigger queue processing
        if not self._processing and self._queue:
            asyncio.create_task(self._process_queue())

        return promoted_count

    def set_printer_offline(self) -> None:
        """Mark printer as offline (queue will hold jobs)."""
        self._printer_online = False
        logger.info(f"[PRINTER_OFFLINE] {self.printer_id}: Queue will hold jobs")

    async def _check_expired_jobs(self) -> None:
        """Background task to expire old offline jobs."""
        while True:
            await asyncio.sleep(60)  # Check every minute

            now = datetime.now()
            expired_jobs: list[QueuedJob] = []

            async with self._lock:
                # Find expired offline jobs
                for job in list(self._queue):
                    if (job.status == JobStatus.QUEUED_OFFLINE
                            and job.expires_at
                            and job.expires_at < now):
                        expired_jobs.append(job)

                # Expire them
                for job in expired_jobs:
                    job.status = JobStatus.EXPIRED
                    job.completed_at = now
                    job.error = "Job expired while printer offline"
                    self._queue.remove(job)
                    self._history.append(job)
                    logger.warning(f"[JOB_EXPIRED] Job {job.job.id} expired after waiting for offline printer")

            # Stop checker if no more offline jobs
            has_offline_jobs = any(
                j.status == JobStatus.QUEUED_OFFLINE for j in self._queue
            )
            if not has_offline_jobs:
                logger.debug("No more offline jobs, stopping expiry checker")
                return

    async def _process_queue(self) -> None:
        """Process jobs from the queue."""
        self._processing = True

        try:
            while True:
                async with self._lock:
                    if not self._queue:
                        self._processing = False
                        return

                    # Skip QUEUED_OFFLINE jobs (they're waiting for printer)
                    next_job = None
                    for job in self._queue:
                        if job.status == JobStatus.QUEUED:
                            next_job = job
                            break

                    if next_job is None:
                        # Only offline jobs remain - stop processing
                        self._processing = False
                        return

                    self._queue.remove(next_job)
                    self._current_job = next_job
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
        offline_count = sum(1 for j in self._queue if j.status == JobStatus.QUEUED_OFFLINE)
        return {
            "printer_id": self.printer_id,
            "queued": len(self._queue),
            "queued_offline": offline_count,
            "processing": self._current_job is not None,
            "current_job": self._current_job.job.id if self._current_job else None,
            "printer_online": self._printer_online,
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
    result = {
        "id": queued.job.id,
        "printer_id": queued.job.printer_id,
        "filename": queued.job.filename,
        "status": queued.status.value,
        "queued_at": queued.queued_at.isoformat(),
        "started_at": queued.started_at.isoformat() if queued.started_at else None,
        "completed_at": queued.completed_at.isoformat() if queued.completed_at else None,
        "error": queued.error,
    }

    # Include expiration for offline jobs
    if queued.expires_at:
        result["expires_at"] = queued.expires_at.isoformat()

    return result

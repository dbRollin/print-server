"""
Tests for USB resilience features.

Tests:
- USB error classification
- Offline queue support
- Job expiration
- Health monitor
"""

import asyncio
import pytest
from datetime import datetime, timedelta

from src.printers.usb_errors import (
    classify_usb_error,
    is_recoverable_error,
    USBErrorType
)
from src.printers.brother_ql_adapter import ResilienceConfig, USBDeviceState
from src.printers.base import PrintJob, PrintResult
from src.queue.manager import PrintQueue, QueuedJob, JobStatus, QueueFullError


class TestUSBErrorClassification:
    """Tests for USB error classification."""

    def test_errno_5_is_recoverable(self):
        """Errno 5 (I/O error) should be recoverable."""
        error = OSError(5, "Input/output error")
        assert classify_usb_error(error) == USBErrorType.RECOVERABLE
        assert is_recoverable_error(error)

    def test_errno_19_is_recoverable(self):
        """Errno 19 (no such device) should be recoverable."""
        error = OSError(19, "No such device")
        assert classify_usb_error(error) == USBErrorType.RECOVERABLE

    def test_errno_110_is_recoverable(self):
        """Errno 110 (connection timed out) should be recoverable."""
        error = OSError(110, "Connection timed out")
        assert classify_usb_error(error) == USBErrorType.RECOVERABLE

    def test_device_not_found_message_is_recoverable(self):
        """Error message containing 'device not found' should be recoverable."""
        error = Exception("USB device not found")
        assert classify_usb_error(error) == USBErrorType.RECOVERABLE

    def test_io_error_message_is_recoverable(self):
        """Error message containing 'i/o error' should be recoverable."""
        error = Exception("USB I/O error occurred")
        assert classify_usb_error(error) == USBErrorType.RECOVERABLE

    def test_generic_error_is_unknown(self):
        """Generic errors without USB indicators should be unknown."""
        error = ValueError("Some validation error")
        assert classify_usb_error(error) == USBErrorType.UNKNOWN
        assert not is_recoverable_error(error)

    def test_nested_exception_is_checked(self):
        """Nested exceptions with USB errors should be recoverable."""
        inner = OSError(5, "Input/output error")
        outer = Exception("Wrapper exception")
        outer.__cause__ = inner
        assert classify_usb_error(outer) == USBErrorType.RECOVERABLE


class TestResilienceConfig:
    """Tests for ResilienceConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = ResilienceConfig()
        assert config.auto_reconnect is True
        assert config.max_retries == 3
        assert config.retry_delay_ms == 1000
        assert config.health_check_interval_sec == 30.0
        assert config.offline_queue_enabled is True
        assert config.offline_queue_timeout_sec == 600.0

    def test_from_dict_with_custom_values(self):
        """Test loading config from dictionary."""
        config_dict = {
            "resilience": {
                "auto_reconnect": False,
                "max_retries": 5,
                "retry_delay_ms": 2000,
                "health_check_interval_sec": 60.0,
                "offline_queue_enabled": False,
                "offline_queue_timeout_sec": 300.0
            }
        }
        config = ResilienceConfig.from_dict(config_dict)
        assert config.auto_reconnect is False
        assert config.max_retries == 5
        assert config.retry_delay_ms == 2000
        assert config.offline_queue_enabled is False

    def test_from_dict_with_empty_dict(self):
        """Test loading config from empty dict uses defaults."""
        config = ResilienceConfig.from_dict({})
        assert config.auto_reconnect is True
        assert config.max_retries == 3

    def test_retry_delay_sec_property(self):
        """Test retry_delay_sec conversion."""
        config = ResilienceConfig(retry_delay_ms=2500)
        assert config.retry_delay_sec == 2.5


class TestUSBDeviceState:
    """Tests for USBDeviceState dataclass."""

    def test_default_state(self):
        """Test default device state."""
        state = USBDeviceState()
        assert state.is_connected is False
        assert state.last_seen is None
        assert state.last_error is None
        assert state.consecutive_failures == 0
        assert state.reconnect_attempts == 0


class TestOfflineQueue:
    """Tests for offline queue functionality."""

    @pytest.fixture
    def mock_print_handler(self):
        """Create a mock print handler."""
        async def handler(job: PrintJob) -> PrintResult:
            return PrintResult(success=True, job_id=job.id, message="OK")
        return handler

    @pytest.mark.asyncio
    async def test_add_offline_creates_queued_offline_job(self, mock_print_handler):
        """Test that add_offline creates a job with QUEUED_OFFLINE status."""
        queue = PrintQueue("test", mock_print_handler, offline_queue_timeout_sec=600)
        job = PrintJob(printer_id="test", filename="test.png", data=b"test")

        queued = await queue.add_offline(job)

        assert queued.status == JobStatus.QUEUED_OFFLINE
        assert queued.expires_at is not None
        assert queued.expires_at > datetime.now()

    @pytest.mark.asyncio
    async def test_add_offline_sets_expiration(self, mock_print_handler):
        """Test that offline jobs have correct expiration time."""
        timeout_sec = 300  # 5 minutes
        queue = PrintQueue("test", mock_print_handler, offline_queue_timeout_sec=timeout_sec)
        job = PrintJob(printer_id="test", filename="test.png", data=b"test")

        before = datetime.now()
        queued = await queue.add_offline(job)
        after = datetime.now()

        # Expiration should be ~5 minutes from now
        expected_min = before + timedelta(seconds=timeout_sec)
        expected_max = after + timedelta(seconds=timeout_sec)

        assert queued.expires_at >= expected_min
        assert queued.expires_at <= expected_max

    @pytest.mark.asyncio
    async def test_on_printer_online_promotes_offline_jobs(self, mock_print_handler):
        """Test that on_printer_online promotes QUEUED_OFFLINE to QUEUED."""
        queue = PrintQueue("test", mock_print_handler, offline_queue_timeout_sec=600)
        job = PrintJob(printer_id="test", filename="test.png", data=b"test")

        queued = await queue.add_offline(job)
        assert queued.status == JobStatus.QUEUED_OFFLINE

        promoted_count = await queue.on_printer_online()

        assert promoted_count == 1
        assert queued.status == JobStatus.QUEUED
        assert queued.expires_at is None  # Should be cleared

    @pytest.mark.asyncio
    async def test_set_printer_offline(self, mock_print_handler):
        """Test set_printer_offline updates queue state."""
        queue = PrintQueue("test", mock_print_handler)

        assert queue._printer_online is True
        queue.set_printer_offline()
        assert queue._printer_online is False

    @pytest.mark.asyncio
    async def test_queue_status_includes_offline_count(self, mock_print_handler):
        """Test that queue status includes offline job count."""
        queue = PrintQueue("test", mock_print_handler, offline_queue_timeout_sec=600)
        job1 = PrintJob(printer_id="test", filename="test1.png", data=b"test1")
        job2 = PrintJob(printer_id="test", filename="test2.png", data=b"test2")

        await queue.add_offline(job1)
        await queue.add_offline(job2)

        status = queue.get_status()
        assert status["queued"] == 2
        assert status["queued_offline"] == 2

    @pytest.mark.asyncio
    async def test_offline_jobs_not_processed_until_online(self, mock_print_handler):
        """Test that offline jobs are not processed until printer comes online."""
        processed = []

        async def tracking_handler(job: PrintJob) -> PrintResult:
            processed.append(job.id)
            return PrintResult(success=True, job_id=job.id, message="OK")

        queue = PrintQueue("test", tracking_handler, offline_queue_timeout_sec=600)
        job = PrintJob(printer_id="test", filename="test.png", data=b"test")

        await queue.add_offline(job)

        # Give some time for any processing to occur
        await asyncio.sleep(0.1)

        # Job should not be processed yet
        assert len(processed) == 0

        # Bring printer online
        await queue.on_printer_online()

        # Give time for processing
        await asyncio.sleep(0.1)

        # Now job should be processed
        assert len(processed) == 1
        assert job.id in processed


class TestJobExpiration:
    """Tests for job expiration functionality."""

    @pytest.mark.asyncio
    async def test_job_dict_includes_expires_at(self):
        """Test that job dict includes expires_at for offline jobs."""
        from src.queue.manager import _job_to_dict

        job = PrintJob(printer_id="test", filename="test.png", data=b"test")
        queued = QueuedJob(
            job=job,
            status=JobStatus.QUEUED_OFFLINE,
            expires_at=datetime.now() + timedelta(minutes=10)
        )

        result = _job_to_dict(queued)
        assert "expires_at" in result
        assert result["expires_at"] is not None

    @pytest.mark.asyncio
    async def test_regular_job_dict_no_expires_at(self):
        """Test that regular jobs don't have expires_at."""
        from src.queue.manager import _job_to_dict

        job = PrintJob(printer_id="test", filename="test.png", data=b"test")
        queued = QueuedJob(job=job, status=JobStatus.QUEUED)

        result = _job_to_dict(queued)
        assert "expires_at" not in result


class TestJobStatus:
    """Tests for extended job status values."""

    def test_queued_offline_status_exists(self):
        """Test that QUEUED_OFFLINE status exists."""
        assert JobStatus.QUEUED_OFFLINE.value == "queued_offline"

    def test_expired_status_exists(self):
        """Test that EXPIRED status exists."""
        assert JobStatus.EXPIRED.value == "expired"

    def test_all_statuses(self):
        """Test all job statuses are present."""
        statuses = [s.value for s in JobStatus]
        assert "queued" in statuses
        assert "queued_offline" in statuses
        assert "printing" in statuses
        assert "completed" in statuses
        assert "failed" in statuses
        assert "cancelled" in statuses
        assert "expired" in statuses

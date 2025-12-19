"""
Brother QL-series label printer adapter with USB resilience.

Requires: brother_ql package
Hardware: Brother QL-720NW, QL-800, QL-810W, QL-820NWB, etc.
Connection: USB (typically usb://0x04f9:0x2044 format)

Resilience features:
- Automatic USB reconnection on I/O errors
- Retry logic with configurable attempts and backoff
- Actual device status probing (not cached)
- Event logging for connection state changes
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from typing import Optional

from .base import PrinterBase, PrinterStatus, PrintJob, PrintResult
from .usb_errors import USBErrorType, classify_usb_error

logger = logging.getLogger(__name__)

# Pillow 10+ compatibility fix for brother_ql
# ANTIALIAS was removed in Pillow 10, replaced with Resampling.LANCZOS
from PIL import Image

if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

# Import brother_ql only when actually used
# This allows the module to be imported even without brother_ql installed
try:
    from brother_ql.backends.helpers import discover, send
    from brother_ql.conversion import convert
    from brother_ql.raster import BrotherQLRaster
    BROTHER_QL_AVAILABLE = True
except ImportError:
    BROTHER_QL_AVAILABLE = False
    logger.warning("brother_ql package not available - BrotherQLAdapter will not function")


@dataclass
class USBDeviceState:
    """Tracks USB device connection state."""

    is_connected: bool = False
    last_seen: Optional[datetime] = None
    last_error: Optional[str] = None
    consecutive_failures: int = 0
    reconnect_attempts: int = 0


@dataclass
class ResilienceConfig:
    """USB resilience configuration."""

    auto_reconnect: bool = True
    max_retries: int = 3
    retry_delay_ms: int = 1000
    health_check_interval_sec: float = 30.0
    offline_queue_enabled: bool = True
    offline_queue_timeout_sec: float = 600.0

    @classmethod
    def from_dict(cls, config: dict) -> "ResilienceConfig":
        """Create from config dictionary."""
        resilience = config.get("resilience", {})
        return cls(
            auto_reconnect=resilience.get("auto_reconnect", True),
            max_retries=resilience.get("max_retries", 3),
            retry_delay_ms=resilience.get("retry_delay_ms", 1000),
            health_check_interval_sec=resilience.get("health_check_interval_sec", 30.0),
            offline_queue_enabled=resilience.get("offline_queue_enabled", True),
            offline_queue_timeout_sec=resilience.get("offline_queue_timeout_sec", 600.0),
        )

    @property
    def retry_delay_sec(self) -> float:
        """Get retry delay in seconds."""
        return self.retry_delay_ms / 1000.0


class BrotherQLAdapter(PrinterBase):
    """
    Adapter for Brother QL-series label printers with USB resilience.

    Config options:
        model: Printer model (e.g., "QL-720NW")
        device: Device path (e.g., "usb://0x04f9:0x2044" or "/dev/usb/lp0")
        label: Label type (e.g., "62" for 62mm continuous)
        resilience: Optional resilience configuration dict
    """

    def __init__(self, printer_id: str, name: str, config: dict):
        super().__init__(printer_id, name, config)
        self.model = config.get("model", "QL-720NW")
        self.device = config.get("device", "")
        self.label = config.get("label", "62")  # 62mm continuous tape

        # Resilience configuration
        self.resilience = ResilienceConfig.from_dict(config)

        # USB device state tracking
        self._device_state = USBDeviceState()
        self._lock = asyncio.Lock()  # Protect device access during print/reconnect

        # Initial status based on device configuration
        if not self.device:
            self._device_state.is_connected = False
        else:
            # Will be verified on first status check
            self._device_state.is_connected = True

    @property
    def supported_content_types(self) -> list[str]:
        return ["image/png"]

    @property
    def device_state(self) -> USBDeviceState:
        """Expose device state for status API."""
        return self._device_state

    async def get_status(self) -> PrinterStatus:
        """
        Get actual printer status by probing the USB device.

        This replaces the old cached status implementation.
        """
        if not BROTHER_QL_AVAILABLE:
            return PrinterStatus.ERROR

        if not self.device:
            return PrinterStatus.OFFLINE

        # Actually probe the device
        try:
            is_accessible = await self._probe_device()
            if is_accessible:
                self._device_state.is_connected = True
                self._device_state.last_seen = datetime.now()
                self._device_state.consecutive_failures = 0
                return PrinterStatus.READY
            else:
                self._device_state.is_connected = False
                return PrinterStatus.OFFLINE
        except Exception as e:
            logger.warning(f"Device probe failed for {self.printer_id}: {e}")
            self._device_state.is_connected = False
            self._device_state.last_error = str(e)
            return PrinterStatus.OFFLINE

    async def _probe_device(self) -> bool:
        """
        Check if USB device is accessible.

        Uses brother_ql discover to enumerate available devices.
        """
        if not BROTHER_QL_AVAILABLE:
            return False

        try:
            # Run discovery in executor to avoid blocking
            loop = asyncio.get_event_loop()
            devices = await loop.run_in_executor(
                None,
                lambda: discover(backend_identifier="pyusb")
            )

            # Check if our configured device is in the list
            for device_info in devices:
                device_id = device_info.get("identifier", "")
                if device_id == self.device:
                    return True

                # Also check if device matches by stripping protocol prefix
                if self.device.startswith("usb://") and device_id == self.device:
                    return True

            return False

        except Exception as e:
            logger.debug(f"Device discovery failed: {e}")
            return False

    def validate_job(self, job: PrintJob) -> tuple[bool, str]:
        if not BROTHER_QL_AVAILABLE:
            return False, "brother_ql package not installed"
        if job.content_type not in self.supported_content_types:
            return False, f"Unsupported content type: {job.content_type}"
        if not job.data:
            return False, "No data provided"
        return True, ""

    async def print(self, job: PrintJob) -> PrintResult:
        """
        Print with automatic retry on USB errors.
        """
        if not BROTHER_QL_AVAILABLE:
            return PrintResult(
                success=False,
                job_id=job.id,
                message="brother_ql package not installed",
                error_code="MISSING_DEPENDENCY"
            )

        if not self.device:
            return PrintResult(
                success=False,
                job_id=job.id,
                message="No device configured",
                error_code="NO_DEVICE"
            )

        # Use retry wrapper if auto_reconnect is enabled
        if self.resilience.auto_reconnect:
            return await self._print_with_retry(job)
        else:
            return await self._do_print(job)

    async def _print_with_retry(self, job: PrintJob) -> PrintResult:
        """
        Execute print with automatic retry on USB errors.
        """
        last_error: Optional[Exception] = None

        for attempt in range(self.resilience.max_retries):
            try:
                async with self._lock:
                    result = await self._do_print(job)
                    if result.success:
                        self._device_state.consecutive_failures = 0
                        return result
                    else:
                        # Print returned failure but didn't raise - don't retry
                        return result

            except Exception as e:
                last_error = e
                error_type = classify_usb_error(e)
                self._device_state.consecutive_failures += 1

                if error_type == USBErrorType.RECOVERABLE:
                    logger.warning(
                        f"[JOB_RETRY] USB error on attempt {attempt + 1}/{self.resilience.max_retries} "
                        f"for job {job.id}: {e}"
                    )
                    self._device_state.last_error = str(e)

                    # Try to reconnect before next attempt
                    if attempt < self.resilience.max_retries - 1:
                        reconnected = await self._attempt_reconnect()
                        if reconnected:
                            logger.info(f"Reconnected, retrying job {job.id}")
                        await asyncio.sleep(self.resilience.retry_delay_sec)
                else:
                    # Non-recoverable error, fail immediately
                    logger.error(f"Non-recoverable print error for job {job.id}: {e}")
                    break

        # All retries exhausted
        self._device_state.is_connected = False
        self._emit_event("USB_RECONNECT_FAILED", str(last_error))

        return PrintResult(
            success=False,
            job_id=job.id,
            message=f"Print failed after {self.resilience.max_retries} attempts: {last_error}",
            error_code="USB_ERROR"
        )

    async def _do_print(self, job: PrintJob) -> PrintResult:
        """
        Execute the actual print operation.
        """
        try:
            # Convert image data to brother_ql raster format
            qlr = BrotherQLRaster(self.model)

            image = Image.open(BytesIO(job.data))

            # Run conversion in executor (CPU-bound)
            loop = asyncio.get_event_loop()
            instructions = await loop.run_in_executor(
                None,
                lambda: convert(
                    qlr=qlr,
                    images=[image],
                    label=self.label,
                    rotate="0",
                    threshold=70,
                    dither=False,
                    compress=False,
                    red=False,
                    dpi_600=False,
                    hq=True,
                    cut=True
                )
            )

            # Send to printer (I/O bound, run in executor)
            await loop.run_in_executor(
                None,
                lambda: send(
                    instructions=instructions,
                    printer_identifier=self.device,
                    backend_identifier="pyusb",
                    blocking=True
                )
            )

            # Update state on success
            self._device_state.is_connected = True
            self._device_state.last_seen = datetime.now()
            self._device_state.last_error = None

            logger.info(f"Printed label job {job.id} to {self.device}")
            return PrintResult(success=True, job_id=job.id, message="Print completed")

        except Exception as e:
            logger.error(f"Print failed for job {job.id}: {e}")
            # Re-raise to let retry wrapper handle it
            raise

    async def _attempt_reconnect(self) -> bool:
        """
        Attempt to rediscover and reconnect to USB device.

        Returns True if device was found, False otherwise.
        """
        self._device_state.reconnect_attempts += 1
        logger.info(
            f"[USB_RECONNECT] Attempting USB reconnect for {self.printer_id} "
            f"(attempt {self._device_state.reconnect_attempts})"
        )

        self._emit_event("USB_DISCONNECTED", self.device)

        if not BROTHER_QL_AVAILABLE:
            return False

        try:
            # Run discovery in executor
            loop = asyncio.get_event_loop()
            devices = await loop.run_in_executor(
                None,
                lambda: discover(backend_identifier="pyusb")
            )

            if not devices:
                logger.warning("No Brother QL devices found during reconnect")
                return False

            # Look for our configured device
            for device_info in devices:
                device_id = device_info.get("identifier", "")
                if device_id == self.device:
                    self._device_state.is_connected = True
                    self._device_state.last_seen = datetime.now()
                    self._emit_event("USB_RECONNECTED", self.device)
                    logger.info(f"[USB_RECONNECTED] Device {self.device} reconnected")
                    return True

            # If device path changed (common after USB re-enumeration),
            # and only one device found, use it
            if len(devices) == 1:
                new_device = devices[0].get("identifier", "")
                if new_device:
                    logger.info(
                        f"[USB_RECONNECTED] Device path changed: {self.device} -> {new_device}"
                    )
                    self.device = new_device
                    self._device_state.is_connected = True
                    self._device_state.last_seen = datetime.now()
                    self._emit_event("USB_RECONNECTED", new_device)
                    return True

            logger.warning(
                f"Configured device {self.device} not found. "
                f"Available: {[d.get('identifier') for d in devices]}"
            )
            return False

        except Exception as e:
            logger.error(f"Reconnect failed: {e}")
            self._device_state.last_error = str(e)
            return False

    def _emit_event(self, event_type: str, detail: str) -> None:
        """
        Log a connection event.

        Events:
        - USB_DISCONNECTED: Device lost
        - USB_RECONNECTED: Device found again
        - USB_RECONNECT_FAILED: Couldn't recover after retries
        """
        logger.info(f"[EVENT] {event_type}: printer={self.printer_id} detail={detail}")

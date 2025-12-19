"""
Background health monitor for USB printers.

Periodically checks printer status and detects connection changes.
Triggers callbacks when printers go offline or come back online.
"""

import asyncio
import logging
from typing import Awaitable, Callable, Optional

from src.printers import PrinterRegistry
from src.printers.base import PrinterBase, PrinterStatus

logger = logging.getLogger(__name__)


# Type alias for status change callback
StatusChangeCallback = Callable[
    [str, Optional[PrinterStatus], PrinterStatus],
    Awaitable[None]
]


class HealthMonitor:
    """
    Background task that monitors USB printer health.

    Features:
    - Periodic status polling for all registered printers
    - Detects status transitions (online → offline, offline → online)
    - Fires callback on status changes to enable queue processing
    - Configurable check interval
    """

    def __init__(
        self,
        registry: PrinterRegistry,
        on_status_change: Optional[StatusChangeCallback] = None,
        default_interval_sec: float = 30.0
    ):
        """
        Initialize the health monitor.

        Args:
            registry: PrinterRegistry containing printers to monitor
            on_status_change: Async callback called when printer status changes.
                              Signature: (printer_id, old_status, new_status) -> None
            default_interval_sec: How often to check printer status (default 30s)
        """
        self.registry = registry
        self.on_status_change = on_status_change
        self.default_interval_sec = default_interval_sec

        self._task: Optional[asyncio.Task] = None
        self._running = False
        self._last_status: dict[str, PrinterStatus] = {}

    async def start(self) -> None:
        """Start the health monitor background task."""
        if self._running:
            logger.warning("Health monitor already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info(
            f"Health monitor started (interval: {self.default_interval_sec}s)"
        )

    async def stop(self) -> None:
        """Stop the health monitor."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Health monitor stopped")

    @property
    def is_running(self) -> bool:
        """Check if monitor is currently running."""
        return self._running

    def get_last_status(self, printer_id: str) -> Optional[PrinterStatus]:
        """Get the last known status for a printer."""
        return self._last_status.get(printer_id)

    async def check_now(self) -> dict[str, PrinterStatus]:
        """
        Perform an immediate status check of all printers.

        Returns dict of printer_id -> current status.
        """
        return await self._check_all_printers()

    async def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        # Do initial check immediately
        try:
            await self._check_all_printers()
        except Exception as e:
            logger.error(f"Initial health check failed: {e}")

        while self._running:
            try:
                await asyncio.sleep(self.default_interval_sec)
                if self._running:  # Check again after sleep
                    await self._check_all_printers()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error: {e}")

    async def _check_all_printers(self) -> dict[str, PrinterStatus]:
        """
        Check status of all printers and detect changes.

        Returns dict of current statuses.
        """
        current_statuses: dict[str, PrinterStatus] = {}

        for printer in self.registry.list_all():
            try:
                current_status = await printer.get_status()
                current_statuses[printer.printer_id] = current_status

                previous_status = self._last_status.get(printer.printer_id)

                if previous_status != current_status:
                    await self._handle_status_change(
                        printer, previous_status, current_status
                    )

                self._last_status[printer.printer_id] = current_status

            except Exception as e:
                logger.error(f"Failed to check status for {printer.printer_id}: {e}")
                # Don't update last_status on error - preserve previous state

        return current_statuses

    async def _handle_status_change(
        self,
        printer: PrinterBase,
        old_status: Optional[PrinterStatus],
        new_status: PrinterStatus
    ) -> None:
        """Handle printer status change."""
        printer_id = printer.printer_id

        if old_status is None:
            logger.info(
                f"[HEALTH] Printer {printer_id}: initial status = {new_status.value}"
            )
        else:
            logger.info(
                f"[HEALTH] Printer {printer_id}: {old_status.value} -> {new_status.value}"
            )

        # Emit specific events based on transition
        if new_status == PrinterStatus.OFFLINE:
            self._emit_event("USB_DISCONNECTED", printer_id)
        elif (old_status == PrinterStatus.OFFLINE and
              new_status in (PrinterStatus.READY, PrinterStatus.BUSY)):
            self._emit_event("USB_RECONNECTED", printer_id)

        # Fire callback for external handling (e.g., queue processing)
        if self.on_status_change:
            try:
                await self.on_status_change(printer_id, old_status, new_status)
            except Exception as e:
                logger.error(f"Status change callback failed: {e}")

    def _emit_event(self, event_type: str, printer_id: str) -> None:
        """Log a connection event."""
        logger.info(f"[EVENT] {event_type}: printer={printer_id}")

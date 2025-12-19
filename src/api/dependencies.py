"""
Dependency injection for API routes.

These are set up during app initialization.
"""

from typing import Awaitable, Callable, Optional

from src.printers import PrinterRegistry
from src.printers.base import PrintJob, PrintResult
from src.queue import PrintQueue
from src.routing import PrintRouter

# Global instances (set during app init)
_printer_registry: Optional[PrinterRegistry] = None
_queue_manager: Optional["QueueManager"] = None
_router: Optional[PrintRouter] = None


class QueueManager:
    """Manages print queues for all printers."""

    def __init__(self):
        self._queues: dict[str, PrintQueue] = {}

    def get_queue(self, printer_id: str) -> Optional[PrintQueue]:
        return self._queues.get(printer_id)

    def get_or_create_queue(
        self,
        printer_id: str,
        print_handler: Callable[[PrintJob], Awaitable[PrintResult]]
    ) -> PrintQueue:
        if printer_id not in self._queues:
            self._queues[printer_id] = PrintQueue(printer_id, print_handler)
        return self._queues[printer_id]

    def get_all_queues(self) -> dict[str, PrintQueue]:
        return self._queues


def init_dependencies(
    registry: PrinterRegistry,
    queue_manager: QueueManager,
    router: PrintRouter
):
    """Initialize global dependencies."""
    global _printer_registry, _queue_manager, _router
    _printer_registry = registry
    _queue_manager = queue_manager
    _router = router


def get_printer_registry() -> PrinterRegistry:
    """Get printer registry instance."""
    if _printer_registry is None:
        raise RuntimeError("Printer registry not initialized")
    return _printer_registry


def get_queue_manager() -> QueueManager:
    """Get queue manager instance."""
    if _queue_manager is None:
        raise RuntimeError("Queue manager not initialized")
    return _queue_manager


def get_router() -> PrintRouter:
    """Get print router instance."""
    if _router is None:
        raise RuntimeError("Router not initialized")
    return _router

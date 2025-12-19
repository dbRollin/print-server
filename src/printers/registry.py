from typing import Optional

from .base import PrinterBase, PrinterStatus


class PrinterRegistry:
    """Registry for managing multiple printer adapters."""

    def __init__(self):
        self._printers: dict[str, PrinterBase] = {}

    def register(self, printer: PrinterBase) -> None:
        """Register a printer adapter."""
        self._printers[printer.printer_id] = printer

    def get(self, printer_id: str) -> Optional[PrinterBase]:
        """Get a printer by ID."""
        return self._printers.get(printer_id)

    def list_all(self) -> list[PrinterBase]:
        """List all registered printers."""
        return list(self._printers.values())

    async def get_all_status(self) -> dict[str, PrinterStatus]:
        """Get status of all printers."""
        statuses = {}
        for printer_id, printer in self._printers.items():
            statuses[printer_id] = await printer.get_status()
        return statuses

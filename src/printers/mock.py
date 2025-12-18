import asyncio
import logging
from .base import PrinterBase, PrintJob, PrintResult, PrinterStatus

logger = logging.getLogger(__name__)


class MockLabelPrinter(PrinterBase):
    """Mock label printer for testing without hardware."""

    def __init__(self, printer_id: str = "mock-label", name: str = "Mock Label Printer", config: dict = None):
        super().__init__(printer_id, name, config or {})
        self._status = PrinterStatus.READY
        self._print_delay = config.get("print_delay", 0.5) if config else 0.5
        self._fail_rate = config.get("fail_rate", 0.0) if config else 0.0  # For testing error handling

    @property
    def supported_content_types(self) -> list[str]:
        return ["image/png"]

    async def get_status(self) -> PrinterStatus:
        return self._status

    def set_status(self, status: PrinterStatus) -> None:
        """Allow tests to set printer status."""
        self._status = status

    def validate_job(self, job: PrintJob) -> tuple[bool, str]:
        if job.content_type not in self.supported_content_types:
            return False, f"Unsupported content type: {job.content_type}"
        if not job.data:
            return False, "No data provided"
        return True, ""

    async def print(self, job: PrintJob) -> PrintResult:
        if self._status != PrinterStatus.READY:
            return PrintResult(
                success=False,
                job_id=job.id,
                message=f"Printer not ready: {self._status.value}",
                error_code="PRINTER_NOT_READY"
            )

        # Simulate print time
        self._status = PrinterStatus.BUSY
        await asyncio.sleep(self._print_delay)
        self._status = PrinterStatus.READY

        logger.info(f"[MOCK] Printed label job {job.id}: {job.filename} ({len(job.data)} bytes)")

        return PrintResult(
            success=True,
            job_id=job.id,
            message="Print job completed (mock)"
        )


class MockDocumentPrinter(PrinterBase):
    """Mock document printer for testing without hardware."""

    def __init__(self, printer_id: str = "mock-document", name: str = "Mock Document Printer", config: dict = None):
        super().__init__(printer_id, name, config or {})
        self._status = PrinterStatus.READY
        self._print_delay = config.get("print_delay", 1.0) if config else 1.0

    @property
    def supported_content_types(self) -> list[str]:
        return ["application/pdf"]

    async def get_status(self) -> PrinterStatus:
        return self._status

    def set_status(self, status: PrinterStatus) -> None:
        """Allow tests to set printer status."""
        self._status = status

    def validate_job(self, job: PrintJob) -> tuple[bool, str]:
        if job.content_type not in self.supported_content_types:
            return False, f"Unsupported content type: {job.content_type}"
        if not job.data:
            return False, "No data provided"
        return True, ""

    async def print(self, job: PrintJob) -> PrintResult:
        if self._status != PrinterStatus.READY:
            return PrintResult(
                success=False,
                job_id=job.id,
                message=f"Printer not ready: {self._status.value}",
                error_code="PRINTER_NOT_READY"
            )

        self._status = PrinterStatus.BUSY
        await asyncio.sleep(self._print_delay)
        self._status = PrinterStatus.READY

        logger.info(f"[MOCK] Printed document job {job.id}: {job.filename} ({len(job.data)} bytes)")

        return PrintResult(
            success=True,
            job_id=job.id,
            message="Print job completed (mock)"
        )

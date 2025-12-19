"""
CUPS printer adapter for document printing.

Requires: pycups package
Works with any CUPS-configured printer (network or local).
"""

import logging
import os
import tempfile

from .base import PrinterBase, PrinterStatus, PrintJob, PrintResult

logger = logging.getLogger(__name__)

try:
    import cups
    CUPS_AVAILABLE = True
except ImportError:
    CUPS_AVAILABLE = False
    logger.warning("pycups package not available - CUPSAdapter will not function")


class CUPSAdapter(PrinterBase):
    """
    Adapter for CUPS-managed printers.

    Config options:
        cups_name: CUPS printer name (as shown in `lpstat -p`)
        cups_server: CUPS server address (default: localhost)
    """

    def __init__(self, printer_id: str, name: str, config: dict):
        super().__init__(printer_id, name, config)
        self.cups_name = config.get("cups_name", "")
        self.cups_server = config.get("cups_server", "localhost")
        self._conn = None

    def _get_connection(self):
        """Get or create CUPS connection."""
        if not CUPS_AVAILABLE:
            return None
        if self._conn is None:
            if self.cups_server != "localhost":
                cups.setServer(self.cups_server)
            self._conn = cups.Connection()
        return self._conn

    @property
    def supported_content_types(self) -> list[str]:
        return ["application/pdf"]

    async def get_status(self) -> PrinterStatus:
        if not CUPS_AVAILABLE:
            return PrinterStatus.ERROR
        if not self.cups_name:
            return PrinterStatus.OFFLINE

        try:
            conn = self._get_connection()
            printers = conn.getPrinters()

            if self.cups_name not in printers:
                return PrinterStatus.OFFLINE

            printer_info = printers[self.cups_name]
            state = printer_info.get("printer-state", 0)

            # CUPS states: 3=idle, 4=printing, 5=stopped
            if state == 3:
                return PrinterStatus.READY
            elif state == 4:
                return PrinterStatus.BUSY
            else:
                return PrinterStatus.OFFLINE

        except Exception as e:
            logger.error(f"Failed to get CUPS status: {e}")
            return PrinterStatus.ERROR

    def validate_job(self, job: PrintJob) -> tuple[bool, str]:
        if not CUPS_AVAILABLE:
            return False, "pycups package not installed"
        if job.content_type not in self.supported_content_types:
            return False, f"Unsupported content type: {job.content_type}"
        if not job.data:
            return False, "No data provided"
        if not self.cups_name:
            return False, "No CUPS printer configured"
        return True, ""

    async def print(self, job: PrintJob) -> PrintResult:
        if not CUPS_AVAILABLE:
            return PrintResult(
                success=False,
                job_id=job.id,
                message="pycups package not installed",
                error_code="MISSING_DEPENDENCY"
            )

        if not self.cups_name:
            return PrintResult(
                success=False,
                job_id=job.id,
                message="No CUPS printer configured",
                error_code="NO_PRINTER"
            )

        try:
            conn = self._get_connection()

            # CUPS requires a file path, so we write to temp file
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
                f.write(job.data)
                temp_path = f.name

            try:
                # Build print options
                options = {}
                if job.copies > 1:
                    options["copies"] = str(job.copies)

                # Submit job
                cups_job_id = conn.printFile(
                    self.cups_name,
                    temp_path,
                    job.filename or "document",
                    options
                )

                logger.info(f"Submitted job {job.id} to CUPS as job {cups_job_id}")

                return PrintResult(
                    success=True,
                    job_id=job.id,
                    message=f"Submitted to CUPS (job {cups_job_id})"
                )

            finally:
                # Clean up temp file
                os.unlink(temp_path)

        except Exception as e:
            logger.error(f"CUPS print failed for job {job.id}: {e}")
            return PrintResult(
                success=False,
                job_id=job.id,
                message=str(e),
                error_code="PRINT_ERROR"
            )

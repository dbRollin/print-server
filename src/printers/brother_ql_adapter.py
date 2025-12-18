"""
Brother QL-series label printer adapter.

Requires: brother_ql package
Hardware: Brother QL-720NW, QL-800, QL-810W, QL-820NWB, etc.
Connection: USB (typically /dev/usb/lp0 or similar)
"""

import logging
from typing import Optional
from .base import PrinterBase, PrintJob, PrintResult, PrinterStatus

logger = logging.getLogger(__name__)

# Pillow 10+ compatibility fix for brother_ql
# ANTIALIAS was removed in Pillow 10, replaced with Resampling.LANCZOS
from PIL import Image
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

# Import brother_ql only when actually used
# This allows the module to be imported even without brother_ql installed
try:
    from brother_ql.raster import BrotherQLRaster
    from brother_ql.backends.helpers import send
    from brother_ql.conversion import convert
    BROTHER_QL_AVAILABLE = True
except ImportError:
    BROTHER_QL_AVAILABLE = False
    logger.warning("brother_ql package not available - BrotherQLAdapter will not function")


class BrotherQLAdapter(PrinterBase):
    """
    Adapter for Brother QL-series label printers.

    Config options:
        model: Printer model (e.g., "QL-720NW")
        device: Device path (e.g., "usb://0x04f9:0x2044" or "/dev/usb/lp0")
        label: Label type (e.g., "62" for 62mm continuous)
    """

    def __init__(self, printer_id: str, name: str, config: dict):
        super().__init__(printer_id, name, config)
        self.model = config.get("model", "QL-720NW")
        self.device = config.get("device", "")
        self.label = config.get("label", "62")  # 62mm continuous tape
        self._status = PrinterStatus.OFFLINE if not self.device else PrinterStatus.READY

    @property
    def supported_content_types(self) -> list[str]:
        return ["image/png"]

    async def get_status(self) -> PrinterStatus:
        if not BROTHER_QL_AVAILABLE:
            return PrinterStatus.ERROR
        if not self.device:
            return PrinterStatus.OFFLINE
        # TODO: Implement actual device status check
        return self._status

    def validate_job(self, job: PrintJob) -> tuple[bool, str]:
        if not BROTHER_QL_AVAILABLE:
            return False, "brother_ql package not installed"
        if job.content_type not in self.supported_content_types:
            return False, f"Unsupported content type: {job.content_type}"
        if not job.data:
            return False, "No data provided"
        return True, ""

    async def print(self, job: PrintJob) -> PrintResult:
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

        try:
            # Convert image data to brother_ql raster format
            qlr = BrotherQLRaster(self.model)

            # The image data needs to be saved temporarily or passed as PIL Image
            # This is a simplified implementation - real usage would need PIL
            from io import BytesIO
            from PIL import Image

            image = Image.open(BytesIO(job.data))

            instructions = convert(
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

            # Send to printer
            send(
                instructions=instructions,
                printer_identifier=self.device,
                backend_identifier="pyusb",  # or "linux_kernel" depending on setup
                blocking=True
            )

            logger.info(f"Printed label job {job.id} to {self.device}")
            return PrintResult(success=True, job_id=job.id, message="Print completed")

        except Exception as e:
            logger.error(f"Print failed for job {job.id}: {e}")
            return PrintResult(
                success=False,
                job_id=job.id,
                message=str(e),
                error_code="PRINT_ERROR"
            )

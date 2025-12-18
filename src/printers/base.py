from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from datetime import datetime
import uuid


class PrinterStatus(Enum):
    READY = "ready"
    BUSY = "busy"
    OFFLINE = "offline"
    ERROR = "error"


@dataclass
class PrintJob:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    printer_id: str = ""
    filename: str = ""
    data: bytes = b""
    content_type: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    copies: int = 1
    options: dict = field(default_factory=dict)


@dataclass
class PrintResult:
    success: bool
    job_id: str
    message: str = ""
    error_code: Optional[str] = None


class PrinterBase(ABC):
    """Abstract base class for all printer adapters."""

    def __init__(self, printer_id: str, name: str, config: dict):
        self.printer_id = printer_id
        self.name = name
        self.config = config

    @abstractmethod
    async def get_status(self) -> PrinterStatus:
        """Check if printer is ready."""
        pass

    @abstractmethod
    async def print(self, job: PrintJob) -> PrintResult:
        """Send a print job to the printer."""
        pass

    @abstractmethod
    def validate_job(self, job: PrintJob) -> tuple[bool, str]:
        """Validate a job before queuing. Returns (is_valid, error_message)."""
        pass

    @property
    @abstractmethod
    def supported_content_types(self) -> list[str]:
        """List of MIME types this printer accepts."""
        pass

    def to_dict(self) -> dict:
        """Return printer info as dict for API responses."""
        return {
            "id": self.printer_id,
            "name": self.name,
            "supported_types": self.supported_content_types,
        }

"""
Document validation for document printing.

Basic PDF validation - ensures the file is actually a PDF.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class DocumentValidationResult:
    valid: bool
    page_count: Optional[int] = None
    error: Optional[str] = None
    error_code: Optional[str] = None


def validate_pdf(data: bytes) -> DocumentValidationResult:
    """
    Validate PDF document.

    Currently performs basic header check. Can be extended with
    pypdf or similar for page count and deeper validation.

    Args:
        data: Raw PDF bytes

    Returns:
        DocumentValidationResult with validation details
    """
    if not data:
        return DocumentValidationResult(
            valid=False,
            error="No data provided",
            error_code="EMPTY_DATA"
        )

    # Check PDF magic bytes
    if not data.startswith(b"%PDF"):
        return DocumentValidationResult(
            valid=False,
            error="File does not appear to be a PDF",
            error_code="INVALID_FORMAT"
        )

    # Optional: use pypdf for deeper validation
    page_count = None
    try:
        from io import BytesIO

        from pypdf import PdfReader

        reader = PdfReader(BytesIO(data))
        page_count = len(reader.pages)
    except ImportError:
        # pypdf not available, skip page count
        pass
    except Exception as e:
        return DocumentValidationResult(
            valid=False,
            error=f"Invalid PDF: {e}",
            error_code="CORRUPT_PDF"
        )

    return DocumentValidationResult(
        valid=True,
        page_count=page_count
    )

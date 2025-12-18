"""
Image validation for label printing.

Per spec requirements:
- Must be PNG format
- Must be exactly 720px wide (for QL-720 at 300 DPI on 62mm tape)
- Must be monochrome (black #000000 and white #FFFFFF only)
- Height is variable
"""

from dataclasses import dataclass
from io import BytesIO
from typing import Optional
from PIL import Image


class ImageValidationError(Exception):
    """Raised when image validation fails."""

    def __init__(self, message: str, code: str):
        super().__init__(message)
        self.code = code


@dataclass
class ImageValidationResult:
    valid: bool
    width: int = 0
    height: int = 0
    mode: str = ""
    error: Optional[str] = None
    error_code: Optional[str] = None


@dataclass
class LabelImageConfig:
    """Configuration for label image validation."""

    required_width: int = 720
    require_monochrome: bool = True
    allowed_formats: tuple = ("PNG",)
    # Tolerance for "near-black" and "near-white" pixels (0 = strict)
    monochrome_tolerance: int = 0


def validate_label_image(
    data: bytes,
    config: Optional[LabelImageConfig] = None
) -> ImageValidationResult:
    """
    Validate an image for label printing.

    Args:
        data: Raw image bytes
        config: Validation configuration (uses defaults if None)

    Returns:
        ImageValidationResult with validation details
    """
    if config is None:
        config = LabelImageConfig()

    try:
        image = Image.open(BytesIO(data))
    except Exception as e:
        return ImageValidationResult(
            valid=False,
            error=f"Cannot read image: {e}",
            error_code="INVALID_IMAGE"
        )

    # Check format
    if image.format not in config.allowed_formats:
        return ImageValidationResult(
            valid=False,
            width=image.width,
            height=image.height,
            mode=image.mode,
            error=f"Invalid format: {image.format}. Required: {config.allowed_formats}",
            error_code="INVALID_FORMAT"
        )

    # Check width
    if image.width != config.required_width:
        return ImageValidationResult(
            valid=False,
            width=image.width,
            height=image.height,
            mode=image.mode,
            error=f"Invalid width: {image.width}px. Required: {config.required_width}px",
            error_code="INVALID_WIDTH"
        )

    # Check monochrome if required
    if config.require_monochrome:
        is_mono, mono_error = _check_monochrome(image, config.monochrome_tolerance)
        if not is_mono:
            return ImageValidationResult(
                valid=False,
                width=image.width,
                height=image.height,
                mode=image.mode,
                error=mono_error,
                error_code="NOT_MONOCHROME"
            )

    return ImageValidationResult(
        valid=True,
        width=image.width,
        height=image.height,
        mode=image.mode
    )


def _check_monochrome(image: Image.Image, tolerance: int = 0) -> tuple[bool, str]:
    """
    Check if image is strictly black and white.

    Returns:
        Tuple of (is_monochrome, error_message)
    """
    # Convert to RGB if necessary for consistent checking
    if image.mode == "1":
        # Already 1-bit, definitely monochrome
        return True, ""

    if image.mode in ("L", "LA"):
        # Grayscale - check for values other than 0 and 255
        pixels = list(image.getdata())
        if image.mode == "LA":
            pixels = [p[0] for p in pixels]  # Extract luminance from LA

        for pixel in pixels:
            if tolerance == 0:
                if pixel not in (0, 255):
                    return False, f"Image contains grayscale values (found {pixel})"
            else:
                if not (pixel <= tolerance or pixel >= 255 - tolerance):
                    return False, f"Image contains grayscale values (found {pixel})"
        return True, ""

    if image.mode in ("RGB", "RGBA"):
        pixels = list(image.getdata())

        for pixel in pixels:
            r, g, b = pixel[:3]
            if tolerance == 0:
                is_black = (r == 0 and g == 0 and b == 0)
                is_white = (r == 255 and g == 255 and b == 255)
            else:
                is_black = (r <= tolerance and g <= tolerance and b <= tolerance)
                is_white = (r >= 255 - tolerance and g >= 255 - tolerance and b >= 255 - tolerance)

            if not (is_black or is_white):
                return False, f"Image contains non-monochrome pixels (found RGB {r},{g},{b})"

        return True, ""

    if image.mode == "P":
        # Palette mode - check palette entries
        rgb_image = image.convert("RGB")
        return _check_monochrome(rgb_image, tolerance)

    return False, f"Unsupported image mode: {image.mode}"


def get_image_info(data: bytes) -> dict:
    """Get basic info about an image without full validation."""
    try:
        image = Image.open(BytesIO(data))
        return {
            "width": image.width,
            "height": image.height,
            "format": image.format,
            "mode": image.mode,
        }
    except Exception as e:
        return {"error": str(e)}

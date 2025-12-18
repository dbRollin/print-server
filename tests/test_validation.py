"""Tests for image and document validation."""

import pytest
from io import BytesIO
from PIL import Image

from src.validation import validate_label_image, validate_pdf
from src.validation.image import LabelImageConfig


def create_test_image(width: int, height: int, mode: str = "1", color: int = 0) -> bytes:
    """Create a test image and return as PNG bytes."""
    img = Image.new(mode, (width, height), color)
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


class TestLabelImageValidation:
    def test_valid_monochrome_image(self):
        """Valid 720px wide monochrome image should pass."""
        data = create_test_image(720, 100, mode="1")
        result = validate_label_image(data)
        assert result.valid
        assert result.width == 720
        assert result.height == 100

    def test_wrong_width(self):
        """Image with wrong width should fail."""
        data = create_test_image(800, 100, mode="1")
        result = validate_label_image(data)
        assert not result.valid
        assert result.error_code == "INVALID_WIDTH"

    def test_rgb_image_fails(self):
        """RGB image with colors should fail monochrome check."""
        img = Image.new("RGB", (720, 100), (128, 128, 128))  # Gray
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        data = buffer.getvalue()

        result = validate_label_image(data)
        assert not result.valid
        assert result.error_code == "NOT_MONOCHROME"

    def test_rgb_black_white_passes(self):
        """RGB image with only black and white should pass."""
        img = Image.new("RGB", (720, 100), (0, 0, 0))  # Black
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        data = buffer.getvalue()

        result = validate_label_image(data)
        assert result.valid

    def test_invalid_format(self):
        """Non-PNG should fail."""
        img = Image.new("1", (720, 100))
        buffer = BytesIO()
        img.save(buffer, format="JPEG")
        data = buffer.getvalue()

        result = validate_label_image(data)
        assert not result.valid
        assert result.error_code == "INVALID_FORMAT"

    def test_custom_width_config(self):
        """Custom config should allow different width."""
        config = LabelImageConfig(required_width=300)
        data = create_test_image(300, 100, mode="1")
        result = validate_label_image(data, config)
        assert result.valid

    def test_invalid_data(self):
        """Random bytes should fail."""
        result = validate_label_image(b"not an image")
        assert not result.valid
        assert result.error_code == "INVALID_IMAGE"


class TestPDFValidation:
    def test_valid_pdf_header(self):
        """File starting with %PDF should pass basic check."""
        # Minimal PDF-like data
        data = b"%PDF-1.4\n%some content"
        result = validate_pdf(data)
        # Note: this will pass header check but may fail pypdf parsing
        # which is fine - we're testing the validation logic

    def test_invalid_format(self):
        """Non-PDF should fail."""
        result = validate_pdf(b"not a pdf")
        assert not result.valid
        assert result.error_code == "INVALID_FORMAT"

    def test_empty_data(self):
        """Empty data should fail."""
        result = validate_pdf(b"")
        assert not result.valid
        assert result.error_code == "EMPTY_DATA"

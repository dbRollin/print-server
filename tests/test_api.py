"""Tests for API endpoints."""

import pytest
from io import BytesIO
from PIL import Image
from fastapi.testclient import TestClient

from src.api.server import create_app
from src.printers import PrinterRegistry
from src.printers.mock import MockLabelPrinter, MockDocumentPrinter


@pytest.fixture
def test_registry():
    """Create a registry with mock printers."""
    registry = PrinterRegistry()
    registry.register(MockLabelPrinter("label", "Test Label Printer", {"print_delay": 0}))
    registry.register(MockDocumentPrinter("document", "Test Document Printer", {"print_delay": 0}))
    return registry


@pytest.fixture
def test_routing_config():
    """Create test routing configuration."""
    return {
        "routing": {
            "shipping-label": "label",
            "price-tag": "label",
            "invoice": "document",
        },
        "defaults": {
            "label_printer": "label",
            "document_printer": "document"
        }
    }


@pytest.fixture
def client(test_registry, test_routing_config):
    """Create test client."""
    app = create_app(test_registry, routing_config=test_routing_config, debug=True)
    return TestClient(app)


def create_test_png(width: int = 720, height: int = 100) -> bytes:
    """Create a valid test PNG."""
    img = Image.new("1", (width, height), 0)
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


class TestHealthEndpoint:
    def test_health_check(self, client):
        """Health endpoint should return ok."""
        response = client.get("/v1/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestStatusEndpoint:
    def test_get_status(self, client):
        """Status should list all printers."""
        response = client.get("/v1/status")
        assert response.status_code == 200
        data = response.json()
        assert "printers" in data
        assert "label" in data["printers"]
        assert "document" in data["printers"]


class TestLabelPrinting:
    def test_print_valid_label(self, client):
        """Valid label image should be accepted."""
        png_data = create_test_png(720, 100)

        response = client.post(
            "/v1/print/label",
            files={"file": ("test.png", png_data, "image/png")}
        )

        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "queued"

    def test_print_wrong_width(self, client):
        """Image with wrong width should be rejected."""
        png_data = create_test_png(800, 100)

        response = client.post(
            "/v1/print/label",
            files={"file": ("test.png", png_data, "image/png")}
        )

        assert response.status_code == 400
        data = response.json()
        assert data["code"] == "INVALID_WIDTH"

    def test_print_to_unknown_printer(self, client):
        """Unknown printer should return 404."""
        png_data = create_test_png()

        response = client.post(
            "/v1/print/label?printer_id=nonexistent",
            files={"file": ("test.png", png_data, "image/png")}
        )

        assert response.status_code == 404


class TestDocumentPrinting:
    def test_print_valid_pdf(self, client):
        """Valid PDF should be accepted."""
        # Minimal valid PDF (complete structure)
        pdf_data = b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj
xref
0 4
0000000000 65535 f
0000000009 00000 n
0000000052 00000 n
0000000101 00000 n
trailer<</Size 4/Root 1 0 R>>
startxref
168
%%EOF"""

        response = client.post(
            "/v1/print/document",
            files={"file": ("test.pdf", pdf_data, "application/pdf")}
        )

        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data

    def test_print_invalid_pdf(self, client):
        """Non-PDF should be rejected."""
        response = client.post(
            "/v1/print/document",
            files={"file": ("test.pdf", b"not a pdf", "application/pdf")}
        )

        assert response.status_code == 400
        data = response.json()
        assert data["code"] == "INVALID_FORMAT"


class TestQueueEndpoint:
    def test_get_queue(self, client):
        """Queue endpoint should return queue status."""
        response = client.get("/v1/queue")
        assert response.status_code == 200
        data = response.json()
        assert "queues" in data

    def test_get_queue_for_printer(self, client):
        """Should get queue for specific printer."""
        # First add a job to create the queue
        png_data = create_test_png()
        client.post(
            "/v1/print/label",
            files={"file": ("test.png", png_data, "image/png")}
        )

        response = client.get("/v1/queue?printer_id=label")
        assert response.status_code == 200
        data = response.json()
        assert data["printer_id"] == "label"


class TestIntentRouting:
    def test_list_intents(self, client):
        """Should list configured intents."""
        response = client.get("/v1/intents")
        assert response.status_code == 200
        data = response.json()
        assert "intents" in data
        assert "shipping-label" in data["intents"]
        assert "invoice" in data["intents"]

    def test_print_with_intent_label(self, client):
        """Should route label intent to label printer."""
        png_data = create_test_png()

        response = client.post(
            "/v1/print?intent=shipping-label",
            files={"file": ("label.png", png_data, "image/png")}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["intent"] == "shipping-label"
        assert data["printer_id"] == "label"
        assert "job_id" in data

    def test_print_with_intent_document(self, client):
        """Should route document intent to document printer."""
        # Valid PDF
        pdf_data = b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj
xref
0 4
0000000000 65535 f
0000000009 00000 n
0000000052 00000 n
0000000101 00000 n
trailer<</Size 4/Root 1 0 R>>
startxref
168
%%EOF"""

        response = client.post(
            "/v1/print?intent=invoice",
            files={"file": ("invoice.pdf", pdf_data, "application/pdf")}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["intent"] == "invoice"
        assert data["printer_id"] == "document"

    def test_print_unknown_intent(self, client):
        """Should reject unknown intent."""
        png_data = create_test_png()

        response = client.post(
            "/v1/print?intent=unknown-thing",
            files={"file": ("label.png", png_data, "image/png")}
        )

        assert response.status_code == 400
        assert "Unknown intent" in response.json()["detail"]

    def test_print_with_intent_validates_image(self, client):
        """Intent routing should still validate images."""
        bad_png = create_test_png(width=800)  # Wrong width

        response = client.post(
            "/v1/print?intent=shipping-label",
            files={"file": ("label.png", bad_png, "image/png")}
        )

        assert response.status_code == 400
        assert response.json()["code"] == "INVALID_WIDTH"

"""
Configuration loading and printer setup.
"""

import os
import logging
from pathlib import Path
from typing import Optional

import yaml

from src.printers import PrinterRegistry
from src.printers.mock import MockLabelPrinter, MockDocumentPrinter
from src.printers.brother_ql_adapter import BrotherQLAdapter
from src.printers.cups_adapter import CUPSAdapter

logger = logging.getLogger(__name__)

# Map adapter types to classes
ADAPTER_TYPES = {
    "mock_label": MockLabelPrinter,
    "mock_document": MockDocumentPrinter,
    "brother_ql": BrotherQLAdapter,
    "cups": CUPSAdapter,
}


def load_config(config_path: Optional[str] = None) -> dict:
    """
    Load configuration from YAML file.

    Looks for config in order:
    1. Explicit path if provided
    2. CONFIG_FILE environment variable
    3. ./config/local.yaml
    4. ./config/default.yaml
    """
    search_paths = []

    if config_path:
        search_paths.append(Path(config_path))

    if env_path := os.environ.get("CONFIG_FILE"):
        search_paths.append(Path(env_path))

    # Default paths relative to project root
    project_root = Path(__file__).parent.parent
    search_paths.extend([
        project_root / "config" / "local.yaml",
        project_root / "config" / "default.yaml",
    ])

    for path in search_paths:
        if path.exists():
            logger.info(f"Loading config from {path}")
            with open(path) as f:
                return yaml.safe_load(f)

    logger.warning("No config file found, using defaults")
    return {}


def setup_printers(config: dict) -> PrinterRegistry:
    """
    Set up printers from configuration.

    Config format:
        printers:
          - id: label
            name: Label Printer
            adapter: brother_ql
            config:
              model: QL-720NW
              device: usb://0x04f9:0x2044
              label: "62"

          - id: document
            name: Document Printer
            adapter: cups
            config:
              cups_name: Brother_MFC
    """
    registry = PrinterRegistry()

    printer_configs = config.get("printers", [])

    if not printer_configs:
        # Default to mock printers for development
        logger.info("No printers configured, using mock printers")
        registry.register(MockLabelPrinter("label", "Mock Label Printer"))
        registry.register(MockDocumentPrinter("document", "Mock Document Printer"))
        return registry

    for printer_conf in printer_configs:
        printer_id = printer_conf.get("id")
        name = printer_conf.get("name", printer_id)
        adapter_type = printer_conf.get("adapter")
        adapter_config = printer_conf.get("config", {})

        if not printer_id:
            logger.warning("Printer config missing 'id', skipping")
            continue

        if adapter_type not in ADAPTER_TYPES:
            logger.warning(f"Unknown adapter type '{adapter_type}' for {printer_id}, skipping")
            continue

        adapter_class = ADAPTER_TYPES[adapter_type]
        try:
            printer = adapter_class(printer_id, name, adapter_config)
            registry.register(printer)
            logger.info(f"Registered printer: {name} ({printer_id}) using {adapter_type}")
        except Exception as e:
            logger.error(f"Failed to initialize printer {printer_id}: {e}")

    return registry


def get_server_config(config: dict) -> dict:
    """Extract server configuration."""
    server = config.get("server", {})
    return {
        "host": server.get("host", "0.0.0.0"),
        "port": server.get("port", 5001),
        "debug": server.get("debug", False),
        "cors_origins": server.get("cors_origins", None),
    }

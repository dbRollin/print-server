"""
Intent-based routing for print jobs.

Maps semantic intents (what you want to print) to physical printers.
Web app sends intent, server handles which printer.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class RouteConfig:
    printer_id: str
    description: str = ""


class PrintRouter:
    """
    Routes print intents to physical printers.

    Config example:
        routing:
          shipping-label: label
          price-tag: label
          invoice: document
          packing-slip: document

    Or with descriptions:
        routing:
          shipping-label:
            printer: label
            description: "4x6 shipping labels"
    """

    def __init__(self):
        self._routes: dict[str, RouteConfig] = {}
        self._default_label_printer: Optional[str] = None
        self._default_document_printer: Optional[str] = None

    def load_config(self, config: dict) -> None:
        """Load routing configuration."""
        routing = config.get("routing", {})

        for intent, target in routing.items():
            if isinstance(target, str):
                # Simple format: intent: printer_id
                self._routes[intent] = RouteConfig(printer_id=target)
            elif isinstance(target, dict):
                # Extended format: intent: { printer: id, description: "..." }
                self._routes[intent] = RouteConfig(
                    printer_id=target.get("printer", ""),
                    description=target.get("description", "")
                )

        # Set defaults
        defaults = config.get("defaults", {})
        self._default_label_printer = defaults.get("label_printer", "label")
        self._default_document_printer = defaults.get("document_printer", "document")

    def resolve(self, intent: str) -> Optional[str]:
        """
        Resolve an intent to a printer ID.

        Returns None if intent not found.
        """
        route = self._routes.get(intent)
        return route.printer_id if route else None

    def resolve_or_default(self, intent: str, content_type: str) -> str:
        """
        Resolve intent, falling back to default based on content type.
        """
        resolved = self.resolve(intent)
        if resolved:
            return resolved

        # Fall back based on content type
        if content_type.startswith("image/"):
            return self._default_label_printer or "label"
        elif content_type == "application/pdf":
            return self._default_document_printer or "document"

        return "label"  # Ultimate fallback

    def list_intents(self) -> dict[str, dict]:
        """List all configured intents for API discovery."""
        return {
            intent: {
                "printer_id": route.printer_id,
                "description": route.description
            }
            for intent, route in self._routes.items()
        }

    def add_route(self, intent: str, printer_id: str, description: str = "") -> None:
        """Programmatically add a route (useful for testing)."""
        self._routes[intent] = RouteConfig(printer_id=printer_id, description=description)

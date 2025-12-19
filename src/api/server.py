"""
FastAPI application factory with health monitoring.
"""

import logging
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.dependencies import QueueManager, init_dependencies
from src.api.routes import router
from src.health import HealthMonitor
from src.printers import PrinterRegistry
from src.printers.base import PrinterStatus
from src.routing import PrintRouter

logger = logging.getLogger(__name__)


def create_app(
    printers: PrinterRegistry,
    routing_config: dict = None,
    cors_origins: list[str] = None,
    debug: bool = False,
    health_check_interval_sec: float = 30.0
) -> FastAPI:
    """
    Create and configure FastAPI application.

    Args:
        printers: Configured printer registry
        routing_config: Intent routing configuration
        cors_origins: List of allowed CORS origins (None = allow all)
        debug: Enable debug mode
        health_check_interval_sec: How often to check printer health (default 30s)

    Returns:
        Configured FastAPI app
    """
    app = FastAPI(
        title="Print Gateway Server",
        description="REST API for centralized print management",
        version="1.0.0",
        debug=debug
    )

    # CORS configuration
    if cors_origins is None:
        # Development: allow all origins
        cors_origins = ["*"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Initialize router
    print_router = PrintRouter()
    if routing_config:
        print_router.load_config(routing_config)

    # Initialize dependencies
    queue_manager = QueueManager()
    init_dependencies(printers, queue_manager, print_router)

    # Create status change handler for health monitor
    async def on_printer_status_change(
        printer_id: str,
        old_status: Optional[PrinterStatus],
        new_status: PrinterStatus
    ) -> None:
        """Handle printer status changes from health monitor."""
        # When printer comes back online, notify its queue to process offline jobs
        if (old_status == PrinterStatus.OFFLINE and
                new_status in (PrinterStatus.READY, PrinterStatus.BUSY)):
            queue = queue_manager.get_queue(printer_id)
            if queue:
                logger.info(f"Printer {printer_id} back online, processing offline queue")
                await queue.on_printer_online()

        # When printer goes offline, mark queue as offline
        elif new_status == PrinterStatus.OFFLINE:
            queue = queue_manager.get_queue(printer_id)
            if queue:
                queue.set_printer_offline()

    # Create health monitor
    health_monitor = HealthMonitor(
        registry=printers,
        on_status_change=on_printer_status_change,
        default_interval_sec=health_check_interval_sec
    )

    # Include routes
    app.include_router(router)

    @app.on_event("startup")
    async def startup():
        logger.info("Print Gateway Server starting...")
        statuses = await printers.get_all_status()
        for printer_id, status in statuses.items():
            printer = printers.get(printer_id)
            logger.info(f"  {printer.name} ({printer_id}): {status.value}")

        intents = print_router.list_intents()
        if intents:
            logger.info("Configured intents:")
            for intent, info in intents.items():
                logger.info(f"  {intent} -> {info['printer_id']}")

        # Start health monitor
        await health_monitor.start()
        logger.info(f"Health monitor started (interval: {health_check_interval_sec}s)")

    @app.on_event("shutdown")
    async def shutdown():
        logger.info("Print Gateway Server shutting down...")
        # Stop health monitor
        await health_monitor.stop()

    return app

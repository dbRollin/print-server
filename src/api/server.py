"""
FastAPI application factory.
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import router
from src.api.dependencies import init_dependencies, QueueManager
from src.printers import PrinterRegistry
from src.routing import PrintRouter

logger = logging.getLogger(__name__)


def create_app(
    printers: PrinterRegistry,
    routing_config: dict = None,
    cors_origins: list[str] = None,
    debug: bool = False
) -> FastAPI:
    """
    Create and configure FastAPI application.

    Args:
        printers: Configured printer registry
        routing_config: Intent routing configuration
        cors_origins: List of allowed CORS origins (None = allow all)
        debug: Enable debug mode

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
                logger.info(f"  {intent} → {info['printer_id']}")

    @app.on_event("shutdown")
    async def shutdown():
        logger.info("Print Gateway Server shutting down...")

    return app

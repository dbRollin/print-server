"""
Print Gateway Server entry point.
"""

import argparse
import logging
import sys

import uvicorn

from src.config import load_config, setup_printers, get_server_config
from src.api.server import create_app
from src.startup import run_startup_checks, print_startup_banner

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Print Gateway Server")
    parser.add_argument(
        "-c", "--config",
        help="Path to config file (default: config/default.yaml)"
    )
    parser.add_argument(
        "--host",
        help="Override host from config"
    )
    parser.add_argument(
        "--port",
        type=int,
        help="Override port from config"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode"
    )
    parser.add_argument(
        "--skip-checks",
        action="store_true",
        help="Skip startup checks (not recommended)"
    )
    args = parser.parse_args()

    # Load configuration
    try:
        config = load_config(args.config)
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        sys.exit(1)

    # Apply CLI overrides before validation
    if args.host:
        config.setdefault("server", {})["host"] = args.host
    if args.port:
        config.setdefault("server", {})["port"] = args.port
    if args.debug:
        config.setdefault("server", {})["debug"] = True

    # Run startup checks
    if not args.skip_checks:
        run_startup_checks(config)

    # Set up printers
    printers = setup_printers(config)

    if not printers.list_all():
        logger.error("No printers configured!")
        logger.error("Check your config file or use --config to specify one.")
        sys.exit(1)

    # Get server config
    server_config = get_server_config(config)

    # Create app
    app = create_app(
        printers=printers,
        routing_config=config,
        cors_origins=server_config.get("cors_origins"),
        debug=server_config.get("debug", False)
    )

    # Print startup banner
    print_startup_banner(config, printers.list_all())

    # Run server
    try:
        uvicorn.run(
            app,
            host=server_config["host"],
            port=server_config["port"],
            log_level="debug" if server_config.get("debug") else "info"
        )
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

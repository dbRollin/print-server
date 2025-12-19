"""
Startup checks and validation.

Run before starting the server to catch configuration issues early.
"""

import logging
import socket
import sys
from typing import Optional

logger = logging.getLogger(__name__)


class StartupError(Exception):
    """Raised when startup checks fail."""
    pass


def check_port_available(host: str, port: int) -> tuple[bool, Optional[str]]:
    """
    Check if a port is available for binding.

    Returns:
        (True, None) if available
        (False, error_message) if not
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind((host, port))
        sock.close()
        return True, None
    except socket.error as e:
        if e.errno == 10048 or e.errno == 98:  # Windows / Linux "address in use"
            return False, f"Port {port} is already in use. Another service may be running on this port."
        elif e.errno == 10049 or e.errno == 99:  # Can't assign address
            return False, f"Cannot bind to {host}:{port}. Check if the host address is valid."
        elif e.errno == 10013 or e.errno == 13:  # Permission denied
            return False, f"Permission denied for port {port}. Ports below 1024 require admin/root privileges."
        else:
            return False, f"Cannot bind to {host}:{port}: {e}"
    finally:
        sock.close()


def validate_config(config: dict) -> list[str]:
    """
    Validate configuration and return list of warnings/errors.

    Returns:
        List of warning/error messages (empty if all good)
    """
    issues = []

    # Check server config
    server = config.get("server", {})
    port = server.get("port", 5001)

    if not isinstance(port, int) or port < 1 or port > 65535:
        issues.append(f"Invalid port: {port}. Must be between 1 and 65535.")

    if port < 1024:
        issues.append(f"Port {port} is a privileged port. Consider using a port >= 1024.")

    # Check printers config
    printers = config.get("printers", [])
    if not printers:
        issues.append("No printers configured. Server will use mock printers.")

    printer_ids = set()
    for i, printer in enumerate(printers):
        pid = printer.get("id")
        if not pid:
            issues.append(f"Printer at index {i} has no 'id' field.")
        elif pid in printer_ids:
            issues.append(f"Duplicate printer ID: '{pid}'")
        else:
            printer_ids.add(pid)

        adapter = printer.get("adapter")
        if not adapter:
            issues.append(f"Printer '{pid}' has no 'adapter' field.")

    # Check routing config
    routing = config.get("routing", {})
    for intent, target in routing.items():
        printer_id = target if isinstance(target, str) else target.get("printer")
        if printer_id and printer_id not in printer_ids and printers:
            issues.append(f"Intent '{intent}' routes to unknown printer '{printer_id}'.")

    return issues


def check_dependencies() -> dict[str, bool]:
    """
    Check which optional dependencies are available.

    Returns:
        Dict of dependency name -> is_available
    """
    deps = {}

    # brother_ql for label printing
    try:
        import brother_ql
        deps["brother_ql"] = True
    except ImportError:
        deps["brother_ql"] = False

    # pycups for CUPS printing
    try:
        import cups
        deps["pycups"] = True
    except ImportError:
        deps["pycups"] = False

    # pypdf for PDF validation
    try:
        import pypdf
        deps["pypdf"] = True
    except ImportError:
        deps["pypdf"] = False

    return deps


def run_startup_checks(config: dict) -> None:
    """
    Run all startup checks. Exits with error if critical issues found.

    Args:
        config: Loaded configuration dict
    """
    logger.info("Running startup checks...")

    errors = []
    warnings = []

    # Check port availability
    server = config.get("server", {})
    host = server.get("host", "0.0.0.0")
    port = server.get("port", 5001)

    available, port_error = check_port_available(host, port)
    if not available:
        errors.append(port_error)

    # Validate config
    config_issues = validate_config(config)
    for issue in config_issues:
        if "No printers configured" in issue:
            warnings.append(issue)
        elif "unknown printer" in issue.lower():
            warnings.append(issue)
        else:
            # Treat most issues as warnings, not errors
            if "Invalid port" in issue or "Duplicate printer" in issue:
                errors.append(issue)
            else:
                warnings.append(issue)

    # Check dependencies
    deps = check_dependencies()
    missing_deps = [name for name, available in deps.items() if not available]
    if missing_deps:
        warnings.append(f"Optional dependencies not installed: {', '.join(missing_deps)}")

    # Report warnings
    for warning in warnings:
        logger.warning(f"  ⚠ {warning}")

    # Report errors and exit if any
    if errors:
        logger.error("Startup checks failed:")
        for error in errors:
            logger.error(f"  ✗ {error}")
        logger.error("")
        logger.error("Fix these issues and try again.")
        sys.exit(1)

    if warnings:
        logger.info(f"Startup checks passed with {len(warnings)} warning(s)")
    else:
        logger.info("Startup checks passed ✓")


def print_startup_banner(config: dict, printers: list) -> None:
    """Print a nice startup banner with useful info."""
    server = config.get("server", {})
    host = server.get("host", "0.0.0.0")
    port = server.get("port", 5001)

    # Get local IP for convenience
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        local_ip = "unknown"

    print("")
    print("=" * 50)
    print("  Print Gateway Server")
    print("=" * 50)
    print("")
    print(f"  Local URL:    http://localhost:{port}")
    print(f"  Network URL:  http://{local_ip}:{port}")
    print(f"  API Docs:     http://localhost:{port}/docs")
    print("")
    print("  Printers:")
    for printer in printers:
        print(f"    • {printer.name} ({printer.printer_id})")
    print("")
    print("  Endpoints:")
    print("    POST /v1/print?intent=<intent>  - Print with routing")
    print("    GET  /v1/intents                - List intents")
    print("    GET  /v1/health                 - Health check")
    print("    GET  /v1/status                 - Printer status")
    print("")
    print("=" * 50)
    print("")

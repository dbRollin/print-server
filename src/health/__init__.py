"""
Health monitoring module.

Provides background health checks for USB printers and status change detection.
"""

from .monitor import HealthMonitor

__all__ = ["HealthMonitor"]

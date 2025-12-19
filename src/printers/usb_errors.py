"""
USB error classification for resilient printer connections.

Classifies USB errors as recoverable (can retry after reconnect) or permanent.
"""

from enum import Enum, auto


class USBErrorType(Enum):
    """Classification of USB errors."""

    RECOVERABLE = auto()  # Errno 5, device not found - can retry after reconnect
    PERMANENT = auto()  # Configuration error, driver issue - won't help to retry
    UNKNOWN = auto()  # Unclassified error


# USB I/O errors that indicate disconnection/sleep - worth retrying
RECOVERABLE_ERRNO = {
    5,  # EIO - Input/Output error (common on USB disconnect)
    6,  # ENXIO - No such device or address
    19,  # ENODEV - No such device
    110,  # ETIMEDOUT - Connection timed out
    121,  # EREMOTEIO - Remote I/O error (USB)
}

# Error message substrings that indicate recoverable USB issues
RECOVERABLE_MESSAGES = (
    "no backend",
    "device not found",
    "i/o error",
    "input/output error",
    "resource busy",
    "pipe error",
    "could not open",
    "no such device",
    "usb error",
    "endpoint halted",
    "operation timed out",
)


def classify_usb_error(exception: Exception) -> USBErrorType:
    """
    Classify whether a USB error is recoverable via reconnection.

    Args:
        exception: The exception raised during USB communication

    Returns:
        USBErrorType indicating if the error is recoverable
    """
    # Check OSError errno values
    if isinstance(exception, OSError):
        if exception.errno in RECOVERABLE_ERRNO:
            return USBErrorType.RECOVERABLE

    # Check for pyusb-specific errors and common USB error messages
    error_msg = str(exception).lower()
    if any(phrase in error_msg for phrase in RECOVERABLE_MESSAGES):
        return USBErrorType.RECOVERABLE

    # Check nested exceptions (some libraries wrap USB errors)
    if exception.__cause__:
        cause_result = classify_usb_error(exception.__cause__)
        if cause_result == USBErrorType.RECOVERABLE:
            return USBErrorType.RECOVERABLE

    return USBErrorType.UNKNOWN


def is_recoverable_error(exception: Exception) -> bool:
    """
    Convenience function to check if an error is recoverable.

    Args:
        exception: The exception to check

    Returns:
        True if the error might be resolved by USB reconnection
    """
    return classify_usb_error(exception) == USBErrorType.RECOVERABLE

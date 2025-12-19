# USB Connection Resilience

**Status: IMPLEMENTED** (December 2025)

## Problem Statement

When a USB-connected printer powers off, sleeps, or loses connection temporarily, the print server's USB handle becomes stale. Subsequent print jobs fail with:

```
[Errno 5] Input/Output Error
```

The print server continues to report the printer as "online" and "ready" because it's checking cached state, not the actual device. The only current fix is to restart the print server process.

## Requirements

### 1. Automatic USB Reconnection

When a print job fails with an I/O error:
1. Detect the failure is USB-related (Errno 5, device not found, etc.)
2. Close the stale USB handle
3. Re-discover the USB device using `brother_ql discover`
4. Re-open the connection
5. Retry the print job (up to N times)

### 2. Proactive Health Checks

Periodically verify the USB device is actually accessible:
- Send a status query to the printer every 30-60 seconds
- If unreachable, mark printer as "offline" in `/v1/status`
- When device reappears, automatically reconnect and mark "online"

### 3. Graceful Degradation

When printer is unavailable:
- Queue jobs instead of failing immediately
- Return `"status": "queued_offline"` to client
- Process queue when printer comes back online
- Configurable queue timeout (e.g., jobs expire after 10 minutes)

### 4. Event Logging

Log connection events for debugging:
- `USB_DISCONNECTED` - device lost
- `USB_RECONNECTED` - device found again
- `USB_RECONNECT_FAILED` - couldn't recover
- `JOB_QUEUED_OFFLINE` - job held due to offline printer
- `JOB_RETRY` - retrying after reconnect

## Implementation Approach

### Option A: Wrapper with Retry Logic

Wrap the `brother_ql` print calls with retry logic:

```python
class ResilientBrotherQL:
    def __init__(self, config):
        self.config = config
        self.device = None
        self.max_retries = 3

    def print(self, image_path):
        for attempt in range(self.max_retries):
            try:
                if not self.device:
                    self.device = self._discover_device()
                return self._do_print(image_path)
            except IOError as e:
                if e.errno == 5:  # I/O Error
                    self.device = None  # Clear stale handle
                    time.sleep(1)  # Brief delay before retry
                    continue
                raise
        raise PrinterOfflineError("Failed after retries")

    def _discover_device(self):
        # Use brother_ql discover or known USB path
        devices = brother_ql.discover()
        if not devices:
            raise PrinterNotFoundError()
        return devices[0]
```

### Option B: udev Integration (Linux)

Create a udev rule that notifies the print server when USB devices change:

```
# /etc/udev/rules.d/99-brother-ql.rules
ACTION=="add", SUBSYSTEM=="usb", ATTR{idVendor}=="04f9", ATTR{idProduct}=="2044", RUN+="/usr/local/bin/notify-print-server reconnect"
ACTION=="remove", SUBSYSTEM=="usb", ATTR{idVendor}=="04f9", ATTR{idProduct}=="2044", RUN+="/usr/local/bin/notify-print-server disconnect"
```

Print server exposes an internal endpoint or listens for signals to handle reconnection.

### Option C: Background Health Monitor

Separate thread/process that monitors USB device:

```python
class USBHealthMonitor:
    def __init__(self, printer_manager):
        self.printer_manager = printer_manager
        self.check_interval = 30  # seconds

    def run(self):
        while True:
            for printer in self.printer_manager.usb_printers:
                if not self._is_device_accessible(printer.device_path):
                    printer.mark_offline()
                    self._attempt_reconnect(printer)
                else:
                    printer.mark_online()
            time.sleep(self.check_interval)

    def _is_device_accessible(self, path):
        try:
            # Try to open device briefly
            with open(path, 'rb') as f:
                pass
            return True
        except:
            return False
```

## Configuration

Add to `config.yaml`:

```yaml
printers:
  - id: label
    name: Brother QL-720NW
    adapter: brother_ql
    config:
      model: QL-720NW
      device: "usb://0x04f9:0x2044"
      label: "62"
    resilience:
      auto_reconnect: true
      max_retries: 3
      retry_delay_ms: 1000
      health_check_interval_sec: 30
      offline_queue_enabled: true
      offline_queue_timeout_sec: 600
```

## API Changes

### Status Endpoint Enhancement

`GET /v1/status` should return actual device state:

```json
{
  "printers": {
    "label": {
      "name": "Brother QL-720NW",
      "status": "offline",
      "online": false,
      "last_seen": "2025-12-18T23:50:00Z",
      "error": "USB device not responding",
      "queued_jobs": 2
    }
  }
}
```

### Print Response Enhancement

`POST /v1/print/label` when offline:

```json
{
  "job_id": "abc-123",
  "status": "queued_offline",
  "message": "Printer offline - job queued for 10 minutes",
  "queue_position": 2,
  "expires_at": "2025-12-18T23:45:00Z"
}
```

## Testing

1. **Power cycle test**: Print, unplug printer, plug back in, print again
2. **Sleep test**: Let printer sleep, send print, verify auto-wake and print
3. **Queue test**: Unplug printer, send 3 jobs, plug in, verify all print
4. **Timeout test**: Unplug printer, send job, wait past timeout, verify job expires

## Priority

**High** - This is a production blocker. Users shouldn't need to SSH into the server to restart services when a printer power cycles.

## Related

- Brother QL Python library: https://github.com/pklaus/brother_ql
- USB device discovery: `brother_ql discover`
- Linux udev documentation: https://www.freedesktop.org/software/systemd/man/udev.html

---

## Implementation Summary

The USB resilience feature was implemented using a hybrid approach (Options A + C):

### Files Created
- `src/printers/usb_errors.py` - USB error classification (errno 5, device not found, etc.)
- `src/health/__init__.py` - Health module init
- `src/health/monitor.py` - Background asyncio health monitor
- `tests/test_usb_resilience.py` - 23 tests for resilience features

### Files Modified
- `src/printers/brother_ql_adapter.py` - Retry wrapper, reconnect logic, actual device probing
- `src/queue/manager.py` - QUEUED_OFFLINE/EXPIRED status, offline queuing, job expiration
- `src/api/routes.py` - 202 response for offline queue, enhanced /v1/status
- `src/api/server.py` - Health monitor integration with server lifecycle
- `src/config.py` - ResilienceConfig dataclass
- `config/default.yaml` - health_check_interval_sec setting
- `config/shop.yaml.example` - Full resilience config example

### Key Features
1. **Automatic Retry** - 3 attempts with 1-second delay on USB I/O errors
2. **Device Rediscovery** - Uses `brother_ql discover` to find device after disconnect
3. **Proactive Health Checks** - Background task checks printer status every 30 seconds
4. **Offline Job Queuing** - Jobs queued with 10-minute timeout when printer offline
5. **Job Expiration** - Background task expires jobs that wait too long
6. **Event Logging** - USB_DISCONNECTED, USB_RECONNECTED, USB_RECONNECT_FAILED events

### Configuration
```yaml
printers:
  - id: label
    adapter: brother_ql
    config:
      device: "usb://0x04f9:0x2044"
    resilience:
      auto_reconnect: true
      max_retries: 3
      retry_delay_ms: 1000
      health_check_interval_sec: 30
      offline_queue_enabled: true
      offline_queue_timeout_sec: 600
```

# Print Gateway Server

**Project Specification Document**

BruTek / Titan USA

---

## Executive Summary

This document outlines the design and implementation plan for a centralized Print Gateway Server. The server will handle print requests from internal web applications and network devices, routing jobs to appropriate printers without requiring client-side printer software or direct printer access.

The immediate goal is to enable label printing from a custom web application to a Brother QL-720 label printer. The architecture is designed to scale, supporting additional printers, devices, and automation services as needs evolve.

---

## Project Goals

### Immediate Objective

Enable users to print box labels directly from the internal web application. When a user clicks "Print Label" in the app, a physical label should print on the QL-720 without any manual steps, file transfers, or third-party software like P-touch Editor.

### Secondary Objectives

- Provide a unified print API that any internal application can use
- Support standard document printing (8.5x11, etc.) to the existing network printer
- Create a foundation for future shop floor integrations (scanners, automation, etc.)
- Centralize print infrastructure on a single, maintainable server

---

## Architecture Overview

### System Topology

The Print Gateway Server sits on the internal network and acts as a bridge between applications and physical printers. All print requests flow through HTTP API endpoints, allowing any networked device or application to print without direct printer access.

**Request Flow:**

1. Web Application generates a print-ready image or document (fully formatted for the target printer)
2. Application sends HTTP POST to Print Gateway API
3. Print Gateway validates, queues, and routes to appropriate printer
4. Print Gateway returns confirmation or error response
5. Physical output is produced (label, document, etc.)

### Network Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      INTERNAL NETWORK                           │
│                                                                 │
│  [Shop Floor PCs]  [Office PCs]  [Mobile/Tablets]  [Web Apps]   │
│         │               │              │               │        │
│         └───────────────┴──────────────┴───────────────┘        │
│                                 │                                │
│                                 ▼                                │
│                    ┌─────────────────────────┐                   │
│                    │   PRINT GATEWAY SERVER  │                   │
│                    │   (Dell Mini - Linux)   │                   │
│                    │                         │                   │
│                    │   POST /print/label     │                   │
│                    │   POST /print/document  │                   │
│                    │   GET  /status          │                   │
│                    │   GET  /queue           │                   │
│                    └───────────┬─────────────┘                   │
│                          ┌─────┴─────┐                           │
│                         USB       Network                        │
│                          │           │                           │
│                          ▼           ▼                           │
│                    [QL-720]    [MFC-L3750CDW]                    │
│                    (Labels)    (Documents)                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## Hardware Configuration

### Print Gateway Server

| Component | Specification |
|-----------|---------------|
| Hardware | Dell Mini Tower (entry-level office PC) |
| Operating System | Ubuntu Server 24.04 LTS (headless, no GUI) |
| Network | Static IP address on internal network |
| Container Runtime | Docker Engine (native Linux, not Docker Desktop) |
| Management | SSH access for remote administration |

### Printers

| Printer | Model | Connection | Purpose |
|---------|-------|------------|---------|
| Label Printer | Brother QL-720 | USB to server | Box labels, shipping labels |
| Document Printer | Brother MFC-L3750CDW | Network (existing) | 8.5x11 documents, color printing |

### Label Media

| Specification | Value |
|---------------|-------|
| Part Number | DK-2205 |
| Type | Continuous length tape (62mm / 2.4" wide) |
| Print Resolution | 300 DPI |
| Image Width | 720 pixels (62mm at 300 DPI) |
| Image Height | Variable (continuous tape, cut after printing) |
| Color Mode | 1-bit monochrome (black and white only, no grayscale) |

---

## Software Stack

### Server Components

| Component | Technology | Purpose |
|-----------|------------|---------|
| Operating System | Ubuntu Server 24.04 LTS | Stable, long-term support, native Docker |
| Container Runtime | Docker Engine + Compose | Service isolation, easy deployment |
| API Framework | Python Flask or FastAPI | HTTP endpoints for print requests |
| Image Processing | Pillow (PIL) | Validation, format conversion if needed |
| Label Printing | brother_ql (Python library) | Direct communication with QL-720 |
| Document Printing | CUPS | Network printer management, PDF rendering |
| USB Access | libusb + udev rules | Device permissions for Docker |

### Why These Choices

**Ubuntu Server (not Windows):**

- Lower resource overhead — no Windows background services consuming RAM/CPU
- Native Docker support — containers run directly on the kernel, not in a VM
- Easier USB device passthrough to containers
- Better stability for always-on server (no forced update reboots)
- Free (no license costs)

**Docker (not bare metal services):**

- Isolated environments — each service in its own container
- Easy to add new services without conflicts
- Reproducible deployments via docker-compose.yml
- Simple backup and migration

**brother_ql (not CUPS for labels):**

- Direct USB communication — bypasses driver complexity
- Full control over raster conversion and print settings
- Open source, well-documented, actively maintained
- Specifically designed for Brother QL-series printers

**CUPS (for document printing):**

- Industry standard for Linux printing
- Native support for Brother MFC-L3750CDW via IPP/AirPrint
- Handles PDF rendering, spooling, queue management
- Mature, stable, well-supported

---

## API Specification

The Print Gateway exposes a REST API. All endpoints are accessible only from the internal network. The API is versioned to allow for future changes without breaking existing integrations.

**Base URL:** `http://<server-ip>:5001/v1`

---

### Label Printing Endpoint

```
POST /v1/print/label
```

**Request:**

| Parameter | Type | Description |
|-----------|------|-------------|
| Content-Type | image/png | Format of the label image |
| Body | Binary image data | The print-ready label image |

The web application is responsible for generating properly formatted images (720px wide, monochrome, correct DPI). The print server expects print-ready images and does not resize or reformat.

**Success Response (HTTP 200):**

```json
{
  "success": true,
  "job_id": "lbl-20241215-001",
  "message": "Label sent to printer",
  "printer": "QL-720",
  "timestamp": "2024-12-15T14:32:01Z"
}
```

**Error Responses:**

| HTTP Code | Condition | Response |
|-----------|-----------|----------|
| 400 | Invalid image format | `{"success": false, "error": "invalid_format", "message": "Expected PNG image"}` |
| 400 | Image validation failed | `{"success": false, "error": "validation_failed", "message": "Image width must be 720px, received 800px"}` |
| 503 | Printer offline | `{"success": false, "error": "printer_offline", "message": "QL-720 is not responding"}` |
| 503 | Printer error | `{"success": false, "error": "printer_error", "message": "Printer reports: out of labels"}` |
| 500 | Server error | `{"success": false, "error": "server_error", "message": "Internal error, check logs"}` |

---

### Document Printing Endpoint

```
POST /v1/print/document
```

**Request:**

| Parameter | Type | Description |
|-----------|------|-------------|
| Content-Type | application/pdf | PDF document to print |
| Body | Binary PDF data | The print-ready document |

The web application is responsible for generating properly formatted PDFs (correct page size, orientation, margins). The print server sends the PDF to CUPS as-is.

**Success Response (HTTP 200):**

```json
{
  "success": true,
  "job_id": "doc-20241215-042",
  "message": "Document sent to printer",
  "printer": "MFC-L3750CDW",
  "pages": 3,
  "timestamp": "2024-12-15T14:35:22Z"
}
```

**Error Responses:**

| HTTP Code | Condition | Response |
|-----------|-----------|----------|
| 400 | Invalid format | `{"success": false, "error": "invalid_format", "message": "Expected PDF document"}` |
| 400 | Corrupt PDF | `{"success": false, "error": "validation_failed", "message": "Unable to parse PDF"}` |
| 503 | Printer offline | `{"success": false, "error": "printer_offline", "message": "MFC-L3750CDW is not responding"}` |
| 503 | Printer error | `{"success": false, "error": "printer_error", "message": "Printer reports: paper jam"}` |
| 500 | Server error | `{"success": false, "error": "server_error", "message": "Internal error, check logs"}` |

---

### Status Endpoint

```
GET /v1/status
```

Returns the current status of all configured printers and the print server itself.

**Response (HTTP 200):**

```json
{
  "server": {
    "status": "online",
    "uptime": "3d 14h 22m",
    "version": "1.0.0"
  },
  "printers": {
    "label": {
      "name": "QL-720",
      "status": "online",
      "connection": "USB",
      "last_job": "2024-12-15T14:32:01Z"
    },
    "document": {
      "name": "MFC-L3750CDW",
      "status": "online",
      "connection": "network",
      "ip": "192.168.1.50",
      "last_job": "2024-12-15T14:35:22Z"
    }
  }
}
```

**Printer Status Values:**

| Status | Meaning |
|--------|---------|
| online | Ready to print |
| offline | Not responding / not connected |
| error | Printer reporting an error (jam, out of paper/labels, etc.) |
| busy | Currently processing a job |

---

### Queue Endpoint

```
GET /v1/queue
```

Returns the current print queue status.

**Response (HTTP 200):**

```json
{
  "label_queue": {
    "pending": 0,
    "processing": null
  },
  "document_queue": {
    "pending": 2,
    "processing": {
      "job_id": "doc-20241215-042",
      "submitted": "2024-12-15T14:35:22Z",
      "pages": 3
    }
  }
}
```

---

### Health Check Endpoint

```
GET /v1/health
```

Simple health check for monitoring systems.

**Response (HTTP 200):**

```json
{
  "status": "healthy",
  "timestamp": "2024-12-15T14:40:00Z"
}
```

Returns HTTP 503 if the server is degraded or unhealthy.

---

## Web Application Integration Requirements

This section outlines what the web application development team needs to know and implement to integrate with the Print Gateway.

### Design Principle

The web application owns all formatting decisions. Each print use case in the web app has its own print preview that generates a correctly-sized, correctly-formatted image or document for its target printer. The print server does not modify, resize, or reformat incoming print jobs — it validates and passes them through.

This means:
- Label images arrive at exactly 720px wide, monochrome PNG
- Documents arrive as properly formatted PDFs
- The user cannot override printer settings at print time
- Each use case in the web app is hard-coded to its target output

### Label Image Requirements

| Requirement | Specification |
|-------------|---------------|
| Format | PNG |
| Width | 720 pixels (fixed for DK-2205 at 300 DPI) |
| Height | Variable — whatever your label content requires |
| Color Mode | Black and white only. Pure black (#000000) and pure white (#FFFFFF). |
| Resolution | 300 DPI |
| Fonts | Rendered at image generation time. The print server receives pixels, not text. |

### Image Generation Options

The web application can generate label images using several approaches:

**Client-side (in browser):**

- html2canvas — renders HTML/CSS to a canvas element, export as PNG
- Canvas API — draw directly on a canvas element
- SVG — create SVG, then rasterize to PNG

**Server-side (in your app backend):**

- Puppeteer/Playwright — headless browser renders HTML, screenshots to PNG
- Canvas libraries (node-canvas, sharp, etc.)

### Integration Code Example

Below is a simplified example of how your web application might call the Print Gateway:

```javascript
// JavaScript/TypeScript example

const PRINT_SERVER = 'http://192.168.1.100:5001';

async function printLabel(imageBlob) {
  try {
    const response = await fetch(
      `${PRINT_SERVER}/v1/print/label`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'image/png' },
        body: imageBlob
      }
    );
    
    const result = await response.json();
    
    if (result.success) {
      // Show success message to user
      showNotification('Label sent to printer', 'success');
      return { success: true, jobId: result.job_id };
    } else {
      // Handle specific error
      showNotification(`Print failed: ${result.message}`, 'error');
      return { success: false, error: result.error };
    }
  } catch (err) {
    // Network error - server unreachable
    showNotification('Print server unreachable', 'error');
    return { success: false, error: 'network_error' };
  }
}

async function checkPrinterStatus() {
  try {
    const response = await fetch(`${PRINT_SERVER}/v1/status`);
    const status = await response.json();
    return status.printers.label.status === 'online';
  } catch {
    return false;
  }
}
```

### Recommended Integration Architecture

Build a configurable integration module in your web application:

- **Configuration settings**: Print server URL stored in app config (easy to change between environments)
- **Connection test function**: Verify server is reachable before showing print options
- **Print service**: Abstraction layer that handles API calls and response parsing
- **User feedback**: Display success confirmations and meaningful error messages
- **Offline handling**: Graceful degradation if print server is unavailable

### CORS Considerations

If your web app runs in a browser and makes direct calls to the print server from client-side JavaScript, you'll need CORS headers. The print server will be configured to allow requests from your web app's origin.

If your web app's backend proxies print requests (app backend → print server), CORS is not a concern.

---

## Print Queue Behavior

The print server maintains a simple queue for each printer:

- **Sequential processing**: Jobs are processed in the order received
- **No blocking**: API calls return immediately with a job ID; the job is queued
- **Queue depth**: Configurable limit (default: 50 jobs per queue)
- **Timeout handling**: Jobs that fail to print within 60 seconds are marked as failed
- **No persistence**: Queue is in-memory; pending jobs are lost on server restart (acceptable for this use case)

### Concurrent Requests

If multiple print requests arrive simultaneously:
1. Each request is assigned a job ID immediately
2. Each request receives a success response (job queued)
3. Jobs print in order

---

## Error Handling & Recovery

### USB Hot-Plug (QL-720)

If the QL-720 is unplugged and reconnected:
- The udev rule ensures consistent device permissions
- The brother_ql library will detect the reconnection
- No container restart required
- Jobs submitted while disconnected will fail with "printer_offline" error

### Network Printer Recovery (MFC-L3750CDW)

If the MFC-L3750CDW goes offline:
- CUPS handles retry logic for queued jobs
- Status endpoint will report "offline"
- Jobs submitted while offline will queue in CUPS (with timeout)

### Container Restart Policy

Docker containers are configured with `restart: unless-stopped`:
- Containers restart automatically after server reboot
- Containers restart if they crash
- Containers stay stopped if manually stopped

---

## Security Considerations

### Network Security

- Internal network only — Print Gateway is not exposed to the internet
- UFW firewall configured to allow only internal IP ranges
- SSH access restricted to specific machines/users
- API port (5001) only accessible from internal network

### Access Control (Current Phase)

For the initial implementation, network isolation is the primary security mechanism. Any device on the internal network can send print requests. This is acceptable for a shop environment with trusted devices.

### Future Enhancements (If Needed)

- API key authentication for print requests
- Per-application credentials
- Request logging and audit trail
- Rate limiting to prevent abuse

---

## Implementation Plan

### Phase 1: Development & Testing (Home)

Initial setup and testing performed at home with the QL-720 printer.

1. Install Ubuntu Server 24.04 LTS on Dell mini tower
2. Install Docker Engine and Docker Compose
3. Configure USB device permissions (udev rules)
4. Deploy print gateway container with brother_ql
5. Test label printing via API (use curl or Postman)
6. Test error handling (unplug printer, send bad image, etc.)
7. Configure CUPS for document printing (if network printer accessible)
8. Document final configuration and assigned IP

**Testing Checklist:**
- [ ] Server boots and containers start automatically
- [ ] `/v1/health` returns healthy
- [ ] `/v1/status` shows QL-720 online
- [ ] POST to `/v1/print/label` with valid PNG prints successfully
- [ ] POST with invalid image returns appropriate error
- [ ] Unplugging printer results in "offline" status
- [ ] Reconnecting printer restores "online" status without restart

### Phase 2: Production Deployment (Shop)

Move server to shop network and finalize configuration.

1. Move Dell server to shop location
2. Connect to shop network, assign static IP (document the IP)
3. Connect QL-720 via USB
4. Configure CUPS to connect to MFC-L3750CDW (by IP address)
5. Update web application configuration with production print server URL
6. End-to-end testing from shop floor devices
7. Configure firewall rules
8. Verify auto-restart after power cycle

**Rollback Plan:**
If issues arise, the web app can fall back to manual label printing via P-touch Editor until resolved. Keep P-touch software installed on at least one shop PC during transition.

### What Changes Between Home and Shop

| Component | At Home | At Shop |
|-----------|---------|---------|
| USB connection | Works | Works (no change) |
| Docker container | Runs | Runs (no change) |
| Print server code | Works | Works (no change) |
| Server IP address | 192.168.x.x (home) | New static IP (shop) |
| Web app config | Points to home IP | Update to shop IP |

Only the IP address configuration in your web application needs to change. Everything else transfers directly.

---

## Backup & Recovery

### What to Back Up

| Item | Location | Backup Method |
|------|----------|---------------|
| docker-compose.yml | /opt/print-gateway/ | Git repo or manual copy |
| Container configs | /opt/print-gateway/ | Git repo or manual copy |
| udev rules | /etc/udev/rules.d/ | Manual copy |
| CUPS config | /etc/cups/ | Manual copy |

### Recovery Procedure

If the Dell server fails:
1. Install Ubuntu Server on replacement hardware
2. Install Docker Engine
3. Copy configuration files from backup
4. Run `docker-compose up -d`
5. Verify with `/v1/health` and `/v1/status`
6. Update static IP if hardware MAC changed

Print queue (in-memory) is not backed up. Any pending jobs at time of failure are lost — users would need to reprint.

---

## Future Expansion Possibilities

The Print Gateway Server architecture is designed to grow. The same Dell machine can host additional services as needs arise.

### Additional Print Services

- Additional label printers (different sizes, locations)
- Receipt printers for shop floor printing
- Large format / plotter support

### Input Devices

- Barcode scanners — USB scanners feeding data to web applications
- Document scanners — scan-to-folder or scan-to-workflow
- Badge/card readers — time tracking, access logging

### Automation Services

- n8n instance — workflow automation running locally
- Watched folders — drop a file, trigger an action
- Scheduled tasks — reports, backups, maintenance

### Data Services

- Network file shares (SMB) — common folders for shop floor
- Local database — PostgreSQL for internal applications
- Backup target — centralized backup destination

### Shop Floor Integration

- Kiosk displays — browser-based interfaces for scanning/lookup
- Machine monitoring — collect data from CNC equipment
- IoT gateway — aggregate sensor data

---

## Appendix: Technical Reference

### Brother QL-720 Specifications

| Specification | Value |
|---------------|-------|
| USB Vendor ID | 0x04f9 |
| USB Product ID | 0x2041 |
| Print Resolution | 300 x 300 DPI |
| Max Print Width | 62mm (2.4 inches) |
| brother_ql Model String | QL-720 |
| Label Type for DK-2205 | 62 (62mm continuous) |

### Brother MFC-L3750CDW Specifications

| Specification | Value |
|---------------|-------|
| Connection | Network (Ethernet/WiFi) |
| Protocol | IPP / AirPrint (driverless CUPS support) |
| Color | Yes (color laser) |
| Duplex | Yes (automatic) |
| Paper Sizes | Letter, Legal, A4, etc. |

### CUPS Overview

CUPS (Common Unix Printing System) is the standard print management system on Linux. It handles printer discovery, driver management, print queues, and network printing protocols. For the MFC-L3750CDW, CUPS will communicate via IPP (Internet Printing Protocol), which the printer supports natively — no additional drivers required.

The MFC-L3750CDW will be configured in CUPS by its IP address to avoid issues if the printer's hostname changes or mDNS is unreliable.

### Key File Locations (On Server)

| Path | Purpose |
|------|---------|
| /etc/udev/rules.d/99-brother-ql.rules | USB device permission rules for QL-720 |
| /opt/print-gateway/ | Print gateway application files |
| /opt/print-gateway/docker-compose.yml | Container orchestration config |
| /var/log/print-gateway/ | Application logs |
| /etc/cups/ | CUPS configuration |
| /etc/cups/printers.conf | Configured printers |

### Network Ports

| Port | Service | Access |
|------|---------|--------|
| 22 | SSH | Internal network only |
| 5001 | Print Gateway API | Internal network only |
| 631 | CUPS (if web UI enabled) | Localhost or internal only |

### API Version History

| Version | Date | Notes |
|---------|------|-------|
| v1 | 2024-12 | Initial release |

---

## Ownership & Support

| Role | Responsibility |
|------|----------------|
| System Owner | [To be assigned] |
| Primary Contact | [To be assigned] |
| Backup Contact | [To be assigned] |

---

*— End of Document —*

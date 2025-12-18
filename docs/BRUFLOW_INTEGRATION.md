# Print Server - BruFLOW Integration Guide

**Document Version:** 1.0
**Last Updated:** 2025-12-16
**Status:** Draft - Awaiting alignment on template rendering

---

## Executive Summary

The Print Server is a dedicated REST API service for handling print requests from internal web applications like BruFLOW. It runs on Ubuntu Server with Docker and manages communication with network label printers.

**Key Principle:** The Print Server is a "dumb pipe" that receives print jobs and routes them to the correct printer. Business logic (templates, job tracking, retries) lives in the calling application.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         BruFLOW                                 │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────┐    │
│  │ Label        │   │ Print Queue  │   │ Image            │    │
│  │ Templates    │──▶│ Management   │──▶│ Rendering        │    │
│  │ (field maps) │   │ UI           │   │ (PNG output)     │    │
│  └──────────────┘   └──────────────┘   └────────┬─────────┘    │
│                                                  │              │
└──────────────────────────────────────────────────┼──────────────┘
                                                   │
                                                   ▼ HTTP POST
┌─────────────────────────────────────────────────────────────────┐
│                      Print Server                               │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────┐    │
│  │ Receive      │   │ Validate     │   │ Send to          │    │
│  │ Image/Job    │──▶│ (size, type) │──▶│ Printer          │    │
│  └──────────────┘   └──────────────┘   └──────────────────┘    │
│                                                                 │
│  Printers: Brother QL-720NW (labels), CUPS (documents)         │
└─────────────────────────────────────────────────────────────────┘
```

---

## Current Print Server API

### Base URL
```
http://printserver.local:5001/v1/
```

### Endpoints

#### List Printers
```http
GET /v1/printers
```

**Response:**
```json
{
  "printers": [
    {
      "id": "label-main",
      "name": "Brother QL-720NW",
      "type": "brother_ql",
      "status": "ready",
      "supported_content_types": ["image/png"]
    }
  ]
}
```

#### Get Printer Status
```http
GET /v1/printers/{printer_id}/status
```

**Response:**
```json
{
  "id": "label-main",
  "status": "ready",
  "queue_length": 0
}
```

#### Submit Print Job
```http
POST /v1/printers/{printer_id}/print
Content-Type: application/json

{
  "content_type": "image/png",
  "content": "<base64-encoded-image>",
  "copies": 1,
  "metadata": {
    "source": "bruflow",
    "source_id": "job-uuid-here"
  }
}
```

**Response (Success):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "printer_id": "label-main"
}
```

**Response (Error):**
```json
{
  "error": "Printer offline",
  "code": 503
}
```

#### Health Check
```http
GET /v1/health
```

---

## Image Requirements (Current)

For Brother QL label printers:

| Requirement | Value | Notes |
|-------------|-------|-------|
| Width | 720 pixels | Exact - validation will reject otherwise |
| Height | Variable | Depends on label length |
| Format | PNG | Monochrome (1-bit or grayscale converted) |
| Color | Black & White | No grayscale gradients |

**Validation happens before queuing.** Invalid images return HTTP 400 immediately.

---

## Alignment Discussion: Template Rendering

### BruFLOW's Expected Flow
```
BruFLOW sends: {template: "box_label.lbx", data: {JobNum: "WO-123", ...}}
Print Server: Loads .lbx, populates fields, renders, prints
```

### Current Print Server Flow
```
BruFLOW sends: {content: "<base64 PNG>", copies: 1}
Print Server: Validates image, sends to printer
```

### Options to Resolve

#### Option A: BruFLOW Renders Templates (Recommended)
- BruFLOW uses a client-side library to render .lbx → PNG
- Sends rendered PNG to Print Server
- Print Server stays simple and hardware-focused
- **Pro:** Clean separation, Print Server is truly swappable
- **Con:** Requires rendering capability in BruFLOW

#### Option B: Print Server Renders Templates
- Print Server loads .lbx files from disk
- Uses b-PAC SDK or custom renderer
- **Pro:** Matches BruFLOW's doc expectations
- **Con:** Ties Print Server to Brother's proprietary format, Windows dependency (b-PAC is Windows-only)

#### Option C: Hybrid - Support Both
- Add `/print-label` endpoint that accepts template + data
- Keep `/v1/printers/{id}/print` for raw images
- **Pro:** Flexibility
- **Con:** Complexity

### Recommendation

**Option A** keeps things cleanest. The Print Server should be printer-agnostic. Template rendering is business logic that belongs in the application layer.

**Proposed BruFLOW change:** Render labels to PNG before sending. This could be:
- Server-side (Node canvas, Puppeteer, etc.)
- Use a label rendering service
- Pre-render templates to SVG, inject data client-side, rasterize

---

## Proposed API Additions (for BruFLOW compatibility)

### Add endpoint alias
```http
POST /print-label
```

Maps to `/v1/printers/{default}/print` for convenience.

### Add batch endpoint
```http
POST /v1/batch
Content-Type: application/json

{
  "jobs": [
    {"printer_id": "label-main", "content": "...", "copies": 1},
    {"printer_id": "label-main", "content": "...", "copies": 2}
  ]
}
```

---

## Hardware Configuration

### Current Setup
| Item | Value |
|------|-------|
| Server | Dell Mini Tower / NUC |
| OS | Ubuntu Server 24.04 LTS |
| Container | Docker + Portainer |
| Label Printer | Brother QL-720NW (network) |
| Document Printer | Via CUPS |

### Network
| Service | Port | URL |
|---------|------|-----|
| Print API | 5001 | `http://printserver:5001/v1/` |
| Cockpit | 9090 | `https://printserver:9090` |
| Portainer | 9000 | `http://printserver:9000` |
| CUPS | 631 | `http://printserver:631` |

---

## Integration Checklist

### Print Server Team
- [ ] Deploy Print Server to hardware
- [ ] Configure Brother QL-720NW printer
- [ ] Test with sample PNG images
- [ ] Provide final endpoint URL to BruFLOW team
- [ ] Add `/print-label` convenience endpoint (if requested)

### BruFLOW Team
- [ ] Implement template → PNG rendering
- [ ] Update `sys_integrations` with Print Server URL
- [ ] Update API calls to match Print Server contract
- [ ] Test end-to-end with real print jobs

### Joint
- [ ] Agree on template rendering approach
- [ ] Define error code mapping
- [ ] Set up monitoring/alerting

---

## Sample Integration Code

### BruFLOW → Print Server (TypeScript)
```typescript
async function sendToPrintServer(
  imageBase64: string,
  copies: number,
  jobId: string
): Promise<{success: boolean, jobId?: string, error?: string}> {
  const config = await getIntegrationConfig('label_printer');

  try {
    const response = await fetch(`${config.endpoint}/v1/printers/label-main/print`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        content_type: 'image/png',
        content: imageBase64,
        copies: copies,
        metadata: {
          source: 'bruflow',
          source_id: jobId
        }
      }),
      signal: AbortSignal.timeout(config.timeout_ms)
    });

    const data = await response.json();

    if (!response.ok) {
      return {success: false, error: data.error || `HTTP ${response.status}`};
    }

    return {success: true, jobId: data.job_id};
  } catch (err) {
    return {success: false, error: err.message};
  }
}
```

---

## Questions for Discussion

1. **Template Rendering:** Should BruFLOW render or Print Server render?
2. **Template Format:** Stick with .lbx or move to something more portable (SVG, HTML)?
3. **Fallback:** What happens if Print Server is down? PDF download only?
4. **Multiple Printers:** How does BruFLOW select which printer to use?

---

## Contact

- **Print Server:** [Your contact]
- **BruFLOW:** [BruFLOW team contact]
- **Hardware Setup:** [IT contact]

---

## Appendix: Print Server Configuration

### config/default.yaml
```yaml
server:
  host: "0.0.0.0"
  port: 5001

printers:
  label-main:
    type: brother_ql
    name: "Brother QL-720NW"
    connection:
      type: network
      host: "192.168.1.100"
      port: 9100
    options:
      label_size: "62x100"

  document:
    type: cups
    name: "Office Printer"
    cups_name: "HP_LaserJet"
```

### Environment Variables
```bash
CONFIG_FILE=/app/config/production.yaml
LOG_LEVEL=INFO
```

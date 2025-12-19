# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Print Gateway Server - a centralized REST API server for handling print requests from internal web applications.

**Target Platform:** Ubuntu Server 24.04 LTS or Debian 13+ (Dell Mini Tower) running Docker containers

**Python:** 3.11+ required

## Commands

```bash
# Install dependencies
pip install -e .                    # Core only
pip install -e ".[dev]"             # With dev tools
pip install -e ".[all-printers]"    # With all printer drivers

# Run server (uses mock printers by default)
python -m src.main
python -m src.main -c config/local.yaml  # Custom config

# Run tests
pytest
pytest tests/test_validation.py -v       # Single file
pytest -k test_valid_monochrome          # By name pattern

# Lint (line-length: 100, target: py311)
ruff check src/                          # Check code
ruff check src/ --fix                    # Auto-fix issues

# Docker
docker compose -f docker/docker-compose.yaml up --build
```

## Architecture

```
src/
├── api/           # FastAPI routes and server setup
├── printers/      # Printer interface + adapters (mock, brother_ql, cups)
├── validation/    # Image/PDF validation (critical for labels)
├── queue/         # In-memory job queue per printer
├── config.py      # YAML config loading
├── routing.py     # Intent-based print job routing
├── startup.py     # Startup checks and banner
└── main.py        # Entry point
config/            # YAML configs (default.yaml, shop.yaml.example)
```

### Printer Adapter Pattern

All printers implement `PrinterBase` (src/printers/base.py):
- `get_status()` → `PrinterStatus` (READY, BUSY, OFFLINE, ERROR)
- `print(job: PrintJob)` → `PrintResult`
- `validate_job(job)` → `tuple[bool, str]` - Pre-queue validation
- `supported_content_types` - MIME types accepted

Available adapters (src/config.py `ADAPTER_TYPES`):
- `mock_label` / `mock_document` - Development/testing
- `brother_ql` - Brother QL series label printers (USB)
- `cups` - Document printers via CUPS

Printers are registered via `PrinterRegistry` (src/printers/registry.py).

### Intent-Based Routing (src/routing.py)

Maps semantic intents to physical printers, allowing clients to request prints by purpose:
```yaml
routing:
  shipping-label: label
  invoice: document
  price-tag: label
```

Use `POST /v1/print?intent=shipping-label` - client doesn't need to know printer IDs.

### Configuration

YAML config files in `config/`. Server loads in order:
1. CLI `-c` path
2. `CONFIG_FILE` env var
3. `config/local.yaml`
4. `config/default.yaml`

## Critical Requirements

### Label Image Validation (src/validation/image.py)
- Must be exactly 720px wide (for QL-720 at 300 DPI on 62mm tape)
- Must be monochrome PNG (black/white only, modes: 1, L, RGB accepted)
- Validation happens BEFORE queuing

Validation error codes: `INVALID_IMAGE`, `INVALID_FORMAT`, `INVALID_WIDTH`, `NOT_MONOCHROME`

### API Error Codes
- 400: Invalid format/validation failure
- 404: Printer not found
- 503: Printer offline

## Key API Endpoints (base: `/v1`)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/status` | GET | All printer statuses |
| `/print/label` | POST | Print PNG to label printer |
| `/print/document` | POST | Print PDF to document printer |
| `/print` | POST | Unified intent-based endpoint |
| `/queue` | GET | Queue status |
| `/job/{id}` | GET/DELETE | Job status / cancel |

## Documentation & Scripts

- `docs/linux-setup.md` - Fresh Ubuntu install to working server
- `docs/checklist.md` - Printable setup checklist
- `install/autoinstall.yaml` - Hands-off Ubuntu installer config
- `install/print-server.service` - Systemd service (non-Docker)
- `scripts/bootstrap.sh` - First-boot setup (Docker, Portainer, Cockpit, CUPS)
- `scripts/set_static_ip.sh` - Set static IP on new network
- `scripts/revert_to_dhcp.sh` - Revert to DHCP
- `scripts/install_bare_metal.sh` - Install without Docker
- `scripts/generate_test_label.py` - Create test PNG images
- `scripts/smoke_test.sh` - Verify server is working
- `Print_Gateway_Server_Specification_v2.md` - Full technical requirements

## Management UIs (after bootstrap)

| Service | Port | URL |
|---------|------|-----|
| Cockpit | 9090 | `https://printserver:9090` (system) |
| Portainer | 9000 | `http://printserver:9000` (containers) |
| Print API | 5001 | `http://printserver:5001/v1/` |
| CUPS | 631 | `http://printserver:631` (doc printer) |

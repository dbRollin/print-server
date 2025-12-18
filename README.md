# Print Gateway Server

A centralized REST API server for handling print requests from internal web applications. Supports label printers (Brother QL series) and document printers (via CUPS).

## Features

- REST API for print job submission
- Brother QL label printer support (USB/network)
- CUPS integration for document printing
- Per-printer job queues with status tracking
- Intent-based routing (e.g., "shipping-label" → label printer)
- Image validation (720px width, monochrome PNG for labels)
- Docker deployment with management UIs (Portainer, Cockpit)

## Quick Start

### Prerequisites

- Ubuntu Server 24.04 LTS or Debian 13+
- Docker

### Installation

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/print-server.git
cd print-server

# Run with Docker (uses mock printers by default)
docker compose -f docker/docker-compose.yaml up -d

# Test it
curl http://localhost:5001/v1/health
```

### Full Server Setup

For a dedicated print server machine, see [docs/linux-setup.md](docs/linux-setup.md) or use the automated installer in `usb-installer/`.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/health` | GET | Health check |
| `/v1/status` | GET | All printer statuses |
| `/v1/print/label` | POST | Print PNG to label printer |
| `/v1/print/document` | POST | Print PDF to document printer |
| `/v1/print` | POST | Unified intent-based endpoint |
| `/v1/queue` | GET | Queue status |
| `/v1/job/{id}` | GET | Job status |
| `/v1/job/{id}` | DELETE | Cancel queued job |

## Configuration

Copy and edit the example config:

```bash
cp config/shop.yaml.example config/local.yaml
nano config/local.yaml
```

See `config/default.yaml` for all options.

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run locally (mock printers)
python -m src.main

# Run tests
pytest

# Lint
ruff check src/
```

## Architecture

```
src/
├── api/           # FastAPI routes and server
├── printers/      # Printer adapters (mock, brother_ql, cups)
├── validation/    # Image/PDF validation
├── queue/         # Job queue management
├── routing.py     # Intent-based routing
└── main.py        # Entry point
```

All printers implement the `PrinterBase` interface. Add new printers by creating an adapter in `src/printers/`.

## Management UIs

After running `scripts/bootstrap.sh`:

| Service | Port | Purpose |
|---------|------|---------|
| Print API | 5001 | REST API |
| Portainer | 9000 | Container management |
| Cockpit | 9090 | System management |
| CUPS | 631 | Document printer config |

## Label Requirements

Label images must be:
- **Width:** Exactly 720px
- **Format:** PNG
- **Color:** Monochrome (black and white only)

## License

MIT

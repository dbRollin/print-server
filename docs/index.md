# Print Server Documentation

## Setup Guides

- [Linux Server Setup](linux-setup.md) - Fresh Ubuntu install to working print server
- [Quick Checklist](checklist.md) - Printable checklist for setup day

## What You Get After Setup

| Service | Port | Purpose |
|---------|------|---------|
| **Cockpit** | 9090 | System management (updates, network, storage) |
| **Portainer** | 9000 | Container management (deploy/manage apps) |
| **Print Server** | 5001 | The print API |
| **CUPS** | 631 | Document printer management |

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/bootstrap.sh` | First-boot setup (Docker, Portainer, Cockpit, CUPS) |
| `scripts/set_static_ip.sh` | Set static IP when moving to new network |
| `scripts/revert_to_dhcp.sh` | Revert to DHCP |
| `scripts/install_bare_metal.sh` | Install without Docker |
| `scripts/generate_test_label.py` | Create test PNG images |
| `scripts/smoke_test.sh` | Verify server is working |

## Configuration

Example configs in `/config/`:
- `default.yaml` - Mock printers for development
- `shop.yaml.example` - Production template

## API Reference

Base URL: `http://<server-ip>:5001/v1`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/status` | GET | All printer status |
| `/queue` | GET | Queue status |
| `/print/label` | POST | Print PNG to label printer |
| `/print/document` | POST | Print PDF to document printer |
| `/job/{id}` | GET | Job status |
| `/job/{id}` | DELETE | Cancel queued job |

## Specification

Full technical requirements: `Print_Gateway_Server_Specification_v2.md`

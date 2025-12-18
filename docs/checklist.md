# Print Server Setup Checklist

Print this out for setup day.

## Before You Start

- [ ] Computer (Beelink, Pi, or similar)
- [ ] USB drive (8GB+) for Ubuntu installer
- [ ] Keyboard + monitor (temporary, for install only)
- [ ] Network cable
- [ ] Brother QL-720 label printer + USB cable

## Create Bootable USB

- [ ] Download Ubuntu Server 24.04 LTS
- [ ] Download Rufus (Windows)
- [ ] Create bootable USB

## Install Ubuntu

- [ ] Boot from USB
- [ ] Install Ubuntu Server
- [ ] Hostname: `printserver`
- [ ] Username: `print`
- [ ] Password: ____________________
- [ ] **Enable OpenSSH server**
- [ ] Reboot, remove USB

## Bootstrap (from another computer)

SSH in:
```
ssh print@printserver.local
```

Run bootstrap:
```
curl -fsSL https://YOUR_REPO/scripts/bootstrap.sh | bash
```

- [ ] Bootstrap completed
- [ ] Logged out and back in (for Docker permissions)

## Verify Management UIs

From a browser on the network:

- [ ] Cockpit works: `https://printserver.local:9090`
- [ ] Portainer works: `http://printserver.local:9000`
- [ ] Created Portainer admin account

## Deploy Print Server

- [ ] Plugged in label printer
- [ ] Found USB device: `lsusb | grep Brother`
- [ ] Device ID: ____________________
- [ ] Created `config/local.yaml`
- [ ] Started container: `docker compose -f docker/docker-compose.prod.yaml up -d`
- [ ] Health check works: `curl http://localhost:5001/v1/health`

## Test Print

- [ ] Created test image (720px wide, black/white PNG)
- [ ] Label printed successfully

## Moving to Shop (later)

When you move this machine to the shop network:

1. Plug in power + ethernet
2. Find it: `ping printserver.local`
3. SSH in: `ssh print@printserver.local`
4. Set static IP: `./scripts/set_static_ip.sh`

Shop IP: ____________________

---

## Quick Reference Card

| What | Where |
|------|-------|
| SSH | `ssh print@printserver.local` |
| Cockpit (system) | `https://printserver:9090` |
| Portainer (containers) | `http://printserver:9000` |
| Print API | `http://printserver:5001` |
| CUPS (doc printer) | `http://printserver:631` |

| Script | Purpose |
|--------|---------|
| `./scripts/set_static_ip.sh` | Set static IP |
| `./scripts/revert_to_dhcp.sh` | Back to DHCP |
| `./scripts/smoke_test.sh` | Test the API |

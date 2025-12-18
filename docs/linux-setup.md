# Linux Print Server Setup

Fresh machine to working print server with management UIs.

## What You'll Get

| Service | Port | Purpose |
|---------|------|---------|
| **Print Server** | 5001 | The print API |
| **Portainer** | 9000 | Container management (deploy/manage apps) |
| **Cockpit** | 9090 | System management (updates, network, disks) |
| **CUPS** | 631 | Document printer management |

All accessible via web browser from any device on the network.

## Hardware

Any of these work:

| Option | Cost | Notes |
|--------|------|-------|
| Dell/HP/Lenovo Mini PC | $50-80 used | Business-grade, reliable |
| Beelink Mini S12 Pro | ~$130 | Overkill but solid |
| Raspberry Pi 4/5 (2GB+) | ~$45-80 | Small, silent |
| Old laptop/desktop | Free | Anything from last 10 years |

## OS Options

| OS | Recommendation |
|----|----------------|
| **Debian 13** | Recommended - stable installer, fewer issues |
| Ubuntu Server 24.04 | Works, but installer has known bugs on some hardware |

If Ubuntu installer crashes (common on Dell hardware), use Debian instead.

---

## Step 1: Create Bootable USB

**Download:**
- **Debian 13**: https://cdimage.debian.org/debian-cd/current/amd64/iso-dvd/
- Ubuntu Server 24.04: https://ubuntu.com/download/server

**Flash with Rufus** (Windows):
1. Download Rufus: https://rufus.ie/
2. Insert USB drive (8GB+)
3. Open Rufus, select ISO, select USB
4. Click Start (use ISO mode if asked)

---

## Step 2: Install OS

1. Boot from USB (F12/F2/Del during startup)
2. Follow installer prompts:

| Setting | Value |
|---------|-------|
| Language | English |
| Hostname | `printserver` |
| Username | Your choice (e.g., `admin`) |
| Password | Remember this! |
| Disk | Use entire disk |
| SSH | **Install SSH server** |
| Desktop | **Don't install** (select SSH + standard utilities only) |

3. Reboot, remove USB

---

## Step 3: Connect and Setup Base

**SSH from another computer:**
```bash
ssh username@<IP-address>
```

**Install sudo** (Debian minimal doesn't include it):
```bash
su -
apt update && apt install -y sudo
usermod -aG sudo username
exit
exit
# SSH back in
```

**Install essentials:**
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl git htop
```

---

## Step 4: Install Docker

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
```

**Log out and back in** for Docker permissions to take effect.

---

## Step 5: Install Management UIs

**Portainer** (container management):
```bash
sudo docker volume create portainer_data
sudo docker run -d --name portainer --restart=always \
  -p 9000:9000 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v portainer_data:/data \
  portainer/portainer-ce:latest
```

**Cockpit** (system management):
```bash
sudo apt install -y cockpit
sudo systemctl enable --now cockpit.socket
```

**CUPS** (document printing):
```bash
sudo apt install -y cups
sudo usermod -aG lpadmin $USER
sudo cupsctl --remote-admin
```

**Avahi** (for .local hostname):
```bash
sudo apt install -y avahi-daemon
```

---

## Step 6: Setup USB Printer

**Find printer:**
```bash
lsusb | grep Brother
```

**Set permissions:**
```bash
sudo chmod 666 /dev/usb/lp0
```

**Make permanent (udev rule):**
```bash
echo 'SUBSYSTEM=="usb", ATTR{idVendor}=="04f9", MODE="0666", GROUP="plugdev"' | sudo tee /etc/udev/rules.d/99-brother-ql.rules
sudo udevadm control --reload-rules
```

---

## Step 7: Deploy Print Server

**Clone repo:**
```bash
cd ~
git clone https://github.com/YOUR_USERNAME/print-server.git
cd print-server
```

**Create config:**
```bash
cp config/shop.yaml.example config/local.yaml
nano config/local.yaml
```

Update the device path based on `lsusb` output.

**Deploy:**
```bash
sudo docker compose -f docker/docker-compose.prod.yaml up -d --build
```

**Test:**
```bash
curl http://localhost:5001/v1/health
curl http://localhost:5001/v1/status
```

---

## Quick Reference

| Task | Command |
|------|---------|
| SSH in | `ssh user@printserver.local` |
| System management | `https://printserver:9090` |
| Container management | `http://printserver:9000` |
| View logs | `sudo docker logs docker-print-server-1 --tail 50` |
| Restart | `sudo docker compose -f docker/docker-compose.prod.yaml restart` |
| Check status | `curl http://localhost:5001/v1/status` |
| Test print | `curl -X POST -F "file=@test.png" http://localhost:5001/v1/print/label` |

---

## Troubleshooting

### Ubuntu installer crashes
Use Debian instead. Known bug (#2045710) with Ubuntu 24.04 installer on Dell hardware.

### Printer not detected
```bash
lsusb | grep Brother
# If nothing, unplug and replug USB
dmesg | tail -20  # Check for errors
```

### Docker can't access USB printer
Add `privileged: true` to docker-compose.prod.yaml:
```yaml
services:
  print-server:
    privileged: true
    # ... rest of config
```

### Print job fails with "No such device"
```bash
# Check device exists
ls -la /dev/usb/lp0

# Check permissions
sudo chmod 666 /dev/usb/lp0

# Restart container
sudo docker compose -f docker/docker-compose.prod.yaml restart
```

### sudo: command not found
```bash
su -
apt install -y sudo
usermod -aG sudo username
exit
```

### Can't find printserver.local
```bash
# Check avahi is running
sudo systemctl status avahi-daemon

# Use IP directly - check your router's DHCP list
```

---

## See Also

- [CLI Cheatsheet](cli-cheatsheet.md) - Common commands reference
- [API Documentation](index.md) - Print server API endpoints

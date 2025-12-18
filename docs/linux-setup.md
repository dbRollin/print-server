# Linux Print Server Setup

Fresh machine to working print server with management UIs.

## What You'll Get

After setup, you'll have:

| Service | Port | Purpose |
|---------|------|---------|
| **Cockpit** | 9090 | System management (updates, network, disks) |
| **Portainer** | 9000 | Container management (deploy/manage apps) |
| **Print Server** | 5001 | The print API |
| **CUPS** | 631 | Document printer management |

All accessible via web browser from any device on the network.

## Hardware

Any of these work:

| Option | Cost | Notes |
|--------|------|-------|
| Beelink Mini S12 Pro | ~$130 | Great choice, overkill but solid |
| Raspberry Pi 4/5 (2GB+) | ~$45-80 | Small, silent, works well |
| Old laptop/desktop | Free | Anything from last 10 years |
| Dell/HP/Lenovo Mini PC | $50-80 used | Business-grade, reliable |

## Step 1: Create Bootable USB

**On Windows:**

1. Download Ubuntu Server 24.04 LTS:
   https://ubuntu.com/download/server

2. Download Rufus:
   https://rufus.ie/

3. Insert USB drive (8GB+), run Rufus:
   - Select your USB drive
   - Select the Ubuntu ISO
   - Click Start

## Step 2: Install Ubuntu

1. Boot from USB (F12/F2/Del during startup for boot menu)
2. Choose "Install Ubuntu Server"
3. Follow prompts:
   - Language: English
   - Keyboard: Your layout
   - Network: DHCP (default)
   - Storage: Use entire disk
   - Profile:
     - Name: `printserver`
     - Server name: `printserver`
     - Username: `print`
     - Password: (remember this!)
   - SSH: **Install OpenSSH server** ← Important!
   - Featured snaps: Skip

4. Reboot, remove USB

## Step 3: Bootstrap (From Another Computer)

SSH in:
```bash
ssh print@printserver.local
# or: ssh print@<IP address shown during install>
```

Run the bootstrap script:
```bash
curl -fsSL https://raw.githubusercontent.com/YOUR_REPO/print-server/main/scripts/bootstrap.sh | bash
```

This installs:
- Docker
- Portainer (container management)
- Cockpit (system management)
- CUPS (document printing)
- USB printer rules

**Log out and back in when done** (for Docker permissions):
```bash
exit
# Then SSH back in
```

## Step 4: Access Management UIs

Open a browser on any device on the same network:

- **Cockpit**: `https://printserver.local:9090`
  - Login with your `print` user credentials
  - Manage system updates, networking, storage

- **Portainer**: `http://printserver.local:9000`
  - Create admin account on first visit
  - This is where you manage containers

## Step 5: Deploy Print Server

```bash
# Find label printer
lsusb | grep Brother
# Note the device (e.g., Bus 001 Device 004: ID 04f9:2044)

# Configure
cd ~/print-server
cp config/shop.yaml.example config/local.yaml
nano config/local.yaml
# Update device path based on lsusb output

# Deploy
docker compose -f docker/docker-compose.prod.yaml up -d

# Test
curl http://localhost:5001/v1/health
```

## Moving to a Different Network (e.g., Home → Shop)

The server uses DHCP by default, so it'll get an IP on any network.

**Find it:**
```bash
ping printserver.local
```

**Set static IP (optional but recommended for shop):**
```bash
cd ~/print-server
./scripts/set_static_ip.sh
```

**Revert to DHCP (if moving again):**
```bash
./scripts/revert_to_dhcp.sh
```

## Quick Reference

| Task | How |
|------|-----|
| SSH in | `ssh print@printserver.local` |
| System management | `https://printserver:9090` (Cockpit) |
| Container management | `http://printserver:9000` (Portainer) |
| View print server logs | `docker logs -f print-server` |
| Restart print server | `docker restart print-server` |
| Check printer status | `curl http://localhost:5001/v1/status` |
| Set static IP | `./scripts/set_static_ip.sh` |
| Revert to DHCP | `./scripts/revert_to_dhcp.sh` |

## Firewall (Optional)

If you want to restrict access:

```bash
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 5001/tcp  # Print server API
sudo ufw allow 9000/tcp  # Portainer
sudo ufw allow 9090/tcp  # Cockpit
sudo ufw allow 631/tcp   # CUPS
sudo ufw enable
```

## Troubleshooting

**Can't find printserver.local:**
- Check it's on the same network
- Try the IP directly (check your router's DHCP list)
- Make sure avahi-daemon is running: `sudo systemctl status avahi-daemon`

**Label printer not detected:**
```bash
lsusb | grep Brother
# If nothing, unplug and replug the USB
```

**Docker permission denied:**
```bash
# Did you log out and back in after bootstrap?
exit
# SSH back in
```

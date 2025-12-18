#!/bin/bash
# Print Server Bootstrap Script
# Run on fresh Ubuntu Server 24.04 LTS or Debian 13+
#
# Sets up:
#   - Docker (container runtime)
#   - Portainer (container management UI - port 9000)
#   - Cockpit (system management UI - port 9090)
#   - CUPS (document printing)
#   - udev rules (USB printer access)
#
# Usage: curl -fsSL https://raw.githubusercontent.com/YOUR_REPO/print-server/main/scripts/bootstrap.sh | bash

set -e

echo "============================================"
echo "  Print Server Bootstrap"
echo "  Base image setup: Docker + Management UIs"
echo "============================================"

# Check we're on Ubuntu or Debian
if ! grep -qE "(Ubuntu|Debian)" /etc/os-release 2>/dev/null; then
    echo "Warning: This script is designed for Ubuntu/Debian. Proceed anyway? (y/N)"
    read -r confirm
    [[ "$confirm" != "y" ]] && exit 1
fi

echo ""
echo "[1/8] Updating system..."
sudo apt update
sudo apt upgrade -y

echo ""
echo "[2/8] Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | sudo sh
    sudo usermod -aG docker "$USER"
    echo "  Docker installed."
else
    echo "  Docker already installed."
fi

echo ""
echo "[3/8] Installing Portainer (container management)..."
if ! sudo docker ps -a --format '{{.Names}}' | grep -q '^portainer$'; then
    sudo docker volume create portainer_data
    sudo docker run -d \
        --name portainer \
        --restart=always \
        -p 9000:9000 \
        -v /var/run/docker.sock:/var/run/docker.sock \
        -v portainer_data:/data \
        portainer/portainer-ce:latest
    echo "  Portainer installed on port 9000"
else
    echo "  Portainer already running."
fi

echo ""
echo "[4/8] Installing Cockpit (system management)..."
if ! command -v cockpit-bridge &> /dev/null; then
    sudo apt install -y cockpit
    sudo systemctl enable --now cockpit.socket
    echo "  Cockpit installed on port 9090"
else
    echo "  Cockpit already installed."
fi

echo ""
echo "[5/8] Installing CUPS (document printing)..."
sudo apt install -y cups
sudo usermod -aG lpadmin "$USER"
sudo cupsctl --remote-admin
echo "  CUPS installed on port 631"

echo ""
echo "[6/8] Setting up udev rules for Brother label printer..."
sudo tee /etc/udev/rules.d/99-brother-ql.rules > /dev/null << 'EOF'
# Brother QL-series label printers
SUBSYSTEM=="usb", ATTR{idVendor}=="04f9", MODE="0666", GROUP="plugdev"
EOF
sudo udevadm control --reload-rules

echo ""
echo "[7/8] Installing utilities..."
sudo apt install -y git curl htop vim avahi-daemon

echo ""
echo "[8/8] Cloning print-server repository..."
cd ~
if [ -d "print-server" ]; then
    echo "  print-server directory exists, pulling latest..."
    cd print-server && git pull
else
    echo "  Enter the git repository URL (or press Enter to skip):"
    read -r REPO_URL
    if [ -n "$REPO_URL" ]; then
        git clone "$REPO_URL" print-server
    else
        echo "  Skipped. Clone manually later."
    fi
fi

# Get the machine's IP
IP_ADDR=$(hostname -I | awk '{print $1}')

echo ""
echo "============================================"
echo "  Bootstrap Complete!"
echo "============================================"
echo ""
echo "  Access your server:"
echo ""
echo "  Cockpit (system):     https://$IP_ADDR:9090"
echo "  Portainer (containers): http://$IP_ADDR:9000"
echo "  CUPS (printers):      http://$IP_ADDR:631"
echo ""
echo "  Or by hostname:"
echo "  ssh print@printserver.local"
echo ""
echo "============================================"
echo ""
echo "IMPORTANT: Log out and back in for Docker permissions!"
echo ""
echo "Next steps:"
echo ""
echo "1. Log out and back in:"
echo "   exit"
echo ""
echo "2. Access Portainer at http://$IP_ADDR:9000"
echo "   - Create admin account on first visit"
echo "   - This is where you'll deploy the print server container"
echo ""
echo "3. Find your label printer:"
echo "   lsusb | grep Brother"
echo ""
echo "4. Deploy print server:"
echo "   cd ~/print-server"
echo "   cp config/shop.yaml.example config/local.yaml"
echo "   nano config/local.yaml  # add your printer device"
echo "   docker compose -f docker/docker-compose.prod.yaml up -d"
echo ""
echo "5. Test it:"
echo "   curl http://localhost:5001/v1/health"
echo ""

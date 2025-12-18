#!/bin/bash
# Print Server Setup Script
# Run this after fresh Ubuntu Server 24.04 install
#
# This script sets up:
#   - Docker (container runtime)
#   - Portainer (container management UI - port 9000)
#   - Cockpit (system management UI - port 9090)
#   - CUPS (document printing - port 631)
#   - udev rules (USB printer access)

set -e

echo ""
echo "========================================================"
echo "  PRINT SERVER SETUP"
echo "========================================================"
echo ""

# Check we're on Ubuntu
if ! grep -q "Ubuntu" /etc/os-release 2>/dev/null; then
    echo "WARNING: This script is designed for Ubuntu."
    echo "Proceed anyway? (y/N)"
    read -r confirm
    [[ "$confirm" != "y" ]] && exit 1
fi

# Determine number of steps
TOTAL_STEPS=7
CURRENT_STEP=0

next_step() {
    CURRENT_STEP=$((CURRENT_STEP + 1))
    echo ""
    echo "--------------------------------------------------------"
    echo "  [$CURRENT_STEP/$TOTAL_STEPS] $1"
    echo "--------------------------------------------------------"
}

next_step "Updating system packages"
sudo apt update
sudo apt upgrade -y

next_step "Installing Docker"
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | sudo sh
    sudo usermod -aG docker "$USER"
    echo "  [OK] Docker installed"
else
    echo "  [OK] Docker already installed"
fi

next_step "Installing Portainer (container management UI)"
# Need sudo for docker since user group not active yet
if ! sudo docker ps -a --format '{{.Names}}' 2>/dev/null | grep -q '^portainer$'; then
    sudo docker volume create portainer_data
    sudo docker run -d \
        --name portainer \
        --restart=always \
        -p 9000:9000 \
        -v /var/run/docker.sock:/var/run/docker.sock \
        -v portainer_data:/data \
        portainer/portainer-ce:latest
    echo "  [OK] Portainer running on port 9000"
else
    echo "  [OK] Portainer already running"
fi

next_step "Installing Cockpit (system management UI)"
if ! command -v cockpit-bridge &> /dev/null; then
    sudo apt install -y cockpit
    sudo systemctl enable --now cockpit.socket
    echo "  [OK] Cockpit running on port 9090"
else
    echo "  [OK] Cockpit already installed"
fi

next_step "Installing CUPS (document printing)"
sudo apt install -y cups
sudo usermod -aG lpadmin "$USER"
sudo cupsctl --remote-admin
echo "  [OK] CUPS running on port 631"

next_step "Setting up USB printer access"
sudo tee /etc/udev/rules.d/99-brother-ql.rules > /dev/null << 'EOF'
# Brother QL-series label printers - allow non-root access
SUBSYSTEM=="usb", ATTR{idVendor}=="04f9", MODE="0666", GROUP="plugdev"
EOF
sudo udevadm control --reload-rules
echo "  [OK] Brother printer udev rules installed"

next_step "Installing utilities"
sudo apt install -y git curl htop vim avahi-daemon
echo "  [OK] Utilities installed"

# Get server IP
IP_ADDR=$(hostname -I | awk '{print $1}')

echo ""
echo "========================================================"
echo "  SETUP COMPLETE!"
echo "========================================================"
echo ""
echo "  Your server is ready. Access it at:"
echo ""
echo "    Cockpit (system):       https://$IP_ADDR:9090"
echo "    Portainer (containers): http://$IP_ADDR:9000"
echo "    CUPS (printers):        http://$IP_ADDR:631"
echo ""
echo "  Or by hostname (from other computers on network):"
echo ""
echo "    https://printserver.local:9090"
echo "    http://printserver.local:9000"
echo ""
echo "========================================================"
echo ""
echo "  >>> IMPORTANT: LOG OUT AND BACK IN NOW <<<"
echo "  >>> (for Docker permissions to take effect) <<<"
echo ""
echo "  Run: exit"
echo "  Then SSH back in: ssh print@printserver.local"
echo ""
echo "========================================================"
echo ""
echo "  NEXT STEPS (after logging back in):"
echo ""
echo "  1. Copy print-server files to server (from your PC):"
echo "     scp -r /path/to/print-server print@printserver.local:~/"
echo ""
echo "  2. Configure and start (on server via SSH):"
echo "     cd ~/print-server"
echo "     cp config/shop.yaml.example config/local.yaml"
echo "     docker compose -f docker/docker-compose.prod.yaml up -d"
echo ""
echo "  3. Test it:"
echo "     curl http://localhost:5001/v1/health"
echo ""
echo "========================================================"

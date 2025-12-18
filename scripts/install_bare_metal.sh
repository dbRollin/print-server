#!/bin/bash
# Install print server directly (no Docker)
# Run as the 'print' user on Ubuntu Server
#
# Usage: ./scripts/install_bare_metal.sh

set -e

INSTALL_DIR="$HOME/print-server"
VENV_DIR="$INSTALL_DIR/.venv"

echo "========================================"
echo "  Print Server - Bare Metal Install"
echo "========================================"

# Check we're not root
if [ "$EUID" -eq 0 ]; then
    echo "Don't run as root. Run as the 'print' user."
    exit 1
fi

# Check we're in the right directory
if [ ! -f "src/main.py" ]; then
    echo "Run this script from the print-server directory"
    exit 1
fi

INSTALL_DIR=$(pwd)

echo ""
echo "[1/6] Installing system dependencies..."
sudo apt update
sudo apt install -y python3 python3-venv python3-pip cups libcups2-dev

echo ""
echo "[2/6] Creating virtual environment..."
python3 -m venv "$VENV_DIR"

echo ""
echo "[3/6] Installing Python packages..."
"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install -e ".[all-printers]"

echo ""
echo "[4/6] Setting up udev rules..."
sudo tee /etc/udev/rules.d/99-brother-ql.rules > /dev/null << 'EOF'
SUBSYSTEM=="usb", ATTR{idVendor}=="04f9", MODE="0666", GROUP="plugdev"
EOF
sudo udevadm control --reload-rules

echo ""
echo "[5/6] Installing systemd service..."
sudo cp install/print-server.service /etc/systemd/system/
sudo sed -i "s|/home/print/print-server|$INSTALL_DIR|g" /etc/systemd/system/print-server.service
sudo sed -i "s|User=print|User=$USER|g" /etc/systemd/system/print-server.service
sudo sed -i "s|Group=print|Group=$USER|g" /etc/systemd/system/print-server.service
sudo systemctl daemon-reload

echo ""
echo "[6/6] Creating default config..."
if [ ! -f "config/local.yaml" ]; then
    cp config/default.yaml config/local.yaml
    echo "Created config/local.yaml - edit this with your printer settings"
fi

echo ""
echo "========================================"
echo "  Installation Complete!"
echo "========================================"
echo ""
echo "Next steps:"
echo ""
echo "1. Configure your printers:"
echo "   nano config/local.yaml"
echo ""
echo "2. Find your label printer:"
echo "   lsusb | grep Brother"
echo ""
echo "3. Start the service:"
echo "   sudo systemctl start print-server"
echo "   sudo systemctl enable print-server  # auto-start on boot"
echo ""
echo "4. Check status:"
echo "   sudo systemctl status print-server"
echo "   curl http://localhost:5001/v1/health"
echo ""
echo "Logs: sudo journalctl -u print-server -f"
echo ""

#!/bin/bash
# ============================================
#   CONFIGURE WI-FI
# ============================================
# Run this on the print server to set up Wi-Fi
#
# Usage: sudo ./configure-wifi.sh
#        sudo ./configure-wifi.sh "NetworkName" "password"

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo ""
echo "============================================"
echo "   CONFIGURE WI-FI"
echo "============================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Please run as root: sudo $0${NC}"
    exit 1
fi

# Get SSID
if [ -n "$1" ]; then
    SSID="$1"
else
    echo "Available Wi-Fi networks:"
    nmcli device wifi list 2>/dev/null || echo "(scanning...)"
    echo ""
    read -p "Enter Wi-Fi network name (SSID): " SSID
fi

# Get password
if [ -n "$2" ]; then
    PASSWORD="$2"
else
    read -sp "Enter Wi-Fi password: " PASSWORD
    echo ""
fi

echo ""
echo "Connecting to: $SSID"

# Try nmcli first (easier)
if command -v nmcli &> /dev/null; then
    nmcli device wifi connect "$SSID" password "$PASSWORD" && {
        echo -e "${GREEN}Connected successfully!${NC}"
        echo ""
        echo "Current IP:"
        ip -4 addr show | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | grep -v '127.0.0.1'
        exit 0
    }
fi

# Fall back to netplan
echo "Using netplan configuration..."

WIFI_INTERFACE=$(ip link | grep -oP 'wl\w+' | head -1)
if [ -z "$WIFI_INTERFACE" ]; then
    echo -e "${RED}No Wi-Fi interface found${NC}"
    exit 1
fi

cat > /etc/netplan/99-wifi.yaml << EOF
network:
  version: 2
  wifis:
    $WIFI_INTERFACE:
      dhcp4: true
      access-points:
        "$SSID":
          password: "$PASSWORD"
EOF

chmod 600 /etc/netplan/99-wifi.yaml

echo "Applying configuration..."
netplan apply

sleep 5

# Check connection
if ip addr show "$WIFI_INTERFACE" | grep -q "inet "; then
    echo -e "${GREEN}Connected successfully!${NC}"
    echo ""
    echo "Current IP:"
    ip -4 addr show | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | grep -v '127.0.0.1'
else
    echo -e "${YELLOW}Connection may still be establishing. Check with: ip addr${NC}"
fi

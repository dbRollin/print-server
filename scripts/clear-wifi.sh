#!/bin/bash
# ============================================
#   CLEAR WI-FI CREDENTIALS
# ============================================
# Run this before moving the server to a new location
# Removes saved Wi-Fi networks so credentials aren't exposed
#
# Usage: sudo ./clear-wifi.sh

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo ""
echo "============================================"
echo "   CLEAR WI-FI CREDENTIALS"
echo "============================================"
echo ""

if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Please run as root: sudo $0${NC}"
    exit 1
fi

echo "This will remove all saved Wi-Fi networks."
echo "You'll need to reconfigure Wi-Fi at the new location."
echo ""
read -p "Continue? (y/N): " CONFIRM

if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
    echo "Cancelled."
    exit 0
fi

# Clear NetworkManager connections
if command -v nmcli &> /dev/null; then
    echo "Clearing NetworkManager Wi-Fi connections..."
    nmcli connection show | grep wifi | awk '{print $1}' | while read conn; do
        echo "  Removing: $conn"
        nmcli connection delete "$conn" 2>/dev/null || true
    done
fi

# Clear netplan Wi-Fi configs
echo "Clearing netplan Wi-Fi configurations..."
rm -f /etc/netplan/*wifi*.yaml 2>/dev/null || true

# Clear wpa_supplicant
if [ -f /etc/wpa_supplicant/wpa_supplicant.conf ]; then
    echo "Clearing wpa_supplicant..."
    echo 'ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
country=US' > /etc/wpa_supplicant/wpa_supplicant.conf
fi

echo ""
echo -e "${GREEN}Wi-Fi credentials cleared!${NC}"
echo ""
echo "The server will now use ethernet only."
echo "Run configure-wifi.sh at the new location to set up Wi-Fi."

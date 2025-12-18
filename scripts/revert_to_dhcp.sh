#!/bin/bash
# Revert to DHCP (undo static IP)
# Use if you need to move the server to a different network
#
# Usage: ./scripts/revert_to_dhcp.sh

set -e

echo "========================================"
echo "  Revert to DHCP"
echo "========================================"
echo ""

IFACE=$(ip route | grep default | awk '{print $5}' | head -1)

read -p "Revert $IFACE to DHCP? (y/N): " CONFIRM

if [[ "$CONFIRM" != "y" && "$CONFIRM" != "Y" ]]; then
    echo "Cancelled."
    exit 0
fi

NETPLAN_FILE=$(ls /etc/netplan/*.yaml 2>/dev/null | head -1)
if [ -z "$NETPLAN_FILE" ]; then
    NETPLAN_FILE="/etc/netplan/01-dhcp.yaml"
fi

sudo tee "$NETPLAN_FILE" > /dev/null << EOF
network:
  version: 2
  ethernets:
    $IFACE:
      dhcp4: yes
EOF

echo "Applying DHCP configuration..."
sudo netplan apply

NEW_IP=$(hostname -I | awk '{print $1}')
echo ""
echo "Done! Now using DHCP."
echo "Current IP: $NEW_IP"
echo ""
echo "Find this machine with: ping printserver.local"

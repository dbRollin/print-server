#!/bin/bash
# Set static IP address
# Run this after moving the server to a new network
#
# Usage: ./scripts/set_static_ip.sh

set -e

echo "========================================"
echo "  Set Static IP Address"
echo "========================================"
echo ""

# Find the network interface
IFACE=$(ip route | grep default | awk '{print $5}' | head -1)
CURRENT_IP=$(hostname -I | awk '{print $1}')
CURRENT_GATEWAY=$(ip route | grep default | awk '{print $3}' | head -1)

echo "Current configuration:"
echo "  Interface: $IFACE"
echo "  IP: $CURRENT_IP"
echo "  Gateway: $CURRENT_GATEWAY"
echo ""

# Get new values
read -p "Enter static IP (e.g., 192.168.1.50): " NEW_IP
read -p "Enter gateway/router IP (e.g., 192.168.1.1): " NEW_GATEWAY
read -p "Enter DNS server [8.8.8.8]: " NEW_DNS
NEW_DNS=${NEW_DNS:-8.8.8.8}

echo ""
echo "New configuration:"
echo "  IP: $NEW_IP"
echo "  Gateway: $NEW_GATEWAY"
echo "  DNS: $NEW_DNS"
echo ""
read -p "Apply this configuration? (y/N): " CONFIRM

if [[ "$CONFIRM" != "y" && "$CONFIRM" != "Y" ]]; then
    echo "Cancelled."
    exit 0
fi

# Backup existing config
NETPLAN_FILE=$(ls /etc/netplan/*.yaml 2>/dev/null | head -1)
if [ -z "$NETPLAN_FILE" ]; then
    NETPLAN_FILE="/etc/netplan/01-static.yaml"
else
    sudo cp "$NETPLAN_FILE" "$NETPLAN_FILE.backup"
    echo "Backed up existing config to $NETPLAN_FILE.backup"
fi

# Write new config
sudo tee "$NETPLAN_FILE" > /dev/null << EOF
network:
  version: 2
  ethernets:
    $IFACE:
      dhcp4: no
      addresses:
        - $NEW_IP/24
      routes:
        - to: default
          via: $NEW_GATEWAY
      nameservers:
        addresses:
          - $NEW_DNS
EOF

echo ""
echo "Configuration written to $NETPLAN_FILE"
echo ""
echo "Applying... (you may lose connection briefly)"
echo ""

sudo netplan apply

echo "Done! New IP: $NEW_IP"
echo ""
echo "If you lost connection, reconnect to: ssh print@$NEW_IP"

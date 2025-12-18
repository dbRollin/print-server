#!/bin/bash
# ============================================
#   SHOW NETWORK INFO
# ============================================
# Displays current network configuration
#
# Usage: ./show-network.sh

echo ""
echo "============================================"
echo "   NETWORK INFORMATION"
echo "============================================"
echo ""

echo "HOSTNAME:"
echo "  $(hostname)"
echo ""

echo "IP ADDRESSES:"
ip -4 addr show | grep -oP '(?<=inet\s)\d+(\.\d+){3}/\d+' | while read ip; do
    iface=$(ip -4 addr | grep -B2 "$ip" | grep -oP '^\d+:\s+\K\w+')
    echo "  $iface: $ip"
done
echo ""

echo "DEFAULT GATEWAY:"
echo "  $(ip route | grep default | awk '{print $3}')"
echo ""

echo "DNS SERVERS:"
cat /etc/resolv.conf 2>/dev/null | grep nameserver | awk '{print "  " $2}'
echo ""

echo "NETWORK INTERFACES:"
ip link show | grep -E "^\d+:" | while read line; do
    iface=$(echo "$line" | awk -F': ' '{print $2}')
    state=$(echo "$line" | grep -oP 'state \K\w+')
    echo "  $iface: $state"
done
echo ""

echo "WI-FI STATUS:"
if command -v nmcli &> /dev/null; then
    nmcli device wifi list 2>/dev/null | head -5 || echo "  Not available"
else
    echo "  NetworkManager not installed"
fi
echo ""

echo "============================================"
echo "   SERVICE URLS"
echo "============================================"
IP=$(hostname -I | awk '{print $1}')
echo ""
echo "  Print API:   http://$IP:5001/v1/"
echo "  Cockpit:     https://$IP:9090"
echo "  Portainer:   http://$IP:9000"
echo "  CUPS:        http://$IP:631"
echo ""

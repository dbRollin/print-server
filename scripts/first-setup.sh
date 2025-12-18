#!/bin/bash
# ============================================
#   PRINT SERVER - FIRST SETUP WIZARD
# ============================================
# Run this when setting up the server at a new location
# Handles network config and cleans up old credentials
#
# Usage: sudo ./first-setup.sh

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

clear
echo ""
echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}   PRINT SERVER - FIRST SETUP WIZARD${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Please run as root: sudo $0${NC}"
    exit 1
fi

# ============================================
# STEP 1: Check for old Wi-Fi credentials
# ============================================

echo -e "${YELLOW}Step 1: Checking for saved Wi-Fi credentials...${NC}"
echo ""

OLD_WIFI_FOUND=false

# Check NetworkManager
if command -v nmcli &> /dev/null; then
    WIFI_CONNS=$(nmcli connection show | grep wifi | wc -l)
    if [ "$WIFI_CONNS" -gt 0 ]; then
        OLD_WIFI_FOUND=true
        echo "Found saved Wi-Fi networks:"
        nmcli connection show | grep wifi | awk '{print "  - " $1}'
    fi
fi

# Check netplan
if ls /etc/netplan/*wifi*.yaml 2>/dev/null | grep -q .; then
    OLD_WIFI_FOUND=true
    echo "Found netplan Wi-Fi configurations"
fi

if [ "$OLD_WIFI_FOUND" = true ]; then
    echo ""
    echo -e "${YELLOW}WARNING: Old Wi-Fi credentials found on this system.${NC}"
    echo "These may be from a previous location (home network, etc.)"
    echo ""
    read -p "Do you want to REMOVE old Wi-Fi credentials? (Y/n): " CLEAR_WIFI

    if [ "$CLEAR_WIFI" != "n" ] && [ "$CLEAR_WIFI" != "N" ]; then
        echo ""
        echo "Clearing old Wi-Fi credentials..."

        # Clear NetworkManager
        if command -v nmcli &> /dev/null; then
            nmcli connection show | grep wifi | awk '{print $1}' | while read conn; do
                nmcli connection delete "$conn" 2>/dev/null || true
            done
        fi

        # Clear netplan wifi configs
        rm -f /etc/netplan/*wifi*.yaml 2>/dev/null || true

        echo -e "${GREEN}Old Wi-Fi credentials removed!${NC}"
    fi
else
    echo "No saved Wi-Fi credentials found."
fi

echo ""

# ============================================
# STEP 2: Network Configuration
# ============================================

echo -e "${YELLOW}Step 2: Network Configuration${NC}"
echo ""

# Show current network status
echo "Current network status:"
IP=$(hostname -I 2>/dev/null | awk '{print $1}')
if [ -n "$IP" ]; then
    echo -e "  ${GREEN}Connected${NC} - IP: $IP"
    CONNECTED=true
else
    echo -e "  ${RED}Not connected${NC}"
    CONNECTED=false
fi
echo ""

if [ "$CONNECTED" = false ]; then
    echo "How do you want to connect?"
    echo "  1) Ethernet (plug in cable)"
    echo "  2) Wi-Fi"
    echo "  3) Skip for now"
    echo ""
    read -p "Choice [1-3]: " NET_CHOICE

    case $NET_CHOICE in
        2)
            echo ""
            echo "Scanning for Wi-Fi networks..."
            nmcli device wifi list 2>/dev/null || echo "(scanning...)"
            echo ""
            read -p "Enter Wi-Fi network name (SSID): " SSID
            read -sp "Enter Wi-Fi password: " PASSWORD
            echo ""
            echo ""
            echo "Connecting to $SSID..."
            if nmcli device wifi connect "$SSID" password "$PASSWORD" 2>/dev/null; then
                echo -e "${GREEN}Connected!${NC}"
                IP=$(hostname -I | awk '{print $1}')
                echo "IP Address: $IP"
            else
                echo -e "${RED}Connection failed. You may need to configure manually.${NC}"
            fi
            ;;
        1)
            echo ""
            echo "Please plug in the ethernet cable and wait..."
            sleep 5
            IP=$(hostname -I | awk '{print $1}')
            if [ -n "$IP" ]; then
                echo -e "${GREEN}Connected!${NC} IP: $IP"
            else
                echo "Still waiting for connection. Check the cable."
            fi
            ;;
        *)
            echo "Skipping network configuration."
            ;;
    esac
fi

echo ""

# ============================================
# STEP 3: Set Static IP (optional)
# ============================================

echo -e "${YELLOW}Step 3: Static IP Configuration (optional)${NC}"
echo ""
echo "Current IP: $(hostname -I | awk '{print $1}')"
echo ""
echo "For a server, a static IP is recommended so the address doesn't change."
read -p "Do you want to set a static IP? (y/N): " SET_STATIC

if [ "$SET_STATIC" = "y" ] || [ "$SET_STATIC" = "Y" ]; then
    read -p "Enter static IP (e.g., 192.168.1.50): " STATIC_IP
    read -p "Enter gateway (e.g., 192.168.1.1): " GATEWAY
    read -p "Enter DNS server (e.g., 192.168.1.1 or 8.8.8.8): " DNS

    # Find primary interface
    IFACE=$(ip route | grep default | awk '{print $5}' | head -1)

    if [ -n "$IFACE" ]; then
        cat > /etc/netplan/99-static.yaml << EOF
network:
  version: 2
  ethernets:
    $IFACE:
      dhcp4: no
      addresses:
        - $STATIC_IP/24
      routes:
        - to: default
          via: $GATEWAY
      nameservers:
        addresses:
          - $DNS
EOF
        netplan apply
        echo -e "${GREEN}Static IP configured!${NC}"
        echo "New IP: $STATIC_IP"
    else
        echo -e "${RED}Could not determine network interface.${NC}"
    fi
fi

echo ""

# ============================================
# STEP 4: Summary
# ============================================

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}   SETUP COMPLETE${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

IP=$(hostname -I | awk '{print $1}')
echo "Server Information:"
echo "  Hostname: $(hostname)"
echo "  IP Address: $IP"
echo ""
echo "Service URLs:"
echo "  Print API:   http://$IP:5001/v1/"
echo "  Cockpit:     https://$IP:9090"
echo "  Portainer:   http://$IP:9000"
echo "  CUPS:        http://$IP:631"
echo ""
echo "Next steps:"
echo "  1. Add this IP to your Unifi as a static reservation"
echo "  2. Test the Print API from BruFLOW"
echo "  3. Configure your label printer in CUPS"
echo ""
echo -e "${GREEN}Setup complete!${NC}"
echo ""

#!/bin/bash
# ============================================
#   PRINT SERVER HEALTH CHECK
# ============================================
# Verifies all services are running correctly
#
# Usage: ./health-check.sh

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo ""
echo "============================================"
echo "   PRINT SERVER HEALTH CHECK"
echo "============================================"
echo ""

ERRORS=0

check_service() {
    local name=$1
    local check=$2
    printf "%-20s" "$name:"
    if eval "$check" > /dev/null 2>&1; then
        echo -e "${GREEN}OK${NC}"
    else
        echo -e "${RED}FAILED${NC}"
        ((ERRORS++))
    fi
}

check_port() {
    local name=$1
    local port=$2
    printf "%-20s" "$name (port $port):"
    if ss -tlnp | grep -q ":$port "; then
        echo -e "${GREEN}LISTENING${NC}"
    else
        echo -e "${RED}NOT LISTENING${NC}"
        ((ERRORS++))
    fi
}

echo "SYSTEM:"
check_service "Docker" "docker info"
check_service "Docker Compose" "docker compose version"
echo ""

echo "SERVICES:"
check_port "Print API" "5001"
check_port "Cockpit" "9090"
check_port "Portainer" "9000"
check_port "CUPS" "631"
check_port "SSH" "22"
echo ""

echo "CONTAINERS:"
if command -v docker &> /dev/null; then
    docker ps --format "  {{.Names}}: {{.Status}}" 2>/dev/null || echo "  (none running)"
else
    echo "  Docker not available"
fi
echo ""

echo "DISK USAGE:"
df -h / | tail -1 | awk '{print "  Root: " $5 " used (" $4 " free)"}'
echo ""

echo "MEMORY:"
free -h | grep Mem | awk '{print "  " $3 " used / " $2 " total"}'
echo ""

echo "NETWORK:"
IP=$(hostname -I | awk '{print $1}')
echo "  Primary IP: $IP"
echo ""

# Test print API if running
if ss -tlnp | grep -q ":5001 "; then
    echo "PRINT API TEST:"
    printf "  Health endpoint: "
    if curl -sf "http://localhost:5001/v1/health" > /dev/null 2>&1; then
        echo -e "${GREEN}OK${NC}"
    else
        echo -e "${YELLOW}NOT RESPONDING${NC}"
    fi
fi

echo ""
echo "============================================"
if [ $ERRORS -eq 0 ]; then
    echo -e "   ${GREEN}ALL CHECKS PASSED${NC}"
else
    echo -e "   ${RED}$ERRORS CHECK(S) FAILED${NC}"
fi
echo "============================================"
echo ""

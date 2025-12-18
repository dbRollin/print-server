#!/bin/bash
# Smoke test for print server
# Run after server is started to verify everything works
#
# Usage: ./scripts/smoke_test.sh [server_url]

set -e

SERVER="${1:-http://localhost:5001}"
PASSED=0
FAILED=0

echo "========================================"
echo "  Print Server Smoke Test"
echo "  Server: $SERVER"
echo "========================================"
echo ""

# Helper functions
pass() {
    echo "  ✓ $1"
    ((PASSED++))
}

fail() {
    echo "  ✗ $1"
    ((FAILED++))
}

test_endpoint() {
    local name="$1"
    local method="$2"
    local endpoint="$3"
    local expected_status="$4"

    status=$(curl -s -o /dev/null -w "%{http_code}" -X "$method" "$SERVER$endpoint")

    if [ "$status" = "$expected_status" ]; then
        pass "$name (HTTP $status)"
    else
        fail "$name (expected $expected_status, got $status)"
    fi
}

# Test 1: Health check
echo "[1] Health Check"
test_endpoint "GET /v1/health" "GET" "/v1/health" "200"

# Test 2: Status endpoint
echo ""
echo "[2] Status Endpoint"
test_endpoint "GET /v1/status" "GET" "/v1/status" "200"

# Test 3: Queue endpoint
echo ""
echo "[3] Queue Endpoint"
test_endpoint "GET /v1/queue" "GET" "/v1/queue" "200"

# Test 4: Create test image and try to print
echo ""
echo "[4] Label Print Test"

# Generate test image
TEMP_IMAGE=$(mktemp /tmp/test_label_XXXXXX.png)
python3 -c "
from PIL import Image, ImageDraw
img = Image.new('1', (720, 100), 1)
draw = ImageDraw.Draw(img)
draw.text((300, 40), 'TEST', fill=0)
img.save('$TEMP_IMAGE', 'PNG')
" 2>/dev/null || {
    echo "  (skipping - PIL not available)"
    TEMP_IMAGE=""
}

if [ -n "$TEMP_IMAGE" ] && [ -f "$TEMP_IMAGE" ]; then
    status=$(curl -s -o /dev/null -w "%{http_code}" \
        -X POST "$SERVER/v1/print/label" \
        -F "file=@$TEMP_IMAGE")

    if [ "$status" = "200" ]; then
        pass "POST /v1/print/label (HTTP $status)"
    else
        fail "POST /v1/print/label (expected 200, got $status)"
    fi

    rm -f "$TEMP_IMAGE"
fi

# Test 5: Invalid image should fail
echo ""
echo "[5] Validation Test (should reject)"

TEMP_BAD=$(mktemp /tmp/bad_label_XXXXXX.png)
python3 -c "
from PIL import Image
img = Image.new('RGB', (800, 100), (128, 128, 128))  # Wrong size, not monochrome
img.save('$TEMP_BAD', 'PNG')
" 2>/dev/null || TEMP_BAD=""

if [ -n "$TEMP_BAD" ] && [ -f "$TEMP_BAD" ]; then
    status=$(curl -s -o /dev/null -w "%{http_code}" \
        -X POST "$SERVER/v1/print/label" \
        -F "file=@$TEMP_BAD")

    if [ "$status" = "400" ]; then
        pass "Rejected invalid image (HTTP $status)"
    else
        fail "Should reject invalid image (expected 400, got $status)"
    fi

    rm -f "$TEMP_BAD"
fi

# Test 6: Unknown printer
echo ""
echo "[6] Unknown Printer Test"
test_endpoint "GET /v1/queue?printer_id=nonexistent" "GET" "/v1/queue?printer_id=nonexistent" "404"

# Summary
echo ""
echo "========================================"
echo "  Results: $PASSED passed, $FAILED failed"
echo "========================================"

if [ $FAILED -gt 0 ]; then
    exit 1
fi

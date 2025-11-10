#!/bin/bash

# Test Rate Limit Headers Script
# Verifies that X-RateLimit headers are present in all services

echo "🔍 Testing Rate Limit Headers Across All Services"
echo "=================================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

test_service() {
    local name=$1
    local url=$2
    
    echo -n "Testing $name... "
    
    # Get headers
    headers=$(curl -s -i "$url" 2>/dev/null | head -20)
    
    # Check for X-RateLimit headers
    if echo "$headers" | grep -qi "x-ratelimit-limit"; then
        limit=$(echo "$headers" | grep -i "x-ratelimit-limit" | cut -d: -f2 | tr -d ' \r')
        remaining=$(echo "$headers" | grep -i "x-ratelimit-remaining" | cut -d: -f2 | tr -d ' \r')
        echo -e "${GREEN}✓ OK${NC}"
        echo "  └─ Limit: $limit, Remaining: $remaining"
    else
        echo -e "${RED}✗ FAILED${NC} - No rate limit headers found"
        echo "  Headers received:"
        echo "$headers" | head -10 | sed 's/^/    /'
    fi
    echo ""
}

echo "📍 Testing Health Endpoints"
echo "----------------------------"
test_service "API Gateway" "http://localhost:8000/api/health"
test_service "Auth Service" "http://localhost:8200/auth/health"
test_service "Partners Service" "http://localhost:8300/partners/health"
test_service "Inventory Service" "http://localhost:8400/inventory/health"
test_service "RAG Service" "http://localhost:8500/rag/health"

echo ""
echo "✨ Testing Complete!"
echo ""
echo "📝 Expected Headers:"
echo "  - X-RateLimit-Limit: 200"
echo "  - X-RateLimit-Remaining: 199 (or less)"
echo "  - X-RateLimit-Reset: <timestamp>"
echo ""

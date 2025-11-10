#!/bin/bash

# Sentry Testing Script
# Tests all debug endpoints and health checks

echo "🧪 Testing Sentry Integration Across All Services"
echo "=================================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to test endpoint
test_endpoint() {
    local name=$1
    local url=$2
    local expected_code=$3
    
    echo -n "Testing $name... "
    response=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null)
    
    if [ "$response" == "$expected_code" ]; then
        echo -e "${GREEN}✓ OK${NC} (HTTP $response)"
        return 0
    else
        echo -e "${RED}✗ FAILED${NC} (Expected $expected_code, got $response)"
        return 1
    fi
}

echo "📍 Step 1: Testing Health Endpoints (should return 200)"
echo "-------------------------------------------------------"
test_endpoint "API Gateway Health" "http://localhost:8000/api/health" "200"
test_endpoint "Auth Health" "http://localhost:8200/auth/health" "200"
test_endpoint "Partners Health" "http://localhost:8300/partners/health" "200"
test_endpoint "Inventory Health" "http://localhost:8400/inventory/health" "200"
test_endpoint "RAG Health" "http://localhost:8500/rag/health" "200"
echo ""

echo "🔥 Step 2: Triggering Sentry Debug Endpoints (should return 500)"
echo "----------------------------------------------------------------"
test_endpoint "API Gateway Debug" "http://localhost:8000/sentry-debug" "500"
test_endpoint "Auth Debug" "http://localhost:8200/auth/sentry-debug" "500"
test_endpoint "Partners Debug" "http://localhost:8300/partners/sentry-debug" "500"
test_endpoint "Inventory Debug" "http://localhost:8400/inventory/sentry-debug" "500"
test_endpoint "RAG Debug" "http://localhost:8500/rag/sentry-debug" "500"
echo ""

echo "✅ Testing Complete!"
echo ""
echo "📊 Next Steps:"
echo "1. Check Sentry Dashboard: https://sentry.io/organizations/waifu-solutions/issues/"
echo "2. You should see 5 new errors (one from each service)"
echo "3. Each error should have:"
echo "   - Service name in release tag"
echo "   - Division by zero stack trace"
echo "   - Request context data"
echo "   - Log breadcrumbs"
echo ""
echo "🎯 Success Criteria:"
echo "   ✓ All health checks return 200"
echo "   ✓ All debug endpoints return 500"
echo "   ✓ Errors appear in Sentry within 30 seconds"
echo ""

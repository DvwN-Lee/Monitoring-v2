#!/bin/bash
# Week 1 Service Integration Tests
# Tests API endpoints and database operations

set -e

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Move to project root (parent of scripts directory)
PROJECT_ROOT="$SCRIPT_DIR/.."
cd "$PROJECT_ROOT"

echo "📁 Working directory: $(pwd)"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0

# Helper functions
print_test() {
    echo ""
    echo "${BLUE}========================================${NC}"
    echo "${BLUE}TEST: $1${NC}"
    echo "${BLUE}========================================${NC}"
}

pass() {
    echo "${GREEN}PASS: $1${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
}

fail() {
    echo "${RED}FAIL: $1${NC}"
    TESTS_FAILED=$((TESTS_FAILED + 1))
}

warn() {
    echo "${YELLOW}WARN: $1${NC}"
}

echo "${GREEN}🧪 Week 1 Service Integration Tests${NC}"
echo "=========================================="

# Get LoadBalancer IP or use port-forward
NAMESPACE="titanium-prod"
SERVICE_NAME="prod-load-balancer-service"

echo "Finding service endpoint..."

# Try to get LoadBalancer external IP
LB_IP=$(kubectl get svc "$SERVICE_NAME" -n "$NAMESPACE" -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")

if [ -z "$LB_IP" ]; then
    # Try hostname (for cloud providers that use DNS)
    LB_IP=$(kubectl get svc "$SERVICE_NAME" -n "$NAMESPACE" -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null || echo "")
fi

if [ -z "$LB_IP" ]; then
    warn "LoadBalancer external IP not found, using port-forward"

    # Start port-forward in background
    kubectl port-forward -n "$NAMESPACE" svc/"$SERVICE_NAME" 7100:7100 &> /dev/null &
    PORT_FORWARD_PID=$!

    # Wait for port-forward to be ready
    sleep 3

    BASE_URL="http://localhost:7100"

    # Trap to kill port-forward on exit
    trap "kill $PORT_FORWARD_PID 2>/dev/null || true" EXIT
else
    BASE_URL="http://$LB_IP:7100"
fi

echo "📍 Using endpoint: $BASE_URL"

# Test 1: Health Checks
print_test "Service Health Checks"

SERVICES=("user-service" "blog-service" "auth-service")

for svc in "${SERVICES[@]}"; do
    HEALTH_URL="$BASE_URL/$svc/health"

    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$HEALTH_URL" 2>/dev/null || echo "000")

    if [ "$HTTP_CODE" == "200" ]; then
        pass "$svc health check returned 200"
    else
        fail "$svc health check returned $HTTP_CODE (expected 200)"
    fi
done

# Test 2: User Registration
print_test "User Registration (PostgreSQL Write)"

REGISTER_URL="$BASE_URL/api/register"
TEST_USER="testuser_$(date +%s)"
TEST_EMAIL="$TEST_USER@test.com"
TEST_PASSWORD="testpass123"

REGISTER_RESPONSE=$(curl -s -X POST "$REGISTER_URL" \
    -H "Content-Type: application/json" \
    -d "{\"username\":\"$TEST_USER\",\"email\":\"$TEST_EMAIL\",\"password\":\"$TEST_PASSWORD\"}" \
    2>/dev/null || echo "{}")

if echo "$REGISTER_RESPONSE" | grep -q "success\|created\|registered"; then
    pass "User registration successful"
    USER_CREATED=true
else
    fail "User registration failed: $REGISTER_RESPONSE"
    USER_CREATED=false
fi

# Test 3: User Login
if [ "$USER_CREATED" = true ]; then
    print_test "User Login (PostgreSQL Read)"

    LOGIN_URL="$BASE_URL/api/login"

    LOGIN_RESPONSE=$(curl -s -X POST "$LOGIN_URL" \
        -H "Content-Type: application/json" \
        -d "{\"username\":\"$TEST_USER\",\"password\":\"$TEST_PASSWORD\"}" \
        2>/dev/null || echo "{}")

    TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"token":"[^"]*"' | cut -d'"' -f4)

    if [ -n "$TOKEN" ]; then
        pass "User login successful, token received"
    else
        fail "User login failed: $LOGIN_RESPONSE"
    fi
else
    warn "Skipping login test (user not created)"
fi

# Test 4: Blog Post Creation
if [ -n "$TOKEN" ]; then
    print_test "Blog Post Creation (PostgreSQL Write)"

    CREATE_POST_URL="$BASE_URL/api/posts"

    POST_RESPONSE=$(curl -s -X POST "$CREATE_POST_URL" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $TOKEN" \
        -d "{\"title\":\"Test Post\",\"content\":\"This is a test post created by integration tests.\"}" \
        2>/dev/null || echo "{}")

    POST_ID=$(echo "$POST_RESPONSE" | grep -o '"id":[0-9]*' | cut -d':' -f2)

    if [ -n "$POST_ID" ]; then
        pass "Blog post created with ID: $POST_ID"
    else
        fail "Blog post creation failed: $POST_RESPONSE"
    fi
else
    warn "Skipping blog post test (no auth token)"
fi

# Test 5: Blog Post Retrieval
if [ -n "$POST_ID" ]; then
    print_test "Blog Post Retrieval (PostgreSQL Read)"

    GET_POST_URL="$BASE_URL/api/posts/$POST_ID"

    GET_RESPONSE=$(curl -s "$GET_POST_URL" 2>/dev/null || echo "{}")

    if echo "$GET_RESPONSE" | grep -q "Test Post"; then
        pass "Blog post retrieved successfully"
    else
        fail "Blog post retrieval failed: $GET_RESPONSE"
    fi

    # Test 6: Blog Post Update
    print_test "Blog Post Update (PostgreSQL Update)"

    UPDATE_RESPONSE=$(curl -s -X PATCH "$GET_POST_URL" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $TOKEN" \
        -d "{\"content\":\"Updated content\"}" \
        2>/dev/null || echo "{}")

    if echo "$UPDATE_RESPONSE" | grep -q "Updated content"; then
        pass "Blog post updated successfully"
    else
        fail "Blog post update failed: $UPDATE_RESPONSE"
    fi

    # Test 7: Blog Post Deletion
    print_test "Blog Post Deletion (PostgreSQL Delete)"

    DELETE_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE "$GET_POST_URL" \
        -H "Authorization: Bearer $TOKEN" 2>/dev/null || echo "000")

    if [ "$DELETE_CODE" == "204" ] || [ "$DELETE_CODE" == "200" ]; then
        pass "Blog post deleted successfully"
    else
        fail "Blog post deletion failed (HTTP $DELETE_CODE)"
    fi
else
    warn "Skipping blog post tests (no post created)"
fi

# Test 8: Database Persistence
print_test "PostgreSQL Data Persistence"

# Check if data exists in PostgreSQL
POD_CHECK=$(kubectl exec postgresql-0 -n "$NAMESPACE" -- \
    psql -U postgres -d titanium -t -c "SELECT COUNT(*) FROM users" 2>/dev/null | tr -d ' ')

if [ "$POD_CHECK" -gt 0 ]; then
    pass "Data persisted in PostgreSQL (users count: $POD_CHECK)"
else
    warn "No users found in PostgreSQL"
fi

# Summary
echo ""
echo "${BLUE}========================================${NC}"
echo "${BLUE}TEST SUMMARY${NC}"
echo "${BLUE}========================================${NC}"
echo "${GREEN}Passed: $TESTS_PASSED${NC}"
echo "${RED}Failed: $TESTS_FAILED${NC}"

if [ $TESTS_FAILED -eq 0 ]; then
    echo ""
    echo "${GREEN}All service tests passed!${NC}"
    echo ""
    echo "PostgreSQL integration working correctly"
    echo "CRUD operations functional"
    echo "Authentication working"
    echo ""
    exit 0
else
    echo ""
    echo "${RED}Some service tests failed.${NC}"
    exit 1
fi

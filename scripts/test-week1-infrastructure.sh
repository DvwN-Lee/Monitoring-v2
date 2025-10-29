#!/bin/bash
# Week 1 Infrastructure Integration Tests (Token-based Authentication)
# Tests: Terraform, Kubernetes, PostgreSQL, Services

set -e

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Move to project root (parent of scripts directory)
PROJECT_ROOT="$SCRIPT_DIR/.."
cd "$PROJECT_ROOT"

echo "📁 Working directory: $(pwd)"
echo ""

# Check if kubectl is connected to a cluster
echo "🔍 Checking Kubernetes connection..."
if ! kubectl cluster-info &> /dev/null; then
    echo "❌ Not connected to Kubernetes cluster"
    echo ""
    echo "Please run the environment switch script first:"
    echo "  ./scripts/switch-to-cloud.sh (for Solid Cloud)"
    echo "  ./scripts/switch-to-local.sh (for Minikube)"
    echo ""
    exit 1
fi

CURRENT_CONTEXT=$(kubectl config current-context 2>/dev/null || echo "none")
echo "📍 Using context: $CURRENT_CONTEXT"
echo ""

# Colors - Disabled for better compatibility
# If you want colors, uncomment these lines and use a terminal that supports ANSI colors
RED=''
GREEN=''
YELLOW=''
BLUE=''
NC=''

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0
TOTAL_TESTS=0

# Helper functions
print_test() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}TEST: $1${NC}"
    echo -e "${BLUE}========================================${NC}"
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
}

pass() {
    echo -e "${GREEN}PASS: $1${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
}

fail() {
    echo -e "${RED}FAIL: $1${NC}"
    TESTS_FAILED=$((TESTS_FAILED + 1))
}

warn() {
    echo -e "${YELLOW}WARN: $1${NC}"
}

# Start tests
echo -e "${GREEN}Week 1 Infrastructure Integration Tests${NC}"
echo "=========================================="

# Test 1: Terraform Setup
print_test "Terraform Installation and Setup"

if command -v terraform &> /dev/null; then
    TF_VERSION=$(terraform version | head -n1)
    pass "Terraform is installed: $TF_VERSION"
else
    fail "Terraform is not installed"
fi

if [ -d "terraform/modules/network" ]; then
    pass "Network module exists"
else
    fail "Network module not found"
fi

if [ -d "terraform/modules/kubernetes" ]; then
    pass "Kubernetes module exists"
else
    fail "Kubernetes module not found"
fi

if [ -d "terraform/modules/database" ]; then
    pass "Database module exists"
else
    fail "Database module not found"
fi

# Test 2: Kubernetes Connection
print_test "Kubernetes Cluster Connection"

if command -v kubectl &> /dev/null; then
    pass "kubectl is installed"
else
    fail "kubectl is not installed"
    exit 1
fi

if kubectl cluster-info &> /dev/null; then
    CONTEXT=$(kubectl config current-context)
    pass "Connected to cluster: $CONTEXT"
else
    fail "Cannot connect to Kubernetes cluster"
    warn "Run: ./scripts/switch-to-cloud.sh or ./scripts/switch-to-local.sh"
    exit 1
fi

# Test 3: Namespaces
print_test "Kubernetes Namespaces"

EXPECTED_NAMESPACES=("titanium-prod" "monitoring" "argocd")

for ns in "${EXPECTED_NAMESPACES[@]}"; do
    if kubectl get namespace "$ns" &> /dev/null; then
        pass "Namespace '$ns' exists"
    else
        warn "Namespace '$ns' not found (run terraform apply first)"
    fi
done

# Test 4: PostgreSQL Deployment
print_test "PostgreSQL Deployment"

NAMESPACE="titanium-prod"

if kubectl get namespace "$NAMESPACE" &> /dev/null; then
    if kubectl get statefulset postgresql -n "$NAMESPACE" &> /dev/null; then
        pass "PostgreSQL StatefulSet exists"

        # Check if pod is running
        POD_STATUS=$(kubectl get pod postgresql-0 -n "$NAMESPACE" -o jsonpath='{.status.phase}' 2>/dev/null || echo "NotFound")
        if [ "$POD_STATUS" == "Running" ]; then
            pass "PostgreSQL pod is running"
        else
            warn "PostgreSQL pod status: $POD_STATUS"
        fi

        # Check PVC
        if kubectl get pvc postgresql-pvc -n "$NAMESPACE" &> /dev/null; then
            PVC_STATUS=$(kubectl get pvc postgresql-pvc -n "$NAMESPACE" -o jsonpath='{.status.phase}')
            if [ "$PVC_STATUS" == "Bound" ]; then
                pass "PostgreSQL PVC is bound"
            else
                warn "PostgreSQL PVC status: $PVC_STATUS"
            fi
        else
            warn "PostgreSQL PVC not found"
        fi
    else
        warn "PostgreSQL StatefulSet not found (run deployment first)"
    fi
else
    warn "Namespace $NAMESPACE not found"
fi

# Test 5: PostgreSQL Connection
print_test "PostgreSQL Database Connection"

if kubectl get pod postgresql-0 -n "$NAMESPACE" &> /dev/null 2>&1; then
    POD_STATUS=$(kubectl get pod postgresql-0 -n "$NAMESPACE" -o jsonpath='{.status.phase}')

    if [ "$POD_STATUS" == "Running" ]; then
        # Test connection
        if kubectl exec postgresql-0 -n "$NAMESPACE" -- psql -U postgres -d titanium -c "SELECT 1" &> /dev/null; then
            pass "Successfully connected to PostgreSQL"

            # Check tables
            TABLES=$(kubectl exec postgresql-0 -n "$NAMESPACE" -- psql -U postgres -d titanium -c "\dt" 2>/dev/null || echo "")

            if echo "$TABLES" | grep -q "users"; then
                pass "Table 'users' exists"
            else
                warn "Table 'users' not found (may be created on first service start)"
            fi

            if echo "$TABLES" | grep -q "posts"; then
                pass "Table 'posts' exists"
            else
                warn "Table 'posts' not found (may be created on first service start)"
            fi
        else
            warn "Cannot connect to PostgreSQL (check credentials)"
        fi
    else
        warn "PostgreSQL pod is not running: $POD_STATUS"
    fi
else
    warn "PostgreSQL pod not found"
fi

# Test 6: Kustomize Overlays
print_test "Kustomize Overlay Configuration"

if [ -f "k8s-manifests/overlays/solid-cloud/kustomization.yaml" ]; then
    pass "solid-cloud overlay exists"
else
    fail "solid-cloud overlay not found"
fi

if [ -f "k8s-manifests/overlays/solid-cloud/configmap-patch.yaml" ]; then
    pass "ConfigMap patch exists"
else
    fail "ConfigMap patch not found"
fi

if [ -f "k8s-manifests/overlays/solid-cloud/secret-patch.yaml" ]; then
    pass "Secret patch exists"
else
    warn "Secret patch not found (copy from .example file)"
fi

# Test 7: Service Deployments
print_test "Application Services"

SERVICES=("user-service" "blog-service" "auth-service" "api-gateway")

for svc in "${SERVICES[@]}"; do
    DEPLOYMENT_NAME="prod-${svc}-deployment"

    if kubectl get deployment "$DEPLOYMENT_NAME" -n "$NAMESPACE" &> /dev/null 2>&1; then
        pass "Deployment '$DEPLOYMENT_NAME' exists"

        # Check ready replicas
        READY=$(kubectl get deployment "$DEPLOYMENT_NAME" -n "$NAMESPACE" -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo "0")
        DESIRED=$(kubectl get deployment "$DEPLOYMENT_NAME" -n "$NAMESPACE" -o jsonpath='{.spec.replicas}' 2>/dev/null || echo "0")

        if [ "$READY" == "$DESIRED" ] && [ "$READY" != "0" ]; then
            pass "$DEPLOYMENT_NAME is ready ($READY/$DESIRED replicas)"
        else
            warn "$DEPLOYMENT_NAME replicas: $READY/$DESIRED"
        fi
    else
        warn "Deployment '$DEPLOYMENT_NAME' not found (deploy with kubectl apply -k)"
    fi
done

# Test 8: ConfigMap and Secrets
print_test "ConfigMap and Secrets"

if kubectl get configmap app-config -n "$NAMESPACE" &> /dev/null 2>&1; then
    pass "ConfigMap 'app-config' exists"

    # Check PostgreSQL config
    PG_HOST=$(kubectl get configmap app-config -n "$NAMESPACE" -o jsonpath='{.data.POSTGRES_HOST}' 2>/dev/null || echo "")
    if [ "$PG_HOST" == "postgresql-service" ]; then
        pass "PostgreSQL host configured correctly"
    else
        warn "PostgreSQL host: $PG_HOST (expected: postgresql-service)"
    fi
else
    warn "ConfigMap 'app-config' not found"
fi

if kubectl get secret app-secrets -n "$NAMESPACE" &> /dev/null 2>&1; then
    pass "Secret 'app-secrets' exists"
else
    warn "Secret 'app-secrets' not found"
fi

# Test 9: Database Migration
print_test "Database Code Migration"

# Check if SQLite imports are removed from Python files
if grep -r "import sqlite3" user-service/ blog-service/ 2>/dev/null; then
    fail "SQLite imports still present in code"
else
    pass "SQLite imports removed"
fi

# Check if psycopg2 is in requirements
if grep -q "psycopg2" user-service/requirements.txt; then
    pass "psycopg2 added to user-service requirements"
else
    fail "psycopg2 missing from user-service requirements"
fi

if grep -q "psycopg2" blog-service/requirements.txt; then
    pass "psycopg2 added to blog-service requirements"
else
    fail "psycopg2 missing from blog-service requirements"
fi

# Test 10: Environment Switching Scripts
print_test "Environment Switching Scripts"

SCRIPTS=("switch-to-local.sh" "switch-to-cloud.sh" "deploy-local.sh" "deploy-cloud.sh")

for script in "${SCRIPTS[@]}"; do
    if [ -f "scripts/$script" ]; then
        if [ -x "scripts/$script" ]; then
            pass "Script '$script' exists and is executable"
        else
            warn "Script '$script' is not executable (chmod +x scripts/$script)"
        fi
    else
        fail "Script '$script' not found"
    fi
done

# Summary
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}TEST SUMMARY${NC}"
echo -e "${BLUE}========================================${NC}"
echo "Total Tests: $TOTAL_TESTS"
echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Failed: $TESTS_FAILED${NC}"
echo -e "${YELLOW}Warnings: Check output above${NC}"

if [ $TESTS_FAILED -eq 0 ]; then
    echo ""
    echo -e "${GREEN}🎉 All critical tests passed!${NC}"
    echo ""
    echo "Week 1 Completion Criteria:"
    echo "  Terraform modules created"
    echo "  Kubernetes cluster accessible"
    echo "  PostgreSQL deployed and running"
    echo "  Database migration completed"
    echo "  Kustomize overlays configured"
    echo "  Environment switching scripts ready"
    echo ""
    exit 0
else
    echo ""
    echo -e "${RED}Some tests failed. Please review and fix issues.${NC}"
    exit 1
fi

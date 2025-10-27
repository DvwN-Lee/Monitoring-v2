#!/bin/bash
# Switch to Solid Cloud Production Environment

set -e

echo "☁️  Switching to Solid Cloud Production Environment..."

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Move to project root (parent of scripts directory)
PROJECT_ROOT="$SCRIPT_DIR/.."
cd "$PROJECT_ROOT"

echo "📁 Working directory: $(pwd)"
echo ""

# Load tool installation functions
source "$SCRIPT_DIR/install-tools.sh"

# Check and install required tools
echo "🔍 필요한 도구 확인 중..."
check_and_install_tools kubectl terraform || exit 1

echo ""

# Check if kubeconfig for Solid Cloud exists
KUBECONFIG_PATH="${KUBECONFIG:-$HOME/.kube/config}"

if [ ! -f "$KUBECONFIG_PATH" ]; then
    echo "Kubeconfig file not found at $KUBECONFIG_PATH"
    echo "   Please download kubeconfig from Solid Cloud and set KUBECONFIG environment variable."
    exit 1
fi

echo "Kubeconfig found at $KUBECONFIG_PATH"

# List available contexts
echo ""
echo "Available Kubernetes contexts:"
kubectl config get-contexts

echo ""
read -p "Enter the context name for Solid Cloud (or press Enter to use current): " CONTEXT_NAME

if [ -n "$CONTEXT_NAME" ]; then
    echo "🔧 Switching to context: $CONTEXT_NAME"
    kubectl config use-context "$CONTEXT_NAME"
fi

# Verify context
CURRENT_CONTEXT=$(kubectl config current-context)
echo "📍 Current context: $CURRENT_CONTEXT"

# Verify connection
echo "Verifying connection to Solid Cloud..."
if kubectl cluster-info &> /dev/null; then
    echo "Successfully connected to Solid Cloud!"
else
    echo "Failed to connect to Solid Cloud. Please check your kubeconfig."
    exit 1
fi

# Check if titanium-prod namespace exists
if kubectl get namespace titanium-prod &> /dev/null; then
    echo "titanium-prod namespace exists"
else
    echo "titanium-prod namespace not found"
    echo "   Run Terraform to create infrastructure first:"
    echo "   cd terraform/environments/solid-cloud && terraform apply"
fi

echo ""
echo "Successfully switched to Solid Cloud Environment!"
echo ""
echo "Next steps:"
echo "  1. Apply infrastructure with Terraform:"
echo "     cd terraform/environments/solid-cloud"
echo "     terraform init"
echo "     terraform apply"
echo ""
echo "  2. Deploy applications:"
echo "     kubectl apply -k k8s-manifests/overlays/solid-cloud"
echo ""
echo "  3. Check deployment status:"
echo "     kubectl get pods -n titanium-prod"
echo "     kubectl get svc -n titanium-prod"
echo ""

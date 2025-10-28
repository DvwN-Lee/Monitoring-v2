#!/bin/bash
# Switch to Solid Cloud Production Environment (Token-based Authentication)

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

# Load Kubernetes credentials from .env.k8s file
ENV_FILE="$PROJECT_ROOT/.env.k8s"

if [ ! -f "$ENV_FILE" ]; then
    echo "❌ .env.k8s file not found!"
    echo ""
    echo "Please create .env.k8s file with your Kubernetes credentials:"
    echo "  1. Copy the example file:"
    echo "     cp .env.k8s.example .env.k8s"
    echo ""
    echo "  2. Edit .env.k8s and fill in your values:"
    echo "     - K8S_API_SERVER: Your Kubernetes API server URL"
    echo "     - K8S_TOKEN: Your service account token"
    echo "     - K8S_CA_CERT: Your CA certificate (base64 encoded)"
    echo ""
    echo "  3. To get token and CA cert from your cluster:"
    echo "     # Create service account"
    echo "     kubectl create serviceaccount monitoring-sa -n default"
    echo "     kubectl create clusterrolebinding monitoring-sa-admin \\"
    echo "       --clusterrole=cluster-admin \\"
    echo "       --serviceaccount=default:monitoring-sa"
    echo ""
    echo "     # Get token (Kubernetes 1.24+)"
    echo "     kubectl create token monitoring-sa --duration=87600h"
    echo ""
    echo "     # Get token (Kubernetes <1.24)"
    echo "     TOKEN_SECRET=\$(kubectl get serviceaccount monitoring-sa -o jsonpath='{.secrets[0].name}')"
    echo "     kubectl get secret \$TOKEN_SECRET -o jsonpath='{.data.token}' | base64 -d"
    echo ""
    echo "     # Get CA certificate"
    echo "     kubectl get secret \$TOKEN_SECRET -o jsonpath='{.data.ca\\.crt}'"
    echo ""
    exit 1
fi

# Load environment variables
source "$ENV_FILE"

# Validate required variables
if [ -z "$K8S_API_SERVER" ] || [ -z "$K8S_TOKEN" ]; then
    echo "❌ Required environment variables not set in .env.k8s"
    echo "   Please ensure K8S_API_SERVER and K8S_TOKEN are set."
    exit 1
fi

# Set default values
K8S_CLUSTER_NAME="${K8S_CLUSTER_NAME:-solid-cloud}"
K8S_SKIP_TLS_VERIFY="${K8S_SKIP_TLS_VERIFY:-false}"
CONTEXT_NAME="${K8S_CLUSTER_NAME}-context"
USER_NAME="${K8S_CLUSTER_NAME}-user"

echo "🔧 Configuring kubectl for token-based authentication..."

# Create cluster configuration
if [ "$K8S_SKIP_TLS_VERIFY" == "true" ]; then
    echo "⚠️  Warning: Skipping TLS verification (not recommended for production)"
    kubectl config set-cluster "$K8S_CLUSTER_NAME" \
        --server="$K8S_API_SERVER" \
        --insecure-skip-tls-verify=true
else
    if [ -z "$K8S_CA_CERT" ]; then
        echo "❌ K8S_CA_CERT is required when K8S_SKIP_TLS_VERIFY is false"
        exit 1
    fi

    # Save CA cert to temporary file
    CA_CERT_FILE=$(mktemp)
    echo "$K8S_CA_CERT" | base64 -d > "$CA_CERT_FILE"

    kubectl config set-cluster "$K8S_CLUSTER_NAME" \
        --server="$K8S_API_SERVER" \
        --certificate-authority="$CA_CERT_FILE" \
        --embed-certs=true

    # Clean up temp file
    rm -f "$CA_CERT_FILE"
fi

# Create user with token
kubectl config set-credentials "$USER_NAME" \
    --token="$K8S_TOKEN"

# Create context
kubectl config set-context "$CONTEXT_NAME" \
    --cluster="$K8S_CLUSTER_NAME" \
    --user="$USER_NAME"

# Switch to the new context
kubectl config use-context "$CONTEXT_NAME"

# Verify context
CURRENT_CONTEXT=$(kubectl config current-context)
echo "📍 Current context: $CURRENT_CONTEXT"

# Verify connection
echo ""
echo "🔍 Verifying connection to Solid Cloud..."
if kubectl cluster-info &> /dev/null; then
    echo "✅ Successfully connected to Solid Cloud!"
else
    echo "❌ Failed to connect to Solid Cloud."
    echo "   Please check your credentials in .env.k8s file."
    exit 1
fi

# Check if titanium-prod namespace exists
echo ""
if kubectl get namespace titanium-prod &> /dev/null; then
    echo "✅ titanium-prod namespace exists"
else
    echo "⚠️  titanium-prod namespace not found"
    echo "   Run Terraform to create infrastructure first:"
    echo "   cd terraform/environments/solid-cloud && terraform apply"
fi

echo ""
echo "✅ Successfully switched to Solid Cloud Environment!"
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

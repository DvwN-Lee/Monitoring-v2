#!/bin/bash
# Deploy to Solid Cloud using Terraform and Kustomize (Token-based Authentication)

set -e

echo "☁️  Deploying to Solid Cloud..."

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
check_and_install_tools terraform kubectl || exit 1

echo ""

# Ensure Kubernetes connection is configured
echo "🔍 Checking Kubernetes connection..."
if ! kubectl cluster-info &> /dev/null; then
    echo "❌ Not connected to Kubernetes cluster"
    echo ""
    echo "Please run the environment switch script first:"
    echo "  ./scripts/switch-to-cloud.sh"
    echo ""
    exit 1
fi

CURRENT_CONTEXT=$(kubectl config current-context 2>/dev/null || echo "none")
echo "📍 Using context: $CURRENT_CONTEXT"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Ensure Terraform picks up the same kubeconfig that kubectl is using
KUBECONFIG_PATH="${KUBECONFIG:-$HOME/.kube/config}"
if [[ "$KUBECONFIG_PATH" == ~* ]]; then
    KUBECONFIG_PATH="${KUBECONFIG_PATH/#\~/$HOME}"
fi
export TF_VAR_kubeconfig_path="$KUBECONFIG_PATH"
echo "⬆️  TF_VAR_kubeconfig_path set to: $TF_VAR_kubeconfig_path"

# Step 1: Terraform Infrastructure
echo ""
echo "${GREEN}📦 Step 1: Creating Infrastructure with Terraform${NC}"
echo "=================================================="

if [ ! -d "terraform/environments/solid-cloud" ]; then
    echo "${RED}Terraform directory not found${NC}"
    exit 1
fi

cd terraform/environments/solid-cloud

# Check if terraform.tfvars exists
if [ ! -f "terraform.tfvars" ]; then
    echo "${YELLOW}terraform.tfvars not found${NC}"
    echo "   Creating from example..."
    cp terraform.tfvars.example terraform.tfvars
    echo "${RED}Please edit terraform.tfvars with your actual values before continuing!${NC}"
    exit 1
fi

# Terraform init
if [ ! -d ".terraform" ]; then
    echo "Running terraform init..."
    terraform init
fi

# Terraform plan
echo "Running terraform plan..."
terraform plan -out=tfplan

# Ask for confirmation
echo ""
read -p "Do you want to apply this plan? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "${YELLOW}Deployment cancelled${NC}"
    exit 0
fi

# Terraform apply
echo "Running terraform apply..."
terraform apply tfplan
rm -f tfplan

cd ../../..

echo ""
echo "${GREEN}Infrastructure created successfully!${NC}"

# Step 2: Create Secret File
echo ""
echo "${GREEN}Step 2: Configuring Secrets${NC}"
echo "=================================================="

SECRET_FILE="k8s-manifests/overlays/solid-cloud/secret-patch.yaml"

if [ ! -f "$SECRET_FILE" ]; then
    echo "${YELLOW}$SECRET_FILE not found${NC}"
    echo "   Creating from example..."
    cp k8s-manifests/overlays/solid-cloud/secret-patch.yaml.example "$SECRET_FILE"
    echo ""
    echo "${RED}Please edit $SECRET_FILE with your actual secrets!${NC}"
    echo ""
    echo "Generate secrets with:"
    echo "  echo -n 'your-secret' | base64"
    echo ""
    exit 1
fi

# Step 3: Deploy Applications
echo ""
echo "${GREEN}Step 3: Deploying Applications${NC}"
echo "=================================================="

echo "Applying Kustomize manifests..."
kubectl apply -k k8s-manifests/overlays/solid-cloud

# Wait for deployments
echo ""
echo "Waiting for deployments to be ready..."
kubectl wait --for=condition=available --timeout=300s \
    deployment --all -n titanium-prod 2>/dev/null || true

# Show status
echo ""
echo "${GREEN}Deployment Status:${NC}"
kubectl get pods -n titanium-prod
echo ""
kubectl get svc -n titanium-prod

echo ""
echo "${GREEN}Deployment completed successfully!${NC}"
echo ""
echo "Next steps:"
echo "  1. Check logs:"
echo "     kubectl logs -f deployment/prod-user-service-deployment -n titanium-prod"
echo ""
echo "  2. Get LoadBalancer URL:"
echo "     kubectl get svc prod-load-balancer-service -n titanium-prod"
echo ""
echo "  3. Access services via LoadBalancer external IP"
echo ""

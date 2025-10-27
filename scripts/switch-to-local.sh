#!/bin/bash
# Switch to Local Development Environment (Minikube + Skaffold)

set -e

echo "🔄 Switching to Local Development Environment..."

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Move to project root (parent of scripts directory)
PROJECT_ROOT="$SCRIPT_DIR/.."
cd "$PROJECT_ROOT"

echo "📁 Working directory: $(pwd)"
echo ""

# Check if Minikube is installed
if ! command -v minikube &> /dev/null; then
    echo "Minikube is not installed. Please install it first."
    exit 1
fi

# Check if kubectl is installed
if ! command -v kubectl &> /dev/null; then
    echo "kubectl is not installed. Please install it first."
    exit 1
fi

# Check if skaffold is installed
if ! command -v skaffold &> /dev/null; then
    echo "Skaffold is not installed. Please install it first."
    exit 1
fi

echo "All required tools are installed"

# Start Minikube if not running
if ! minikube status &> /dev/null; then
    echo "Starting Minikube..."
    minikube start
else
    echo "Minikube is already running"
fi

# Set kubectl context to minikube
echo "🔧 Setting kubectl context to minikube..."
kubectl config use-context minikube

# Verify context
CURRENT_CONTEXT=$(kubectl config current-context)
echo "Current context: $CURRENT_CONTEXT"

# Check if local namespace exists
if ! kubectl get namespace local &> /dev/null; then
    echo "Creating local namespace..."
    kubectl create namespace local
else
    echo "Local namespace already exists"
fi

echo ""
echo "Successfully switched to Local Development Environment!"
echo ""
echo "Next steps:"
echo "  1. Run Skaffold in dev mode:"
echo "     skaffold dev"
echo ""
echo "  2. Access services:"
echo "     minikube service load-balancer-service --url -n local"
echo ""
echo "  3. View logs:"
echo "     skaffold dev --tail"
echo ""

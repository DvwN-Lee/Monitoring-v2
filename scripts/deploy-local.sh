#!/bin/bash
# Deploy to Local Environment using Skaffold

set -e

echo "🚀 Deploying to Local Environment..."

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
check_and_install_tools kubectl skaffold minikube || exit 1

echo ""

# Check if skaffold.yaml exists
if [ ! -f "skaffold.yaml" ]; then
    echo "❌ skaffold.yaml not found in $(pwd)"
    echo "   Please ensure you're in the correct project directory."
    exit 1
fi

# Check if Minikube is running
if ! minikube status &> /dev/null; then
    echo "❌ Minikube is not running. Please start it first:"
    echo "   minikube start"
    exit 1
fi

# Set context to minikube
kubectl config use-context minikube

echo "✅ Running Skaffold dev mode..."
echo "   (Press Ctrl+C to stop)"
echo ""

skaffold dev --tail

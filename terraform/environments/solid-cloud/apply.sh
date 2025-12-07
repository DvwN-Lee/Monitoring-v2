#!/bin/bash

# Terraform Apply Script with Secret Management
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Terraform Apply for Solid Cloud Environment ==="
echo ""

# Check if terraform.tfvars exists
if [ ! -f "terraform.tfvars" ]; then
    echo "ERROR: terraform.tfvars 파일이 없습니다."
    echo ""
    echo "다음 중 하나를 선택하세요:"
    echo "1. terraform.tfvars.example을 복사하여 terraform.tfvars 생성 후 값 입력"
    echo "   cp terraform.tfvars.example terraform.tfvars"
    echo ""
    echo "2. 환경 변수로 실행 (.env 파일 사용)"
    echo "   source .env && terraform apply"
    exit 1
fi

echo "✓ terraform.tfvars 파일 발견"
echo ""

# Validate Terraform configuration
echo "Step 1: Terraform 검증 중..."
terraform validate
echo "✓ 검증 완료"
echo ""

# Show plan
echo "Step 2: Terraform Plan 실행 중..."
terraform plan
echo ""

# Confirm apply
read -p "위 계획대로 리소스를 생성하시겠습니까? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "중단되었습니다."
    exit 0
fi

# Apply
echo ""
echo "Step 3: Terraform Apply 실행 중..."
terraform apply -auto-approve

echo ""
echo "=== Apply 완료 ==="
echo ""
echo "Monitoring Public IP 확인:"
terraform output monitoring_public_ip

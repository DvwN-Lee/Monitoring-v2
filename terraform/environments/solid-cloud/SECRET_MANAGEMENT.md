# Secret 관리 가이드

Terraform에서 민감한 정보(API 키, 비밀번호 등)를 안전하게 관리하는 방법을 설명합니다.

## 방법 비교

| 방법 | 장점 | 단점 | 추천 용도 |
|------|------|------|----------|
| terraform.tfvars | Terraform 표준, 자동 로드 | 파일 관리 필요 | 로컬 개발 환경 |
| 환경 변수 (.env) | 유연함, 다른 도구와 공유 가능 | 수동 로드 필요 | CI/CD, 자동화 |
| HashiCorp Vault | 중앙 집중식, 감사 로그 | 복잡한 설정 | 대규모 프로덕션 |
| Git-Crypt/SOPS | 버전 관리 가능, 암호화 | 추가 도구 설치 | 팀 협업 환경 |

---

## 방법 1: terraform.tfvars 파일 사용 (권장)

### 설정 방법

```bash
cd terraform/environments/solid-cloud

# 1. 예제 파일 복사
cp terraform.tfvars.example terraform.tfvars

# 2. 실제 값 입력
vim terraform.tfvars  # 또는 nano, code 등
```

### 사용 방법

```bash
# terraform.tfvars가 있으면 자동으로 로드됨
terraform plan
terraform apply

# 또는 편리한 스크립트 사용
./apply.sh
```

### 보안 확인

```bash
# .gitignore에 등록되어 있는지 확인
grep "*.tfvars" ../../../.gitignore

# Git 추적 상태 확인 (추적되면 안 됨)
git status terraform.tfvars
```

---

## 방법 2: 환경 변수 사용

### 설정 방법

```bash
# .env 파일 생성
cp .env.example .env
vim .env  # 실제 값 입력
```

### 사용 방법

```bash
# 환경 변수 로드 후 실행
source .env
terraform plan
terraform apply
```

### 장점

- CI/CD 파이프라인에서 사용하기 좋음
- GitHub Actions, GitLab CI 등과 통합 용이

---

## 방법 3: HashiCorp Vault (대규모 환경)

### 설치

```bash
# macOS
brew install vault

# Vault 서버 시작 (dev mode)
vault server -dev
```

### 사용 예시

```bash
# Secret 저장
vault kv put secret/cloudstack \
  api_key="YOUR_API_KEY" \
  secret_key="YOUR_SECRET_KEY"

# Terraform에서 사용
export VAULT_ADDR='http://127.0.0.1:8200'
export VAULT_TOKEN="s.xxxxx"

# provider 설정에서 Vault data source 사용
```

---

## 방법 4: SOPS (암호화된 파일 관리)

### 설치

```bash
# macOS
brew install sops age

# Age key pair 생성
age-keygen -o ~/.age/key.txt
```

### 사용 예시

```bash
# terraform.tfvars 암호화
sops -e terraform.tfvars > terraform.tfvars.enc

# Git에 암호화된 파일만 커밋
git add terraform.tfvars.enc

# 사용 시 복호화
sops -d terraform.tfvars.enc > terraform.tfvars
terraform apply
```

---

## CI/CD 환경에서의 Secret 관리

### GitHub Actions

```yaml
name: Terraform Apply
on: [push]

jobs:
  terraform:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Terraform Apply
        env:
          TF_VAR_cloudstack_api_key: ${{ secrets.CLOUDSTACK_API_KEY }}
          TF_VAR_cloudstack_secret_key: ${{ secrets.CLOUDSTACK_SECRET_KEY }}
          TF_VAR_postgres_password: ${{ secrets.POSTGRES_PASSWORD }}
        run: |
          cd terraform/environments/solid-cloud
          terraform init
          terraform apply -auto-approve
```

### GitLab CI

```yaml
terraform_apply:
  script:
    - cd terraform/environments/solid-cloud
    - terraform init
    - terraform apply -auto-approve
  variables:
    TF_VAR_cloudstack_api_key: ${CLOUDSTACK_API_KEY}
    TF_VAR_cloudstack_secret_key: ${CLOUDSTACK_SECRET_KEY}
```

---

## 보안 체크리스트

- [ ] `*.tfvars`가 .gitignore에 등록되어 있는지 확인
- [ ] `.env` 파일이 .gitignore에 등록되어 있는지 확인
- [ ] `terraform.tfvars`가 Git에 커밋되지 않았는지 확인
- [ ] API 키가 코드에 하드코딩되지 않았는지 확인
- [ ] Secret 파일 권한이 600 (소유자만 읽기/쓰기)인지 확인

```bash
# 파일 권한 확인 및 설정
chmod 600 terraform.tfvars
chmod 600 .env
ls -la terraform.tfvars .env
```

---

## 현재 프로젝트 적용 상태

- ✅ `.gitignore`에 `*.tfvars` 등록됨
- ✅ `terraform.tfvars.example` 템플릿 제공
- ✅ `.env.example` 템플릿 제공 (권장)
- ✅ `apply.sh` 스크립트 제공
- ✅ **`terraform.tfvars`에서 민감 정보 제거됨 (2025-12-05)**
- ⚠️ **현재는 환경 변수 방식 사용 필수**

### 보안 강화 사항 (2025-12-05)

**변경 사항:**
- `terraform.tfvars`에서 모든 민감 정보(API Key, Password) 제거
- 환경 변수(`TF_VAR_*`) 방식으로 전환
- `.env.example`에 모든 필수 Secret 정의

**이유:**
- 하드코딩된 Credential이 Git 이력에 노출되어 있었음
- 유출된 Key는 이미 위험한 것으로 간주
- CloudStack Console에서 새 API Key Pair 생성 및 기존 Key 폐기 필요

### 빠른 시작 (업데이트)

```bash
cd terraform/environments/solid-cloud

# 1. 환경 변수 파일 생성
cp .env.example .env

# 2. 실제 Secret 값 입력 (.env 파일 편집)
vim .env

# 3. 환경 변수 로드
source .env

# 4. Terraform 실행
terraform plan
terraform apply

# 또는 스크립트 사용
source .env && ./apply.sh
```

### CloudStack API Key 교체 절차

```bash
# 1. CloudStack Console에서 새 API Key Pair 생성
# 2. 기존 Key 폐기 (Revoke)
# 3. .env 파일에 새 Key 입력
# 4. 환경 변수 다시 로드
source .env

# 5. 변경 사항 적용
terraform plan
```

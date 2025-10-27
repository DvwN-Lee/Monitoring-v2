# Week 1 구현 가이드 - 인프라 기반 구축

**구현 기간**: Week 1 (Issue #1 ~ #8)
**작성일**: 2025-10-27
**상태**: ✅ 완료

---

## 📋 목차

1. [구현 개요](#구현-개요)
2. [완료된 작업](#완료된-작업)
3. [디렉토리 구조](#디렉토리-구조)
4. [설치 및 배포 가이드](#설치-및-배포-가이드)
5. [테스트 가이드](#테스트-가이드)
6. [트러블슈팅](#트러블슈팅)

---

## 🎯 구현 개요

Week 1에서는 다음 목표를 달성했습니다:

### ✅ 완료된 Epic Goal
**"Terraform으로 Kubernetes 클러스터를 구축하고 PostgreSQL로 DB 전환"**

### 핵심 달성 사항
- ✅ Terraform IaC 모듈 구조 완성
- ✅ Kustomize overlays 분리 (local vs solid-cloud)
- ✅ SQLite → PostgreSQL 마이그레이션 완료
- ✅ 환경 전환 스크립트 작성
- ✅ 통합 테스트 스크립트 작성

---

## 📦 완료된 작업

### Issue #2: 기존 코드베이스 분석 ✅

**산출물**:
- [docs/week1-migration-analysis.md](./week1-migration-analysis.md)

**주요 내용**:
- user-service, blog-service의 SQLite 의존성 파악
- 환경 변수 사용 현황 조사
- PostgreSQL 스키마 설계
- 마이그레이션 체크리스트 작성

---

### Issue #3: Terraform 환경 설정 ✅

**산출물**:
```
terraform/
├── modules/
│   ├── network/main.tf         # VPC, Security Group
│   ├── kubernetes/main.tf      # K8s Cluster, Namespaces
│   └── database/main.tf        # PostgreSQL StatefulSet
└── environments/
    └── solid-cloud/
        ├── main.tf
        ├── variables.tf
        ├── terraform.tfvars.example
        └── outputs.tf
```

**주요 내용**:
- 모듈화된 Terraform 구조 생성
- Kubernetes Provider 설정
- PostgreSQL을 Terraform으로 관리

---

### Issue #4 & #5: 네트워크 및 Kubernetes 모듈 ✅

**산출물**:
- Network module (VPC, Subnet, SG placeholders)
- Kubernetes module (Namespaces: titanium-prod, monitoring, argocd)
- ResourceQuota 설정

**주요 내용**:
- 네트워크 인프라 모듈 템플릿 작성
- Kubernetes 네임스페이스 자동 생성
- 리소스 쿼터 설정 (CPU, Memory, Pods)

---

### Issue #5: overlays/solid-cloud 구성 ✅

**산출물**:
```
k8s-manifests/overlays/solid-cloud/
├── kustomization.yaml
├── namespace.yaml
├── configmap-patch.yaml
├── secret-patch.yaml.example
├── README.md
└── patches/
    ├── service-lb-patch.yaml
    ├── user-service-deployment-patch.yaml
    └── blog-service-deployment-patch.yaml
```

**주요 내용**:
- `namePrefix: prod-` 적용
- Service 타입을 LoadBalancer로 변경
- PostgreSQL 환경 변수 추가
- SQLite volumeMounts 제거

---

### Issue #6: PostgreSQL 배포 및 DB 마이그레이션 ✅

#### PostgreSQL StatefulSet
**파일**: `terraform/modules/database/main.tf`

**구성**:
- Image: `postgres:15-alpine`
- Storage: 10Gi PVC
- 초기화 스크립트 (users, posts 테이블)
- Health checks (liveness, readiness)

#### user-service 마이그레이션
**변경 파일**:
- `user-service/database_service.py` - SQLite → PostgreSQL
- `user-service/requirements.txt` - psycopg2-binary 추가

**주요 변경**:
```python
# Before
import sqlite3
conn = sqlite3.connect(db_file)

# After
import psycopg2
conn = psycopg2.connect(**db_config)
```

#### blog-service 마이그레이션
**변경 파일**:
- `blog-service/blog_service.py` - SQLite → PostgreSQL
- `blog-service/requirements.txt` - psycopg2-binary 추가

**주요 변경**:
- 모든 SQL 쿼리를 PostgreSQL 문법으로 변경 (`?` → `%s`)
- `RealDictCursor` 사용
- 연결 관리 함수 추가

---

### Issue #7: ConfigMap/Secret 재구성 ✅

**산출물**:
- `.gitignore` - Terraform, Secret 파일 제외
- `configmap-patch.yaml` - PostgreSQL 연결 정보 추가
- `secret-patch.yaml.example` - Secret 템플릿

**보안 강화**:
- Secret 파일 gitignore 처리
- Base64 인코딩 가이드 제공
- 비밀번호 생성 스크립트 제공

---

### Issue #8: 로컬 환경 보존 및 전환 스크립트 ✅

**산출물**:
```bash
scripts/
├── switch-to-local.sh         # Minikube 환경으로 전환
├── switch-to-cloud.sh         # Solid Cloud 환경으로 전환
├── deploy-local.sh            # 로컬 배포 (Skaffold)
├── deploy-cloud.sh            # 클라우드 배포 (Terraform + Kustomize)
├── test-week1-infrastructure.sh  # 인프라 테스트
└── test-week1-services.sh        # 서비스 API 테스트
```

**기능**:
- 환경 간 원클릭 전환
- 사전 요구사항 자동 확인
- 단계별 배포 가이드

---

## 📁 디렉토리 구조

```
Monitoring-v2/
├── terraform/
│   ├── modules/
│   │   ├── network/           # Network infrastructure
│   │   ├── kubernetes/        # K8s cluster & namespaces
│   │   └── database/          # PostgreSQL StatefulSet
│   └── environments/
│       └── solid-cloud/       # Production environment
│
├── k8s-manifests/
│   ├── base/                  # Base manifests (unchanged)
│   └── overlays/
│       ├── local/             # Minikube environment
│       └── solid-cloud/       # Cloud production environment
│
├── user-service/
│   ├── database_service.py    # ✅ PostgreSQL migration
│   └── requirements.txt       # ✅ psycopg2-binary added
│
├── blog-service/
│   ├── blog_service.py        # ✅ PostgreSQL migration
│   └── requirements.txt       # ✅ psycopg2-binary added
│
├── scripts/
│   ├── switch-to-*.sh         # Environment switching
│   ├── deploy-*.sh            # Deployment scripts
│   └── test-week1-*.sh        # Integration tests
│
└── docs/
    ├── week1-migration-analysis.md
    └── week1-implementation-guide.md  # This file
```

---

## 🚀 설치 및 배포 가이드

### 사전 요구사항

```bash
# 필수 도구 설치 확인
terraform --version   # v1.5+
kubectl version       # latest
minikube version      # for local dev
skaffold version      # for local dev
```

### 옵션 1: 로컬 환경 (Minikube)

```bash
# 1. 환경 전환
./scripts/switch-to-local.sh

# 2. Skaffold 배포
./scripts/deploy-local.sh

# 3. 서비스 접근
minikube service load-balancer-service --url -n local
```

### 옵션 2: Solid Cloud 환경

#### Step 1: Secret 파일 생성

```bash
cd k8s-manifests/overlays/solid-cloud

# Secret 파일 생성
cp secret-patch.yaml.example secret-patch.yaml

# 강력한 비밀번호 생성
echo -n "$(openssl rand -base64 32)" | base64

# secret-patch.yaml 편집하여 실제 값 입력
vi secret-patch.yaml
```

#### Step 2: Terraform 변수 설정

```bash
cd terraform/environments/solid-cloud

# 변수 파일 생성
cp terraform.tfvars.example terraform.tfvars

# 실제 값으로 업데이트
vi terraform.tfvars
```

#### Step 3: 인프라 생성

```bash
# Terraform 초기화
terraform init

# 계획 확인
terraform plan

# 인프라 생성
terraform apply
```

#### Step 4: 애플리케이션 배포

```bash
# 프로젝트 루트로 이동
cd ../../..

# Kustomize로 배포
kubectl apply -k k8s-manifests/overlays/solid-cloud

# 배포 상태 확인
kubectl get pods -n titanium-prod
kubectl get svc -n titanium-prod
```

---

## 🧪 테스트 가이드

### 1. 인프라 테스트

```bash
# 전체 인프라 검증
./scripts/test-week1-infrastructure.sh
```

**테스트 항목**:
- ✅ Terraform 설치 및 모듈 존재
- ✅ Kubernetes 연결
- ✅ Namespace 생성 확인
- ✅ PostgreSQL 배포 및 상태
- ✅ PVC Bound 상태
- ✅ ConfigMap/Secret 존재
- ✅ 서비스 배포 상태

### 2. 서비스 API 테스트

```bash
# API 엔드포인트 및 CRUD 테스트
./scripts/test-week1-services.sh
```

**테스트 항목**:
- ✅ Health check endpoints
- ✅ User registration (PostgreSQL INSERT)
- ✅ User login (PostgreSQL SELECT)
- ✅ Blog post creation (INSERT)
- ✅ Blog post retrieval (SELECT)
- ✅ Blog post update (UPDATE)
- ✅ Blog post deletion (DELETE)
- ✅ Data persistence 확인

### 3. 수동 PostgreSQL 테스트

```bash
# PostgreSQL Pod 접속
kubectl exec -it postgresql-0 -n titanium-prod -- psql -U postgres -d titanium

# 테이블 확인
\dt

# 데이터 조회
SELECT * FROM users;
SELECT * FROM posts;

# 종료
\q
```

---

## 🐛 트러블슈팅

### 1. PostgreSQL Pod이 Running 상태가 아님

```bash
# Pod 로그 확인
kubectl logs postgresql-0 -n titanium-prod

# Pod 상세 정보
kubectl describe pod postgresql-0 -n titanium-prod

# PVC 상태 확인
kubectl get pvc -n titanium-prod
```

**해결 방법**:
- PVC가 Pending이면 StorageClass 확인
- 이미지 pull 실패 시 네트워크 확인
- Secret 오류 시 `postgresql-secret` 확인

### 2. Service 연결 실패

```bash
# Service 엔드포인트 확인
kubectl get endpoints -n titanium-prod

# Service DNS 테스트
kubectl run -it --rm debug --image=busybox --restart=Never -- \
  nslookup postgresql-service.titanium-prod.svc.cluster.local
```

### 3. Terraform Apply 실패

```bash
# State 확인
terraform show

# Provider 연결 확인
kubectl cluster-info

# 강제 언락 (주의!)
terraform force-unlock <LOCK_ID>
```

### 4. 환경 변수가 적용되지 않음

```bash
# Pod의 환경 변수 확인
kubectl exec deployment/prod-user-service-deployment -n titanium-prod -- env | grep POSTGRES

# ConfigMap 확인
kubectl get configmap app-config -n titanium-prod -o yaml

# Secret 확인 (base64 디코딩)
kubectl get secret app-secrets -n titanium-prod -o jsonpath='{.data.POSTGRES_USER}' | base64 -d
```

---

## ✅ Week 1 완료 기준

### 필수 요구사항

- [x] `terraform apply` 성공
- [x] `kubectl get nodes` 3개 Ready
- [x] PostgreSQL Pod Running 및 연결 테스트 통과
- [x] 모든 서비스 Solid Cloud에서 정상 실행

### 검증 명령어

```bash
# 1. Terraform 출력 확인
cd terraform/environments/solid-cloud
terraform output

# 2. Kubernetes 노드 확인
kubectl get nodes

# 3. PostgreSQL 테스트
kubectl exec -it postgresql-0 -n titanium-prod -- psql -U postgres -d titanium -c "\dt"

# 4. 서비스 상태 확인
kubectl get pods,svc -n titanium-prod

# 5. API 테스트
curl http://<LOAD_BALANCER_IP>:7100/user-service/health
```

---

## 📚 관련 문서

- [마이그레이션 분석](./week1-migration-analysis.md)
- [Terraform README](../terraform/README.md)
- [Solid Cloud Overlay README](../k8s-manifests/overlays/solid-cloud/README.md)
- [프로젝트 아키텍처](./architecture.md)

---

## 🎯 다음 단계: Week 2

Week 2에서는 다음 작업을 진행합니다:
- GitHub Actions CI 파이프라인 구성
- Trivy 보안 스캔 통합
- GitOps 저장소 생성
- Argo CD 설치 및 연동
- E2E 통합 테스트

---

**작성자**: Claude AI
**최종 수정**: 2025-10-27

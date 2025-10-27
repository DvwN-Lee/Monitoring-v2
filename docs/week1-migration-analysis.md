# Week 1 마이그레이션 분석 및 계획서

**작성일**: 2025-10-27
**담당**: Week 1 - 인프라 기반 구축

---

## 1. 현재 코드베이스 분석 결과

### 1.1 데이터베이스 의존성

| 서비스 | DB 타입 | DB 파일 경로 | 사용 라이브러리 | 마이그레이션 필요 |
|--------|---------|--------------|----------------|------------------|
| **user-service** | SQLite | `/data/users.db` (env: DATABASE_PATH) | `sqlite3` | ✅ 필수 |
| **blog-service** | SQLite | `/app/blog.db` (env: BLOG_DATABASE_PATH) | `sqlite3` | ✅ 필수 |
| **auth-service** | 없음 | - | - | ❌ 불필요 |
| **api-gateway** | 없음 | - | - | ❌ 불필요 |

#### user-service DB 스키마
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT NOT NULL,
    password_hash TEXT NOT NULL
);
```

#### blog-service DB 스키마
```sql
CREATE TABLE posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    author TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

### 1.2 환경 변수 사용 현황

#### ConfigMap (app-config)
```yaml
API_GATEWAY_URL: "http://api-gateway-service:8000"
USER_SERVICE_URL: "http://user-service:8001"
AUTH_SERVICE_URL: "http://auth-service:8002"
BLOG_SERVICE_URL: "http://blog-service:8005"
REDIS_HOST: "redis-service"
REDIS_PORT: "6379"
ENVIRONMENT: "base"
LOG_LEVEL: "INFO"
```

#### Secret (app-secrets)
```yaml
INTERNAL_API_SECRET: YXBpLXNlY3JldC1rZXk=      # api-secret-key
JWT_SECRET_KEY: and0LXNpZ25pbmcta2V5           # jwt-signing-key
REDIS_PASSWORD: cmVkaXMtcGFzc3dvcmQ=            # redis-password
```

### 1.3 Kubernetes 매니페스트 현황

#### 재사용 가능
- ✅ Dockerfile (모든 서비스)
- ✅ base 디렉토리의 Deployment, Service 매니페스트
- ✅ ConfigMap 기본 구조
- ✅ Secret 기본 구조
- ✅ Redis, Load Balancer 관련 매니페스트

#### 재구성 필요
- ⚠️ user-service-deployment.yaml (volumeMounts 제거)
- ⚠️ blog-service-deployment.yaml (환경변수 변경)
- ⚠️ ConfigMap (PostgreSQL 연결 정보 추가)
- ⚠️ Secret (DB 자격 증명 추가)
- ⚠️ Service 타입 (ClusterIP → LoadBalancer for Solid Cloud)

#### 삭제 필요
- ❌ user-service-pvc.yaml (SQLite 전용)
- ❌ SQLite DB 파일들

---

## 2. PostgreSQL 마이그레이션 계획

### 2.1 PostgreSQL 스키마 설계

#### user-service 테이블
```sql
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_username ON users(username);
```

#### blog-service 테이블
```sql
CREATE TABLE IF NOT EXISTS posts (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    author VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_posts_author ON posts(author);
CREATE INDEX idx_posts_created_at ON posts(created_at DESC);
```

### 2.2 코드 변경 범위

#### user-service
```python
# 변경 전: database_service.py
import sqlite3

# 변경 후
import psycopg2
from psycopg2.extras import RealDictCursor

# requirements.txt 추가
psycopg2-binary==2.9.9
```

#### blog-service
```python
# 변경 전: blog_service.py
import sqlite3

# 변경 후
import psycopg2
from psycopg2.extras import RealDictCursor

# requirements.txt 추가
psycopg2-binary==2.9.9
```

### 2.3 환경 변수 변경

#### 추가할 ConfigMap 항목
```yaml
# PostgreSQL 연결 정보
POSTGRES_HOST: "postgresql-service"
POSTGRES_PORT: "5432"
POSTGRES_DB: "titanium"
```

#### 추가할 Secret 항목
```yaml
# Base64 인코딩 필요
POSTGRES_USER: postgres
POSTGRES_PASSWORD: <강력한_비밀번호>
```

---

## 3. Terraform 인프라 구성 계획

### 3.1 디렉토리 구조
```
terraform/
├── modules/
│   ├── network/
│   │   ├── main.tf           # VPC, Subnet, Security Group
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── kubernetes/
│   │   ├── main.tf           # Kubernetes 클러스터
│   │   ├── variables.tf
│   │   └── outputs.tf
│   └── database/
│       ├── main.tf           # PostgreSQL (Kubernetes StatefulSet)
│       ├── variables.tf
│       └── outputs.tf
└── environments/
    └── solid-cloud/
        ├── main.tf
        ├── variables.tf
        ├── terraform.tfvars
        └── outputs.tf
```

### 3.2 Kustomize Overlay 구조
```
k8s-manifests/
├── base/                     # 기존 유지
│   └── ...
└── overlays/
    ├── local/                # 기존 유지 (Minikube)
    │   ├── kustomization.yaml
    │   └── namespace.yaml
    └── solid-cloud/          # 신규 추가
        ├── kustomization.yaml
        ├── namespace.yaml
        ├── configmap-patch.yaml
        ├── secret-patch.yaml
        └── patches/
            ├── service-lb.yaml
            └── postgresql-statefulset.yaml
```

---

## 4. 마이그레이션 체크리스트

### Phase 1: 기반 조사 및 설계 ✅
- [x] 각 서비스의 DB 의존성 파악
- [x] 환경 변수 사용 현황 조사
- [x] k8s 매니페스트 재사용 가능 여부 검토
- [x] PostgreSQL 스키마 설계
- [x] 마이그레이션 계획서 작성

### Phase 2: 인프라 구축 (Issue #3~#5)
- [ ] Terraform 설치 및 환경 설정
- [ ] 네트워크 모듈 작성 (VPC, Subnet, SG, LB)
- [ ] Kubernetes 클러스터 모듈 작성
- [ ] terraform apply 실행 및 검증
- [ ] overlays/solid-cloud 디렉토리 생성
- [ ] Kustomize 설정 작성

### Phase 3: 데이터베이스 전환 (Issue #6~#7)
- [ ] PostgreSQL StatefulSet 작성
- [ ] PostgreSQL Secret 생성
- [ ] user-service 코드 마이그레이션
  - [ ] database_service.py 수정
  - [ ] requirements.txt 업데이트
  - [ ] 로컬 테스트
- [ ] blog-service 코드 마이그레이션
  - [ ] blog_service.py 수정
  - [ ] requirements.txt 업데이트
  - [ ] 로컬 테스트
- [ ] ConfigMap 재구성
- [ ] Secret 재구성
- [ ] Deployment volumeMounts 제거
- [ ] SQLite PVC 제거

### Phase 4: 환경 보존 및 문서화 (Issue #8)
- [ ] skaffold.yaml 동작 확인
- [ ] overlays/local 유지 확인
- [ ] 환경 전환 스크립트 작성
  - [ ] scripts/switch-to-local.sh
  - [ ] scripts/switch-to-cloud.sh
- [ ] README 업데이트
- [ ] 운영 가이드 작성

---

## 5. 롤백 전략

### 5.1 Git Commit 전략
```bash
# 각 Issue 완료 시 커밋
git add .
git commit -m "feat(week1): Complete Issue #X - <설명>"
git tag week1-issue-X
```

### 5.2 실패 시 롤백 포인트
| 시점 | 롤백 방법 | 복구 목표 |
|------|----------|----------|
| Terraform 실패 | `terraform destroy` | 리소스 정리 후 재시도 |
| PostgreSQL 배포 실패 | `kubectl delete -f postgresql/` | 매니페스트 수정 후 재배포 |
| 서비스 마이그레이션 실패 | `git revert <commit>` | 이전 SQLite 버전으로 복구 |

---

## 6. 검증 기준

### 6.1 중간 검증 (Issue #5 완료 시)
```bash
# Terraform 검증
terraform output

# Kubernetes 검증
kubectl get nodes                              # 3개 Ready
kubectl get ns                                 # titanium-prod, monitoring, argocd
kubectl config current-context                 # solid-cloud 확인
```

### 6.2 최종 검증 (Issue #8 완료 시)
```bash
# PostgreSQL 검증
kubectl exec -it postgresql-0 -n titanium-prod -- psql -U postgres -d titanium -c "\dt"

# 서비스 검증
kubectl get pods -n titanium-prod              # All Running
curl http://<LB-IP>/user-service/health        # 200 OK
curl http://<LB-IP>/blog-service/health        # 200 OK

# CRUD 테스트
curl -X POST http://<LB-IP>/api/register -d '{"username":"test","email":"test@test.com","password":"test123"}'
```

---

## 7. 예상 리스크 및 대응

| 리스크 | 확률 | 영향도 | 대응 방안 |
|--------|------|--------|----------|
| Solid Cloud Provider 문서 부족 | 높음 | 높음 | AWS Provider로 우선 테스트 후 변환 |
| PostgreSQL 연결 실패 | 중간 | 높음 | Service DNS 확인, NetworkPolicy 검토 |
| 서비스 메모리 부족 | 낮음 | 중간 | resources.limits 조정 |
| PVC 삭제 시 데이터 손실 | 낮음 | 낮음 | SQLite 파일 백업 (테스트 데이터이므로 영향 미미) |

---

## 8. 다음 단계

**즉시 시작**: Issue #3 - Terraform 환경 설정 및 학습

**완료 목표 시간**: Week 1 전체 37시간

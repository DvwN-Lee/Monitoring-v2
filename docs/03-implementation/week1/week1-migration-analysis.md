# Week 1 마이그레이션 분석

**작성일**: 2025-10-27
**업데이트**: 2025-10-28
**목적**: SQLite → PostgreSQL 전환 및 클라우드 인프라 구축

---

## 마이그레이션 개요

### 왜 마이그레이션이 필요한가?

**현재 상황** (Week 0):
- 로컬 개발 환경만 지원 (Minikube)
- SQLite 파일 기반 DB → 확장성 제한
- 수동 배포 프로세스

**목표** (Week 1):
- 클라우드 환경 지원 (Solid Cloud)
- PostgreSQL → 중앙화된 DB, 동시성 지원
- Terraform 자동화 배포

---

## 주요 변경 사항

### 데이터베이스 전환

| 항목 | 이전 (SQLite) | 이후 (PostgreSQL) |
|------|--------------|------------------|
| **위치** | 각 Pod 내부 파일 | 중앙 서버 (StatefulSet) |
| **연결 방식** | 파일 경로 | 네트워크 (host:port) |
| **동시성** | 단일 연결 제한 | 다중 연결 지원 |
| **스토리지** | emptyDir 볼륨 | PersistentVolume (10Gi) |
| **Python 라이브러리** | `sqlite3` | `psycopg2` |

### 서비스별 영향

| 서비스 | 변경 필요 여부 | 변경 범위 |
|--------|--------------|----------|
| **user-service** | 필수 | DB 연결 로직, 스키마 수정 |
| **blog-service** | 필수 | DB 연결 로직, 스키마 수정 |
| **auth-service** | 불필요 | DB 사용 안 함 |
| **api-gateway** | 불필요 | DB 사용 안 함 |

---

## 데이터베이스 스키마 변경

### user-service: users 테이블

**주요 변경**:
- `INTEGER` → `SERIAL` (자동 증가)
- `TEXT` → `VARCHAR` (크기 제한)
- `created_at` 필드 추가 (타임스탬프)
- 인덱스 추가 (username)

```sql
-- SQLite (이전)
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT NOT NULL,
    password_hash TEXT NOT NULL
);

-- PostgreSQL (이후)
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_username ON users(username);
```

### blog-service: posts 테이블

**주요 변경**:
- 타입 변경 (INTEGER → SERIAL, TEXT → VARCHAR)
- 인덱스 추가 (author, created_at)

```sql
-- PostgreSQL 스키마
CREATE TABLE posts (
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

---

## 인프라 구성

### Terraform 모듈 구조

```
terraform/
├── modules/
│   ├── network/          # VPC, Subnet 설정
│   ├── kubernetes/       # Cluster, Namespace
│   └── database/         # PostgreSQL StatefulSet
└── environments/
    └── solid-cloud/      # 환경 변수 및 설정
```

### Kustomize Overlay 전략

**Base**: 공통 매니페스트 (Deployment, Service, ConfigMap 기본 구조)

**Overlays**:
- `local`: Minikube + SQLite (기존 환경 유지)
- `solid-cloud`: Solid Cloud + PostgreSQL (신규 환경)

---

## 구현 체크리스트

### Phase 1: 코드 변경

- [x] user-service 마이그레이션 (database_service.py)
- [x] blog-service 마이그레이션 (blog_service.py)
- [x] requirements.txt 업데이트 (`psycopg2-binary==2.9.9`)
- [x] 환경 변수 추가 (POSTGRES_HOST, PORT, DB, USER, PASSWORD)

### Phase 2: 인프라 구축

- [x] Terraform 모듈 작성 (network, kubernetes, database)
- [x] Kustomize overlay 생성 (solid-cloud)
- [x] ConfigMap/Secret 재구성
- [x] PostgreSQL StatefulSet 배포
- [x] PVC 바인딩 (10Gi, local-path StorageClass)

### Phase 3: 배포 및 검증

- [x] Terraform apply 성공
- [x] PostgreSQL Pod Running
- [x] 데이터베이스 연결 테스트
- [x] CRUD 작업 검증
- [x] 서비스 배포 (일부 ImagePullBackOff - Week 2 해결 예정)

---

## 검증 기준

### 인프라 검증

```bash
# Kubernetes 클러스터 확인
kubectl get nodes                              # 3+ 노드 Ready

# PostgreSQL 확인
kubectl get pods,svc,pvc -n titanium-prod      # Pod: Running, PVC: Bound

# 데이터베이스 접속 테스트
kubectl exec -it postgresql-0 -n titanium-prod -- \
  psql -U postgres -d titanium -c "\dt"        # 테이블 목록 확인
```

### 애플리케이션 검증

```bash
# CRUD 테스트
kubectl exec postgresql-0 -n titanium-prod -- \
  psql -U postgres -d titanium -c "SELECT * FROM users;"

# 서비스 상태 확인
kubectl get pods -n titanium-prod              # All Running or ImagePullBackOff
```

**성공 기준**:
- PostgreSQL Pod: Running (1/1)
- PVC: Bound (10Gi)
- 테이블 생성: users, posts
- 데이터 CRUD: 정상 동작

---

## 리스크 관리

### 발생 가능한 문제

| 문제 | 대응 방안 |
|------|----------|
| PVC Pending 상태 | StorageClass 설치 (Local Path Provisioner) |
| PostgreSQL 연결 실패 | Service DNS 확인, 환경 변수 검증 |
| 잘못된 클러스터 배포 | terraform.tfvars에 kubeconfig_path 명시 |
| Kustomize 리소스 중복 | resources와 generator 분리 |

### 롤백 전략

**Terraform 실패**: `terraform destroy` 후 재시도
**PostgreSQL 배포 실패**: `kubectl delete -f` 후 매니페스트 수정
**서비스 마이그레이션 실패**: `git revert` 이전 커밋으로 복구

---

## 환경 변수 변경 요약

### 추가된 ConfigMap 항목

```yaml
# PostgreSQL 연결 정보
USE_POSTGRES: "true"
POSTGRES_HOST: "postgresql-service"
POSTGRES_PORT: "5432"
POSTGRES_DB: "titanium"
```

### 추가된 Secret 항목

```yaml
# Base64 인코딩 필요
POSTGRES_USER: <base64-encoded>
POSTGRES_PASSWORD: <base64-encoded>
```

**생성 방법**:
```bash
echo -n "postgres" | base64
echo -n "your-strong-password" | base64
```

---

## 핵심 교훈

### 기술적 학습

1. **Infrastructure as Code**: Terraform으로 재현 가능한 인프라 구축
2. **환경 분리**: Kustomize Base/Overlay 패턴으로 환경별 설정 관리
3. **데이터베이스 전환**: 파일 기반 → 네트워크 기반 DB의 차이 이해
4. **Kubernetes 스토리지**: PVC, StorageClass, 볼륨 바인딩 모드

### 운영 고려사항

- **보안**: Secret 파일은 `.gitignore`에 추가, 실제 값은 별도 관리
- **확장성**: PostgreSQL 단일 레플리카 → 향후 HA 구성 검토
- **모니터링**: Week 2에서 로깅 및 모니터링 추가 예정

---

## 다음 단계

**Week 2 준비**:
- Docker 이미지 자동 빌드 (GitHub Actions)
- GitOps 저장소 구성
- Argo CD 설치 및 연동

**참고 문서**:
- [Week 1 구현 가이드](./week1-implementation-guide.md)
- [Week 1 요약](./week1-summary.md)
- [트러블슈팅 가이드](./week1-troubleshooting-pvc.md)

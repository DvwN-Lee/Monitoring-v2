---
version: 1.0
last_updated: 2025-12-04
author: Dongju Lee
---

# [Troubleshooting] blog-service DATABASE_PATH 환경변수 문제 해결

## 1. 문제 상황

Phase 1+2 개선사항 배포 후, blog-service Pod가 `CrashLoopBackOff` 상태에 빠져 서비스가 정상적으로 시작되지 않는 문제가 발생했습니다.

```bash
$ kubectl get pods -n titanium-prod
NAME                                   READY   STATUS             RESTARTS   AGE
prod-blog-service-7d9f8b5c4d-k8m2p    0/1     CrashLoopBackOff   5          10m
```

## 2. 증상

### 2.1 Pod 로그 확인

`kubectl logs` 명령으로 확인한 결과, SQLite 관련 오류가 발생했습니다:

```bash
$ kubectl logs -n titanium-prod prod-blog-service-7d9f8b5c4d-k8m2p

Traceback (most recent call last):
  File "/app/blog_service.py", line 45, in <module>
    init_db()
  File "/app/database.py", line 23, in init_db
    conn = sqlite3.connect(DATABASE_PATH)
NameError: name 'DATABASE_PATH' is not defined
```

### 2.2 환경변수 확인

Pod의 환경변수를 확인한 결과, `DATABASE_PATH`가 설정되지 않았습니다:

```bash
$ kubectl describe pod -n titanium-prod prod-blog-service-7d9f8b5c4d-k8m2p | grep -A 20 "Environment:"

Environment:
  USE_POSTGRES:           true
  POSTGRES_HOST:          postgresql-service
  POSTGRES_PORT:          5432
  POSTGRES_DB:            titanium
  POSTGRES_USER:          titanium
  POSTGRES_PASSWORD:      <set to the key 'postgres_password' in secret 'db-secret'>
  # DATABASE_PATH가 누락됨
```

## 3. 원인 분석

### 3.1 근본 원인

ADR-002에서 데이터베이스를 SQLite에서 PostgreSQL로 전환했지만, blog-service 코드에 여전히 SQLite 의존성이 일부 남아있었습니다.

**코드 분석** (`blog-service/blog_service.py:45`):
```python
# PostgreSQL 사용 시에도 SQLite 초기화 코드가 실행됨
if os.getenv("USE_POSTGRES", "false").lower() == "true":
    # PostgreSQL 연결
    pass
else:
    # SQLite 연결 (DATABASE_PATH 필요)
    init_db()  # 이 부분이 실행됨
```

### 3.2 발생 조건

1. ConfigMap에 `USE_POSTGRES=true` 설정
2. 하지만 `DATABASE_PATH` 환경변수는 미설정
3. 애플리케이션 시작 시 SQLite 초기화 로직이 실행되어 에러 발생

## 4. 해결 방법

### 방법 1: ConfigMap에 DATABASE_PATH 추가 (임시 해결)

```yaml
# k8s-manifests/overlays/solid-cloud/kustomization.yaml
configMapGenerator:
  - name: app-config
    behavior: merge
    literals:
      - USE_POSTGRES=true
      - DATABASE_PATH=/tmp/blog.db  # 추가
```

### 방법 2: 코드에서 SQLite 의존성 제거 (권장)

**변경 파일**: `blog-service/blog_service.py`

```python
# Before
import sqlite3

def init_db():
    conn = sqlite3.connect(DATABASE_PATH)
    # ...

# After
# SQLite import 및 초기화 코드 완전 제거
```

**적용 커밋**: `d9a777b` (blog-service 이미지 태그 업데이트)

### 4.1 배포 및 검증

```bash
# 1. Kustomize 빌드 확인
$ kubectl kustomize k8s-manifests/overlays/solid-cloud | grep DATABASE_PATH
          - name: DATABASE_PATH
            value: /tmp/blog.db

# 2. 적용
$ kubectl apply -k k8s-manifests/overlays/solid-cloud

# 3. Pod 재시작 확인
$ kubectl get pods -n titanium-prod -w
NAME                                   READY   STATUS    RESTARTS   AGE
prod-blog-service-7d9f8b5c4d-k8m2p    1/1     Running   0          30s

# 4. 로그 정상 확인
$ kubectl logs -n titanium-prod prod-blog-service-7d9f8b5c4d-k8m2p
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

## 5. 교훈

### 5.1 DB 전환 시 체크리스트

1. **코드에서 이전 DB 드라이버 import 제거**
   - `import sqlite3` → 완전 삭제
   - 조건부 import 대신 완전 제거 권장

2. **환경변수 정리**
   - 사용하지 않는 환경변수도 명시적으로 제거
   - ConfigMap/Secret에서 불필요한 키 삭제

3. **테스트 환경에서 먼저 검증**
   - Local Kubernetes 환경에서 먼저 테스트
   - Production 배포 전 Staging 환경 검증

### 5.2 예방책

1. **Linter 활용**: `ruff` 또는 `pylint`로 미사용 import 자동 감지
2. **CI Pipeline 강화**: 환경변수 의존성 검증 스크립트 추가
3. **코드 리뷰**: DB 전환 PR에 대한 철저한 리뷰

## 관련 문서

- [ADR-002: 데이터베이스로 PostgreSQL 채택](../../02-architecture/adr/002-postgresql-vs-sqlite.md)
- [ADR-010: Phase 1+2 보안 및 성능 개선](../../02-architecture/adr/010-phase1-phase2-improvements.md)
- [운영 가이드](../../04-operations/guides/operations-guide.md)

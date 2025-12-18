---
version: 1.0
last_updated: 2025-12-04
author: Dongju Lee
---

# [Troubleshooting] auth-service INTERNAL_API_SECRET 환경변수 문제 해결

## 1. 문제 상황

Phase 1 보안 강화 배포 후, auth-service와 다른 Service 간의 내부 API 통신에서 인증 실패가 발생했습니다. 사용자 로그인 기능이 정상 작동하지 않았습니다.

```bash
# 로그인 API 호출 시 500 Internal Server Error 발생
$ curl -X POST http://localhost:8080/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"test123"}'

{"detail":"Internal authentication error"}
```

## 2. 증상

### 2.1 auth-service 로그 확인

```bash
$ kubectl logs -n titanium-prod prod-auth-service-6c8d9f7b5d-x4k2m

ERROR:    Missing required environment variable: INTERNAL_API_SECRET
ERROR:    Cannot verify internal API request without secret
INFO:     127.0.0.1:42356 - "POST /internal/verify-user HTTP/1.1" 401 Unauthorized
```

### 2.2 Service 간 통신 실패

API Gateway → auth-service 내부 API 호출 시 401 응답:

```bash
# API Gateway 로그
$ kubectl logs -n titanium-prod prod-api-gateway-5f8c7d6b4a-p9k3n

INFO:     Calling auth-service internal API: /internal/verify-user
ERROR:    Auth service returned 401: {"detail":"Unauthorized"}
ERROR:    Failed to verify user credentials
```

## 3. 원인 분석

### 3.1 근본 원인

Phase 1 보안 강화 작업에서 내부 Service 간 통신에 인증 메커니즘을 추가했으나, 필요한 Secret 설정이 누락되었습니다.

**코드 변경 사항** (`auth-service/auth_service.py`):
```python
# Phase 1에서 추가된 내부 API 인증
INTERNAL_API_SECRET = os.getenv("INTERNAL_API_SECRET")

@app.post("/internal/verify-user")
async def verify_user_internal(request: Request):
    # 내부 API 인증 헤더 검증
    auth_header = request.headers.get("X-Internal-Secret")
    if not INTERNAL_API_SECRET or auth_header != INTERNAL_API_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")
    # ...
```

### 3.2 발생 조건

1. Phase 1 코드 변경: 내부 API에 `X-Internal-Secret` 헤더 검증 추가
2. Kubernetes Secret 미생성: `INTERNAL_API_SECRET` 환경변수 없음
3. API Gateway에서 auth-service 호출 시 401 오류 발생

### 3.3 보안 영향

내부 API 인증 메커니즘은 Service 간 통신 보안을 위해 필수적입니다:
- 외부에서 직접 내부 API 호출 방지
- Service Mesh (Istio) mTLS와 함께 다층 보안 구현

## 4. 해결 방법

### 4.1 Kubernetes Secret 생성

```bash
# 1. Secret 값 생성 (32자 랜덤 문자열)
$ openssl rand -base64 32
mK7vR2xQ9pL8nH5tC3wE6yU4gJ1oB0sA2fD9iN7mV6xZ8

# 2. Secret YAML 작성
$ cat <<EOF > /tmp/internal-api-secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: internal-api-secret
  namespace: titanium-prod
type: Opaque
data:
  # Base64 인코딩된 값
  internal_api_secret: bUs3dlIyeFE5cEw4bkg1dEMzd0U2eVU0Z0oxb0Iwc0EyZkQ5aU43bVY2eFo4Cg==
EOF

# 3. Secret 적용
$ kubectl apply -f /tmp/internal-api-secret.yaml
secret/internal-api-secret created
```

### 4.2 Deployment 환경변수 설정

**Terraform 모듈** (`terraform/modules/kubernetes/auth-service.tf`):
```hcl
resource "kubernetes_deployment" "auth_service" {
  # ...
  spec {
    template {
      spec {
        container {
          env {
            name = "INTERNAL_API_SECRET"
            value_from {
              secret_key_ref {
                name = "internal-api-secret"
                key  = "internal_api_secret"
              }
            }
          }
        }
      }
    }
  }
}
```

또는 **Kustomize 방식**:
```yaml
# k8s-manifests/base/auth-service-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: auth-service-deployment
spec:
  template:
    spec:
      containers:
      - name: auth-service
        env:
        - name: INTERNAL_API_SECRET
          valueFrom:
            secretKeyRef:
              name: internal-api-secret
              key: internal_api_secret
```

### 4.3 배포 및 검증

```bash
# 1. 환경변수 확인
$ kubectl describe pod -n titanium-prod prod-auth-service-6c8d9f7b5d-x4k2m | grep INTERNAL_API_SECRET
      INTERNAL_API_SECRET:      <set to the key 'internal_api_secret' in secret 'internal-api-secret'>

# 2. Pod 재시작 (Secret 주입)
$ kubectl rollout restart deployment -n titanium-prod prod-auth-service-deployment

# 3. 로그인 API 테스트
$ curl -X POST http://localhost:8080/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"test123"}'

{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}

# 4. auth-service 로그 정상 확인
$ kubectl logs -n titanium-prod prod-auth-service-6c8d9f7b5d-x4k2m
INFO:     Internal API request verified successfully
INFO:     127.0.0.1:42356 - "POST /internal/verify-user HTTP/1.1" 200 OK
```

## 5. 교훈

### 5.1 보안 강화 시 체크리스트

1. **환경변수 의존성 명확화**
   - 새로 추가된 환경변수 목록 문서화
   - 필수(required) vs 선택(optional) 구분

2. **Secret 관리 자동화**
   - Terraform에서 Secret 생성까지 자동화
   - External Secrets Operator 도입 검토

3. **단계적 배포 (Canary)**
   - 전체 서비스 동시 배포 대신 1개 Pod만 먼저 배포
   - 정상 작동 확인 후 나머지 Pod 배포

### 5.2 예방책

1. **환경변수 검증 스크립트**
   ```python
   # startup.py
   REQUIRED_VARS = ["INTERNAL_API_SECRET", "POSTGRES_PASSWORD"]
   for var in REQUIRED_VARS:
       if not os.getenv(var):
           raise EnvironmentError(f"Missing required env: {var}")
   ```

2. **Integration Test 추가**
   - Service 간 통신 테스트 케이스 작성
   - CI Pipeline에 통합 테스트 단계 추가

3. **Monitoring Alert 설정**
   - 401 Unauthorized 응답 급증 시 Alert 발송
   - Prometheus Alert: `rate(http_requests_total{status="401"}[5m]) > 0.1`

## 관련 문서

- [ADR-010: Phase 1+2 보안 및 성능 개선](../../02-architecture/adr/010-phase1-phase2-improvements.md)
- [Phase 1 보안 강화 개선사항](../../03-implementation/improvements/phase1-security-improvements.md)
- [Kubernetes Secret 관리 가이드](../../04-operations/guides/operations-guide.md#2-secrets-관리)

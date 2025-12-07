# 최종 코드 리뷰 보고서

**작성일:** 2025-12-05
**분석 도구:** 설계 전문가 병렬 분석
**분석 범위:** API Gateway, Auth Service, User Service, Blog Service, Terraform

---

## Executive Summary

총 **18개**의 이슈가 발견되었습니다:
- **CRITICAL**: 4개 (Terraform 보안, Database 설정)
- **HIGH**: 4개 (CORS, Token 파싱, Credential 로깅)
- **MEDIUM**: 8개 (코드 품질, Best practices)
- **LOW**: 2개 (로깅 스타일, 설정 관리)

---

## CRITICAL Issues (즉시 조치 필요)

### 1. Terraform: terraform.tfvars에 실제 API Key 하드코딩
**파일:** `terraform/environments/solid-cloud/terraform.tfvars:3-4,12`
**심각도:** CRITICAL

**문제:**
```hcl
cloudstack_api_key    = "U6fgYIJ3_dvD5TmfGyDYLERBo4B62BNpt4xxCQj-CRtpzsC5rCjFGILNfOk9jBVrhRpuSzfdL_scziWXd6GSFA"
cloudstack_secret_key = "VlvPIE_eNJ5ycq2JFWnNhiTDHj40TPiQnG_mPbwEOMpVXuo_YaCNDw_HPMI7XAbLpF_oQwMA_qz1tLGQd8eZ4w"
postgres_password     = "TempPassword123!"
```

**위험:** CloudStack 전체 인프라에 대한 무단 접근 가능. 파일이 유출될 경우 VM 생성/삭제, Network 설정 등 모든 인프라 제어권 탈취 가능.

**권장 조치:**
1. 환경 변수 사용: `export TF_VAR_cloudstack_api_key="..."`
2. 현재 API Key 즉시 교체 (Rotate)
3. `.gitignore`에 `terraform.tfvars` 등록 확인 (현재: 등록됨)
4. CI/CD에서는 Secret Manager 사용

---

### 2. Terraform: terraform.tfstate에 Secret 평문 노출
**파일:** `terraform/environments/solid-cloud/terraform.tfstate:395,1501-1505`
**심각도:** CRITICAL

**문제:**
State 파일에 다음 Secret이 평문으로 저장됨:
- `POSTGRES_PASSWORD`: "TempPassword123!"
- `INTERNAL_API_SECRET`: "api-secret-key"
- `JWT_SECRET_KEY`: "jwt-signing-key"
- `REDIS_PASSWORD`: "redis-password"

**위험:** State 파일 유출 시 Database, API, Cache 모든 서비스 자격 증명 노출.

**권장 조치:**
1. Remote Backend 사용 (S3 + Server-side encryption)
2. Terraform Cloud 사용 (State 자동 암호화)
3. State 파일 접근 권한 강화
4. `.gitignore`에 `*.tfstate` 등록 확인 (현재: 등록됨)

---

### 3. Terraform: Firewall 0.0.0.0/0 허용
**파일:** `terraform/modules/instance/main.tf:107-111`
**심각도:** CRITICAL

**문제:**
```hcl
rule {
  protocol  = "tcp"
  cidr_list = ["0.0.0.0/0"]
  ports     = ["22", "6443", "80"]
}
```

**위험:** SSH(22), Kubernetes API Server(6443)가 전 세계 모든 IP에 공개됨. Brute-force 공격, 무단 접근 위험.

**권장 조치:**
1. SSH(22): Bastion Host 또는 특정 IP 대역으로 제한
2. K8s API(6443): VPN CIDR 또는 관리자 IP로 제한
3. HTTP(80): Cloudflare 또는 CDN IP 대역으로 제한 가능

**예시:**
```hcl
rule {
  protocol  = "tcp"
  cidr_list = ["203.0.113.0/24"]  # 관리자 IP 대역
  ports     = ["22", "6443"]
}
```

---

### 4. Blog Service: POSTGRES_PASSWORD 빈 문자열 기본값
**파일:** `blog-service/app/config.py:25`
**심각도:** CRITICAL
**상태:** 수정 완료

**문제:**
```python
'password': os.getenv('POSTGRES_PASSWORD', ''),
```

**위험:** 환경 변수 미설정 시 빈 Password로 Database 연결 시도. 인증 우회 가능.

**수정 내용:**
User Service와 동일하게 빈 값일 경우 `ValueError` 발생시키도록 수정.

---

## HIGH Priority Issues (단기 조치)

### 5. Auth Service: CORS Wildcard + Credentials
**파일:** `auth-service/main.py:55-62`
**심각도:** HIGH

**문제:**
```python
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**위험:**
- `allow_origins=["*"]` + `allow_credentials=True` 조합은 CSRF 공격 취약
- 모든 Method/Header 허용으로 보안 범위 확대

**권장 조치:**
```python
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # 명시적 도메인 목록
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],  # 필요한 Method만
    allow_headers=["Content-Type", "Authorization"],   # 필요한 Header만
)
```

---

### 6. Auth Service: Bearer Token 파싱 미검증
**파일:** `auth-service/main.py:148`
**심각도:** HIGH
**상태:** 수정 완료

**문제:**
```python
token = auth_header.split(' ')[1]  # IndexError 가능성
```

**위험:** `Authorization: Bearer` 형식이 아닐 경우 IndexError 발생.

**수정 내용:**
Split 결과 길이 검증 추가.

---

### 7. Cache Services: Redis URL Logging 시 Credential 노출 위험
**파일:** `user-service/cache_service.py:14`, `blog-service/app/cache.py:15`
**심각도:** HIGH
**상태:** 수정 완료

**문제:**
```python
logger.info(f"Cache service initialized and connected to Redis at {config.REDIS_URL}")
```

**위험:** Redis URL에 password가 포함된 경우 (예: `redis://:password@host:6379`) 로그에 credential 노출.

**수정 내용:**
URL에서 password 마스킹 후 로깅.

---

### 8. Terraform: 취약한 기본값 설정
**파일:** `terraform/environments/solid-cloud/variables.tf:88-107`
**심각도:** HIGH

**문제:**
```hcl
variable "jwt_secret_key" {
  default = "jwt-signing-key"  # 예측 가능한 취약한 기본값
}

variable "internal_api_secret" {
  default = "api-secret-key"
}

variable "redis_password" {
  default = "redis-password"
}
```

**위험:** 사용자가 값을 지정하지 않으면 예측 가능한 취약한 Password가 사용됨.

**권장 조치:**
```hcl
variable "jwt_secret_key" {
  description = "JWT signing secret key"
  type        = string
  sensitive   = true
  # default 제거하여 필수 입력으로 변경
}
```

---

## MEDIUM Priority Issues

| 번호 | 이슈 | 파일 | 라인 | 설명 |
|------|------|------|------|------|
| 9 | X-Forwarded-Proto "http" 하드코딩 | `api-gateway/main.go` | 121,141,161 | HTTPS 환경에서 실제 Protocol 전파 안 됨 |
| 10 | json.Encode/w.Write 오류 무시 | `api-gateway/main.go` | 103, 213 | Error 반환값 미처리 |
| 11 | Uvicorn Timeout 미설정 | `auth-service/main.py` | 174 | 서버 Timeout 설정 없음 |
| 12 | Password 복잡성 검증 없음 | `user-service/user_service.py` | 22-24 | 취약한 Password 등록 가능 |
| 13 | Blog CORS wildcard+credentials | `blog-service/blog_service.py` | 50-57 | Auth Service와 동일한 CORS 이슈 |
| 14 | Import 파일 중간 위치 | `auth-service/main.py` | 52 | PEP 8 스타일 위반 |
| 15 | Import 파일 중간 위치 | `blog-service/blog_service.py` | 47 | PEP 8 스타일 위반 |
| 16 | SCAN_ITER 성능 이슈 | `blog-service/app/cache.py` | 111-124 | 대량 Key 수집 시 Memory 이슈 |

---

## LOW Priority Issues

| 번호 | 이슈 | 파일 | 라인 | 설명 |
|------|------|------|------|------|
| 17 | 로그 메시지 이모지 사용 | `auth-service/main.py` | 36, 173 | 로그 파싱 일관성 저해 |
| 18 | Cache TTL 하드코딩 | 여러 파일 | - | Configuration 파일로 관리 권장 |

---

## 긍정적 발견 사항

### 보안
- **SQL Injection 방어:** 모든 Database Query에서 Parameterized Query 사용
- **Password Hashing:** OWASP 2023 권장 PBKDF2-SHA256 600,000 iterations 적용
- **Rate Limiting:** Auth Service에 slowapi를 통한 Rate Limiting 구현
- **Input Validation:** Pydantic 모델을 통한 Request Validation

### Infrastructure
- **Sensitive 변수 설정:** cloudstack_api_key, secret_key에 `sensitive=true` 설정
- **`.gitignore` 설정:** .tfvars, .tfstate, .env 파일 적절히 등록됨
- **Secret 필수 검증:** User Service에서 POSTGRES_PASSWORD 필수 체크 구현

### Architecture
- **Async Architecture:** asyncio 기반 Non-blocking I/O 패턴 적용
- **Connection Pooling:** PostgreSQL asyncpg pool 사용
- **Graceful Shutdown:** lifespan context manager를 통한 Resource Cleanup
- **Prometheus Metrics:** 표준화된 Metrics 노출

---

## 수정 완료 항목

### CRITICAL/HIGH Priority 수정 완료

| 항목 | 파일 | 내용 |
|------|------|------|
| POSTGRES_PASSWORD 빈 기본값 | `blog-service/app/config.py` | ValueError 발생 로직 추가 |
| Bearer Token 파싱 미검증 | `auth-service/main.py` | Split 결과 길이 검증 추가 |
| Redis URL Credential 로깅 | `user-service/cache_service.py` | URL 마스킹 후 로깅 |
| Redis URL Credential 로깅 | `blog-service/app/cache.py` | URL 마스킹 후 로깅 |

### MEDIUM Priority 수정 완료

| 항목 | 파일 | 내용 |
|------|------|------|
| X-Forwarded-Proto 하드코딩 | `api-gateway/main.go:121,146,171` | TLS/Header 기반 동적 Protocol 설정 |
| Error Handling 누락 | `api-gateway/main.go:103,230` | w.Write 및 json.Encode Error 로깅 추가 |
| Import 위치 (PEP 8) | `auth-service/main.py:2,54` | `import os`를 파일 상단으로 이동 |
| Import 위치 (PEP 8) | `blog-service/blog_service.py:9,11-12` | CORS, Prometheus import를 상단으로 이동 |
| SCAN_ITER Memory 이슈 | `blog-service/app/cache.py:119-140` | Batch 처리로 변경 (100개 단위) |

### LOW Priority 수정 완료

| 항목 | 파일 | 내용 |
|------|------|------|
| Log Emoji 사용 | `auth-service/main.py:37,177` | "✅" Emoji 제거 |
| Log Emoji 사용 | `blog-service/blog_service.py:39,338` | "✅" Emoji 제거 |

---

## Phase 4: Operations & Hardening 완료 항목 (2025-12-05)

### CRITICAL Priority 수정 완료

| 항목 | 파일 | 내용 |
|------|------|------|
| Terraform API Key/Secret 환경 변수화 | `terraform/environments/solid-cloud/terraform.tfvars` | 모든 민감 정보 제거, 환경 변수 방식으로 전환 |
| Terraform API Key/Secret 환경 변수화 | `terraform/environments/solid-cloud/.env.example` | 환경 변수 템플릿 생성 (TF_VAR_*) |
| Terraform API Key/Secret 환경 변수화 | `terraform/environments/solid-cloud/SECRET_MANAGEMENT.md` | 보안 강화 사항 및 CloudStack API Key 교체 절차 문서화 |
| Terraform Variables 기본값 제거 | `terraform/environments/solid-cloud/variables.tf` | jwt_secret_key, redis_password, internal_api_secret default 제거 |

### HIGH Priority 수정 완료

| 항목 | 파일 | 내용 |
|------|------|------|
| Firewall CIDR 제한 | `terraform/modules/instance/main.tf:103-133` | SSH, K8s API, HTTP를 개별 Firewall Rule로 분리 |
| Firewall CIDR 제한 | `terraform/modules/instance/variables.tf:38-55` | allowed_ssh_cidrs, allowed_k8s_cidrs, allowed_http_cidrs 변수 추가 |
| Firewall CIDR 제한 | `terraform/environments/solid-cloud/variables.tf:107-124` | Firewall CIDR 변수 정의 및 보안 경고 추가 |
| Firewall CIDR 제한 | `terraform/environments/solid-cloud/main.tf:63-66` | Instance Module에 Firewall CIDR 변수 전달 |
| Firewall CIDR 제한 | `terraform/environments/solid-cloud/.env.example:29-39` | Firewall CIDR 설정 예시 및 경고 추가 |
| CORS 도메인 명시 설정 | `k8s-manifests/base/configmap.yaml:29-31` | CORS_ALLOWED_ORIGINS → ALLOWED_ORIGINS 변경, localhost 기본값 |
| CORS 도메인 명시 설정 | `k8s-manifests/overlays/solid-cloud/configmap-patch.yaml:34-38` | Production에서 "*" 제거, 명시적 도메인 (https://titanium.example.com) 설정 |

### MEDIUM Priority 수정 완료

| 항목 | 파일 | 내용 |
|------|------|------|
| Password 복잡성 검증 (NIST SP 800-63B) | `user-service/user_service.py:21-57` | 최소 12자, 흔한 비밀번호 차단, Pydantic field_validator 추가 |

---

## 향후 권장 사항 (수동 작업 필요)

### CloudStack API Key 교체 (즉시)
**현황:** 기존 API Key가 Git 이력에 노출되어 유출된 것으로 간주
**조치:**
1. CloudStack Console에서 새 API Key Pair 생성
2. 기존 Key 폐기 (Revoke)
3. `.env` 파일에 새 Key 입력
4. `source .env && terraform plan` 실행하여 검증

### Terraform Remote Backend 이전 (단기)
**현황:** terraform.tfstate가 로컬에 저장되어 Secret이 평문 노출
**조치:**
- S3 + DynamoDB (State Locking) 또는 Terraform Cloud 사용
- S3 Bucket에 Server-side Encryption (SSE) 활성화
- State 파일 암호화

### Production 환경 설정 (단기)
**현황:** ConfigMap에 설정된 도메인이 예시 값
**조치:**
1. `k8s-manifests/overlays/solid-cloud/configmap-patch.yaml`에서 실제 Production 도메인으로 변경
2. Firewall CIDR 설정을 실제 관리자 IP/VPN 대역으로 제한

### 중기 조치 (3개월 이내)
**현황:** 현재는 환경 변수 방식으로 Secret 관리 중
**조치:**
- HashiCorp Vault 또는 SOPS 도입 검토 (팀 협업 환경에 적합)
- Cache TTL을 환경 변수로 설정 가능하도록 Configuration 개선

---

## 전체 작업 요약

### Phase 1-3: Code Quality (완료)
- CRITICAL/HIGH/MEDIUM/LOW 우선순위 이슈 총 11개 수정
- Dead Code 제거, Error Handling 강화, PEP 8 준수, Performance 최적화

### Phase 4: Operations & Hardening (완료)
- Infrastructure 보안 강화: API Key 환경 변수화, Firewall CIDR 제한
- Application 보안 강화: CORS 도메인 명시, Password 검증 (NIST)
- 문서화: Secret 관리 가이드, CloudStack API Key 교체 절차

### 수동 작업 필요
- CloudStack API Key 교체 (기존 Key 유출로 간주)
- Terraform Remote Backend 이전 (S3 + Encryption)
- Production ConfigMap 도메인 설정

---

## 참고 문서

- OWASP Top 10: https://owasp.org/www-project-top-ten/
- OWASP Password Storage Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html
- NIST SP 800-63B (Password Guidelines): https://pages.nist.gov/800-63-3/sp800-63b.html
- Terraform Remote State: https://developer.hashicorp.com/terraform/language/state/remote
- CORS Best Practices: https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS
- CloudStack API Documentation: https://cloudstack.apache.org/api.html

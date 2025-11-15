---
version: 1.0
last_updated: 2025-11-15
author: Dongju Lee
---

# API Gateway 라우팅 오류 문제 해결

## 문제 현상

### 에러 메시지

#### 404 Not Found
```
HTTP 404 Not Found
{"error": "Not Found"}
```

로그:
```
INFO: 127.0.0.6:35973 - "GET /api/posts HTTP/1.1" 404 Not Found
INFO: 127.0.0.6:39903 - "GET /api/posts?category=infrastructure HTTP/1.1" 404 Not Found
```

#### 405 Method Not Allowed
```
HTTP 405 Method Not Allowed
{"error": "Method Not Allowed"}
```

로그:
```
INFO: 127.0.0.7:41234 - "PATCH /api/posts/5 HTTP/1.1" 405 Method Not Allowed
```

### 발생 상황
- 프론트엔드에서 API 호출 시 404 또는 405 에러 발생
- 브라우저 콘솔에서 에러 확인 가능
- 백엔드 서비스 로그에는 요청이 도달하지 않음
- API Gateway 또는 Istio Ingress Gateway 로그에만 기록됨

### 영향 범위
- 사용자 인증 (로그인, 회원가입) 실패
- 게시글 목록 로딩 실패
- 게시글 수정/삭제 기능 작동 안 함
- 전체적인 애플리케이션 기능 장애

## 원인 분석

### 근본 원인

마이크로서비스 아키텍처에서 클라이언트가 사용하는 API 경로와 API Gateway가 처리하는 경로가 일치하지 않아 발생하는 문제입니다.

### 시나리오별 분석

#### 시나리오 1: 클라이언트 경로 불일치 (404)

**문제 상황**:
- 클라이언트: `GET /api/posts`
- API Gateway 라우팅: `/blog/api/*` → blog-service
- 결과: 404 Not Found (경로 매칭 실패)

**아키텍처 변경 이력**:
```
[초기 설계]
프론트엔드 → /api/* → blog-service

[변경 후]
프론트엔드 → /api/* → ??? (매칭 실패)
                      ↓
                /blog/api/* → blog-service
```

#### 시나리오 2: 라우팅 규칙 누락 (404)

**문제 상황**:
API Gateway나 VirtualService에 특정 경로에 대한 라우팅 규칙이 누락됨

예시:
```yaml
# VirtualService에 /blog/api/posts는 정의되어 있음
# 하지만 /api/posts는 정의되지 않음
```

#### 시나리오 3: HTTP 메서드 불일치 (405)

**문제 상황**:
- 클라이언트: `PATCH /api/posts/5`
- API Gateway 핸들러: `PATCH /blog/api/posts/5` 만 처리
- 결과: 405 Method Not Allowed

**예시 코드**:
```go
// 잘못된 경로 등록
mux.HandleFunc("/blog/api/posts/{id}", handleUpdatePost)  // PATCH 지원

// 클라이언트 요청
PATCH /api/posts/5  // 매칭 안 됨
```

## 해결 방법

### 해결 방안 1: 클라이언트 경로 수정 (권장)

백엔드 라우팅 구조에 맞게 프론트엔드 API 경로를 통일합니다.

#### JavaScript/TypeScript 수정

**수정 전**:
```javascript
// 로그인
fetch('/api/login', { method: 'POST', ... })

// 게시글 목록
fetch('/api/posts')

// 게시글 수정
fetch(`/api/posts/${id}`, { method: 'PATCH', ... })
```

**수정 후**:
```javascript
// 로그인
fetch('/blog/api/login', { method: 'POST', ... })

// 게시글 목록
fetch('/blog/api/posts')

// 게시글 수정
fetch(`/blog/api/posts/${id}`, { method: 'PATCH', ... })
```

#### 전체 엔드포인트 변경 목록

| 기능 | 기존 경로 | 수정된 경로 |
|------|-----------|-------------|
| 로그인 | `/api/login` | `/blog/api/login` |
| 회원가입 | `/api/register` | `/blog/api/register` |
| 카테고리 조회 | `/api/categories` | `/blog/api/categories` |
| 게시물 목록 | `/api/posts` | `/blog/api/posts` |
| 게시물 상세 | `/api/posts/{id}` | `/blog/api/posts/{id}` |
| 게시물 생성 | `POST /api/posts` | `POST /blog/api/posts` |
| 게시물 수정 | `PATCH /api/posts/{id}` | `PATCH /blog/api/posts/{id}` |
| 게시물 삭제 | `DELETE /api/posts/{id}` | `DELETE /blog/api/posts/{id}` |

### 해결 방안 2: API Gateway 라우팅 추가

클라이언트를 수정할 수 없는 경우, API Gateway에 추가 라우팅 규칙을 등록합니다.

#### Go API Gateway (main.go)

```go
mux := http.NewServeMux()

// 기존 경로
mux.Handle("/blog/api/", http.StripPrefix("/blog/api", authProxy))

// 호환성을 위한 추가 경로
mux.Handle("/api/", http.StripPrefix("/api", authProxy))
```

#### Istio VirtualService

```yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: blog-virtualservice
  namespace: titanium-prod
spec:
  hosts:
  - "*"
  gateways:
  - titanium-gateway
  http:
  # 새로운 경로 추가
  - match:
    - uri:
        prefix: /api/
    route:
    - destination:
        host: api-gateway
        port:
          number: 8000
  # 기존 경로
  - match:
    - uri:
        prefix: /blog/api/
    route:
    - destination:
        host: api-gateway
        port:
          number: 8000
```

### 해결 방안 3: Path Rewriting

Istio VirtualService에서 경로 변환 규칙 적용:

```yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: blog-virtualservice
  namespace: titanium-prod
spec:
  hosts:
  - "*"
  gateways:
  - titanium-gateway
  http:
  - match:
    - uri:
        prefix: /api/
    rewrite:
      uri: /blog/api/
    route:
    - destination:
        host: blog-service
        port:
          number: 8005
```

## 검증 방법

### 1. 로컬 테스트

```bash
# 프론트엔드 서버 시작
cd blog-service
python3 blog_service.py

# 브라우저에서 접속
# http://localhost:8005/blog/

# 개발자 도구 > 네트워크 탭에서 API 호출 확인
# 모든 요청이 200 OK 응답을 받아야 함
```

### 2. 클러스터 테스트

```bash
# Istio Ingress Gateway를 통한 요청
export GATEWAY_URL=$(kubectl get svc istio-ingressgateway -n istio-system -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

# 게시글 목록 조회
curl -v http://$GATEWAY_URL/blog/api/posts

# 예상: HTTP 200 OK
# {"posts": [...]}

# 로그인 테스트
curl -X POST http://$GATEWAY_URL/blog/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"testpass"}'

# 예상: HTTP 200 OK 또는 401 Unauthorized
# 404나 405가 발생하면 안 됨
```

### 3. 로그 확인

```bash
# API Gateway 로그
kubectl logs -n titanium-prod deployment/api-gateway-deployment --tail=50

# 성공적인 요청 예시:
# INFO: "POST /blog/api/login HTTP/1.1" 200 OK
# INFO: "GET /blog/api/posts HTTP/1.1" 200 OK

# blog-service 로그
kubectl logs -n titanium-prod deployment/blog-service-deployment --tail=50

# 요청이 백엔드까지 도달했는지 확인
```

### 4. Istio 메트릭 확인

```bash
# Prometheus 쿼리
kubectl port-forward -n monitoring svc/prometheus-kube-prometheus-prometheus 9090:9090

# 브라우저에서 http://localhost:9090
# 쿼리: istio_requests_total{response_code="404"}
# 결과: 404 에러가 감소해야 함
```

## 예방 방법

### 1. API 경로 문서화

`docs/api-specification.md` 파일 생성:

```markdown
# API 경로 명세

## Base URL
- 로컬: http://localhost:8005
- 클러스터: http://istio-ingressgateway.istio-system.svc.cluster.local

## 엔드포인트

### 인증
- POST /blog/api/login
- POST /blog/api/register

### 게시글
- GET /blog/api/posts
- GET /blog/api/posts/{id}
- POST /blog/api/posts
- PATCH /blog/api/posts/{id}
- DELETE /blog/api/posts/{id}

### 카테고리
- GET /blog/api/categories
```

### 2. API Gateway 통합 테스트

```go
// api-gateway/main_test.go
func TestRouting(t *testing.T) {
    tests := []struct {
        method string
        path   string
        expectedCode int
    }{
        {"GET", "/blog/api/posts", 200},
        {"POST", "/blog/api/login", 200},
        {"PATCH", "/blog/api/posts/1", 200},
        {"DELETE", "/blog/api/posts/1", 200},
    }

    for _, tt := range tests {
        req := httptest.NewRequest(tt.method, tt.path, nil)
        rec := httptest.NewRecorder()

        handler.ServeHTTP(rec, req)

        if rec.Code != tt.expectedCode {
            t.Errorf("%s %s: expected %d, got %d",
                tt.method, tt.path, tt.expectedCode, rec.Code)
        }
    }
}
```

### 3. CI/CD 파이프라인에 E2E 테스트 추가

```yaml
# .github/workflows/ci.yml
- name: Run E2E API Tests
  run: |
    kubectl port-forward -n istio-system svc/istio-ingressgateway 8080:80 &
    sleep 5
    npm run test:e2e
```

### 4. OpenAPI 스펙 활용

OpenAPI/Swagger를 사용하여 API 계약 정의:

```yaml
# openapi.yaml
openapi: 3.0.0
info:
  title: Blog Service API
  version: 1.0.0
servers:
  - url: /blog/api
paths:
  /posts:
    get:
      summary: 게시글 목록 조회
      responses:
        '200':
          description: 성공
    post:
      summary: 게시글 생성
      responses:
        '201':
          description: 생성 성공
```

## 관련 문서

- [시스템 아키텍처 - 전체 시스템](../../02-architecture/architecture.md#2-전체-시스템-아키텍처)
- [시스템 아키텍처 - 마이크로서비스 구조](../../02-architecture/architecture.md#3-마이크로서비스-구조)
- [운영 가이드](../../04-operations/guides/operations-guide.md)
- [Istio와 Go Reverse Proxy 라우팅 충돌](troubleshooting-istio-routing-with-go-reverseproxy.md)
- [서비스 엔드포인트 누락](../kubernetes/troubleshooting-service-endpoint-missing.md)


## 참고 사항

### 경로 설계 Best Practice

1. **일관성**: 모든 서비스가 동일한 경로 규칙 사용
2. **명확성**: `/api/v1/`, `/blog/api/` 등 명확한 prefix 사용
3. **문서화**: OpenAPI, Swagger 등으로 계약 명시

### 디버깅 팁

```bash
# VirtualService 확인
kubectl get virtualservice -n titanium-prod -o yaml

# API Gateway 핸들러 확인
kubectl logs -n titanium-prod <api-gateway-pod> | grep "Registered handler"

# Istio 라우팅 설정 확인
istioctl proxy-config routes <pod-name> -n titanium-prod
```

### 자주 발생하는 실수

1. **StripPrefix 누락**
   ```go
   // Wrong: prefix가 백엔드로 전달됨
   mux.Handle("/blog/api/", authProxy)

   // Correct
   mux.Handle("/blog/api/", http.StripPrefix("/blog/api", authProxy))
   ```

2. **Trailing Slash 불일치**
   ```go
   // /blog/api 와 /blog/api/ 는 다름
   mux.Handle("/blog/api/", handler)  // /blog/api/login 매칭
   mux.Handle("/blog/api", handler)   // /blog/api 만 매칭
   ```

3. **대소문자 구분**
   ```
   /API/posts ≠ /api/posts
   ```

## 관련 커밋
- `c06da66`: fix: PATCH 엔드포인트 경로에 /blog prefix 추가
- `e48ec98`: fix: 프론트엔드 API 경로를 /blog/api로 수정
- `b092787`: fix: /blog/api/ 경로를 핸들러에 등록하여 라우팅 문제 해결

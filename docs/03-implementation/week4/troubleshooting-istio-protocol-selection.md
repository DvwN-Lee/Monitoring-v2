# Istio 프로토콜 선택 문제 해결

## 문제 현상

### 간헐적 연결 실패
```
HTTP 503 Service Unavailable (간헐적)
upstream connect error or disconnect/reset before headers
```

### 발생 상황
- Istio 서비스 메시 도입 후 서비스 간 통신이 간헐적으로 실패
- mTLS가 일부 요청에만 적용됨 (일관성 없음)
- Istio Ingress Gateway를 통한 접근이 불안정함
- VirtualService, DestinationRule 설정은 정상으로 보임

### Envoy 로그
```bash
$ kubectl logs <pod> -c istio-proxy
[warning] Protocol detection timeout for 10.244.1.15:8001
[warning] Unable to detect protocol, using TCP
```

### 영향 범위
- L7 라우팅 기능 작동 안 함 (경로 기반 라우팅, 헤더 기반 라우팅)
- mTLS 인증서 검증 실패
- 메트릭 수집 누락 (HTTP 메트릭이 TCP로 집계됨)
- 트래픽 분할, Canary 배포 등 고급 기능 사용 불가

## 원인 분석

### 근본 원인

Kubernetes Service 정의에서 포트 이름(port name)을 명시하지 않거나 프로토콜을 명확히 지정하지 않으면, Istio가 트래픽을 L4(TCP)로 처리하여 L7(HTTP/gRPC) 기능을 사용할 수 없습니다.

### 기술적 배경

#### Istio 프로토콜 선택 메커니즘

Istio는 다음 순서로 트래픽 프로토콜을 결정합니다:

1. **포트 이름**: Service의 `port.name`에서 프로토콜 접두사 확인
2. **자동 감지**: 포트 이름이 없으면 연결의 첫 몇 바이트를 검사 (프로토콜 스니핑)
3. **기본값**: 감지 실패 시 TCP로 처리

#### 지원되는 프로토콜 접두사

| 접두사 | 프로토콜 | 예시 |
|--------|----------|------|
| `http` | HTTP/1.x | `http`, `http-web` |
| `http2` | HTTP/2 | `http2`, `http2-grpc` |
| `https` | HTTPS | `https`, `https-web` |
| `tcp` | TCP | `tcp`, `tcp-database` |
| `grpc` | gRPC | `grpc`, `grpc-svc` |
| `mongo` | MongoDB | `mongo` |
| `redis` | Redis | `redis` |
| `mysql` | MySQL | `mysql` |

#### 문제가 되는 Service 정의

**문제 있는 예시**:
```yaml
apiVersion: v1
kind: Service
metadata:
  name: blog-service
spec:
  selector:
    app: blog-service
  ports:
  - protocol: TCP      # ← 포트 이름 없음
    port: 8005
    targetPort: http
```

**문제점**:
1. `name` 필드가 누락됨
2. Istio가 프로토콜을 자동 감지 시도
3. 감지 실패 시 TCP로 처리
4. L7 기능 사용 불가

#### Istio가 TCP로 처리하면 발생하는 문제

1. **라우팅**:
   - 경로 기반 라우팅 불가 (`/api/users`, `/api/posts` 구분 안 됨)
   - 헤더 기반 라우팅 불가
   - 쿼리 파라미터 라우팅 불가

2. **보안**:
   - mTLS는 작동하지만 HTTP 헤더 검증 불가
   - JWT 인증 불가
   - Authorization 정책 제한적

3. **관측성**:
   - HTTP 상태 코드 메트릭 수집 안 됨
   - 요청/응답 헤더 로깅 불가
   - HTTP 경로별 메트릭 구분 안 됨

4. **트래픽 관리**:
   - Canary 배포의 헤더 기반 분할 불가
   - Retry, Timeout 설정 제한적
   - Fault injection 제한적

## 해결 방법

### 해결 방안 1: 포트 이름 추가 (권장)

모든 Kubernetes Service에 명시적인 프로토콜 접두사를 포함한 포트 이름을 추가합니다.

#### 수정 전
```yaml
apiVersion: v1
kind: Service
metadata:
  name: blog-service
  namespace: titanium-prod
spec:
  selector:
    app: blog-service
  ports:
  - protocol: TCP
    port: 8005
    targetPort: http
```

#### 수정 후
```yaml
apiVersion: v1
kind: Service
metadata:
  name: blog-service
  namespace: titanium-prod
spec:
  selector:
    app: blog-service
  ports:
  - name: http          # ← 프로토콜 명시
    protocol: TCP
    port: 8005
    targetPort: http
```

### 해결 방안 2: 모든 서비스에 적용

**user-service-service.yaml**:
```yaml
apiVersion: v1
kind: Service
metadata:
  name: user-service
  namespace: titanium-prod
spec:
  selector:
    app: user-service
  ports:
  - name: http
    protocol: TCP
    port: 8001
    targetPort: http
```

**auth-service-service.yaml**:
```yaml
apiVersion: v1
kind: Service
metadata:
  name: auth-service
  namespace: titanium-prod
spec:
  selector:
    app: auth-service
  ports:
  - name: http
    protocol: TCP
    port: 8002
    targetPort: http
```

**api-gateway-service.yaml**:
```yaml
apiVersion: v1
kind: Service
metadata:
  name: api-gateway
  namespace: titanium-prod
spec:
  selector:
    app: api-gateway
  ports:
  - name: http
    protocol: TCP
    port: 8000
    targetPort: http
```

### 해결 방안 3: 여러 포트를 사용하는 서비스

하나의 서비스에 여러 프로토콜이 있는 경우:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: multi-protocol-service
  namespace: titanium-prod
spec:
  selector:
    app: multi-protocol-service
  ports:
  - name: http-web      # HTTP 웹 트래픽
    protocol: TCP
    port: 8080
    targetPort: 8080
  - name: grpc-api      # gRPC API
    protocol: TCP
    port: 9090
    targetPort: 9090
  - name: tcp-metrics   # Prometheus 메트릭 (HTTP)
    protocol: TCP
    port: 9091
    targetPort: 9091
```

### 해결 방안 4: Kustomize 패치로 일괄 적용

```yaml
# kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - ../../base

patches:
  # 모든 Service의 첫 번째 포트에 name: http 추가
  - patch: |-
      - op: add
        path: /spec/ports/0/name
        value: http
    target:
      kind: Service
```

## 검증 방법

### 1. Service 정의 확인

```bash
# 모든 Service의 포트 이름 확인
kubectl get svc -n titanium-prod -o json | \
  jq '.items[] | {name: .metadata.name, ports: .spec.ports}'

# 예상 출력:
# {
#   "name": "blog-service",
#   "ports": [
#     {
#       "name": "http",
#       "port": 8005,
#       "protocol": "TCP",
#       "targetPort": "http"
#     }
#   ]
# }
```

### 2. Istio 프로토콜 감지 확인

```bash
# Envoy 설정 확인
istioctl proxy-config listener <pod-name> -n titanium-prod -o json | \
  grep -A 5 "blog-service"

# HTTP 프로토콜로 감지되었는지 확인
# "name": "envoy.filters.network.http_connection_manager"
```

### 3. Envoy 로그 확인

```bash
# 프로토콜 감지 경고 확인
kubectl logs <pod> -n titanium-prod -c istio-proxy | grep -i protocol

# 경고가 없어야 함:
# ✓ (경고 없음)
# ✗ "Protocol detection timeout"
```

### 4. L7 메트릭 확인

```bash
# Prometheus 쿼리
kubectl port-forward -n monitoring svc/prometheus-kube-prometheus-prometheus 9090:9090

# 브라우저: http://localhost:9090
# 쿼리: istio_requests_total{destination_service="blog-service.titanium-prod.svc.cluster.local"}

# response_code 레이블이 있어야 함 (L7 메트릭 증거)
```

### 5. VirtualService 테스트

```bash
# 경로 기반 라우팅 테스트
curl -v http://istio-ingressgateway/blog/

# 예상: HTTP 200 OK (L7 라우팅 작동)
# 실패: HTTP 503 (L4로 처리됨)
```

### 6. mTLS 상태 확인

```bash
# mTLS 상태 확인
istioctl authn tls-check <pod-name> -n titanium-prod

# 예상 출력:
# HOST:PORT                           STATUS     SERVER     CLIENT     AUTHN POLICY
# blog-service.titanium-prod.svc...   OK         STRICT     ISTIO_MUTUAL     default/
```

## 예방 방법

### 1. Service 템플릿 작성

모든 새로운 서비스에 사용할 표준 템플릿:

```yaml
# templates/service-template.yaml
apiVersion: v1
kind: Service
metadata:
  name: <SERVICE_NAME>
  namespace: titanium-prod
  labels:
    app: <SERVICE_NAME>
spec:
  selector:
    app: <SERVICE_NAME>
  ports:
  - name: http          # ← 필수: 프로토콜 명시
    protocol: TCP
    port: <PORT>
    targetPort: http
```

### 2. Pre-commit Hook

Git commit 전 Service 검증:

```bash
#!/bin/bash
# .git/hooks/pre-commit

echo "Checking Kubernetes Service definitions..."

for file in $(git diff --cached --name-only | grep -E '.*-service\.yaml$'); do
  # 포트 이름 확인
  if ! grep -q "name: http" "$file"; then
    echo "ERROR: $file is missing 'name: http' in ports definition"
    echo "Please add 'name: http' to ensure Istio protocol detection"
    exit 1
  fi
done

echo "✓ All Service definitions are valid"
```

### 3. CI/CD 검증

```yaml
# .github/workflows/validate.yml
name: Validate Kubernetes Manifests

on: [push, pull_request]

jobs:
  validate-services:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Validate Service Ports
        run: |
          for file in k8s-manifests/**/*-service.yaml; do
            echo "Checking $file..."

            # 포트 이름 확인
            if ! grep -q "name: http" "$file"; then
              echo "❌ ERROR: $file missing port name"
              exit 1
            fi
          done

          echo "✅ All Service definitions are valid"
```

### 4. OPA (Open Policy Agent) 정책

```rego
# policies/service-port-name.rego
package kubernetes.admission

deny[msg] {
  input.request.kind.kind == "Service"
  not input.request.object.spec.ports[_].name
  msg := "Service ports must have a name field for Istio protocol detection"
}

deny[msg] {
  input.request.kind.kind == "Service"
  port := input.request.object.spec.ports[_]
  not regex.match("^(http|https|http2|grpc|tcp|mongo|redis|mysql)", port.name)
  msg := sprintf("Port name '%s' does not start with a valid protocol prefix", [port.name])
}
```

### 5. 문서화

```markdown
# docs/development/service-guidelines.md

## Kubernetes Service 생성 가이드

### 필수 사항
1. **포트 이름 명시**: 모든 포트에 `name` 필드 추가
2. **프로토콜 접두사**: 이름은 프로토콜로 시작 (http, grpc, tcp 등)
3. **일관성**: 동일한 프로토콜은 동일한 접두사 사용

### 예시
\`\`\`yaml
ports:
- name: http        # HTTP 트래픽
  port: 8080
- name: grpc-api    # gRPC API
  port: 9090
- name: tcp-admin   # TCP 관리 포트
  port: 9091
\`\`\`

### 주의사항
- 포트 이름 없으면 Istio L7 기능 사용 불가
- 자동 감지는 신뢰할 수 없음
- 명시적 선언 권장
```

## 관련 문서
- troubleshooting-istio-routing-with-go-reverseproxy.md
- troubleshooting-istio-mtls-communication.md
- troubleshooting-service-endpoint-missing.md

## 참고 사항

### Istio 버전별 차이

#### Istio 1.15 이전
- 프로토콜 자동 감지 타임아웃: 5초
- 감지 실패 시 TCP로 처리

#### Istio 1.16+
- 프로토콜 자동 감지 타임아웃: 10초
- 더 나은 HTTP/2 감지
- 여전히 명시적 이름 지정 권장

#### Istio 1.20+
- 자동 감지 개선
- WebSocket 지원 강화
- 명시적 이름 지정 여전히 Best Practice

### 포트 이름 네이밍 컨벤션

**권장**:
```yaml
# 명확하고 의미 있는 이름
- name: http-web      # 웹 트래픽
- name: grpc-api      # API 서비스
- name: http-metrics  # Prometheus
```

**피해야 할 이름**:
```yaml
# Bad: 프로토콜 없음
- name: web
- name: api

# Bad: 숫자만
- name: 8080

# Bad: 모호함
- name: main
- name: default
```

### 자주 발생하는 실수

1. **대소문자 혼동**
   ```yaml
   # Wrong
   - name: HTTP
   - name: Http

   # Correct
   - name: http
   ```

2. **하이픈 vs 언더스코어**
   ```yaml
   # Both work, but hyphen is more common
   - name: http-web    # Recommended
   - name: http_web    # Works but less common
   ```

3. **프로토콜 접두사 누락**
   ```yaml
   # Wrong
   - name: web-api

   # Correct
   - name: http-web-api
   ```

### 디버깅 팁

```bash
# 1. Service 프로토콜 확인
kubectl get svc <service-name> -n <namespace> -o yaml | grep -A 3 "ports:"

# 2. Envoy 리스너 프로토콜 확인
istioctl proxy-config listener <pod> -n <namespace> --port <port> -o json

# 3. 프로토콜 감지 로그 확인
kubectl logs <pod> -n <namespace> -c istio-proxy | grep -i "protocol"

# 4. Istio 설정 검증
istioctl analyze -n <namespace>
```

## 관련 커밋
- git diff의 `blog-service-service.yaml` 변경사항 (name: http 추가)

## 추가 자료
- [Istio Protocol Selection](https://istio.io/latest/docs/ops/configuration/traffic-management/protocol-selection/)
- [Kubernetes Service API Reference](https://kubernetes.io/docs/reference/kubernetes-api/service-resources/service-v1/)
- [Envoy HTTP Connection Manager](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_conn_man/http_conn_man)

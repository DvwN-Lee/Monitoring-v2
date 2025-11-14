# Istio 서비스 메시 환경에서 Go ReverseProxy 라우팅 문제 해결

## 문제 현상

### 에러 메시지
```
HTTP 503 Service Unavailable
upstream connect error or disconnect/reset before headers. reset reason: connection failure
```

### 발생 상황
- Istio 서비스 메시 환경에서 Go로 구현된 API Gateway를 통해 다른 마이크로서비스 호출 시 503 에러 발생
- 특히 `/blog/api/login`, `/blog/api/register` 등의 엔드포인트 호출 실패
- 직접 서비스 엔드포인트를 호출하면 정상 작동

### 영향 범위
- 모든 API Gateway를 통한 백엔드 서비스 호출 실패
- 사용자 인증, 데이터 조회 등 핵심 기능 장애

## 원인 분석

### 근본 원인
Go의 `httputil.NewSingleHostReverseProxy()` 함수는 내부적으로 업스트림 서비스의 호스트 이름을 IP 주소로 변환합니다. Istio는 서비스 이름(FQDN)을 기반으로 트래픽을 라우팅하고 mTLS를 적용하는데, IP 주소로 변환된 요청은 Istio가 올바르게 인식하지 못해 503 에러가 발생합니다.

### 기술적 배경

#### 기존 코드의 문제
```go
userServiceURL, _ := url.Parse("http://user-service:8001")
userProxy := httputil.NewSingleHostReverseProxy(userServiceURL)
```

`NewSingleHostReverseProxy()`는 다음과 같이 동작합니다:
1. DNS를 통해 `user-service:8001`을 IP 주소로 변환 (예: `10.244.1.15:8001`)
2. 요청의 `Host` 헤더를 IP 주소로 설정
3. Istio Envoy 프록시가 IP 기반 요청을 인식하지 못함

#### Istio의 요구사항
- Istio는 서비스 이름(예: `user-service`)을 기반으로 라우팅 규칙 적용
- `VirtualService`, `DestinationRule` 등은 모두 서비스 이름으로 정의됨
- `Host` 헤더가 IP 주소인 경우 Istio가 적절한 규칙을 찾지 못함

## 해결 방법

### 1. 커스텀 Director 함수 사용

`ReverseProxy`의 `Director` 함수를 커스터마이징하여 호스트 이름을 유지합니다.

#### 수정 전
```go
transport := &http.Transport{
    ResponseHeaderTimeout: 2 * time.Second,
    IdleConnTimeout:       30 * time.Second,
    ExpectContinueTimeout: 1 * time.Second,
}
userProxy := httputil.NewSingleHostReverseProxy(userServiceURL)
userProxy.Transport = transport
```

#### 수정 후
```go
userProxy := &httputil.ReverseProxy{
    Director: func(req *http.Request) {
        req.URL.Scheme = userServiceURL.Scheme  // http
        req.URL.Host = userServiceURL.Host      // user-service:8001
        req.Host = userServiceURL.Host          // Host 헤더도 서비스 이름 유지
    },
}
```

### 2. 전체 서비스에 적용

모든 백엔드 서비스(user-service, auth-service, blog-service)에 동일한 패턴 적용:

```go
authProxy := &httputil.ReverseProxy{
    Director: func(req *http.Request) {
        req.URL.Scheme = authServiceURL.Scheme
        req.URL.Host = authServiceURL.Host
        req.Host = authServiceURL.Host
    },
}

blogProxy := &httputil.ReverseProxy{
    Director: func(req *http.Request) {
        req.URL.Scheme = blogServiceURL.Scheme
        req.URL.Host = blogServiceURL.Host
        req.Host = blogServiceURL.Host
    },
}
```

### 3. 핸들러 등록

```go
mux := http.NewServeMux()
mux.Handle("/blog/api/", http.StripPrefix("/blog/api", authProxy))
mux.Handle("/api/users/", http.StripPrefix("/api/users", userProxy))
```

## 검증 방법

### 1. API Gateway 재배포
```bash
# 이미지 빌드 및 푸시
docker build -t your-registry/api-gateway:latest ./api-gateway
docker push your-registry/api-gateway:latest

# Kubernetes 배포 업데이트
kubectl set image deployment/api-gateway-deployment \
  api-gateway=your-registry/api-gateway:latest -n titanium-prod

# Pod 재시작 확인
kubectl rollout status deployment/api-gateway-deployment -n titanium-prod
```

### 2. 엔드포인트 테스트
```bash
# Istio Ingress Gateway를 통한 요청
curl -X POST http://istio-ingressgateway.istio-system.svc.cluster.local/blog/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"testpass"}'

# 예상 응답: HTTP 200 또는 401 (인증 실패)
# 503 에러가 발생하지 않아야 함
```

### 3. Istio 메트릭 확인
```bash
# Envoy 프록시 통계 확인
kubectl exec -n titanium-prod <api-gateway-pod> -c istio-proxy \
  -- curl localhost:15000/stats | grep upstream_rq

# upstream_rq_5xx 카운터가 증가하지 않아야 함
```

### 4. 로그 확인
```bash
# API Gateway 로그
kubectl logs -n titanium-prod <api-gateway-pod> -c api-gateway

# Istio Envoy 로그
kubectl logs -n titanium-prod <api-gateway-pod> -c istio-proxy
```

## 예방 방법

### 1. Istio와 함께 사용하는 Go 프록시 Best Practice

```go
// Good: Istio 호환 커스텀 Director
proxy := &httputil.ReverseProxy{
    Director: func(req *http.Request) {
        req.URL.Scheme = targetURL.Scheme
        req.URL.Host = targetURL.Host
        req.Host = targetURL.Host  // 중요: Host 헤더 유지
    },
}

// Bad: 기본 NewSingleHostReverseProxy 사용
proxy := httputil.NewSingleHostReverseProxy(targetURL)
```

### 2. 개발 환경에서 테스트

로컬 Minikube나 Kind 클러스터에 Istio를 설치하여 프록시 구현을 사전 검증:

```bash
# Istio 설치
istioctl install --set profile=demo -y

# 네임스페이스에 사이드카 주입 활성화
kubectl label namespace default istio-injection=enabled

# 프록시 테스트
kubectl apply -f test-deployment.yaml
```

### 3. 통합 테스트 작성

API Gateway의 통합 테스트에 Istio 환경 시뮬레이션 추가:

```go
func TestReverseProxyWithHostHeader(t *testing.T) {
    // 테스트 서버 생성
    backend := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        // Host 헤더가 서비스 이름인지 확인
        assert.Equal(t, "user-service:8001", r.Host)
    }))
    defer backend.Close()

    // 프록시 테스트
    // ...
}
```

## 관련 문서
- [Istio Traffic Management](https://istio.io/latest/docs/concepts/traffic-management/)
- [Go httputil.ReverseProxy Documentation](https://pkg.go.dev/net/http/httputil#ReverseProxy)
- troubleshooting-istio-mtls-communication.md

## 참고 사항

### Istio 버전별 차이
- Istio 1.20+에서는 IP 기반 라우팅도 일부 지원하지만, 여전히 서비스 이름 사용이 권장됨
- 이전 버전(1.15-1.19)에서는 호스트 이름 유지가 필수

### 성능 고려사항
- 커스텀 Director 함수는 매 요청마다 실행되므로 로직을 간결하게 유지
- DNS 조회는 Kubernetes DNS가 자동으로 캐싱하므로 성능 저하 없음

### 디버깅 팁
```bash
# Envoy 설정 확인
istioctl proxy-config cluster <api-gateway-pod> -n titanium-prod

# 라우팅 규칙 확인
istioctl proxy-config routes <api-gateway-pod> -n titanium-prod
```

## 관련 커밋
- `8849bdb`: fix: Istio 서비스 메시 환경에서 api-gateway 라우팅 문제 해결
- `48da645`: fix: ReverseProxy가 호스트 이름을 IP로 해석하지 않도록 수정

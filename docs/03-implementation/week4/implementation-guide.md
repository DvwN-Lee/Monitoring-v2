# Week 4 구현 가이드: 서비스 메시 & 고급 기능

작성: 이동주
작성일: 2025-11-01

## 목차
1. [개요](#개요)
2. [Istio 서비스 메시 설치](#istio-서비스-메시-설치)
3. [mTLS 보안 설정](#mtls-보안-설정)
4. [HPA 자동 스케일링 구성](#hpa-자동-스케일링-구성)
5. [API Rate Limiting](#api-rate-limiting)
6. [검증 및 테스트](#검증-및-테스트)

---

## 개요

Week 4에서는 Kubernetes 클러스터에 Istio 서비스 메시를 도입하고, 다음과 같은 고급 기능을 구현했습니다:

- **서비스 메시**: Istio를 통한 마이크로서비스 간 통신 관리
- **mTLS 보안**: 서비스 간 통신 암호화
- **자동 스케일링**: HPA를 통한 동적 Pod 관리
- **Rate Limiting**: API 요청 속도 제한

### 관련 이슈
- Epic: #22
- #23: Istio 서비스 메시 설치
- #24: Istio mTLS 보안 설정
- #25: HPA 구성
- #26: API Rate Limiting
- #27: 통합 테스트 및 검증

---

## Istio 서비스 메시 설치

### 1. Istio 다운로드 및 설치

```bash
# Istio 1.20.1 다운로드
cd /path/to/project
curl -L https://istio.io/downloadIstio | ISTIO_VERSION=1.20.1 sh -

# PATH 설정
export PATH="$PATH:/path/to/project/istio-1.20.1/bin"

# 설치 전 클러스터 검증
istioctl x precheck

# Demo profile로 설치
istioctl install --set profile=demo -y
```

**결과 확인:**
```bash
kubectl get pods -n istio-system
```

예상 출력:
```
NAME                                   READY   STATUS
istio-egressgateway-xxx                1/1     Running
istio-ingressgateway-xxx               1/1     Running
istiod-xxx                             1/1     Running
```

### 2. 네임스페이스에 사이드카 자동 주입 활성화

```bash
# titanium-prod 네임스페이스에 레이블 추가
kubectl label namespace titanium-prod istio-injection=enabled
```

### 3. 사이드카 리소스 최적화

Istio의 기본 사이드카 리소스(CPU: 2000m)는 너무 높아 ResourceQuota를 초과할 수 있습니다.

**k8s-manifests/overlays/solid-cloud/kustomization.yaml에 패치 추가:**

```yaml
patches:
  # ... 기존 패치들 ...

  # Add Istio sidecar resource limits to all Deployments
  - patch: |-
      apiVersion: apps/v1
      kind: Deployment
      metadata:
        name: not-used
      spec:
        template:
          metadata:
            annotations:
              sidecar.istio.io/proxyCPU: "50m"
              sidecar.istio.io/proxyCPULimit: "200m"
              sidecar.istio.io/proxyMemory: "64Mi"
              sidecar.istio.io/proxyMemoryLimit: "256Mi"
    target:
      kind: Deployment
```

**적용 및 재배포:**
```bash
kubectl apply -k k8s-manifests/overlays/solid-cloud
kubectl rollout restart deployment -n titanium-prod
```

### 4. Istio 애드온 설치

```bash
# Prometheus (메트릭 수집)
kubectl apply -f istio-1.20.1/samples/addons/prometheus.yaml

# Kiali (서비스 메시 시각화)
kubectl apply -f istio-1.20.1/samples/addons/kiali.yaml

# Jaeger (분산 추적)
kubectl apply -f istio-1.20.1/samples/addons/jaeger.yaml
```

[주의] Kiali는 Prometheus를 필요로 하므로 Prometheus를 먼저 설치해야 합니다.

#### Kiali 외부 서비스 설정

Kiali가 Grafana, Jaeger 등과 연동되도록 ConfigMap을 업데이트합니다.

**k8s-manifests/overlays/solid-cloud/istio/kiali-config.yaml:**

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: kiali
  namespace: istio-system
data:
  config.yaml: |
    auth:
      strategy: anonymous
    deployment:
      accessible_namespaces:
      - '**'
    external_services:
      grafana:
        enabled: true
        in_cluster_url: 'http://prometheus-grafana.monitoring:80'
      prometheus:
        url: 'http://prometheus.istio-system:9090'
      tracing:
        enabled: true
        in_cluster_url: 'http://tracing.istio-system:80'
    istio_namespace: istio-system
```

**적용:**
```bash
kubectl apply -f k8s-manifests/overlays/solid-cloud/istio/kiali-config.yaml
kubectl rollout restart deployment kiali -n istio-system
```

### 5. Gateway 및 VirtualService 생성

**k8s-manifests/overlays/solid-cloud/istio/gateway.yaml:**

```yaml
apiVersion: networking.istio.io/v1beta1
kind: Gateway
metadata:
  name: titanium-gateway
  namespace: titanium-prod
spec:
  selector:
    istio: ingressgateway
  servers:
  - port:
      number: 80
      name: http
      protocol: HTTP
    hosts:
    - "*"
---
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: load-balancer-vs
  namespace: titanium-prod
spec:
  hosts:
  - "*"
  gateways:
  - titanium-gateway
  http:
  - match:
    - uri:
        prefix: /
    route:
    - destination:
        host: prod-load-balancer-service
        port:
          number: 7100
```

**적용:**
```bash
kubectl apply -f k8s-manifests/overlays/solid-cloud/istio/gateway.yaml
```

### 6. 검증

```bash
# 모든 Pod에 사이드카 주입 확인 (2/2 READY)
kubectl get pods -n titanium-prod

# Istio proxy 상태 확인
istioctl proxy-status

# 모든 proxy가 SYNCED 상태여야 함
```

---

## mTLS 보안 설정

### 1. PeerAuthentication 생성

**k8s-manifests/overlays/solid-cloud/istio/peer-authentication.yaml:**

```yaml
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default-mtls
  namespace: titanium-prod
spec:
  mtls:
    mode: STRICT
```

STRICT 모드는 모든 서비스 간 통신이 반드시 mTLS를 사용하도록 강제합니다.

### 2. DestinationRule 생성

**k8s-manifests/overlays/solid-cloud/istio/destination-rules.yaml:**

```yaml
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: default-mtls
  namespace: titanium-prod
spec:
  host: "*.titanium-prod.svc.cluster.local"
  trafficPolicy:
    tls:
      mode: ISTIO_MUTUAL
---
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: user-service
  namespace: titanium-prod
spec:
  host: prod-user-service
  trafficPolicy:
    tls:
      mode: ISTIO_MUTUAL
# ... 다른 서비스들도 동일하게 생성 ...
```

**적용:**
```bash
kubectl apply -f k8s-manifests/overlays/solid-cloud/istio/peer-authentication.yaml
kubectl apply -f k8s-manifests/overlays/solid-cloud/istio/destination-rules.yaml
```

### 3. mTLS 검증

```bash
# PeerAuthentication 확인
kubectl get peerauthentication -n titanium-prod

# DestinationRule 확인
kubectl get destinationrule -n titanium-prod

# mTLS 인증서 확인
POD_NAME=$(kubectl get pods -n titanium-prod -l app=api-gateway -o jsonpath='{.items[0].metadata.name}')
istioctl proxy-config secret $POD_NAME -n titanium-prod
```

예상 출력:
```
RESOURCE NAME     TYPE           STATUS     VALID CERT
default           Cert Chain     ACTIVE     true
ROOTCA            CA             ACTIVE     true
```

---

## HPA 자동 스케일링 구성

### 1. Metrics Server 설치

```bash
# Metrics Server 설치
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# Kubelet TLS 검증 비활성화 (온프레미스 환경)
kubectl patch deployment metrics-server -n kube-system --type='json' \
  -p='[{"op": "add", "path": "/spec/template/spec/containers/0/args/-", "value": "--kubelet-insecure-tls"}]'
```

### 2. Metrics Server 동작 확인

```bash
# 노드 메트릭 확인
kubectl top nodes

# Pod 메트릭 확인
kubectl top pods -n titanium-prod
```

### 3. HPA 리소스 생성

**k8s-manifests/overlays/solid-cloud/hpa.yaml:**

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: prod-user-service-hpa
  namespace: titanium-prod
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: prod-user-service-deployment
  minReplicas: 1
  maxReplicas: 5
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
---
# auth-service, blog-service, api-gateway도 동일하게 생성
```

**적용:**
```bash
kubectl apply -f k8s-manifests/overlays/solid-cloud/hpa.yaml
```

### 4. HPA 동작 확인

```bash
# HPA 상태 확인
kubectl get hpa -n titanium-prod

# 예상 출력:
# NAME                    REFERENCE                                 TARGETS   MINPODS   MAXPODS   REPLICAS
# prod-user-service-hpa   Deployment/prod-user-service-deployment   4%/70%    1         5         2
```

HPA는 CPU 사용률이 70%를 초과하면 Pod를 자동으로 증가시키고, 사용률이 낮아지면 감소시킵니다.

---

## API Rate Limiting

### 1. EnvoyFilter를 사용한 Rate Limiting

**k8s-manifests/overlays/solid-cloud/istio/rate-limit.yaml:**

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: rate-limit-filter
  namespace: titanium-prod
spec:
  workloadSelector:
    labels:
      app: load-balancer
  configPatches:
  - applyTo: HTTP_FILTER
    match:
      context: SIDECAR_INBOUND
      listener:
        filterChain:
          filter:
            name: "envoy.filters.network.http_connection_manager"
            subFilter:
              name: "envoy.filters.http.router"
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.filters.http.local_ratelimit
        typed_config:
          "@type": type.googleapis.com/udpa.type.v1.TypedStruct
          type_url: type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit
          value:
            stat_prefix: http_local_rate_limiter
            token_bucket:
              max_tokens: 100
              tokens_per_fill: 100
              fill_interval: 60s
            filter_enabled:
              runtime_key: local_rate_limit_enabled
              default_value:
                numerator: 100
                denominator: HUNDRED
            filter_enforced:
              runtime_key: local_rate_limit_enforced
              default_value:
                numerator: 100
                denominator: HUNDRED
            response_headers_to_add:
            - append: false
              header:
                key: x-local-rate-limit
                value: 'true'
            local_rate_limit_per_downstream_connection: false
```

이 설정은 load-balancer 서비스에 분당 100 요청 제한을 적용합니다.

**적용:**
```bash
kubectl apply -f k8s-manifests/overlays/solid-cloud/istio/rate-limit.yaml
```

### 2. Rate Limit 동작 확인

```bash
# EnvoyFilter 확인
kubectl get envoyfilter -n titanium-prod

# 부하 테스트 (선택)
# 분당 100개 이상의 요청을 보내면 429 응답을 받아야 함
```

---

## 검증 및 테스트

### 1. 전체 시스템 상태 확인

```bash
# 모든 Pod가 2/2 Running 상태 확인
kubectl get pods -n titanium-prod

# Istio 리소스 확인
kubectl get gateway,virtualservice,destinationrule,peerauthentication,envoyfilter -n titanium-prod

# HPA 상태 확인
kubectl get hpa -n titanium-prod

# Istio proxy 동기화 상태
istioctl proxy-status
```

### 2. 서비스 메시 시각화

```bash
# Kiali 대시보드 접근
kubectl port-forward -n istio-system svc/kiali 20001:20001

# 브라우저에서 http://localhost:20001 접속
# Graph 메뉴에서 titanium-prod 네임스페이스 선택
# 서비스 간 트래픽 흐름 및 mTLS 잠금 아이콘 확인
```

### 3. 리소스 사용량 확인

```bash
# ResourceQuota 확인
kubectl describe resourcequota titanium-prod-quota -n titanium-prod

# 예상 사용량:
# limits.cpu: 5500m / 16000m (사이드카 최적화 후)
# limits.memory: 7424Mi / 32Gi
```

### 4. 성능 테스트 (선택)

```bash
# 간단한 부하 테스트
for i in {1..100}; do
  curl -s http://<load-balancer-external-ip> > /dev/null &
done
wait

# HPA가 Pod 수를 증가시키는지 확인
kubectl get hpa -n titanium-prod -w
```

---

## 다음 단계

Week 4 구현을 완료했습니다. 다음 단계:

1. **모니터링 강화**: Grafana에서 Istio 메트릭 대시보드 추가
2. **보안 강화**: NetworkPolicy 추가, RBAC 세밀화
3. **관찰성 향상**: Jaeger를 통한 분산 추적 분석
4. **성능 최적화**: 부하 테스트 결과 기반 리소스 튜닝

## 참고 문서

- [Istio 공식 문서](https://istio.io/latest/docs/)
- [Kubernetes HPA](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)
- [Envoy Rate Limiting](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_filters/local_rate_limit_filter)
- [Week 4 트러블슈팅 가이드](./troubleshooting-week4.md)

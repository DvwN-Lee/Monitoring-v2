# Week 4 트러블슈팅 가이드

작성: 이동주
작성일: 2025-11-01

## 목차
1. [Istio 설치 및 사이드카 주입 문제](#istio-설치-및-사이드카-주입-문제)
2. [Kiali 및 관찰성 문제](#kiali-및-관찰성-문제)
3. [mTLS 관련 문제](#mtls-관련-문제)
4. [Metrics Server 및 HPA 문제](#metrics-server-및-hpa-문제)
5. [ResourceQuota 초과 문제](#resourcequota-초과-문제)
6. [Rate Limiting 문제](#rate-limiting-문제)

---

## Istio 설치 및 사이드카 주입 문제

### 문제 1: Pod가 2/2가 아닌 1/1로 표시됨

**증상:**
```bash
kubectl get pods -n titanium-prod
NAME                                          READY   STATUS
prod-user-service-deployment-xxx              1/1     Running
```

**원인:**
- 네임스페이스에 `istio-injection=enabled` 레이블이 없음
- 기존 Pod는 레이블 추가 전에 생성됨

**해결 방법:**
```bash
# 1. 네임스페이스 레이블 확인
kubectl get namespace titanium-prod --show-labels

# 2. 레이블이 없다면 추가
kubectl label namespace titanium-prod istio-injection=enabled

# 3. 기존 Pod 재시작
kubectl rollout restart deployment -n titanium-prod

# 4. 모든 Pod가 2/2인지 확인
kubectl get pods -n titanium-prod
```

### 문제 2: Istio 사이드카가 CrashLoopBackOff 상태

**증상:**
```bash
kubectl get pods -n titanium-prod
NAME                                          READY   STATUS
prod-user-service-deployment-xxx              1/2     CrashLoopBackOff
```

**원인:**
- 사이드카와 애플리케이션 컨테이너 간 포트 충돌
- 네트워크 정책 문제

**해결 방법:**
```bash
# 1. 사이드카 로그 확인
kubectl logs -n titanium-prod <pod-name> -c istio-proxy

# 2. 애플리케이션 로그 확인
kubectl logs -n titanium-prod <pod-name> -c <app-container-name>

# 3. Pod 상세 정보 확인
kubectl describe pod -n titanium-prod <pod-name>

# 4. 필요시 사이드카 주입 제외
kubectl label pod -n titanium-prod <pod-name> sidecar.istio.io/inject=false
```

### 문제 3: istioctl 명령어를 찾을 수 없음

**증상:**
```bash
istioctl version
command not found: istioctl
```

**해결 방법:**
```bash
# PATH 설정 추가
export PATH="$PATH:/path/to/istio-1.20.1/bin"

# 영구 설정 (bash)
echo 'export PATH="$PATH:/path/to/istio-1.20.1/bin"' >> ~/.bashrc
source ~/.bashrc

# 영구 설정 (zsh)
echo 'export PATH="$PATH:/path/to/istio-1.20.1/bin"' >> ~/.zshrc
source ~/.zshrc
```

---

## Kiali 및 관찰성 문제

### 문제 4: Kiali에서 "Could not fetch metrics" 오류

**증상:**
```
Could not fetch metrics: error in metric request_count: Post "http://prometheus.istio-system:9090/api/v1/query_range": dial tcp: lookup prometheus.istio-system on 10.96.0.10:53: no such host
```

Kiali 대시보드에 접속하면 메트릭을 가져올 수 없다는 오류가 표시됩니다.

**원인:**
- Istio의 Prometheus addon이 설치되지 않음
- Kiali는 기본적으로 `prometheus.istio-system` 서비스를 찾음

**해결 방법:**

**방법 1: Istio Prometheus addon 설치 (권장)**

```bash
# Prometheus 설치
kubectl apply -f istio-1.20.1/samples/addons/prometheus.yaml

# Prometheus Pod 확인
kubectl get pods -n istio-system -l app=prometheus

# Prometheus 서비스 확인
kubectl get svc -n istio-system prometheus

# Kiali 재시작
kubectl rollout restart deployment kiali -n istio-system

# Kiali가 준비될 때까지 대기
kubectl wait --for=condition=ready pod -l app=kiali -n istio-system --timeout=60s
```

**방법 2: 기존 Prometheus 사용 (고급)**

monitoring 네임스페이스에 이미 Prometheus가 있다면 Kiali ConfigMap을 수정:

```bash
kubectl edit configmap kiali -n istio-system
```

다음 내용 추가:
```yaml
external_services:
  prometheus:
    url: "http://prometheus-kube-prometheus-prometheus.monitoring:9090"
```

Kiali 재시작:
```bash
kubectl rollout restart deployment kiali -n istio-system
```

**검증:**
1. Kiali 대시보드에 접속: `kubectl port-forward -n istio-system svc/kiali 20001:20001`
2. 브라우저에서 `http://localhost:20001` 접속
3. Graph 메뉴 선택
4. 네임스페이스에서 `titanium-prod` 선택
5. 서비스 간 트래픽 흐름과 메트릭이 표시되는지 확인

---

## mTLS 관련 문제

### 문제 5: 서비스 간 통신이 실패함

**증상:**
```bash
# 애플리케이션 로그에서 TLS 관련 에러
Error: upstream connect error or disconnect/reset before headers
```

**원인:**
- PeerAuthentication이 STRICT이지만 DestinationRule이 설정되지 않음
- mTLS 모드 불일치

**해결 방법:**
```bash
# 1. PeerAuthentication 확인
kubectl get peerauthentication -n titanium-prod default-mtls -o yaml

# 2. DestinationRule 확인
kubectl get destinationrule -n titanium-prod

# 3. 모든 서비스에 DestinationRule이 있는지 확인
# 없다면 생성
kubectl apply -f k8s-manifests/overlays/solid-cloud/istio/destination-rules.yaml

# 4. Istio proxy 재시작
kubectl rollout restart deployment -n titanium-prod
```

### 문제 6: mTLS 인증서가 유효하지 않음

**증상:**
```bash
istioctl proxy-config secret <pod-name> -n titanium-prod
# VALID CERT: false
```

**원인:**
- istiod와의 연결 문제
- 인증서 갱신 실패

**해결 방법:**
```bash
# 1. istiod 상태 확인
kubectl get pods -n istio-system -l app=istiod

# 2. istiod 로그 확인
kubectl logs -n istio-system -l app=istiod

# 3. Pod 재시작으로 인증서 재발급
kubectl delete pod -n titanium-prod <pod-name>

# 4. 인증서 재확인
POD_NAME=$(kubectl get pods -n titanium-prod -l app=<service> -o jsonpath='{.items[0].metadata.name}')
istioctl proxy-config secret $POD_NAME -n titanium-prod
```

---

## Metrics Server 및 HPA 문제

### 문제 7: Metrics Server가 동작하지 않음

**증상:**
```bash
kubectl top nodes
Error from server (ServiceUnavailable): the server is currently unable to handle the request
```

**원인:**
- Metrics Server Pod가 실행되지 않음
- Kubelet과의 TLS 인증서 검증 실패

**해결 방법:**
```bash
# 1. Metrics Server Pod 상태 확인
kubectl get pods -n kube-system -l k8s-app=metrics-server

# 2. Metrics Server 로그 확인
kubectl logs -n kube-system -l k8s-app=metrics-server

# 3. TLS 검증 오류가 있다면 패치 적용
kubectl patch deployment metrics-server -n kube-system --type='json' \
  -p='[{"op": "add", "path": "/spec/template/spec/containers/0/args/-", "value": "--kubelet-insecure-tls"}]'

# 4. 동작 확인
sleep 30
kubectl top nodes
```

**로그 예시 (TLS 오류):**
```
Failed to scrape node: tls: failed to verify certificate: x509: cannot validate certificate
```

### 문제 8: HPA가 메트릭을 수집하지 못함

**증상:**
```bash
kubectl get hpa -n titanium-prod
NAME                    REFERENCE            TARGETS         MINPODS   MAXPODS
prod-user-service-hpa   Deployment/...       <unknown>/70%   1         5
```

**원인:**
- Deployment에 리소스 요청(requests)이 설정되지 않음
- Metrics Server가 동작하지 않음

**해결 방법:**
```bash
# 1. Deployment에 리소스 설정 확인
kubectl get deployment -n titanium-prod prod-user-service-deployment -o yaml | grep -A 10 resources

# 2. 리소스 요청이 없다면 추가 필요
# base Deployment YAML 파일에서 다음 추가:
#   resources:
#     requests:
#       memory: "128Mi"
#       cpu: "100m"

# 3. 30초 대기 후 재확인
sleep 30
kubectl get hpa -n titanium-prod
```

### 문제 9: HPA가 스케일링하지 않음

**증상:**
- CPU 사용률이 목표를 초과했지만 Pod가 증가하지 않음

**원인:**
- 스케일 다운/업 쿨다운 시간
- ResourceQuota 초과

**해결 방법:**
```bash
# 1. HPA 상세 정보 확인
kubectl describe hpa -n titanium-prod prod-user-service-hpa

# 2. 이벤트 확인
kubectl get events -n titanium-prod --sort-by='.lastTimestamp' | grep HorizontalPodAutoscaler

# 3. ResourceQuota 확인
kubectl describe resourcequota -n titanium-prod

# 4. 쿨다운 시간 대기 (기본 3-5분)
# HPA는 급격한 변화를 방지하기 위해 쿨다운을 사용
```

---

## ResourceQuota 초과 문제

### 문제 10: Pod 생성이 Quota 초과로 실패

**증상:**
```bash
kubectl get pods -n titanium-prod
NAME                              READY   STATUS
prod-user-service-deployment-xxx  0/2     Pending

kubectl describe pod -n titanium-prod <pod-name>
Error: exceeded quota: titanium-prod-quota, requested: limits.cpu=2200m
```

**원인:**
- Istio 사이드카의 기본 CPU limits가 2000m로 너무 높음
- 여러 Pod를 동시에 생성하면 Quota 초과

**해결 방법:**

**방법 1: 사이드카 리소스 최적화 (권장)**

k8s-manifests/overlays/solid-cloud/kustomization.yaml에 패치 추가:

```yaml
patches:
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

적용:
```bash
kubectl apply -k k8s-manifests/overlays/solid-cloud
kubectl rollout restart deployment -n titanium-prod
```

**방법 2: 임시로 Quota 증가 (비권장)**

```bash
# 임시로 CPU limits 증가 (16 → 24)
kubectl patch resourcequota titanium-prod-quota -n titanium-prod --type merge \
  -p '{"spec":{"hard":{"limits.cpu":"24"}}}'

# Pod 재생성 대기
sleep 30

# Quota를 원래대로 복원
kubectl patch resourcequota titanium-prod-quota -n titanium-prod --type merge \
  -p '{"spec":{"hard":{"limits.cpu":"16"}}}'
```

### 문제 11: Rolling Update가 진행되지 않음

**증상:**
- Deployment는 업데이트되었지만 새 Pod가 생성되지 않음
- 기존 1/1 Pod와 새 2/2 Pod가 혼재

**원인:**
- ResourceQuota 부족으로 새 Pod 생성 실패
- Rolling Update 전략에서 maxSurge로 인한 일시적 Quota 초과

**해결 방법:**
```bash
# 1. 기존 1/1 Pod 수동 삭제
kubectl get pods -n titanium-prod -o wide | grep "1/1"
kubectl delete pod -n titanium-prod <old-pod-name> <old-pod-name2> ...

# 2. 새 Pod 생성 확인
kubectl get pods -n titanium-prod -w

# 3. 모든 Pod가 2/2가 될 때까지 반복
```

---

## Rate Limiting 문제

### 문제 12: Rate Limiting이 동작하지 않음

**증상:**
- 대량의 요청을 보내도 429 응답을 받지 못함

**원인:**
- EnvoyFilter가 적용되지 않음
- workloadSelector가 잘못됨

**해결 방법:**
```bash
# 1. EnvoyFilter 확인
kubectl get envoyfilter -n titanium-prod rate-limit-filter -o yaml

# 2. workloadSelector가 올바른 레이블을 사용하는지 확인
kubectl get pods -n titanium-prod --show-labels | grep load-balancer

# 3. EnvoyFilter 재적용
kubectl delete envoyfilter -n titanium-prod rate-limit-filter
kubectl apply -f k8s-manifests/overlays/solid-cloud/istio/rate-limit.yaml

# 4. Pod 재시작 (선택)
kubectl rollout restart deployment -n titanium-prod prod-load-balancer-deployment
```

### 문제 13: Rate Limit 헤더가 응답에 포함되지 않음

**증상:**
- 429 응답은 받지만 x-local-rate-limit 헤더가 없음

**원인:**
- EnvoyFilter 설정에서 response_headers_to_add가 누락됨

**해결 방법:**

EnvoyFilter YAML 확인 및 수정:
```yaml
response_headers_to_add:
- append: false
  header:
    key: x-local-rate-limit
    value: 'true'
```

적용:
```bash
kubectl apply -f k8s-manifests/overlays/solid-cloud/istio/rate-limit.yaml
```

---

## 일반적인 디버깅 명령어

### Pod 상태 확인
```bash
# 모든 Pod 상태
kubectl get pods -n titanium-prod

# 특정 Pod 상세 정보
kubectl describe pod -n titanium-prod <pod-name>

# 컨테이너 로그
kubectl logs -n titanium-prod <pod-name> -c <container-name>

# 이전 컨테이너 로그 (재시작된 경우)
kubectl logs -n titanium-prod <pod-name> -c <container-name> --previous
```

### Istio 디버깅
```bash
# Proxy 상태 확인
istioctl proxy-status

# Proxy 설정 확인
istioctl proxy-config cluster <pod-name> -n titanium-prod
istioctl proxy-config listener <pod-name> -n titanium-prod
istioctl proxy-config route <pod-name> -n titanium-prod

# Proxy 로그 레벨 변경
istioctl proxy-config log <pod-name> -n titanium-prod --level debug
```

### 리소스 확인
```bash
# ResourceQuota 상세
kubectl describe resourcequota -n titanium-prod

# 노드 리소스
kubectl top nodes

# Pod 리소스
kubectl top pods -n titanium-prod

# HPA 상태
kubectl get hpa -n titanium-prod
kubectl describe hpa -n titanium-prod <hpa-name>
```

### 이벤트 확인
```bash
# 최근 이벤트
kubectl get events -n titanium-prod --sort-by='.lastTimestamp'

# 특정 리소스의 이벤트
kubectl describe <resource-type> -n titanium-prod <resource-name>
```

---

## 추가 지원

문제가 해결되지 않을 경우:

1. **Istio 커뮤니티**: https://discuss.istio.io/
2. **Kubernetes 문서**: https://kubernetes.io/docs/tasks/debug/
3. **프로젝트 이슈**: GitHub Issues에 문제 보고

## 관련 문서

- [Week 4 구현 가이드](./implementation-guide.md)
- [Week 4 요약](./week4-summary.md)

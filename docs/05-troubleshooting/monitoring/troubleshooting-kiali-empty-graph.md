# Kiali Empty Graph 오류 해결

**날짜**: 2025-12-08
**카테고리**: Monitoring, Kiali
**심각도**: Medium
**상태**: 해결됨

---

## 문제 설명

Kiali UI에서 다음 오류가 발생하며 트래픽 그래프가 표시되지 않음:

```
Error fetching Istio deployment status
Cannot load the graph
```

### 증상

- Kiali UI 접속 가능
- Graph 메뉴 선택 시 "No inbound traffic" 메시지
- titanium-prod namespace 트래픽 시각화 불가

---

## 환경 정보

| 구성 요소 | 버전/상태 |
|-----------|-----------|
| Kiali | v2.0.0 |
| Istio | 1.0.0 |
| Prometheus | istio-system namespace |
| Grafana | istio-system namespace |
| Kubernetes | K3s |

---

## 근본 원인 분석

### 진단 과정

1. **Sidecar 주입 확인**
   ```bash
   kubectl get pods -n titanium-prod -o wide
   ```
   결과: 모든 Pod READY 2/2 (istio-proxy 정상 주입)

2. **Istio 메트릭 생성 확인**
   ```bash
   kubectl exec -n titanium-prod deploy/prod-api-gateway-deployment \
     -c istio-proxy -- curl -s localhost:15000/stats/prometheus | \
     grep istio_requests_total
   ```
   결과: istio_requests_total 메트릭 존재 (31,284+ requests)

3. **Prometheus 메트릭 수집 확인**
   ```bash
   kubectl exec -n istio-system prometheus-65dbd67cfd-9z5t7 -- \
     wget -qO- "http://localhost:9090/api/v1/query?query=istio_requests_total"
   ```
   결과: Prometheus가 Istio 메트릭 정상 수집 중

4. **Kiali ConfigMap 확인**
   ```bash
   kubectl get cm kiali -n istio-system -o yaml
   ```
   결과: `external_services.prometheus` 설정 없음 (근본 원인)

### 근본 원인

Kiali ConfigMap의 `config.yaml`에 다음 URL이 설정되지 않음:
- Prometheus URL
- Grafana URL
- Istio API URL (istiod)

---

## 해결 방법

### 1. 기존 ConfigMap 백업

```bash
kubectl get cm kiali -n istio-system -o yaml > kiali-cm-backup.yaml
```

### 2. ConfigMap 재생성

기존 ConfigMap 삭제:
```bash
kubectl delete cm kiali -n istio-system
```

새 ConfigMap 생성 (`kiali-cm-new.yaml`):
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: kiali
  namespace: istio-system
  labels:
    app: kiali
data:
  config.yaml: |
    auth:
      strategy: anonymous
    deployment:
      cluster_wide_access: true
      namespace: istio-system
    external_services:
      custom_dashboards:
        enabled: true
      prometheus:
        url: "http://prometheus.istio-system.svc.cluster.local:9090"
      grafana:
        enabled: true
        url: "http://grafana.istio-system.svc.cluster.local:3000"
      istio:
        root_namespace: istio-system
        istiod_deployment_name: istiod
        url_service_version: "http://istiod.istio-system.svc.cluster.local:15014/version"
      tracing:
        enabled: false
    istio_namespace: istio-system
    server:
      port: 20001
      web_root: /kiali
```

적용:
```bash
kubectl apply -f kiali-cm-new.yaml
```

### 3. Kiali 재시작

```bash
kubectl rollout restart deployment/kiali -n istio-system
kubectl rollout status deployment/kiali -n istio-system --timeout=60s
```

### 4. 검증

Pod 상태 확인:
```bash
kubectl get pods -n istio-system | grep kiali
```

예상 출력:
```
kiali-557559b8b7-2g5qx    1/1     Running   0          2m
```

로그 확인:
```bash
kubectl logs -n istio-system deployment/kiali --tail=20
```

정상 로그:
```
2025-12-08T00:52:26Z INF [Kiali Cache] Started
```

### 5. 테스트 트래픽 생성

```bash
for i in {1..10}; do
  curl http://10.0.1.70/blog/
  sleep 0.5
done
```

---

## 검증 결과

### Kiali UI 확인

1. **접속**: `http://10.0.1.70:31200/kiali`
2. **Graph 메뉴 선택**
3. **Namespace**: titanium-prod 선택
4. **Time Range**: Last 5m 설정

### 예상 결과

- istio-ingressgateway → prod-blog-service 트래픽 표시
- 녹색 자물쇠 아이콘 (mTLS 활성화)
- HTTP 200 응답 코드
- Request rate, Error rate, Duration 메트릭 표시

---

## 추가 참고사항

### Deprecated 경고

Kiali 로그에 다음 경고가 표시될 수 있음:
```
DEPRECATION NOTICE: 'external_services.grafana.url' has been deprecated -
switch to 'external_services.grafana.external_url'
```

향후 Kiali 업그레이드 시 `external_url`로 변경 권장.

### 대안: ConfigMap Patch 방식

전체 교체 대신 patch 사용 가능 (단, YAML 구조 주의):
```bash
kubectl patch cm kiali -n istio-system --type=merge -p '{
  "data": {
    "config.yaml": "external_services:\n  prometheus:\n    url: http://prometheus:9090"
  }
}'
```

---

## 관련 문서

- [Kiali Configuration Reference](https://kiali.io/docs/configuration/)
- [Istio Telemetry](https://istio.io/latest/docs/tasks/observability/)
- [Prometheus 메트릭 수집 실패 해결](./troubleshooting-prometheus-metric-collection-failure.md)

---

## 태그

`#kiali` `#empty-graph` `#prometheus` `#istio` `#configmap` `#monitoring`

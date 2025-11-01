# Week 3: 관측성 시스템 구축 - 구현 가이드

## 개요

이 문서는 Titanium 프로젝트 Week 3에서 구현한 관측성(Observability) 시스템의 전체 구현 과정을 설명합니다.

**구축 기간**: 2025-10-30 ~ 2025-10-31
**상태**: [완료]
**Epic**: [#16 Week 3 - 관측성 시스템 구축](https://github.com/DvwN-Lee/Monitoring-v2/issues/16)

---

## 목차

1. [아키텍처 개요](#아키텍처-개요)
2. [구현 단계](#구현-단계)
3. [주요 컴포넌트](#주요-컴포넌트)
4. [검증 결과](#검증-결과)
5. [접속 정보](#접속-정보)
6. [트러블슈팅](#트러블슈팅)

---

## 아키텍처 개요

### 관측성 스택

```
┌─────────────────────────────────────────────────────────┐
│                    Grafana Dashboard                    │
│              (시각화 + 알림 + 탐색)                      │
└────────────┬────────────────────┬───────────────────────┘
             │                    │
    ┌────────▼────────┐   ┌──────▼──────┐
    │   Prometheus    │   │     Loki    │
    │  (메트릭 수집)   │   │  (로그 수집) │
    └────────┬────────┘   └──────┬──────┘
             │                    │
    ┌────────▼────────┐   ┌──────▼──────┐
    │ ServiceMonitor  │   │  Promtail   │
    │  (타겟 발견)     │   │ (로그 수집기)│
    └────────┬────────┘   └──────┬──────┘
             │                    │
    ┌────────▼────────────────────▼──────┐
    │         Titanium Services          │
    │  (api-gateway, user, auth, blog)   │
    └────────────────────────────────────┘
```

### Golden Signals 모니터링

4가지 핵심 시그널을 추적합니다:

1. **Latency (지연 시간)**: P95/P99 응답 시간
2. **Traffic (트래픽)**: RPS (초당 요청 수)
3. **Errors (에러)**: 4xx/5xx 에러율
4. **Saturation (포화도)**: CPU/Memory 사용률

---

## 구현 단계

### Step 1: Prometheus & Grafana 설치 (#17)

**목표**: kube-prometheus-stack으로 모니터링 기반 구축

#### 1.1 Helm Values 설정

파일: [k8s-manifests/monitoring/prometheus-values.yaml](../../k8s-manifests/monitoring/prometheus-values.yaml)

```yaml
grafana:
  enabled: true
  adminPassword: admin123
  service:
    type: NodePort
    nodePort: 30300

  # Grafana Sidecar - 자동 대시보드/datasource 로드
  sidecar:
    dashboards:
      enabled: true
      label: grafana_dashboard
    datasources:
      enabled: true
      label: grafana_datasource

prometheus:
  service:
    type: NodePort
    nodePort: 30090

  prometheusSpec:
    # ServiceMonitor 검색 설정
    serviceMonitorSelector:
      matchLabels:
        release: prometheus

    # 7일 보관
    retention: 7d

    # PrometheusRule 검색 설정
    ruleSelector:
      matchLabels:
        release: prometheus

alertmanager:
  enabled: true
  service:
    type: NodePort
    nodePort: 30093
```

#### 1.2 설치 명령

```bash
# Helm 차트 설치
helm install prometheus prometheus-community/kube-prometheus-stack \
  -n monitoring \
  --create-namespace \
  -f k8s-manifests/monitoring/prometheus-values.yaml

# 설치 확인
kubectl get pods -n monitoring
kubectl get svc -n monitoring
```

#### 1.3 검증

```bash
# Prometheus UI 접속
kubectl port-forward -n monitoring svc/prometheus-kube-prometheus-prometheus 9090:9090

# Grafana UI 접속
kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80
# ID: admin, PW: admin123
```

**결과**:
- [완료] Prometheus Pod 실행 중
- [완료] Grafana Pod 실행 중 (3 containers)
- [완료] AlertManager Pod 실행 중
- [완료] Node Exporter DaemonSet (4 nodes)
- [완료] Kube State Metrics 실행 중

---

### Step 2: 애플리케이션 메트릭 수집 (#18)

**목표**: 4개 마이크로서비스에서 Prometheus 메트릭 수집

#### 2.1 Python 서비스 계측 (user/auth/blog)

**의존성 추가** ([user-service/requirements.txt](../../user-service/requirements.txt)):
```txt
prometheus-client
prometheus-fastapi-instrumentator
```

**메트릭 설정** ([user-service/user_service.py:31-35](../../user-service/user_service.py#L31-L35)):
```python
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI()

# Prometheus 메트릭 설정
# 히스토그램 버킷을 세밀하게 설정하여 정확한 P95/P99 계산 가능
Instrumentator(
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 10.0)
).instrument(app).expose(app)
```

**생성되는 메트릭**:
- `http_requests_total{method, status, handler}`
- `http_request_duration_seconds{method, handler}`
- FastAPI 기본 메트릭

#### 2.2 Go 서비스 계측 (api-gateway)

**의존성 추가** ([api-gateway/go.mod](../../api-gateway/go.mod)):
```go
require github.com/prometheus/client_golang v1.20.5
```

**메트릭 설정** ([api-gateway/main.go:20-36](../../api-gateway/main.go#L20-L36)):
```go
import (
    "github.com/prometheus/client_golang/prometheus"
    "github.com/prometheus/client_golang/prometheus/promauto"
    "github.com/prometheus/client_golang/promhttp"
)

var (
    httpRequestsTotal = promauto.NewCounterVec(
        prometheus.CounterOpts{
            Name: "http_requests_total",
            Help: "Total number of HTTP requests",
        },
        []string{"method", "status"},
    )
    httpRequestDuration = promauto.NewHistogramVec(
        prometheus.HistogramOpts{
            Name:    "http_request_duration_seconds",
            Help:    "Duration of HTTP requests",
            Buckets: prometheus.DefBuckets,
        },
        []string{"method"},
    )
)

// /metrics 엔드포인트
mux.Handle("/metrics", promhttp.Handler())
```

#### 2.3 ServiceMonitor 생성

ServiceMonitor는 Prometheus가 자동으로 타겟을 발견하도록 합니다.

**예시** ([k8s-manifests/monitoring/servicemonitor-user-service.yaml](../../k8s-manifests/monitoring/servicemonitor-user-service.yaml)):
```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: user-service
  namespace: titanium-prod
  labels:
    app: user-service
    release: prometheus  # 필수! Prometheus가 발견할 수 있도록
spec:
  selector:
    matchLabels:
      app: user-service  # Service 레이블과 매칭
  endpoints:
  - port: http
    path: /metrics
    interval: 30s
```

**생성된 ServiceMonitor**:
- `api-gateway` (titanium-prod)
- `auth-service` (titanium-prod)
- `blog-service` (titanium-prod)
- `user-service` (titanium-prod)

#### 2.4 검증

```bash
# Prometheus에서 타겟 확인
curl 'http://localhost:9090/api/v1/targets' | jq -r '.data.activeTargets[] | select(.labels.namespace == "titanium-prod") | .labels.job'
# 출력:
# prod-api-gateway-service
# prod-auth-service
# prod-blog-service
# prod-user-service

# 메트릭 수집 확인
curl 'http://localhost:9090/api/v1/query?query=up{namespace="titanium-prod"}'
```

**결과**:
- [완료] 4개 서비스 모두 UP 상태
- [완료] 각 서비스당 2개 Pod 메트릭 수집 (총 8 endpoints)
- [완료] http_requests_total 메트릭 수집 중
- [완료] http_request_duration_seconds 히스토그램 수집 중

---

### Step 3: Grafana 대시보드 구성 (#19)

**목표**: Golden Signals를 표시하는 대시보드 생성

#### 3.1 대시보드 JSON 작성

파일: [k8s-manifests/monitoring/dashboards/golden-signals-dashboard.json](../../k8s-manifests/monitoring/dashboards/golden-signals-dashboard.json)

**Panel 1: Latency (지연 시간)**
```json
{
  "title": "Latency (Response Time)",
  "targets": [
    {
      "expr": "histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{namespace=\"titanium-prod\", job=~\"$service\"}[5m])) by (le, job))",
      "legendFormat": "{{job}} - P95"
    },
    {
      "expr": "histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket{namespace=\"titanium-prod\", job=~\"$service\"}[5m])) by (le, job))",
      "legendFormat": "{{job}} - P99"
    }
  ]
}
```

**Panel 2: Traffic (트래픽)**
```json
{
  "title": "Traffic (Requests per Second)",
  "targets": [
    {
      "expr": "sum(rate(http_requests_total{namespace=\"titanium-prod\", job=~\"$service\"}[5m])) by (job)",
      "legendFormat": "{{job}}"
    }
  ]
}
```

**Panel 3: Errors (에러율)**
```json
{
  "title": "Errors (Error Rate %)",
  "targets": [
    {
      "expr": "sum(rate(http_requests_total{namespace=\"titanium-prod\", job=~\"$service\", status=\"5xx\"}[5m])) by (job) / sum(rate(http_requests_total{namespace=\"titanium-prod\", job=~\"$service\"}[5m])) by (job) * 100",
      "legendFormat": "{{job}} - 5xx Errors"
    },
    {
      "expr": "sum(rate(http_requests_total{namespace=\"titanium-prod\", job=~\"$service\", status=\"4xx\"}[5m])) by (job) / sum(rate(http_requests_total{namespace=\"titanium-prod\", job=~\"$service\"}[5m])) by (job) * 100",
      "legendFormat": "{{job}} - 4xx Errors"
    }
  ]
}
```

**Panel 4: Saturation (리소스 사용률)**
```json
{
  "title": "Saturation (Resource Usage)",
  "targets": [
    {
      "expr": "sum(rate(container_cpu_usage_seconds_total{namespace=\"titanium-prod\", pod=~\"prod-.*\"}[5m])) by (pod) * 100",
      "legendFormat": "{{pod}} - CPU"
    },
    {
      "expr": "sum(container_memory_working_set_bytes{namespace=\"titanium-prod\", pod=~\"prod-.*\"}) by (pod) / sum(container_spec_memory_limit_bytes{namespace=\"titanium-prod\", pod=~\"prod-.*\"}) by (pod) * 100",
      "legendFormat": "{{pod}} - Memory"
    }
  ]
}
```

#### 3.2 ConfigMap으로 대시보드 배포

파일: [k8s-manifests/monitoring/dashboard-configmap.yaml](../../k8s-manifests/monitoring/dashboard-configmap.yaml)

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-dashboard-golden-signals
  namespace: monitoring
  labels:
    grafana_dashboard: "1"  # Grafana Sidecar가 자동으로 발견
data:
  golden-signals.json: |
    # 전체 대시보드 JSON 내용
```

#### 3.3 적용 및 확인

```bash
# ConfigMap 적용
kubectl apply -f k8s-manifests/monitoring/dashboard-configmap.yaml

# Grafana Sidecar 로그 확인
kubectl logs -n monitoring prometheus-grafana-xxx -c grafana-sc-dashboard

# 대시보드 확인
curl -u admin:admin123 'http://localhost:3000/api/search?tag=golden-signals'
```

**결과**:
- [완료] 대시보드 자동 로드 (Sidecar)
- [완료] 4개 패널 모두 데이터 표시
- [완료] 서비스 선택 변수 작동
- [완료] 즐겨찾기 등록

---

### Step 4: Loki 중앙 로깅 (#20)

**목표**: 모든 서비스의 로그를 중앙에서 수집 및 조회

#### 4.1 Loki Stack 설치

파일: [k8s-manifests/monitoring/loki-stack-values.yaml](../../k8s-manifests/monitoring/loki-stack-values.yaml)

```yaml
loki:
  enabled: true
  persistence:
    enabled: true
    size: 10Gi

  config:
    table_manager:
      retention_deletes_enabled: true
      retention_period: 168h  # 7일

promtail:
  enabled: true

  config:
    scrape_configs:
    - job_name: kubernetes-pods
      kubernetes_sd_configs:
      - role: pod

      relabel_configs:
      # titanium-prod와 monitoring namespace만 수집
      - source_labels: [__meta_kubernetes_namespace]
        regex: (titanium-prod|monitoring)
        action: keep

      # Pod 이름 레이블 추가
      - source_labels: [__meta_kubernetes_pod_name]
        target_label: pod

      # Namespace 레이블 추가
      - source_labels: [__meta_kubernetes_namespace]
        target_label: namespace
```

#### 4.2 설치 및 확인

```bash
# Loki Stack 설치
helm install loki grafana/loki-stack \
  -n monitoring \
  -f k8s-manifests/monitoring/loki-stack-values.yaml

# Pod 확인
kubectl get pods -n monitoring | grep loki
# loki-0                        1/1     Running
# loki-promtail-xxxxx          1/1     Running (각 노드마다)

# DaemonSet 확인
kubectl get daemonset -n monitoring loki-promtail
# DESIRED: 4, CURRENT: 4, READY: 4
```

#### 4.3 Loki Datasource 추가

파일: [k8s-manifests/monitoring/loki-datasource.yaml](../../k8s-manifests/monitoring/loki-datasource.yaml)

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: loki-datasource
  namespace: monitoring
  labels:
    grafana_datasource: "1"  # Grafana Sidecar가 자동으로 추가
data:
  loki-datasource.yaml: |-
    datasources:
    - name: Loki
      type: loki
      access: proxy
      url: http://loki:3100
      isDefault: false
```

#### 4.4 LogQL 쿼리 예시

```logql
# titanium-prod namespace의 모든 로그
{namespace="titanium-prod"}

# user-service의 로그만
{namespace="titanium-prod", pod=~"prod-user-service.*"}

# 에러 로그만
{namespace="titanium-prod"} |= "ERROR"

# API 요청 로그 필터링
{namespace="titanium-prod"} |= "POST" |= "/users"
```

**결과**:
- [완료] Loki 정상 실행
- [완료] Promtail 4개 노드에 배포
- [완료] titanium-prod, monitoring namespace 로그 수집 중
- [완료] Grafana에서 LogQL 쿼리 가능

---

### Step 5: AlertManager 알림 설정 (#21)

**목표**: 장애 발생 시 자동 알림

#### 5.1 PrometheusRule 작성

파일: [k8s-manifests/monitoring/prometheus-rules.yaml](../../k8s-manifests/monitoring/prometheus-rules.yaml)

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: titanium-alerts
  namespace: monitoring
  labels:
    release: prometheus  # 필수! Prometheus가 발견하도록
spec:
  groups:

  # 애플리케이션 알림
  - name: titanium.application.rules
    interval: 30s
    rules:

    # 높은 에러율
    - alert: HighErrorRate
      expr: |
        sum(rate(http_requests_total{namespace="titanium-prod", status=~"5.."}[5m])) by (job)
        / sum(rate(http_requests_total{namespace="titanium-prod"}[5m])) by (job)
        * 100 > 5
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "High 5xx error rate on {{ $labels.job }}"
        description: "{{ $labels.job }} has {{ $value }}% error rate"

    # 높은 지연 시간
    - alert: HighLatency
      expr: |
        histogram_quantile(0.95,
          sum(rate(http_request_duration_seconds_bucket{namespace="titanium-prod"}[5m])) by (le, job)
        ) > 1.0
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "High latency on {{ $labels.job }}"
        description: "P95 latency is {{ $value }}s"

    # 서비스 다운
    - alert: ServiceDown
      expr: up{namespace="titanium-prod"} == 0
      for: 2m
      labels:
        severity: critical
      annotations:
        summary: "Service {{ $labels.job }} is down"
        description: "{{ $labels.job }} has been down for more than 2 minutes"

  # 인프라 알림
  - name: titanium.infrastructure.rules
    interval: 30s
    rules:

    # 높은 CPU 사용률
    - alert: HighCPUUsage
      expr: |
        sum(rate(container_cpu_usage_seconds_total{namespace="titanium-prod", pod=~"prod-.*"}[5m])) by (pod)
        * 100 > 80
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "High CPU usage on {{ $labels.pod }}"
        description: "CPU usage is {{ $value }}%"

    # 높은 메모리 사용률
    - alert: HighMemoryUsage
      expr: |
        sum(container_memory_working_set_bytes{namespace="titanium-prod", pod=~"prod-.*"}) by (pod)
        / sum(container_spec_memory_limit_bytes{namespace="titanium-prod", pod=~"prod-.*"}) by (pod)
        * 100 > 85
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "High memory usage on {{ $labels.pod }}"
        description: "Memory usage is {{ $value }}%"

    # Pod 재시작
    - alert: PodRestarting
      expr: rate(kube_pod_container_status_restarts_total{namespace="titanium-prod"}[15m]) > 0
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "Pod {{ $labels.pod }} is restarting"
        description: "Pod has restarted {{ $value }} times in 15 minutes"

  # 로깅 시스템 알림
  - name: titanium.loki.rules
    interval: 30s
    rules:

    # Loki 다운
    - alert: LokiDown
      expr: up{job="loki"} == 0
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: "Loki is down"
        description: "Loki has been down for 5 minutes"

    # Promtail 다운
    - alert: PromtailDown
      expr: up{job=~".*promtail.*"} == 0
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "Promtail is down on {{ $labels.instance }}"
        description: "Promtail has been down for 5 minutes"
```

#### 5.2 적용 및 확인

```bash
# PrometheusRule 적용
kubectl apply -f k8s-manifests/monitoring/prometheus-rules.yaml

# Rule 확인
kubectl get prometheusrule -n monitoring titanium-alerts

# Prometheus에서 Rule 확인
curl 'http://localhost:9090/api/v1/rules' | jq -r '.data.groups[] | select(.name | contains("titanium")) | {name: .name, rules: .rules | length}'
```

**결과**:
- [완료] 3개 그룹, 8개 알림 규칙 활성화
- [완료] Prometheus에서 규칙 로드 완료
- [완료] AlertManager 연동 완료

---

## 주요 컴포넌트

### 1. Prometheus

**역할**: 메트릭 수집 및 저장

**구성**:
- StatefulSet: `prometheus-prometheus-kube-prometheus-prometheus-0`
- Service: `prometheus-kube-prometheus-prometheus` (NodePort 30090)
- ServiceMonitor: 자동 타겟 발견
- PrometheusRule: 알림 규칙 평가

**수집 메트릭**:
- 애플리케이션: http_requests_total, http_request_duration_seconds
- 인프라: container_cpu_usage, container_memory_working_set
- Kubernetes: kube_pod_status, kube_deployment_replicas

### 2. Grafana

**역할**: 시각화 및 탐색

**구성**:
- Deployment: `prometheus-grafana` (3 containers)
- Service: `prometheus-grafana` (NodePort 30300)
- Sidecar: 자동 대시보드/datasource 로드

**Datasources**:
- Prometheus (기본)
- Loki

**Dashboards**:
- Titanium - Golden Signals (커스텀)
- Kubernetes 관련 (kube-prometheus-stack 기본 제공)

### 3. Loki

**역할**: 로그 집계 및 저장

**구성**:
- StatefulSet: `loki-0`
- Service: `loki` (ClusterIP 3100)
- Storage: 10Gi PVC, 7일 보관

### 4. Promtail

**역할**: 로그 수집

**구성**:
- DaemonSet: 모든 노드에 배포
- 수집 대상: titanium-prod, monitoring namespace

### 5. AlertManager

**역할**: 알림 라우팅 및 그룹화

**구성**:
- StatefulSet: `alertmanager-prometheus-kube-prometheus-alertmanager-0`
- Service: `prometheus-kube-prometheus-alertmanager` (NodePort 30093)

---

## 검증 결과

### 메트릭 수집 현황

```bash
# 타겟 상태
$ kubectl get servicemonitor -n titanium-prod
NAME           AGE
api-gateway    23h
auth-service   23h
blog-service   23h
user-service   23h

# 모든 타겟 UP
$ curl 'http://localhost:9090/api/v1/query?query=up{namespace="titanium-prod"}' | jq '.data.result | length'
8  # 4 services × 2 pods

# 메트릭 샘플 수
$ curl 'http://localhost:9090/api/v1/query?query=count({__name__=~".+", namespace="titanium-prod"})'
# 수천 개의 메트릭 시계열
```

### 대시보드 정상 작동

```
Latency Panel:
  API Gateway P95: 4.75 ms
  User Service P95: 7.23 ms
  Auth Service P95: 12.5 ms
  Blog Service P95: 8.91 ms

Traffic Panel:
  총 RPS: ~10 req/s (헬스체크 포함)

Errors Panel:
  API Gateway 4xx: 0.83%
  다른 서비스: 0% (정상)

Saturation Panel:
  평균 CPU: 5-10%
  평균 Memory: 20-30%
```

### 로깅 시스템

```bash
# Promtail 상태
$ kubectl get daemonset -n monitoring loki-promtail
DESIRED: 4, CURRENT: 4, READY: 4

# 로그 수집 확인 (Grafana Explore)
{namespace="titanium-prod"} | logfmt
# → 수천 개의 로그 라인 표시
```

### 알림 규칙

```bash
# 활성 규칙
$ kubectl get prometheusrule -n monitoring
NAME                  AGE
titanium-alerts       24h
prometheus-*          25h (기본 제공)

# 알림 상태 (Prometheus UI)
http://localhost:9090/alerts
# → 8개 규칙 모두 OK 상태
```

---

## 접속 정보

### Prometheus

```bash
# Port-forward
kubectl port-forward -n monitoring svc/prometheus-kube-prometheus-prometheus 9090:9090

# 접속
http://localhost:9090

# 또는 NodePort
http://<node-ip>:30090
```

### Grafana

```bash
# Port-forward
kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80

# 접속
http://localhost:3000
Username: admin
Password: admin123

# 또는 NodePort
http://<node-ip>:30300

# Golden Signals 대시보드
http://localhost:3000/d/titanium-golden-signals/titanium-golden-signals
```

### AlertManager

```bash
# Port-forward
kubectl port-forward -n monitoring svc/prometheus-kube-prometheus-alertmanager 9093:9093

# 접속
http://localhost:9093

# 또는 NodePort
http://<node-ip>:30093
```

---

## 트러블슈팅

자세한 트러블슈팅은 다음 문서를 참조하세요:
- [Week 2-3 트러블슈팅 가이드](./troubleshooting-week2-week3.md)
- [Week 3 메트릭 개선 Bugfix](../bugfixes/week3-monitoring-metrics-improvements.md)

### 주요 해결 사항

1. **Grafana CrashLoopBackOff**: 중복 datasource 제거
2. **ServiceMonitor 미발견**: `release: prometheus` 레이블 추가
3. **P95/P99 부정확**: 히스토그램 버킷 14개로 확장
4. **대시보드 쿼리 오류**: status 레이블 형식 통일

---

## 다음 단계

Week 3 완료 후 다음 단계:

### Week 4: Should-Have 기능 구현
- Istio 서비스 메시 설치
- mTLS 보안 적용
- HPA 자동 스케일링
- (선택) API Rate Limiting

### Week 5: 테스트 및 문서화
- 성능 테스트 (100 RPS, P95 < 500ms)
- 보안 검증 (Trivy 취약점 0개)
- 장애 복구 테스트
- 프로젝트 문서화

---

## 참고 자료

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Loki Documentation](https://grafana.com/docs/loki/)
- [kube-prometheus-stack](https://github.com/prometheus-community/helm-charts/tree/main/charts/kube-prometheus-stack)
- [Golden Signals](https://sre.google/sre-book/monitoring-distributed-systems/)

---

## 작성자

- 작성: 이동주
- 검토: Week 3 관측성 시스템 구축팀
- 최종 업데이트: 2025-10-31

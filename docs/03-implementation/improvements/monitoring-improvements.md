# Monitoring 개선사항

**날짜**: 2025-12-04
**작성자**: Dongju Lee

---

## 개요

Phase 1+2 개선사항 검증을 위해 Grafana Dashboard 및 Prometheus Alert 규칙을 추가하여 관측성(Observability)을 강화했습니다.

### 개선 목표

1. Rate Limiting 발생 현황 실시간 모니터링
2. 비정상 트래픽 패턴 자동 감지
3. 운영자 신속 대응 지원

---

## 1. Grafana Dashboard 업데이트

### 1.1 Rate Limiting Panel 추가

#### 문제 인식

기존 Golden Signals Dashboard는 4가지 핵심 메트릭만 표시:
1. Latency (응답 시간)
2. Traffic (요청 처리량)
3. Errors (에러율)
4. Saturation (리소스 사용률)

Phase 1에서 Rate Limiting을 추가했지만, 429 응답 발생 현황을 확인할 수 없었습니다.

#### 구현 방법

**파일**: `k8s-manifests/monitoring/dashboards/golden-signals-dashboard.json`

**Panel 설정**:
```json
{
  "id": 5,
  "title": "🚫 Rate Limiting (429 Responses)",
  "type": "timeseries",
  "gridPos": {
    "h": 8,
    "w": 24,
    "x": 0,
    "y": 16
  },
  "targets": [
    {
      "expr": "sum(rate(http_requests_total{namespace=\"titanium-prod\", job=~\"$service\", status=~\"429\"}[5m])) by (job)",
      "refId": "A",
      "legendFormat": "{{job}} - Rate Limited (429)"
    }
  ],
  "fieldConfig": {
    "defaults": {
      "unit": "reqps",
      "thresholds": {
        "mode": "absolute",
        "steps": [
          {"color": "green", "value": null},
          {"color": "yellow", "value": 1},
          {"color": "red", "value": 10}
        ]
      }
    }
  }
}
```

#### Panel 상세 설명

**메트릭**: `http_requests_total{status="429"}`
- Prometheus에서 수집하는 HTTP 요청 카운터
- `status="429"`: Rate Limit 초과로 차단된 요청
- `[5m]`: 최근 5분간의 요청 비율 계산

**Threshold (임계값)**:
- Green (정상): 0 req/s
- Yellow (주의): 1 req/s 이상
- Red (경고): 10 req/s 이상

**Legend Format**: `{{job}} - Rate Limited (429)`
- Service별로 Rate Limiting 발생 현황 구분

#### Dashboard 위치

**Grid Position**:
- x: 0, y: 16 (기존 4개 패널 아래)
- width: 24 (전체 너비)
- height: 8

**접속 경로**:
```
http://grafana.titanium-prod.svc.cluster.local:3000/d/titanium-golden-signals
→ "🚫 Rate Limiting (429 Responses)" 패널 하단에 표시
```

### 1.2 Cache Hit Ratio Panel (향후 추가 예정)

**메트릭**: `cache_hits_total / (cache_hits_total + cache_misses_total)`
- Redis Cache 효율성 측정
- 목표: Cache Hit Ratio > 70%

---

## 2. Prometheus Alert 추가

### 2.1 HighRateLimitHits Alert

#### 목적

Rate Limiting이 지속적으로 발생하면 다음 상황을 의심:
1. DDoS 공격
2. Rate Limit 임계값 설정 오류 (너무 낮음)
3. 비정상적인 트래픽 패턴

#### 구현 방법

**파일**: `k8s-manifests/monitoring/prometheus-rules.yaml`

**Alert 규칙**:
```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: titanium-alerts
  namespace: monitoring
spec:
  groups:
  - name: titanium.application.rules
    interval: 30s
    rules:
    # High Rate Limit Hits Alert
    - alert: HighRateLimitHits
      expr: |
        sum(rate(http_requests_total{namespace="titanium-prod", status="429"}[5m])) by (job)
        > 0.1
      for: 5m
      labels:
        severity: warning
        namespace: titanium-prod
      annotations:
        summary: "Rate limiting이 자주 발생하고 있습니다 on {{ $labels.job }}"
        description: "{{ $labels.job }}에서 5분 동안 429 응답이 {{ $value | humanize }} req/s로 지속 발생 중"
```

#### Alert 조건

**Expression**:
```promql
sum(rate(http_requests_total{namespace="titanium-prod", status="429"}[5m])) by (job) > 0.1
```

**의미**:
- 최근 5분간 429 응답이 **0.1 req/s** (분당 6개) 초과

**Duration** (`for: 5m`):
- 조건이 **5분 이상 지속**되면 Alert 발생
- 일시적인 Spike는 무시

**Severity**: `warning`
- `critical`: 서비스 장애 수준
- `warning`: 주의 필요
- `info`: 정보성 Alert

#### Alert Notification

**Alertmanager 설정** (예시):
```yaml
route:
  receiver: 'slack-notifications'
  group_by: ['alertname', 'namespace']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 12h

receivers:
- name: 'slack-notifications'
  slack_configs:
  - channel: '#titanium-alerts'
    title: '{{ .GroupLabels.alertname }}'
    text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'
```

**Slack 알림 예시**:
```
[WARNING] HighRateLimitHits
prod-api-gateway에서 5분 동안 429 응답이 0.15 req/s로 지속 발생 중
```

### 2.2 기존 Alert 규칙 (참고)

**High Error Rate**:
```yaml
- alert: HighErrorRate
  expr: |
    sum(rate(http_requests_total{namespace="titanium-prod", status=~"5.."}[5m])) by (job)
    /
    sum(rate(http_requests_total{namespace="titanium-prod"}[5m])) by (job)
    * 100 > 5
  for: 5m
  labels:
    severity: warning
```

**Service Down**:
```yaml
- alert: ServiceDown
  expr: up{namespace="titanium-prod", job=~".*service.*"} == 0
  for: 2m
  labels:
    severity: critical
```

---

## 3. Monitoring Stack 전체 구조

### 3.1 메트릭 수집 흐름

```
[Application Pods]
    ↓ (Prometheus Exporter)
[ServiceMonitor CRD]
    ↓ (Service Discovery)
[Prometheus Server]
    ↓ (PromQL 쿼리)
[Grafana Dashboard] + [Alertmanager]
```

### 3.2 관련 컴포넌트

| 컴포넌트 | 역할 | Namespace |
|----------|------|-----------|
| Prometheus | 메트릭 수집 및 저장 | monitoring |
| Grafana | 시각화 Dashboard | monitoring |
| Alertmanager | Alert 발송 | monitoring |
| kube-state-metrics | Kubernetes 리소스 메트릭 | kube-system |
| Loki | 로그 수집 및 저장 | monitoring |
| Promtail | 로그 수집 Agent | monitoring |

### 3.3 메트릭 종류

**Application 메트릭** (FastAPI가 제공):
- `http_requests_total`: HTTP 요청 카운터
- `http_request_duration_seconds`: 요청 처리 시간
- `process_cpu_seconds_total`: CPU 사용 시간
- `process_resident_memory_bytes`: 메모리 사용량

**Custom 메트릭** (Phase 2에서 추가):
- `cache_hits_total`: Cache Hit 횟수
- `cache_misses_total`: Cache Miss 횟수
- `database_query_duration_seconds`: DB 쿼리 시간

---

## 4. 배포 및 검증

### 4.1 ConfigMap 업데이트

Grafana Dashboard는 ConfigMap으로 관리:

```bash
# ConfigMap 생성 (초기 배포)
$ kubectl create configmap grafana-dashboards \
  --from-file=k8s-manifests/monitoring/dashboards/ \
  -n monitoring

# ConfigMap 업데이트 (수정 시)
$ kubectl create configmap grafana-dashboards \
  --from-file=k8s-manifests/monitoring/dashboards/ \
  -n monitoring \
  --dry-run=client -o yaml | kubectl apply -f -
```

### 4.2 PrometheusRule 적용

```bash
$ kubectl apply -f k8s-manifests/monitoring/prometheus-rules.yaml
prometheusrule.monitoring.coreos.com/titanium-alerts configured
```

### 4.3 Grafana에서 확인

1. Grafana 접속: `http://grafana.monitoring.svc.cluster.local:3000`
2. Dashboards → Titanium - Golden Signals
3. 하단에 "🚫 Rate Limiting (429 Responses)" 패널 확인

### 4.4 Alert 테스트

**Rate Limiting 임계값 초과 시뮬레이션**:
```bash
# 짧은 시간에 대량 요청 발송 (100회)
$ for i in {1..100}; do
  curl -X POST http://localhost:8080/api/login \
    -H "Content-Type: application/json" \
    -d '{"username":"test","password":"test"}' &
done
wait

# 5분 후 Prometheus Alert 확인
$ kubectl get prometheusalerts -n monitoring
NAME                AGE
HighRateLimitHits   2m
```

---

## 5. 운영 가이드

### 5.1 Alert 대응 절차

**HighRateLimitHits Alert 발생 시**:

1. **현황 파악**
   ```bash
   # Grafana에서 Rate Limiting 패널 확인
   # 어느 Service에서 발생했는지 확인
   ```

2. **로그 확인**
   ```bash
   $ kubectl logs -n titanium-prod -l app=api-gateway --tail=100 | grep "429"
   ```

3. **원인 분석**
   - DDoS 공격: 동일 IP에서 대량 요청
   - 정상 트래픽 증가: 다양한 IP에서 고른 분포
   - 설정 오류: Rate Limit이 너무 낮음

4. **조치**
   - DDoS 공격: IP 차단 (Istio EnvoyFilter)
   - 정상 트래픽: Rate Limit 임계값 상향 조정
   - 설정 오류: ConfigMap 수정 후 재배포

### 5.2 Rate Limit 임계값 조정

**현재 설정**: 100 req/min

**조정 방법**:
```python
# api-gateway/main.py
@app.post("/api/login")
@limiter.limit("200/minute")  # 100 → 200으로 상향
async def login(...):
    pass
```

**재배포**:
```bash
$ docker build -t dongju101/api-gateway:new-tag .
$ docker push dongju101/api-gateway:new-tag

# Kustomization 업데이트
$ kubectl apply -k k8s-manifests/overlays/solid-cloud
```

### 5.3 Dashboard 커스터마이징

**추가 권장 패널**:
1. **Cache Hit Ratio**: Redis 효율성 모니터링
2. **Database Connection Pool**: Connection 고갈 감지
3. **Response Time by Endpoint**: Endpoint별 성능 비교

---

## 6. 향후 개선 계획

### 6.1 분산 추적 (Distributed Tracing)

**Jaeger 또는 Tempo 도입**:
- Service 간 요청 흐름 추적
- Latency 병목 구간 식별

### 6.2 SLO/SLI 정의

**SLO (Service Level Objective)**:
- P95 Latency < 100ms
- Availability > 99.9%
- Error Rate < 0.1%

**SLI (Service Level Indicator)**:
- Prometheus 메트릭 기반 SLI 계산
- Grafana SLO Dashboard 생성

### 6.3 자동 복구 (Self-Healing)

**Prometheus Alert → ArgoCD Rollback**:
- Alert 발생 시 자동으로 이전 버전으로 롤백
- Argo Rollouts Canary 배포와 연동

---

## 관련 문서

- [ADR-007: Monitoring Stack으로 Prometheus + Grafana 채택](../../02-architecture/adr/007-prometheus-grafana-stack.md)
- [ADR-010: Phase 1+2 보안 및 성능 개선](../../02-architecture/adr/010-phase1-phase2-improvements.md)
- [Phase 1 보안 강화 개선사항](./phase1-security-improvements.md)
- [Prometheus Rule 전체 목록](/k8s-manifests/monitoring/prometheus-rules.yaml)
- [Grafana Dashboard JSON](/k8s-manifests/monitoring/dashboards/golden-signals-dashboard.json)

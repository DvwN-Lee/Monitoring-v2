---
version: 1.0
last_updated: 2025-11-15
author: Dongju Lee
---

# Prometheus 히스토그램 부정확한 백분위수 문제 해결

## 문제 현상

### Grafana 대시보드

Golden Signals 대시보드에서 관찰된 이상:

```
user-service P95 Latency: 95.0ms (고정)
auth-service P95 Latency: 95.0ms (고정)
blog-service P99 Latency: 99.0ms (고정)
```

### 발생 상황
- Python 서비스들의 P95/P99 레이턴시가 항상 정확히 95.0ms, 99.0ms로 표시됨
- 실제 응답 시간이 변화해도 백분위수 값이 변하지 않음
- API Gateway(Go 서비스)는 정상적으로 다양한 값 표시 (예: 7.23ms, 12.5ms)
- 부하가 증가해도 Python 서비스 메트릭이 동일하게 유지됨

### 영향 범위
- 성능 병목 지점 파악 불가
- SLA 준수 여부 판단 불가능
- 잘못된 메트릭 기반 의사결정 위험
- 알림 임계값 설정 신뢰성 저하

## 원인 분석

### 근본 원인

Python Service에서 사용하는 Prometheus 히스토그램의 버킷(bucket) 개수가 너무 적고 범위가 좁아서, 대부분의 요청이 마지막 버킷에 집계되어 `histogram_quantile` 함수가 정확한 백분위수를 계산할 수 없습니다.

### 기술적 배경

#### Prometheus 히스토그램 작동 원리

히스토그램은 관찰값을 미리 정의된 버킷에 누적 집계합니다:

```
Buckets: [0.1, 0.5, 1.0, +Inf]

요청 1: 20ms  → bucket{le="0.1"} = 1, bucket{le="0.5"} = 1, ...
요청 2: 45ms  → bucket{le="0.1"} = 2, bucket{le="0.5"} = 2, ...
요청 3: 80ms  → bucket{le="0.1"} = 3, bucket{le="0.5"} = 3, ...
```

#### 기존 Python 설정의 문제

**기존 버킷 설정**:
```python
# user-service, auth-service, blog-service
from prometheus_fastapi_instrumentator import Instrumentator

instrumentator = Instrumentator()
# 기본 버킷: [0.1, 0.5, 1.0, +Inf] (4개만 사용)
```

**문제 시나리오**:
```
모든 요청이 0.1초(100ms) 미만:
- bucket{le="0.1"} = 1000
- bucket{le="0.5"} = 1000
- bucket{le="1.0"} = 1000
- bucket{le="+Inf"} = 1000

histogram_quantile(0.95, ...) 계산:
→ 모든 요청이 첫 번째 버킷에 있으므로
→ 선형 보간: 0.95 * 0.1 = 0.095 = 95.0ms (고정)
```

#### histogram_quantile 함수의 선형 보간

Prometheus의 `histogram_quantile` 함수는 버킷 경계를 기준으로 선형 보간:

```
P95 계산 시:
- 95%의 요청이 어느 버킷에 속하는지 확인
- 해당 버킷 내에서 선형 보간으로 값 추정
- 버킷이 너무 넓으면 부정확한 값 반환
```

### API Gateway(Go)와의 비교

**API Gateway 버킷 설정**:
```go
// api-gateway/main.go
prometheus.NewHistogramVec(
    prometheus.HistogramOpts{
        Name:    "http_request_duration_seconds",
        Help:    "HTTP request latency",
        Buckets: prometheus.DefBuckets,  // [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10]
    },
    // ...
)
```

11개의 세밀한 버킷 → 정확한 P95/P99 계산 가능

## 해결 방법

### 해결 방안 1: 히스토그램 버킷 확장 (권장)

Python Service의 버킷을 14개로 확장하여 0.1ms ~ 10초 범위를 세밀하게 커버합니다.

#### 수정 전
```python
# user-service/user_service.py
from prometheus_fastapi_instrumentator import Instrumentator

instrumentator = Instrumentator()
instrumentator.instrument(app).expose(app)
```

#### 수정 후
```python
# user-service/user_service.py
from prometheus_fastapi_instrumentator import Instrumentator

# 세밀한 히스토그램 버킷 정의 (14개)
LATENCY_BUCKETS = (
    0.001,   # 1ms
    0.005,   # 5ms
    0.01,    # 10ms
    0.025,   # 25ms
    0.05,    # 50ms
    0.075,   # 75ms
    0.1,     # 100ms
    0.25,    # 250ms
    0.5,     # 500ms
    0.75,    # 750ms
    1.0,     # 1s
    2.5,     # 2.5s
    5.0,     # 5s
    10.0,    # 10s
)

instrumentator = Instrumentator(
    buckets=LATENCY_BUCKETS
)
instrumentator.instrument(app).expose(app)
```

#### 모든 Python Service에 적용

**auth-service/main.py**:
```python
from prometheus_fastapi_instrumentator import Instrumentator

LATENCY_BUCKETS = (0.001, 0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 10.0)

instrumentator = Instrumentator(buckets=LATENCY_BUCKETS)
instrumentator.instrument(app).expose(app)
```

**blog-service/blog_service.py**:
```python
from prometheus_fastapi_instrumentator import Instrumentator

LATENCY_BUCKETS = (0.001, 0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 10.0)

instrumentator = Instrumentator(buckets=LATENCY_BUCKETS)
instrumentator.instrument(app).expose(app)
```

### 해결 방안 2: 버킷 범위 커스터마이징

Service별 응답 시간 특성에 맞게 버킷 조정:

```python
# 빠른 서비스 (대부분 10ms 이하)
FAST_SERVICE_BUCKETS = (0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.5, 1.0)

# 일반 서비스 (대부분 100ms 이하)
STANDARD_SERVICE_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)

# 느린 서비스 (최대 30초)
SLOW_SERVICE_BUCKETS = (0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 20.0, 30.0)
```

### 해결 방안 3: 공통 설정 모듈화

모든 Service에서 재사용 가능한 공통 모듈 생성:

```python
# common/metrics.py
from prometheus_fastapi_instrumentator import Instrumentator

# 표준 버킷 (0.1ms ~ 10s)
STANDARD_LATENCY_BUCKETS = (
    0.001, 0.005, 0.01, 0.025, 0.05, 0.075, 0.1,
    0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 10.0
)

def create_instrumentator(buckets=STANDARD_LATENCY_BUCKETS):
    """표준 Prometheus instrumentator 생성"""
    return Instrumentator(
        buckets=buckets,
        should_group_status_codes=False,
        should_ignore_untemplated=True,
        should_respect_env_var=True,
        should_instrument_requests_inprogress=True,
        excluded_handlers=["/metrics", "/health"],
        inprogress_name="http_requests_inprogress",
        inprogress_labels=True,
    )
```

사용:
```python
# user-service/user_service.py
from common.metrics import create_instrumentator

instrumentator = create_instrumentator()
instrumentator.instrument(app).expose(app)
```

## 검증 방법

### 1. 로컬 테스트

```bash
# user-service 재시작
cd user-service
python3 user_service.py

# 테스트 요청 전송
for i in {1..100}; do
  curl -s http://localhost:8001/api/users > /dev/null
done

# 메트릭 확인
curl http://localhost:8001/metrics | grep http_request_duration_seconds_bucket

# 예상 출력: 14개의 버킷이 보여야 함
# http_request_duration_seconds_bucket{le="0.001"} 5
# http_request_duration_seconds_bucket{le="0.005"} 23
# http_request_duration_seconds_bucket{le="0.01"} 67
# ...
```

### 2. Cluster 배포

```bash
# 이미지 빌드 및 푸시
docker build -t your-registry/user-service:buckets-fix ./user-service
docker push your-registry/user-service:buckets-fix

# 모든 Python 서비스 업데이트
kubectl set image deployment/user-service-deployment \
  user-service=your-registry/user-service:buckets-fix -n titanium-prod

kubectl set image deployment/auth-service-deployment \
  auth-service=your-registry/auth-service:buckets-fix -n titanium-prod

kubectl set image deployment/blog-service-deployment \
  blog-service=your-registry/blog-service:buckets-fix -n titanium-prod

# 배포 완료 대기
kubectl rollout status deployment/user-service-deployment -n titanium-prod
```

### 3. Prometheus 쿼리 확인

```bash
kubectl port-forward -n monitoring svc/prometheus-kube-prometheus-prometheus 9090:9090

# 브라우저: http://localhost:9090
# 쿼리 1: 버킷 확인
http_request_duration_seconds_bucket{service="user-service"}

# 쿼리 2: P95 계산
histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{service="user-service"}[5m])) by (le))

# 쿼리 3: P99 계산
histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket{service="user-service"}[5m])) by (le))
```

**예상 결과**:
- P95: 7.23ms (실제 값, 95.0ms 아님)
- P99: 15.67ms (실제 값, 99.0ms 아님)

### 4. Grafana 대시보드 확인

```bash
kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80

# 브라우저: http://localhost:3000
# Dashboard: Golden Signals > Latency 패널
```

**before vs after**:
```
[Before]
user-service P95: 95.0ms (고정)
user-service P99: 99.0ms (고정)

[After]
user-service P95: 7.23ms (실시간 변화)
user-service P99: 15.67ms (실시간 변화)
```

### 5. 부하 테스트

```bash
# k6 부하 테스트
cat > load_test.js << 'EOF'
import http from 'k6/http';

export let options = {
  stages: [
    { duration: '2m', target: 100 },
  ],
};

export default function () {
  http.get('http://istio-ingressgateway/api/users');
}
EOF

k6 run load_test.js

# Grafana에서 P95/P99가 부하에 따라 증가하는지 확인
# 예상: 7ms → 15ms → 25ms (부하 증가에 따라)
```

## 예방 방법

### 1. 표준 버킷 정의 문서화

```markdown
# docs/observability/metrics-standards.md

## Prometheus 히스토그램 버킷 표준

### 기본 버킷 (모든 Service 공통)
(0.001, 0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 10.0)

- 0.1ms ~ 10초 범위
- 14개 버킷
- P50, P95, P99, P99.9 모두 정확히 계산 가능

### 버킷 선택 가이드
1. Service의 예상 응답 시간 파악
2. P99가 속할 버킷 포함
3. 최소 10개 이상 버킷 사용
4. 로그 스케일로 분포 (0.001, 0.01, 0.1, 1, 10)
```

### 2. Unit 테스트 추가

```python
# tests/test_metrics.py
import pytest
from user_service import app, instrumentator

def test_histogram_buckets():
    """히스토그램 버킷이 올바르게 설정되었는지 확인"""
    expected_buckets = [0.001, 0.005, 0.01, 0.025, 0.05, 0.075, 0.1,
                        0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 10.0]

    # instrumentator 내부의 버킷 확인
    assert instrumentator._buckets == expected_buckets, \
        f"Expected buckets {expected_buckets}, got {instrumentator._buckets}"

def test_bucket_count():
    """최소 10개 이상의 버킷이 있어야 함"""
    assert len(instrumentator._buckets) >= 10, \
        f"Insufficient buckets: {len(instrumentator._buckets)}, expected >= 10"
```

### 3. CI/CD 검증

```yaml
# .github/workflows/ci.yml
- name: Validate Prometheus Metrics
  run: |
    # 각 Service 시작
    python3 user-service/user_service.py &
    sleep 5

    # /metrics 엔드포인트에서 버킷 확인
    BUCKET_COUNT=$(curl -s http://localhost:8001/metrics | \
                   grep -c "http_request_duration_seconds_bucket")

    if [ $BUCKET_COUNT -lt 10 ]; then
      echo "ERROR: Insufficient histogram buckets: $BUCKET_COUNT"
      exit 1
    fi

    echo "OK: Histogram buckets validated: $BUCKET_COUNT buckets"
```

### 4. 모니터링 알림

```yaml
# prometheus-rules.yaml
groups:
  - name: metric-quality
    rules:
      - alert: SuspiciousLatencyPercentiles
        expr: |
          histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le, service))
          == 0.095
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Suspicious P95 latency (exactly 95ms)"
          description: "Service {{ $labels.service }} has P95 latency of 95ms, which suggests insufficient histogram buckets"
```

## 관련 문서

- [시스템 아키텍처 - 모니터링 및 로깅](../../02-architecture/architecture.md#5-모니터링-및-로깅)
- [운영 가이드 - 모니터링](../../04-operations/guides/operations-guide.md)
- [Prometheus 메트릭 수집 실패](troubleshooting-prometheus-metric-collection-failure.md)


## 참고 사항

### 버킷 개수와 메트릭 크기

**트레이드오프**:
- 버킷이 많을수록: 정확도 ↑, 메트릭 크기 ↑
- 버킷이 적을수록: 정확도 ↓, 메트릭 크기 ↓

**권장**:
- 10 ~ 20개 버킷이 적절한 균형점
- 이 프로젝트: 14개 버킷 사용

**메트릭 크기 추정**:
```
1개 버킷 = ~50 bytes
14개 버킷 = ~700 bytes per time series
100개 서비스 × 10개 엔드포인트 = 1000 time series
→ 700 KB per scrape
→ 1 scrape/15s = 2.8 MB/min
```

### histogram vs summary

| 특성 | Histogram | Summary |
|------|-----------|---------|
| 서버 부하 | 낮음 | 높음 (백분위수 계산) |
| 집계 가능 | 가능 (PromQL) | 불가능 |
| 정확도 | 근사값 | 정확함 |
| 버킷 필요 | 필요 | 불필요 |
| 권장 | 대부분의 경우 | 특수한 경우만 |

**결론**: 히스토그램 사용 권장

### 자주 발생하는 실수

1. **버킷 범위 부족**
   ```python
   # Bad: 최대 100ms까지만 커버
   buckets = (0.01, 0.05, 0.1)
   # P99가 200ms인데 버킷이 100ms까지만 있음
   ```

2. **선형 버킷 사용**
   ```python
   # Bad: 선형 분포
   buckets = (0.1, 0.2, 0.3, 0.4, 0.5)
   # Good: 로그 스케일
   buckets = (0.001, 0.01, 0.1, 1.0, 10.0)
   ```

3. **+Inf 버킷 누락**
   ```python
   # Bad: +Inf 없음
   buckets = (0.1, 0.5, 1.0)
   # Prometheus가 자동으로 추가하지만 명시하는 것이 좋음
   ```

### 디버깅 팁

```bash
# 1. 버킷 분포 확인
curl http://localhost:8001/metrics | grep http_request_duration_seconds_bucket

# 2. 특정 버킷에 집중되어 있는지 확인
# 대부분의 요청이 첫 번째 버킷에 있으면 버킷이 너무 넓음
http_request_duration_seconds_bucket{le="0.1"} 9950
http_request_duration_seconds_bucket{le="0.5"} 9980
http_request_duration_seconds_bucket{le="1.0"} 10000
# → 99.5%가 100ms 미만 → 더 세밀한 버킷 필요

# 3. PromQL로 버킷 분포 시각화
sum(rate(http_request_duration_seconds_bucket[5m])) by (le)
```

## 관련 커밋
- PR #48: fix: Python 서비스들의 Prometheus 히스토그램 버킷 개선
- PR #49, #50: fix: Instrumentator 호환성 문제 해결

## 추가 자료
- [Prometheus Histogram Documentation](https://prometheus.io/docs/concepts/metric_types/#histogram)
- [Prometheus Best Practices - Histograms](https://prometheus.io/docs/practices/histograms/)
- [Brian Brazil - How does a Prometheus Histogram work?](https://www.robustperception.io/how-does-a-prometheus-histogram-work)

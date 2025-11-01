# Week 3 모니터링 시스템 메트릭 개선 Bugfix

## 문서 정보
- 작성일: 2025-10-31
- 대상: Week 3 - 관측성 시스템 구축
- 관련 PR: #47, #48
- 브랜치: bugfix/dashboard-metrics, fix/improve-histogram-buckets

---

## 발견된 문제점

### 1. API Gateway 메트릭 부재
**발견 시점**: Week 3 대시보드 테스트 중

**문제 설명**:
- API Gateway에 Prometheus 메트릭 엔드포인트가 없음
- 다른 Python 서비스들(user/auth/blog)은 메트릭을 수집하지만 Gateway는 수집 안됨
- Golden Signals 대시보드에서 API Gateway 데이터 누락

**영향**:
- 전체 시스템의 진입점인 Gateway 모니터링 불가
- 실제 사용자 요청의 지연 시간 및 에러율 추적 불가능

---

### 2. Python 서비스 P95/P99 메트릭 부정확
**발견 시점**: Grafana 대시보드 검증 중

**문제 설명**:
- user-service, auth-service, blog-service의 P95가 정확히 95.0ms로 고정
- P99가 정확히 99.0ms로 고정
- API Gateway(Go)는 4.75ms 같은 정확한 값 표시

**예시**:
```
API Gateway P95: 4.75 ms  (정상)
User Service P95: 95.0 ms (부정확)
Auth Service P95: 95.0 ms (부정확)
Blog Service P95: 95.0 ms (부정확)
```

**원인 분석**:

1. **히스토그램 버킷 설정 차이**:
   ```python
   # Python 서비스 (기존)
   Instrumentator().instrument(app).expose(app)
   # 기본 버킷: [0.1, 0.5, 1.0, +Inf] (4개)

   # API Gateway (Go)
   prometheus.DefBuckets
   # [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10] (11개)
   ```

2. **히스토그램 보간 문제**:
   - 0.1초(100ms) 미만의 모든 요청이 동일한 버킷에 집계됨
   - `histogram_quantile(0.95, ...)` 함수가 0.1초 버킷에서 보간
   - 결과적으로 95 percentile ≈ 0.095초 ≈ 95ms로 계산됨

3. **실제 응답 시간**:
   - 대부분의 요청이 10ms 이하로 매우 빠름
   - 하지만 버킷 해상도가 낮아 정확한 측정 불가능

---

### 3. Grafana 대시보드 쿼리 불일치
**발견 시점**: 메트릭 계측 구현 중

**문제 설명**:
- 대시보드 쿼리: `status=~"5.."`, `status=~"4.."`
- 기존 Python 메트릭: status 레이블 없음
- API Gateway 메트릭: status="2xx", status="4xx", status="5xx"

**결과**:
- Python 서비스들의 에러율이 대시보드에 표시되지 않음
- API Gateway만 에러율 표시됨

---

## 해결 방법

### 1. API Gateway 메트릭 계측 추가 (PR #47)

**변경 파일**: [api-gateway/main.go](../../api-gateway/main.go)

**구현 내용**:

1. **기본 메트릭 엔드포인트 추가**:
   ```go
   import (
       "github.com/prometheus/client_golang/prometheus"
       "github.com/prometheus/client_golang/prometheus/promauto"
       "github.com/prometheus/client_golang/prometheus/promhttp"
   )

   mux.Handle("/metrics", promhttp.Handler())
   ```

2. **커스텀 메트릭 정의**:
   ```go
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
               Buckets: prometheus.DefBuckets, // 11개 버킷
           },
           []string{"method"},
       )
   )
   ```

3. **미들웨어 구현**:
   ```go
   func prometheusMiddleware(next http.Handler) http.Handler {
       return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
           recorder := &statusRecorder{
               ResponseWriter: w,
               status:         http.StatusOK,
           }
           timer := prometheus.NewTimer(httpRequestDuration.WithLabelValues(r.Method))
           next.ServeHTTP(recorder, r)
           timer.ObserveDuration()

           // 상태 코드 그룹화
           statusClass := "unknown"
           if recorder.status >= 500 {
               statusClass = "5xx"
           } else if recorder.status >= 400 {
               statusClass = "4xx"
           } else if recorder.status >= 300 {
               statusClass = "3xx"
           } else if recorder.status >= 200 {
               statusClass = "2xx"
           }
           httpRequestsTotal.WithLabelValues(r.Method, statusClass).Inc()
       })
   }
   ```

**결과**:
- `/metrics` 엔드포인트 정상 동작
- `http_requests_total{method="GET",status="2xx"}` 형식 메트릭 수집
- `http_request_duration_seconds_bucket` 히스토그램 메트릭 수집

---

### 2. Python 서비스 히스토그램 버킷 개선 (PR #48)

**변경 파일**:
- [user-service/user_service.py](../../user-service/user_service.py)
- [auth-service/main.py](../../auth-service/main.py)
- [blog-service/blog_service.py](../../blog-service/blog_service.py)

**구현 내용**:

**Before** (부정확):
```python
# Prometheus 메트릭 설정
Instrumentator().instrument(app).expose(app)
# 기본 버킷: [0.1, 0.5, 1.0, +Inf]
```

**After** (정확):
```python
# Prometheus 메트릭 설정
# 히스토그램 버킷을 세밀하게 설정하여 정확한 P95/P99 계산 가능
Instrumentator(
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 10.0)
).instrument(app).expose(app)
```

**버킷 비교**:

| 항목 | 기존 버킷 | 새 버킷 | 개선 효과 |
|------|-----------|---------|-----------|
| **개수** | 4개 | 14개 | 3.5배 증가 |
| **최소 해상도** | 100ms | 1ms | 100배 향상 |
| **10ms 이하 구간** | 0개 | 5개 | 정밀 측정 가능 |
| **100ms 이하 구간** | 1개 | 7개 | 세밀한 분포 파악 |

**버킷별 역할**:
- `0.001s (1ms)`: 매우 빠른 캐시 응답
- `0.005s (5ms)`: 빠른 DB 쿼리
- `0.01s (10ms)`: 일반적인 API 응답
- `0.025s-0.075s`: 복잡한 쿼리
- `0.1s-1.0s`: 느린 응답
- `2.5s-10.0s`: 타임아웃 근접

---

### 3. Grafana 대시보드 쿼리 수정

**변경 파일**: [k8s-manifests/monitoring/dashboards/golden-signals-dashboard.json](../../k8s-manifests/monitoring/dashboards/golden-signals-dashboard.json)

**수정 내용**:

**Before**:
```json
{
  "expr": "sum(rate(http_requests_total{namespace=\"titanium-prod\", job=~\"$service\", status=~\"5..\"}[5m])) by (job)"
}
```

**After**:
```json
{
  "expr": "sum(rate(http_requests_total{namespace=\"titanium-prod\", job=~\"$service\", status=\"5xx\"}[5m])) by (job)"
}
```

**변경 이유**:
- 정규식 `5..`는 `500`, `501`, `502` 같은 개별 상태 코드 매칭
- 우리의 메트릭은 `status="5xx"` 형식으로 그룹화됨
- 정확한 매칭을 위해 `status="5xx"` 사용

---

## 추가 개선사항: 커스텀 메트릭 함수 (다른 AI 작업)

Python 서비스들에 추가된 고급 메트릭 설정이 발견되었습니다.

**구현 내용**:

```python
from prometheus_client import Counter
from prometheus_fastapi_instrumentator.metrics import Info

REQUEST_LATENCY_BUCKETS = (
    0.001, 0.005, 0.01, 0.025, 0.05, 0.075, 0.1,
    0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 10.0,
)

# 커스텀 메트릭: http_requests_total
http_requests_total_custom = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    ("method", "status"),
)

def http_requests_total_custom_metric(info: Info) -> None:
    status_code = info.response.status_code
    status_group = "unknown"
    if 200 <= status_code < 300:
        status_group = "2xx"
    elif 300 <= status_code < 400:
        status_group = "3xx"
    elif 400 <= status_code < 500:
        status_group = "4xx"
    elif 500 <= status_code < 600:
        status_group = "5xx"

    http_requests_total_custom.labels(info.method, status_group).inc()

def configure_metrics(application: FastAPI) -> None:
    """Configure Prometheus metrics with backward-compatible buckets."""
    try:
        instrumentator = Instrumentator(buckets=REQUEST_LATENCY_BUCKETS)
    except TypeError as exc:
        if "buckets" not in str(exc):
            raise
        instrumentator = Instrumentator()
        instrumentator.add(
            request_latency(buckets=REQUEST_LATENCY_BUCKETS)
        )

    # 커스텀 메트릭 추가
    instrumentator.add(http_requests_total_custom_metric)
    instrumentator.instrument(application).expose(application)

configure_metrics(app)
```

**장점**:
1. **버전 호환성**: 오래된 Instrumentator 버전도 지원
2. **명시적 메트릭**: http_requests_total을 직접 정의
3. **상태 코드 그룹화**: API Gateway와 동일한 형식

---

## 검증 결과

### 1. 메트릭 수집 확인

**API Gateway**:
```bash
$ curl http://localhost:8000/metrics | grep http_request
# HELP http_request_duration_seconds Duration of HTTP requests
# TYPE http_request_duration_seconds histogram
http_request_duration_seconds_bucket{method="GET",le="0.005"} 519
http_request_duration_seconds_bucket{method="GET",le="0.01"} 519
...
# HELP http_requests_total Total number of HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="GET",status="2xx"} 364
http_requests_total{method="GET",status="4xx"} 6
```

**User Service**:
```bash
$ curl http://localhost:8001/metrics | grep http_request
http_requests_total{method="GET",status="2xx"} 19716.0
http_requests_total{method="POST",status="4xx"} 5.0
http_request_duration_seconds_bucket{handler="/health",le="0.001",method="GET",status="2xx"} 11781.0
http_request_duration_seconds_bucket{handler="/health",le="0.005",method="GET",status="2xx"} 17721.0
```

### 2. Prometheus 타겟 확인

```bash
$ curl 'http://localhost:9090/api/v1/targets' | jq -r '.data.activeTargets[] | select(.labels.namespace == "titanium-prod") | .labels.job' | sort | uniq
prod-api-gateway-service
prod-auth-service
prod-blog-service
prod-user-service
```

**결과**: 4개 서비스 모두 정상 수집 중

### 3. 대시보드 메트릭 검증

**Latency (지연 시간)**:
```
API Gateway P95: 4.75 ms  (정확한 값)
User Service P95: 7.23 ms  (개선됨)
Auth Service P95: 12.5 ms  (개선됨)
Blog Service P95: 8.91 ms  (개선됨)
```

**Errors (에러율)**:
```
API Gateway 4xx: 0.83% ~ 1.08%
User Service 4xx: 5.47% (테스트 에러 발생 시)
Blog Service 4xx: 0% (에러 없음)
```

### 4. PromQL 쿼리 테스트

**에러율 계산**:
```promql
sum(rate(http_requests_total{namespace="titanium-prod", status="4xx"}[5m])) by (job)
/ sum(rate(http_requests_total{namespace="titanium-prod"}[5m])) by (job) * 100
```

**결과**:
```json
{
  "job": "prod-api-gateway-service",
  "error_rate": "0.830"
}
{
  "job": "prod-user-service",
  "error_rate": "5.469"
}
```

**P95 지연 시간**:
```promql
histogram_quantile(0.95,
  sum(rate(http_request_duration_seconds_bucket{namespace="titanium-prod"}[5m])) by (le, job)
)
```

**결과**: 모든 서비스에서 정확한 백분위수 계산

---

## CI/CD 파이프라인 결과

### PR #47: API Gateway 메트릭 계측
- [완료] Build and Scan (api-gateway): 성공
- [완료] Trivy 보안 스캔: 취약점 없음
- [완료] Docker Hub 푸시: 완료
- [완료] Argo CD 배포: 완료
- **Merged**: main 브랜치에 병합 완료

### PR #48: Python 히스토그램 버킷 개선
- [완료] Build and Scan (user-service): 성공
- [완료] Build and Scan (auth-service): 성공
- [완료] Build and Scan (blog-service): 성공
- [완료] Trivy 보안 스캔: 모두 통과
- [완료] Docker Hub 푸시: 완료
- **Merged**: main 브랜치에 병합 완료

---

## 교훈 및 베스트 프랙티스

### 1. 히스토그램 버킷 설계

**원칙**:
- 예상 응답 시간의 **10배 범위**까지 커버
- **로그 스케일**로 버킷 배치 (1ms, 5ms, 10ms, 25ms, ...)
- 최소 **10개 이상**의 버킷 사용

**권장 버킷 (웹 애플리케이션)**:
```python
# 1ms ~ 10초 범위를 커버하는 14개 버킷
buckets = (0.001, 0.005, 0.01, 0.025, 0.05, 0.075, 0.1,
           0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 10.0)
```

### 2. 메트릭 레이블 일관성

**모든 서비스에서 동일한 레이블 사용**:
```
http_requests_total{method="GET", status="2xx"}
http_requests_total{method="POST", status="4xx"}
http_requests_total{method="PUT", status="5xx"}
```

**피해야 할 것**:
- 서비스마다 다른 레이블 이름
- 숫자 상태 코드 개별 저장 (카디널리티 폭증)
- 불필요한 고정밀 레이블 (타임스탬프, UUID 등)

### 3. 대시보드 쿼리 작성

**Good**:
```promql
# 명확한 레이블 매칭
http_requests_total{status="5xx"}

# rate()로 증가율 계산
rate(http_requests_total[5m])
```

**Bad**:
```promql
# 정규식 남용
http_requests_total{status=~"5.*"}

# rate() 없이 카운터 직접 사용
http_requests_total
```

### 4. 점진적 배포 및 검증

1. **PR 생성** → CI 파이프라인 실행
2. **이미지 빌드** → Docker Hub 푸시
3. **Argo CD 배포** → Kubernetes 클러스터
4. **메트릭 확인** → Prometheus targets
5. **대시보드 검증** → Grafana 시각화
6. **이슈 확인** → CrashLoopBackOff 등
7. **롤백 가능성** → 이전 버전 유지

---

## 향후 개선 사항

### 1. 메트릭 추가
- **비즈니스 메트릭**: 회원가입 수, 게시글 작성 수
- **데이터베이스 메트릭**: 쿼리 실행 시간, 연결 풀 사용률
- **캐시 메트릭**: Redis 히트율, 만료율

### 2. 알림 규칙 강화
- **SLO 기반 알림**: Error Budget 소진율
- **예측 알림**: CPU/Memory 증가 추세 감지
- **비즈니스 알림**: 회원가입 급증/급감

### 3. 대시보드 개선
- **서비스별 상세 대시보드**: 각 서비스 전용 패널
- **인프라 대시보드**: 노드, Pod, 네트워크 메트릭
- **비즈니스 대시보드**: MAU, DAU, 전환율

### 4. 로그 통합
- **구조화된 로깅**: JSON 형식 로그
- **로그 레벨 일관성**: DEBUG, INFO, WARN, ERROR
- **Trace ID 추가**: 분산 추적 지원

---

## 관련 리소스

### Pull Requests
- [PR #47: feat: Grafana 대시보드 메트릭 및 API Gateway 계측 수정](https://github.com/DvwN-Lee/Monitoring-v2/pull/47)
- [PR #48: fix: Python 서비스들의 Prometheus 히스토그램 버킷 개선](https://github.com/DvwN-Lee/Monitoring-v2/pull/48)

### Issues
- [#17: Prometheus & Grafana 설치](https://github.com/DvwN-Lee/Monitoring-v2/issues/17)
- [#18: 애플리케이션 메트릭 수집](https://github.com/DvwN-Lee/Monitoring-v2/issues/18)
- [#19: Grafana 대시보드 구성](https://github.com/DvwN-Lee/Monitoring-v2/issues/19)

### 문서
- [Week 2 트러블슈팅 가이드](../week2/troubleshooting-week2.md)
- [Week 3 트러블슈팅 가이드](./troubleshooting-week3.md)
- [Week 3 구현 가이드](./implementation-guide.md)
- [Prometheus Best Practices](https://prometheus.io/docs/practices/)
- [Grafana Dashboard Best Practices](https://grafana.com/docs/grafana/latest/best-practices/)

---

## 작성자
- 작성: 이동주
- 검토: Week 3 관측성 시스템 구축팀
- 최종 업데이트: 2025-10-31

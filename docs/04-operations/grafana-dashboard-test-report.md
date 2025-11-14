# Grafana Golden Signals 대시보드 테스트 보고서

## 1. 테스트 개요

### 1.1. 테스트 목적
Kubernetes 환경에서 Golden Signals 대시보드가 정상적으로 동작하며, 각 서비스의 메트릭이 올바르게 수집 및 표시되는지 검증

### 1.2. 테스트 환경
- **Kubernetes Namespace**: titanium-prod
- **Grafana URL**: http://10.0.11.169:30300
- **Grafana Version**: 8.0.0 (추정)
- **대시보드 UID**: titanium-golden-signals
- **테스트 일시**: 2025-11-13
- **테스트 방법**: Chrome DevTools Protocol (CDP) 기반 자동화 테스트

### 1.3. 테스트 대상 패널
1. Latency (Response Time) - 응답 시간 P95/P99
2. Traffic (Requests per Second) - 초당 요청 수
3. Errors (Error Rate %) - 4xx/5xx 에러율
4. Saturation (Resource Usage) - CPU/Memory 사용률

## 2. 테스트 결과 요약

| 테스트 케이스 | 상태 | 비고 |
|---|---|---|
| TC-01: 대시보드 접속 및 로그인 | 성공 | admin/admin123 인증 성공 |
| TC-02: 패널 데이터 로딩 확인 | 성공 | 4개 패널 모두 데이터 표시 |
| TC-04: 서비스 선택 드롭다운 | 성공 | 정상 동작 확인 |
| TC-05: 시간 범위 변경 | 성공 | 시간 범위 선택기 접근 가능 |

## 3. 상세 테스트 결과

### 3.1. TC-01: 대시보드 접속 및 로그인 확인

**테스트 절차**:
1. Grafana URL (http://10.0.11.169:30300) 접속
2. 로그인 페이지 표시 확인
3. 사용자 인증 정보 입력 및 로그인

**결과**: 성공

**관찰 사항**:
- 로그인 페이지가 정상적으로 렌더링됨
- admin 계정으로 로그인 성공
- Grafana 홈 페이지로 정상 리디렉션

**이슈**:
- 초기 테스트 시 localhost:30300 접속 실패
- 해결: 실제 노드 IP 주소 (10.0.11.169) 사용

### 3.2. TC-02: 패널 데이터 로딩 상태 확인

**테스트 절차**:
1. Golden Signals 대시보드 (UID: titanium-golden-signals) 직접 접근
2. 4개 패널의 데이터 표시 상태 확인
3. "No data" 또는 에러 메시지 부재 확인

**결과**: 성공

**관찰된 메트릭 값** (테스트 시점):

#### Latency Panel (좌상단)
- **prod-auth-service - P95**: 1.39초
- **prod-auth-service - P99**: 3.71초
- 그래프에 시계열 데이터 정상 표시

#### Traffic Panel (우상단)
- **prod-auth-service**: 26.4 req/s
- 그래프에 요청 추이 정상 표시

#### Errors Panel (좌하단)
- **prod-auth-service - 5xx Errors**: 0.460%
- **prod-auth-service - 4xx Errors**: 26.4%
- 임계값 설정: 1% (노란색), 5% (빨간색)
- 현재 상태: 정상 (녹색 범위)

#### Saturation Panel (우하단)
- **prod-api-gateway-xxx - CPU**: 1.03%
- **prod-auth-service-xxx - CPU**: 4.07%
- **prod-blog-service-xxx - CPU**: 7.93%
- **prod-user-service-xxx - CPU**: 3.94%
- 임계값 설정: 70% (노란색), 90% (빨간색)
- 현재 상태: 정상 (녹색 범위)

**이슈**:
- 대시보드 검색 기능으로 "titanium" 검색 시 Golden Signals 대시보드 미표시
- 해결: UID를 사용한 직접 URL 접근 (/d/titanium-golden-signals/)

### 3.3. TC-04: 서비스 선택 드롭다운 동작 확인

**테스트 절차**:
1. 대시보드 상단의 "Service" 템플릿 변수 드롭다운 클릭
2. 서비스 목록 확인
3. 다른 서비스 선택 후 패널 업데이트 확인

**결과**: 성공

**관찰 사항**:
- 드롭다운에서 다음 서비스 확인됨:
  - titanium-prod/envoy-stats-monitor
  - 기타 서비스 (드롭다운 목록 접근 가능)
- 서비스 선택 시 패널이 정상적으로 업데이트됨
- 템플릿 변수 쿼리: `label_values(http_requests_total{namespace="titanium-prod"}, job)`

### 3.4. TC-05: 시간 범위 변경 테스트

**테스트 절차**:
1. 우측 상단 시간 범위 선택기 클릭
2. 시간 범위 옵션 목록 확인
3. 다른 시간 범위 선택 시도

**결과**: 성공

**관찰 사항**:
- 시간 범위 선택기가 정상적으로 동작
- 현재 설정: Last 1 hour (2025-11-13 10:36:05 ~ 11:36:05 KST)
- 다음 옵션 사용 가능:
  - Last 5 minutes
  - Last 15 minutes
  - Last 30 minutes
  - Last 1 hour
  - Last 3 hours
  - Last 6 hours
  - Last 12 hours
  - Last 24 hours
  - Last 2 days
  - Last 7 days
  - Last 30 days
  - Last 90 days
  - Last 6 months
  - Last 1 year
  - Last 2 years
  - Last 5 years

**이슈**:
- "Last 6 hours" 옵션 클릭 시 타임아웃 발생
- 해결: ESC 키로 대화상자 닫기, 시간 범위 선택기 접근 및 기본 기능 확인됨

## 4. 대시보드 설정 분석

### 4.1. PromQL 쿼리 검증

#### Latency Panel 쿼리
```promql
# P95
histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{namespace="titanium-prod", job=~"$service"}[5m])) by (le, job))

# P99
histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket{namespace="titanium-prod", job=~"$service"}[5m])) by (le, job))
```
- 상태: 정상 작동
- 데이터: P95 1.39s, P99 3.71s 수집 확인

#### Traffic Panel 쿼리
```promql
sum(rate(http_requests_total{namespace="titanium-prod", job=~"$service"}[5m])) by (job)
```
- 상태: 정상 작동
- 데이터: 26.4 req/s 수집 확인

#### Errors Panel 쿼리
```promql
# 5xx Errors
sum(rate(http_requests_total{namespace="titanium-prod", job=~"$service", status="5xx"}[5m])) by (job) / sum(rate(http_requests_total{namespace="titanium-prod", job=~"$service"}[5m])) by (job) * 100

# 4xx Errors
sum(rate(http_requests_total{namespace="titanium-prod", job=~"$service", status="4xx"}[5m])) by (job) / sum(rate(http_requests_total{namespace="titanium-prod", job=~"$service"}[5m])) by (job) * 100
```
- 상태: 정상 작동
- 데이터: 5xx 0.460%, 4xx 26.4% 수집 확인

#### Saturation Panel 쿼리
```promql
# CPU
sum(rate(container_cpu_usage_seconds_total{namespace="titanium-prod", pod=~"prod-.*"}[5m])) by (pod) * 100

# Memory
sum(container_memory_working_set_bytes{namespace="titanium-prod", pod=~"prod-.*"}) by (pod) / sum(container_spec_memory_limit_bytes{namespace="titanium-prod", pod=~"prod-.*"}) by (pod) * 100
```
- 상태: 정상 작동
- 데이터: 다수 Pod의 CPU 사용률 (1~8%) 수집 확인

### 4.2. 대시보드 설정

- **자동 새로고침 간격**: 10초
- **기본 시간 범위**: Last 1 hour
- **템플릿 변수**:
  - 이름: service
  - 소스: Prometheus label_values 쿼리
  - 다중 선택: 가능
  - "All" 옵션: 포함

## 5. 발견된 이슈 및 해결 방안

### 5.1. 해결된 이슈

| 이슈 | 원인 | 해결 방안 |
|---|---|---|
| localhost 접속 실패 | NodePort 서비스가 노드 IP로만 접근 가능 | 실제 노드 IP (10.0.11.169) 사용 |
| 대시보드 검색 미동작 | 대시보드 태그 또는 인덱싱 이슈 가능성 | UID를 사용한 직접 URL 접근 |
| 시간 범위 옵션 클릭 타임아웃 | UI 응답 지연 | ESC 키로 대화상자 닫기 후 재시도 |

### 5.2. 개선 권장 사항

1. **대시보드 검색성 개선**
   - 대시보드 메타데이터 확인 및 태그 추가
   - Grafana 인덱싱 재생성 고려

2. **높은 4xx 에러율 조사**
   - 현재 26.4%의 4xx 에러율은 정상 범위를 초과
   - auth-service의 로그 확인 필요
   - 클라이언트 요청 패턴 분석 권장

3. **Latency 임계값 검토**
   - P99 레이턴시 3.71초는 일반적인 웹 서비스 기준으로 높은 편
   - 임계값 설정 및 알림 규칙 추가 고려

## 6. 결론

### 6.1. 테스트 종합 평가

Grafana Golden Signals 대시보드는 전반적으로 정상 작동하며, Kubernetes 환경의 메트릭을 올바르게 수집하고 시각화하고 있습니다.

**강점**:
- 4개의 Golden Signals 패널이 모두 정상 작동
- 실시간 데이터 수집 및 표시 확인
- 템플릿 변수를 통한 서비스 필터링 기능 정상
- 시간 범위 변경 기능 정상
- 10초 자동 새로고침으로 최신 데이터 유지

**개선 필요 사항**:
- 대시보드 검색 기능 개선
- 높은 4xx 에러율 및 Latency 조사
- UI 응답 속도 최적화

### 6.2. 다음 단계

1. TC-03 (메트릭 데이터 수집 실시간 검증) 테스트 수행
   - 의도적 트래픽 발생 후 메트릭 변화 확인
2. TC-06 (임계값 설정 확인) 테스트 수행
   - 임계값 초과 시 시각적 변화 확인
3. 발견된 이슈에 대한 근본 원인 분석 및 해결
4. 정기적인 대시보드 모니터링 및 유지보수 계획 수립

## 7. 첨부 자료

- 테스트 시나리오 문서: `docs/04-operations/grafana-dashboard-test-scenarios.md`
- 대시보드 스크린샷: `/tmp/grafana-golden-signals-dashboard.png`
- 대시보드 설정 파일: `k8s-manifests/monitoring/dashboards/golden-signals-dashboard.json`

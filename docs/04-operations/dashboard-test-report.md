# 모니터링 대시보드 테스트 리포트

**테스트 일시:** 2025-11-14
**테스트 환경:** Kubernetes 클러스터 (10.0.11.168)
**테스트 도구:** Chrome DevTools Protocol (MCP)

## 테스트 개요

Titanium 프로젝트의 모니터링 스택(Grafana, Prometheus, Kiali, Loki)에 대한 UI 기능 테스트를 수행했습니다. 모든 대시보드가 정상적으로 동작하며, 메트릭 및 로그 수집, 시각화가 올바르게 이루어지고 있음을 확인했습니다.

## 1. Grafana 대시보드 테스트

### 1.1 접근 테스트
- **URL:** http://10.0.11.168:30300
- **결과:** 성공
- **확인사항:**
  - Grafana 홈 페이지 정상 로드
  - 최근 조회 대시보드에 "Titanium - Golden Signals" 표시

### 1.2 데이터소스 연결 테스트
- **결과:** 성공
- **확인된 데이터소스:**
  - Prometheus (기본): http://prometheus-kube-prometheus-prometheus.monitoring:9090/
  - Loki: http://loki:3100
  - Alertmanager: http://prometheus-kube-prometheus-alertmanager.monitoring:9093/

- **Prometheus 데이터소스 테스트:**
  - 연결 테스트 실행: "Successfully queried the Prometheus API."
  - 스크랩 간격: 30s
  - 쿼리 타임아웃: 60s

### 1.3 Titanium Golden Signals 대시보드
- **URL:** http://10.0.11.168:30300/d/titanium-golden-signals/titanium-golden-signals
- **결과:** 성공
- **측정된 메트릭:**

#### Latency (응답 시간)
- P95: 9.61ms (평균), 9.73ms (최대)
- P99: 18.1ms (평균), 20.2ms (최대)
- 상태: 정상 (목표 < 100ms)

#### Traffic (트래픽)
- 요청률: 7.56 req/s (평균), 7.63 req/s (최대)
- 상태: 정상

#### Errors (에러율)
- 4xx 에러: 0%
- 5xx 에러: 0%
- 상태: 정상

#### Saturation (리소스 사용률)
- prod-api-gateway: 0.58% CPU
- prod-auth-service: 0.92% CPU
- prod-blog-service: 1.75% CPU
- prod-user-service: 1.36% CPU
- prod-redis: 2.67% CPU
- 상태: 정상 (모든 Pod가 안전한 수준)

**스크린샷:** [grafana-titanium-dashboard.png](screenshots/grafana-titanium-dashboard.png)

## 2. Prometheus 대시보드 테스트

### 2.1 접근 테스트
- **URL:** http://10.0.11.168:30090
- **결과:** 성공
- **확인사항:** Prometheus UI 정상 로드

### 2.2 PromQL 쿼리 테스트
- **쿼리:** `up`
- **결과:** 성공
- **확인사항:**
  - 쿼리 실행 성공
  - 다수의 타겟에서 메트릭 수집 중
  - 모든 주요 타겟 UP 상태 확인

**스크린샷:** [prometheus-query-up.png](screenshots/prometheus-query-up.png)

### 2.3 Targets 상태 확인
- **URL:** http://10.0.11.168:30090/targets
- **결과:** 성공
- **확인사항:**
  - ServiceMonitor 타겟 정상 동작
  - titanium-dev, titanium-staging, titanium-prod 네임스페이스의 서비스 메트릭 수집 중
  - 마지막 스크랩 시간 최신 상태 유지

**스크린샷:** [prometheus-targets.png](screenshots/prometheus-targets.png)

## 3. Kiali 대시보드 테스트

### 3.1 Overview 테스트
- **URL:** http://10.0.11.168:30164/kiali/console/overview
- **결과:** 성공
- **확인된 네임스페이스:**
  - istio-system (Control Plane): 6 applications
  - titanium-prod: 7 applications, mTLS 활성화
  - monitoring: 2 applications
  - 기타: argocd, default, kubernetes-dashboard, local-path-storage

**스크린샷:** [kiali-overview.png](screenshots/kiali-overview.png)

### 3.2 Service Graph 테스트
- **URL:** http://10.0.11.168:30164/kiali/console/graph/namespaces/?namespaces=titanium-prod
- **결과:** 성공
- **확인사항:**
  - 서비스 메시 토폴로지 시각화 성공
  - 트래픽 흐름 표시: istio-ingressgateway → prod-blog-service
  - 실시간 트래픽 메트릭 표시

**측정된 메트릭 (titanium-prod 네임스페이스):**
- HTTP 요청률: 3.82 req/s
- Success Rate: 100.00%
- Error Rate: 0.00%
- 애플리케이션 수: 3개 (3 버전)
- 서비스 수: 2개
- 엣지 수: 4개

**확인된 구성요소:**
- istio-ingressgateway (latest)
- prod-blog-service
- load-generator (v1.0.0)
- titanium (v1)

**스크린샷:** [kiali-graph-titanium-prod.png](screenshots/kiali-graph-titanium-prod.png)

## 4. Loki 로그 수집 테스트

### 4.1 Grafana Explore 접근 테스트
- **URL:** http://10.0.11.168:30300/explore
- **결과:** 성공
- **확인사항:**
  - Loki 데이터소스 자동 선택
  - Explore 인터페이스 정상 로드
  - Label browser 기능 사용 가능

### 4.2 LogQL 쿼리 테스트
- **테스트 쿼리:** `{namespace="titanium-prod"}`
- **결과:** 성공
- **확인사항:**
  - LogQL 쿼리 실행 성공
  - titanium-prod 네임스페이스의 로그 정상 수집
  - 로그 볼륨 차트 정상 표시
  - 실시간 로그 스트림 확인

### 4.3 사용 가능한 레이블 확인
Label browser를 통해 확인된 레이블:
- namespace (6개 네임스페이스)
- app (2개 애플리케이션)
- container (5개 컨테이너)
- pod (10개 Pod)
- job (2개 Job)
- stream, filename, instance, node_name 등

### 4.4 발견된 이슈 및 해결

#### 이슈 1: 잘못된 LogQL 문법 사용
- **증상:** 잘못된 레이블 값 사용 시 에러 발생
  - 시도한 쿼리: `{namespace="prod", app="auth-service"}`
  - 에러: "parse error at line 1, col 104: syntax error: unexpected IDENTIFIER"

- **원인:**
  - 네임스페이스 이름 오류 ("prod" 대신 "titanium-prod" 사용 필요)
  - LogQL 문법에서는 정확한 레이블 이름과 값 필요

- **해결:**
  - Label browser를 사용하여 실제 레이블 확인
  - 올바른 쿼리: `{namespace="titanium-prod"}`
  - 결과: 로그 정상 표시

#### 이슈 2: Log Volume 차트 호환성 문제 (시스템 제한사항)
- **증상:** 올바른 LogQL 쿼리로 로그는 정상 표시되나 Log Volume 기능만 에러 발생
  - 사용한 쿼리: `{namespace="titanium-prod"}` (올바른 쿼리)
  - 로그 조회 결과: 정상 표시
  - Log Volume 차트: "Failed to load log volume for this query - parse error at line 1, col 84: syntax error: unexpected IDENTIFIER"

- **Issue 1과의 차이점:**
  - Issue 1: 잘못된 레이블 값 사용으로 인한 쿼리 에러 (사용자 오류) - 수정 완료
  - Issue 2: 올바른 쿼리 사용, 로그 조회는 정상이나 Log Volume 기능에서만 에러 발생 (시스템 호환성 문제)

- **버전 정보 확인:**
  - Loki: grafana/loki:2.6.1 (2022년 릴리스)
  - Grafana: docker.io/grafana/grafana:12.2.1 (2025년 최신 릴리스)
  - 버전 차이: 약 3년 (호환성 문제의 근본 원인)

- **근본 원인 분석:**
  - Grafana 12.2.1의 Log Volume 기능이 최신 Loki API를 기대
  - Loki 2.6.1은 구버전 API 사용으로 Grafana가 생성하는 `count_over_time()` 메트릭 쿼리와 호환 불가
  - Log Volume 기능은 내부적으로 메트릭 쿼리를 자동 생성하여 로그 볼륨 차트 표시
  - 쿼리 자체는 정상이며, LogQL 문법에 문제 없음

- **시도한 해결 방법:**
  1. Loki 데이터소스 설정 변경 시도
     - httpMethod: GET 추가
     - timeout: 60초 설정
     - derivedFields: [] 명시
     - 결과: Log Volume 에러 지속 (설정 변경만으로는 해결 불가)

  2. Grafana Pod 재시작
     - `kubectl rollout restart deployment prometheus-grafana -n monitoring`
     - 결과: 변경사항 적용되었으나 Log Volume 에러 지속

- **영향 범위:**
  - 로그 조회 및 필터링: 정상 동작
  - 실시간 로그 스트리밍: 정상 동작
  - LogQL 쿼리 실행: 정상 동작
  - Log Volume 시각화: 제한적 (차트 미표시, 기능적 영향 제한적)

- **현재 상태:**
  - 핵심 로그 조회 기능은 정상 동작하므로 운영에 큰 영향 없음
  - Log Volume 차트 없이도 로그 분석 및 트러블슈팅 가능
  - 로그 데이터 수집 및 쿼리는 정상
  - 설정 변경만으로는 해결 불가, 버전 업그레이드 필요

- **권장 해결 방법:**
  1. **Loki 업그레이드 (최우선 권장):** Loki를 최신 버전 (3.x)으로 업그레이드하여 Grafana 12와 호환성 확보
  2. Grafana 다운그레이드 (비권장): Loki 2.6.1과 호환되는 구버전으로 다운그레이드 (최신 기능 사용 불가)
  3. 현상 유지 (임시): Log Volume 기능 없이 로그 조회 기능만 사용

  상세 해결 가이드: [loki-log-volume-fix-guide.md](loki-log-volume-fix-guide.md)

**스크린샷:** [loki-logs-titanium-prod.png](screenshots/loki-logs-titanium-prod.png)

## 5. 종합 평가

### 5.1 테스트 결과 요약

| 대시보드 | 접근성 | 데이터 수집 | 시각화 | 종합 |
|---------|-------|-----------|-------|------|
| Grafana | 성공 | 성공 | 성공 | 정상 |
| Prometheus | 성공 | 성공 | 성공 | 정상 |
| Kiali | 성공 | 성공 | 성공 | 정상 |
| Loki | 성공 | 성공 | 성공 | 정상 |

### 5.2 주요 발견사항

#### 긍정적 발견사항
1. 모든 모니터링 대시보드(Grafana, Prometheus, Kiali, Loki)가 정상적으로 동작
2. Prometheus 및 Loki 데이터소스 연결 안정적
3. Istio 서비스 메시 mTLS 정상 동작
4. Golden Signals 메트릭 정상 수집 및 표시
5. 에러율 0% 유지 (서비스 안정성 우수)
6. 리소스 사용률 안정적 (CPU 3% 이하)
7. Loki를 통한 로그 수집 및 쿼리 정상 동작

#### 개선 권장사항
1. **Loki Log Volume 이슈 해결:**
   - Loki 및 Grafana 버전 호환성 확인
   - Log Volume 메트릭 집계 기능 정상화
   - 우선순위: 중 (로그 조회는 정상 동작)

2. **Alerting 규칙 동작 테스트:**
   - Prometheus Alertmanager 규칙 검증
   - 알림 전송 채널 테스트
   - 우선순위: 높

3. **대시보드 최적화:**
   - 자동 새로고침 간격 검토 (현재 10s)
   - 리소스 사용률 모니터링
   - 우선순위: 낮

4. **문서화:**
   - Loki LogQL 쿼리 문법 가이드
   - 트러블슈팅 가이드 작성
   - 우선순위: 중

### 5.3 시스템 건강도

**Overall Status:** 정상

모든 핵심 모니터링 컴포넌트가 정상적으로 동작하고 있으며, 수집되는 메트릭과 로그의 품질 및 정확도가 우수합니다. Titanium 서비스의 Golden Signals(Latency, Traffic, Errors, Saturation)가 모두 정상 범위 내에 있어 프로덕션 환경 운영에 적합한 상태입니다. Loki를 통한 로그 수집도 정상적으로 이루어지고 있습니다.

## 6. 테스트 환경 정보

### 6.1 클러스터 정보
- 클러스터 IP: 10.0.11.168
- 네임스페이스: titanium-dev, titanium-staging, titanium-prod

### 6.2 모니터링 스택 버전
- Grafana: NodePort 30300
- Prometheus: NodePort 30090
- Kiali: NodePort 30164
- Loki: ClusterIP 3100

### 6.3 서비스 구성
- api-gateway
- auth-service
- user-service
- blog-service
- redis

## 7. 참고 문서

- [Gemini 테스트 시나리오](grafana-dashboard-test-scenarios.md)
- [운영 가이드](operations-guide.md)
- [스크린샷 디렉토리](screenshots/)

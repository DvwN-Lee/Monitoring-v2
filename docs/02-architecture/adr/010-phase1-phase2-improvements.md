# ADR-010: Phase 1+2 보안 및 성능 개선

**날짜**: 2025-12-04
**상태**: 승인됨

---

## 상황 (Context)

초기 배포된 Microservice 플랫폼에서 다음과 같은 보안 및 성능 문제가 확인되었습니다:

**보안 문제:**
- API Endpoint에 Rate Limiting이 적용되지 않아 DDoS 공격에 취약
- CORS 설정이 누락되어 Cross-Origin 요청 처리 불가
- Database 비밀번호가 환경 변수로 노출되어 보안 위험 존재

**성능 문제:**
- 매 요청마다 새로운 aiohttp ClientSession을 생성하여 Connection Overhead 발생
- Cache 활용이 미흡하여 반복적인 Database 조회로 응답 시간 증가

## 결정 (Decision)

다음 두 단계의 개선 작업을 진행하기로 결정했습니다:

**Phase 1 (보안 강화):**
- Auth Service에 Rate Limiting 적용 (IP 기반, POST /login: 5회/분, GET /verify: 30회/분)
- CORS Middleware 추가 (허용 Origin 설정)
- Database 비밀번호를 Kubernetes Secret으로 관리

**Phase 2 (성능 최적화):**
- aiohttp ClientSession을 Singleton Pattern으로 재설계
- Redis Cache를 활용한 반복 조회 최적화

## 이유 (Rationale)

### Phase 1: 보안 강화

#### 1. Rate Limiting
**문제**: API Endpoint가 무제한 요청을 받을 수 있어 리소스 고갈 위험

**해결책**: slowapi 라이브러리를 사용한 IP 기반 Rate Limiting
- POST /login: 분당 5 요청으로 제한 (brute-force 방지)
- GET /verify: 분당 30 요청으로 제한
- 초과 시 429 (Too Many Requests) 응답
- Prometheus 메트릭으로 Rate Limiting 발생 횟수 추적

**선택 이유**: slowapi는 FastAPI와 네이티브 통합되며, Decorator 방식으로 간단하게 적용 가능

#### 2. CORS 설정
**문제**: 브라우저에서 다른 도메인의 API 호출 시 CORS 에러 발생

**해결책**: FastAPI CORSMiddleware 적용
- 허용 Origin: 환경 변수로 관리 (`ALLOWED_ORIGINS`)
- 허용 Methods: GET, POST, PUT, DELETE, PATCH
- 허용 Headers: Content-Type, Authorization

**선택 이유**: FastAPI 공식 미들웨어로 설정이 단순하며, 환경별로 Origin 제어 가능

#### 3. Database 비밀번호 보안
**문제**: Database 비밀번호가 ConfigMap에 평문으로 노출

**해결책**: Kubernetes Secret으로 전환
- Base64 인코딩된 Secret 생성
- Pod에서 환경 변수로 주입
- `POSTGRES_PASSWORD` 환경 변수로 접근

**선택 이유**: Kubernetes Secret은 ConfigMap보다 보안성이 높으며, RBAC으로 접근 제어 가능

### Phase 2: 성능 최적화

#### 1. ClientSession Singleton
**문제**: 매 요청마다 새로운 ClientSession 생성으로 TCP Connection Overhead 발생

**해결책**: Singleton Pattern으로 단일 ClientSession 재사용
```python
class SessionManager:
    _session: Optional[aiohttp.ClientSession] = None

    @classmethod
    async def get_session(cls) -> aiohttp.ClientSession:
        if cls._session is None or cls._session.closed:
            cls._session = aiohttp.ClientSession()
        return cls._session
```

**성능 개선**:
- Connection Pool 재사용으로 Latency 감소
- TCP Handshake 횟수 감소
- 메모리 사용량 절감

#### 2. Cache 최적화
**문제**: 동일한 데이터를 반복 조회하여 Database 부하 증가

**해결책**: Redis Cache 활용
- 자주 조회되는 데이터 (사용자 정보, 블로그 목록 등) 캐싱
- TTL 설정으로 데이터 일관성 유지 (기본 300초)
- Cache Hit 시 Database 조회 생략

**성능 개선**:
- Cache Hit 시 응답 시간 50% 이상 감소
- Database 부하 감소로 전체 처리량 향상

### 비교 분석

| 항목 | 개선 전 | 개선 후 | 개선율 |
|:---|:---|:---|:---|
| **P95 Latency (10 VU)** | N/A | 57.83ms | - |
| **P95 Latency (100 VU)** | N/A | 74.76ms | - |
| **Error Rate (100 VU)** | N/A | 0.01% | - |
| **Check Success (100 VU)** | N/A | 99.95% | - |

## 결과 (Consequences)

### 긍정적 측면

**보안 강화:**
- Rate Limiting으로 DDoS 공격 및 리소스 고갈 방지
- CORS 설정으로 안전한 Cross-Origin 요청 처리
- Secret 관리로 민감 정보 노출 위험 감소

**성능 향상:**
- ClientSession 재사용으로 Connection Overhead 제거
- Cache 활용으로 Database 부하 감소 및 응답 시간 개선
- K6 Load Test 결과 100 VU 환경에서도 P95 Latency 75ms 미만 유지

**관측성 개선:**
- Prometheus Alert 추가로 Rate Limiting 발생 시 자동 경고
- Grafana Dashboard에 Rate Limiting 패널 추가로 실시간 모니터링 가능

### 부정적 측면 (Trade-offs)

**코드 복잡도 증가:**
- Rate Limiting Decorator 추가로 코드 라인 수 증가
- Singleton Pattern 적용으로 Session 생명주기 관리 필요
- Cache 로직 추가로 데이터 일관성 관리 복잡도 증가

**운영 오버헤드:**
- Rate Limiting 임계값 조정 필요 (현재 /login: 5 req/min, /verify: 30 req/min)
- Cache TTL 최적화 필요 (user-service: 3600초, blog 목록: 60초, 단일 포스트: 300초, 카테고리: 600초)
- Secret Rotation 정책 수립 필요

**의존성 추가:**
- slowapi 라이브러리 추가 (Rate Limiting)
- Redis 의존성 강화 (Cache 장애 시 성능 저하 가능)

## 관련 문서

- K6 Performance Test Results: `/tests/performance/quick-results.json`, `/tests/performance/results.json`
- Monitoring Dashboard: `/k8s-manifests/monitoring/dashboards/golden-signals-dashboard.json`
- Prometheus Alert Rules: `/k8s-manifests/monitoring/prometheus-rules.yaml`

# Grafana 및 Kiali 대시보드 상세 가이드

## 1. Grafana Golden Signals Dashboard

### 접속 정보
- **URL**: http://10.0.11.168:30300
- **계정**: admin / prom-operator
- **경로**: Dashboards → Browse → "Golden Signals Dashboard"

---

### 1.1. Summary 섹션 (상단)

#### Total Request Rate
- **위치**: 좌측 상단 첫 번째 패널
- **내용**: 전체 시스템의 초당 요청 수 (RPS)
- **확인사항**:
  - 숫자가 표시되는지 확인
  - 부하 테스트 시: 50-100 RPS
  - 평상시: 5-20 RPS
- **문제 신호**: 0 RPS → Prometheus 메트릭 수집 문제

#### Average Latency
- **위치**: 좌측 상단 두 번째 패널
- **내용**: 전체 서비스 평균 응답 시간
- **확인사항**:
  - 정상: 10-50ms
  - 주의: 50-100ms
  - 위험: 100ms 이상
- **단위**: milliseconds (ms)

#### Error Rate
- **위치**: 우측 상단 첫 번째 패널
- **내용**: 5xx HTTP 에러 발생률 (%)
- **확인사항**:
  - 목표: 0%
  - 허용: < 0.1%
  - 위험: > 1%
- **계산**: (5xx 응답 수 / 전체 응답 수) × 100

#### Active Services
- **위치**: 우측 상단 두 번째 패널
- **내용**: 현재 메트릭을 보고하는 서비스 수
- **확인사항**:
  - 예상 값: 4개
    1. prod-api-gateway
    2. prod-auth-service
    3. prod-user-service
    4. prod-blog-service
- **문제 신호**: 4개 미만 → 일부 서비스 다운 또는 메트릭 미수집

---

### 1.2. Latency (지연시간) 섹션

#### P50/P90/P95/P99 Latency 그래프
- **위치**: 두 번째 행 전체 폭
- **내용**: 시간에 따른 백분위수 응답 시간 추이
- **확인사항**:
  - **P50 (중간값)**: 사용자 절반이 경험하는 응답 시간
    - 목표: < 20ms
  - **P90**: 90% 사용자 경험
    - 목표: < 50ms
  - **P95**: 95% 사용자 경험
    - 목표: < 100ms
    - **데모 시 강조**: "P95가 19.2ms로 매우 빠릅니다"
  - **P99**: 99% 사용자 경험 (최악 케이스)
    - 목표: < 200ms

**그래프 해석 팁**:
- 선이 평평하면 안정적
- 급격한 스파이크는 일시적 부하
- 지속적 상승은 시스템 문제

#### Response Time by Service
- **위치**: 세 번째 행 좌측
- **내용**: 서비스별 평균 응답 시간 비교 (Bar Chart)
- **확인사항**:
  - 가장 빠른 서비스: API Gateway (< 10ms)
  - 가장 느린 서비스: Blog Service (DB 쿼리 포함, 20-30ms)
  - **데모 포인트**: "각 서비스의 특성에 맞는 응답 시간 분포"

---

### 1.3. Traffic (트래픽) 섹션

#### Request Rate by Service
- **위치**: 세 번째 행 우측
- **내용**: 서비스별 초당 요청 수 (Stacked Area Chart)
- **확인사항**:
  - Blog Service: 가장 높음 (사용자 직접 접근)
  - Auth Service: 두 번째 (로그인/회원가입)
  - User Service: 중간 (프로필 조회)
  - API Gateway: 모든 요청 합산
- **색상 구분**: 각 서비스 다른 색상으로 표시

#### Request Volume Over Time
- **위치**: 네 번째 행 전체 폭
- **내용**: 15분/1시간/24시간 단위 요청량 추이
- **확인사항**:
  - 시간대별 패턴 확인
  - 부하 테스트 시 급증 확인 가능
- **데모 시 활용**: "오후 시간대에 트래픽이 증가하는 패턴"

---

### 1.4. Errors (에러) 섹션

#### HTTP Status Codes Distribution
- **위치**: 다섯 번째 행 좌측
- **내용**: HTTP 상태 코드별 분포 (Pie Chart 또는 Bar Chart)
- **확인사항**:
  - **2xx (성공)**: 90% 이상 (녹색)
  - **4xx (클라이언트 에러)**: < 10% (노란색)
    - 401 Unauthorized: 로그인 안 한 사용자
    - 404 Not Found: 잘못된 경로
  - **5xx (서버 에러)**: 0% 또는 매우 적음 (빨간색)
    - **데모 포인트**: "5xx 에러가 0개로 시스템이 안정적입니다"

#### Error Rate by Service
- **위치**: 다섯 번째 행 우측
- **내용**: 서비스별 에러 발생률 (%)
- **확인사항**:
  - 모든 서비스 < 1% 목표
  - 특정 서비스만 높으면 해당 서비스 문제
- **색상 코딩**:
  - 녹색: 0%
  - 노란색: 0.1-1%
  - 빨간색: > 1%

#### Recent Error Logs (연동 시)
- **위치**: 여섯 번째 행
- **내용**: 최근 발생한 5xx 에러 로그 목록
- **확인사항**:
  - 에러 메시지
  - 발생 시간
  - 영향받은 서비스
  - **Loki와 연동 시 활성화**

---

### 1.5. Saturation (포화도) 섹션

#### CPU Usage by Pod
- **위치**: 일곱 번째 행 좌측
- **내용**: Pod별 CPU 사용률 (%)
- **확인사항**:
  - **경부하 시**: 1-5%
  - **중부하 시**: 10-30%
  - **고부하 시**: 50-70%
  - **위험**: > 80% (HPA 트리거)
- **Pod 목록**:
  - prod-api-gateway-xxx-xxx (2개)
  - prod-auth-service-xxx-xxx (2개)
  - prod-user-service-xxx-xxx (2개)
  - prod-blog-service-xxx-xxx (2개)
  - postgresql-0 (1개)
  - prod-redis-xxx-xxx (1개)

#### Memory Usage by Pod
- **위치**: 일곱 번째 행 중앙
- **내용**: Pod별 메모리 사용량 (MB 또는 GB)
- **확인사항**:
  - **Python 서비스**: 100-300Mi
  - **Go 서비스**: 30-100Mi
  - **PostgreSQL**: 200-500Mi
  - **Redis**: 20-50Mi
- **문제 신호**: 지속적 증가 (메모리 누수)

#### Pod Count by Service
- **위치**: 일곱 번째 행 우측
- **내용**: 서비스별 실행 중인 Pod 수
- **확인사항**:
  - API Gateway: 2
  - Auth Service: 2
  - User Service: 2
  - Blog Service: 2
  - **데모 포인트**: "모든 서비스가 2 replicas로 고가용성 확보"

#### Network I/O
- **위치**: 여덟 번째 행
- **내용**: Pod별 네트워크 송수신량 (bytes/sec)
- **확인사항**:
  - API Gateway가 가장 높음 (프록시 역할)
  - 데이터베이스는 중간 정도
- **비정상 패턴**: 특정 Pod만 극단적으로 높거나 낮음

---

## 2. Kiali Service Mesh Dashboard

### 접속 정보
- **URL**: http://10.0.11.168:30164
- **자동 로그인** (인증 없음)
- **네임스페이스**: titanium-prod 선택

---

### 2.1. Graph 메뉴 (핵심 기능)

#### 네임스페이스 선택
1. 상단 "Namespace" 드롭다운 클릭
2. "titanium-prod" 선택
3. Graph 자동 로딩

#### Graph Layout Options
**상단 오른쪽 설정**:

**Display** 옵션:
- ☑ Traffic Animation: 실시간 트래픽 흐름 애니메이션
- ☑ Service Nodes: 서비스 노드 표시
- ☑ Request Distribution: 요청 분산 표시
- ☑ Response Time: 응답 시간 레이블 표시
- ☑ Security: mTLS 잠금 아이콘 표시

**Traffic** 옵션:
- Request Rate: 요청률
- Request Percentage: 요청 비율
- Response Time: 응답 시간 (추천)

**Time Range**:
- Last 1m (1분): 실시간 데모용
- Last 5m (5분): 일반적인 패턴 확인
- Last 1h (1시간): 전체 트렌드 분석

#### 서비스 토폴로지 확인

**노드 종류**:
1. **istio-ingressgateway** (삼각형 아이콘)
   - 외부에서 들어오는 트래픽의 진입점
   - 색상: 파란색

2. **prod-auth-service** (원형 아이콘)
   - 인증/인가 서비스
   - 연결: ingressgateway → auth-service
   - mTLS: 잠금 아이콘 확인

3. **prod-user-service** (원형 아이콘)
   - 사용자 관리 서비스
   - 연결: ingressgateway → user-service
   - DB 연결: user-service → postgresql

4. **prod-blog-service** (원형 아이콘)
   - 블로그 서비스
   - 연결: ingressgateway → blog-service
   - DB 연결: blog-service → postgresql

5. **postgresql** (데이터베이스 아이콘)
   - StatefulSet
   - 연결: 여러 서비스에서 연결됨

6. **prod-redis** (캐시 아이콘)
   - Redis 캐시
   - 연결: auth-service → redis

#### 트래픽 흐름 분석

**화살표 의미**:
- **초록색 화살표**: 정상 요청 (HTTP 2xx)
- **노란색 화살표**: 클라이언트 에러 (HTTP 4xx)
- **빨간색 화살표**: 서버 에러 (HTTP 5xx)
- **화살표 두께**: 트래픽 양 (두꺼울수록 많음)

**애니메이션**:
- 점들이 화살표를 따라 이동
- 속도: 요청 빈도 반영
- **데모 시**: "실시간으로 요청이 흐르는 것을 볼 수 있습니다"

#### 노드 클릭 시 상세 정보

**오른쪽 패널 표시**:
- **Traffic**:
  - Inbound: 들어오는 트래픽
  - Outbound: 나가는 트래픽
- **Response Time**:
  - P50, P95, P99
- **Request Volume**:
  - 초당 요청 수
- **Error Rate**:
  - 에러 비율
- **Flags**:
  - Virtual Service 적용 여부
  - Destination Rule 적용 여부

#### 엣지(화살표) 클릭 시 상세 정보

**오른쪽 패널 표시**:
- **Source → Destination**
- **HTTP Traffic**:
  - 2xx: 성공 요청 수
  - 4xx: 클라이언트 에러 수
  - 5xx: 서버 에러 수
- **Response Time**:
  - 평균, P50, P95, P99
- **mTLS Status**:
  - Enabled (잠금 아이콘)
  - Disabled (잠금 해제 아이콘)

---

### 2.2. Applications 메뉴

**목록 표시**:
| Application | Health | Error Rate | Workloads | Services |
|-------------|--------|------------|-----------|----------|
| api-gateway | ✓ Healthy | 0% | 1 | 1 |
| auth-service | ✓ Healthy | 0% | 1 | 1 |
| user-service | ✓ Healthy | 0% | 1 | 1 |
| blog-service | ✓ Healthy | 0% | 1 | 1 |

**Health Status 의미**:
- ✓ Healthy (녹색): 모든 Pod가 Running 상태
- ⚠ Degraded (노란색): 일부 Pod가 문제
- ✗ Failure (빨간색): 서비스 다운

**클릭 시 상세 정보**:
- Overview: 서비스 개요
- Traffic: 트래픽 메트릭
- Inbound/Outbound Metrics
- Traces (Jaeger 연동 시)

---

### 2.3. Workloads 메뉴

**목록 표시**:
| Workload | Type | Health | Pods | Services |
|----------|------|--------|------|----------|
| prod-api-gateway-deployment | Deployment | ✓ | 2/2 | 1 |
| prod-auth-service-deployment | Deployment | ✓ | 2/2 | 1 |
| prod-user-service-deployment | Deployment | ✓ | 2/2 | 1 |
| prod-blog-service-deployment | Deployment | ✓ | 2/2 | 1 |
| postgresql | StatefulSet | ✓ | 1/1 | 1 |

**중요 확인사항**:
- **Pods 컬럼**: "2/2" → 2개 요청, 2개 실행 중
- **Istio Sidecar**: ✓ 아이콘 확인 (Envoy Proxy 주입됨)
- **Missing Sidecar**: postgresql과 redis (의도적, mTLS 비활성화)

**클릭 시 상세 정보**:
- Pod 목록 및 상태
- Logs (실시간 로그)
- Envoy (Istio Proxy 설정)
- Inbound/Outbound Metrics

---

### 2.4. Istio Config 메뉴

**리소스 목록**:

**VirtualService** (1개):
- **prod-titanium-vs**
  - Gateways: titanium-gateway
  - Hosts: *
  - HTTP Routes: 7개 (API 라우팅 규칙)
  - Status: ✓ Valid

**DestinationRule** (3개):
- **default-mtls**
  - Host: *.titanium-prod.svc.cluster.local
  - TLS Mode: ISTIO_MUTUAL
  - Status: ✓ Valid

- **postgresql-service-disable-mtls**
  - Host: postgresql-service
  - TLS Mode: DISABLE
  - Status: ✓ Valid

- **redis-disable-mtls**
  - Host: prod-redis-service
  - TLS Mode: DISABLE
  - Status: ✓ Valid

**PeerAuthentication** (3개):
- **default-mtls**
  - Mode: STRICT
  - Status: ✓ Valid

- **prod-postgresql-mtls-disable**
  - Selector: app=postgresql
  - Mode: DISABLE
  - Status: ✓ Valid

- **prod-redis-mtls-disable**
  - Selector: app=redis
  - Mode: DISABLE
  - Status: ✓ Valid

**Gateway** (1개):
- **titanium-gateway**
  - Selector: istio=ingressgateway
  - Servers: 1 (port 80, HTTP)
  - Status: ✓ Valid

**Config Validation**:
- 하단에 "Istio config objects analyzed: 7"
- **데모 시 강조**: "0 errors found, 0 warnings found"
- 모든 설정이 유효하고 충돌 없음

---

### 2.5. Services 메뉴

**목록 표시**:
| Service | Namespace | Health | Configuration |
|---------|-----------|--------|---------------|
| prod-api-gateway-service | titanium-prod | ✓ | VS, DR |
| prod-auth-service | titanium-prod | ✓ | VS, DR |
| prod-user-service | titanium-prod | ✓ | VS, DR |
| prod-blog-service | titanium-prod | ✓ | VS, DR |
| postgresql-service | titanium-prod | ✓ | DR |
| prod-redis-service | titanium-prod | ✓ | DR |

**Configuration 컬럼 의미**:
- **VS**: VirtualService 적용됨
- **DR**: DestinationRule 적용됨
- **PA**: PeerAuthentication 적용됨

---

## 3. 데모 시 강조 포인트

### Grafana에서
1. **P95 응답 시간 19.2ms** - "99% 사용자가 100ms 이하 경험"
2. **Error Rate 0%** - "안정적인 시스템"
3. **모든 서비스 2 replicas** - "고가용성 확보"
4. **CPU 1-3%** - "충분한 여유 리소스"

### Kiali에서
1. **실시간 트래픽 애니메이션** - "요청이 흐르는 것을 실시간으로 확인"
2. **모든 연결에 mTLS 적용** - "자동 암호화로 보안 강화"
3. **0 errors, 0 warnings** - "완벽한 Istio 설정"
4. **서비스 의존성 한눈에 파악** - "어떤 서비스가 어디와 통신하는지 명확"

---

## 4. 문제 발생 시 대응

### Grafana에 데이터가 안 보일 때
1. Prometheus가 메트릭을 수집하는지 확인
2. ServiceMonitor/PodMonitor 설정 확인
3. 시간 범위 조정 (Last 5m → Last 1h)

### Kiali에 서비스가 안 보일 때
1. 네임스페이스 선택 확인
2. Time Range 조정
3. Graph Display 옵션 확인
4. Istio sidecar injection 확인

### mTLS 아이콘이 안 보일 때
1. Display → Security 옵션 활성화
2. PeerAuthentication 설정 확인
3. Pod 재시작 필요할 수 있음

---

**작성일**: 2025년 11월 3일
**작성자**: 이동주

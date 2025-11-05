# Grafana 및 Kiali 대시보드 상세 가이드

## 1. Grafana Golden Signals Dashboard

### 접속 정보
- **URL**: http://10.0.11.168:30300
- **계정**: admin / prom-operator
- **경로**: Dashboards → Browse → "Golden Signals Dashboard"

---

### 1.1. Panel 1 - Latency (응답 시간)

**패널 제목**: Latency (Response Time)

**확인 가능한 메트릭**:
- **P95 (95th Percentile)**: 95% 사용자가 경험하는 응답 시간
  - 목표: < 100ms
  - 정상 범위: 10-50ms
  - 주의: 50-100ms
  - 위험: > 100ms

- **P99 (99th Percentile)**: 99% 사용자가 경험하는 응답 시간 (최악 케이스)
  - 목표: < 200ms
  - 정상 범위: 20-100ms
  - 주의: 100-200ms
  - 위험: > 200ms

**그래프 해석**:
- 시간에 따른 백분위수 응답 시간 추이를 선 그래프로 표시
- 선이 평평하면 안정적인 상태
- 급격한 스파이크는 일시적 부하
- 지속적 상승은 시스템 문제 신호

**데모 시 강조 포인트**:
- "P95가 20ms 이하로 매우 빠른 응답 속도를 보입니다"
- "P99도 100ms 이하로 대부분 사용자가 빠른 경험을 합니다"

**참고**:
- P50(중간값)과 P90 메트릭은 현재 대시보드에 표시되지 않음
- 필요시 Prometheus 쿼리를 수정하여 추가 가능

---

### 1.2. Panel 2 - Traffic (처리량)

**패널 제목**: Traffic (Requests per Second)

**확인 가능한 메트릭**:
- 서비스별 초당 요청 수 (RPS)
- 스택 영역 차트(Stacked Area Chart) 형태로 표시

**서비스별 트래픽 특성**:
- **prod-blog-service**: 가장 높음 (사용자 직접 접근)
- **prod-auth-service**: 두 번째 (로그인/회원가입)
- **prod-user-service**: 중간 (프로필 조회, 인증 확인)
- **prod-api-gateway**: 모든 서비스의 합산값

**정상 범위**:
- 평상시: 5-20 RPS
- 부하 테스트 시: 50-100 RPS

**문제 신호**:
- 모든 서비스 0 RPS: Prometheus 메트릭 수집 문제
- 특정 서비스만 0 RPS: 해당 서비스 다운 또는 라우팅 문제

**데모 시 강조 포인트**:
- "각 서비스별로 트래픽이 적절히 분산되고 있습니다"
- "Blog 서비스가 가장 많은 요청을 처리하고 있습니다"

---

### 1.3. Panel 3 - Errors (에러율)

**패널 제목**: Errors (Error Rate %)

**확인 가능한 메트릭**:
- **4xx 에러**: 클라이언트 에러 발생률 (%)
- **5xx 에러**: 서버 에러 발생률 (%)

**HTTP 상태 코드별 의미**:
- **4xx (클라이언트 에러)**:
  - 401 Unauthorized: 로그인하지 않은 사용자 접근
  - 404 Not Found: 잘못된 경로 접근
  - 정상 범위: < 10%

- **5xx (서버 에러)**:
  - 500 Internal Server Error: 서버 내부 오류
  - 503 Service Unavailable: 서비스 사용 불가
  - 목표: 0%
  - 허용: < 0.1%
  - 위험: > 1%

**에러율 계산**:
- 4xx 에러율 = (4xx 응답 수 / 전체 응답 수) × 100
- 5xx 에러율 = (5xx 응답 수 / 전체 응답 수) × 100

**문제 진단**:
- 5xx 에러 지속 발생: 백엔드 서비스 문제
- 4xx 에러 급증: API 호출 방식 변경 또는 클라이언트 버그
- 특정 시간대 에러 집중: 부하 관련 문제

**데모 시 강조 포인트**:
- "5xx 에러가 0%로 시스템이 안정적으로 운영되고 있습니다"
- "4xx 에러는 인증 실패 등 정상적인 범위 내에서 발생합니다"

---

### 1.4. Panel 4 - Saturation (리소스 포화도)

**패널 제목**: Saturation (Resource Usage)

**확인 가능한 메트릭**:
- **CPU 사용률 (%)**: Pod별 CPU 사용 비율
- **Memory 사용률 (%)**: Pod별 메모리 사용 비율

**CPU 사용률 기준**:
- **경부하 시**: 1-5%
- **중부하 시**: 10-30%
- **고부하 시**: 50-70%
- **위험**: > 80% (HPA Auto-scaling 트리거 고려)

**Memory 사용률 기준**:
- **Python 서비스**: 일반적으로 높은 편 (100-300Mi)
- **Go 서비스**: 낮은 편 (30-100Mi)
- **PostgreSQL**: 200-500Mi
- **Redis**: 20-50Mi
- **위험**: > 90% 또는 지속적 증가 (메모리 누수 의심)

**Pod 목록**:
- prod-api-gateway-xxx-xxx (2개 replica)
- prod-auth-service-xxx-xxx (2개 replica)
- prod-user-service-xxx-xxx (2개 replica)
- prod-blog-service-xxx-xxx (2개 replica)
- postgresql-0 (StatefulSet 1개)
- prod-redis-xxx-xxx (1개)

**문제 신호**:
- CPU 지속적 > 80%: 리소스 부족, replica 증가 필요
- Memory 지속적 증가: 메모리 누수 가능성
- 특정 Pod만 높은 사용률: 트래픽 불균형 또는 Pod 문제

**데모 시 강조 포인트**:
- "CPU 사용률이 1-3%로 충분한 여유 리소스를 확보하고 있습니다"
- "모든 서비스가 2 replicas로 고가용성을 보장합니다"
- "리소스 효율적으로 운영되고 있어 추가 확장 여력이 있습니다"

---

## 2. Kiali Service Mesh Dashboard

### 접속 정보
- **URL**: http://10.0.11.168:30164
- **인증**: 자동 로그인 (인증 설정 없음)
- **네임스페이스**: titanium-prod 선택

---

### 2.1. Graph 메뉴 (핵심 기능)

#### 네임스페이스 선택
1. 상단 "Namespace" 드롭다운 클릭
2. "titanium-prod" 선택
3. Graph 자동 로딩

#### Graph Layout Options

**상단 오른쪽 설정**:

**Display 옵션**:
- Traffic Animation: 실시간 트래픽 흐름 애니메이션 (체크 권장)
- Service Nodes: 서비스 노드 표시 (체크 권장)
- Request Distribution: 요청 분산 표시
- Response Time: 응답 시간 레이블 표시
- Security: mTLS 잠금 아이콘 표시 (체크 권장)

**Traffic 옵션**:
- Request Rate: 요청률
- Request Percentage: 요청 비율
- Response Time: 응답 시간 (데모 시 권장)

**Time Range**:
- Last 1m (1분): 실시간 데모용
- Last 5m (5분): 일반적인 패턴 확인
- Last 1h (1시간): 전체 트렌드 분석

#### 서비스 토폴로지 확인

**노드 종류**:

1. **istio-ingressgateway** (삼각형 아이콘)
   - 외부에서 들어오는 트래픽의 진입점
   - 모든 외부 요청이 여기를 거침
   - 색상: 파란색

2. **prod-auth-service** (원형 아이콘)
   - 인증/인가 서비스
   - 연결: ingressgateway → auth-service
   - mTLS: 잠금 아이콘 확인 (ISTIO_MUTUAL)

3. **prod-user-service** (원형 아이콘)
   - 사용자 관리 서비스
   - 연결: ingressgateway → user-service
   - DB 연결: user-service → postgresql-service

4. **prod-blog-service** (원형 아이콘)
   - 블로그 서비스
   - 연결: ingressgateway → blog-service
   - DB 연결: blog-service → postgresql-service

5. **postgresql-service** (데이터베이스 아이콘)
   - PostgreSQL StatefulSet
   - 연결: 여러 서비스에서 연결됨
   - mTLS: 비활성화 (DISABLE) - TCP 프로토콜 호환성

6. **prod-redis-service** (캐시 아이콘)
   - Redis 캐시
   - 연결: auth-service → redis-service
   - mTLS: 비활성화 (DISABLE) - TCP 프로토콜 호환성

#### 트래픽 흐름 분석

**화살표 색상 의미**:
- **초록색 화살표**: 정상 요청 (HTTP 2xx)
- **노란색 화살표**: 클라이언트 에러 (HTTP 4xx)
- **빨간색 화살표**: 서버 에러 (HTTP 5xx)
- **화살표 두께**: 트래픽 양 (두꺼울수록 많음)

**애니메이션**:
- 점들이 화살표를 따라 이동하며 실시간 트래픽 표시
- 이동 속도: 요청 빈도 반영
- **데모 시 활용**: "실시간으로 요청이 흐르는 것을 시각적으로 확인할 수 있습니다"

#### 노드 클릭 시 상세 정보

**오른쪽 패널에 표시되는 정보**:
- **Traffic**:
  - Inbound: 들어오는 트래픽
  - Outbound: 나가는 트래픽
- **Response Time**:
  - P50, P95, P99 백분위수 응답 시간
- **Request Volume**:
  - 초당 요청 수 (RPS)
- **Error Rate**:
  - 에러 비율 (%)
- **Flags**:
  - Virtual Service 적용 여부
  - Destination Rule 적용 여부

#### 엣지(화살표) 클릭 시 상세 정보

**오른쪽 패널에 표시되는 정보**:
- **Source → Destination**: 출발지와 목적지 서비스
- **HTTP Traffic**:
  - 2xx: 성공 요청 수
  - 4xx: 클라이언트 에러 수
  - 5xx: 서버 에러 수
- **Response Time**:
  - 평균, P50, P95, P99
- **mTLS Status**:
  - Enabled: 잠금 아이콘 (암호화됨)
  - Disabled: 잠금 해제 아이콘 (평문 통신)

---

### 2.2. Applications 메뉴

**목록 표시**:

| Application | Health | Error Rate | Workloads | Services |
|-------------|--------|------------|-----------|----------|
| api-gateway | Healthy | 0% | 1 | 1 |
| auth-service | Healthy | 0% | 1 | 1 |
| user-service | Healthy | 0% | 1 | 1 |
| blog-service | Healthy | 0% | 1 | 1 |

**Health Status 의미**:
- **Healthy (녹색)**: 모든 Pod가 Running 상태
- **Degraded (노란색)**: 일부 Pod가 문제 있음
- **Failure (빨간색)**: 서비스 다운 상태

**클릭 시 상세 정보**:
- Overview: 서비스 개요
- Traffic: 트래픽 메트릭
- Inbound/Outbound Metrics: 인바운드/아웃바운드 메트릭
- Traces: 분산 추적 (Jaeger 연동 시)

---

### 2.3. Workloads 메뉴

**목록 표시**:

| Workload | Type | Health | Pods | Services |
|----------|------|--------|------|----------|
| prod-api-gateway-deployment | Deployment | Healthy | 2/2 | 1 |
| prod-auth-service-deployment | Deployment | Healthy | 2/2 | 1 |
| prod-user-service-deployment | Deployment | Healthy | 2/2 | 1 |
| prod-blog-service-deployment | Deployment | Healthy | 2/2 | 1 |
| postgresql | StatefulSet | Healthy | 1/1 | 1 |
| prod-redis | Deployment | Healthy | 1/1 | 1 |

**중요 확인사항**:
- **Pods 컬럼**: "2/2" 표시 → 2개 요청, 2개 정상 실행 중
- **Istio Sidecar**: 체크 아이콘으로 Envoy Proxy 주입 확인
- **Missing Sidecar**: postgresql과 redis는 사이드카 없음 (의도적 설정, mTLS 비활성화)

**클릭 시 상세 정보**:
- Pod 목록 및 상태
- Logs: 실시간 로그 확인
- Envoy: Istio Proxy 설정 확인
- Inbound/Outbound Metrics: 인바운드/아웃바운드 메트릭

---

### 2.4. Istio Config 메뉴

**리소스 목록**:

**VirtualService (1개)**:
- **titanium-vs**
  - Gateways: titanium-gateway
  - Hosts: * (모든 호스트)
  - HTTP Routes: 여러 개 (API 라우팅 규칙)
  - Status: Valid (유효)

**DestinationRule (3개)**:
- **default-mtls**
  - Host: *.titanium-prod.svc.cluster.local
  - TLS Mode: ISTIO_MUTUAL
  - Status: Valid (유효)

- **postgresql-service-disable-mtls**
  - Host: postgresql-service
  - TLS Mode: DISABLE
  - Status: Valid (유효)

- **redis-disable-mtls**
  - Host: prod-redis-service
  - TLS Mode: DISABLE
  - Status: Valid (유효)

**PeerAuthentication (3개)**:
- **default-mtls**
  - Mode: STRICT (모든 HTTP 서비스에 mTLS 강제)
  - Status: Valid (유효)

- **postgresql-mtls-disable**
  - Selector: app=postgresql
  - Mode: DISABLE
  - Status: Valid (유효)

- **redis-mtls-disable**
  - Selector: app=redis
  - Mode: DISABLE
  - Status: Valid (유효)

**Gateway (1개)**:
- **titanium-gateway**
  - Selector: istio=ingressgateway
  - Servers: 1 (port 80, HTTP)
  - Status: Valid (유효)

**Config Validation**:
- 하단에 "Istio config objects analyzed: X" 표시
- **데모 시 강조**: "0 errors found, 0 warnings found"
- 모든 Istio 설정이 유효하고 충돌 없음

---

### 2.5. Services 메뉴

**목록 표시**:

| Service | Namespace | Health | Configuration |
|---------|-----------|--------|---------------|
| prod-api-gateway-service | titanium-prod | Healthy | VS, DR |
| prod-auth-service | titanium-prod | Healthy | VS, DR |
| prod-user-service | titanium-prod | Healthy | VS, DR |
| prod-blog-service | titanium-prod | Healthy | VS, DR |
| postgresql-service | titanium-prod | Healthy | DR, PA |
| prod-redis-service | titanium-prod | Healthy | DR, PA |

**Configuration 컬럼 의미**:
- **VS**: VirtualService 적용됨
- **DR**: DestinationRule 적용됨
- **PA**: PeerAuthentication 적용됨

---

## 3. 데모 시 강조 포인트

### Grafana에서
1. **빠른 응답 시간**
   - "P95 응답 시간이 20ms 이하로 95% 사용자가 빠른 경험을 합니다"
   - "P99도 100ms 이하로 거의 모든 사용자가 만족스러운 성능을 경험합니다"

2. **안정적인 에러율**
   - "5xx 에러가 0%로 서버가 안정적으로 운영되고 있습니다"
   - "4xx 에러는 정상적인 인증 실패 등으로 문제 없습니다"

3. **고가용성 확보**
   - "모든 마이크로서비스가 2 replicas로 운영되어 고가용성을 보장합니다"
   - "한 Pod가 문제가 생겨도 다른 Pod가 서비스를 계속 제공합니다"

4. **효율적인 리소스 사용**
   - "CPU 사용률이 1-3%로 충분한 여유 리소스를 확보하고 있습니다"
   - "필요시 Auto-scaling으로 자동 확장이 가능합니다"

### Kiali에서
1. **실시간 서비스 메시 시각화**
   - "실시간으로 트래픽이 흐르는 것을 애니메이션으로 확인할 수 있습니다"
   - "서비스 간 의존성과 통신 패턴을 한눈에 파악할 수 있습니다"

2. **자동 보안 (mTLS)**
   - "모든 HTTP 서비스 간 통신이 자동으로 암호화됩니다 (mTLS)"
   - "별도 코드 수정 없이 Istio가 자동으로 보안을 제공합니다"
   - "데이터베이스는 TCP 프로토콜 호환성을 위해 mTLS 비활성화"

3. **완벽한 Istio 설정**
   - "Istio Config에서 0 errors, 0 warnings로 모든 설정이 유효합니다"
   - "VirtualService로 라우팅, DestinationRule로 트래픽 정책 관리"

4. **서비스 헬스 모니터링**
   - "모든 서비스가 Healthy 상태로 정상 운영 중입니다"
   - "각 서비스의 에러율, 응답 시간, 트래픽을 실시간 모니터링"

---

## 4. 문제 발생 시 대응

### Grafana에 데이터가 안 보일 때
1. **Prometheus 메트릭 수집 확인**
   ```bash
   kubectl get servicemonitors -n monitoring
   kubectl get podmonitors -n monitoring
   ```

2. **시간 범위 조정**
   - 대시보드 우측 상단의 시간 범위를 "Last 5m"에서 "Last 1h"로 변경
   - 최근 데이터가 없을 경우 과거 데이터 확인

3. **Prometheus 상태 확인**
   ```bash
   kubectl get pods -n monitoring | grep prometheus
   kubectl logs -n monitoring prometheus-kube-prometheus-stack-prometheus-0
   ```

### Kiali에 서비스가 안 보일 때
1. **네임스페이스 선택 확인**
   - 상단 Namespace 드롭다운에서 "titanium-prod" 선택 확인

2. **Time Range 조정**
   - Graph 화면 우측 상단 Time Range를 "Last 5m" 또는 "Last 1h"로 조정
   - 트래픽이 없으면 노드가 표시되지 않을 수 있음

3. **Graph Display 옵션 확인**
   - Display → Service Nodes 체크
   - Display → Traffic Animation 체크

4. **Istio Sidecar Injection 확인**
   ```bash
   kubectl get pods -n titanium-prod -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.containers[*].name}{"\n"}{end}'
   ```
   - "istio-proxy" 컨테이너가 있는지 확인

### mTLS 잠금 아이콘이 안 보일 때
1. **Display 옵션 확인**
   - Graph 화면 우측 상단 Display → Security 체크

2. **PeerAuthentication 설정 확인**
   ```bash
   kubectl get peerauthentication -n titanium-prod
   kubectl describe peerauthentication default-mtls -n titanium-prod
   ```

3. **Pod 재시작**
   - 설정 변경 후 즉시 반영 안 될 수 있음
   ```bash
   kubectl rollout restart deployment -n titanium-prod
   ```

### 특정 서비스만 에러가 발생할 때
1. **Kiali에서 해당 서비스 클릭**
   - Traffic 탭에서 에러율 확인
   - Logs 탭에서 실시간 로그 확인

2. **Pod 로그 직접 확인**
   ```bash
   kubectl logs -n titanium-prod <pod-name> -c <container-name>
   ```

3. **Istio Proxy 로그 확인**
   ```bash
   kubectl logs -n titanium-prod <pod-name> -c istio-proxy
   ```

---

**작성일**: 2025년 11월 3일
**최종 수정**: 실제 대시보드 구성에 맞게 업데이트

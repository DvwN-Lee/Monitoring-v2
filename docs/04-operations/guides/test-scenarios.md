---
version: 1.0
last_updated: 2025-11-15
author: Dongju Lee
---

# 모니터링 대시보드 테스트 시나리오

## 테스트 환경 정보

- 클러스터 IP: 10.0.11.168
- Grafana: http://10.0.11.168:30300
- Prometheus: http://10.0.11.168:30090
- Kiali: http://10.0.11.168:30164
- Loki: Grafana 데이터소스로 연결됨

## 1. Grafana 대시보드 테스트

### 1.1 대시보드 접근 및 로그인

**테스트 단계:**
1. 브라우저에서 http://10.0.11.168:30300 접속
2. 로그인 페이지 확인
3. 기본 자격증명으로 로그인 시도 (admin/prom-operator)

**예상 결과:**
- 로그인 페이지가 정상적으로 로드됨
- 로그인 후 Grafana 홈 대시보드로 이동

**확인 포인트:**
- 페이지 로딩 시간 (3초 이내)
- 로그인 폼의 정상 동작
- 세션 유지 확인

### 1.2 데이터소스 확인

**테스트 단계:**
1. 왼쪽 메뉴에서 "Connections" > "Data sources" 클릭
2. Prometheus 데이터소스 확인
3. Loki 데이터소스 확인
4. 각 데이터소스의 "Test" 버튼 클릭

**예상 결과:**
- Prometheus 데이터소스: 연결 성공
- Loki 데이터소스: 연결 성공
- "Data source is working" 메시지 표시

**확인 포인트:**
- 데이터소스 상태가 "Connected"로 표시
- 연결 테스트 응답 시간 (2초 이내)

### 1.3 대시보드 목록 확인

**테스트 단계:**
1. 왼쪽 메뉴에서 "Dashboards" 클릭
2. 대시보드 목록 로드 확인
3. "Titanium Monitoring Dashboard" 검색

**예상 결과:**
- 커스텀 대시보드가 목록에 표시됨
- 대시보드 이름, 폴더, 태그가 정확히 표시됨

**확인 포인트:**
- 대시보드 목록 로딩 시간
- 검색 기능 정상 동작

### 1.4 메트릭 시각화 확인

**테스트 단계:**
1. "Titanium Monitoring Dashboard" 클릭
2. 각 패널의 데이터 로드 확인
3. 시간 범위 변경 (Last 5 minutes → Last 1 hour)
4. 패널 새로고침 버튼 클릭

**예상 결과:**
- 모든 패널에 데이터가 표시됨
- 그래프가 정상적으로 렌더링됨
- 시간 범위 변경 시 데이터가 업데이트됨

**확인 포인트:**
- HTTP Request Rate 패널에 istio_requests_total 메트릭 표시
- Response Time P95 패널에 히스토그램 데이터 표시
- CPU/Memory 사용률 그래프 표시
- 에러 발생 시 "No data" 대신 적절한 메시지 표시

### 1.5 알림 규칙 확인

**테스트 단계:**
1. 왼쪽 메뉴에서 "Alerting" > "Alert rules" 클릭
2. 설정된 알림 규칙 목록 확인
3. 각 규칙의 상태 확인

**예상 결과:**
- HighErrorRate, HighLatency 등 알림 규칙이 표시됨
- 규칙 상태가 "Normal" 또는 "Pending"으로 표시

**확인 포인트:**
- 알림 규칙 개수
- 각 규칙의 임계값 설정 확인
- Alertmanager 연동 상태

## 2. Prometheus 대시보드 테스트

### 2.1 Prometheus UI 접근

**테스트 단계:**
1. 브라우저에서 http://10.0.11.168:30090 접속
2. Prometheus UI 로드 확인

**예상 결과:**
- Prometheus UI가 정상적으로 로드됨
- 상단 메뉴바에 "Graph", "Alerts", "Status" 탭 표시

**확인 포인트:**
- 페이지 응답 시간 (2초 이내)
- UI 레이아웃 정상 표시

### 2.2 메트릭 쿼리 테스트

**테스트 단계:**
1. "Graph" 탭 클릭
2. PromQL 쿼리 입력: `up`
3. "Execute" 버튼 클릭
4. "Graph" 탭과 "Table" 탭 전환 확인

**예상 결과:**
- 쿼리 실행 성공
- 모든 타겟의 up 상태(1) 표시
- 그래프와 테이블 뷰 정상 전환

**확인 포인트:**
- 쿼리 실행 시간 (1초 이내)
- 타겟 개수 확인 (최소 10개 이상)
- 그래프 렌더링 품질

### 2.3 서비스 메트릭 확인

**테스트 단계:**
1. PromQL 쿼리 입력: `istio_requests_total{namespace="titanium-prod"}`
2. "Execute" 버튼 클릭
3. 레이블 필터링 테스트: `istio_requests_total{namespace="titanium-prod", destination_service_name="prod-blog-service"}`

**예상 결과:**
- Istio 메트릭이 정상적으로 수집됨
- 각 서비스별 요청 수 표시
- 레이블 필터링 정상 동작

**확인 포인트:**
- 메트릭 시계열 개수
- 레이블 정확도 (namespace, service_name, response_code 등)
- 최신 데이터 시간 (현재 시간과 1분 이내 차이)

### 2.4 타겟 상태 확인

**테스트 단계:**
1. "Status" > "Targets" 클릭
2. 모든 ServiceMonitor 타겟 확인
3. 각 타겟의 "UP" 상태 확인

**예상 결과:**
- 모든 ServiceMonitor 타겟이 "UP" 상태
- 스크래핑 간격이 설정값(15s)과 일치
- 마지막 스크래핑 시간이 최신

**확인 포인트:**
- titanium-dev, titanium-staging, titanium-prod의 모든 서비스 포함
- 각 타겟의 labels/scrape 정보 정확성
- 에러 메시지 없음

### 2.5 알림 규칙 상태 확인

**테스트 단계:**
1. "Alerts" 탭 클릭
2. 활성 알림 규칙 목록 확인
3. 각 규칙의 현재 상태 확인

**예상 결과:**
- prometheus-rules.yaml에 정의된 모든 규칙 표시
- 대부분의 규칙이 "Inactive" 상태 (정상 운영 시)
- 규칙 평가 시간이 최신

**확인 포인트:**
- 알림 규칙 개수 (최소 5개 이상)
- expr 쿼리 정확성
- Alertmanager 연동 확인

## 3. Kiali 대시보드 테스트

### 3.1 Kiali UI 접근

**테스트 단계:**
1. 브라우저에서 http://10.0.11.168:30164 접속
2. Kiali 로그인 페이지 확인 (인증 필요 시)
3. Kiali 홈 화면 로드 확인

**예상 결과:**
- Kiali UI가 정상적으로 로드됨
- 왼쪽 메뉴에 "Overview", "Graph", "Applications", "Workloads", "Services" 표시

**확인 포인트:**
- 페이지 로딩 시간 (5초 이내)
- Istio 버전 정보 표시

### 3.2 네임스페이스 개요 확인

**테스트 단계:**
1. "Overview" 메뉴 클릭
2. titanium-dev, titanium-staging, titanium-prod 네임스페이스 확인
3. 각 네임스페이스의 애플리케이션 개수 확인

**예상 결과:**
- 3개 네임스페이스가 모두 표시됨
- 각 네임스페이스에 4개 애플리케이션 (api-gateway, auth-service, user-service, blog-service) 표시
- 헬스 상태가 녹색 (정상)

**확인 포인트:**
- 네임스페이스별 애플리케이션, 워크로드, 서비스 개수
- 에러율, 요청률 메트릭 표시
- mTLS 상태 표시 (잠금 아이콘)

### 3.3 서비스 그래프 확인

**테스트 단계:**
1. "Graph" 메뉴 클릭
2. 네임스페이스 선택: titanium-prod
3. Display 옵션: "Request Distribution", "Traffic Animation" 활성화
4. 그래프 레이아웃 변경 (Dagre → Kiali)

**예상 결과:**
- 서비스 간 트래픽 흐름이 시각화됨
- 화살표에 요청률(req/s) 표시
- 애니메이션이 실시간 트래픽을 표현

**확인 포인트:**
- api-gateway → (auth/user/blog)-service 연결 표시
- HTTP 응답 코드별 색상 구분 (200: 녹색, 4xx/5xx: 빨강)
- 각 엣지의 응답 시간 표시
- mTLS 잠금 아이콘 표시

### 3.4 애플리케이션 상세 정보 확인

**테스트 단계:**
1. "Applications" 메뉴 클릭
2. titanium-prod 네임스페이스의 "prod-blog" 애플리케이션 클릭
3. "Overview", "Traffic", "Inbound Metrics", "Outbound Metrics" 탭 확인

**예상 결과:**
- 애플리케이션 상세 정보 표시
- 트래픽 그래프에 인바운드/아웃바운드 요청 표시
- 메트릭 차트에 요청률, 응답시간, 에러율 표시

**확인 포인트:**
- 워크로드 개수 (Deployment 1개)
- 서비스 개수 (Service 1개)
- 메트릭 데이터 정확성 (Prometheus 데이터와 일치)
- Istio 설정 검증 (VirtualService, DestinationRule 등)

### 3.5 Istio Config 검증

**테스트 단계:**
1. "Istio Config" 메뉴 클릭
2. titanium-prod 네임스페이스 선택
3. VirtualService, DestinationRule 목록 확인
4. 각 설정의 유효성 검증 상태 확인

**예상 결과:**
- 모든 Istio Config가 "Valid" 상태
- VirtualService에 라우팅 규칙 정확히 표시
- DestinationRule에 mTLS 설정 표시

**확인 포인트:**
- Config 오류 없음 (빨간색 경고 없음)
- 각 설정의 YAML 정확성
- Gateway 설정 (있는 경우)

## 4. Loki 로그 쿼리 테스트 (Grafana Explore)

### 4.1 Grafana Explore 접근

**테스트 단계:**
1. Grafana에서 왼쪽 메뉴의 "Explore" 클릭
2. 데이터소스를 "Loki" 로 선택

**예상 결과:**
- Explore 페이지가 로드됨
- 상단 드롭다운에서 "Loki" 데이터소스 선택됨

**확인 포인트:**
- Loki 데이터소스 연결 상태
- LogQL 쿼리 입력창 표시

### 4.2 기본 로그 쿼리

**테스트 단계:**
1. LogQL 쿼리 입력: `{namespace="titanium-prod"}`
2. "Run query" 버튼 클릭
3. 로그 스트림 확인

**예상 결과:**
- titanium-prod 네임스페이스의 모든 로그 표시
- 로그 레벨, 타임스탬프, 메시지 정상 표시
- 스트림별로 그룹핑됨

**확인 포인트:**
- 로그 개수 (최소 100개 이상)
- 최신 로그 시간 (현재 시간과 1분 이내 차이)
- 로그 포맷 (JSON 또는 plain text)

### 4.3 서비스별 로그 필터링

**테스트 단계:**
1. LogQL 쿼리 입력: `{namespace="titanium-prod", app="prod-blog"}`
2. "Run query" 버튼 클릭
3. 로그 레벨 필터링: `{namespace="titanium-prod", app="prod-blog"} |= "error"`

**예상 결과:**
- prod-blog 서비스의 로그만 표시
- error 키워드가 포함된 로그만 필터링됨
- 로그 볼륨 그래프에 시계열 데이터 표시

**확인 포인트:**
- 레이블 필터링 정확성
- 텍스트 검색 정확성
- 로그 볼륨 그래프 렌더링

### 4.4 Istio 액세스 로그 확인

**테스트 단계:**
1. LogQL 쿼리 입력: `{namespace="titanium-prod"} |= "envoy"`
2. "Run query" 버튼 클릭
3. JSON 파싱: `{namespace="titanium-prod"} | json | response_code=200`

**예상 결과:**
- Istio sidecar(Envoy)의 액세스 로그 표시
- JSON 파싱 후 response_code 필드로 필터링됨
- HTTP 요청 정보 (method, path, status, duration) 표시

**확인 포인트:**
- Envoy 액세스 로그 포맷 확인
- JSON 필드 파싱 정상 동작
- 로그와 Prometheus 메트릭의 일관성

### 4.5 로그 집계 쿼리

**테스트 단계:**
1. LogQL 쿼리 입력: `sum(rate({namespace="titanium-prod"}[1m])) by (app)`
2. "Run query" 버튼 클릭
3. 시간 범위 변경: Last 1 hour

**예상 결과:**
- 각 애플리케이션의 로그 비율 그래프 표시
- 여러 앱의 로그 비율이 겹쳐서 표시됨
- 범례에 앱 이름 표시

**확인 포인트:**
- 집계 함수 정상 동작
- 그래프 렌더링 품질
- 데이터 정확성

## 테스트 체크리스트

### Grafana
- [ ] 로그인 성공
- [ ] Prometheus 데이터소스 연결
- [ ] Loki 데이터소스 연결
- [ ] 대시보드 로드 및 렌더링
- [ ] 메트릭 시각화 정상
- [ ] 알림 규칙 설정 확인

### Prometheus
- [ ] UI 접근 성공
- [ ] 기본 쿼리 실행
- [ ] Istio 메트릭 수집 확인
- [ ] ServiceMonitor 타겟 UP 상태
- [ ] 알림 규칙 로드 확인

### Kiali
- [ ] UI 접근 성공
- [ ] 네임스페이스 개요 표시
- [ ] 서비스 그래프 렌더링
- [ ] 트래픽 메트릭 표시
- [ ] Istio Config 검증 성공

### Loki
- [ ] Grafana Explore 접근
- [ ] 기본 로그 쿼리 성공
- [ ] 로그 필터링 정상
- [ ] Istio 액세스 로그 확인
- [ ] 로그 집계 쿼리 성공
다음은 요청하신 Kubernetes 모니터링 대시보드 테스트 시나리오입니다. 각 대시보드별로 자동화된 UI 테스트에 적합하도록 상세한 단계와 예상 결과를 포함하여 작성했습니다.

---

## Kubernetes 모니터링 대시보드 테스트 시나리오

### 1. Grafana 대시보드 테스트

- **대시보드 URL**: `http://10.0.11.168:30300`
- **접근 방법**: 웹 브라우저를 통해 NodePort 주소로 직접 접근. (초기 ID/PW는 `admin`/`prom-operator` 또는 설치 시 설정된 값일 수 있음)

#### 1.1. 핵심 기능 검증 목록
- [ ] Grafana 접속 및 기본 대시보드 확인
- [ ] Kubernetes 클러스터 전체 현황 대시보드 검증
- [ ] 마이크로서비스별 상세 성능 대시보드 검증
- [ ] Loki 데이터소스를 이용한 로그 쿼리 검증

#### 1.2. 상세 테스트 단계 및 예상 결과

**시나리오 1: Kubernetes 클러스터 리소스 대시보드 검증**
1.  **단계 1**: `http://10.0.11.168:30300` URL로 이동하여 Grafana에 로그인합니다.
2.  **단계 2**: 왼쪽 메뉴에서 'Dashboards' 아이콘을 클릭합니다.
3.  **단계 3**: 'Browse' 탭에서 'Kubernetes / Compute Resources / Cluster' 대시보드를 찾아 클릭합니다.
4.  **단계 4**: 대시보드가 로딩되고 CPU, Memory, Filesystem 사용량과 같은 패널들이 나타나는지 확인합니다.
5.  **예상 결과**:
    - 대시보드 내 모든 패널에 'No data' 또는 에러 메시지 없이 데이터가 정상적으로 시각화됩니다.
    - 클러스터의 전체 CPU 사용량, 메모리 사용량, Pod 용량 등의 메트릭이 실시간으로 표시됩니다.
6.  **주요 확인 포인트**:
    - `node_cpu_seconds_total`, `node_memory_MemAvailable_bytes` 등 핵심 노드 메트릭 수집 여부.
    - 패널의 시간 범위(Time range)를 변경했을 때 데이터가 올바르게 다시 그려지는지 확인.

**시나리오 2: `user-service` 성능 대시보드 검증**
1.  **단계 1**: 'Dashboards' -> 'Browse' 메뉴로 이동합니다.
2.  **단계 2**: 'Istio / Istio Service Dashboard' 또는 유사한 이름의 서비스 메시 대시보드를 클릭합니다.
3.  **단계 3**: 대시보드 상단의 'Namespace' 드롭다운에서 `dev`를 선택합니다.
4.  **단계 4**: 'Service' 드롭다운에서 `user-service.dev.svc.cluster.local`을 선택합니다.
5.  **단계 5**: 'Client/Server Request Volume', 'Success Rate', 'Request Duration' 패널들을 확인합니다.
6.  **예상 결과**:
    - `user-service`에 대한 요청량(RPS), 성공률(%), 95/99 percentile 응답 시간 데이터가 표시됩니다.
    - 서버 측과 클라이언트 측 메트릭이 모두 정상적으로 나타납니다.
7.  **주요 확인 포인트**:
    - `istio_requests_total`, `istio_request_duration_milliseconds_bucket` 등 Istio 표준 메트릭이 Prometheus로부터 정상 수집되는지 확인.
    - 부하 테스트(load-tests) 실행 시 관련 메트릭이 동적으로 변화하는지 확인.

**시나리오 3: Loki를 통한 `auth-service` 로그 검색**
1.  **단계 1**: 왼쪽 메뉴에서 'Explore' 아이콘을 클릭합니다.
2.  **단계 2**: 화면 상단의 데이터소스 드롭다운에서 'Loki'를 선택합니다.
3.  **단계 3**: LogQL 쿼리 입력창에 `{namespace="prod", app="auth-service"}`를 입력하고 'Run query' 버튼을 클릭합니다.
4.  **단계 4**: 쿼리 결과로 `auth-service`의 로그가 시간순으로 표시되는지 확인합니다.
5.  **단계 5**: 쿼리를 `{namespace="prod", app="auth-service"} |= "error"`로 수정하여 에러 로그만 필터링되는지 확인합니다.
6.  **예상 결과**:
    - 지정된 네임스페이스와 앱 라벨에 해당하는 로그 스트림이 정상적으로 조회됩니다.
    - 라인 필터(`|=`)를 사용한 로그 내용 검색이 정확하게 동작합니다.
7.  **주요 확인 포인트**:
    - Grafana와 Loki 데이터소스 연결 상태.
    - Promtail 또는 Loki 에이전트가 각 Pod로부터 로그를 수집하고 `app`, `namespace` 등의 라벨을 올바르게 첨부하는지 확인.

---

### 2. Prometheus 대시보드 테스트

- **대시보드 URL**: `http://10.0.11.168:30090`
- **접근 방법**: 웹 브라우저를 통해 NodePort 주소로 직접 접근.

#### 2.1. 핵심 기능 검증 목록
- [ ] Prometheus 접속 및 UI 확인
- [ ] PromQL 쿼리를 통한 메트릭 조회
- [ ] 서비스 디스커버리 타겟 상태 확인 (`/targets`)

#### 2.2. 상세 테스트 단계 및 예상 결과

**시나리오 1: PromQL을 이용한 메트릭 직접 조회**
1.  **단계 1**: `http://10.0.11.168:30090` URL로 이동하여 Prometheus UI에 접근합니다.
2.  **단계 2**: 상단 메뉴에서 'Graph'를 클릭합니다.
3.  **단계 3**: 'Expression' 입력창에 `up{job="kubelet"}` 쿼리를 입력하고 'Execute' 버튼을 클릭합니다.
4.  **단계 4**: 쿼리 결과로 각 노드의 kubelet 상태를 나타내는 시계열 데이터가 'Table' 뷰에 표시되는지 확인합니다.
5.  **예상 결과**:
    - 쿼리 결과로 하나 이상의 시계열 데이터가 반환되며, 값은 `1` (up) 이어야 합니다.
    - `instance`, `job` 등의 라벨이 올바르게 표시됩니다.
6.  **주요 확인 포인트**:
    - Prometheus가 Kubernetes API와 통신하여 서비스 디스커버리를 수행하는지 여부.

**시나리오 2: 서비스 모니터링 타겟 상태 검증**
1.  **단계 1**: Prometheus UI 상단 메뉴에서 'Status' -> 'Targets'를 클릭합니다.
2.  **단계 2**: 타겟 목록에서 `serviceMonitor/dev/api-gateway/0`, `serviceMonitor/staging/user-service/0` 등과 같이 마이크로서비스별로 생성된 타겟들을 찾습니다.
3.  **단계 3**: 각 타겟의 'State'가 'UP'인지 확인합니다.
4.  **예상 결과**:
    - `api-gateway`, `auth-service`, `user-service`, `blog-service`에 대한 모든 타겟의 상태가 'UP'으로 표시됩니다.
    - 'Last Scrape' 시간이 최근으로 표시되며, 'Scrape Duration'이 비정상적으로 길지 않아야 합니다.
5.  **주요 확인 포인트**:
    - `ServiceMonitor` CRD가 올바르게 생성되었고 Prometheus Operator가 이를 인지하여 scrape 설정을 동적으로 생성했는지 확인.
    - 서비스 Pod에 `/metrics` 엔드포인트가 노출되어 있고, 네트워크 정책(NetworkPolicy)에 의해 접근이 차단되지 않는지 확인.

---

### 3. Kiali 대시보드 테스트

- **대시보드 URL**: `http://10.0.11.168:30164`
- **접근 방법**: 웹 브라우저를 통해 NodePort 주소로 직접 접근. (Istio 설치 시 설정된 인증 방식에 따라 로그인 필요)

#### 3.1. 핵심 기능 검증 목록
- [ ] Kiali 접속 및 서비스 그래프 시각화
- [ ] 네임스페이스별 서비스 토폴로지 확인
- [ ] 서비스 상세 정보 및 인/아웃바운드 트래픽 확인

#### 3.2. 상세 테스트 단계 및 예상 결과

**시나리오 1: `prod` 네임스페이스 서비스 그래프 검증**
1.  **단계 1**: `http://10.0.11.168:30164` URL로 이동하여 Kiali 대시보드에 로그인합니다.
2.  **단계 2**: 왼쪽 메뉴에서 'Graph'를 클릭합니다.
3.  **단계 3**: 상단 'Namespace' 셀렉트 박스에서 `prod`를 선택합니다.
4.  **단계 4**: 'Display' 드롭다운 메뉴에서 'Traffic Animation'과 'Response Time' 엣지 라벨을 활성화합니다.
5.  **예상 결과**:
    - `prod` 네임스페이스의 서비스들(`api-gateway`, `auth-service` 등)과 외부 트래픽(ingress) 간의 관계가 그래프로 시각화됩니다.
    - 서비스 간 연결선(edge) 위로 트래픽 흐름을 나타내는 애니메이션이 표시됩니다.
    - 각 연결선에는 95th percentile 응답 시간이 표시됩니다.
6.  **주요 확인 포인트**:
    - Istio Proxy(Envoy)가 각 서비스 Pod에 정상적으로 주입(injection)되었는지 확인.
    - Prometheus의 `istio_*` 메트릭을 Kiali가 올바르게 수집하여 그래프를 생성하는지 확인.

**시나리오 2: `blog-service` 상세 정보 및 트래픽 검증**
1.  **단계 1**: 'Graph' 뷰 또는 왼쪽 'Applications' 메뉴에서 `blog-service`를 찾아 클릭합니다.
2.  **단계 2**: `blog-service`의 상세 페이지로 이동되는지 확인합니다.
3.  **단계 3**: 'Traffic' 탭을 클릭하여 인바운드/아웃바운드 트래픽 정보를 확인합니다.
4.  **단계 4**: 'Inbound Metrics' 탭에서 `api-gateway`로부터 들어오는 트래픽의 상세 메트릭(RPS, 에러율, 응답 시간 등)을 확인합니다.
5.  **예상 결과**:
    - `blog-service`로 들어오고 나가는 트래픽의 소스-목적지 관계가 명확히 표시됩니다.
    - 상세 메트릭 그래프들이 Grafana와 유사한 형태로 시각화됩니다.
6.  **주요 확인 포인트**:
    - Kiali가 Istio의 `VirtualService`, `DestinationRule` 등 CRD 정보를 올바르게 파싱하여 보여주는지 확인.
    - 트래픽이 없을 경우 "No traffic" 메시지가 표시되고, 트래픽 발생 시 데이터가 즉시 반영되는지 확인.

---

### 4. Loki 로그 쿼리 (Grafana Explore 통합 테스트)

- **접근 방법**: Grafana UI 내 'Explore' 기능을 통해 Loki 데이터소스 접근.

#### 4.1. 핵심 기능 검증 목록
- [ ] Grafana의 Explore 뷰를 통한 Loki 데이터소스 접근
- [ ] LogQL 기본 쿼리 실행 및 로그 스트림 확인
- [ ] 필터링 및 파싱을 통한 고급 로그 분석

#### 4.2. 상세 테스트 단계 및 예상 결과

**시나리오 1: 전체 네임스페이스 로그 조회**
1.  **단계 1**: Grafana에서 'Explore' 메뉴로 이동합니다.
2.  **단계 2**: 데이터소스 선택 드롭다운에서 'Loki'를 선택합니다.
3.  **단계 3**: LogQL 쿼리 입력창에 `{namespace=~"titanium-.*"}`를 입력하고 실행합니다.
4.  **예상 결과**:
    - `titanium-dev`, `titanium-staging`, `titanium-prod` 네임스페이스의 모든 로그가 시간순으로 정렬되어 표시됩니다.
    - 각 로그 라인에 네임스페이스, Pod 이름, 컨테이너 이름 등의 메타데이터가 함께 표시됩니다.
5.  **주요 확인 포인트**:
    - 로그 볼륨 그래프가 정상적으로 렌더링되어 시간대별 로그 발생량을 시각화하는지 확인.

**시나리오 2: JSON 로그 파싱 및 필터링**
1.  **단계 1**: LogQL 쿼리를 `{namespace="titanium-prod"} | json | level="error"`로 작성하여 실행합니다.
2.  **단계 2**: 파싱된 JSON 필드가 테이블 형태로 표시되는지 확인합니다.
3.  **예상 결과**:
    - `level` 필드가 `error`인 로그만 필터링되어 표시됩니다.
    - JSON 필드들이 개별 컬럼으로 구조화되어 읽기 편한 형태로 나타납니다.
4.  **주요 확인 포인트**:
    - 애플리케이션에서 구조화된 로그(Structured Logging)를 사용하고 있는지 확인.

---

## 통합 테스트 체크리스트

### Grafana
- [ ] Grafana 대시보드 접속 성공
- [ ] Prometheus 데이터소스 정상 작동
- [ ] Loki 데이터소스 정상 작동
- [ ] 최소 2개 이상의 대시보드가 데이터를 표시함
- [ ] Alerting 규칙이 설정되어 있고 상태가 정상임

### Prometheus
- [ ] Prometheus UI 접속 성공
- [ ] 기본 PromQL 쿼리 실행 성공
- [ ] ServiceMonitor 타겟들이 모두 'UP' 상태
- [ ] Istio 메트릭이 정상적으로 수집되고 있음

### Kiali
- [ ] Kiali UI 접속 성공
- [ ] 서비스 그래프가 정상적으로 시각화됨
- [ ] 최소 하나의 네임스페이스에서 트래픽 흐름 확인
- [ ] 서비스 상세 정보 및 메트릭이 표시됨

### Loki (Grafana Explore)
- [ ] Grafana Explore에서 Loki 데이터소스 접근 성공
- [ ] 기본 LogQL 쿼리 실행 성공
- [ ] 로그 필터링 및 파싱 기능 정상 작동
- [ ] 로그 볼륨 그래프가 표시됨

---

## Chrome DevTools Protocol 자동화 참고 사항

위 테스트 시나리오를 Chrome DevTools Protocol 기반 자동화 스크립트로 변환할 때 다음 사항을 고려하세요:

1.  **페이지 로딩 대기**: `Page.loadEventFired`를 활용하여 각 단계 후 페이지가 완전히 로드될 때까지 대기합니다.
2.  **요소 선택**: CSS 셀렉터 또는 XPath를 사용하여 버튼, 입력창 등을 정확히 찾습니다. 예: `document.querySelector('[data-testid="explore-tab"]')`.
3.  **동적 콘텐츠 대기**: AJAX 요청 후 렌더링되는 데이터는 `MutationObserver`를 사용하거나 일정 시간 대기(`setTimeout`) 후 확인합니다.
4.  **스크린샷 캡처**: 각 테스트 시나리오 완료 시 `Page.captureScreenshot`을 사용하여 스크린샷을 저장하면 디버깅에 유용합니다.
5.  **네트워크 요청 모니터링**: `Network.enable`을 활성화하고 `Network.responseReceived` 이벤트를 수신하여 API 응답 상태 코드를 검증할 수 있습니다.

---

이상으로 Grafana, Prometheus, Kiali, Loki 대시보드에 대한 상세 테스트 시나리오를 작성했습니다. 각 시나리오는 수동 테스트와 자동화된 UI 테스트 양쪽에서 활용할 수 있도록 구성했습니다.
Loaded cached credentials.
네, 알겠습니다. Chrome DevTools Protocol(CDP)을 활용한 자동화 테스트에 적합하도록, 제공해주신 프로젝트 정보를 바탕으로 상세한 UI/UX 테스트 시나리오를 작성해 드리겠습니다.

다음은 블로그 서비스와 모니터링 대시보드 UI에 대한 포괄적인 테스트 시나리오입니다.

***

## Chrome DevTools Protocol 기반 UI/UX 자동화 테스트 시나리오

### 1. 블로그 서비스 UI (Blog Service UI)

- **Target URL:** `http://10.0.11.168:31304/blog/`
- **주요 기술:** Python FastAPI (Jinja2 템플릿), JavaScript (Fetch API), Bootstrap

#### 1.1. 핵심 사용자 시나리오 (User Flow)

**시나리오 1: 비로그인 사용자의 게시물 조회**
1.  **[Navigate]** 블로그 메인 페이지 접속
2.  **[Verify]** 페이지 타이틀이 "블로그"인지 확인
3.  **[Verify]** 게시물 목록이 1개 이상 표시되는지 확인
4.  **[Action]** "CI/CD" 카테고리 필터 클릭
5.  **[Verify]** URL이 `?category=CI/CD` 와 같이 변경되고, 해당 카테고리 게시물만 필터링되어 표시되는지 확인
6.  **[Action]** 첫 번째 게시물 제목 클릭
7.  **[Verify]** 게시물 상세 페이지로 이동하고, 해당 게시물의 제목과 내용이 올바르게 표시되는지 확인
8.  **[Action]** 브라우저 '뒤로 가기' 기능 실행
9.  **[Verify]** 이전의 필터링된 게시물 목록 페이지로 돌아오는지 확인
10. **[Action]** 페이지네이션(Pagination)의 '2'번 또는 '다음' 버튼 클릭
11. **[Verify]** 다음 페이지의 게시물 목록이 로드되는지 확인

**시나리오 2: 신규 사용자 회원가입 및 자동 로그인**
1.  **[Navigate]** 블로그 메인 페이지 접속
2.  **[Action]** 네비게이션 바의 '회원가입' 버튼 클릭
3.  **[Verify]** 회원가입 모달 창이 표시되는지 확인
4.  **[Action]** 사용자 이름(`testuser_` + timestamp), 비밀번호(`password123!`) 입력
5.  **[Action]** '가입' 버튼 클릭
6.  **[Verify]** "회원가입이 완료되었습니다." 와 같은 성공 메시지 확인
7.  **[Verify]** 모달이 닫히고, 네비게이션 바에 '로그아웃'과 '새 글 작성' 버튼이 표시되는지 확인 (자동 로그인 검증)

**시나리오 3: 기존 사용자 로그인 후 게시물 작성, 수정, 삭제**
1.  **[Navigate]** 블로그 메인 페이지 접속
2.  **[Action]** 네비게이션 바의 '로그인' 버튼 클릭
3.  **[Action]** 사용자 이름(`testuser`), 비밀번호(`password`) 입력 후 '로그인' 버튼 클릭
4.  **[Verify]** 네비게이션 바에 '로그아웃'과 '새 글 작성' 버튼이 표시되는지 확인
5.  **[Action]** '새 글 작성' 버튼 클릭
6.  **[Verify]** 글 작성 페이지로 이동하는지 확인
7.  **[Action]** 제목("자동화 테스트 게시물"), 내용("이것은 CDP를 통해 작성된 테스트입니다."), 카테고리("Test") 선택 후 '저장' 버튼 클릭
8.  **[Verify]** 메인 페이지로 리디렉션되고, 방금 작성한 게시물이 목록 최상단에 표시되는지 확인
9.  **[Action]** 방금 작성한 게시물의 '수정' 버튼 클릭
10. **[Action]** 제목을 "자동화 테스트 게시물 (수정됨)"으로 변경 후 '저장' 버튼 클릭
11. **[Verify]** 메인 페이지에서 게시물 제목이 수정되었는지 확인
12. **[Action]** 해당 게시물의 '삭제' 버튼 클릭
13. **[Action]** 브라우저의 `confirm()` 대화상자에서 '확인' 클릭
14. **[Verify]** 해당 게시물이 목록에서 사라졌는지 확인

#### 1.2. 테스트 UI 요소 및 상호작용

-   **네비게이션 바:** 로고, 홈, 로그인/로그아웃, 회원가입, 새 글 작성 버튼
-   **게시물 목록 (`.post-item`):** 제목, 작성자, 작성일, 카테고리 태그
-   **카테고리 필터 (`.category-filter`):** 각 카테고리 링크 (인프라, CI/CD 등)
-   **페이지네이션 (`.pagination`):** 이전/다음, 페이지 번호 링크
-   **모달 (`#loginModal`, `#signupModal`):** 입력 필드(username, password), 액션 버튼
-   **글 작성/수정 폼:** 제목/내용 입력 필드, 카테고리 선택 드롭다운, 저장 버튼
-   **게시물 상세:** 제목, 내용, 댓글(구현된 경우)
-   **버튼:** 수정, 삭제 버튼

#### 1.3. 예상 결과 및 검증 포인트

-   **API 호출 검증:** CDP의 `Network` 도메인을 사용하여 각 상호작용 시 예상되는 API 요청(메서드, URL, 페이로드)과 응답(상태 코드 200/201)을 확인.
    -   `GET /blog/api/posts?category=...`
    -   `POST /blog/api/users/signup`
    -   `POST /blog/api/users/login`
    -   `POST /blog/api/posts`
    -   `PUT /blog/api/posts/{id}`
    -   `DELETE /blog/api/posts/{id}`
-   **DOM 상태 검증:** 액션 이후 DOM이 예상대로 변경되었는지 확인. (예: 로그인 후, `#login-button`이 사라지고 `#logout-button`이 나타남)
-   **쿠키/로컬 스토리지 검증:** 로그인 시 `access_token`과 같은 인증 토큰이 저장되는지 확인.

#### 1.4. 성능 및 접근성 고려사항

-   **성능 (Performance):**
    -   `Performance.getMetrics`를 사용하여 LCP(Largest Contentful Paint), CLS(Cumulative Layout Shift) 등 Core Web Vitals 측정.
    -   게시물 100개 이상일 때 페이지네이션 및 필터링 성능 측정. API 응답 시간이 200ms 이내인지 확인.
-   **접근성 (Accessibility):**
    -   CDP의 `Accessibility.getFullAXTree`를 사용하여 접근성 트리 스냅샷 생성.
    -   모든 버튼과 링크에 `aria-label` 또는 명확한 텍스트가 있는지 확인.
    -   `Tab` 키를 이용한 키보드 네비게이션이 논리적 순서로 동작하는지 테스트.

#### 1.5. 에러 케이스 및 엣지 케이스

-   **로그인 실패:** 잘못된 비밀번호 입력 시 "아이디 또는 비밀번호가 올바르지 않습니다." 메시지 표시 확인.
-   **회원가입 실패:** 이미 존재하는 사용자 이름으로 가입 시도 시 "이미 존재하는 사용자입니다." 메시지 확인.
-   **폼 유효성 검사:** 글 작성 시 제목이나 내용을 비워두고 저장 시도 시 "필수 입력 항목입니다."와 같은 경고 확인.
-   **권한 없음:** 로그인하지 않은 상태에서 글 작성 페이지 URL(`.../create`)로 직접 접근 시 로그인 페이지로 리디렉션되는지 확인.
-   **API 서버 오류:** 백엔드 API가 500 에러를 반환할 때, UI가 깨지지 않고 "일시적인 오류가 발생했습니다."와 같은 사용자 친화적 메시지를 표시하는지 확인. (Mocking 필요)
-   **데이터 없음:** 특정 카테고리에 게시물이 없을 경우, "표시할 게시물이 없습니다." 메시지 확인.

---

### 2. 모니터링 대시보드 UI (Dashboard UI)

-   **Target URL:** `http://10.0.11.168:30300` (Grafana) 또는 별도 Dashboard UI URL
-   **주요 기술:** JavaScript (React/Vue 등 SPA 가능성), Chart.js/D3.js, WebSocket

#### 2.1. 핵심 사용자 시나리오 (User Flow)

**시나리오 1: 대시보드 초기 로딩 및 실시간 데이터 확인**
1.  **[Navigate]** 대시보드 페이지 접속
2.  **[Verify]** 페이지가 3초 이내에 로드되고, 모든 차트와 패널의 레이아웃이 깨지지 않는지 확인.
3.  **[Verify]** '서비스별 상태' 패널에 `api-gateway`, `auth-service`, `blog-service` 등이 'Healthy' 또는 녹색 상태로 표시되는지 확인.
4.  **[Verify]** '처리량(RPS)' 및 '응답시간' 차트에 데이터가 렌더링되는지 확인.
5.  **[Wait]** 15초 대기 (Grafana 등 대시보드의 일반적인 refresh 주기).
6.  **[Verify]** 차트 데이터가 자동으로 업데이트되는지 확인 (이전 스냅샷과 비교).
7.  **[Verify]** 'Load Balancer 로그' 패널에 새로운 로그가 스트리밍되는지 확인.

**시나리오 2: 차트 상호작용**
1.  **[Action]** '응답시간' 차트 위로 마우스 커서 이동.
2.  **[Verify]** 특정 시간대의 p99, p95, p50 응답시간을 보여주는 툴팁(Tooltip)이 표시되는지 확인.
3.  **[Action]** (시간 범위 선택 기능이 있다면) 시간 범위를 '지난 1시간'에서 '지난 6시간'으로 변경.
4.  **[Verify]** 모든 차트가 새로운 시간 범위에 맞춰 데이터와 X축을 다시 렌더링하는지 확인.

#### 2.2. 테스트 UI 요소 및 상호작용

-   **패널/위젯:** 서비스 상태, RPS, 응답시간, 알람, 로그 뷰어 등 각 대시보드 구성 요소.
-   **차트 (`<canvas>` 또는 `<svg>`):** 라인/바 차트의 데이터 포인트.
-   **툴팁:** 차트 호버 시 나타나는 정보 창.
-   **시간 범위 선택기:** '지난 5분', '지난 1시간' 등.
-   **상태 표시기:** 서비스별 상태를 나타내는 아이콘 또는 텍스트 (예: 녹색 점).

#### 2.3. 예상 결과 및 검증 포인트

-   **데이터 정확성:** Prometheus/Loki에서 직접 쿼리한 결과와 대시보드에 표시되는 값이 일치하는지 비교. (자동화 시, 특정 시점의 API 응답을 스냅샷으로 저장 후 비교)
-   **WebSocket 연결:** `Network` 탭에서 WebSocket 연결이 수립되고 데이터가 주기적으로 수신되는지 확인.
-   **동적 업데이트:** `requestAnimationFrame` 또는 주기적인 `fetch` 호출을 통해 DOM이 업데이트되는 것을 감지.

#### 1.4. 성능 및 접근성 고려사항

-   **성능:**
    -   장시간(예: 1시간) 대시보드를 열어 두었을 때 메모리 누수(Memory Leak)가 없는지 `Performance.getMetrics`로 확인.
    -   데이터 포인트가 수천 개 이상일 때도 UI가 버벅이지 않고 부드럽게 상호작용되는지 확인.
-   **접근성:**
    -   차트 데이터는 시각 정보 외에 테이블 형태로도 제공되는지 확인.
    -   상태를 나타내는 색상(빨강/녹색) 외에 텍스트나 아이콘으로도 상태를 명시하는지 확인 (색맹 사용자 고려).

#### 1.5. 에러 케이스 및 엣지 케이스

-   **데이터 소스 연결 실패:** Grafana가 Prometheus/Loki에 연결할 수 없을 때, 각 패널에 "Data source error"와 같은 명확한 오류 메시지가 표시되는지 확인.
-   **데이터 없음 (No Data):** 특정 기간에 메트릭이 없을 경우, 차트에 "No data"라고 표시되는지 확인.
-   **알람 발생:** Prometheus Alertmanager에서 의도적으로 알람을 발생시킨 후, 대시보드의 '알람' 패널에 해당 알람이 빨간색으로 표시되는지 확인.
-   **급격한 로그 증가:** Load Balancer에 초당 수백 개의 로그가 발생할 때, 로그 뷰어가 UI를 멈추게 하지 않고 정상적으로 스크롤 및 렌더링되는지 확인.

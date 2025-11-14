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

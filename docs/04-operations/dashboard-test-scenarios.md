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

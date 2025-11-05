# Week 3 트러블슈팅 가이드: 모니터링 스택

이 문서는 Prometheus, Grafana, Loki로 구성된 모니터링 스택을 운영하면서 발생할 수 있는 일반적인 문제와 해결 방법을 다룹니다.

---

## 1. Prometheus & Grafana 설치 문제

### 문제 1: Prometheus/Grafana 파드(Pod)가 `Pending` 상태에 머무름

- **원인**: 클러스터에 가용한 리소스(CPU, 메모리)가 부족하거나, PersistentVolumeClaim(PVC)을 바인딩할 수 없는 경우입니다.
- **해결 방법**:
  1.  **리소스 확인**: `kubectl describe pod <pod-name> -n monitoring` 명령어로 파드의 이벤트를 확인하여 리소스 부족 메시지가 있는지 확인합니다.
  2.  **노드 용량 확인**: `kubectl top nodes` 또는 `kubectl describe nodes`로 각 노드의 리소스 사용량을 점검합니다.
  3.  **PVC 상태 확인**: `kubectl get pvc -n monitoring`으로 PVC 상태를 확인합니다. `Pending` 상태라면 스토리지 클래스(StorageClass) 설정이 올바른지, 동적 프로비저닝이 정상 동작하는지 확인해야 합니다.

### 문제 2: Grafana에 접속할 수 없음

- **원인**: 서비스(Service) 타입이 잘못되었거나, 인그레스(Ingress) 설정이 없거나, 네트워크 정책(NetworkPolicy)에 의해 접근이 차단된 경우입니다.
- **해결 방법**:
  1.  **서비스 확인**: `kubectl get svc -n monitoring grafana` 명령어로 Grafana 서비스의 타입(`ClusterIP`, `NodePort`, `LoadBalancer`)과 포트를 확인합니다.
  2.  **포트 포워딩 (테스트용)**: `kubectl port-forward -n monitoring svc/grafana 3000:3000` 명령어로 로컬에서 접속을 시도하여 Grafana 자체의 동작 여부를 확인합니다.
  3.  **인그레스/네트워크 정책**: 인그레스 컨트롤러 로그를 확인하거나, 네트워크 정책이 Grafana로의 트래픽을 허용하는지 검토합니다.

---

## 2. 애플리케이션 메트릭 수집 문제

### 문제 1: Prometheus UI의 Targets 페이지에 애플리케이션이 보이지 않음

- **원인**: ServiceMonitor가 Prometheus에 의해 선택되지 않았거나, ServiceMonitor가 애플리케이션 서비스를 제대로 찾지 못하는 경우입니다.
- **해결 방법**:
  1.  **레이블 확인**: ServiceMonitor에 `release: prometheus`와 같은 Prometheus Operator가 인식하는 레이블이 있는지 확인합니다.
  2.  **네임스페이스 확인**: ServiceMonitor의 `namespaceSelector`가 애플리케이션이 배포된 네임스페이스를 올바르게 가리키고 있는지 확인합니다.
  3.  **서비스 레이블 확인**: ServiceMonitor의 `selector`가 애플리케이션 서비스의 레이블과 일치하는지 확인합니다.
  4.  **Prometheus 설정**: Prometheus CRD의 `serviceMonitorSelector`가 ServiceMonitor의 레이블과 일치하는지 확인합니다.

### 문제 2: Targets 페이지에 애플리케이션은 보이지만 상태가 `DOWN`임

- **원인**: Prometheus 파드가 애플리케이션의 메트릭 엔드포인트(`/metrics`)에 접근할 수 없거나, 엔드포인트가 실제로 존재하지 않는 경우입니다.
- **해결 방법**:
  1.  **엔드포인트 확인**: `kubectl get endpoints -n <app-namespace> <service-name>` 명령어로 서비스에 연결된 파드의 IP와 포트가 올바른지 확인합니다.
  2.  **네트워크 연결 테스트**: Prometheus 파드에 접속하여(`kubectl exec -it ...`) `curl` 명령어로 애플리케이션의 메트릭 엔드포인트에 직접 접근을 시도해 봅니다. (`curl http://<pod-ip>:<port>/metrics`)
  3.  **네트워크 정책**: Prometheus 네임스페이스에서 애플리케이션 네임스페이스로의 트래픽을 허용하는 네트워크 정책이 있는지 확인합니다.

---

## 3. Grafana 대시보드 문제

### 문제 1: 대시보드가 자동으로 로드되지 않음

- **원인**: 대시보드 ConfigMap이 잘못된 형식으로 생성되었거나, Grafana의 sidecar/provider 설정이 잘못된 경우입니다.
- **해결 방법**:
  1.  **ConfigMap 레이블 확인**: 대시보드를 담고 있는 ConfigMap에 `grafana_dashboard: "1"` 레이블이 있는지 확인합니다.
  2.  **Grafana 설정 확인**: Grafana의 `dashboardproviders.yaml` 설정에서 대시보드를 스캔하는 경로(`path`)가 ConfigMap이 마운트된 경로와 일치하는지 확인합니다.
  3.  **Grafana 파드 로그**: Grafana 파드의 로그를 확인하여 대시보드를 로드하는 과정에서 발생하는 오류 메시지를 확인합니다.

### 문제 2: 대시보드에 데이터가 보이지 않거나 "N/A"로 표시됨

- **원인**: PromQL 쿼리가 잘못되었거나, Prometheus 데이터소스가 잘못 설정되었거나, 시간 범위(time range)에 데이터가 없는 경우입니다.
- **해결 방법**:
  1.  **데이터소스 확인**: Grafana의 `Settings -> Data Sources`에서 Prometheus 데이터소스 연결을 테스트하여 성공하는지 확인합니다.
  2.  **쿼리 테스트**: 대시보드 패널의 PromQL 쿼리를 복사하여 Prometheus UI의 Graph 탭에서 직접 실행해 봅니다. 결과가 나오는지 확인합니다.
  3.  **시간 범위 조정**: Grafana 대시보드의 우측 상단 시간 범위를 늘려 데이터가 수집된 기간을 포함하는지 확인합니다.
  4.  **레이블 확인**: PromQL 쿼리에 사용된 레이블(`job`, `service`, `instance` 등)이 실제 메트릭에 존재하는지 확인합니다.

---

## 4. Loki 로깅 시스템 문제

### 문제 1: Grafana의 Explore 탭에서 로그가 보이지 않음

- **원인**: Promtail이 로그를 수집하지 못하거나, Loki로 전송하지 못하거나, Grafana의 Loki 데이터소스 설정이 잘못된 경우입니다.
- **해결 방법**:
  1.  **Promtail 파드 로그 확인**: `kubectl logs -n monitoring -l app.kubernetes.io/name=promtail` 명령어로 Promtail 파드의 로그를 확인하여 Loki 서버로의 연결 오류나 파일 읽기 오류가 없는지 확인합니다.
  2.  **Loki 데이터소스 확인**: Grafana에서 Loki 데이터소스 연결을 테스트합니다.
  3.  **레이블 확인**: Promtail 설정에서 로그를 수집할 파드의 레이블이나 네임스페이스가 올바르게 지정되었는지 확인합니다.
  4.  **LogQL 쿼리 확인**: Grafana Explore 탭에서 가장 기본적인 LogQL 쿼리(`{job="kubernetes-pods"}`)를 실행하여 어떤 로그 스트림이라도 보이는지 확인합니다.

### 문제 2: 애플리케이션의 JSON 로그가 파싱되지 않음

- **원인**: Promtail의 파이프라인 설정에 JSON 파싱 단계가 없거나, 로그가 유효한 JSON 형식이 아닌 경우입니다.
- **해결 방법**:
  1.  **Promtail 설정 확인**: Promtail의 `pipeline_stages` 설정에 `json` 단계가 포함되어 있는지 확인합니다.
    ```yaml
    pipeline_stages:
    - json:
        expressions: { level: level, message: msg }
    ```
  2.  **로그 형식 확인**: `kubectl logs <pod-name>` 명령어로 실제 로그가 한 줄에 하나의 유효한 JSON 객체 형식으로 출력되는지 확인합니다.

---

## 5. Alertmanager 알림 문제

### 문제 1: Prometheus에서 알림이 발생(firing)했지만, Slack/이메일로 알림이 오지 않음

- **원인**: Alertmanager 설정이 잘못되었거나, Prometheus가 Alertmanager를 찾지 못하거나, 네트워크 문제로 Alertmanager가 외부 서비스(Slack 등)에 접근할 수 없는 경우입니다.
- **해결 방법**:
  1.  **Prometheus 설정**: Prometheus CRD 설정에서 `alerting.alertmanagers` 섹션이 Alertmanager 서비스를 올바르게 가리키고 있는지 확인합니다.
  2.  **Alertmanager UI 확인**: Alertmanager UI에 접속하여 알림이 수신되었는지, 그룹핑/억제(silence) 규칙에 의해 처리되었는지 확인합니다.
  3.  **Alertmanager 설정 확인**: `alertmanager.yaml` 설정에서 라우팅(`route`) 규칙과 수신자(`receiver`) 설정이 올바른지, Slack Webhook URL이나 이메일 서버 정보가 정확한지 확인합니다.
  4.  **Alertmanager 파드 로그**: Alertmanager 파드의 로그를 확인하여 외부로 알림을 발송하는 과정에서 오류가 없는지 확인합니다.

---

## 6. 통합 문제

### 문제 1: Argo CD에서 모니터링 스택 Application이 `Degraded` 또는 `Missing` 상태임

- **원인**: Helm 차트나 Kustomize 설정에 오류가 있거나, CRD가 클러스터에 먼저 적용되지 않았거나, 리소스 충돌이 발생하는 경우입니다.
- **해결 방법**:
  1.  **Argo CD UI 확인**: Argo CD UI에서 동기화 실패 메시지나 `Degraded` 상태의 리소스를 클릭하여 상세한 오류 원인을 확인합니다.
  2.  **CRD 우선 적용**: Prometheus Operator나 다른 Operator를 설치하는 경우, CRD를 먼저 클러스터에 적용해야 합니다. Argo CD의 Sync Waves나 별도의 Application으로 CRD를 관리하는 것을 고려합니다.
  3.  **Helm/Kustomize 렌더링 테스트**: 로컬에서 `helm template ...` 또는 `kustomize build ...` 명령어를 실행하여 최종적으로 생성되는 매니페스트가 유효한지 확인합니다.

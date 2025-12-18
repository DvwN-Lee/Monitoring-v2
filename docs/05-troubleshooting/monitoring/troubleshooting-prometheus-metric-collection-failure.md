---
version: 1.0
last_updated: 2025-11-15
author: Dongju Lee
---

# [Troubleshooting] Prometheus 애플리케이션 메트릭 수집 실패 문제 해결

## 문제 상황
Prometheus가 배포된 애플리케이션의 메트릭을 수집하지 못하는 문제

## 증상
- Prometheus UI의 Targets 페이지에 애플리케이션이 나타나지 않거나 `DOWN` 상태로 표시됩니다.
- Grafana 대시보드에서 해당 애플리케이션의 메트릭이 보이지 않습니다.

## 원인 분석
Prometheus가 애플리케이션 메트릭을 수집하지 못하는 주요 원인은 다음과 같습니다.

1.  **ServiceMonitor 리소스 누락 또는 잘못된 레이블**: Prometheus Operator는 `ServiceMonitor` 리소스를 통해 어떤 서비스에서 메트릭을 수집할지 파악합니다. 이 리소스가 없거나, Prometheus가 찾을 수 없는 잘못된 레이블을 가지고 있을 수 있습니다.
2.  **ServiceMonitor의 `selector`가 Service와 불일치**: `ServiceMonitor`의 `selector` 필드가 메트릭을 노출하는 `Service`의 레이블과 정확히 일치하지 않으면 Prometheus는 해당 서비스를 찾을 수 없습니다.
3.  **Namespace `selector` 오류**: `ServiceMonitor`가 특정 Namespace의 서비스를 감시하도록 설정되어 있는데, 실제 서비스가 다른 Namespace에 있거나, `ServiceMonitor`의 Namespace `selector` 설정이 잘못되었을 수 있습니다.
4.  **애플리케이션의 `/metrics` 엔드포인트 미구현 또는 오류**: 애플리케이션 자체가 `/metrics` 엔드포인트를 통해 메트릭을 노출하지 않거나, 엔드포인트에 접근 시 오류가 발생할 수 있습니다.
5.  **Prometheus Operator의 `serviceMonitorSelector` 설정 문제**: Prometheus 인스턴스를 배포하는 `Prometheus` 커스텀 리소스(CR)의 `serviceMonitorSelector`가 `ServiceMonitor` 리소스를 제대로 선택하지 못할 수 있습니다. Solid Cloud Cluster 환경에서는 이 부분이 이미 잘 설정되어 있을 가능성이 높지만, 확인이 필요할 수 있습니다.

## 해결 방법 (Solid Cloud Cluster 환경 기반)

### 1단계: Prometheus UI Targets 페이지에서 상태 확인
- Prometheus UI (`http://<prometheus-ip>:9090/targets`)에 접속하여 문제가 되는 애플리케이션의 상태를 확인합니다.
- `DOWN` 상태이거나 아예 목록에 없다면 다음 단계로 진행합니다.

### 2단계: ServiceMonitor 리소스 확인
- 문제가 되는 애플리케이션에 대한 `ServiceMonitor` 리소스가 존재하는지 확인합니다.
  ```bash
  kubectl get servicemonitor -n <애플리케이션_Namespace>
  ```
- 만약 `ServiceMonitor`가 없다면, 해당 애플리케이션에 맞는 `ServiceMonitor`를 생성해야 합니다. (예: `k8s-manifests/monitoring/servicemonitor-api-gateway.yaml` 파일 참조)

### 3단계: Service와 ServiceMonitor의 레이블 일치 여부 확인
- `ServiceMonitor`의 `selector`가 메트릭을 노출하는 `Service`의 레이블과 정확히 일치하는지 확인합니다.

  **ServiceMonitor 확인:**
  ```bash
  kubectl get servicemonitor <servicemonitor_이름> -n <애플리케이션_Namespace> -o yaml
  ```
  `spec.selector.matchLabels` 필드를 확인합니다.

  **Service 확인:**
  ```bash
  kubectl get service <service_이름> -n <애플리케이션_Namespace> -o yaml
  ```
  `metadata.labels` 필드를 확인합니다.

- `ServiceMonitor`의 `selector`와 `Service`의 `labels`가 일치하지 않으면, 둘 중 하나를 수정하여 일치시켜야 합니다. 일반적으로 `ServiceMonitor`의 `selector`를 `Service`의 `labels`에 맞게 수정합니다.

### 4단계: 애플리케이션 `/metrics` 엔드포인트 테스트
- 애플리케이션이 실제로 `/metrics` 엔드포인트를 통해 메트릭을 노출하고 있는지 확인합니다.
- `kubectl port-forward`를 사용하여 애플리케이션 파드에 로컬에서 접근한 후 `curl` 등으로 테스트할 수 있습니다.
  ```bash
  # 애플리케이션 파드 이름 확인
  kubectl get pods -n <애플리케이션_Namespace>

  # 포트 포워딩 (예: 8080 포트)
  kubectl port-forward <애플리케이션_파드_이름> 8080:8080 -n <애플리케이션_Namespace> &

  # 로컬에서 /metrics 엔드포인트 접속 테스트
  curl http://localhost:8080/metrics
  ```
- 메트릭이 제대로 출력되지 않거나 오류가 발생한다면, 애플리케이션 코드 또는 설정(`config.py` 등)을 확인하여 메트릭 노출을 활성화해야 합니다.

### 5단계: ServiceMonitor 생성 또는 수정
- 위 단계에서 문제가 발견되었다면, `ServiceMonitor` 리소스를 생성하거나 수정합니다.
- `k8s-manifests/monitoring/` 디렉토리 내의 기존 `servicemonitor-*.yaml` 파일들을 참고하여 새로운 `ServiceMonitor` 파일을 작성하거나 기존 파일을 수정합니다.
- 수정 후에는 `kubectl apply -f <servicemonitor_파일.yaml>` 명령으로 적용합니다.

## 검증
- **Prometheus Targets 페이지에서 UP 상태 확인**: Prometheus UI (`http://<prometheus-ip>:9090/targets`)에 접속하여 해당 애플리케이션이 `UP` 상태로 변경되었는지 확인합니다.
- **메트릭 쿼리 테스트**: Prometheus UI의 Graph 탭에서 해당 애플리케이션의 메트릭을 쿼리하여 데이터가 정상적으로 수집되는지 확인합니다. (예: `go_gc_duration_seconds_count` 등)
- **Grafana 대시보드 확인**: Grafana 대시보드에서 해당 애플리케이션의 메트릭이 정상적으로 표시되는지 확인합니다.

## 교훈
- **ServiceMonitor 레이블 관리**: `ServiceMonitor`의 `selector`와 `Service`의 `labels`는 항상 일관성 있게 관리해야 합니다.
- **Namespace `selector` 설정**: `ServiceMonitor`의 `namespaceSelector` 설정을 주의 깊게 확인하여 올바른 Namespace의 서비스를 감시하도록 합니다.
- **`/metrics` 엔드포인트 사전 테스트**: 애플리케이션 배포 전 또는 문제 발생 시 `/metrics` 엔드포인트가 정상적으로 동작하는지 미리 테스트하는 습관을 들입니다.
- **Prometheus Operator 설정 이해**: Solid Cloud 환경에서는 Prometheus Operator가 `ServiceMonitor`를 관리하므로, `Prometheus` CR의 `serviceMonitorSelector` 설정이 어떻게 동작하는지 이해하는 것이 중요합니다.

## 관련 문서

- [시스템 아키텍처 - 모니터링 및 로깅](../../02-architecture/architecture.md#5-모니터링-및-로깅)
- [운영 가이드 - 모니터링](../../04-operations/guides/operations-guide.md)

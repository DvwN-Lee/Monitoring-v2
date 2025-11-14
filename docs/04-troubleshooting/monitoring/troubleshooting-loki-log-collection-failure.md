# [Troubleshooting] Loki 로그 수집 실패 문제 해결

## 1. 문제 상황

Solid Cloud 클러스터 환경의 Grafana Explore에서 Loki 데이터소스를 통해 애플리케이션 로그를 조회하려고 시도했으나, 로그가 정상적으로 나타나지 않는 문제가 발생했습니다. 이로 인해 실시간 로그 모니터링 및 디버깅에 어려움을 겪었습니다.

## 2. 증상

- Grafana의 **Explore** 탭에서 Loki 데이터소스를 선택하고 LogQL 쿼리(`{job="<service-name>"}`)를 실행했을 때, "No logs found" 메시지가 표시됩니다.
- 로그 스트림이 전혀 나타나지 않거나, 특정 시간 이후의 로그가 누락됩니다.
- `Log labels` 드롭다운 메뉴에서 예상되는 레이블(예: `pod`, `namespace`)이 보이지 않습니다.

## 3. 원인 분석

문제의 원인을 파악하기 위해 다음 다섯 가지 가능성을 중심으로 조사를 진행했습니다.

1.  **Promtail Pod의 로그 수집 실패**: Promtail Pod가 Kubernetes 노드의 로그 파일에 접근할 권한이 없거나, 설정 오류로 인해 로그 파일을 찾지 못하는 경우입니다.
2.  **Promtail의 Loki 전송 실패**: Promtail이 수집한 로그를 Loki 서버로 전송하는 과정에서 네트워크 문제(방화벽, DNS)나 Loki 서비스 자체의 오류로 인해 실패하는 경우입니다.
3.  **Grafana 데이터소스 설정 오류**: Grafana에 등록된 Loki 데이터소스의 URL이 잘못되었거나, 인증 정보가 올바르지 않아 Grafana가 Loki API에 접근하지 못하는 경우입니다.
4.  **Promtail 파이프라인 설정 오류**: Promtail의 `pipeline_stages` 설정에서 로그를 파싱(예: JSON)하는 과정에 오류가 있어 로그가 올바르게 처리되지 못하고 드롭되는 경우입니다.
5.  **로그 경로 또는 레이블 Selector 오류**: Promtail의 `scrape_configs` 설정에서 지정한 로그 파일 경로(`__path__`)나 Kubernetes Pod를 타겟팅하는 레이블 Selector(`kubernetes_sd_configs`)가 잘못된 경우입니다.

## 4. 해결 방법

아래 5단계 절차에 따라 문제를 해결했습니다.

### 1단계: Promtail Pod 로그 확인

가장 먼저 로그 수집 에이전트인 Promtail의 상태를 확인했습니다.

```bash
kubectl logs -n monitoring -l app.kubernetes.io/name=promtail
```

로그 확인 결과, "permission denied" 오류가 다수 발견되었습니다. 이는 Promtail Pod가 호스트(노드)의 로그 파일 디렉토리(`/var/log/pods`)에 접근할 권한이 부족했기 때문입니다.

### 2단계: Loki 데이터소스 연결 테스트

Grafana 대시보드에서 `Configuration > Data Sources > Loki`로 이동한 후, **"Save & Test"** 버튼을 클릭하여 Loki 서버와의 연결 상태를 확인했습니다. "Data source is working" 메시지가 나타나며 연결에는 문제가 없음을 확인했습니다. 만약 여기서 오류가 발생한다면 Loki 서비스의 URL(`http://loki-stack.monitoring.svc.cluster.local:3100`)이 올바른지 확인해야 합니다.

### 3단계: Promtail 설정 검증 (`scrape_configs`)

Promtail의 `ConfigMap` 또는 `values.yaml` 파일에서 `scrape_configs` 섹션을 검증했습니다. 특히 컨테이너 로그를 수집하는 `job`의 `kubernetes_sd_configs` 설정이 올바르게 구성되어 있는지 확인했습니다.

```yaml
# promtail-config.yaml 예시
...
scrape_configs:
- job_name: kubernetes-pods
  kubernetes_sd_configs:
  - role: pod
  relabel_configs:
  - source_labels:
    - __meta_kubernetes_pod_node_name
    target_label: __host__
  - action: replace
    source_labels:
    - __meta_kubernetes_pod_name
    target_label: pod
...
```

초기 설정에서 `relabel_configs`의 일부 규칙이 누락되어 레이블이 정상적으로 추가되지 않고 있었습니다. 이를 표준 설정에 맞게 수정했습니다.

### 4단계: LogQL 쿼리 테스트

Grafana Explore에서 가장 기본적인 LogQL 쿼리인 `{job="monitoring/promtail"}`을 실행하여 Promtail 자체의 로그가 수집되고 있는지 확인했습니다. 이 쿼리를 통해 최소한의 로그라도 수집되는지 점검하며, 쿼리 문법의 오류가 아님을 확인했습니다.

### 5단계: Promtail DaemonSet 재배포

권한 문제를 해결하기 위해 Promtail의 `DaemonSet`에 `securityContext`를 추가하여 권한을 명시적으로 부여하고, 수정된 설정을 적용하여 재배포했습니다.

```bash
# Helm을 사용하는 경우 values.yaml 수정 후 업그레이드
helm upgrade loki-stack grafana/loki-stack -f loki-stack-values.yaml -n monitoring

# 또는 DaemonSet 직접 수정 후 재배포
kubectl rollout restart daemonset/loki-stack-promtail -n monitoring
```

재배포 후 Promtail Pod가 정상적으로 실행되고 로그에 더 이상 "permission denied" 오류가 없는지 다시 확인했습니다.

## 5. 검증

모든 조치 완료 후, Grafana Explore에서 다시 로그 조회를 시도했습니다.

1.  **로그 스트림 확인**: `{app="user-service"}`와 같은 쿼리를 실행했을 때, 해당 서비스의 로그가 실시간으로 스트리밍되는 것을 확인했습니다.
2.  **기본 LogQL 쿼리 테스트**: `Log labels` 드롭다운에서 `namespace`, `pod`, `container` 등의 레이블이 정상적으로 표시되는 것을 확인하고, 이를 기반으로 한 필터링이 잘 동작하는지 검증했습니다.

## 6. 교훈

이번 문제 해결을 통해 다음과 같은 교훈을 얻었습니다.

-   **Promtail 로그의 중요성**: 로그 수집 문제 발생 시 가장 먼저 확인해야 할 것은 Promtail 자체의 로그입니다. 대부분의 설정 오류나 권한 문제는 이곳에서 단서를 찾을 수 있습니다.
-   **데이터소스 연결 사전 검증**: Grafana에서 데이터소스를 추가할 때는 반드시 "Save & Test" 기능을 통해 연결성을 사전에 검증하는 습관이 중요합니다.
-   **JSON 파싱 파이프라인 주의**: 애플리케이션이 JSON 형식으로 로그를 출력하는 경우, Promtail의 `pipeline_stages`에서 `json` 파서 설정을 정확하게 구성해야 합니다. 파싱 실패 시 로그가 드롭될 수 있습니다.
-   **권한 문제 인지**: 컨테이너화된 환경에서 로그 에이전트는 호스트 시스템의 파일에 접근해야 하므로, `SecurityContext`나 `RBAC` 등 Kubernetes의 권한 설정을 항상 염두에 두어야 합니다.

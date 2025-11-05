# Week 3 구현 가이드: Prometheus, Grafana, Loki 모니터링 스택 구축

## 1. 개요

이 가이드는 쿠버네티스 클러스터에 Prometheus, Grafana, Loki를 사용하여 포괄적인 모니터링 및 로깅 시스템을 구축하는 방법을 설명합니다. 모든 과정은 GitOps 원칙에 따라 Argo CD와 Kustomize를 통해 자동화됩니다.

**아키텍처 다이어그램:**
```
+--------------------------------------------------------------------+
|                           Kubernetes Cluster                       |
|--------------------------------------------------------------------|
| +-------------------------+      +-------------------------------+ |
| | Monitoring Namespace    |      | Application Namespace (default) | |
| |                         |      |                               | |
| |  +-------------------+  |      |  +-------------------------+  | |
| |  | Prometheus Operator|  |      |  |      Application Pod    |  | |
| |  +-------------------+  |      |  |-------------------------|  | |
| |        |                |      |  | - Container             |  | |
| |        v                |      |  | - Metrics Endpoint (/metrics)|  | |
| |  +-------------------+  |      |  +-------------------------+  | |
| |  |   Prometheus      |  |      |        ^           |          | |
| |  | (Metrics DB)      |  |      |        |           |          | |
| |  +-------------------+  |      | (scrape) |           v          | |
| |        ^                |      |  +-------------------------+  | |
| |        |                |      |  |      Promtail Agent     |  | |
| |  +-------------------+  |      |  | (Log Collector)         |  | |
| |  |     Grafana       |  |      |  +-------------------------+  | |
| |  | (Visualization)   |  |      |              |              | |
| |  +-------------------+  |      |              | (send logs)  | |
| |        ^                |      |              v              | |
| |        |                |      +-------------------------------+ |
| |  +-------------------+  |                                        |
| |  |      Loki         |  |                                        |
| |  | (Logging DB)      |  |                                        |
| |  +-------------------+  |                                        |
| |                         |                                        |
| +-------------------------+                                        |
+--------------------------------------------------------------------+
```

---

## 2. Prometheus Operator 설치 및 구성

Prometheus Operator는 Prometheus 관련 리소스(Prometheus, ServiceMonitor, Alertmanager 등)를 쿠버네티스 네이티브 방식으로 관리해줍니다.

### 단계 1: `monitoring` 네임스페이스 생성

모든 모니터링 관련 리소스를 격리하기 위해 `monitoring` 네임스페이스를 생성합니다.

**`k8s-manifests/monitoring/namespace.yaml`**
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: monitoring
```

### 단계 2: Prometheus Operator 설치

Helm 차트를 사용하여 Prometheus Community의 `kube-prometheus-stack`을 설치합니다. Argo CD Application으로 관리하는 것이 좋습니다.

**`argocd/applications/prometheus-stack.yaml` (예시)**
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: prometheus-stack
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://prometheus-community.github.io/helm-charts
    chart: kube-prometheus-stack
    targetRevision: 45.2.1 # 특정 버전 명시
    helm:
      values: | # (A)
        # 여기에 아래의 values.yaml 내용 추가
  destination:
    server: https://kubernetes.default.svc
    namespace: monitoring
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

### 단계 3: Prometheus 설정 (`values.yaml`)

`kube-prometheus-stack` 차트의 핵심 설정을 `values.yaml` 파일로 관리합니다.

**`k8s-manifests/monitoring/prometheus-values.yaml`**
```yaml
prometheus:
  prometheusSpec:
    # 서비스 모니터를 모든 네임스페이스에서 찾도록 설정
    serviceMonitorSelectorNilUsesHelmValues: false
    # Pod 모니터를 모든 네임스페이스에서 찾도록 설정
    podMonitorSelectorNilUsesHelmValues: false
    # 룰을 모든 네임스페이스에서 찾도록 설정
    ruleSelectorNilUsesHelmValues: false

grafana:
  # Grafana 활성화
  enabled: true
  # 아래 Grafana 설정에서 설명

# Alertmanager, Exporters 등 기타 설정...
```

### 단계 4: ServiceMonitor 생성

애플리케이션의 메트릭을 수집하기 위해 ServiceMonitor 리소스를 생성합니다. 이 리소스는 `app: <app-name>` 레이블을 가진 서비스를 찾아 `/metrics` 엔드포인트를 스크랩합니다.

**`k8s-manifests/monitoring/servicemonitor-user-service.yaml`**
```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: user-service-monitor
  namespace: monitoring # Prometheus가 설치된 네임스페이스
  labels:
    release: prometheus # Prometheus Operator가 인지하도록 레이블 추가
    app: user-service
spec:
  selector:
    matchLabels:
      app: user-service
  namespaceSelector:
    matchNames:
      - default # 애플리케이션이 배포된 네임스페이스
  endpoints:
  - port: http
    interval: 15s
    path: /metrics
```

---

## 3. Grafana 및 Golden Signals 대시보드

Grafana를 설치하고, 4대 핵심 지표(Golden Signals) 대시보드를 자동으로 프로비저닝합니다.

### 단계 1: Grafana 설정 (`prometheus-values.yaml`에 추가)

```yaml
grafana:
  enabled: true
  # 기본 admin 비밀번호 설정 (Secret으로 관리 권장)
  adminPassword: "admin"

  # 데이터소스 자동 프로비저닝
  additionalDataSources:
    - name: Prometheus
      type: prometheus
      url: http://prometheus-kube-prometheus-prometheus.monitoring.svc:9090
      access: proxy
      isDefault: true
    - name: Loki
      type: loki
      url: http://loki-stack.monitoring.svc:3100
      access: proxy

  # 대시보드 자동 프로비저닝
  dashboardProviders:
    dashboardproviders.yaml:
      apiVersion: 1
      providers:
      - name: 'default'
        orgId: 1
        folder: ''
        type: file
        disableDeletion: false
        editable: true
        options:
          path: /var/lib/grafana/dashboards/default

  dashboards:
    default:
      # ConfigMap으로 생성될 대시보드 정의
      golden-signals:
        file: dashboards/golden-signals-dashboard.json # (B)
```

### 단계 2: Golden Signals 대시보드 JSON 생성

대시보드 정의를 JSON 파일로 생성합니다. 이 파일은 ConfigMap으로 변환되어 Grafana에 마운트됩니다.

**`k8s-manifests/monitoring/dashboards/golden-signals-dashboard.json`**
- 이 파일은 Latency, Traffic, Errors, Saturation 패널을 포함하는 복잡한 JSON 구조입니다.
- 각 패널은 PromQL 쿼리를 사용하여 Prometheus 데이터를 시각화합니다.
  - **Latency (P95)**: `histogram_quantile(0.95, sum(rate(http_requests_latency_seconds_bucket[5m])) by (le, service))`
  - **Traffic**: `sum(rate(http_requests_total[5m])) by (service)`
  - **Errors**: `sum(rate(http_requests_total{code=~"5.."}[5m])) by (service) / sum(rate(http_requests_total[5m])) by (service)`

### 단계 3: Kustomize 설정

Kustomize를 사용하여 대시보드 ConfigMap을 생성합니다.

**`k8s-manifests/monitoring/kustomization.yaml`**
```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - namespace.yaml
  # ... 다른 리소스 ...

configMapGenerator:
- name: grafana-dashboards
  files:
    - dashboards/golden-signals-dashboard.json
  options:
    labels:
      grafana_dashboard: "1"
```

---

## 4. Loki 및 Promtail 로깅 시스템

Loki는 로그를 저장하고, Promtail은 로그를 수집하여 Loki로 전송합니다.

### 단계 1: Loki 및 Promtail 설치

Grafana Labs의 `loki-stack` Helm 차트를 사용합니다.

**`argocd/applications/loki-stack.yaml` (예시)**
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: loki-stack
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://grafana.github.io/helm-charts
    chart: loki-stack
    targetRevision: 2.9.10
    helm:
      values: | # (C)
        # 여기에 아래의 values.yaml 내용 추가
  destination:
    server: https://kubernetes.default.svc
    namespace: monitoring
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

### 단계 2: Loki 및 Promtail 설정 (`values.yaml`)

**`k8s-manifests/monitoring/loki-stack-values.yaml`**
```yaml
loki:
  # Loki 설정 (예: 스토리지, 보존 기간)
  persistence:
    enabled: true
    size: 10Gi
  config:
    table_manager:
      retention_deletes_enabled: true
      retention_period: 168h # 7일

promtail:
  # Promtail 활성화
  enabled: true
  # 모든 노드에 DaemonSet으로 배포
  config:
    snippets:
      # 특정 네임스페이스의 로그만 수집
      scrapeConfigs: |
        - job_name: kubernetes-pods
          kubernetes_sd_configs:
            - role: pod
          relabel_configs:
            - source_labels:
                - __meta_kubernetes_pod_node_name
              target_label: __host__
            # ...
            - source_labels: [__meta_kubernetes_namespace]
              action: keep
              regex: '(default|monitoring)' # 수집할 네임스페이스 지정
```

### 단계 3: Grafana Loki 데이터소스 확인

위의 Grafana 설정에서 `additionalDataSources`에 Loki가 이미 추가되었습니다. Grafana UI에서 `Explore` 탭으로 이동하여 Loki 데이터소스를 선택하고, LogQL 쿼리(`{app="user-service"}`)를 실행하여 로그가 정상적으로 수집되는지 확인합니다.

---

## 5. Argo CD와 GitOps 통합

모든 모니터링 스택 구성 요소를 Argo CD Application으로 등록하여 GitOps 워크플로우를 완성합니다.

1.  **Application 등록**: 위에서 설명한 `prometheus-stack.yaml`과 `loki-stack.yaml`을 Argo CD가 관리하는 경로에 추가합니다.
2.  **Kustomize 설정**: `k8s-manifests/monitoring/kustomization.yaml`에 ServiceMonitor, PrometheusRule 등 모든 커스텀 리소스를 포함시킵니다.
3.  **App of Apps 패턴 (권장)**: 모든 모니터링 관련 Argo CD Application들을 관리하는 최상위 Application을 만들어 관리를 중앙화합니다.

이제 Git 리포지토리의 모니터링 관련 매니페스트를 수정하고 push하면, Argo CD가 변경 사항을 감지하여 클러스터의 모니터링 시스템을 자동으로 업데이트합니다.

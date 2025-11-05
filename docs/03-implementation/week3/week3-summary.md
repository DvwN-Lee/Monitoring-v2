# Week 3 요약: 쿠버네티스 모니터링 시스템 구축

작성: 이동주
작성일: 2025-10-31

## 개요

Week 3에서는 Prometheus, Grafana, Loki를 중심으로 쿠버네티스 클러스터의 포괄적인 모니터링 및 로깅 시스템을 구축했습니다. 모든 설정은 GitOps 원칙에 따라 Argo CD를 통해 관리되어 선언적 구성과 자동화를 달성했습니다.

---

## 주요 성과

### 1. Prometheus 기반 메트릭 수집
- **Prometheus Operator**: 설치 및 구성을 통해 Prometheus 인스턴스와 관련 리소스(ServiceMonitor, PrometheusRules)를 효율적으로 관리합니다.
- **ServiceMonitor**: 각 마이크로서비스(api-gateway, auth-service, user-service 등)에 대한 ServiceMonitor를 생성하여 자동으로 메트릭을 수집합니다.
- **Custom Rules**: CPU 및 메모리 사용량에 대한 사용자 정의 알림 규칙을 추가하여 잠재적인 문제를 사전에 감지합니다.

### 2. Grafana를 이용한 시각화
- **Golden Signals Dashboard**: Latency, Traffic, Errors, Saturation (UTES)의 4가지 핵심 지표를 시각화하는 대시보드를 구축했습니다.
    - **Latency**: P95, P99 응답 시간 추적
    - **Traffic**: 서비스별 초당 요청(RPS)
    - **Errors**: 4xx, 5xx 에러 비율
    - **Saturation**: CPU 및 메모리 사용률
- **자동 프로비저닝**: Grafana 대시보드와 데이터소스(Prometheus, Loki)를 ConfigMap과 sidecar를 통해 자동으로 프로비저닝하여 GitOps 워크플로우에 통합했습니다.

### 3. Loki 중앙 로깅 시스템
- **Loki 및 Promtail**: Loki는 로그 저장을, Promtail은 클러스터의 모든 노드에서 로그를 수집하는 역할을 합니다.
- **중앙화된 로그 관리**: 모든 파드(Pod)의 stdout/stderr 로그를 수집하여 Grafana에서 LogQL을 통해 조회하고 분석할 수 있습니다.
- **JSON 파싱**: 애플리케이션의 JSON 형식 로그를 자동으로 파싱하여 'level', 'msg'와 같은 키를 기반으로 효율적인 검색 및 필터링이 가능합니다.

### 4. GitOps 통합
- **Argo CD**: Prometheus, Grafana, Loki 등 모든 모니터링 구성 요소를 Argo CD 애플리케이션으로 관리합니다.
- **Kustomize**: 기본(base) 매니페스트와 환경별(overlays) 설정을 분리하여 구성의 재사용성과 확장성을 높였습니다.
- **자동 동기화**: Git 리포지토리의 변경 사항이 클러스터에 자동으로 동기화되어, 모니터링 인프라를 코드로 관리(IaC)합니다.

---

## 아키텍처 변화

### Before (Week 2)
- CI/CD 파이프라인 구축 완료
- Argo CD를 통한 기본적인 애플리케이션 배포

### After (Week 3)
```
[Kubernetes Cluster]
├───[Monitoring Namespace]
│   ├─── Prometheus Operator
│   │    └── Prometheus (Metrics Data)
│   ├─── Grafana (Visualization)
│   └─── Loki (Log Data)
│
└───[Application Namespaces]
    ├─── Pods
    │    └── Metrics Endpoint
    └─── Promtail (Log Collector)
```
- **주요 변경점**:
  - 모니터링 전용 네임스페이스(`monitoring`) 신설
  - Prometheus가 ServiceMonitor를 통해 애플리케이션 메트릭 수집
  - Promtail이 각 노드의 컨테이너 로그를 수집하여 Loki로 전송
  - Grafana가 Prometheus 메트릭과 Loki 로그를 시각화

---

## 기술적 성과

- **통합된 관찰성(Observability)**: 메트릭, 로그, 트레이스(향후 확장 기반)를 Grafana라는 단일 인터페이스에서 확인할 수 있는 기반을 마련했습니다.
- **선언적 구성**: 모든 모니터링 리소스가 YAML 매니페스트로 정의되고 Git에서 버전 관리되어, 변경 추적 및 롤백이 용이해졌습니다.
- **자동화된 배포**: Argo CD를 통해 모니터링 스택의 설치, 업그레이드, 구성 변경이 자동으로 이루어져 운영 부담이 감소했습니다.

---

## 다음 단계

- **Alertmanager 연동**: Prometheus 알림 규칙과 Alertmanager를 연동하여 Slack, 이메일 등 외부 채널로 알림을 발송하는 시스템을 구축합니다.
- **고급 대시보드**: 서비스별 상세 대시보드, 리소스 사용량 예측 등 더 심층적인 분석을 위한 대시보드를 추가합니다.

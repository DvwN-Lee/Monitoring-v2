# ADR-007: Monitoring Stack으로 Prometheus + Grafana 채택

**날짜**: 2025-10-01

---

## 상황 (Context)

마이크로서비스 환경에서 시스템의 건강 상태를 지속적으로 모니터링하고, Golden Signals(Latency, Traffic, Errors, Saturation)를 추적하기 위한 메트릭 수집 및 시각화 솔루션이 필요했습니다. Kubernetes 네이티브 환경에 최적화되고, Istio Service Mesh와 원활하게 통합될 수 있는 도구를 찾고 있었습니다.

## 결정 (Decision)

- 메트릭 수집: **Prometheus**
- 메트릭 시각화: **Grafana**
- 배포 방식: **kube-prometheus-stack** Helm 차트 사용

## 이유 (Rationale)

CNCF Graduated 프로젝트인 Prometheus와 오픈소스 시각화 도구 Grafana를 중심으로 한 스택을 다른 대안들과 비교했습니다.

### 비교 분석

| 기준 | Prometheus + Grafana | Datadog | New Relic | 선택 이유 |
|:---|:---|:---|:---|:---|
| **비용** | **무료 (오픈소스)** | 유료 (호스트당 과금) | 유료 (사용량 기반) | 학습 목적 프로젝트이므로 비용 부담 없음. |
| **Kubernetes 통합** | **네이티브 지원** (ServiceMonitor CRD) | Kubernetes 지원 | Kubernetes 지원 | Prometheus Operator를 통한 선언적 모니터링 설정. |
| **Istio 통합** | **완벽한 통합** (Istio 메트릭 자동 수집) | 수동 설정 필요 | 수동 설정 필요 | Istio가 Prometheus 형식으로 메트릭을 기본 제공함. |
| **커뮤니티** | **매우 활발함** (CNCF Graduated) | 상용 지원 | 상용 지원 | 방대한 문서와 커뮤니티 생태계. |
| **커스터마이징** | **높음** (PromQL, Grafana 대시보드) | 제한적 | 제한적 | 모든 대시보드와 쿼리를 완전히 제어 가능. |
| **데이터 보관** | **로컬 스토리지** (완전한 제어) | 클라우드 | 클라우드 | 데이터 주권과 보안 요구사항 충족. |
| **Alert Manager** | **내장됨** | 내장됨 | 내장됨 | Kubernetes 네이티브 AlertManager CRD 지원. |

### Prometheus 선택 이유

1. **Pull 기반 메트릭 수집 모델**: Kubernetes의 Service Discovery와 완벽하게 통합되어 동적으로 타겟을 발견하고 메트릭을 수집합니다.
2. **ServiceMonitor CRD**: Prometheus Operator를 통해 모니터링 대상을 선언적으로 정의할 수 있어 GitOps 워크플로우와 일치합니다.
3. **Istio 메트릭 자동 수집**: Istio Proxy(Envoy)가 Prometheus 형식의 메트릭을 `/stats/prometheus` 엔드포인트로 노출하여 별도 설정 없이 수집 가능합니다.
4. **PromQL**: 강력한 쿼리 언어로 복잡한 집계와 계산을 수행할 수 있습니다.

### Grafana 선택 이유

1. **다양한 데이터소스 지원**: Prometheus뿐만 아니라 Loki(로그), Jaeger(트레이싱)를 단일 대시보드에서 통합 조회 가능합니다.
2. **풍부한 대시보드 템플릿**: Istio, Kubernetes, Node Exporter 등 사전 구성된 대시보드를 활용하여 빠르게 시각화를 구축할 수 있습니다.
3. **커스터마이징 자유도**: JSON 기반 대시보드 정의로 완전한 커스터마이징과 버전 관리가 가능합니다.
4. **알림 통합**: Slack, Email 등 다양한 알림 채널을 지원합니다.

### kube-prometheus-stack 선택 이유

단순히 Prometheus와 Grafana를 설치하는 대신 **kube-prometheus-stack** Helm 차트를 선택했습니다:
- Prometheus Operator, Grafana, AlertManager를 한 번에 배포
- Node Exporter, Kube State Metrics 등 필수 exporter 자동 포함
- Kubernetes 클러스터 모니터링을 위한 기본 대시보드와 알림 규칙 제공
- CRD 기반 설정으로 선언적 관리 가능

## 결과 (Consequences)

### 긍정적 측면
- Kubernetes와 Istio의 모든 메트릭을 자동으로 수집하고 시각화
- Golden Signals(Latency, Traffic, Errors, Saturation) 대시보드 구축으로 시스템 건강도 실시간 추적
- PromQL을 통한 세밀한 메트릭 분석 및 알림 규칙 정의
- Grafana를 통해 Prometheus(메트릭), Loki(로그)를 단일 인터페이스에서 통합 조회
- 완전한 오픈소스로 비용 부담 없음
- ServiceMonitor CRD를 통한 선언적 모니터링 설정으로 GitOps 워크플로우 통합
- 방대한 커뮤니티 지원과 레퍼런스

### 부정적 측면 (Trade-offs)
- 데이터 보관 기간이 길어질수록 스토리지 사용량 증가 (Persistent Volume 필요)
- Prometheus는 장기 데이터 보관에 최적화되지 않음 (Thanos, Cortex 등 추가 솔루션 필요)
- 초기 대시보드 구성 및 PromQL 학습 곡선
- AlertManager 알림 규칙 설정 복잡도
- Self-hosted이므로 운영 부담 존재 (상용 SaaS 대비)

# ADR-006: Service Mesh로 Istio 채택

**날짜**: 2025-10-01
**상태**: 승인됨

---

## 상황 (Context)

마이크로서비스 아키텍처에서 서비스 간 통신을 안전하고 효율적으로 관리하기 위해 Service Mesh 도입이 필요했습니다. 트래픽 관리, 보안(mTLS), 관측성(Observability), 그리고 장애 복구 기능을 통합적으로 제공하는 솔루션을 찾고 있었습니다.

## 결정 (Decision)

- Service Mesh 솔루션으로 **Istio**를 채택

## 이유 (Rationale)

CNCF 생태계의 두 주요 Service Mesh인 Istio와 Linkerd를 비교 분석했습니다.

### 비교 분석

| 기준 | Istio | Linkerd | 선택 이유 |
|:---|:---|:---|:---|
| **기능 범위** | **포괄적** (트래픽 관리, 보안, 관측성, 정책) | 경량화된 핵심 기능 중심 | Ingress Gateway, VirtualService, DestinationRule 등 세밀한 트래픽 제어 기능이 필요함. |
| **관측성** | **Kiali, Jaeger, Grafana 통합** | Linkerd Dashboard 제공 | Kiali를 통한 서비스 메시 시각화가 데모와 운영에 효과적임. |
| **보안** | **mTLS STRICT 모드 지원** | mTLS 자동 적용 | 네임스페이스 단위로 mTLS 정책을 세밀하게 제어 가능함. |
| **트래픽 관리** | **강력함** (카나리, A/B 테스트, 미러링) | 기본적인 로드밸런싱 | VirtualService를 통한 정교한 라우팅 규칙 설정 가능. |
| **커뮤니티** | **매우 활발함** (Google, IBM 지원) | 활발함 | 더 많은 레퍼런스와 엔터프라이즈 지원 사례가 있음. |
| **리소스 사용량** | 상대적으로 높음 | **경량** (Rust 기반) | 학습 목적 프로젝트이므로 리소스보다 기능성을 우선시함. |
| **학습 곡선** | 가파름 | **완만함** | 복잡하지만 실무에서 더 많이 사용되는 기술을 학습하는 것이 유리함. |

### 최종 선택 이유

**Kiali를 통한 서비스 메시 시각화**와 **세밀한 트래픽 제어 기능**이 결정적이었습니다. Kiali 대시보드를 통해 서비스 간 트래픽 흐름, mTLS 상태, 에러율을 실시간으로 시각화할 수 있어 운영과 디버깅에 매우 유용합니다. 또한 VirtualService와 DestinationRule을 활용한 카나리 배포, A/B 테스트 등 고급 트래픽 관리 기능을 실습할 수 있다는 점도 학습 목적에 부합했습니다.

리소스 사용량이 높다는 단점이 있지만, 실제 프로덕션 환경에서 가장 널리 사용되는 Service Mesh를 경험하는 것이 장기적으로 더 가치 있다고 판단했습니다.

## 결과 (Consequences)

### 긍정적 측면
- Kiali를 통해 서비스 메시의 트래픽 패턴과 mTLS 상태를 시각적으로 모니터링 가능
- VirtualService를 통한 정교한 라우팅 규칙 설정 (헤더 기반, 가중치 기반)
- Prometheus와의 완벽한 통합으로 풍부한 메트릭 수집 (요청 수, 지연시간, 에러율)
- 네임스페이스 단위 mTLS STRICT 모드 적용으로 서비스 간 통신 보안 강화
- Istio IngressGateway를 통한 외부 트래픽 통합 관리
- 실무에서 가장 많이 사용되는 Service Mesh 경험 획득

### 부정적 측면 (Trade-offs)
- 높은 리소스 사용량 (Control Plane: istiod, Data Plane: Envoy sidecar)
- 가파른 학습 곡선 (CRD 종류가 많고 설정이 복잡함)
- 초기 설정 및 트러블슈팅에 시간 소요
- Envoy 사이드카 주입으로 인한 Pod 시작 시간 증가

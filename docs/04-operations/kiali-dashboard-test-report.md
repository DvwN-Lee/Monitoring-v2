# Kiali 대시보드 테스트 보고서

## 1. 테스트 개요

### 1.1. 테스트 목적
Istio 서비스 메시 환경에서 Kiali 대시보드가 정상적으로 동작하며, 서비스 토폴로지, 트래픽 흐름, Istio 설정이 올바르게 시각화되는지 검증

### 1.2. 테스트 환경
- **Kubernetes Namespace**: titanium-prod, istio-system
- **Kiali URL**: http://10.0.11.169:30164
- **Kiali Version**: 추정 v1.x
- **테스트 일시**: 2025-11-13
- **테스트 방법**: Chrome DevTools Protocol (CDP) 기반 자동화 테스트
- **인증 방식**: anonymous

### 1.3. 테스트 대상 기능
1. Overview - 네임스페이스 및 애플리케이션 개요
2. Graph View - 서비스 메시 토폴로지 시각화
3. Applications View - 애플리케이션 목록 및 상태
4. Istio Config - Istio 리소스 설정 검증

## 2. 테스트 결과 요약

| 테스트 케이스 | 상태 | 비고 |
|---|---|---|
| TC-01: Overview 페이지 확인 | 성공 | titanium-prod 네임스페이스 7개 애플리케이션 확인 |
| TC-02: Graph View 서비스 토폴로지 | 성공 | 트래픽 흐름 및 메트릭 정상 표시 |
| TC-03: Applications View 탐색 | 성공 | 7개 애플리케이션 및 Istio 설정 확인 |
| TC-04: Istio Config 검증 | 성공 | VirtualService, PeerAuthentication 확인 |

## 3. 상세 테스트 결과

### 3.1. TC-01: Overview 페이지 확인

**테스트 절차**:
1. Kiali URL (http://10.0.11.169:30164) 접속
2. Overview 페이지 로딩 확인
3. titanium-prod 네임스페이스 상태 확인

**결과**: 성공

**관찰 사항**:
- titanium-prod 네임스페이스에 7개 애플리케이션 확인
- mTLS 상태: 전체 활성화 (Full dark icon)
- Inbound traffic 표시 정상
- istio-system 네임스페이스에 6개 컨트롤 플레인 애플리케이션 확인

**확인된 애플리케이션**:
1. api-gateway
2. auth-service
3. blog-service
4. load-generator
5. postgresql
6. redis
7. user-service

### 3.2. TC-02: Graph View 서비스 메시 토폴로지

**테스트 절차**:
1. Graph View로 이동
2. titanium-prod 네임스페이스 선택
3. Display 옵션에서 Response Time(95th Percentile) 활성화
4. Traffic Animation 활성화
5. 서비스 간 트래픽 흐름 확인

**결과**: 성공

**관찰된 토폴로지 메트릭**:
```
Graph Summary:
- Applications: 3 (3 versions)
- Services: 2
- Edges: 4
- HTTP RPS: 3.78-3.87
- Success Rate: 100.00%
- Error Rate: 0.00%
```

**Graph View 주요 기능 확인**:
- 서비스 노드 시각화: 정상
- 트래픽 애니메이션: 정상 작동
- Response Time 표시: P95 메트릭 정상 표시
- 엣지 상태: 모두 녹색 (정상 통신)

**이슈**:
- "Select Namespaces" 버튼 클릭 시 Overview 페이지로 리디렉션됨
- 해결: URL 직접 접근으로 네임스페이스 선택 (`?namespaces=titanium-prod`)

### 3.3. TC-03: Applications View 애플리케이션 목록

**테스트 절차**:
1. Applications View로 이동
2. titanium-prod 네임스페이스의 애플리케이션 목록 확인
3. 각 애플리케이션의 Istio 설정 확인

**결과**: 성공

**확인된 애플리케이션 및 Istio 설정**:

| 애플리케이션 | Istio 설정 | 비고 |
|---|---|---|
| api-gateway | Gateway, PeerAuthentication, VirtualService | 3개 설정 |
| auth-service | Gateway, PeerAuthentication | 2개 설정 |
| blog-service | Gateway, PeerAuthentication, VirtualService | 3개 설정 |
| load-generator | PeerAuthentication | 1개 설정 |
| postgresql | DestinationRule (mTLS disabled), PeerAuthentication | 2개 설정 |
| redis | DestinationRule (mTLS disabled), PeerAuthentication | 2개 설정 |
| user-service | Gateway, PeerAuthentication | 2개 설정 |

**주요 관찰 사항**:
- 모든 애플리케이션에 PeerAuthentication 설정 존재
- postgresql과 redis는 DestinationRule로 mTLS 비활성화 (데이터베이스 특성상 정상)
- API 서비스들(api-gateway, blog-service)은 VirtualService로 라우팅 규칙 정의

### 3.4. TC-04: Istio Config 검증

**테스트 절차**:
1. Istio Config View로 이동
2. titanium-prod 네임스페이스의 Istio 리소스 목록 확인
3. 주요 리소스 상세 확인:
   - VirtualService: prod-titanium-vs
   - PeerAuthentication: prod-default-mtls

**결과**: 성공

**확인된 Istio 리소스**:

#### DestinationRule (3개)
1. **prod-default-mtls**
   - 용도: 기본 mTLS 설정

2. **prod-postgresql-service-disable-mtls**
   - 용도: PostgreSQL 서비스의 mTLS 비활성화

3. **prod-redis-disable-mtls**
   - 용도: Redis 서비스의 mTLS 비활성화

#### PeerAuthentication (3개)
1. **prod-default-mtls**
   - **mTLS Mode: STRICT**
   - 용도: titanium-prod 네임스페이스 전체에 STRICT mTLS 적용
   - Namespace-wide 정책

2. **prod-postgresql-mtls-disable**
   - 용도: PostgreSQL 워크로드의 mTLS 예외 처리

3. **prod-redis-mtls-disable**
   - 용도: Redis 워크로드의 mTLS 예외 처리

#### VirtualService (1개)
**prod-titanium-vs**:
- API Version: networking.istio.io/v1beta1
- Hosts: ['*']
- Gateways: [titanium-gateway]
- References:
  - Service: titanium-prod/prod-blog-service
  - Service: titanium-prod/prod-api-gateway-service
  - Gateway: titanium-prod/titanium-gateway

#### Gateway (1개)
**titanium-gateway**:
- 용도: Ingress 게이트웨이 설정

## 4. mTLS 설정 분석

### 4.1. 전체 mTLS 정책
**PeerAuthentication (prod-default-mtls)**:
```yaml
spec:
  mtls:
    mode: STRICT
```
- titanium-prod 네임스페이스의 모든 워크로드에 STRICT mTLS 적용
- 모든 서비스 간 통신이 상호 TLS 인증 필요
- Overview 페이지에서 전체 mTLS 활성화 아이콘(full dark) 확인

### 4.2. mTLS 예외 처리
**PostgreSQL 및 Redis의 mTLS 비활성화**:
- 이유: 데이터베이스와 캐시 서비스는 일반적으로 자체 인증 메커니즘 사용
- 구현: PeerAuthentication과 DestinationRule 조합으로 특정 워크로드만 mTLS 비활성화
- 보안: 네트워크 정책 및 애플리케이션 레벨 인증으로 보완 필요

## 5. 발견된 이슈 및 해결 방안

### 5.1. 해결된 이슈

| 이슈 | 원인 | 해결 방안 |
|---|---|---|
| Namespace 선택 버튼 미동작 | UI 버그 또는 설정 문제 | URL 파라미터로 직접 네임스페이스 지정 |

### 5.2. 개선 권장 사항

1. **Workloads View 및 Services View 추가 테스트**
   - 현재 테스트에서는 Applications View만 확인
   - Pod 상태 및 서비스 엔드포인트 추가 검증 필요

2. **Health Check 기능 검증**
   - 각 서비스의 Health 상태가 실제 Pod 상태를 정확히 반영하는지 확인
   - 의도적 장애 발생 후 Kiali 대시보드 반응 테스트

3. **Traffic Animation 성능 모니터링**
   - 대규모 트래픽 발생 시 Graph View 렌더링 성능 확인

## 6. 서비스 메시 상태 평가

### 6.1. 강점
- STRICT mTLS 정책으로 높은 보안 수준 유지
- 데이터베이스 워크로드에 대한 합리적인 mTLS 예외 처리
- VirtualService를 통한 명확한 라우팅 규칙 정의
- Istio 설정 간 참조 관계 명확

### 6.2. 현재 상태
- 서비스 간 통신: 정상 (Success Rate 100%)
- mTLS 적용: 정상 (STRICT 모드 활성화)
- 트래픽 흐름: 정상 (HTTP RPS 3.78-3.87)
- Istio 설정 유효성: 정상 (검증 오류 없음)

## 7. 결론

### 7.1. 테스트 종합 평가

Kiali 대시보드는 Istio 서비스 메시의 상태를 효과적으로 시각화하고 있으며, 주요 기능이 모두 정상 작동합니다.

**강점**:
- 서비스 메시 토폴로지 시각화 정상
- 실시간 트래픽 메트릭 수집 및 표시
- Istio 설정 검증 기능 정상
- mTLS 상태 명확히 표시
- STRICT mTLS 정책 정상 적용

**개선 필요 사항**:
- Namespace 선택 UI 개선
- Workloads/Services View 추가 테스트

### 7.2. 다음 단계

1. Workloads View 및 Services View 테스트 수행
2. Health Check 기능 상세 검증
3. 장애 시나리오 테스트 (서비스 다운, mTLS 오류 등)
4. Kiali 알림 및 모니터링 기능 검증

## 8. 첨부 자료

- 테스트 시나리오 문서: (별도 저장 필요)
- Graph View 스크린샷: `/tmp/kiali-graph-titanium-prod.png`
- Graph with Metrics 스크린샷: `/tmp/kiali-graph-with-metrics.png`
- Applications View 스크린샷: `/tmp/kiali-applications-view.png`
- Istio Config 스크린샷: `/tmp/kiali-istio-config-view.png`
- VirtualService 상세 스크린샷: `/tmp/kiali-virtualservice-detail.png`
- PeerAuthentication 상세 스크린샷: `/tmp/kiali-peerauthentication-strict-mtls.png`

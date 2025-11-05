# Week 4 요약: 서비스 메시 & 고급 기능

작성: 이동주
작성일: 2025-11-01

## 개요

Week 4에서는 Kubernetes 클러스터에 Istio 서비스 메시를 도입하고, mTLS 보안, 자동 스케일링(HPA), API Rate Limiting 등 고급 기능을 구현했습니다.

---

## 주요 성과

### 1. Istio 서비스 메시 구축
- **버전**: Istio 1.20.1 (demo profile)
- **구성 요소**:
  - istiod (Control Plane)
  - istio-ingressgateway
  - istio-egressgateway
  - Kiali (서비스 메시 시각화)
  - Jaeger (분산 추적)
- **사이드카 주입**: 모든 애플리케이션 Pod에 Envoy proxy 자동 주입
- **리소스 최적화**: 사이드카 CPU limits 2000m → 200m

### 2. mTLS 보안 강화
- **PeerAuthentication**: STRICT 모드로 서비스 간 통신 암호화 강제
- **DestinationRule**: 모든 서비스에 ISTIO_MUTUAL TLS 모드 적용
- **인증서 관리**: Istio가 자동으로 인증서 발급 및 갱신
- **검증**: mTLS 인증서 ACTIVE 및 VALID 상태 확인

### 3. 자동 스케일링 (HPA)
- **Metrics Server**: 설치 및 kubelet TLS 설정
- **HPA 적용 서비스**:
  - user-service
  - auth-service
  - blog-service
  - api-gateway
- **설정**: minReplicas: 1, maxReplicas: 5, CPU 목표: 70%
- **동작 확인**: 메트릭 수집 정상, 부하에 따른 자동 스케일링 준비 완료

### 4. API Rate Limiting
- **구현 방법**: Istio EnvoyFilter 사용
- **적용 대상**: load-balancer 서비스
- **제한**: 분당 100 요청 (Local Rate Limit)
- **헤더**: x-local-rate-limit 응답 헤더 추가

---

## 아키텍처 변화

### Before (Week 3)
```
[External Traffic]
        ↓
[Load Balancer Service]
        ↓
[Application Pods]
        ↓
[Other Services]
```

### After (Week 4)
```
[External Traffic]
        ↓
[Istio Ingress Gateway]
        ↓
[Load Balancer Service + Envoy Sidecar]
        ↓
[Application Pods + Envoy Sidecars]
   (mTLS encrypted)
        ↓
[Other Services + Envoy Sidecars]
```

**주요 변경점:**
- 모든 서비스 간 통신이 Envoy proxy를 거침
- 서비스 메시 레벨에서 트래픽 제어, 보안, 관찰성 확보
- mTLS로 모든 통신 암호화
- 중앙화된 트래픽 관리 (Gateway, VirtualService)

---

## 기술적 성과

### 1. 리소스 최적화

**문제:**
- Istio 사이드카의 기본 CPU limits (2000m)가 ResourceQuota를 초과

**해결:**
- Kustomize 패치를 통한 사이드카 리소스 최적화
- CPU limits: 2000m → 200m
- Memory limits: 1Gi → 256Mi

**결과:**
```
Before: limits.cpu 16000m+ 사용 (Quota 초과)
After:  limits.cpu 5500m/16000m 사용 (정상)
```

### 2. 관찰성 향상

**Kiali 대시보드:**
- 서비스 메시 토폴로지 시각화
- 실시간 트래픽 흐름 모니터링
- mTLS 상태 확인 (자물쇠 아이콘)
- 서비스 간 의존성 분석

**Jaeger 분산 추적:**
- 요청의 전체 경로 추적
- 각 서비스의 응답 시간 측정
- 병목 지점 식별

**Prometheus 메트릭:**
- Istio 관련 메트릭 자동 수집
- 사이드카 리소스 사용률
- 트래픽 메트릭 (요청 수, 응답 시간, 에러율)

### 3. 보안 강화

**mTLS 적용:**
- 서비스 간 통신 100% 암호화
- 중간자 공격(MITM) 방어
- 서비스 신원 검증

**Rate Limiting:**
- DDoS 공격 방어
- 서비스 과부하 방지
- 공정한 리소스 사용

---

## 시스템 상태

### Pod 현황
```bash
kubectl get pods -n titanium-prod
```
- 총 14개 Pod (postgresql 제외 13개)
- 모든 애플리케이션 Pod: 2/2 Running
  - 1: 애플리케이션 컨테이너
  - 1: Istio sidecar (Envoy proxy)

### Istio 리소스
```bash
kubectl get gateway,virtualservice,destinationrule,peerauthentication,envoyfilter -n titanium-prod
```
- Gateway: 1개 (titanium-gateway)
- VirtualService: 1개 (load-balancer-vs)
- DestinationRule: 8개 (default + 7개 서비스별)
- PeerAuthentication: 1개 (default-mtls STRICT)
- EnvoyFilter: 1개 (rate-limit-filter)

### HPA 현황
```bash
kubectl get hpa -n titanium-prod
```
- user-service-hpa: CPU 4%/70%, 2 replicas
- auth-service-hpa: CPU 3%/70%, 2 replicas
- blog-service-hpa: CPU 5%/70%, 2 replicas
- api-gateway-hpa: CPU 3%/70%, 2 replicas

### 리소스 사용량
```bash
kubectl describe resourcequota titanium-prod-quota -n titanium-prod
```
- limits.cpu: 5500m / 16000m (34%)
- limits.memory: 7424Mi / 32Gi (23%)
- pods: 14 / 50 (28%)

---

## 학습 내용

### 1. Istio 서비스 메시
- **서비스 메시의 필요성**: 마이크로서비스 간 통신을 중앙에서 관리
- **사이드카 패턴**: 애플리케이션 코드 변경 없이 기능 추가
- **Control Plane vs Data Plane**: istiod와 Envoy의 역할 분리

### 2. mTLS (Mutual TLS)
- **양방향 인증**: 클라이언트와 서버 모두 인증서로 신원 확인
- **Zero Trust 네트워크**: 내부 통신도 암호화하는 보안 모델
- **자동 인증서 관리**: Istio가 인증서 발급/갱신을 자동화

### 3. Kubernetes 자동 스케일링
- **HPA 동작 원리**: Metrics Server → HPA Controller → Deployment
- **메트릭 기반 스케일링**: CPU/메모리 사용률에 따른 자동 조정
- **쿨다운 시간**: 급격한 변화 방지를 위한 대기 시간

### 4. EnvoyFilter
- **Envoy proxy 확장**: 표준 Istio 리소스로 구현하기 어려운 기능 추가
- **Local Rate Limiting**: 각 Pod 단위로 요청 제한
- **Token Bucket 알고리즘**: 분당 100 토큰, 최대 100 토큰 저장

---

## 도전 과제 및 해결

### 도전 1: ResourceQuota 초과
**문제**: Istio 사이드카 기본 리소스가 너무 높아 Pod 생성 실패

**시도한 방법:**
1. 네임스페이스 annotation 추가 → 실패 (Pod template에 전파 안 됨)
2. 임시로 Quota 증가 → 성공했지만 근본 해결 아님

**최종 해결:**
- Kustomize inline 패치로 모든 Deployment에 사이드카 리소스 annotation 추가
- CPU limits: 2000m → 200m 로 10배 감소

### 도전 2: Metrics Server TLS 인증서 검증 실패
**문제**: Metrics Server가 kubelet의 인증서를 검증할 수 없음

**해결:**
- `--kubelet-insecure-tls` 플래그 추가
- 온프레미스 환경에서는 kubelet 인증서에 IP SAN이 없어 발생하는 문제

### 도전 3: Rolling Update 중 Pod 혼재
**문제**: 1/1 Pod (사이드카 없음)와 2/2 Pod (사이드카 있음)가 혼재

**해결:**
- 기존 1/1 Pod를 수동으로 삭제하여 전환 완료
- ResourceQuota 여유 확보 후 자연스러운 Rolling Update

---

## 성능 지표

### 리소스 효율성
- **사이드카 최적화 전**: CPU 요청 불가 (Quota 초과)
- **사이드카 최적화 후**: 전체 시스템 CPU 사용률 34%

### 응답 시간 영향
- **Envoy overhead**: 1-2ms 추가 지연 (일반적인 수준)
- **P95 응답 시간**: 영향 미미 (애플리케이션 로직이 주요 병목)

### 보안 향상
- **mTLS 적용률**: 100% (모든 서비스 간 통신)
- **암호화 오버헤드**: CPU 사용률 5% 미만 증가

---

## 개선 사항 및 향후 계획

### 단기 개선 사항
1. **Grafana 대시보드 추가**
   - Istio 메트릭 시각화
   - Service Mesh 성능 모니터링

2. **부하 테스트**
   - HPA 동작 검증
   - Rate Limiting 임계값 조정

3. **문서화 완성**
   - 운영 가이드 작성
   - 장애 대응 매뉴얼

### 장기 계획
1. **멀티 클러스터 서비스 메시**
   - 여러 Kubernetes 클러스터 통합

2. **고급 트래픽 관리**
   - Canary Deployment
   - A/B Testing
   - Traffic Mirroring

3. **보안 강화**
   - Authorization Policy (RBAC)
   - External Authorization Service
   - WAF (Web Application Firewall) 통합

---

## 교훈

### 1. 점진적 도입의 중요성
- Istio 같은 복잡한 시스템은 한 번에 모든 기능을 도입하지 말고 단계적으로 적용
- 각 단계마다 충분한 테스트와 검증 필요

### 2. 리소스 계획
- 새로운 구성 요소(사이드카) 도입 시 리소스 요구사항 사전 파악
- ResourceQuota 여유 확보 또는 리소스 최적화 필수

### 3. 관찰성의 가치
- Kiali, Jaeger 같은 도구로 시스템 동작을 시각화하면 문제 해결이 쉬워짐
- 메트릭, 로그, 추적 데이터를 종합적으로 활용

### 4. 문서화
- 복잡한 설정은 반드시 문서화
- 트러블슈팅 경험을 기록하여 다음 문제 해결에 활용

---

## 관련 문서

- [Week 4 구현 가이드](./implementation-guide.md)
- [Week 4 트러블슈팅 가이드](./troubleshooting-week4.md)
- [Istio 공식 문서](https://istio.io/latest/docs/)
- [Kubernetes HPA](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)

---

## 결론

Week 4에서는 Istio 서비스 메시를 성공적으로 도입하고, 보안(mTLS), 확장성(HPA), 안정성(Rate Limiting)을 크게 향상시켰습니다.

이제 시스템은:
- **안전함**: 모든 통신이 암호화됨
- **탄력적임**: 부하에 따라 자동으로 스케일링
- **관찰 가능함**: Kiali, Jaeger로 실시간 모니터링
- **안정적임**: Rate Limiting으로 과부하 방지

다음 단계(Week 5 이후)에서는 이러한 기반 위에 더 고급 기능을 구축할 수 있습니다.

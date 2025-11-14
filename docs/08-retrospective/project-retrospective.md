# Cloud-Native 마이크로서비스 플랫폼 v2.0 프로젝트 회고

## 프로젝트 정보
- **프로젝트명**: Cloud-Native 마이크로서비스 플랫폼 v2.0
- **개발 기간**: 2025년 9월 30일 ~ 11월 3일 (5주)
- **개발 환경**: 단국대학교 Solid Cloud
- **작성일**: 2025년 11월 3일
- **작성자**: 이동주

---

## 프로젝트 개요

로컬 환경(Minikube)에서 운영되던 마이크로서비스 블로그 플랫폼을 클라우드 네이티브 아키텍처로 재구축한 프로젝트입니다. Terraform을 이용한 인프라 자동화, GitOps 기반의 CI/CD 파이프라인, Istio 서비스 메시를 통한 관측성과 보안 강화를 목표로 5주간 진행되었습니다.

---

## 주요 성과

### 1. 프로젝트 목표 달성

**Must-Have 요구사항**: 100% 완료
- Terraform으로 Kubernetes 클러스터 생성
- PostgreSQL StatefulSet 배포 및 데이터 영속성 확인
- GitHub Actions CI 파이프라인 동작
- Argo CD GitOps 배포 자동화
- Prometheus + Grafana 모니터링 대시보드
- 모든 서비스 정상 동작 확인

**Should-Have 요구사항**: 100% 완료
- Loki 중앙 로깅 시스템
- Istio mTLS 활성화
- ADR 5건 작성 (목표 3건 초과 달성)

**Could-Have 요구사항**: 67% 완료
- Rate Limiting 구현 (완료)
- HPA 자동 확장 (완료)
- Jaeger 분산 추적 (미완료)

### 2. 기술적 성과

**완전 자동화된 CI/CD 파이프라인**:
- Git Push → 자동 빌드 → 자동 배포 전체 플로우 구축
- 평균 배포 시간: 5분 이내
- Trivy 보안 스캔 자동화
- 롤백 기능 구현

**관측성 시스템 구축**:
- Golden Signals 기반 실시간 모니터링
- 중앙 로깅 시스템으로 분산 로그 통합
- Istio 메트릭 수집 및 시각화
- AlertManager를 통한 알림 설정

**보안 강화**:
- Istio mTLS STRICT 모드로 서비스 간 암호화 통신
- NetworkPolicy를 통한 네트워크 격리
- RBAC를 통한 접근 제어
- Trivy를 통한 컨테이너 이미지 자동 보안 스캔

**고가용성 확보**:
- 주요 서비스 2+ replicas 유지
- HPA를 통한 자동 확장 설정
- StatefulSet을 통한 데이터 영속성 보장
- 실시간 P95 응답 시간 19.2ms, HTTP 실패율 0%

---

## 기술적 도전 과제 및 해결

### 1. Istio 메트릭 수집 문제

**문제**:
- Grafana 대시보드에서 Latency, Traffic, Errors 메트릭이 "No data"로 표시
- Prometheus가 Istio 메트릭을 수집하지 못하는 상황

**원인 분석**:
1. Prometheus가 Istio Control Plane (istiod)과 Envoy Proxy의 메트릭을 수집하지 못함
2. ServiceMonitor 및 PodMonitor 설정 누락
3. 대시보드 쿼리가 잘못된 메트릭 이름 사용
4. 레이블 이름 불일치 (status vs response_code)

**해결 과정**:
1. istiod용 ServiceMonitor 생성
2. envoy-proxy용 PodMonitor 생성 (relabeling 설정 포함)
3. 대시보드 쿼리 수정:
   - `http_requests_total` → `istio_requests_total`
   - `status` 레이블 → `response_code` 레이블
4. Latency 메트릭 단위 변환 추가 (밀리초 → 초)

**배운 점**:
- Istio 메트릭 구조에 대한 깊은 이해
- Prometheus Operator의 ServiceMonitor/PodMonitor 활용법
- PromQL 쿼리 작성 및 디버깅 능력 향상
- 메트릭 레이블 명명 규칙의 중요성

**파일**: `k8s-manifests/overlays/solid-cloud/istio/servicemonitors.yaml`

### 2. Grafana Pod 재시작 문제

**문제**:
- Grafana Pod가 `chown: /var/lib/grafana/csv: Permission denied` 오류로 재시작 실패
- PersistentVolumeClaim 권한 문제로 인한 무한 재시작

**시도한 해결 방법**:
1. Init container 제거 시도 → Deployment 충돌 발생
2. Deployment 직접 패치 시도 → JSON 검증 오류
3. PVC 강제 삭제 시도 → Terminating 상태에서 멈춤

**최종 해결**:
1. PVC finalizer 제거:
```bash
kubectl patch pvc prometheus-grafana -n monitoring -p '{"metadata":{"finalizers":null}}'
```
2. 새로운 PVC 생성 (local-path StorageClass)
3. Grafana Deployment 재시작

**배운 점**:
- Kubernetes finalizer의 역할과 처리 방법
- PersistentVolume의 라이프사이클 관리
- 권한 문제 해결을 위한 다양한 접근 방법
- 단순 삭제보다 근본 원인 해결의 중요성

### 3. 성능 병목 현상

**문제**:
- k6 부하 테스트에서 P95 응답 시간 835ms (목표: 500ms 미달성)
- 10명의 동시 사용자에서도 성능 저하 발생

**원인 분석**:
1. HPA minReplicas=1로 설정되어 단일 Pod가 모든 부하 처리
2. CPU 사용률이 낮아 (3-5%) HPA threshold (70%)에 도달하지 못함
3. 자동 스케일링이 발생하지 않음

**해결 과정**:
1. 리소스 사용률 분석 (kubectl top, Grafana 대시보드)
2. HPA 설정 검토 및 minReplicas 조정 (1 → 2)
3. 모든 주요 서비스에 동일 설정 적용
4. 재테스트 수행

**결과**:
- P95 응답 시간: 835ms → 739ms (11.6% 개선)
- 고가용성 확보 (장애 발생 시 서비스 지속 가능)
- 실시간 환경에서 P95 19.2ms 달성

**배운 점**:
- HPA 설정의 중요성과 최적화 방법
- minReplicas와 maxReplicas 밸런스 조정
- 부하 테스트의 중요성과 성능 병목 분석 능력
- 리소스 사용률과 애플리케이션 성능의 상관관계

**파일**: `k8s-manifests/overlays/solid-cloud/hpa.yaml`

### 4. Solid Cloud 환경 적응

**도전 과제**:
- AWS EKS 기반으로 설계된 프로젝트를 Solid Cloud로 전환
- Token 기반 인증 방식 적용
- 제한된 리소스 환경에서의 최적화

**해결 과정**:
1. Terraform 코드를 Solid Cloud API에 맞게 수정
2. .env.k8s 파일 기반 인증 시스템 구축
3. 스크립트를 통한 환경 전환 자동화 (switch-to-cloud.sh)
4. Kustomize Overlays를 통한 환경별 설정 분리

**배운 점**:
- 클라우드 플랫폼 간의 차이점과 이식성
- IaC (Infrastructure as Code)의 유연성과 한계
- 환경 추상화의 중요성
- 제한된 리소스에서의 최적화 기법

---

## 각 주차별 회고

### Week 1: 인프라 기반 구축 (9/30 ~ 10/6)

**목표**: Terraform을 사용하여 Solid Cloud에 Kubernetes 클러스터와 기본 인프라 구축

**잘한 점**:
- Terraform 코드를 모듈화하여 재사용성 확보
- Kustomize Overlays로 환경별 설정 분리 (local, solid-cloud)
- PostgreSQL StatefulSet으로 데이터 영속성 확보
- 통합 테스트 스크립트 작성으로 검증 자동화

**아쉬운 점**:
- Terraform 학습에 예상보다 시간 소요
- Solid Cloud 특성 파악에 시행착오 발생

**배운 것**:
- Terraform으로 인프라를 코드로 관리하는 방법
- Kubernetes StatefulSet과 PersistentVolume 개념
- 환경별 설정 관리의 중요성

### Week 2: CI/CD 파이프라인 구축 (10/7 ~ 10/13)

**목표**: GitHub Actions와 Argo CD를 연동하여 자동 배포 파이프라인 완성

**잘한 점**:
- GitHub Actions workflow를 CI와 CD로 명확히 분리
- Trivy 보안 스캔을 CI 파이프라인에 통합
- Argo CD 자동 동기화 설정으로 GitOps 완전 구현
- 전체 파이프라인 5분 이내 완료 달성

**아쉬운 점**:
- 초기 Argo CD 설정에서 권한 문제 발생
- Docker Hub rate limit 문제 고려 필요

**배운 것**:
- GitOps 방법론과 선언적 배포의 장점
- GitHub Actions의 workflow 작성법과 베스트 프랙티스
- Argo CD의 Application CRD와 동기화 정책

### Week 3: 관측성 시스템 구축 (10/14 ~ 10/20)

**목표**: Prometheus, Grafana, Loki를 설치하여 시스템 모니터링 환경 구축

**잘한 점**:
- Prometheus Operator를 사용하여 메트릭 수집 자동화
- Golden Signals 기반 대시보드로 핵심 메트릭 집중 모니터링
- Loki와 Promtail로 중앙 로깅 구현
- AlertManager 설정으로 알림 체계 구축

**아쉬운 점**:
- 초기 ServiceMonitor 설정 미흡으로 메트릭 수집 누락
- Grafana 대시보드 쿼리 작성에 시행착오

**배운 것**:
- Prometheus Operator의 ServiceMonitor/PodMonitor 개념
- PromQL 쿼리 작성법
- Golden Signals (Latency, Traffic, Errors, Saturation) 이해
- Loki의 LogQL 쿼리 작성법

### Week 4: Should-Have 기능 구현 (10/21 ~ 10/27)

**목표**: Istio 서비스 메시 적용 및 추가 기능 구현

**잘한 점**:
- Istio 1.20.1 설치 및 sidecar 자동 주입 성공
- mTLS STRICT 모드로 서비스 간 암호화 통신 구현
- Kiali 연동으로 서비스 메시 시각화
- VirtualService와 DestinationRule로 트래픽 관리

**아쉬운 점**:
- Istio 복잡도로 인한 학습 곡선
- 초기 Istio 메트릭 수집 문제 발생
- Rate Limiting 구현은 했으나 검증 미흡

**배운 것**:
- Istio 아키텍처와 sidecar 패턴
- mTLS 동작 원리와 PeerAuthentication 설정
- Envoy Proxy의 역할과 메트릭 수집
- 서비스 메시의 장점과 트레이드오프

### Week 5: 테스트 및 문서화 (10/28 ~ 11/3)

**목표**: 최종 테스트 수행 및 프로젝트 문서 완성

**잘한 점**:
- k6를 사용한 체계적인 부하 테스트 수행
- 성능 병목 분석 및 HPA 최적화로 11.6% 개선
- 보안 검증 (Trivy, mTLS, NetworkPolicy, RBAC) 완료
- ADR 5건 작성 (목표 초과 달성)
- 운영 가이드 등 실용적인 문서 작성

**아쉬운 점**:
- 시간 부족으로 장애 복구 시나리오 테스트 미완료
- Jaeger 분산 추적 시스템 구축 못함
- 프로젝트 회고 작성에 충분한 시간 확보 못함

**배운 것**:
- 부하 테스트 도구 (k6) 사용법
- 성능 병목 분석 및 최적화 방법
- 문서화의 중요성과 베스트 프랙티스
- ADR (Architecture Decision Record) 작성법

---

## 기술 스택별 학습 내용

### Kubernetes
**배운 것**:
- Deployment, StatefulSet, Service, Ingress 등 핵심 리소스
- ConfigMap과 Secret을 통한 설정 관리
- PersistentVolume과 PersistentVolumeClaim
- HorizontalPodAutoscaler (HPA) 설정 및 최적화
- NetworkPolicy를 통한 네트워크 격리
- RBAC (Role-Based Access Control)

**어려웠던 점**:
- StatefulSet의 복잡한 라이프사이클 관리
- PVC finalizer 문제 해결
- HPA threshold 설정 최적화

### Terraform
**배운 것**:
- IaC (Infrastructure as Code) 개념과 장점
- Terraform 기본 문법 (resource, variable, output)
- 모듈화를 통한 코드 재사용
- State 관리의 중요성

**어려웠던 점**:
- Solid Cloud API와의 호환성 문제
- Provider 설정 및 인증 방식 이해

### CI/CD (GitHub Actions + Argo CD)
**배운 것**:
- GitHub Actions workflow 작성법
- Docker 이미지 빌드 및 푸시 자동화
- Trivy 보안 스캔 통합
- GitOps 방법론과 선언적 배포
- Argo CD Application CRD와 동기화 정책

**어려웠던 점**:
- GitHub Actions와 Argo CD 간의 워크플로우 설계
- Secrets 관리 (GitHub Secrets, Kubernetes Secrets)

### Istio
**배운 것**:
- 서비스 메시 아키텍처와 sidecar 패턴
- mTLS (mutual TLS) 동작 원리
- VirtualService와 DestinationRule을 통한 트래픽 관리
- Envoy Proxy 메트릭 수집 및 활용
- PeerAuthentication과 AuthorizationPolicy

**어려웠던 점**:
- Istio의 높은 복잡도와 학습 곡선
- Istio 메트릭 수집 설정
- mTLS 디버깅 및 검증

### 모니터링 (Prometheus + Grafana + Loki)
**배운 것**:
- Prometheus 아키텍처와 메트릭 수집 방식
- ServiceMonitor와 PodMonitor 설정
- PromQL 쿼리 작성 및 최적화
- Grafana 대시보드 설계 (Golden Signals)
- Loki와 Promtail을 통한 중앙 로깅
- LogQL 쿼리 작성법

**어려웠던 점**:
- PromQL의 복잡한 쿼리 작성
- Istio 메트릭과 Prometheus 연동
- Grafana 대시보드 JSON 구조 이해

---

## 프로젝트 관리 측면

### 잘한 점

**계획 수립**:
- 5주 개발 계획을 Must-Have, Should-Have, Could-Have로 명확히 구분
- 주차별 목표 설정으로 진행 상황 추적 용이
- 마일스톤 설정으로 중간 점검 가능

**문서화**:
- ADR (Architecture Decision Record)로 기술 결정 과정 기록
- 주차별 구현 가이드 작성
- 상세한 트러블슈팅 문서 작성

**우선순위 관리**:
- Must-Have에 집중하여 핵심 기능 완성
- Should-Have도 모두 완료하여 목표 초과 달성
- Could-Have는 선택적으로 구현

### 아쉬운 점

**시간 관리**:
- Week 4에서 Istio 복잡도로 인해 예상보다 시간 소요
- Week 5에서 장애 복구 테스트 미완료
- 마지막 주에 문서화 작업 집중으로 시간 부족

**범위 관리**:
- Jaeger 분산 추적 시스템 구축 못함
- 일부 Could-Have 항목 미완료

**테스트**:
- 단위 테스트 및 통합 테스트 커버리지 부족
- 장애 복구 시나리오 테스트 미완료

### 개선할 점

**프로젝트 계획**:
- 각 작업의 예상 시간을 더 보수적으로 설정
- 버퍼 타임을 충분히 확보
- 주간 검토 시간을 명시적으로 계획에 포함

**기술 학습**:
- 신기술(Istio 등) 학습에 더 많은 시간 할당
- 공식 문서와 튜토리얼을 먼저 숙지한 후 구현

**문서화**:
- 진행하면서 동시에 문서화 (나중에 몰아서 하지 않기)
- 트러블슈팅 내용을 즉시 기록

---

## 프로젝트를 통해 얻은 인사이트

### 1. 클라우드 네이티브 아키텍처의 가치

**인사이트**:
- 자동화된 CI/CD 파이프라인은 개발 생산성을 크게 향상시킴
- 관측성(Observability)은 시스템 운영에 필수적
- 인프라를 코드로 관리하면 재현 가능하고 버전 관리가 가능함

**실제 경험**:
- Git Push만으로 5분 이내에 프로덕션 배포 완료
- Grafana 대시보드로 실시간 시스템 상태 파악
- Terraform으로 인프라를 언제든 재생성 가능

### 2. 마이크로서비스의 복잡도

**인사이트**:
- 마이크로서비스는 확장성과 유연성을 제공하지만 복잡도가 높음
- 서비스 간 통신, 모니터링, 로깅, 보안 등 고려 사항이 많음
- Istio와 같은 서비스 메시가 이러한 복잡도를 해결하는 데 도움

**실제 경험**:
- 5개의 마이크로서비스 관리에만 14개의 Pod 실행
- Istio 도입으로 mTLS, 트래픽 관리, 메트릭 수집 자동화
- 중앙 로깅 시스템으로 분산된 로그 통합 조회 가능

### 3. 관측성의 중요성

**인사이트**:
- 시스템을 제대로 관측할 수 없으면 문제를 해결할 수 없음
- 메트릭, 로그, 트레이스가 모두 필요 (아직 트레이스는 미구현)
- Golden Signals (Latency, Traffic, Errors, Saturation)는 핵심 지표

**실제 경험**:
- Grafana 대시보드가 없었다면 성능 병목 발견 불가능
- Loki 로그 조회로 에러 원인 빠르게 파악
- Istio 메트릭으로 서비스 간 통신 상태 모니터링

### 4. 보안은 설계 단계부터

**인사이트**:
- 보안은 나중에 추가하는 것이 아니라 처음부터 설계해야 함
- mTLS, NetworkPolicy, RBAC 등 다층 보안 필요
- 자동화된 보안 스캔(Trivy)으로 지속적인 검증

**실제 경험**:
- Istio mTLS STRICT로 모든 서비스 간 통신 암호화
- NetworkPolicy로 불필요한 트래픽 차단
- CI 파이프라인에 Trivy 통합으로 취약점 조기 발견

### 5. 문서화는 미래의 나를 위한 투자

**인사이트**:
- 상세한 문서는 운영과 유지보수에 필수적
- ADR (Architecture Decision Record)은 기술 결정의 컨텍스트 보존
- 트러블슈팅 문서는 동일 문제 재발 시 시간 절약

**실제 경험**:
- Istio 메트릭 문제 해결 과정을 문서화하여 유사 문제 빠르게 해결
- 운영 가이드 작성으로 시스템 인수인계 준비
- ADR 5건 작성으로 기술 선택 근거 명확히 기록

---

## 향후 개선 계획

### 단기 개선 사항 (1개월 이내)

**1. 장애 복구 테스트 완료**:
- Pod 강제 종료 시 자동 복구 확인
- 데이터베이스 장애 시나리오 테스트
- 서비스 롤백 시나리오 테스트

**2. 성능 추가 최적화**:
- 애플리케이션 코드 프로파일링
- 데이터베이스 쿼리 최적화
- Istio 프록시 오버헤드 분석 및 최적화

**3. 테스트 자동화**:
- 단위 테스트 추가 (목표: 70% 커버리지)
- 통합 테스트 자동화
- E2E 테스트 시나리오 작성

### 중기 개선 사항 (3개월 이내)

**1. Jaeger 분산 추적**:
- Jaeger 설치 및 서비스 연동
- 요청 흐름 시각화
- 병목 지점 분석 자동화

**2. 고급 배포 전략**:
- Canary 배포 구현
- Blue-Green 배포 구현
- Argo Rollouts 도입 검토

**3. 캐싱 전략**:
- Redis 캐싱 레이어 추가
- CDN 활용 검토
- 데이터베이스 Read Replica 추가

### 장기 개선 사항 (6개월 이내)

**1. Multi-region 배포**:
- 여러 지역에 클러스터 배포
- 글로벌 로드 밸런싱
- 지역 간 데이터 동기화

**2. 고급 보안**:
- Open Policy Agent (OPA) 도입
- Falco 런타임 보안 모니터링
- Vault를 통한 Secrets 관리

**3. 비용 최적화**:
- 리소스 사용량 분석 및 최적화
- Spot Instance 활용 검토
- 자동 스케일링 정책 고도화

---

## 다른 프로젝트에 적용할 교훈

### 1. 점진적 접근

**교훈**: 복잡한 시스템은 한 번에 구축하지 말고 단계적으로 접근

**적용 방법**:
- Week 1: 기본 인프라
- Week 2: CI/CD
- Week 3: 모니터링
- Week 4: 고급 기능
- Week 5: 테스트 및 문서화

### 2. 자동화 우선

**교훈**: 반복 작업은 최대한 빨리 자동화

**적용 방법**:
- CI/CD 파이프라인 초기 구축
- 테스트 스크립트 작성
- 모니터링 알림 설정

### 3. 관측성 필수

**교훈**: 시스템을 만들면서 동시에 관측 수단도 구축

**적용 방법**:
- Prometheus, Grafana, Loki 초기 설치
- 애플리케이션에 /metrics 엔드포인트 추가
- 핵심 메트릭 대시보드 먼저 구성

### 4. 문서화 습관

**교훈**: 나중에 몰아서 하지 말고 진행하면서 바로 문서화

**적용 방법**:
- 주요 기술 결정 시 ADR 즉시 작성
- 트러블슈팅 과정 즉시 기록
- README 지속적 업데이트

### 5. 실용주의

**교훈**: 완벽을 추구하기보다 핵심 기능에 집중

**적용 방법**:
- Must-Have, Should-Have, Could-Have 명확히 구분
- 시간 부족 시 과감히 포기할 항목 미리 선정
- 완성도 80%를 목표로 (100%는 비현실적)

---

## 최종 소감

이번 프로젝트를 통해 클라우드 네이티브 기술 스택을 종합적으로 경험할 수 있었습니다. Kubernetes, Terraform, Istio, Prometheus 등 각각 강력하지만 복잡한 도구들을 하나의 시스템으로 통합하는 과정은 도전적이었지만 매우 값진 경험이었습니다.

특히 **자동화의 힘**을 실감했습니다. Git Push만으로 5분 이내에 프로덕션 배포가 완료되고, Grafana 대시보드에서 실시간으로 시스템 상태를 확인할 수 있는 것은 매우 값진 경험이었습니다.

**Istio 서비스 메시**는 학습 곡선이 가파르지만, mTLS를 통한 자동 암호화, 트래픽 관리, 메트릭 수집 등의 기능은 마이크로서비스 운영에 매우 유용했습니다.

**관측성**의 중요성도 다시 한번 깨달았습니다. Prometheus + Grafana + Loki를 통해 시스템을 360도로 관측할 수 있었고, 이는 문제 해결과 성능 최적화에 결정적인 역할을 했습니다.

시간 부족으로 Jaeger 분산 추적과 장애 복구 테스트를 완료하지 못한 것은 아쉽지만, **Must-Have 100%, Should-Have 100%를 달성**하여 프로젝트의 핵심 목표는 모두 완수했습니다.

이번 프로젝트에서 배운 기술과 경험은 앞으로 더 큰 규모의 시스템을 설계하고 운영하는 데 큰 자산이 될 것입니다.

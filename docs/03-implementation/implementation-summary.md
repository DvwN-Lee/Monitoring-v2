# Implementation Summary

## 프로젝트 개요

**프로젝트명**: Cloud-Native 마이크로서비스 플랫폼 v2.0

**프로젝트 기간**: 2025년 9월 30일 ~ 2025년 11월 3일 (5주)

**개발 환경**: 단국대학교 Solid Cloud

**Kubernetes 버전**: v1.29.7

이 프로젝트는 로컬 개발 환경(Minikube + SQLite)에서 동작하던 마이크로서비스를 클라우드 환경(Solid Cloud + PostgreSQL)으로 전환하고, 완전 자동화된 CI/CD 파이프라인, 서비스 메시, 그리고 포괄적인 관측성 시스템을 구축하여 엔터프라이즈급 마이크로서비스 플랫폼을 완성했습니다.

**전체 완료율**:
- Must-Have 요구사항: 100%
- Should-Have 요구사항: 100%
- Could-Have 요구사항: 67%

---

## Week 1: 인프라 기반 구축

**기간**: 2025-10-27 ~ 2025-10-28

**목표**: Terraform으로 Kubernetes 클러스터를 구축하고 PostgreSQL로 DB 전환

### 주요 성과

**완료된 작업**:
- Terraform 기반 Infrastructure as Code (IaC) 구축
- Kubernetes 클러스터 구성 (Control Plane 1개, Worker 3개)
- SQLite → PostgreSQL 데이터베이스 마이그레이션
- Kustomize 기반 환경 분리 (Local/Cloud overlays)
- 배포 및 테스트 자동화 스크립트 작성

**아키텍처 변화**:

**이전**:
- Minikube 로컬 환경만 지원
- SQLite 파일 기반 DB
- 수동 배포 (skaffold)

**이후**:
- 멀티 환경 지원 (Local + Cloud)
- PostgreSQL 중앙화된 DB
- Terraform 자동화 배포
- Kustomize 환경별 설정 관리

### 산출물

**Terraform 모듈**:
```
terraform/modules/
├── network/         # VPC, Subnet 구성
├── kubernetes/      # 클러스터 및 Namespace
└── database/        # PostgreSQL StatefulSet
```

**환경별 설정**:
```
k8s-manifests/overlays/
├── local/          # 로컬 개발 환경 (Minikube)
└── solid-cloud/    # 클라우드 프로덕션 환경
```

**데이터베이스 마이그레이션**:
- user-service: SQLite → PostgreSQL (psycopg2)
- blog-service: SQLite → PostgreSQL (psycopg2)
- 스키마: users, posts 테이블 + 인덱스

### 검증 결과

- Terraform apply 성공 (3분 소요)
- Kubernetes 클러스터 4노드 Ready
- PostgreSQL Running (10Gi PVC Bound)
- 데이터베이스 연결 및 CRUD 정상 동작

### 주요 학습 내용

- Infrastructure as Code (IaC) 원칙 및 Terraform 활용
- Kustomize Base/Overlay 패턴을 통한 환경 분리 전략
- 데이터베이스 마이그레이션 (파일 기반 → 네트워크 기반)
- Kubernetes 스토리지 관리 (PVC, PV, StorageClass)

---

## Week 2: CI/CD 및 GitOps

**기간**: 2025-10-07 ~ 2025-10-13

**목표**: Git Push만으로 빌드부터 배포까지 자동화

### 주요 성과

**CI 파이프라인 구축**:
- GitHub Actions 기반 자동 빌드 파이프라인
- 변경된 서비스만 자동 감지 및 빌드
- 멀티 플랫폼 Docker 이미지 빌드 (linux/amd64, linux/arm64)
- Trivy 보안 스캔 통합
- Docker Hub 자동 푸시

**CD 파이프라인 구축**:
- Argo CD GitOps 도구 설치 및 구성
- kustomization.yaml 이미지 태그 자동 업데이트
- 자동 동기화 및 배포 (3분 주기)

**아키텍처**:
```
Git Push → GitHub Actions CI (빌드/스캔)
    ↓
Docker Hub Push
    ↓
GitHub Actions CD (매니페스트 업데이트)
    ↓
Argo CD (자동 배포)
    ↓
Kubernetes Cluster
```

### 이미지 태그 전략

**Pull Request**:
- `pr-{pr-number}`: PR 번호 포함 테스트 이미지
- Docker Hub에 푸시하지 않음 (빌드만)

**Main 브랜치**:
- `main-{short-sha}`: Git commit SHA 포함 이미지
- `latest`: 최신 stable 이미지

### 보안 스캔

**Trivy 보안 스캔**:
- CRITICAL 및 HIGH 취약점 스캔
- GitHub Security 탭에 SARIF 형식으로 업로드
- PR에 코멘트로 요약 결과 게시

### Argo CD 구성

**syncPolicy 설정**:
- `prune: true`: Git에서 삭제된 리소스를 클러스터에서도 삭제
- `selfHeal: true`: 클러스터의 리소스가 변경되면 자동으로 Git 상태로 복구
- `allowEmpty: false`: 빈 커밋 무시

---

## Week 3: 모니터링 및 관측성

**기간**: 2025-10-14 ~ 2025-10-20

**목표**: Prometheus, Grafana, Loki를 사용한 포괄적인 관측성 시스템 구축

### 주요 성과

**1. Prometheus 기반 메트릭 수집**:
- Prometheus Operator 설치 및 구성
- ServiceMonitor 생성 (각 마이크로서비스별)
- 모든 네임스페이스에서 메트릭 수집 설정
- Custom Rules: CPU/메모리 사용량 알림 규칙

**2. Grafana 시각화**:
- Golden Signals Dashboard 구축
  - **Latency**: P95, P99 응답 시간 추적
  - **Traffic**: 서비스별 초당 요청(RPS)
  - **Errors**: 4xx, 5xx 에러 비율
  - **Saturation**: CPU 및 메모리 사용률
- 데이터소스 자동 프로비저닝 (Prometheus, Loki)
- 대시보드 자동 프로비저닝 (ConfigMap 및 sidecar)

**3. Loki 중앙 로깅 시스템**:
- Loki: 로그 저장소 (7일 보존 기간)
- Promtail: DaemonSet으로 모든 노드에서 로그 수집
- JSON 파싱: 애플리케이션의 JSON 형식 로그 자동 파싱
- Grafana 통합: LogQL을 통한 로그 조회 및 분석

**4. GitOps 통합**:
- 모든 모니터링 구성 요소를 Argo CD Application으로 관리
- Kustomize 기반 환경별 설정 관리
- Git 리포지토리의 변경 사항 자동 동기화

### 아키텍처

```
[Kubernetes Cluster]
├── [Monitoring Namespace]
│   ├── Prometheus Operator
│   │   └── Prometheus (Metrics Data)
│   ├── Grafana (Visualization)
│   └── Loki (Log Data)
│
└── [Application Namespaces]
    ├── Pods
    │   └── Metrics Endpoint (/metrics)
    └── Promtail (Log Collector)
```

---

## Week 4: 서비스 메시 및 보안

**기간**: 2025-10-21 ~ 2025-10-27

**목표**: Istio 서비스 메시 도입 및 고급 기능 구현

### 주요 성과

**1. Istio 서비스 메시 구축**:
- Istio 1.20.1 설치 (demo profile)
- 구성 요소: istiod, istio-ingressgateway, istio-egressgateway
- 사이드카 자동 주입: 모든 애플리케이션 Pod에 Envoy proxy 주입
- 리소스 최적화: 사이드카 CPU limits 2000m → 200m (10배 감소)
- Gateway 및 VirtualService 생성

**2. mTLS 보안 강화**:
- PeerAuthentication STRICT 모드 활성화
- DestinationRule: 모든 서비스에 ISTIO_MUTUAL TLS 모드 적용
- 인증서 자동 발급 및 갱신
- 서비스 간 통신 100% 암호화

**3. 자동 스케일링 (HPA)**:
- Metrics Server 설치 (kubelet TLS 설정)
- HPA 적용 서비스: user-service, auth-service, blog-service, api-gateway
- 설정: minReplicas: 2, maxReplicas: 5, CPU 목표: 70%

**4. API Rate Limiting**:
- Istio EnvoyFilter 사용
- 적용 대상: load-balancer 서비스
- 제한: 분당 100 요청 (Local Rate Limit)
- Token Bucket 알고리즘 적용

**5. 관찰성 향상**:
- Kiali 대시보드: 서비스 메시 토폴로지 시각화
- Jaeger 분산 추적 (기본 설치)
- Prometheus Istio 메트릭 자동 수집

### 아키텍처 변화

**Before (Week 3)**:
```
[External Traffic]
    ↓
[Load Balancer Service]
    ↓
[Application Pods]
    ↓
[Other Services]
```

**After (Week 4)**:
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

### 시스템 상태

**Pod 현황**:
- 총 12개 Pod (api-gateway:2, auth:2, blog:2, user:2, redis:1, load-generator:2, postgresql:1)
- 모든 애플리케이션 Pod: 2/2 Running
  - 1: 애플리케이션 컨테이너
  - 1: Istio sidecar (Envoy proxy)

**Istio 리소스**:
- Gateway: 1개 (titanium-gateway)
- VirtualService: 1개 (load-balancer-vs)
- DestinationRule: 8개 (default + 7개 서비스별)
- PeerAuthentication: 1개 (default-mtls STRICT)
- EnvoyFilter: 1개 (rate-limit-filter)

**리소스 사용량**:
- limits.cpu: 5500m / 16000m (34%)
- limits.memory: 7424Mi / 32Gi (23%)
- pods: 14 / 50 (28%)

### 주요 도전 과제 및 해결

**도전 1: ResourceQuota 초과**

문제: Istio 사이드카 기본 리소스(CPU: 2000m)가 너무 높아 Pod 생성 실패

해결: Kustomize inline 패치로 모든 Deployment에 사이드카 리소스 annotation 추가
- CPU limits: 2000m → 200m (10배 감소)
- Memory limits: 1Gi → 256Mi

**도전 2: Metrics Server TLS 인증서 검증 실패**

문제: Metrics Server가 kubelet의 인증서를 검증할 수 없음

해결: `--kubelet-insecure-tls` 플래그 추가 (온프레미스 환경)

---

## Week 5: 최적화 및 안정화

**기간**: 2025-10-28 ~ 2025-11-03

**목표**: 성능 테스트, 보안 검증, 문서화 및 최종 점검

### 주요 성과

**1. 성능 테스트 및 최적화**:
- k6를 사용한 부하 테스트 수행
- 초기 성능 측정: P95 835.68ms
- 병목 지점 분석: HPA minReplicas=1로 인한 단일 Pod 병목
- 최적화 수행: HPA minReplicas를 2로 증가
- 최적화 후 성능: P95 738.75ms (11.6% 개선)

**실시간 성능 지표**:
- Latency P95: 19.2ms
- Latency P99: 23.8ms
- Traffic: 0.210 req/s
- Errors: 0%
- Saturation: CPU 1-3%

**2. 보안 검증**:
- Trivy 보안 스캔: CI 파이프라인 통합 완료
- Secrets 관리: Kubernetes Secrets 사용
- RBAC 설정: ServiceAccount, Role, RoleBinding 구성
- NetworkPolicy: Calico CNI 기반 네트워크 격리
- Istio mTLS: STRICT 모드 활성화

**3. Grafana 메트릭 표시 문제 해결**:

문제: Grafana 대시보드에서 Latency, Traffic, Errors가 "No data"로 표시

원인:
- Prometheus가 Istio 메트릭을 수집하지 못함
- 대시보드 쿼리가 잘못된 메트릭 이름 사용
- 잘못된 레이블 사용 (`status` 대신 `response_code`)

해결:
- ServiceMonitor 생성: istiod 메트릭 수집
- PodMonitor 생성: envoy-proxy 사이드카 메트릭 수집
- 대시보드 쿼리 수정: 올바른 메트릭 이름 및 레이블 사용

**4. 문서화**:
- Architecture Decision Records (ADR): 5건 작성
- 시스템 설계 문서 작성
- Week 4 구현 가이드 및 트러블슈팅 가이드 작성
- 성능 분석 문서 작성

---

## 주요 기술 결정 사항

### 1. Argo CD vs Flux (GitOps 도구)

**선택**: Argo CD

**근거**:
- 직관적인 UI로 배포 상태 시각화 용이
- 멀티 클러스터 관리 기능 제공
- 대규모 커뮤니티 및 활발한 개발
- Kubernetes 네이티브 설치 방식

### 2. PostgreSQL vs SQLite (데이터베이스)

**선택**: PostgreSQL

**근거**:
- 중앙화된 데이터 관리
- 멀티 Pod 환경에서 데이터 일관성 보장
- 트랜잭션 지원 및 동시성 제어
- 프로덕션 환경에 적합

### 3. Loki vs EFK (로깅 시스템)

**선택**: Loki

**근거**:
- 경량 구조로 리소스 효율적
- Grafana와 네이티브 통합
- LogQL을 통한 직관적인 로그 쿼리
- Prometheus와 유사한 레이블 기반 인덱싱

### 4. GitHub Actions vs Jenkins (CI/CD)

**선택**: GitHub Actions

**근거**:
- 코드 저장소와 동일 플랫폼으로 관리 편의성
- YAML 기반 선언적 설정
- GitHub Marketplace를 통한 다양한 액션 활용
- 별도 서버 관리 불필요

### 5. Terraform vs Pulumi (IaC)

**선택**: Terraform

**근거**:
- 성숙한 에코시스템 및 대규모 커뮤니티
- HCL 언어의 명확성 및 가독성
- 다양한 Provider 지원
- State 관리 기능 우수

---

## 주요 기술 스택

| 카테고리 | 기술 | 버전 | 용도 |
|---------|------|------|------|
| **인프라** | Terraform | - | IaC (Infrastructure as Code) |
| | Kubernetes | v1.29.7 | 컨테이너 오케스트레이션 |
| | Calico | - | CNI 및 NetworkPolicy |
| **CI/CD** | GitHub Actions | - | CI/CD 파이프라인 |
| | Argo CD | v2.8.4 | GitOps 배포 자동화 |
| | Docker | - | 컨테이너 이미지 빌드 |
| | Trivy | - | 보안 스캔 |
| **모니터링** | Prometheus | - | 메트릭 수집 및 저장 |
| | Grafana | - | 시각화 대시보드 |
| | AlertManager | - | 알림 관리 |
| **로깅** | Loki | 3.5.7 | 중앙 로그 저장소 |
| | Promtail | 3.5.1 | 로그 수집 에이전트 |
| **서비스 메시** | Istio | 1.20.1 | mTLS, 트래픽 관리 |
| **데이터베이스** | PostgreSQL | - | 관계형 데이터베이스 |
| **테스트** | k6 | v1.3.0 | 부하 테스트 |

---

## 구현 성과

### 1. 완전 자동화된 CI/CD 파이프라인

**달성 내용**:
- Git Push → 자동 빌드 → 자동 배포 전체 플로우 구축
- 평균 배포 시간: 5분 이내
- 롤백 기능: Argo CD를 통한 즉시 롤백 가능

### 2. 관측성 시스템 구축

**달성 내용**:
- Golden Signals 대시보드를 통한 실시간 모니터링
- 중앙 로깅 시스템으로 분산 로그 통합
- Istio 메트릭 수집 및 시각화

**실시간 지표**:
- Latency P95: 19.2ms
- Latency P99: 23.8ms
- HTTP 실패율: 0%
- CPU 사용률: 1-3%

### 3. 보안 강화

**달성 내용**:
- mTLS를 통한 서비스 간 암호화 통신 (100%)
- Trivy를 통한 자동 보안 스캔
- NetworkPolicy를 통한 네트워크 격리
- RBAC를 통한 접근 제어

### 4. 고가용성 확보

**달성 내용**:
- 주요 서비스 2+ replicas 유지
- HPA를 통한 자동 확장 설정 (minReplicas: 2, maxReplicas: 5)
- StatefulSet을 통한 데이터 영속성 보장

### 5. 성능 최적화

**달성 내용**:
- P95 응답 시간 11.6% 개선 (835ms → 739ms)
- 실시간 P95 응답 시간 19.2ms 달성
- HTTP 실패율 0% 유지

### 6. 리소스 최적화

**달성 내용**:
- Istio 사이드카 리소스 최적화 (CPU limits 10배 감소)
- 전체 시스템 리소스 사용률 최적화
  - CPU: 34% (5500m/16000m)
  - Memory: 23% (7424Mi/32Gi)
  - Pods: 28% (14/50)

### 7. 문서화

**달성 내용**:
- ADR 5건 작성
- 주차별 구현 가이드 및 트러블슈팅 가이드 작성
- 성능 분석 문서 작성
- 시스템 아키텍처 문서 작성

---

## 주요 학습 내용

### 1. GitOps 기반 배포 자동화
- Argo CD를 사용한 선언적 배포 관리
- Kustomize를 활용한 환경별 설정 관리
- Git을 Single Source of Truth로 사용하는 배포 전략

### 2. Istio 서비스 메시
- Sidecar 패턴을 통한 트래픽 관리
- mTLS를 통한 서비스 간 보안 통신
- Envoy 프록시 메트릭 수집 및 활용
- Control Plane vs Data Plane의 역할 분리

### 3. Prometheus + Grafana 관측성
- ServiceMonitor 및 PodMonitor를 통한 메트릭 수집
- Golden Signals (Latency, Traffic, Errors, Saturation) 모니터링
- PromQL을 사용한 복잡한 쿼리 작성

### 4. Loki 중앙 로깅
- Promtail DaemonSet을 통한 로그 수집
- Grafana에서 로그와 메트릭 통합 조회
- LogQL을 사용한 로그 검색 및 필터링

### 5. Kubernetes HPA
- CPU 기반 자동 확장 설정
- minReplicas 및 maxReplicas 최적화
- 성능과 리소스 효율성 균형 유지

### 6. Infrastructure as Code
- Terraform을 통한 선언적 인프라 관리
- 코드로 관리되는 인프라의 장점: 버전 관리, 재현 가능성, 자동화

---

## 프로젝트 타임라인

| 주차 | 기간 | 목표 | 완료율 |
|------|------|------|--------|
| Week 1 | 9/30 - 10/6 | 인프라 기반 구축 | 100% |
| Week 2 | 10/7 - 10/13 | CI/CD 파이프라인 구축 | 100% |
| Week 3 | 10/14 - 10/20 | 관측성 시스템 구축 | 100% |
| Week 4 | 10/21 - 10/27 | 서비스 메시 및 보안 | 100% |
| Week 5 | 10/28 - 11/3 | 테스트 및 최적화 | 100% |

---

## 최종 평가

이번 프로젝트는 **5주간의 계획된 일정 내에 모든 핵심 요구사항을 달성**했으며, 실제 운영 환경에서 사용 가능한 수준의 시스템을 구축했습니다.

**주요 성과**:
- Must-Have 요구사항 100% 달성
- Should-Have 요구사항 100% 달성
- Could-Have 요구사항 67% 달성

**현재 시스템 상태**:
- 안정적으로 운영 중
- 완전 자동화된 CI/CD 파이프라인
- 서비스 간 통신 100% 암호화 (mTLS)
- 실시간 모니터링 및 로깅 시스템 구축
- 고가용성 및 자동 확장 구현

특히 Istio 서비스 메시와 관측성 시스템 구축을 통해 엔터프라이즈급 마이크로서비스 플랫폼의 핵심 요소들을 성공적으로 구현했으며, GitOps 원칙을 따르는 선언적 배포 관리를 실현했습니다.

---

**작성자**: 이동주

**작성일**: 2025년 11월 3일

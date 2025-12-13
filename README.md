# Cloud-Native 마이크로서비스 플랫폼 v2.0

**문서 버전**: 3.4 <br>
**최종 수정일**: 2025년 12월 14일

로컬 환경(Minikube)에서 운영되던 마이크로서비스 블로그 플랫폼을 클라우드 네이티브 아키텍처로 재구축한 프로젝트입니다. Terraform을 이용한 인프라 자동화, GitOps 기반의 CI/CD 파이프라인, 그리고 Istio 서비스 메시를 통한 관측성과 보안 강화를 목표로 합니다.

---

## 문서 변경 이력

| 문서 버전 | 날짜 | 주요 변경 내용 |
|----------|------|---------------|
| **1.0** | 2025-09-29 | 초안 작성 (AWS EKS 기반 아키텍처) |
| **2.0** | 2025-10-13 | CloudStack 기반 단국대 클라우드(Solid Cloud) 개발/테스트 후 AWS는 최종 배포하는 것으로 변경 |
| **3.0** | 2025-11-03 | 프로젝트 완료, Week 5 최종 상태 반영 (CI/CD, 모니터링, Istio 서비스 메시 구축 완료) |
| **3.1** | 2025-11-14 | README 개선 (대시보드 이미지를 상단으로 이동, Kiali 대시보드 추가, 모든 문서 링크 수정) |
| **3.2** | 2025-11-22 | k6 부하 테스트 통합 및 성능 테스트 문서화 (스크립트 개선, threshold 최적화) |
| **3.3** | 2025-12-08 | Phase 1+2 보안/성능 개선 적용 |
| **3.4** | 2025-12-14 | 카테고리 동적 관리 기능, 최신 성능 지표 반영, 문서 업데이트 |

---

## 프로젝트 배경

### v1.0의 한계
- 로컬 환경(Minikube)에서만 동작
- 수동으로 인프라를 구성하고 관리 (IaC 미적용)
- CI/CD 파이프라인이 없어 배포를 수동으로 진행
- 파일 기반 DB(SQLite) 사용으로 확장 불가능

### v2.0에서 개선한 점
- **Solid Cloud 기반 실제 클라우드 환경 구축**
- **Terraform으로 인프라를 코드로 관리 (IaC)**
- **GitHub Actions + Argo CD로 자동화된 배포 파이프라인**
- **PostgreSQL로 전환하여 데이터 정합성 및 확장성 확보**
- **Prometheus + Grafana + Loki로 시스템 모니터링 구축**
- **Istio를 통한 서비스 간 보안 통신(mTLS) 적용**

---

## 주요 기능

-   **Infrastructure as Code (IaC)**: Terraform을 사용하여 Kubernetes 클러스터 내 필수 리소스(네임스페이스, PostgreSQL 배포 등)를 코드로 관리합니다. 참고: 현재 terraform/modules의 네트워크 및 클러스터 모듈은 기본 구조를 보여주는 템플릿이며, 실제 클라우드 환경에 맞게 구체화가 필요합니다.
-   **GitOps CI/CD 파이프라인**: GitHub에 코드를 Push하면 자동으로 빌드, 테스트, 보안 스캔을 거쳐 Solid Cloud에 배포됩니다.
-   **마이크로서비스 아키텍처**: Go와 Python(FastAPI)을 활용한 폴리글랏 MSA 구조로 각 서비스를 독립적으로 개발하고 배포합니다.
-   **관측성 (Observability)**: Prometheus, Grafana, Loki를 도입하여 시스템의 메트릭과 로그를 실시간으로 모니터링합니다.
-   **서비스 메시**: Istio를 적용하여 서비스 간 통신을 자동으로 암호화하고 트래픽을 세밀하게 제어합니다.
-   **데이터 영속성**: PostgreSQL과 Redis를 사용하여 안정적인 데이터 저장과 빠른 캐싱을 지원합니다.
-   **성능 테스트**: k6를 활용한 자동화된 부하 테스트로 시스템 성능과 안정성을 검증합니다.
-   **Rate Limiting**: slowapi를 활용한 API 요청 제한으로 서비스 안정성을 보장합니다.
-   **카테고리 동적 관리**: CSS 변수 기반 동적 색상 시스템으로 카테고리별 고유 색상을 자동 할당합니다.

---

## 아키텍처

프로젝트의 전체 아키텍처, 서비스 간 통신 흐름, CI/CD 파이프라인, 마이크로서비스 구조 등 상세한 설계 내용은 다음 문서를 참고하세요:

**[전체 시스템 아키텍처 문서 보기](./docs/02-architecture/architecture.md)**

주요 내용:
- 전체 시스템 아키텍처 다이어그램 (CI/CD, Kubernetes 클러스터, 모니터링)
- 마이크로서비스 구조 및 각 서비스 설명
- 서비스 간 통신 흐름 (Sequence Diagram)
- 네트워크 및 보안 구조

---

## 시스템 현황 및 대시보드

### 블로그 서비스

![Blog Service](https://raw.githubusercontent.com/DvwN-Lee/Monitoring-v2/main/docs/04-operations/screenshots/blog-service.png)

FastAPI 기반의 블로그 애플리케이션으로, 게시글 CRUD 기능과 웹 UI를 제공합니다.

### Grafana Golden Signals 대시보드

![Grafana Golden Signals](https://raw.githubusercontent.com/DvwN-Lee/Monitoring-v2/main/docs/04-operations/screenshots/grafana-golden-signals.png)

**주요 지표**:
- **Latency**: P95/P99 응답 시간 추적
- **Traffic**: 초당 요청 수 (req/s) 모니터링
- **Errors**: 에러율 추적
- **Saturation**: CPU 리소스 사용률 모니터링

### Prometheus 메트릭 수집

![Prometheus](https://raw.githubusercontent.com/DvwN-Lee/Monitoring-v2/main/docs/04-operations/screenshots/prometheus-metrics.png)

Prometheus로 모든 서비스의 메트릭을 수집하고 쿼리할 수 있습니다.

### Loki 중앙 로깅

![Loki Logs](https://raw.githubusercontent.com/DvwN-Lee/Monitoring-v2/main/docs/04-operations/screenshots/loki-logs.png)

Loki를 통해 모든 서비스의 로그를 한곳에서 조회하고 검색할 수 있습니다.

### Kiali Service Mesh 시각화

![Kiali Service Graph](https://raw.githubusercontent.com/DvwN-Lee/Monitoring-v2/main/docs/04-operations/screenshots/kiali-service-graph.png)

Kiali를 통해 Istio 서비스 메시의 트래픽 흐름과 서비스 간 의존성을 시각화하고, mTLS 상태를 확인할 수 있습니다.

---

## 시작하기

### 빠른 시작 가이드

프로젝트를 처음 시작하는 경우, 아래 가이드 문서를 먼저 읽어보세요:

**[Getting Started - 로컬 환경에서 시작하기](./docs/00-getting-started/GETTING_STARTED.md)**

이 가이드는 필수 도구 설치부터 로컬 환경에서 전체 시스템을 실행하는 과정까지 단계별로 안내합니다.

---

### 배포 옵션

이 프로젝트는 **로컬 개발 환경**과 **Solid Cloud 프로덕션 환경** 두 가지 방식으로 실행할 수 있습니다.

### 옵션 1: 로컬 개발 환경 (Minikube + Skaffold)

빠른 개발 및 테스트를 위한 로컬 쿠버네티스 환경입니다.

**요구사항:** `Minikube`, `Skaffold`, `kubectl`

```bash
# 1. Minikube 클러스터 시작
minikube start

# 2. Skaffold 개발 모드 실행
skaffold dev

# 3. 서비스 접속
kubectl port-forward svc/api-gateway 8000:8000
```

---

### 옵션 2: Solid Cloud 프로덕션 환경

실제 클라우드 환경에서 Terraform으로 인프라를 생성하고 GitOps 방식으로 배포합니다.

**요구사항:** `Terraform`, `kubectl`, Solid Cloud 접근 권한 (Token 기반 인증)

```bash
# 1. Kubernetes 인증 설정 (Token 기반)
# .env.k8s 파일 생성
cp .env.k8s.example .env.k8s

# .env.k8s 파일 편집 (API Server, Token, CA Cert 입력)
# - K8S_API_SERVER: Kubernetes API 서버 URL
# - K8S_TOKEN: Service Account Token
# - K8S_CA_CERT: CA Certificate (Base64 인코딩)

# 2. Solid Cloud 환경으로 전환
./scripts/switch-to-cloud.sh

# 3. Terraform으로 인프라 생성
cd terraform/environments/solid-cloud
terraform init
terraform apply

# 4. 애플리케이션 배포
cd ../../..
kubectl apply -k k8s-manifests/overlays/solid-cloud

# 5. 배포 상태 확인
kubectl get pods -n titanium-prod
kubectl get svc -n titanium-prod
```

**Token 발급 방법:**

```bash
# Service Account 생성 (기존 클러스터 접근 가능한 경우)
kubectl create serviceaccount monitoring-sa -n default
kubectl create clusterrolebinding monitoring-sa-admin \
  --clusterrole=cluster-admin \
  --serviceaccount=default:monitoring-sa

# Token 발급 (Kubernetes 1.24+)
kubectl create token monitoring-sa --duration=87600h

# CA Certificate 가져오기
kubectl config view --raw -o jsonpath='{.clusters[0].cluster.certificate-authority-data}'
```

---

## 문서 구조 및 가이드

이 프로젝트는 학습 및 개발 과정을 체계적으로 보여주기 위해 상세한 문서를 포함하고 있습니다.

**전체 문서 구조와 내용을 파악하려면 아래 가이드 문서를 먼저 읽어보시는 것을 강력히 추천합니다.**

- **[문서 탐색 가이드](./docs/README.md)**: 전체 문서 구조, 추천 탐색 순서, 각 문서의 역할을 안내합니다.

### 핵심 문서 바로가기

- **[시스템 아키텍처](./docs/02-architecture/architecture.md)**: 전체 시스템의 상세 설계 문서
  - 전체 시스템 아키텍처 (Mermaid 다이어그램)
  - 서비스 간 통신 흐름 (Sequence Diagram)
  - CI/CD 파이프라인 상세 설계
  - 네트워크 구조 및 보안 설계
- **[운영 가이드](./docs/04-operations/guides/operations-guide.md)**: 시스템 운영, 모니터링, 장애 대응 Runbook
- **[프로젝트 회고](./docs/08-retrospective/project-retrospective.md)**: 프로젝트 성과 및 회고
- **[기술 결정 기록 (ADR)](./docs/02-architecture/adr/)**: 주요 기술 선택의 배경과 근거

---

## 기술 스택

| 구분                | 기술                                                                                              |
| ------------------- | ------------------------------------------------------------------------------------------------- |
| **Cloud**           | `Solid Cloud (CloudStack 기반)`, `Kubernetes`                                                           |
| **IaC**             | `Terraform`                                                                                       |
| **CI/CD**           | `GitHub Actions`, `Argo CD`                                                                       |
| **Container**       | `Docker`, `Kustomize`                                                                             |
| **Service Mesh**    | `Istio`                                                                                           |
| **Monitoring**      | `Prometheus`, `Grafana`, `Loki`                                                                   |
| **Performance**     | `k6`                                                                                              |
| **Backend**         | `Go`, `Python`, `FastAPI`                                                                         |
| **Database/Cache**  | `PostgreSQL`, `Redis`                                                                             |
| **Libraries**       | `asyncpg`, `slowapi`, `alembic`, `sqlalchemy`, `aiohttp`                                          |
| **Local Dev**       | `Minikube`, `Skaffold`                                                                            |

**각 기술을 선택한 이유는 [ADR 문서](./docs/02-architecture/adr/)를 참고하세요.**

---

## 개발 계획 및 목표

### 개발 기간
- **프로젝트 기간**: 2025년 9월 30일 ~ 11월 15일
- **개발/테스트 환경**: Solid Cloud (CloudStack 기반)
- **프로젝트 상태**: 완료 (Must-Have 100%, Should-Have 100%)

### 성능 목표 및 달성 현황

**K6 부하 테스트 기준 (100 VU, 10분)**:
- **P95 Latency**: 74.76ms (목표 500ms 대비 85% 개선)
- **P90 Latency**: 55.67ms
- **Error Rate**: 0.01%
- **Check Success Rate**: 99.95%

**시스템 안정성**:
- **HTTP 실패율**: 0% (목표 달성)
- **보안**: Trivy 스캔 자동화, mTLS STRICT 모드, Rate Limiting 적용 (목표 달성)
- **배포 시간**: Git Push 후 5분 이내 자동 배포 (목표 달성)
- **고가용성**: 주요 서비스 2+ replicas 유지 (목표 달성)

---

## 프로젝트 진행 상황

### Week 1 완료 (9/30 ~ 10/6): 인프라 기반 구축
- [x] 로컬 개발 환경 구축 (Minikube + Skaffold)
- [x] 마이크로서비스 기본 구조 설계
- [x] Solid Cloud 인프라 구축 (Terraform)
- [x] PostgreSQL 적용 및 데이터 마이그레이션 완료
- [x] Kustomize Overlays 분리 (local vs solid-cloud)
- [x] 환경 전환 및 배포 스크립트 작성
- [x] 통합 테스트 스크립트 작성

### Week 2 완료 (10/7 ~ 10/13): CI/CD 파이프라인 구축
- [x] GitHub Actions CI 워크플로우 작성 (빌드, 테스트, Trivy 스캔)
- [x] Docker 이미지 자동 빌드 및 Push
- [x] GitOps 저장소 구성 (Kustomize 기반)
- [x] Argo CD 설치 및 Application 설정
- [x] 자동 동기화 정책 설정
- [x] Git Push → 자동 배포 전체 플로우 검증

### Week 3 완료 (10/14 ~ 10/20): 관측성 시스템 구축
- [x] Prometheus Operator 설치
- [x] Grafana 설치 및 Prometheus 연동
- [x] ServiceMonitor 설정 (애플리케이션 메트릭 수집)
- [x] Golden Signals 대시보드 구성 (Latency, Traffic, Errors, Saturation)
- [x] Loki 및 Promtail 설치 (중앙 로깅)
- [x] Grafana에서 로그 조회 및 검색 구현
- [x] AlertManager 설정

### Week 4 완료 (10/21 ~ 10/27): Should-Have 기능 구현
- [x] Istio 1.20.1 설치
- [x] 서비스에 Sidecar 자동 주입 설정
- [x] mTLS STRICT 모드 활성화
- [x] Istio 메트릭 수집 (ServiceMonitor/PodMonitor)
- [x] Kiali 외부 서비스 연동
- [x] VirtualService 및 DestinationRule 설정
- [x] Rate Limiting 구현

### Week 5 완료 (10/28 ~ 11/3): 테스트 및 문서화
- [x] k6 부하 테스트 수행 및 성능 분석
- [x] HPA 최적화 (minReplicas 2로 증가)
- [x] 보안 검증 (Trivy, mTLS, NetworkPolicy, RBAC)
- [x] ADR 5건 작성
- [x] Week 5 최종 상태 보고서 작성
- [x] README 최종 업데이트
- [x] 운영 가이드 작성
- [x] 프로젝트 회고 작성
- [x] 장애 복구 시나리오 테스트
- [x] 데모 준비

### Phase 1+2 완료 (2025-12): 보안 및 성능 최적화
- [x] Rate Limiting 적용 (slowapi) - API 분당 100 요청 제한
- [x] CORS Middleware 추가
- [x] ClientSession Singleton Pattern 적용 - Connection Pool 재사용
- [x] Redis Cache TTL 최적화 (사용자: 5분, 블로그: 1분, 카테고리: 1시간)
- [x] Database Secret Kubernetes Secret 전환
- [x] 카테고리 동적 관리 기능 구현 - 랜덤 색상 자동 할당
- [x] LEFT JOIN -> INNER JOIN DB 최적화 - 데이터 무결성 강화

---

## 주요 성과

### 완료된 핵심 기능
- **Must-Have 요구사항**: 100% 완료
  - Terraform 인프라 자동화
  - CI/CD 파이프라인 (GitHub Actions + Argo CD)
  - Prometheus + Grafana 모니터링
  - PostgreSQL 데이터 영속성

- **Should-Have 요구사항**: 100% 완료
  - Loki 중앙 로깅 시스템
  - Istio mTLS STRICT 모드
  - ADR 5건 작성 (목표 3건 초과 달성)

- **Could-Have 요구사항**: 67% 완료
  - Rate Limiting 구현
  - HPA 자동 확장

### 시스템 현황
- **실행 중인 서비스**: 14개 Pod (모든 주요 서비스 2+ replicas)
- **부하 테스트 성능 (K6 100 VU, 10분)**:
  - P95: 74.76ms, P90: 55.67ms
  - Error Rate: 0.01%, Check Success: 99.95%
- **보안**: mTLS STRICT, Trivy 자동 스캔, Rate Limiting, NetworkPolicy 적용
- **CI/CD**: Git Push → 5분 이내 자동 배포

### 접속 정보
- **Grafana 대시보드**: http://10.0.11.168:30300
- **Kiali 서비스 메시**: http://10.0.11.168:30164
- **Prometheus**: http://10.0.11.168:30090
- **애플리케이션**: http://10.0.11.168:31304

---

## 프로젝트 문서

상세한 기술 문서 및 가이드는 다음을 참고하세요:

-   **[요구사항 명세서](./docs/01-planning/requirements.md)**: 프로젝트에서 구현할 기능과 목표
-   **[시스템 설계서](./docs/02-architecture/architecture.md)**: 시스템 아키텍처와 구조
-   **[프로젝트 계획서](./docs/01-planning/project-plan.md)**: 개발 일정과 마일스톤
-   **[기술 결정 기록 (ADR)](./docs/02-architecture/adr/)**: 주요 기술 선택의 이유와 배경
-   **[Secret 관리 가이드](./docs/04-operations/guides/SECRET_MANAGEMENT.md)**: 보안 비밀 정보 관리 방법
-   **[Week 5 최종 상태 보고서](./docs/04-operations/reports/final-status-report.md)**: 프로젝트 완료 상태
-   **[k6 부하 테스트 결과 분석](./docs/06-performance/k6-load-test-results.md)**: 부하 테스트 및 최적화 결과
-   **[k6 부하 테스트 가이드](./tests/performance/README.md)**: k6 성능 테스트 실행 방법
-   **[k6 테스트 결과 보고서](./docs/06-performance/k6-load-test-results.md)**: 부하 테스트 결과 및 성능 지표
-   **[Istio 트러블슈팅 가이드](./docs/05-troubleshooting/istio/)**: Istio 서비스 메시 문제 해결

---

## 참고 사항
- 이 프로젝트는 CloudStack 기반 Solid Cloud 환경에서 개발 및 운영되었습니다.
- 모든 핵심 요구사항이 완료되어 실제 운영 가능한 상태입니다.
- 추가 개선 사항은 프로젝트 문서를 참고하세요.

## 보안 주의사항

- Secret(비밀번호, API 키 등)은 Git 저장소에 커밋하지 마세요
- 프로덕션 환경에서는 External Secrets Operator 또는 클라우드 네이티브 Secret 관리 솔루션 사용을 권장합니다
- 자세한 내용은 [Secret 관리 가이드](./docs/04-operations/guides/SECRET_MANAGEMENT.md)를 참고하세요

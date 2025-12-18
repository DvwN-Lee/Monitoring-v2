# 프로젝트 회고

**작성일**: 2025-12-14
**프로젝트 기간**: 2025년 9월 30일 ~ 12월 14일

---

## 1. 프로젝트 개요

Cloud-Native 마이크로서비스 플랫폼 v2.0은 로컬 환경(Minikube)에서 운영되던 블로그 플랫폼을 Solid Cloud 기반 클라우드 네이티브 아키텍처로 재구축한 프로젝트입니다.

### 목표
- Terraform을 이용한 Infrastructure as Code 구현
- GitOps 기반 CI/CD Pipeline 구축
- Istio Service Mesh 적용 (mTLS STRICT)
- Prometheus + Grafana + Loki 관측성 시스템 구축
- 성능 최적화 및 보안 강화

---

## 2. 잘한 점 (What Went Well)

### 2.1 체계적인 문서화

- **ADR 10건 작성**: 주요 기술 결정 과정을 문서화하여 의사결정 근거를 명확히 기록
- **Troubleshooting 가이드 30건+**: 실제 발생한 문제와 해결 방법을 카테고리별로 체계적으로 정리
- **단계별 문서 구조**: 계획(01-planning) → 설계(02-architecture) → 구현(03-implementation) → 운영(04-operations)으로 프로젝트 진행 과정을 시간순으로 기록

### 2.2 GitOps 기반 자동화 Pipeline

- **GitHub Actions + Argo CD**: Git Push 후 5분 이내 자동 배포 달성
- **보안 스캔 자동화**: Trivy를 활용한 Docker Image 취약점 스캔
- **Image Tagging 자동화**: `main-<short_sha>` 형식으로 자동 태깅 및 Kustomize 업데이트

### 2.3 Istio Service Mesh 적용

- **mTLS STRICT 모드**: 서비스 간 통신 암호화로 보안 강화
- **Kiali 시각화**: 서비스 메시 트래픽 흐름 및 의존성 모니터링
- **Golden Signals Dashboard**: Latency, Traffic, Errors, Saturation 지표 통합 모니터링

### 2.4 성능 최적화 (Phase 1+2)

- **P95 Latency 개선**: 74.76ms 달성 (K6 100 VU 부하 테스트)
- **ClientSession Singleton Pattern**: Connection Pool 재사용으로 TCP Handshake Overhead 90% 감소
- **Redis Cache 최적화**: Cache Hit 시 응답 시간 90% 감소

---

## 3. 아쉬운 점 (What Could Be Improved)

### 3.1 초기 성능 베이스라인 부재

- Phase 1+2 적용 전 성능 데이터를 측정하지 않아 정확한 개선율 비교 어려움
- 향후 프로젝트에서는 프로젝트 초기 단계부터 성능 베이스라인 설정 필요

### 3.2 External Secrets Operator 미도입

- Database 비밀번호, API Key 등을 Kubernetes Secret으로 관리하고 있으나, Git 저장소에는 `.env.k8s.example` 형태로 관리
- External Secrets Operator 또는 Vault 도입 시 보안성 더욱 강화 가능

### 3.3 Distributed Tracing 미구축

- Prometheus, Grafana, Loki를 통한 메트릭 및 로그 수집은 완료
- Jaeger 또는 Tempo를 활용한 Distributed Tracing 미도입으로 서비스 간 요청 추적 어려움

### 3.4 카테고리 동적 관리 색상 충돌 가능성

- 랜덤 색상 할당 방식으로 인해 동일 색상이 중복 할당될 가능성 존재
- 색상 중복 검증 로직 추가 필요

---

## 4. 배운 점 (Lessons Learned)

### 4.1 Kubernetes 운영 경험

- **Pod Lifecycle 관리**: Liveness/Readiness Probe 설정의 중요성
- **Resource Limits**: CPU/Memory Limits 미설정 시 Node 리소스 고갈 위험
- **HPA 설정**: minReplicas 1 -> 2로 증가하여 고가용성 확보

### 4.2 Service Mesh 아키텍처 이해

- **mTLS 통신**: Istio Sidecar를 통한 자동 암호화 및 인증
- **Traffic Management**: VirtualService, DestinationRule을 통한 세밀한 트래픽 제어
- **Observability**: Kiali, Prometheus를 통한 서비스 메시 가시성 확보

### 4.3 관측성(Observability)의 중요성

- **Golden Signals**: Latency, Traffic, Errors, Saturation 지표를 중심으로 모니터링
- **중앙 로깅**: Loki를 통해 모든 서비스 로그를 한곳에서 조회
- **Alert 설정**: Prometheus Alert Rule을 통한 장애 사전 감지

### 4.4 성능 최적화 기법

- **Connection Pooling**: ClientSession Singleton Pattern으로 Connection 재사용
- **Cache 전략**: TTL 기반 Redis Cache로 Database 부하 감소
- **Query 최적화**: LEFT JOIN -> INNER JOIN 변경으로 데이터 무결성 강화

---

## 5. 향후 계획

### 5.1 보안 강화

- **OAuth 2.0 인증**: 현재 JWT 기반 인증을 OAuth 2.0으로 업그레이드
- **External Secrets Operator**: Kubernetes Secret 관리 자동화
- **Network Policy 강화**: Namespace 간 트래픽 제한 정책 세밀화

### 5.2 성능 개선

- **CDN 적용**: 정적 리소스(이미지, CSS, JS)를 CDN으로 제공하여 Origin Server 부하 감소
- **Database Connection Pool**: asyncpg Connection Pool 크기 최적화 (min_size, max_size)
- **Query 최적화**: N+1 쿼리 문제 해결, Index 추가

### 5.3 관측성 확장

- **Distributed Tracing**: Jaeger 또는 Tempo 도입하여 서비스 간 요청 추적
- **SLO/SLI 정의**: 서비스 수준 목표(SLO) 및 지표(SLI) 명확히 정의
- **Custom Metrics**: 비즈니스 로직 관련 커스텀 메트릭 수집 (예: 게시글 작성 수, 사용자 활동)

### 5.4 기능 확장

- **댓글 기능**: 블로그 게시글에 댓글 작성/삭제 기능 추가
- **검색 기능**: Elasticsearch를 활용한 전문 검색 기능
- **이미지 업로드**: S3 호환 Object Storage 연동

---

## 6. 성과 요약 (정량적 지표)

### 6.1 요구사항 달성도

| 구분 | 달성률 |
|------|--------|
| Must-Have | 100% |
| Should-Have | 100% |
| Could-Have | 67% |

### 6.2 성능 지표

| 메트릭 | 값 |
|--------|-----|
| **P95 Latency** | 74.76ms (K6 100 VU, 10분) |
| **P90 Latency** | 55.67ms |
| **Error Rate** | 0.01% |
| **Check Success Rate** | 99.95% |
| **배포 시간** | Git Push 후 5분 이내 |

### 6.3 시스템 안정성

- **5xx 에러율**: 0%
- **4xx 에러율**: 0%
- **Uptime**: 99.9% (HPA 기반 자동 복구)
- **보안**: mTLS STRICT, Trivy 자동 스캔, Rate Limiting 적용

### 6.4 문서화

- **ADR**: 10건
- **Troubleshooting 가이드**: 30건+
- **README**: 357줄 (v3.4)
- **전체 문서**: 60개+ 파일

---

## 7. 결론

Cloud-Native 마이크로서비스 플랫폼 v2.0 프로젝트는 Terraform IaC, GitOps CI/CD, Istio Service Mesh, Prometheus/Grafana 관측성을 성공적으로 구축한 프로젝트입니다.

특히 보안/성능 개선을 통해 P95 Latency 74.76ms, Error Rate 0.01%를 달성하여 프로덕션 수준의 성능과 안정성을 확보했습니다.

체계적인 문서화와 트러블슈팅 가이드 작성을 통해 프로젝트 진행 과정과 의사결정 근거를 명확히 기록했으며, 이는 향후 유지보수 및 확장에 큰 도움이 될 것입니다.

아쉬운 점으로는 초기 성능 베이스라인 부재, External Secrets Operator 미도입, Distributed Tracing 미구축 등이 있으나, 이는 향후 개선 과제로 남겨두었습니다.

이 프로젝트를 통해 Kubernetes 운영, Service Mesh 아키텍처, 관측성 시스템 구축, 성능 최적화 등 클라우드 네이티브 기술 스택에 대한 실전 경험을 쌓을 수 있었습니다.

---

**작성자**: Dongju Lee
**GitHub**: https://github.com/DvwN-Lee/Monitoring-v2

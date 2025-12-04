# 기술 결정 기록 (Architecture Decision Records)

이 디렉토리에는 "Cloud-Native 마이크로서비스 플랫폼" 프로젝트의 중요한 아키텍처 결정을 기록한 문서들이 포함되어 있습니다.

## ADR 목록

### CI/CD 및 자동화
- **[ADR-001: GitOps CD 도구로 Argo CD 채택](./001-argocd-vs-flux.md)** (2025-09-30)
- **[ADR-004: CI 도구로 GitHub Actions 채택](./004-github-actions-vs-jenkins.md)** (2025-09-30)
- **[ADR-005: IaC 도구로 Terraform 채택](./005-terraform-vs-pulumi.md)** (2025-10-01)

### 데이터 및 캐시
- **[ADR-002: 데이터베이스로 PostgreSQL 채택](./002-postgresql-vs-sqlite.md)** (2025-09-30)
- **[ADR-008: 캐시 솔루션으로 Redis 채택](./008-redis-cache.md)** (2025-10-01)

### 모니터링 및 관측성
- **[ADR-003: 중앙 로깅 시스템으로 Loki Stack 채택](./003-loki-vs-efk.md)** (2025-09-30)
- **[ADR-007: Monitoring Stack으로 Prometheus + Grafana 채택](./007-prometheus-grafana-stack.md)** (2025-10-01)

### 네트워크 및 인프라
- **[ADR-006: Service Mesh로 Istio 채택](./006-istio-vs-linkerd.md)** (2025-10-01)
- **[ADR-009: Kubernetes 플랫폼으로 Solid Cloud 채택](./009-solid-cloud-platform.md)** (2025-10-01)

### 보안 및 성능
- **[ADR-010: Phase 1+2 보안 및 성능 개선](./010-phase1-phase2-improvements.md)** (2025-12-04)

---

모든 ADR은 [ADR 템플릿](./template.md)을 기반으로 작성되었습니다.
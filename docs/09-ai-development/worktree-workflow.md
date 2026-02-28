# Worktree 기반 AI 협업 프로세스

**작성일**: 2026-02-28
**문서 경로**: `docs/09-ai-development/worktree-workflow.md`

---

## 개요

본 문서는 Git Worktree를 활용하여 AI Agent와의 작업을 격리하고, 안전한 협업 환경을 구성한 과정을 기록합니다.

각 기능 개발 및 문서 작업은 독립된 Worktree 환경에서 진행되었으며, 작업 완료 후 PR 생성 및 merge를 거쳐 Worktree는 정리되었습니다. 현재 저장소에 Worktree 아티팩트가 남아있지 않으나, PR 히스토리가 격리 작업의 간접 증거로 기능합니다.

---

## Worktree 전략 개요

### Git Worktree란

Git Worktree는 단일 Git 저장소에서 여러 작업 디렉토리(working tree)를 동시에 생성하고 유지할 수 있는 기능입니다.

- 동일한 `.git` 데이터베이스를 공유하면서 서로 다른 브랜치를 각각의 독립 디렉토리에서 체크아웃합니다.
- 브랜치 간 전환(switch) 없이 여러 브랜치 작업을 병렬로 진행할 수 있습니다.
- 실험적 변경 사항이 메인 브랜치에 영향을 주지 않습니다.

### 왜 Worktree를 사용하였는가

| 목적 | 설명 |
|---|---|
| AI Agent 작업 격리 | AI Agent가 수정하는 파일이 `main` 브랜치에 직접 영향을 미치지 않도록 격리 |
| 병렬 개발 | 여러 기능/문서 작업을 동시에 진행하며 컨텍스트 전환 비용 최소화 |
| 안전한 실험 | 파이프라인, Istio, 모니터링 등 시스템 변경 작업을 안전하게 시도 |
| 리뷰 기반 통합 | Worktree에서 완성된 결과물을 PR을 통해 검토 후 `main`에 통합 |

---

## 워크플로우 설명

### 실제 작업 흐름

아래는 각 기능 개발 시 반복된 표준 워크플로우입니다.

```
1. 작업 브랜치 생성
   git branch feature/new-feature

2. Worktree 생성 및 격리된 디렉토리에서 작업
   git worktree add ../worktree-new-feature feature/new-feature

3. AI Agent가 격리된 디렉토리 내에서 작업 수행
   - 코드 작성, 파일 수정, 테스트 등

4. PR 생성
   gh pr create --base main --head feature/new-feature

5. 코드 리뷰 및 CI 통과 확인

6. main 브랜치에 merge

7. Worktree 정리
   git worktree remove ../worktree-new-feature
   git branch -d feature/new-feature
```

### Worktree 정리에 관하여

Worktree는 해당 브랜치가 `main`에 merge된 후 `git worktree remove` 명령으로 정리하는 것이 일반적인 관례입니다.

**현재 저장소에 Worktree가 남아있지 않은 이유**: 모든 작업 완료 후 정상적으로 정리가 이루어졌기 때문입니다.

```bash
# 현재 상태 확인 결과
$ git worktree list
/Users/idongju/Desktop/Git/Monitoring-v2  3b37dda [main]
# -> 메인 worktree만 존재, 추가 worktree 없음 (정리 완료)
```

Worktree를 활용하여 개발하였으며, 각 작업 완료 후 정리되었습니다. PR 히스토리가 격리 작업의 간접 증거입니다.

---

## PR 히스토리 (간접 증거)

PR 총 27건이 생성되었으며, MERGED 23건, CLOSED 4건입니다.
GitHub에서 Issue와 PR은 번호를 공유하므로, 최고 번호(#61)가 곧 PR 총수를 의미하지 않습니다.

각 PR이 독립된 브랜치(feature/, docs/, fix/, bugfix/, test/ 등)에서 진행되었다는 사실은, 각 작업이 격리된 환경에서 이루어졌음을 간접적으로 증명합니다.

### 브랜치 유형별 대표 PR 목록

#### feature/ - 기능 개발

| PR | 브랜치 | 제목 | 상태 |
|---|---|---|---|
| #34 | `feature/infra-foundation` | Week 1: 클라우드 인프라 기반 구축 | MERGED |
| #35 | `feature/ci-cd-pipeline` | feat: CI/CD 파이프라인 구축 및 GitOps 설정 | MERGED |
| #45 | `feature/monitoring-setup` | feat: Prometheus & Grafana 모니터링 시스템 구축 | MERGED |
| #46 | `feature/grafana-dashboards` | feat: Grafana 대시보드 & Loki 로깅 시스템 구축 | MERGED |
| #53 | `feature/istio-setup` | [EPIC] Week 4: 서비스 메시 & 고급 기능 구현 완료 | MERGED |
| #56 | `feature/blog-categories` | feat: 블로그 서비스 카테고리 기능 추가 (백엔드) | MERGED |

#### docs/ - 문서 작업

| PR | 브랜치 | 제목 | 상태 |
|---|---|---|---|
| #54 | `docs/restructure` | docs: 문서 구조 개선 | MERGED |
| #55 | `docs/improve-architecture-diagrams` | docs: 아키텍처 문서 Mermaid 다이어그램으로 개선 | MERGED |
| #59 | `docs/validation-and-monitoring-screenshots` | docs: 문서 검증 결과 반영 및 모니터링 대시보드 스크린샷 추가 | MERGED |
| #61 | `docs/improve-consistency` | docs: 전체 문서 정합도 수정 | MERGED |

#### fix/ / bugfix/ - 버그 수정

| PR | 브랜치 | 제목 | 상태 |
|---|---|---|---|
| #36 | `bugfix/ci-cd-issues` | fix: CI/CD 파이프라인 및 대시보드 연결 문제 해결 | MERGED |
| #37 | `bugfix/ci-cd-issues` | fix: 대시보드 nginx 프록시 설정 추가로 API 및 Blog 서비스 연결 | MERGED |
| #47 | `bugfix/dashboard-metrics` | feat: Grafana 대시보드 메트릭 및 API Gateway 계측 수정 | MERGED |
| #48 | `fix/improve-histogram-buckets` | fix: Python 서비스들의 Prometheus 히스토그램 버킷 개선 | MERGED |
| #57 | `bugfix/post-loading-issue` | fix: 게시물 로딩 실패 수정 - 프론트엔드 API 경로 업데이트 | MERGED |
| #58 | `bugfix/istio-service-routing-fix` | fix: Istio 서비스 메시 환경에서 api-gateway 라우팅 문제 해결 | CLOSED |

#### test/ - 테스트 시나리오

| PR | 브랜치 | 제목 | 상태 |
|---|---|---|---|
| #38 | `feature/e2e-test` | test: E2E 테스트 - user-service v1.1.1 | MERGED |
| #39 | `test/fail-build-test` | test: 실패 시나리오 #1 - Docker 빌드 실패 | CLOSED |
| #40 | `test/fail-security-scan` | test: 실패 시나리오 #2 - 보안 스캔 실패 | CLOSED |
| #41 | `test/fail-invalid-manifest` | test: 실패 시나리오 #3 - 잘못된 매니페스트 | CLOSED |
| #42 | `test/rollback-scenario` | [TEST] 롤백 시나리오 테스트 - user-service v1.1.2 | MERGED |

#### rollback/ - 롤백

| PR | 브랜치 | 제목 | 상태 |
|---|---|---|---|
| #43 | `rollback/revert-v1.1.2` | [ROLLBACK] Git revert를 통한 v1.1.1 롤백 | MERGED |

### PR 통계 요약

| 구분 | 건수 |
|---|---|
| 전체 PR | 27건 |
| MERGED | 23건 |
| CLOSED (미merge) | 4건 |

---

## AI Agent와 Worktree 결합의 이점

### 작업 격리로 인한 안전성 확보

AI Agent가 코드를 생성하거나 파일을 수정할 때, 해당 변경 사항은 격리된 Worktree 내에서만 적용됩니다. AI의 판단 오류나 예기치 않은 수정이 발생하더라도, `main` 브랜치는 영향을 받지 않습니다. 모든 변경 사항은 PR 리뷰 단계를 통과한 후에만 `main`에 통합됩니다.

### 병렬 작업 가능

여러 Worktree를 동시에 운용하면, 서로 다른 기능 개발과 문서 작업을 병렬로 진행할 수 있습니다. 브랜치 전환 없이 각 디렉토리에서 독립적으로 작업하므로, 컨텍스트 전환에 따른 오류 가능성이 낮습니다.

### 실험적 변경의 안전한 수행

Istio 설정, Prometheus 메트릭 튜닝, CI/CD 파이프라인 변경과 같이 시스템 전반에 영향을 미칠 수 있는 작업도, Worktree로 격리된 환경에서 안전하게 시도할 수 있습니다.

---

## 관련 문서

- [AI Agent 설계 및 역할 분리](./agent-design.md)
- [Scrum 리뷰 기록](./scrum-reviews/)


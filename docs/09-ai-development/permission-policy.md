# AI Agent CLI 권한 정책 설계 문서

**작성일**: 2026-02-28

---

## 개요

이 문서는 Monitoring-v2 프로젝트에서 Claude Code AI Agent가 실행할 수 있는 CLI 명령을 allowlist 방식으로 명시적으로 관리한 과정을 기술합니다.

Claude Code는 `.claude/settings.local.json` 파일의 `permissions` 필드를 통해 Agent가 자율적으로 실행 가능한 Bash 명령과 MCP 도구를 제어합니다. 이 프로젝트에서는 deny(거부) 목록 없이 allow(허용) 목록만을 운용하는 allowlist 기반 방식을 채택하였으며, 총 153개 항목이 등록되어 있습니다.

---

## 권한 정책 설계 배경

### AI Agent 실행 범위 관리의 필요성

Claude Code AI Agent는 사용자의 명시적인 승인 없이도 터미널 명령을 실행할 수 있습니다. Monitoring-v2 프로젝트는 Kubernetes 클러스터, Terraform 인프라, GitHub Actions, 원격 서버 접속 등 광범위한 운영 작업을 포함합니다. Agent가 임의의 명령을 실행하는 상황을 방지하고, 어떤 명령이 허용되는지를 명확히 기록하기 위해 권한 목록 관리가 필요했습니다.

특히 아래와 같은 상황에서 명시적인 허용 목록 관리의 필요성이 확인되었습니다.

- 인프라 변경 명령(`terraform apply`, `kubectl delete`) 실행 시 사전 파악 필요
- 복수의 Kubernetes 클러스터(solid-cloud, gcp) 접근 혼용 시 컨텍스트 혼동 방지
- 프로젝트 진행 과정에서 새 도구 추가 시 기록을 남기는 수단으로 활용

### Claude Code의 permissions 구조

Claude Code의 `settings.local.json`은 `permissions` 객체 아래 세 개의 배열을 지원합니다.

| 필드 | 역할 | 이 프로젝트의 설정 |
|------|------|------------------|
| `allow` | 사용자 승인 없이 Agent가 자율 실행 가능한 명령 목록 | 153개 항목 |
| `deny` | Agent가 절대 실행할 수 없는 명령 목록 | 0개 (사용 안 함) |
| `ask` | 실행 전 사용자 확인을 요구하는 명령 목록 | 0개 (사용 안 함) |

이 설정에서는 허용 목록에 없는 명령은 Claude Code가 실행 전 사용자에게 승인을 요청합니다. deny와 ask 목록은 별도로 운용하지 않으며, 필요한 명령을 allow 목록에 추가하는 방식으로 관리합니다.

---

## allowlist 기반 권한 관리

### 실제 설정 구조

`.claude/settings.local.json`의 `permissions.allow` 배열에 153개 항목이 등록되어 있습니다. 각 항목은 다음 두 가지 형식을 따릅니다.

- `Bash(<명령어 패턴>)`: 허용할 Bash 명령과 인자 패턴
- `mcp__<서버>__<도구명>`: 허용할 MCP 서버 도구

와일드카드(`*`)는 해당 명령어 이후의 인자를 모두 허용함을 의미합니다. 예를 들어 `Bash(terraform destroy:*)` 는 `terraform destroy` 에 어떤 인자가 붙더라도 허용합니다.

### 도구별 허용 명령 분류

#### Kubernetes (kubectl)

두 개의 KUBECONFIG 파일을 환경 변수로 명시하여 클러스터별로 허용 목록을 분리 관리합니다.

| 클러스터 | 허용 명령 | 분류 |
|---------|---------|------|
| `config-solid-cloud` | `kubectl get:*` | 읽기 |
| `config-solid-cloud` | `kubectl describe:*` | 읽기 |
| `config-solid-cloud` | `kubectl logs:*` | 읽기 |
| `config-solid-cloud` | `kubectl wait:*` | 읽기/대기 |
| `config-solid-cloud` | `kubectl cluster-info:*` | 읽기 |
| `config-solid-cloud` | `kubectl exec:*` | 실행 |
| `config-solid-cloud` | `kubectl apply:*` | 쓰기 |
| `config-solid-cloud` | `kubectl patch:*` | 쓰기 |
| `config-solid-cloud` | `kubectl delete:*` | 삭제 |
| `config-solid-cloud` | `kubectl rollout status:*` | 상태 확인 |
| `config-gcp` | `kubectl get:*`, `kubectl get nodes:*` | 읽기 |
| `config-gcp` | `kubectl describe:*` | 읽기 |
| `config-gcp` | `kubectl logs:*` | 읽기 |
| `config-gcp` | `kubectl wait:*` | 읽기/대기 |
| `config-gcp` | `kubectl exec:*` | 실행 |
| `config-gcp` | `kubectl patch:*` | 쓰기 |
| `config-gcp` | `kubectl annotate:*` | 쓰기 |
| `config-gcp` | `kubectl rollout:*` | 롤아웃 관리 |
| `config-gcp` | `kubectl:*` | 전체 와일드카드 허용 |

`config-gcp` 클러스터의 경우, 프로젝트 후반에 `kubectl:*` 형태로 전체 와일드카드가 추가되었습니다. 이는 새 서브커맨드를 사용할 때마다 개별 항목을 추가하는 번거로움을 줄이기 위한 선택이었습니다.

#### Terraform

인프라 프로비저닝 워크플로우 단계별로 허용 명령이 등록되어 있습니다.

| 명령 | 단계 |
|------|------|
| `terraform init:*` | 초기화 |
| `terraform validate:*` | 유효성 검사 |
| `terraform plan:*` | 변경 계획 확인 |
| `terraform apply:*` | 인프라 적용 |
| `terraform destroy:*` | 인프라 삭제 (와일드카드 전체 허용) |
| `terraform output:*` | 출력 값 조회 |
| `terraform state list:*` | 상태 목록 조회 |
| `terraform state show:*` | 상태 상세 조회 |
| `terraform state rm:*` | 상태 항목 제거 |
| `terraform import:*` | 기존 리소스 import |
| `terraform taint:*` | 리소스 강제 재생성 지정 |

`terraform destroy:*`는 와일드카드 허용 항목으로, 인프라 해제 작업 자동화를 위해 추가되었습니다.

#### Git 및 GitHub CLI

소스 코드 관리와 PR 워크플로우에 필요한 명령이 허용됩니다.

| 명령 | 용도 |
|------|------|
| `git add:*` | 변경 사항 스테이징 |
| `git commit:*` | 커밋 생성 |
| `git push:*` | 원격 브랜치 push |
| `git pull:*` | 원격 브랜치 pull |
| `git fetch:*` | 원격 브랜치 fetch |
| `git checkout:*` | 브랜치 전환 |
| `git restore:*` | 파일 복원 |
| `git stash:*` | 작업 임시 저장 |
| `git show:*` | 커밋 상세 조회 |
| `git check-ignore:*` | .gitignore 규칙 확인 |
| `git ls-files:*` | 추적 파일 목록 조회 |
| `git filter-repo:*` | 히스토리 재작성 |
| `gh pr:*` | PR 생성/조회/병합 |
| `gh run list:*` | Actions 실행 목록 조회 |
| `gh run watch:*` | Actions 실행 상태 모니터링 |

프로젝트 히스토리 조회를 위한 다수의 `git -C /Users/idongju/Desktop/Git/Monitoring-v2 log ...` 형태의 세부 명령도 허용 목록에 포함되어 있습니다. 이는 AI 협업 커밋 분석 작업 중 구체적인 명령 패턴이 개별 항목으로 누적된 결과입니다.

#### 클라우드 도구

| 명령 | 용도 |
|------|------|
| `gcloud compute ssh:*` | GCP 인스턴스 SSH 접속 |
| `gcloud compute instances list:*` | 인스턴스 목록 조회 |
| `gcloud compute instances describe:*` | 인스턴스 상세 조회 |
| `gcloud compute firewall-rules list:*` | 방화벽 규칙 목록 조회 |
| `gcloud compute firewall-rules describe:*` | 방화벽 규칙 상세 조회 |
| `helm show:*` | Helm 차트 정보 조회 |
| `helm search repo:*` | Helm 저장소 검색 |

#### 기타 도구

| 명령 | 용도 |
|------|------|
| `ssh:*` | SSH 접속 (와일드카드 전체 허용) |
| `curl:*` | HTTP 요청 |
| `python3:*` | Python 스크립트 실행 |
| `go build:*` | Go 빌드 |
| `go test:*` | Go 테스트 실행 |
| `go mod download:*` | Go 모듈 다운로드 |
| `go mod tidy:*` | Go 모듈 정리 |
| `openssl rand:*` | 난수/비밀값 생성 |
| `gemini:*` | Gemini CLI 실행 |
| `find:*`, `grep:*`, `ls:*`, `cat:*`, `echo:*`, `tail:*`, `tree:*` | 파일 시스템 조회 및 텍스트 처리 |
| `mkdir:*`, `chmod:*`, `tee:*` | 파일 시스템 조작 |
| `pkill:*` | 프로세스 종료 |
| `env` | 환경 변수 조회 |

`ssh:*`는 와일드카드 허용으로, 원격 서버 접속 시 대상 호스트를 제한하지 않습니다.

### 와일드카드 허용 현황 요약

와일드카드(`*`)를 사용하는 주요 항목은 다음과 같습니다.

| 항목 | 허용 범위 |
|------|---------|
| `ssh:*` | 임의 호스트로의 SSH 접속 전체 허용 |
| `terraform destroy:*` | 인자 제한 없이 인프라 삭제 허용 |
| `KUBECONFIG=~/.kube/config-gcp kubectl:*` | GCP 클러스터의 모든 kubectl 서브커맨드 허용 |
| `gemini:*` | Gemini CLI의 모든 인자 허용 |
| `python3:*` | 임의 Python 스크립트 실행 허용 |
| `curl:*` | 임의 URL로의 HTTP 요청 허용 |

이 항목들은 작업 진행 중 세부 인자를 매번 개별 등록하는 대신, 도구 단위로 와일드카드를 적용하여 등록한 것입니다.

### 허용 항목이 많아진 배경

153개 항목은 프로젝트 초기부터 계획된 것이 아니라, 작업을 진행하면서 Claude Code가 승인을 요청할 때마다 해당 명령을 allow 목록에 추가하는 방식으로 점진적으로 누적된 결과입니다. 특히 git log 조회를 위한 세부 명령들이 여러 번 개별 항목으로 추가되면서 항목 수가 증가하였습니다.

---

## 보안 고려사항

### 환경 변수 관리

Terraform이 사용하는 민감한 설정값은 `TF_VAR_*` 환경 변수로 관리합니다. 실제 운영 값을 코드에 포함시키지 않고, 더미 값을 허용 목록에 명시하여 CI/CD 파이프라인과 로컬 개발 환경에서의 실행 흐름을 분리합니다.

허용 목록에 등록된 환경 변수 export 명령은 다음과 같습니다.

```
export TF_VAR_cloudstack_api_url="dummy"
export TF_VAR_cloudstack_api_key="dummy"
export TF_VAR_cloudstack_secret_key="dummy"
export TF_VAR_postgres_password="dummy"
```

이 항목들은 `terraform plan` 실행 시 변수 미설정 오류를 방지하면서도, 실제 자격 증명을 설정 파일에 노출시키지 않기 위한 방법으로 사용되었습니다.

### MCP 서버 접근 제어

`settings.local.json`은 MCP 서버 접근을 두 가지 방식으로 제어합니다.

| 설정 필드 | 값 | 의미 |
|---------|---|------|
| `enableAllProjectMcpServers` | `true` | 프로젝트에 정의된 모든 MCP 서버를 활성화 |
| `enabledMcpjsonServers` | `["claude-gemini-collaboration"]` | 전역 MCP 서버 중 명시된 서버만 활성화 |

개별 MCP 도구 허용 항목으로는 `mcp__chrome-devtools__*` 계열 도구 5개가 allow 목록에 등록되어 있습니다. 이는 Chrome DevTools MCP 서버의 도구 중 실제 사용하는 항목만을 개별 허용한 예시입니다.

`WebFetch`는 도메인 제한 형식(`WebFetch(domain:<도메인>)`)으로 허용되어 있어, 허용된 외부 도메인에서만 웹 콘텐츠를 가져올 수 있습니다. 허용된 도메인은 `raw.githubusercontent.com`, `carat.im`, `www.raylogue.com`, `www.wanted.co.kr` 이며, `WebSearch`는 도메인 제한 없이 전체 허용됩니다.

---

## 관련 파일

| 파일 | 설명 |
|------|------|
| `.claude/settings.local.json` | 실제 권한 설정 파일 (git 추적 제외) |
| `docs/09-ai-development/agent-design.md` | 커스텀 Agent 설계 문서 |
| `docs/09-ai-development/mcp-multi-ai.md` | MCP 기반 다중 AI 협업 문서 |

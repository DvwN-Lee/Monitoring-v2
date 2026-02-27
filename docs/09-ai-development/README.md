# AI Agent 활용 개발 프로세스

**작성일**: 2026-02-28

---

## 개요

이 프로젝트는 Kubernetes, Terraform, Istio 등 Cloud-Native 기술 스택을 기반으로, Claude Code AI Agent를 도구로 활용하여 개발 프로세스를 구성했습니다. AI Agent가 "만든" 프로젝트가 아니라, AI Agent를 "활용하여 구성한" 프로젝트입니다.

---

## 핵심 활용 영역

### 1. 커스텀 Agent 설계

프로젝트 특성에 맞는 `code-implementation-expert` Agent를 정의하여, 코드 구현 및 인프라 작업에 적합한 도구 권한과 행동 지침을 설정했습니다.

### 2. Worktree 기반 AI 협업

Git Worktree로 작업 브랜치를 격리하여, AI Agent와의 협업 중 메인 브랜치에 영향을 주지 않는 안전한 작업 환경을 구성했습니다.

### 3. Agent Teams Scrum

다관점 교차 검증을 위한 병렬 Agent 분석 프로세스로, 문서 및 코드 품질 검토를 구조화된 방식으로 수행했습니다.

### 4. MCP 프로토콜을 통한 AI 도구 통합

Claude Code와 Gemini를 MCP(Model Context Protocol) 프로토콜로 연동하여, 여러 AI 도구를 개발 워크플로우에 통합했습니다.

---

## 하위 문서

| 문서 | 설명 |
|------|------|
| [agent-design.md](agent-design.md) | 커스텀 Agent 설계 과정 |
| [worktree-workflow.md](worktree-workflow.md) | Worktree 기반 AI 협업 프로세스 |
| [mcp-multi-ai.md](mcp-multi-ai.md) | MCP 프로토콜을 통한 AI 도구 통합 |
| [permission-policy.md](permission-policy.md) | CLI 권한 정책 설계 |
| [scrum-reviews/](scrum-reviews/) | Agent Teams Scrum 문서 검토 이력 |

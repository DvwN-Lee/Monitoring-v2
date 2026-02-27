# MCP 프로토콜을 통한 AI 도구 통합

**작성일**: 2026-02-28
**문서 경로**: `docs/09-ai-development/mcp-multi-ai.md`

---

## 개요

본 문서는 MCP(Model Context Protocol) 프로토콜을 활용하여 Claude Code와 Gemini를 연동한 과정을 기술합니다.

이 프로젝트에서의 MCP 활용 범위는 `settings.local.json`의 `enabledMcpjsonServers: ["claude-gemini-collaboration"]` 설정 1건으로, Claude Code 세션 내에서 Gemini를 보조 AI 도구로 호출할 수 있는 통합 구성입니다.

---

## MCP 개요

### Model Context Protocol이란

MCP(Model Context Protocol)는 AI 모델과 외부 도구 및 서비스를 연결하기 위한 표준 프로토콜입니다. Anthropic이 제안한 오픈 프로토콜로, AI 모델이 외부 데이터 소스, API, 도구를 일관된 인터페이스로 사용할 수 있도록 설계되었습니다.

MCP의 핵심 구성 요소는 다음과 같습니다.

| 구성 요소 | 설명 |
|-----------|------|
| MCP 서버 | 외부 도구 또는 서비스를 MCP 인터페이스로 노출하는 서버 |
| MCP 클라이언트 | MCP 서버에 연결하여 도구를 호출하는 AI 모델 측 컴포넌트 |
| 프로토콜 | JSON-RPC 기반의 표준 통신 규약 |

### Claude Code에서 MCP 서버 설정 방식

Claude Code는 두 가지 수준에서 MCP 서버를 설정할 수 있습니다.

- **전역 설정**: `~/.claude/settings.json` 또는 `~/.claude.json` - 모든 프로젝트에 적용
- **프로젝트 설정**: `.claude/settings.local.json` - 해당 프로젝트에만 적용

프로젝트 설정에서 `enabledMcpjsonServers` 배열에 MCP 서버 이름을 명시하면, Claude Code 세션에서 해당 서버를 통해 외부 도구를 사용할 수 있습니다.

---

## 프로젝트에서의 MCP 활용

### settings.local.json 설정

이 프로젝트의 `.claude/settings.local.json`에는 다음 설정이 포함되어 있습니다.

```json
{
  "enableAllProjectMcpServers": true,
  "enabledMcpjsonServers": [
    "claude-gemini-collaboration"
  ]
}
```

`enabledMcpjsonServers` 배열에 `"claude-gemini-collaboration"` 1개의 MCP 서버가 등록되어 있습니다. 이 설정을 통해 Claude Code 세션 내에서 Gemini API를 MCP 인터페이스를 통해 호출할 수 있습니다.

### Claude Code + Gemini MCP 서버 구성

`claude-gemini-collaboration` MCP 서버는 Claude Code가 Gemini 모델에 쿼리를 전달하고 응답을 받을 수 있도록 중간 계층 역할을 합니다. 구성 흐름은 다음과 같습니다.

```
Claude Code (MCP 클라이언트)
    │
    │  MCP 프로토콜 (JSON-RPC)
    ▼
claude-gemini-collaboration MCP 서버
    │
    │  Gemini API 호출
    ▼
Google Gemini 모델
```

이 통합을 통해 Claude Code 세션 내에서 Gemini의 응답을 직접 참조하는 것이 가능해졌습니다.

### 실제 활용 방식

이 프로젝트에서 Gemini MCP 통합의 실제 활용 방식은 다음과 같습니다.

- **교차 참조 분석**: 특정 설계 결정이나 문서 내용에 대해 Claude와 Gemini 양쪽의 의견을 비교하여 다관점 분석을 수행
- **검증 용도**: Claude가 작성한 내용을 Gemini에 질의하여 오류 또는 누락 여부를 확인
- **보완적 사용**: Claude Code의 주 작업 흐름 내에서 Gemini를 보조 참조 도구로 선택적으로 활용

---

## 설정 예시

### settings.local.json 전체 구조 (MCP 관련 부분)

```json
{
  "permissions": {
    "allow": [
      "Bash(gemini:*)",
      "..."
    ],
    "deny": [],
    "ask": []
  },
  "enableAllProjectMcpServers": true,
  "enabledMcpjsonServers": [
    "claude-gemini-collaboration"
  ]
}
```

`permissions.allow` 배열에 `"Bash(gemini:*)"` 항목이 포함되어 있어, Claude Code가 `gemini` CLI 명령도 직접 실행할 수 있습니다. MCP 서버 통합과 CLI 직접 호출 두 가지 방식이 모두 설정되어 있습니다.

---

## 활용 사례

### 문서 검토 시 Claude와 Gemini 의견 비교

문서 내용이나 아키텍처 결정에 대해 Claude와 Gemini의 의견을 비교하는 방식으로 활용했습니다. 두 모델의 응답이 일치하는 경우 결정에 대한 신뢰도를 높이고, 차이가 있는 경우 추가 검토의 근거로 활용합니다.

활용 예시:

- ADR(Architecture Decision Record) 작성 시 Claude가 초안을 작성하고, Gemini에 동일한 질문을 통해 추가 관점 확인
- 트러블슈팅 문서에서 Claude가 제안한 해결 방안을 Gemini에 교차 확인

### Agent Teams Scrum과의 연계

Agent Teams Scrum 프로세스에서 다관점 교차 검증이 필요한 경우, Gemini MCP 통합을 활용했습니다. Claude Code의 Agent Teams가 분석한 결과를 Gemini에 추가 질의하여 검증 범위를 넓히는 방식입니다.

다만 이 연계는 선택적으로 활용되었으며, Scrum의 핵심 검증 프로세스는 Claude Code Agent Teams 내에서 완결됩니다. Gemini는 추가 참조 도구로서의 역할에 한정되었습니다.

---

## 제약 및 한계

이 MCP 통합 구성에서 확인된 제약 사항은 다음과 같습니다.

- **단일 서버 구성**: `enabledMcpjsonServers`에 등록된 서버가 `claude-gemini-collaboration` 1개로, 현재 Gemini 연동에 특화된 구성입니다.
- **보조적 역할**: Gemini는 Claude Code의 주 작업 흐름을 대체하는 것이 아니라 보조 참조 도구로 활용됩니다.
- **수동 호출**: Gemini에 대한 질의는 자동으로 실행되지 않으며, 필요한 시점에 사용자 또는 Claude Code가 명시적으로 호출합니다.

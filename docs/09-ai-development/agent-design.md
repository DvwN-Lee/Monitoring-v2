# 커스텀 AI Agent 설계 문서

**작성일**: 2026-02-28

---

## 개요

이 문서는 Claude Code의 커스텀 Agent 기능을 활용하여 Monitoring-v2 프로젝트 특성에 맞는 `code-implementation-expert` Agent를 정의한 과정을 기술합니다.

Claude Code는 `.claude/agents/` 디렉토리에 마크다운 파일을 배치하는 방식으로 프로젝트 전용 커스텀 Agent를 등록할 수 있습니다. 이 Agent 파일은 YAML 프론트매터(메타데이터)와 마크다운 본문(시스템 프롬프트)으로 구성됩니다.

---

## Agent 설계 동기

### 코드 구현 품질 확보 필요성

Monitoring-v2는 Kubernetes 기반의 Cloud-Native 마이크로서비스 플랫폼으로, 다수의 언어와 프레임워크(Go, Python, Java, TypeScript)가 혼재합니다. 각 서비스마다 코드 구현 시 다음 요소를 일관되게 적용해야 합니다.

- 엣지 케이스 및 에러 핸들링 일관성
- N+1 쿼리, 경쟁 조건(race condition) 등 성능 이슈 방지
- 프로젝트 컨벤션에 맞는 명명 규칙 및 코드 구조 준수

기본 Claude Code 동작은 범용적으로 설계되어 있어, 위 요구사항을 반복적으로 지시하지 않으면 일관된 품질을 보장하기 어렵습니다.

### 커스터마이징 목적

기본 Claude Code 동작을 프로젝트 컨벤션에 맞게 커스터마이징하는 구체적인 목적은 다음과 같습니다.

- **한국어 코멘트 규칙 적용**: 코드 주석을 한국어로 작성하는 규칙을 Agent 수준에서 강제
- **Quality Over Speed 원칙 내재화**: 빠른 답변보다 정확하고 방어적인 구현을 우선하도록 Agent 행동 방침 설정
- **구현 워크플로우 표준화**: 요구사항 확인 → 설계 계획 → 코드 구현 → 품질 검증의 단계를 Agent가 자동으로 따르도록 지시
- **호출 맥락 명시**: 언제 이 Agent를 사용해야 하는지 `description` 필드에 명시하여, Claude Code가 적절한 상황에 자동으로 Agent를 선택하도록 유도

---

## Agent 파일 구조

### 파일 위치

```
.claude/
└── agents/
    └── code-implementation-expert.md
```

### YAML 프론트매터

파일 상단의 YAML 프론트매터는 Agent의 메타데이터를 정의합니다.

```yaml
---
name: code-implementation-expert
description: Use this agent when you need to implement functional, production-ready code ...
model: sonnet
color: yellow
---
```

| 필드 | 값 | 설명 |
|---|---|---|
| `name` | `code-implementation-expert` | Agent 식별자. Claude Code 내부에서 참조할 때 사용 |
| `description` | (상세 텍스트) | Agent 호출 맥락 설명. Claude Code가 이 내용을 기반으로 적절한 상황에 Agent를 선택 |
| `model` | `sonnet` | 이 Agent가 사용할 Claude 모델 지정 |
| `color` | `yellow` | Claude Code UI에서 Agent를 시각적으로 구분하기 위한 색상 |

### 마크다운 본문 = 시스템 프롬프트

YAML 프론트매터 이후의 마크다운 본문 전체가 해당 Agent의 시스템 프롬프트로 작동합니다. 별도의 코드 파일이나 스크립트 없이, 마크다운으로 작성된 지시문이 곧 Agent의 행동 방침이 됩니다.

---

## 핵심 설정 내용

### 모델 선택: `sonnet`

`model: sonnet`으로 지정하였습니다. 코드 구현은 복잡한 추론과 정확성이 요구되는 작업으로, sonnet 모델이 구현 품질과 응답 속도 사이의 균형을 적절히 제공합니다.

### Quality Over Speed 원칙

Agent의 핵심 원칙(Core Principles)으로 명시된 첫 번째 항목입니다.

> **Quality Over Speed**: 빠른 해결책보다 정확하고 유지보수 가능한 코드를 우선합니다. 작성하는 모든 코드는 근거 있고 방어적이어야 합니다.

이 원칙은 Agent가 코드를 작성할 때 속도보다 정확성을 우선하도록 행동 방침을 설정합니다.

### 구현 워크플로우 단계

Agent는 코드 구현 시 다음 5단계 워크플로우를 따르도록 정의되어 있습니다.

1. **Requirements Clarification**: 요구사항이 모호하거나 불완전한 경우 확인 후 진행
2. **Design Planning**: 복잡한 구현을 논리적 단계로 분해하고, 성능·에러 처리 전략 수립
3. **Code Implementation**: 명확한 변수/함수 명명, 에러 핸들링, 엣지 케이스 처리, 성능 최적화 적용
4. **Code Quality Standards**: 기존 코드베이스 컨벤션 준수, 타입 안전성, 모듈화 및 테스트 가능성 확보
5. **Verification**: 다양한 입력값으로 코드를 추적하여 에러 경로와 리소스 정리를 검증

### 한국어 코멘트 규칙

`Special Instructions from User Context` 섹션에 다음 규칙이 명시되어 있습니다.

- 모든 코드 주석은 한국어로 작성
- 기술 용어(Technical terms)는 영어 그대로 사용 가능
- 변수명·함수명은 영어 표준 컨벤션 유지

이를 통해 코드 주석의 언어 일관성을 Agent 수준에서 보장합니다.

### 엣지 케이스 처리 기준

Agent는 다음 항목을 항상 고려하도록 정의되어 있습니다.

- Null, undefined, 빈 값
- 빈 배열/컬렉션
- 잘못된 입력 타입
- 경계 조건(최솟값/최댓값)
- 동시 접근 및 경쟁 조건
- 네트워크 장애 및 타임아웃
- 데이터베이스 트랜잭션 실패

### 출력 형식 표준

코드 제공 시 Agent가 따르는 출력 형식입니다.

1. 구현 접근 방식을 한국어로 간략히 설명
2. 주석이 포함된 완전한 동작 코드 제시
3. 중요한 고려사항 또는 제한사항 명시
4. 관련 테스트 시나리오 제안(해당하는 경우)

### description 필드의 호출 맥락 정의

`description` 필드에는 Agent를 언제 호출해야 하는지 명확한 조건과 예시가 포함되어 있습니다.

**호출 조건**:
- 요구사항 분석 후 코드 구현이 필요한 경우
- 오류 없이 정확하게 동작해야 하는 코드를 작성해야 하는 경우
- 명세나 설계를 동작하는 구현으로 전환해야 하는 경우
- 엣지 케이스와 에러 핸들링이 필요한 기능을 구축하는 경우
- 유지보수 가능하고 모범 사례를 따르는 코드를 생성해야 하는 경우

이 정의를 통해 Claude Code가 적절한 상황에서 자동으로 이 Agent를 선택하도록 유도합니다.

---

## Claude Code 커스텀 Agent 개요

Claude Code의 커스텀 Agent 기능은 다음과 같이 동작합니다.

- **파일 위치**: `.claude/agents/` 디렉토리에 `.md` 파일로 정의
- **메타데이터**: YAML 프론트매터(`---` 블록)로 `name`, `model`, `color`, `description` 등 설정
- **시스템 프롬프트**: YAML 프론트매터 이후의 마크다운 본문 전체가 해당 Agent의 시스템 프롬프트로 적용
- **자동 선택**: `description` 필드 내용을 기반으로 Claude Code가 맥락에 맞는 Agent를 자동으로 선택
- **수동 호출**: 사용자가 명시적으로 특정 Agent를 지정하여 호출하는 것도 가능

이 방식은 별도의 코드 실행 없이 마크다운 파일만으로 Agent 동작을 정의할 수 있다는 점에서, 프로젝트 요구사항 변경 시 수정이 용이합니다.

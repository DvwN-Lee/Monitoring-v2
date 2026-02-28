# Agent Teams Scrum 리뷰 문서 모음

**작성일**: 2026-02-28
**위치**: `docs/09-ai-development/scrum-reviews/`

---

## 개요

Agent Teams Scrum은 복수의 AI Agent를 병렬로 실행하여 다관점 교차 검증을 수행하는 방법론입니다. 각 Agent는 독립적으로 주어진 분석 대상을 검토하고, VETO 투표를 통해 합의를 도출합니다. 단일 Agent의 편향이나 맹점을 복수의 관점으로 상쇄하는 것이 핵심 목적입니다.

이 디렉토리는 Monitoring-v2 프로젝트 개발 과정에서 수행한 Agent Teams Scrum의 결과 문서를 보관합니다.

---

## Scrum 방법론 개요

### 3-Agent VETO 합의 프로세스

```
1. 분석 대상 정의
   ├── 검토할 문서 또는 계획을 명확히 정의
   └── 각 Agent의 전문 관점 역할 배정

2. 병렬 독립 분석
   ├── Agent A: 첫 번째 관점에서 독립적으로 분석
   ├── Agent B: 두 번째 관점에서 독립적으로 분석
   └── Agent C: 세 번째 관점에서 독립적으로 분석

3. VETO 투표 및 합의
   ├── 각 항목에 대해 APPROVE / MODIFY / VETO 투표
   ├── 1건 이상 VETO → 해당 항목 수정 또는 제외
   ├── MODIFY만 존재 → 수정 반영 후 구현
   └── 전원 APPROVE → 즉시 구현 대상

4. 합의 결과 정리
   └── 구현 가능 항목, 수정 필요 항목, 제외 항목 분류
```

**규칙 요약**:

- VETO는 1건이라도 발생하면 해당 항목은 사용자 판단 또는 제외
- 사실 오류(Fact Checker VETO)는 반드시 수정
- 합의가 완료된 항목만 구현 진행

---

## 이 프로젝트에서 수행한 Scrum 이력

| 회차 | 제목 | Agent 구성 | 핵심 결과 | 문서 |
|:----:|------|-----------|---------|------|
| 1차 | 문서 재구성 분석 | doc-reviewer, fact-checker, recommendation-writer | VETO 없음, 문서 재구성 방향 수립 | [document-restructuring-review.md](document-restructuring-review.md) |
| 2차 | AI Agent 포트폴리오 시장 분석 | market-analyst, portfolio-strategist, hiring-reviewer | VETO 2건(구축 증거 부재, 포지셔닝 불일치), 하이브리드 포지셔닝 권장 | [portfolio-restructuring-analysis.md](portfolio-restructuring-analysis.md) |
| 3차 | 문서 재구성 구현 전략 검토 | doc-quality-reviewer, fact-checker, portfolio-reviewer | VETO 1건(PR 수량/Worktree 표현), 수정 후 승인 | [doc-restructuring-strategy-review.md](doc-restructuring-strategy-review.md) |
| 4차 | Phase 1 완성 문서 최종 검토 | doc-quality-reviewer, fact-checker, portfolio-reviewer | VETO 1건(이다체→합쇼체 수정), 수정 후 NO VETO. 점수 4.20/5 PASS | [final-document-review.md](final-document-review.md) |

---

## 각 Scrum에서 배운 점

### 1차 Scrum: 문서 재구성 분석

- **배운 점**: "무엇을 만들었는가(시스템 기능)"와 "어떻게 만들었는가(개발 프로세스)"를 문서 내에서 명확히 분리해야 합니다. 두 범주를 혼재시키면 문서 구성력 부족으로 보일 수 있습니다.
- **핵심 원칙 도출**: 사실 기반 서술만 허용, 측정된 성능 데이터 변경 금지, 기존 문서 톤/구조 일관성 유지.
- **결과**: 9건의 수정안 확정 (즉시 구현 3건, MODIFY 반영 후 구현 6건, 제외 2건).

### 2차 Scrum: AI Agent 포트폴리오 시장 분석

- **배운 점**: "AI Agent를 사용한 프로젝트"와 "AI Agent를 개발한 프로젝트"는 채용 시장에서 명확히 구별됩니다. 현재 프로젝트는 전자에 해당하며, 이를 과대 포장하면 역효과가 발생합니다.
- **VETO 2건의 교훈**: Agent 구축 증거 부재와 포지셔닝 불일치는 전원 합의 VETO를 받았습니다. 이는 사실에 근거한 포지셔닝의 중요성을 보여줍니다.
- **결과**: "AI Agent를 체계적으로 활용하는 Cloud-Native 엔지니어" 하이브리드 포지셔닝 권장. 후속 AI Agent 시스템 구축 프로젝트 방향 도출.

### 3차 Scrum: 문서 재구성 구현 전략 검토

- **배운 점**: 구현 계획에도 사실 검증이 필요합니다. "PR 61건"이라는 표현은 GitHub의 Issue/PR 번호 공유 방식에 대한 오해에서 비롯되었으며, 실제는 PR 27건이었습니다.
- **Worktree 표현의 교훈**: Worktree는 merge 후 정리하면 흔적이 남지 않습니다. 현재 존재하지 않는 것을 존재하는 것처럼 표현하는 것은 사실 오류입니다. 간접 증거(PR 히스토리)를 간접 증거로 표현해야 합니다.
- **결과**: VETO 1건 수정 후 구현 승인. 포트폴리오 점수 3.23 → 3.73/5 개선 예측.

---

## 하위 문서 링크

| 문서 | 작성일 | 설명 |
|------|:------:|------|
| [document-restructuring-review.md](document-restructuring-review.md) | 2026-02-27 | 1차 Scrum: 4개 핵심 문서에 AI Agent 개발 프로세스 반영을 위한 다관점 분석 |
| [portfolio-restructuring-analysis.md](portfolio-restructuring-analysis.md) | 2026-02-28 | 2차 Scrum: 한국 AI Agent 취업 시장 분석 및 포트폴리오 포지셔닝 전략 |
| [doc-restructuring-strategy-review.md](doc-restructuring-strategy-review.md) | 2026-02-28 | 3차 Scrum: 문서 재구성 구현 계획(Task 1~10) 사실 검증 및 품질 검토 |

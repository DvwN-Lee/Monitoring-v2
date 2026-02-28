# AI Agent 엔지니어 포트폴리오 재구성 - Scrum 분석 리포트

**작성일**: 2026-02-28
**분석 방법**: Agent Teams 병렬 전문가 분석 (3-Agent VETO 교차 검증)
**대상 프로젝트**: Monitoring-v2 (Cloud-Native Microservice 플랫폼 v2.0)

---

## Executive Summary

3개 전문가 Agent(Market Analyst, Portfolio Strategist, Hiring Reviewer)가 독립적으로 분석한 결과, **핵심 결론이 완전히 수렴**했다:

> **현재 프로젝트는 AI Agent를 "사용/설정"한 증거는 있으나, "설계/구축"한 증거가 없다.**
> **AI Agent 엔지니어 단독 포트폴리오로는 부족하지만, Cloud-Native + AI Agent 활용의 하이브리드 포지셔닝으로는 강력한 차별화가 가능하다.**

---

## 1. VETO 교차 검증 (3-Agent 합의)

### 1.1 VETO 매트릭스

| VETO 항목 | Market Analyst | Portfolio Strategist | Hiring Reviewer | 합의 |
|-----------|:-:|:-:|:-:|:-:|
| Agent "구축" 증거 부재 | VETO | VETO (조건부) | VETO | **전원 VETO** |
| 과대 포장 위험 | - | VETO (조건부) | VETO (조건부) | 2/3 VETO |
| 포지셔닝 불일치 (DevOps vs AI Agent) | VETO (조건부) | VETO (조건부) | VETO | **전원 VETO** |
| 핵심 기술 스택 부재 (RAG, LangChain, 벡터DB) | VETO | - | - | 1/3 VETO |
| 문서 재구성만으로 충분한가 | - | VETO (조건부) | - | 1/3 VETO |

### 1.2 전원 합의 VETO (2건) - 반드시 대응 필요

**VETO-A: Agent "구축" 증거 부재**

- Market Analyst: "AI '활용' vs AI '개발'의 차이. 시장은 후자를 요구"
- Portfolio Strategist: "AI Agent를 만든 것이 아니라 사용한 프로젝트"
- Hiring Reviewer: "YAML+마크다운 프롬프트 파일이지, Python/TypeScript Agent 코드가 아니다"

구체적 부재 항목:
- LLM API 호출 코드 없음
- Agent 프레임워크(LangChain, CrewAI, AutoGen) 활용 없음
- Tool-use/Function-calling 정의 없음
- RAG 파이프라인 없음
- Agent 오케스트레이션 코드 없음

**VETO-B: 포지셔닝 불일치**

- Market Analyst: "프로젝트 핵심 가치는 Cloud-Native 인프라에 있으며, AI Agent 개발 프로젝트로 포지셔닝하기에는 AI 관련 구현물이 너무 적다"
- Portfolio Strategist: "Terraform, Kubernetes, Istio가 기술의 90%+. AI Agent는 개발 방법론/도구에 해당"
- Hiring Reviewer: "면접에서 'Agent 아키텍처를 직접 설계해본 경험이 있는가?'에 답변 곤란"

---

## 2. 한국 AI Agent 취업 시장 핵심 요약

### 2.1 시장 규모

- 국내 기업 85%가 생성형 AI 도입 (2026년)
- AI Agent 소프트웨어 시장: 2025년 $15억 → 2030년 $418억 (연평균 175% 성장)
- 잡코리아 기준 'LLM agent' 169건, 'LLM' 699건, 'AI 개발자' 3,815건

### 2.2 시장이 요구하는 핵심 스킬 (JD 빈도순)

| 순위 | 스킬 | 빈도 |
|:----:|------|:----:|
| 1 | Python | 거의 모든 JD |
| 2 | LLM 이해 (GPT, Claude) | 매우 높음 |
| 3 | LangChain / LlamaIndex | 높음 |
| 4 | RAG 파이프라인 | 높음 |
| 5 | 프롬프트 엔지니어링 | 높음 |
| 6 | Docker / Kubernetes | 중간~높음 |
| 7 | MCP (Model Context Protocol) | **급상승** |
| 8 | 벡터 DB | 중간 |
| 9 | 멀티에이전트 (CrewAI, LangGraph) | 상승 중 |

### 2.3 한국 시장 특수성

- **Cloud-Native 인프라 역량이 AI Agent 직무의 필수 요건** (네이버클라우드 JD 증거)
- MCP가 카카오 PlayMCP로 국내 선도 (공모전까지 개최)
- 실용화 중심 전략: "기존 사업에 AI를 어떻게 적용할 것인가"에 초점
- IBM "Cloud Native Dev base AI Agent" 교육과정이 정부 지원으로 운영 중

---

## 3. 현재 프로젝트 자산 평가

### 3.1 강점 (3-Agent 공통 인정)

| 자산 | 평가 | 활용 방향 |
|------|------|----------|
| Cloud-Native 인프라 (K8s, Terraform, Istio, GitOps) | **매우 강함** | AI Agent 직무에서도 필수 요건 (특히 한국) |
| MCP 실무 경험 (Gemini MCP 통합) | **희소성 높음** | 시장에서 급부상 중인 기술의 실전 경험 |
| CLI 권한 정책 설계 (150줄+) | **차별화** | AI 거버넌스/보안 관점 성숙도 증명 |
| 3-Agent VETO 합의 워크플로우 | **매우 높은 차별화** | Agent 시스템 설계 사고의 직접 증거 |
| 문서화 역량 (60+ 파일, ADR 10건) | **4.5/5** (Hiring Reviewer) | 엔지니어링 기본기 증명 |
| 커스텀 Agent 정의서 | **중간** | Agent "설정" 수준이지만 구조적 사고 보임 |

### 3.2 약점 (3-Agent 공통 지적)

| 약점 | 심각도 | 설명 |
|------|:------:|------|
| AI Agent "제품" 부재 | 높음 | Agent를 만든 것이 아니라 사용한 프로젝트 |
| LLM/RAG/벡터DB 코드 없음 | 높음 | AI Agent 핵심 기술 스택 증거 부재 |
| AI 활용 비율 낮음 | 중간 | Co-Authored 5건/535건 (0.9%) |
| Agent 프레임워크 미사용 | 중간 | LangChain, CrewAI 등 범용 프레임워크 경험 없음 |
| 커스텀 Agent 1개뿐 | 낮음 | Agent 설계 역량의 폭 미증명 |

### 3.3 채용 심사 평가 (Hiring Reviewer)

| 항목 | 점수 |
|------|:----:|
| 첫인상 (README) | 3.5/5 |
| Agent 시스템 설계 역량 | 3.0/5 |
| 차별화 요소 | 2.5/5 |
| 실무 적용 가능성 | 3.5/5 |
| 문서화 역량 | 4.5/5 |
| 기술 깊이 | 2.5/5 |
| **가중 합계** | **3.23/5** |
| **서류 판정** | **FAIL** |

---

## 4. 전략적 방향성 제안

### 4.1 포지셔닝 전략 (3-Agent 합의)

**"AI Agent를 만드는 엔지니어" 단독 포지셔닝 → 불가** (전원 VETO)

대신 두 가지 실행 가능한 경로:

#### 경로 A: 하이브리드 포지셔닝 (문서 재구성만으로 가능)

**"AI Agent를 체계적으로 활용하는 Cloud-Native 엔지니어"**

- 주축: Cloud-Native Microservice 엔지니어 (검증된 역량)
- 부축: AI Agent 활용/설계 역량 (개발 도구로서의 활용)
- 타겟 포지션: "AI-Augmented DevOps Engineer", "Platform Engineer (AI 도구 활용)"
- 차별점: "단순 사용이 아닌, Agent 커스터마이징/권한 설계/멀티 AI 통합/다관점 합의 워크플로우 설계"

적합도: 중간 - 문서 재구성만으로 실현 가능하나, AI Agent 엔지니어 직군과는 거리가 있음

#### 경로 B: AI Agent 프로젝트 추가 구축 후 듀얼 포트폴리오 (권장)

**"AI Agent를 개발하고 + Cloud-Native로 배포/운영할 수 있는 풀스택 AI 엔지니어"**

- 메인 포트폴리오: 새로 구축할 AI Agent 시스템 (RAG, LangChain/LangGraph, Agent 오케스트레이션)
- 보조 포트폴리오: 현재 Monitoring-v2 (인프라 역량 + AI 활용 경험 증명)
- 타겟 포지션: "AI Agent 개발 엔지니어", "LLM Engineer"

적합도: 높음 - 한국 시장 특수성(Cloud-Native + AI 결합 요구)에 정확히 부합

### 4.2 경로 B의 구체적 제안 (3-Agent 교차 제안)

**Hiring Reviewer 제안**: "Prometheus 알림을 수신하고 자동으로 원인 분석 및 대응 방안을 제시하는 SRE Agent"
→ 기존 도메인 지식(K8s, 모니터링)과 AI Agent 기술을 자연스럽게 결합

**Market Analyst 제안**: RAG 파이프라인 + LangChain/LangGraph + 벡터DB 포함, 실제 도메인 문제 해결
→ 시장 JD 필수 요건을 직접 충족

**Portfolio Strategist 제안**: 현재 프로젝트에서 확장 가능한 방향으로
→ 기존 자산 활용 극대화

**종합**: 현재 Monitoring-v2의 관측성 스택(Prometheus/Grafana/Loki)을 활용하여, **K8s 클러스터 장애를 자동 진단/대응하는 AI Agent 시스템**을 LangGraph + MCP 기반으로 구축하면:
- 시장 요구 핵심 기술(LLM, RAG, Agent Framework, MCP) 충족
- 기존 인프라 역량과 자연스러운 연결
- 한국 시장의 "실용화 중심" 특성에 부합
- DevAI Solutions(IT 인프라 관리 자동화 Agent, 600만 달러 투자)와 유사한 도메인

### 4.3 문서 재구성 시 주의사항 (과대 포장 방지)

| 위험 표현 | 안전한 대체 표현 |
|-----------|-----------------|
| "AI Agent 엔지니어링 프로젝트" | "AI Agent를 활용한 Cloud-Native 개발 프로젝트" |
| "광범위한 AI 활용" | "특정 인프라 작업에서의 AI Agent 협업" |
| "멀티 Agent 오케스트레이션 시스템" | "MCP 프로토콜을 통한 멀티 AI 환경 구성" |
| "AI가 생산성을 N% 향상" | "AI 도구를 IaC 작성, 문서화에 통합" |

---

## 5. 즉시 실행 가능한 액션 (문서 재구성 범위)

현재 세션의 범위(README + 문서 재구성)에서 실행 가능한 항목:

| 우선순위 | 액션 | 효과 |
|:--------:|------|------|
| 1 | README에 "AI Agent 개발 프로세스" Top-level 섹션 추가 | 첫인상 변화 |
| 2 | docs/09-ai-development/ 디렉토리 신설 + 기존 자산 문서화 | 깊이 증명 |
| 3 | Agent 관련 ADR 2건 추가 (Agent 프레임워크 선택, 권한 관리 전략) | 아키텍처 사고 증명 |
| 4 | document-restructuring-report.md를 공개 문서로 승격 | 시스템 설계 역량 증명 |
| 5 | 커스텀 Agent 2-3개 추가 정의 | Agent 설계 폭 확장 |

**단, 위 액션만으로는 AI Agent 엔지니어 서류 통과가 어려움 (전원 합의)**

---

## 6. 결론

### 한 줄 요약

이 프로젝트는 **AI Agent 엔지니어 "단독" 포트폴리오로는 FAIL**이지만, **새로운 AI Agent 시스템 프로젝트와 결합하면 한국 시장에서 매우 차별화된 "Cloud-Native + AI Agent" 풀스택 프로필**을 구성할 수 있다.

### 3-Agent 최종 합의

| Agent | 최종 판정 | 핵심 메시지 |
|-------|----------|------------|
| Market Analyst | 조건부 VETO | 시장은 Agent "개발" 역량을 요구. 단, Cloud-Native 인프라가 한국에서는 필수 요건이므로 보조 포트폴리오로 강력 |
| Portfolio Strategist | 조건부 VETO | "Agent를 활용하는 엔지니어"로는 충분하나, "Agent를 만드는 엔지니어"로는 갭 존재 |
| Hiring Reviewer | FAIL (3.23/5) | Agent 구축 증거 부재로 서류 탈락. 단 엔지니어링 기본기(문서화 4.5/5)는 우수 |

### 권장 Next Step

1. **이번 세션**: README + 문서 재구성으로 현재 AI Agent 활용 자산을 최대한 표면화 (경로 A)
2. **후속 프로젝트**: LangGraph + MCP 기반 K8s 장애 자동 진단 AI Agent 시스템 구축 (경로 B)
3. **최종 포트폴리오**: Monitoring-v2(인프라) + AI Agent 시스템(AI) 듀얼 포트폴리오로 AI Agent 엔지니어 포지션 지원

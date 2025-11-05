# 롤백 테스트 결과 보고서

## 테스트 개요

Issue #15 [FEATURE-2.6] E2E 테스트 및 롤백의 일환으로 세 가지 롤백 시나리오를 테스트했습니다.

### 테스트 환경
- **Kubernetes Cluster**: Solid Cloud (On-premise)
- **GitOps Tool**: Argo CD (auto-sync enabled)
- **CI/CD**: GitHub Actions
- **대상 서비스**: user-service
- **테스트 버전**: v1.1.1 <-> v1.1.2

---

## 시나리오 #1: Git revert를 통한 롤백

### 방법
```bash
git revert <commit-hash>
git push origin main
# CI/CD 파이프라인 자동 실행
```

### 실행 과정
1. v1.1.2 커밋 (2fd69a0)을 revert하는 새로운 커밋 생성
2. 롤백 브랜치 생성: `rollback/revert-v1.1.2`
3. PR #43 생성 및 머지
4. CI Pipeline 실행 (빌드, 스캔, 검증)
5. CD Pipeline 실행 (kustomization.yaml 업데이트)
6. Argo CD 동기화 및 배포

### 결과
- **결과**: 성공
- **소요 시간**: 
  - CI (PR): 1분 15초
  - CI (main): 36초
  - CD: 11초
  - Argo CD Sync + Rollout: ~1분
  - **총 소요 시간**: 약 3-4분

### 장점
- Git 히스토리에 롤백이 명확하게 기록됨
- 완전한 추적성 (audit trail)
- GitOps 원칙을 완전히 준수
- 롤백 자체도 CI/CD 파이프라인을 통과하여 검증됨

### 단점
- 가장 느린 롤백 방법
- PR 생성 및 머지 과정이 필요
- CI/CD 파이프라인 전체를 다시 실행

### 권장 사용 사례
- 프로덕션 환경의 공식 롤백
- 롤백 이유와 과정을 명확히 문서화해야 할 때
- 팀 승인이 필요한 롤백

---

## 시나리오 #2: Argo CD UI를 통한 롤백

### 방법
Argo CD 웹 UI의 History 탭에서 이전 버전 선택 후 Rollback 버튼 클릭

### Argo CD 배포 히스토리
```
ID  배포 시간              Git Revision  설명
7   2025-10-30 11:45:20   e89e4db       현재 버전 (v1.1.1 롤백)
6   2025-10-30 11:36:20   56d8c24       v1.1.2 배포
5   2025-10-30 09:35:56   f59e199       v1.1.1 배포
4   2025-10-30 09:00:39   dd5c6a9       nginx 프록시 설정
```

### 실행 과정
1. Argo CD UI 접속 (https://localhost:8080)
2. titanium-prod 애플리케이션 선택
3. History 탭 이동
4. 롤백할 버전 선택 (예: ID 6)
5. "..." 메뉴에서 "Rollback" 클릭
6. 확인 후 배포 자동 진행

### 결과
- **결과**: 문서화 완료 (실제 UI 롤백은 사용자가 필요시 수행)
- **예상 소요 시간**: 약 1-2분
  - Argo CD 동기화: 즉시
  - Kubernetes 롤아웃: ~1분

### 장점
- 빠른 롤백 (Git revert보다 빠름)
- GUI를 통한 직관적인 조작
- 배포 히스토리를 시각적으로 확인 가능
- Git 저장소의 이전 커밋으로 롤백

### 단점
- Git 저장소의 소스 코드는 변경되지 않음 (불일치 발생)
- 다음 배포 시 Git의 최신 상태로 덮어쓰여질 수 있음
- CI/CD 파이프라인을 거치지 않음 (검증 단계 생략)

### 권장 사용 사례
- 긴급 롤백이 필요한 경우
- 테스트 환경에서의 빠른 롤백
- 이전 배포 상태로 일시적으로 복구

### 주의사항
- **GitOps 불일치**: Git 저장소의 kustomization.yaml은 여전히 최신 버전을 가리킴
- **영구 롤백이 필요한 경우**: Argo CD UI 롤백 후 반드시 Git revert 수행 필요

---

## 시나리오 #3: kubectl rollout undo를 통한 롤백

### 방법
```bash
kubectl rollout undo deployment/prod-user-service-deployment -n titanium-prod
```

### 실행 과정
1. **첫 번째 시도 (Auto-sync 활성화 상태)**
   - kubectl rollout undo 실행
   - 롤백 시작되었으나...
   - Argo CD auto-sync가 즉시 Git 상태로 되돌림
   - **결과**: 롤백 실패 (GitOps에 의해 차단됨)

2. **두 번째 시도 (Auto-sync 비활성화)**
   ```bash
   # Auto-sync 비활성화
   kubectl patch application titanium-prod -n argocd \
     --type merge -p '{"spec":{"syncPolicy":{"automated":null}}}'
   
   # 롤백 실행
   kubectl rollout undo deployment/prod-user-service-deployment -n titanium-prod
   
   # Auto-sync 재활성화
   kubectl patch application titanium-prod -n argocd \
     --type merge -p '{"spec":{"syncPolicy":{"automated":{"prune":true,"selfHeal":true}}}}'
   ```
   - **결과**: 롤백 성공 (auto-sync 비활성화 시)
   - Auto-sync 재활성화 시 즉시 Git 상태로 되돌아감

### Kubernetes Rollout History
```
REVISION  CHANGE-CAUSE
12        <none>
13        <none>
14        <none> (main-2fd69a0 - v1.1.2)
15        <none> (main-f65f807 - v1.1.1)
16        <none> (undo to rev 14)
17        <none> (undo to rev 15)
```

### 결과
- **결과**: GitOps 환경에서는 제한적으로 작동
- **소요 시간**: 30초-1분 (가장 빠름)
- **Argo CD 동작**:
  - Auto-sync 활성화: kubectl 변경을 즉시 되돌림
  - Auto-sync 비활성화: 롤백 성공하지만 Git과 불일치

### 장점
- 가장 빠른 롤백 방법 (30초 내)
- 간단한 명령어 한 줄로 실행
- Kubernetes 내장 기능 (외부 도구 불필요)

### 단점
- **GitOps 환경에서는 사실상 사용 불가**
- Git 저장소와 완전히 동기화되지 않음
- Argo CD auto-sync에 의해 자동으로 되돌려짐
- 롤백 이력이 Git에 기록되지 않음

### 권장 사용 사례
- **Argo CD가 없는 순수 Kubernetes 환경**
- 테스트 목적의 일시적 롤백
- 긴급 상황에서 auto-sync를 일시 비활성화하고 롤백

### GitOps 환경에서의 제약사항
Argo CD와 같은 GitOps 도구가 활성화된 환경에서는 kubectl rollout undo가 제대로 작동하지 않습니다:
- **Single Source of Truth**: Git이 유일한 진실의 원천
- **Self-Heal**: Argo CD가 수동 변경을 자동으로 되돌림
- **불일치 방지**: Kubernetes 상태를 항상 Git과 동기화

---

## 롤백 방법 비교표

| 항목 | Git revert | Argo CD UI | kubectl rollout undo |
|------|-----------|-----------|---------------------|
| **소요 시간** | 3-4분 | 1-2분 | 30초 |
| **Git 변경** | O | X | X |
| **CI/CD 실행** | O | X | X |
| **추적성** | 매우 높음 (5/5) | 중간 (3/5) | 낮음 (1/5) |
| **GitOps 호환** | 완벽 | 부분적 | 비호환 |
| **검증 단계** | O | X | X |
| **복잡도** | 중간 | 낮음 | 매우 낮음 |
| **프로덕션 사용** | 권장 | 긴급시만 | 비권장 |
| **Argo CD 필요** | No | Yes | No |
| **승인 프로세스** | PR 머지 | UI 클릭 | 없음 |

---

## 권장 사항

### 프로덕션 환경
**Git revert 방식을 강력히 권장합니다.**

이유:
1. 완전한 추적성과 audit trail
2. CI/CD 파이프라인을 통한 검증
3. 팀 리뷰 및 승인 프로세스
4. GitOps 원칙 완벽 준수

### 긴급 상황
**Argo CD UI 롤백 사용 후 Git revert 수행**

절차:
1. Argo CD UI로 즉시 롤백 (1-2분)
2. 서비스 정상 동작 확인
3. Git revert로 정식 롤백 PR 생성
4. 다음 배포 시 Git과 동기화

### GitOps 환경에서 kubectl rollout undo
**사용하지 않는 것을 권장합니다.**

대안:
- Argo CD auto-sync 일시 비활성화 필요
- 롤백 후 반드시 Git revert로 정식 롤백
- 복잡도가 높고 실수 가능성 있음

---

## 테스트 결론

1. **Git revert**: GitOps 환경에서 가장 안전하고 추적 가능한 롤백 방법
2. **Argo CD UI**: 긴급 상황에 유용하지만 반드시 Git revert로 후속 조치 필요
3. **kubectl rollout undo**: GitOps 환경에서는 Argo CD에 의해 자동으로 되돌려져 사실상 사용 불가

GitOps 원칙을 준수하는 환경에서는 **Git이 single source of truth**이므로, 모든 변경사항(롤백 포함)이 Git을 통해 이루어져야 합니다.

---

## 다음 단계

Issue #15의 남은 작업:
- [완료] 1. E2E 테스트 (전체 플로우)
- [완료] 2. 실패 시나리오 테스트
- [완료] 3. 롤백 테스트
- [대기] 4. 성능 최적화
- [대기] 5. 문서화

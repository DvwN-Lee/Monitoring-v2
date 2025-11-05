# Argo CD UI 롤백 가이드

## 현재 배포 히스토리
```
ID  배포 시간              Git Revision  설명
7   2025-10-30 11:45:20   e89e4db       현재 버전 (v1.1.1 롤백)
6   2025-10-30 11:36:20   56d8c24       v1.1.2 배포
5   2025-10-30 09:35:56   f59e199       v1.1.1 배포
4   2025-10-30 09:00:39   dd5c6a9       nginx 프록시 설정
3   2025-10-30 08:32:08   3d38c29       이전 배포
2   2025-10-30 08:28:33   cd705bd       이전 배포
1   2025-10-30 04:21:39   8c80a02       이전 배포
0   2025-10-30 03:01:53   857812c       초기 배포
```

## Argo CD UI 롤백 단계

### 1. Argo CD UI 접속
```bash
kubectl port-forward svc/argocd-server -n argocd 8080:443
```
브라우저에서 https://localhost:8080 접속

### 2. 로그인
- Username: admin
- Password: kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d

### 3. 애플리케이션 선택
- Applications 목록에서 `titanium-prod` 클릭

### 4. History & Rollback 탭 이동
- 상단 메뉴에서 "History and Rollback" 또는 "History" 탭 클릭

### 5. 롤백할 버전 선택
히스토리 목록에서 이전 버전을 선택할 수 있습니다:
- 각 버전은 배포 시간, Git revision, sync 상태를 표시
- "⋮" (세로 점 3개) 메뉴를 클릭하면 "Rollback" 옵션 표시

### 6. 롤백 실행
1. 롤백하고 싶은 버전의 "⋮" 메뉴 클릭
2. "Rollback" 선택
3. 확인 다이얼로그에서 "OK" 클릭

### 7. 배포 모니터링
- 자동으로 Overview 탭으로 이동
- Resource Tree에서 실시간 배포 상태 확인
- 모든 리소스가 다음 상태가 될 때까지 대기:
  - Health: Healthy
  - Sync: Synced

### 8. 롤백 확인
```bash
# 배포된 이미지 버전 확인
kubectl get deployment prod-user-service-deployment -n titanium-prod -o jsonpath='{.spec.template.spec.containers[0].image}'

# Pod 상태 확인
kubectl get pods -n titanium-prod -l app=user-service

# 서비스 상태 확인
curl http://10.0.11.168:31193/stats
```

## 주요 특징

### 장점
- **GUI 기반**: 직관적인 웹 인터페이스
- **시각적 확인**: 배포 히스토리를 한눈에 확인
- **빠른 롤백**: 클릭 몇 번으로 이전 버전으로 복구
- **GitOps 유지**: 롤백도 Git 기반으로 추적 가능

### 주의사항
- Argo CD UI 롤백은 Kubernetes 리소스만 롤백
- Git 저장소의 코드는 변경되지 않음
- 완전한 롤백을 위해서는 Git revert 또는 kubectl rollout undo 사용 권장

## 롤백 시나리오 비교

| 방법 | Git 변경 | 자동 CI/CD | 롤백 속도 | 추적성 |
|------|----------|------------|-----------|--------|
| Git revert | O | O | 느림 (5-6분) | 최고 |
| Argo CD UI | X | X | 빠름 (1분) | 중간 |
| kubectl rollout | X | X | 매우 빠름 (30초) | 낮음 |


# GitOps with Argo CD 설정 가이드

## 개요

Titanium 프로젝트는 Argo CD를 사용하여 GitOps 방식의 지속적 배포(Continuous Deployment)를 구현합니다. 이 가이드는 Argo CD 설정 및 사용 방법을 설명합니다.

## 아키텍처

```
GitHub (main 브랜치)
    ↓
CI Pipeline (GitHub Actions)
    ↓
Docker Hub (이미지 빌드 & 푸시)
    ↓
CD Pipeline (GitHub Actions)
    ↓
K8s Manifests 업데이트 (kustomization.yaml)
    ↓
Argo CD (자동 감지 & 동기화)
    ↓
Kubernetes Cluster (배포)
```

## Argo CD 설치

### 1. Argo CD 설치 (이미 완료됨)

```bash
# Namespace 생성
kubectl create namespace argocd

# Argo CD 설치
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# 설치 확인
kubectl get pods -n argocd
```

### 2. Argo CD UI 접근 설정

```bash
# 서비스를 NodePort로 노출
kubectl patch svc argocd-server -n argocd -p '{"spec": {"type": "NodePort"}}'

# NodePort 확인
kubectl get svc argocd-server -n argocd
# 출력 예: 80:31619/TCP,443:30547/TCP

# 초기 admin 비밀번호 확인
kubectl get secret argocd-initial-admin-secret -n argocd -o jsonpath="{.data.password}" | base64 -d && echo
```

### 3. Argo CD 로그인

**접속 정보:**
- **URL**: https://10.0.11.168:30547 (HTTPS) 또는 http://10.0.11.168:31619 (HTTP)
- **Username**: `admin`
- **Password**: (위에서 확인한 초기 비밀번호)

**비밀번호 변경 (권장):**
```bash
# Argo CD CLI 설치 (선택사항)
brew install argocd  # macOS
# 또는
curl -sSL -o argocd https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64
chmod +x argocd
sudo mv argocd /usr/local/bin/

# 로그인
argocd login 10.0.11.168:30547 --insecure

# 비밀번호 변경
argocd account update-password
```

## Application 배포

### 1. Application Manifest 적용

```bash
# Titanium Application 배포
kubectl apply -f argocd/applications/titanium-app.yaml

# Application 상태 확인
kubectl get application -n argocd
```

### 2. Argo CD UI에서 확인

1. Argo CD UI에 로그인
2. Applications 목록에서 `titanium-prod` 확인
3. 애플리케이션 상태:
   - **Healthy**: 모든 리소스가 정상
   - **Synced**: Git과 클러스터가 동기화됨
   - **Progressing**: 배포 진행 중

### 3. 수동 동기화 (필요시)

Argo CD UI에서:
1. `titanium-prod` 애플리케이션 클릭
2. **SYNC** 버튼 클릭
3. **SYNCHRONIZE** 버튼 클릭

또는 CLI로:
```bash
argocd app sync titanium-prod
```

## CI/CD 파이프라인 작동 방식

### 1. CI Pipeline (이미지 빌드)

```yaml
Pull Request → main 브랜치 머지
    ↓
GitHub Actions CI Pipeline 실행
    ↓
변경된 서비스 감지
    ↓
Docker 이미지 빌드 (멀티 플랫폼)
    ↓
Trivy 보안 스캔
    ↓
Docker Hub에 푸시 (태그: main-{short-sha}, latest)
```

### 2. CD Pipeline (Manifest 업데이트)

```yaml
CI Pipeline 완료
    ↓
GitHub Actions CD Pipeline 실행
    ↓
kustomization.yaml 업데이트 (이미지 태그 변경)
    ↓
변경사항 커밋 & 푸시 ([skip ci] 플래그 사용)
    ↓
Argo CD가 자동으로 변경 감지
    ↓
클러스터에 자동 배포
```

### 3. 자동 배포 프로세스

Argo CD는 다음과 같이 자동으로 배포합니다:

1. **Polling**: Git 저장소를 주기적으로 확인 (기본: 3분마다)
2. **Diff**: Git의 desired state와 클러스터의 actual state 비교
3. **Sync**: 차이가 있으면 자동으로 동기화
4. **Health Check**: 배포된 리소스의 상태 확인

## 이미지 태그 전략

### CI에서 생성되는 태그

- **Pull Request**: `pr-{pr-number}`
  - 예: `dongju101/user-service:pr-42`
  - Docker Hub에 푸시되지 않음 (빌드만)

- **Main 브랜치**: `main-{short-sha}`, `latest`
  - 예: `dongju101/user-service:main-abc1234`
  - 예: `dongju101/user-service:latest`

### CD에서 업데이트되는 태그

CD pipeline은 `kustomization.yaml`의 이미지 태그를 `main-{short-sha}`로 업데이트합니다:

```yaml
images:
  - name: dongju101/user-service
    newTag: main-abc1234  # ← CD pipeline이 자동 업데이트
```

## Argo CD Application 설정 상세

### syncPolicy 설정

```yaml
syncPolicy:
  automated:
    prune: true        # Git에서 삭제된 리소스를 클러스터에서도 삭제
    selfHeal: true     # 클러스터의 리소스가 변경되면 자동으로 Git 상태로 복구
    allowEmpty: false  # 빈 커밋은 무시
```

### 주요 옵션

- **prune**: Git에서 삭제된 리소스를 클러스터에서도 자동 삭제
- **selfHeal**: 누군가 kubectl로 직접 수정한 내용을 Git 상태로 되돌림
- **CreateNamespace**: 네임스페이스가 없으면 자동 생성
- **ServerSideApply**: 서버 측 Apply 사용 (대규모 리소스에 유용)

## 모니터링 및 관리

### 1. Application 상태 확인

```bash
# CLI로 상태 확인
kubectl get application -n argocd titanium-prod

# 상세 정보 확인
kubectl describe application -n argocd titanium-prod

# Argo CD CLI로 확인
argocd app get titanium-prod
```

### 2. 동기화 히스토리 확인

Argo CD UI에서:
1. `titanium-prod` 애플리케이션 클릭
2. **History and Rollback** 탭 확인
3. 각 배포의 Git 커밋, 시간, 상태 확인

### 3. 로그 확인

```bash
# Argo CD Application Controller 로그
kubectl logs -n argocd -l app.kubernetes.io/name=argocd-application-controller

# Argo CD Server 로그
kubectl logs -n argocd -l app.kubernetes.io/name=argocd-server
```

## 롤백

### 1. UI에서 롤백

1. Argo CD UI에서 `titanium-prod` 클릭
2. **History and Rollback** 탭
3. 이전 버전 선택
4. **ROLLBACK** 버튼 클릭

### 2. CLI로 롤백

```bash
# 이전 버전으로 롤백
argocd app rollback titanium-prod <revision-id>

# 또는 Git에서 직접 revert
git revert <commit-sha>
git push origin main
# Argo CD가 자동으로 이전 상태로 배포
```

### 3. Kubernetes에서 직접 롤백

```bash
# Deployment 롤백 (긴급 상황)
kubectl rollout undo deployment -n titanium-prod prod-user-service-deployment

# 주의: Argo CD의 selfHeal이 활성화되어 있으면 다시 Git 상태로 복구됨
# 영구적인 롤백은 Git을 통해 수행해야 함
```

## 트러블슈팅

### Application이 OutOfSync 상태

**원인:**
- Git의 manifest와 클러스터의 상태가 다름
- 누군가 kubectl로 직접 수정

**해결:**
```bash
# 수동 동기화
argocd app sync titanium-prod

# 또는 UI에서 SYNC 버튼 클릭
```

### Application이 Degraded 상태

**원인:**
- Pod가 CrashLoopBackOff
- 이미지를 가져올 수 없음
- ConfigMap/Secret 누락

**해결:**
```bash
# Pod 로그 확인
kubectl logs -n titanium-prod <pod-name>

# Pod 이벤트 확인
kubectl describe pod -n titanium-prod <pod-name>

# Application 이벤트 확인
kubectl describe application -n argocd titanium-prod
```

### 자동 동기화가 작동하지 않음

**확인 사항:**
1. Application의 `syncPolicy.automated` 설정 확인
2. Git 저장소 접근 권한 확인
3. Argo CD가 Git을 폴링하는 주기 확인 (기본 3분)

```bash
# Application 설정 확인
kubectl get application -n argocd titanium-prod -o yaml

# 수동으로 강제 새로고침
argocd app get titanium-prod --refresh
```

### CD Pipeline이 manifest를 업데이트하지 않음

**확인 사항:**
1. CI Pipeline이 성공적으로 완료되었는지 확인
2. GitHub Actions의 CD workflow 로그 확인
3. 변경된 서비스가 있는지 확인

```bash
# GitHub Actions에서 workflow 로그 확인
# Repository → Actions → CD Pipeline
```

## 보안 고려사항

### 1. Argo CD 비밀번호 변경

초기 비밀번호는 반드시 변경하세요:
```bash
argocd account update-password
```

### 2. RBAC 설정

프로덕션 환경에서는 RBAC을 설정하여 권한을 제한하세요:
```bash
# argocd-rbac-cm ConfigMap 수정
kubectl edit configmap argocd-rbac-cm -n argocd
```

### 3. Private Repository 설정

Private 저장소를 사용하는 경우:
```bash
# SSH 키 또는 HTTPS 토큰 등록
argocd repo add https://github.com/your-org/repo.git --username <username> --password <token>
```

## 다음 단계

Argo CD 설정이 완료되었다면:

1. [E2E 테스트 가이드](./e2e-testing.md) - 배포 후 테스트
2. [롤백 가이드](./rollback-guide.md) - 배포 롤백 절차
3. [모니터링 설정](./monitoring-setup.md) - Prometheus & Grafana 설정

## 참고 자료

- [Argo CD 공식 문서](https://argo-cd.readthedocs.io/)
- [GitOps란?](https://www.gitops.tech/)
- [Kustomize 문서](https://kustomize.io/)
- [Argo CD Best Practices](https://argo-cd.readthedocs.io/en/stable/user-guide/best_practices/)

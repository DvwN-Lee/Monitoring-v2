# Week 2 트러블슈팅 가이드 - CI/CD 파이프라인

이 문서는 Week 2 (CI/CD 파이프라인) 구축 중 발생할 수 있는 문제들과 해결 방법을 정리합니다.

## 목차
- [GitHub Actions 관련](#github-actions-관련)
- [Docker 빌드 관련](#docker-빌드-관련)
- [Argo CD 관련](#argo-cd-관련)
- [Rollback 관련](#rollback-관련)
- [일반적인 디버깅 명령어](#일반적인-디버깅-명령어)
- [추가 리소스](#추가-리소스)

---

## GitHub Actions 관련

### 1.1 Secrets 설정 문제

**문제**: DOCKERHUB_USERNAME, DOCKERHUB_TOKEN 미설정으로 빌드 실패

**증상**:
```
Error: Username and password required
Error response from daemon: login attempt to https://registry-1.docker.io/v2/ failed with status: 401 Unauthorized
```

**원인**: GitHub Repository Secrets에 Docker Hub 인증 정보가 설정되지 않음

**해결 방법**:
1. GitHub Repository → Settings → Secrets and variables → Actions
2. New repository secret 클릭
3. 다음 secrets 추가:
   - `DOCKERHUB_USERNAME`: Docker Hub 사용자명
   - `DOCKERHUB_TOKEN`: Docker Hub Access Token

**검증**:
```bash
gh secret list
```

---

### 1.2 Workflow 권한 문제

**문제**: GITHUB_TOKEN 권한 부족으로 PR comment 작성 실패

**증상**:
```
Error: Resource not accessible by integration
HttpError: Resource not accessible by integration
```

**원인**: Workflow에 필요한 권한이 부여되지 않음

**해결 방법**:

`.github/workflows/ci.yml`에 permissions 추가:
```yaml
permissions:
  contents: read
  security-events: write
  pull-requests: write  # PR comment를 위해 필요
```

**참고**: Repository Settings → Actions → General → Workflow permissions에서 "Read and write permissions" 활성화 필요

---

### 1.3 Trivy 스캔 중복 실행

**문제**: PR과 Main 브랜치에서 동일한 이미지를 각각 스캔하여 CI 시간 증가

**증상**:
- PR 빌드: 3-4분
- Main 빌드: 3-4분
- 총 시간: 6-8분 (불필요한 중복)

**원인**: PR과 Main 모두에서 Trivy 스캔 실행

**해결 방법**:

최적화된 CI 전략:
```yaml
# PR에서는 이미지만 빌드 (스캔 X)
- name: Build Docker image (PR)
  if: github.event_name == 'pull_request'
  uses: docker/build-push-action@v5
  with:
    push: false
    cache-from: type=gha
    cache-to: type=gha,mode=max

# Main에서만 빌드 + 푸시 + 스캔
- name: Build and Push Docker image (Main)
  if: github.event_name == 'push' && github.ref == 'refs/heads/main'
  uses: docker/build-push-action@v5
  with:
    push: true
    cache-from: type=gha
```

**효과**: 총 CI 시간을 6-8분 → 3-4분으로 단축

---

## Docker 빌드 관련

### 2.1 멀티플랫폼 빌드 시간

**문제**: linux/amd64와 linux/arm64 동시 빌드로 시간 2배 이상 증가

**증상**:
- 단일 플랫폼: 1-2분
- 멀티 플랫폼: 3-5분

**원인**: 크로스 플랫폼 빌드는 QEMU 에뮬레이션 사용

**해결 방법**:

**옵션 1**: 필요한 플랫폼만 빌드
```yaml
platforms: linux/amd64  # 단일 플랫폼
```

**옵션 2**: 빌드 캐시 최적화
```yaml
- name: Set up Docker Buildx
  uses: docker/setup-buildx-action@v3
  with:
    buildkitd-flags: --allow-insecure-entitlement network.host

- name: Build
  uses: docker/build-push-action@v5
  with:
    cache-from: type=gha
    cache-to: type=gha,mode=max
```

---

### 2.2 Go 모듈 다운로드 실패

**문제**: go.mod의 require 버전이 실제 코드와 불일치

**증상**:
```
go: github.com/prometheus/client_golang@v1.20.5:
module github.com/prometheus/client_golang: Get "https://proxy.golang.org/...": dial tcp: lookup proxy.golang.org: no such host
```

**원인**:
1. go.mod 파일이 업데이트되지 않음
2. 네트워크 문제
3. 모듈이 존재하지 않음

**해결 방법**:

```bash
# 로컬에서 실행
cd api-gateway
go mod tidy
go mod verify

# 커밋
git add go.mod go.sum
git commit -m "fix: update go.mod dependencies"
```

**Dockerfile에서 검증**:
```dockerfile
# go.sum 파일도 반드시 포함
COPY go.mod go.sum ./
RUN go mod download
```

---

### 2.3 Python 의존성 설치 실패

**문제**: requirements.txt의 패키지 버전 충돌

**증상**:
```
ERROR: Cannot install package-a==1.0 and package-b==2.0 because these package versions have conflicting dependencies.
```

**원인**: 패키지 간 의존성 충돌

**해결 방법**:

```bash
# 가상환경에서 테스트
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 충돌 해결 후 freeze
pip freeze > requirements.txt
```

**best practice**:
```txt
# 메이저 버전만 고정
prometheus-client>=0.19,<1.0
prometheus-fastapi-instrumentator>=6.0,<7.0
```

---

## Argo CD 관련

### 3.1 동기화 지연

**문제**: kustomization.yaml의 이미지 태그 업데이트 후 즉시 반영되지 않음

**증상**:
- CD 파이프라인 완료
- Git에 새 이미지 태그 커밋됨
- 하지만 Pod가 이전 이미지로 실행 중

**원인**: Argo CD의 자동 동기화 주기 (기본 3분)

**해결 방법**:

**옵션 1**: 수동 동기화
```bash
# CLI
kubectl patch application titanium-prod -n argocd \
  --type merge \
  -p '{"operation":{"initiatedBy":{"username":"admin"},"sync":{"revision":"HEAD"}}}'

# 또는 Argo CD UI에서 "Sync" 버튼 클릭
```

**옵션 2**: Webhook 설정 (즉시 동기화)
```yaml
# argocd/application.yaml
spec:
  source:
    repoURL: https://github.com/your-org/your-repo
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
    - CreateNamespace=true
```

**검증**:
```bash
kubectl get pods -n titanium-prod -l app=user-service -o jsonpath='{.items[0].spec.containers[0].image}'
```

---

### 3.2 Image pull 실패

**문제**: Docker Hub rate limit 초과

**증상**:
```
Failed to pull image "dongju101/user-service:main-abc123":
rpc error: code = Unknown desc = Error response from daemon:
toomanyrequests: You have reached your pull rate limit.
You may increase the limit by authenticating and upgrading: https://www.docker.com/increase-rate-limit
```

**원인**:
- 익명 사용자: 시간당 100회
- 인증된 사용자: 시간당 200회 (무료)
- 빈번한 Pod 재시작 또는 노드 추가

**해결 방법**:

**옵션 1**: Docker Hub 인증
```bash
kubectl create secret docker-registry dockerhub-secret \
  --docker-server=docker.io \
  --docker-username=YOUR_USERNAME \
  --docker-password=YOUR_PASSWORD \
  -n titanium-prod

# Deployment에 추가
spec:
  template:
    spec:
      imagePullSecrets:
      - name: dockerhub-secret
```

**옵션 2**: Image pull policy 최적화
```yaml
spec:
  template:
    spec:
      containers:
      - name: app
        imagePullPolicy: IfNotPresent  # Always 대신 사용
```

**옵션 3**: Private registry 사용

---

### 3.3 GitOps 불일치

**문제**: kubectl로 직접 수정 시 Argo CD가 계속 원래대로 되돌림

**증상**:
```bash
# kubectl edit로 수정
kubectl edit deployment prod-user-service -n titanium-prod

# 잠시 후 다시 원래대로 복구됨
```

**원인**: Argo CD의 self-heal 기능이 Git 상태로 복구

**해결 방법**:

**올바른 방법**: Git을 통한 변경
```bash
# 1. Git에서 수정
vi k8s-manifests/overlays/solid-cloud/patches/user-service-patch.yaml

# 2. 커밋 및 푸시
git add .
git commit -m "update: user-service replicas"
git push

# 3. Argo CD가 자동으로 동기화 (또는 수동 sync)
```

**긴급 상황**: self-heal 일시 비활성화
```bash
kubectl patch application titanium-prod -n argocd \
  --type merge \
  -p '{"spec":{"syncPolicy":{"automated":{"selfHeal":false}}}}'
```

---

## Rollback 관련

### 4.1 Git revert vs kubectl rollout undo

**문제**: kubectl rollout undo는 GitOps 환경에서 권장되지 않음

**비교**:

| 방법 | 장점 | 단점 | GitOps 호환 |
|------|------|------|-------------|
| git revert | Git 히스토리 보존, 추적 가능 | 3-4분 소요 | [권장] |
| Argo CD UI | 빠름 (1-2분) | Git 불일치 | [주의] |
| kubectl rollout undo | 가장 빠름 (30초) | Argo CD가 되돌림 | [비권장] |

**권장 방법**: Git revert
```bash
# 1. 문제 커밋 확인
git log --oneline

# 2. Revert
git revert abc1234

# 3. 푸시
git push

# 4. Argo CD 동기화 대기 (또는 수동 sync)
```

**긴급 상황**: Argo CD UI
1. Applications → titanium-prod
2. History 탭
3. 이전 revision 선택
4. Sync

---

### 4.2 Deployment history 부족

**문제**: revision-history-limit이 작아서 롤백 불가

**증상**:
```bash
kubectl rollout undo deployment/prod-user-service -n titanium-prod

error: unable to find specified revision 5 in history
```

**원인**: `spec.revisionHistoryLimit` 기본값이 10

**해결 방법**:

```yaml
# k8s-manifests/base/user-service-deployment.yaml
spec:
  revisionHistoryLimit: 20  # 기본 10 → 20으로 증가
```

**검증**:
```bash
kubectl rollout history deployment/prod-user-service -n titanium-prod
```

---

## 일반적인 디버깅 명령어

### 로그 확인
```bash
# Pod 로그
kubectl logs -n NAMESPACE POD_NAME

# 이전 컨테이너 로그 (재시작된 경우)
kubectl logs -n NAMESPACE POD_NAME --previous

# 특정 컨테이너 로그 (multi-container pod)
kubectl logs -n NAMESPACE POD_NAME -c CONTAINER_NAME

# 실시간 로그
kubectl logs -n NAMESPACE POD_NAME -f
```

### 리소스 확인
```bash
# Pod 상태
kubectl get pods -n NAMESPACE -o wide

# Pod 상세 정보
kubectl describe pod -n NAMESPACE POD_NAME

# Events 확인
kubectl get events -n NAMESPACE --sort-by='.lastTimestamp'

# 리소스 사용량
kubectl top pods -n NAMESPACE
kubectl top nodes
```

### 네트워크 디버깅
```bash
# Service 확인
kubectl get svc -n NAMESPACE

# Endpoint 확인
kubectl get endpoints -n NAMESPACE

# 네트워크 테스트
kubectl run -it --rm debug --image=curlimages/curl:latest --restart=Never -- sh
```

### ConfigMap/Secret 확인
```bash
# ConfigMap 내용
kubectl get configmap -n NAMESPACE NAME -o yaml

# Secret 내용 (base64 decode)
kubectl get secret -n NAMESPACE NAME -o jsonpath='{.data.KEY}' | base64 -d
```

---

## 추가 리소스

### 공식 문서
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Docker Build Documentation](https://docs.docker.com/build/)
- [Argo CD Documentation](https://argo-cd.readthedocs.io/)
- [Argo CD Troubleshooting](https://argo-cd.readthedocs.io/en/stable/operator-manual/troubleshooting/)

### 유용한 도구
- [Lens](https://k8slens.dev/) - Kubernetes IDE
- [k9s](https://k9scli.io/) - Terminal UI
- [stern](https://github.com/stern/stern) - Multi pod log tailing
- [kubectx/kubens](https://github.com/ahmetb/kubectx) - Context/namespace 전환

---

**작성일**: 2025-10-31
**작성자**: 이동주
**버전**: 1.0

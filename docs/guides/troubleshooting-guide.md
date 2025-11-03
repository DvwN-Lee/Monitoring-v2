# CI/CD 파이프라인 트러블슈팅 가이드

## 목차
1. [GitHub Actions CI 문제](#github-actions-ci-문제)
2. [Docker 빌드 문제](#docker-빌드-문제)
3. [CD 파이프라인 문제](#cd-파이프라인-문제)
4. [Argo CD 문제](#argo-cd-문제)
5. [Kubernetes 배포 문제](#kubernetes-배포-문제)
6. [네트워크 및 서비스 문제](#네트워크-및-서비스-문제)
7. [일반적인 GitOps 문제](#일반적인-gitops-문제)

---

## GitHub Actions CI 문제

### 문제 1: CI가 트리거되지 않음

**증상**
- PR 생성 또는 push 후 CI 워크플로우가 실행되지 않음

**원인**
1. paths 필터가 변경된 파일과 맞지 않음
2. 브랜치가 트리거 조건과 맞지 않음
3. 워크플로우 파일에 문법 오류 있음

**해결 방법**
```bash
# 1. 변경된 파일 경로 확인
git diff --name-only origin/main

# 2. 워크플로우 파일의 paths 필터 확인
cat .github/workflows/ci.yml | grep -A 10 "paths:"

# 3. GitHub Actions 탭에서 워크플로우 상태 확인
# 워크플로우가 비활성화되어 있는지 확인

# 4. 워크플로우 파일 문법 검증
# https://rhysd.github.io/actionlint/
actionlint .github/workflows/ci.yml
```

**예방**
- `.github/workflows/` 경로를 paths에 포함하여 워크플로우 변경 시에도 CI 실행

---

### 문제 2: Docker Hub 로그인 실패

**증상**
```
Error: Error response from daemon: Get "https://registry-1.docker.io/v2/": 
unauthorized: incorrect username or password
```

**원인**
1. DOCKER_HUB_TOKEN 시크릿이 설정되지 않음
2. 토큰이 만료됨
3. 토큰 권한이 불충분함

**해결 방법**
```bash
# 1. GitHub 리포지토리 설정에서 시크릿 확인
# Settings > Secrets and variables > Actions > Repository secrets
# DOCKER_HUB_TOKEN이 존재하는지 확인

# 2. Docker Hub에서 새 Access Token 생성
# https://hub.docker.com/settings/security
# Permissions: Read, Write, Delete

# 3. GitHub 시크릿 업데이트
# Settings > Secrets and variables > Actions > Update secret
```

**예방**
- Docker Hub Access Token에 만료 기간 설정하지 않기
- 토큰 생성 시 Read, Write 권한 부여
- 정기적으로 토큰 갱신 (보안 강화 시)

---

### 문제 3: Trivy 스캔 시간 초과

**증상**
- Trivy 스캔이 매우 오래 걸리거나 timeout 발생
- CI 시간이 5분 이상 소요

**원인**
1. Trivy 데이터베이스 다운로드 실패
2. 이미지 크기가 너무 큼
3. 중복 스캔 실행

**해결 방법**
```yaml
# Trivy 캐시 사용
- name: Run Trivy vulnerability scanner
  uses: aquasecurity/trivy-action@master
  with:
    cache-dir: ~/.trivy
    timeout: 10m

# GitHub Actions Cache 활용
- name: Cache Trivy DB
  uses: actions/cache@v3
  with:
    path: ~/.trivy
    key: trivy-db-${{ github.run_id }}
    restore-keys: |
      trivy-db-
```

**최적화**
- Trivy 스캔을 한 번만 실행하고 결과를 재사용
- 이미지 크기 최소화 (멀티스테이지 빌드)
- Critical 및 High 취약점만 스캔

---

### 문제 4: Matrix 빌드 중 일부만 실패

**증상**
- 여러 서비스 중 일부만 빌드 실패
- 다른 서비스는 정상 빌드

**원인**
1. 특정 서비스의 Dockerfile 오류
2. 의존성 설치 실패
3. 파일 경로 문제

**해결 방법**
```bash
# 1. 실패한 서비스의 로그 확인
gh run view [RUN_ID] --log | grep -A 20 "Build and Scan ([서비스명])"

# 2. 로컬에서 Docker 빌드 재현
cd [서비스명]
docker build -t test:local .

# 3. 빌드 컨텍스트 확인
docker build --progress=plain -t test:local . 2>&1 | tee build.log
```

**예방**
- 로컬에서 Docker 빌드 테스트 후 커밋
- Dockerfile에 명확한 에러 메시지 추가
- 의존성 버전 고정 (requirements.txt, package.json)

---

## Docker 빌드 문제

### 문제 5: Docker 빌드 캐시 미작동

**증상**
- 매번 전체 레이어를 다시 빌드
- 빌드 시간이 예상보다 오래 걸림

**원인**
1. Dockerfile 레이어 순서 최적화 안 됨
2. GitHub Actions Cache 설정 오류
3. 캐시 키가 자주 변경됨

**해결 방법**
```dockerfile
# 잘못된 예
FROM python:3.11-slim
COPY . .
RUN pip install -r requirements.txt  # 코드 변경 시 매번 재실행

# 올바른 예
FROM python:3.11-slim
COPY requirements.txt .
RUN pip install -r requirements.txt  # requirements.txt 변경 시만 재실행
COPY . .
```

```yaml
# GitHub Actions에서 캐시 설정 확인
- uses: docker/build-push-action@v5
  with:
    cache-from: type=gha
    cache-to: type=gha,mode=max  # mode=max 중요!
```

**최적화**
- 자주 변경되지 않는 파일을 먼저 COPY
- .dockerignore 파일 활용
- 멀티스테이지 빌드 사용

---

### 문제 6: Multi-platform 빌드 느림

**증상**
- main 브랜치 빌드가 5분 이상 소요
- arm64 플랫폼 빌드가 특히 느림

**원인**
- 크로스 플랫폼 빌드는 QEMU 에뮬레이션 사용
- arm64 빌드는 amd64보다 2-3배 느림

**해결 방법**
```yaml
# 옵션 1: 필요한 플랫폼만 빌드
platforms: linux/amd64  # arm64 제거

# 옵션 2: 조건부 빌드
platforms: ${{ github.ref == 'refs/tags/v*' && 'linux/amd64,linux/arm64' || 'linux/amd64' }}

# 옵션 3: 별도 워크플로우로 분리
# release 워크플로우에서만 multi-platform 빌드
```

**권장 사항**
- 프로덕션 환경이 amd64만 사용한다면 arm64 빌드 제거
- 릴리스 태그 시에만 multi-platform 빌드 수행

---

## CD 파이프라인 문제

### 문제 7: CD가 Git push 실패 (403 Forbidden)

**증상**
```
remote: Permission to DvwN-Lee/Monitoring-v2.git denied
fatal: unable to access: The requested URL returned error: 403
```

**원인**
1. workflow_run 트리거는 기본적으로 read-only 권한
2. GitHub 리포지토리 설정이 제한적

**해결 방법**
```yaml
# .github/workflows/cd.yml에 권한 추가
permissions:
  contents: write  # 필수!

# GitHub 리포지토리 설정 확인
# Settings > Actions > General > Workflow permissions
# "Read and write permissions" 선택
```

**확인**
```bash
# CD 워크플로우 로그에서 권한 확인
gh run view [CD_RUN_ID] --log | grep -i "permission"
```

---

### 문제 8: kustomization.yaml 업데이트 안 됨

**증상**
- CD는 성공하지만 이미지 태그가 업데이트되지 않음
- Argo CD가 이전 이미지를 계속 사용

**원인**
1. yq 명령어 오류
2. 잘못된 파일 경로
3. Git conflict

**해결 방법**
```bash
# 1. 로컬에서 yq 명령어 테스트
yq eval '.images[] | select(.name == "dongju101/user-service") | .newTag = "main-abc123"' \
  k8s-manifests/overlays/solid-cloud/kustomization.yaml

# 2. CD 워크플로우 로그에서 실제 실행된 명령어 확인
gh run view [CD_RUN_ID] --log | grep "yq eval"

# 3. Git 히스토리 확인
git log --oneline k8s-manifests/overlays/solid-cloud/kustomization.yaml
```

**예방**
- yq 명령어에 -i (in-place) 옵션 사용
- 변경 전후 diff 출력하여 확인
- CI/CD 파이프라인에 검증 단계 추가

---

## Argo CD 문제

### 문제 9: Argo CD가 Git 변경사항을 감지하지 못함

**증상**
- CD가 성공했지만 Argo CD가 동기화하지 않음
- kustomization.yaml이 업데이트되었는데 배포되지 않음

**원인**
1. Argo CD polling 주기 (기본 3분)
2. Git revision이 올바르지 않음
3. Argo CD Application 설정 오류

**해결 방법**
```bash
# 1. 수동으로 Argo CD 동기화 트리거
kubectl patch application titanium-prod -n argocd \
  --type merge \
  -p '{"metadata":{"annotations":{"argocd.argoproj.io/refresh":"hard"}}}'

# 2. Argo CD Application 상태 확인
kubectl get application titanium-prod -n argocd -o yaml

# 3. Git 저장소 연결 확인
kubectl get application titanium-prod -n argocd -o jsonpath='{.status.sync.revision}'

# 4. Argo CD 로그 확인
kubectl logs -n argocd deployment/argocd-application-controller | grep titanium-prod
```

**예방**
- GitHub Webhook 설정으로 즉시 동기화
- polling 주기 단축 (1분)
- auto-sync 활성화 확인

---

### 문제 10: Argo CD Out of Sync 상태

**증상**
- Argo CD UI에서 "OutOfSync" 표시
- Git과 Kubernetes 상태가 다름

**원인**
1. kubectl로 수동 변경
2. Kubernetes Admission Webhook이 리소스 수정
3. Kustomize 빌드 오류

**해결 방법**
```bash
# 1. Diff 확인
kubectl get application titanium-prod -n argocd -o yaml | grep -A 20 "status:"

# 2. Desired State와 Live State 비교
# Argo CD UI > App Details > Diff 탭

# 3. 강제 동기화
kubectl patch application titanium-prod -n argocd \
  --type merge \
  -p '{"operation":{"sync":{"syncOptions":["Replace=true"]}}}'

# 4. selfHeal 활성화로 자동 복구
kubectl patch application titanium-prod -n argocd \
  --type merge \
  -p '{"spec":{"syncPolicy":{"automated":{"selfHeal":true}}}}'
```

**예방**
- kubectl 수동 변경 금지
- selfHeal 활성화
- Git을 single source of truth로 유지

---

### 문제 11: Argo CD Health Status "Degraded"

**증상**
- 배포는 완료되었지만 Health Status가 "Degraded"
- 일부 Pod가 Ready 상태가 아님

**원인**
1. Pod 헬스체크 실패
2. 이미지 pull 실패
3. 리소스 부족

**해결 방법**
```bash
# 1. Pod 상태 확인
kubectl get pods -n titanium-prod -l app=[서비스명]

# 2. Pod 이벤트 확인
kubectl describe pod [POD_NAME] -n titanium-prod

# 3. Pod 로그 확인
kubectl logs [POD_NAME] -n titanium-prod

# 4. 리소스 사용량 확인
kubectl top pods -n titanium-prod
kubectl top nodes
```

**일반적인 원인과 해결**
- ImagePullBackOff: 이미지 태그 확인, Docker Hub 로그인
- CrashLoopBackOff: 애플리케이션 로그 확인, 환경변수 확인
- Pending: 리소스 부족, PVC 바인딩 실패

---

## Kubernetes 배포 문제

### 문제 12: Pod가 CrashLoopBackOff 상태

**증상**
- Pod가 시작되자마자 종료되고 재시작 반복
- kubectl get pods에서 RESTARTS 수가 계속 증가

**원인**
1. 애플리케이션 시작 오류
2. 잘못된 환경변수
3. 의존 서비스 연결 실패

**해결 방법**
```bash
# 1. Pod 로그 확인
kubectl logs [POD_NAME] -n titanium-prod --previous

# 2. 환경변수 확인
kubectl exec [POD_NAME] -n titanium-prod -- env | sort

# 3. ConfigMap 및 Secret 확인
kubectl get configmap -n titanium-prod
kubectl get secret -n titanium-prod

# 4. 의존 서비스 연결 테스트
kubectl exec [POD_NAME] -n titanium-prod -- curl http://prod-postgresql-service:5432
```

**일반적인 원인**
- PostgreSQL 연결 실패: POSTGRES_HOST 확인
- Redis 연결 실패: REDIS_HOST 확인
- 포트 충돌: SERVICE_PORT 중복 확인

---

### 문제 13: ImagePullBackOff 오류

**증상**
```
Failed to pull image "dongju101/user-service:main-abc123": 
rpc error: code = Unknown desc = Error response from daemon: 
manifest for dongju101/user-service:main-abc123 not found
```

**원인**
1. 이미지 태그가 존재하지 않음
2. Docker Hub에 이미지 푸시 실패
3. 이미지 이름 오타

**해결 방법**
```bash
# 1. Docker Hub에서 이미지 확인
docker pull dongju101/user-service:main-abc123

# 2. kustomization.yaml에서 태그 확인
cat k8s-manifests/overlays/solid-cloud/kustomization.yaml | grep -A 2 "user-service"

# 3. GitHub Actions CI 로그에서 푸시 확인
gh run list --workflow=ci.yml --limit 1
gh run view [RUN_ID] --log | grep "push\|tag"

# 4. 임시로 이전 태그로 수정
kubectl set image deployment/prod-user-service-deployment \
  user-service-container=dongju101/user-service:main-[이전SHA] \
  -n titanium-prod
```

**예방**
- CI가 성공한 후에만 CD 실행
- 이미지 푸시 후 pull 테스트
- Deployment에 imagePullPolicy: IfNotPresent 설정

---

### 문제 14: Service가 Pod를 찾지 못함

**증상**
- Service는 생성되었지만 Endpoint가 없음
- `kubectl get endpoints [SERVICE_NAME]`에서 ENDPOINTS가 비어있음

**원인**
1. Service selector와 Pod label 불일치
2. Pod가 Ready 상태가 아님
3. Port 매핑 오류

**해결 방법**
```bash
# 1. Service selector 확인
kubectl get service prod-user-service -n titanium-prod -o yaml | grep -A 5 "selector:"

# 2. Pod label 확인
kubectl get pods -n titanium-prod -l app=user-service --show-labels

# 3. Endpoint 확인
kubectl get endpoints prod-user-service -n titanium-prod

# 4. Port 매핑 확인
kubectl describe service prod-user-service -n titanium-prod | grep -A 3 "Port:"
```

**수정 방법**
```yaml
# Service의 selector가 Pod의 label과 일치해야 함
# Service:
selector:
  app: user-service
  
# Pod:
labels:
  app: user-service
```

---

## 네트워크 및 서비스 문제

### 문제 15: NodePort 서비스에 외부에서 접근 안 됨

**증상**
- kubectl get svc에서 NodePort 확인되지만 브라우저에서 접근 안 됨
- curl로도 연결 실패

**원인**
1. 방화벽 규칙
2. 잘못된 노드 IP
3. Service type이 ClusterIP로 설정

**해결 방법**
```bash
# 1. Service type 확인
kubectl get service [SERVICE_NAME] -n titanium-prod -o yaml | grep "type:"

# 2. NodePort 번호 확인
kubectl get service [SERVICE_NAME] -n titanium-prod -o jsonpath='{.spec.ports[0].nodePort}'

# 3. 노드 IP 확인
kubectl get nodes -o wide

# 4. 연결 테스트
curl http://[NODE_IP]:[NODE_PORT]/

# 5. Pod가 실행 중인 노드 확인
kubectl get pods -n titanium-prod -o wide
```

**Kustomize patch로 NodePort 설정**
```yaml
# patches/service-nodeport-patch.yaml
apiVersion: v1
kind: Service
metadata:
  name: [SERVICE_NAME]
spec:
  type: NodePort
  ports:
  - port: [PORT]
    nodePort: [NODE_PORT]
```

---

## 일반적인 GitOps 문제

### 문제 17: kubectl 수동 변경이 자동으로 되돌려짐

**증상**
- kubectl로 리소스 수정했는데 몇 분 후 원래대로 돌아감
- Argo CD가 계속 "OutOfSync" 표시

**원인**
- Argo CD의 selfHeal 기능이 활성화됨
- Git이 single source of truth

**해결 방법**
```bash
# 옵션 1: Git을 통해 변경 (권장)
# 1. 로컬에서 Manifest 수정
# 2. Git commit & push
# 3. Argo CD가 자동 동기화

# 옵션 2: 일시적으로 selfHeal 비활성화 (비권장)
kubectl patch application titanium-prod -n argocd \
  --type merge \
  -p '{"spec":{"syncPolicy":{"automated":{"selfHeal":false}}}}'
  
# kubectl 수동 변경

# selfHeal 재활성화
kubectl patch application titanium-prod -n argocd \
  --type merge \
  -p '{"spec":{"syncPolicy":{"automated":{"selfHeal":true}}}}'
```

**GitOps 원칙**
- 모든 변경은 Git을 통해서만
- kubectl은 read-only 용도로만 사용
- 긴급 상황에도 Git revert 사용

---

### 문제 18: Git과 Kubernetes 상태가 장기간 불일치

**증상**
- Argo CD가 계속 "Syncing..." 상태
- 몇 분이 지나도 동기화 완료되지 않음

**원인**
1. Kustomize 빌드 오류
2. 순환 의존성
3. Webhook이 리소스 수정

**해결 방법**
```bash
# 1. Kustomize 빌드 테스트
kubectl kustomize k8s-manifests/overlays/solid-cloud/

# 2. Argo CD 로그 확인
kubectl logs -n argocd deployment/argocd-application-controller \
  | grep -A 10 "titanium-prod"

# 3. Application 상태 확인
kubectl get application titanium-prod -n argocd -o yaml | grep -A 20 "status:"

# 4. 강제 동기화 (Replace 옵션)
kubectl patch application titanium-prod -n argocd \
  --type merge \
  -p '{"operation":{"sync":{"syncOptions":["Replace=true","Force=true"]}}}'
```

**예방**
- 로컬에서 kubectl kustomize 테스트
- Kustomize validation 추가
- Admission Webhook 로그 모니터링

---

## 빠른 진단 체크리스트

### CI 실패 시
```bash
[ ] 1. 워크플로우가 트리거되었는가? (GitHub Actions 탭 확인)
[ ] 2. paths 필터가 변경된 파일과 매치하는가?
[ ] 3. Docker Hub 시크릿이 설정되어 있는가?
[ ] 4. 로컬에서 Docker 빌드가 성공하는가?
[ ] 5. CI 로그에서 정확한 에러 메시지 확인
```

### CD 실패 시
```bash
[ ] 1. CI가 성공적으로 완료되었는가?
[ ] 2. CD 워크플로우에 contents: write 권한이 있는가?
[ ] 3. kustomization.yaml이 올바르게 업데이트되었는가?
[ ] 4. Git commit이 push되었는가?
```

### Argo CD 문제 시
```bash
[ ] 1. Argo CD Application이 Healthy 상태인가?
[ ] 2. Git 저장소에 최신 변경사항이 반영되었는가?
[ ] 3. Argo CD가 올바른 Git revision을 보고 있는가?
[ ] 4. Kustomize 빌드가 로컬에서 성공하는가?
```

### 배포 실패 시
```bash
[ ] 1. Pod가 Running 상태인가?
[ ] 2. Pod 로그에 에러가 있는가?
[ ] 3. 이미지 태그가 존재하는가?
[ ] 4. Service Endpoint가 생성되었는가?
[ ] 5. 리소스(CPU/Memory)가 충분한가?
```

---

## 유용한 명령어 모음

```bash
# CI/CD 상태 확인
gh run list --workflow=ci.yml --limit 5
gh run list --workflow=cd.yml --limit 5
gh run view [RUN_ID] --log

# Argo CD 상태 확인
kubectl get application -n argocd
kubectl describe application titanium-prod -n argocd
kubectl logs -n argocd deployment/argocd-server

# Kubernetes 리소스 확인
kubectl get all -n titanium-prod
kubectl get pods -n titanium-prod -o wide
kubectl describe pod [POD_NAME] -n titanium-prod
kubectl logs [POD_NAME] -n titanium-prod --tail=100

# 네트워크 디버깅
kubectl exec [POD_NAME] -n titanium-prod -- curl http://[SERVICE]:PORT
kubectl get endpoints -n titanium-prod
kubectl describe service [SERVICE_NAME] -n titanium-prod

# 롤백
kubectl rollout history deployment/[DEPLOYMENT] -n titanium-prod
kubectl rollout undo deployment/[DEPLOYMENT] -n titanium-prod
git revert [COMMIT_SHA]
```

---

## 추가 리소스

- [GitHub Actions 문서](https://docs.github.com/actions)
- [Docker 빌드 최적화](https://docs.docker.com/build/cache/)
- [Argo CD 트러블슈팅](https://argo-cd.readthedocs.io/en/stable/operator-manual/troubleshooting/)
- [Kubernetes 디버깅](https://kubernetes.io/docs/tasks/debug/)
- [Kustomize 문서](https://kustomize.io/)

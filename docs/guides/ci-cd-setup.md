# CI/CD 파이프라인 설정 가이드

## 개요

Titanium 프로젝트는 GitHub Actions를 사용하여 CI/CD 파이프라인을 구축했습니다. 이 가이드는 CI/CD 파이프라인을 설정하고 사용하는 방법을 설명합니다.

## GitHub Secrets 설정

CI/CD 파이프라인이 작동하려면 GitHub Repository에 다음 Secrets를 설정해야 합니다.

### 1. Docker Hub Token 생성

1. [Docker Hub](https://hub.docker.com)에 로그인
2. 우측 상단 프로필 → **Account Settings** 클릭
3. 좌측 메뉴에서 **Security** 선택
4. **New Access Token** 버튼 클릭
5. Token Description 입력 (예: `github-actions-ci`)
6. Access permissions: **Read, Write, Delete** 선택
7. **Generate** 버튼 클릭
8. 생성된 토큰을 안전한 곳에 복사 (한 번만 표시됩니다)

### 2. GitHub Repository Secrets 등록

1. GitHub Repository 페이지로 이동
2. **Settings** 탭 클릭
3. 좌측 메뉴에서 **Secrets and variables** → **Actions** 선택
4. **New repository secret** 버튼 클릭
5. 다음 Secret 추가:
   - **Name**: `DOCKER_HUB_TOKEN`
   - **Value**: 위에서 생성한 Docker Hub Access Token 붙여넣기
6. **Add secret** 버튼 클릭

## CI 파이프라인 구조

### Workflow 트리거

CI 파이프라인은 다음 경우에 자동으로 실행됩니다:

1. **Pull Request 생성/업데이트**: `main` 또는 `develop` 브랜치로의 PR
2. **Main 브랜치 Push**: `main` 브랜치에 직접 푸시할 때

### 서비스별 변경 감지

워크플로우는 변경된 서비스만 빌드하도록 최적화되어 있습니다:

- `user-service/**` 변경 시 → user-service만 빌드
- `blog-service/**` 변경 시 → blog-service만 빌드
- 여러 서비스 변경 시 → 변경된 모든 서비스 빌드

### 빌드 프로세스

#### Pull Request 시

1. **변경 감지**: 어떤 서비스가 변경되었는지 감지
2. **Docker 이미지 빌드**: 멀티 플랫폼 빌드 (linux/amd64, linux/arm64)
3. **Trivy 보안 스캔**: CRITICAL 및 HIGH 취약점 스캔
4. **스캔 결과 업로드**:
   - GitHub Security 탭에 SARIF 형식으로 업로드
   - PR에 코멘트로 요약 결과 게시

#### Main 브랜치 Push 시

1. **변경 감지**: 어떤 서비스가 변경되었는지 감지
2. **Docker 이미지 빌드**: 멀티 플랫폼 빌드
3. **Docker Hub에 Push**:
   - 태그: `main-{git-sha}`, `latest`
4. **이미지 메타데이터 추가**: 라벨 및 버전 정보

## 사용 방법

### 1. 기능 개발 시

```bash
# 1. 기능 브랜치 생성
git checkout -b feature/new-feature

# 2. 코드 수정 (예: user-service)
# ... 코드 수정 ...

# 3. 커밋 및 푸시
git add user-service/
git commit -m "feat: Add new feature to user-service"
git push origin feature/new-feature

# 4. GitHub에서 PR 생성
# → CI 파이프라인 자동 실행
# → Trivy 스캔 결과 PR에 코멘트로 표시
```

### 2. PR 리뷰 및 머지

```bash
# PR 승인 후 main 브랜치로 머지
# → main 브랜치에 push 이벤트 발생
# → CI 파이프라인 자동 실행
# → Docker Hub에 새 이미지 푸시
```

### 3. 빌드 상태 확인

- **Actions 탭**: GitHub Repository의 Actions 탭에서 워크플로우 실행 상태 확인
- **Security 탭**: Security 탭의 Code scanning alerts에서 Trivy 스캔 결과 확인

## Docker 이미지 태그 전략

### Pull Request
- `pr-{pr-number}`: PR 번호를 포함한 테스트 이미지
- 예: `dongju101/user-service:pr-42`

### Main 브랜치
- `main-{git-sha}`: Git commit SHA를 포함한 이미지
- `latest`: 최신 stable 이미지
- 예:
  - `dongju101/user-service:main-abc1234`
  - `dongju101/user-service:latest`

## Trivy 보안 스캔

### 스캔 대상
- 빌드된 Docker 이미지의 OS 패키지 취약점
- 애플리케이션 의존성 취약점

### 심각도 수준
- **CRITICAL**: 즉시 수정 필요
- **HIGH**: 가능한 빠르게 수정 필요

### 결과 확인

1. **PR 코멘트**: 각 서비스별 취약점 요약
   ```
   ### 🔒 Trivy Security Scan Results - `user-service`
   - Total Vulnerabilities: 5
   - Critical: 2
   - High: 3
   ```

2. **GitHub Security 탭**: 상세한 취약점 정보 및 수정 방법

## 트러블슈팅

### Docker Hub Push 실패

**증상**: `unauthorized: authentication required` 오류

**해결방법**:
1. GitHub Secrets에 `DOCKER_HUB_TOKEN`이 올바르게 설정되었는지 확인
2. Docker Hub Access Token이 만료되지 않았는지 확인
3. Token 권한이 Read, Write, Delete인지 확인

### Trivy 스캔 실패

**증상**: Trivy 액션에서 오류 발생

**해결방법**:
1. 이미지가 올바르게 빌드되었는지 확인
2. Trivy 데이터베이스 업데이트 문제일 수 있음 (재실행 시도)

### 빌드 캐시 문제

**증상**: 빌드가 예상보다 느리거나 이전 변경사항이 반영되지 않음

**해결방법**:
1. GitHub Actions 캐시 삭제:
   - Repository Settings → Actions → Caches → 관련 캐시 삭제
2. Dockerfile에서 `--no-cache` 옵션 사용 고려

## 다음 단계

CI 파이프라인 설정이 완료되었다면:

1. [GitOps 설정 가이드](./gitops-setup.md) - Argo CD를 사용한 자동 배포
2. [Rollback 가이드](./rollback-guide.md) - 배포 롤백 프로시저

## 참고 자료

- [GitHub Actions 문서](https://docs.github.com/en/actions)
- [Docker Buildx 문서](https://docs.docker.com/buildx/working-with-buildx/)
- [Trivy 문서](https://aquasecurity.github.io/trivy/)
- [Docker Hub Access Tokens](https://docs.docker.com/docker-hub/access-tokens/)

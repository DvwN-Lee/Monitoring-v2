---
version: 1.0
last_updated: 2025-11-15
author: Dongju Lee
---

# [Troubleshooting] Docker Hub 로그인 실패 문제 해결

## 1. 문제 상황

GitHub Actions CI 워크플로우에서 `docker/login-action`을 사용하여 Docker Hub에 로그인하는 단계에서 인증 오류가 발생했습니다. 이로 인해 새로 빌드한 Docker 이미지를 Docker Hub 리포지토리로 푸시(push)하지 못하고 CI Pipeline이 실패했습니다.

## 2. 증상

GitHub Actions 워크플로우의 'Build and push Docker image' 작업 로그를 확인했을 때, 'Login to Docker Hub' 단계에서 다음과 같은 오류 메시지가 출력됩니다.

```
Error: failed to login to docker.io: invalid username or password
```

또는

```
Error: Username and password required
```

이 오류는 `docker/login-action`이 제공된 인증 정보(credentials)를 사용하여 Docker Hub에 로그인하려고 시도했으나 거부되었음을 의미합니다.

## 3. 원인 분석

Docker Hub 로그인 실패는 대부분 인증 정보 자체의 문제이거나, GitHub Actions에서 해당 정보를 가져오는 과정의 문제입니다.

1.  **`DOCKER_HUB_TOKEN` 시크릿 미설정 또는 오타**:
    *   가장 흔한 원인으로, GitHub 리포지토리의 `Settings > Secrets and variables > Actions`에 Docker Hub Access Token이 `DOCKER_HUB_TOKEN`이라는 이름의 시크릿으로 저장되지 않았거나, 이름에 오타가 있는 경우입니다. (예: `DOCKERHUB_TOKEN`)

2.  **Access Token 만료**:
    *   Docker Hub에서 발급받은 Access Token은 유효 기간이 있을 수 있습니다. 저장된 토큰이 만료되어 더 이상 유효하지 않은 경우 로그인에 실패합니다.

3.  **Access Token 권한 부족**:
    *   Docker Hub에서 Access Token을 생성할 때 부여한 권한(Permissions)이 부족한 경우입니다. 이미지를 푸시하려면 최소한 **Read & Write** 권한이 필요합니다. `Read-only` 권한만 가진 토큰으로는 로그인 후 푸시할 수 없습니다.

4.  **GitHub Secrets 참조 오류**:
    *   워크플로우 YAML 파일 내에서 시크릿을 잘못 참조한 경우입니다. `secrets.DOCKER_HUB_TOKEN` 대신 `secret.DOCKER_HUB_TOKEN`이나 `secrets.DOCKER_TOKEN` 등 잘못된 이름으로 참조하면, 액션은 빈 값을 받게 되어 로그인에 실패합니다.

## 4. 해결 방법

#### 1단계: Docker Hub에서 Access Token 확인 및 재발급

1.  [Docker Hub](https://hub.docker.com/)에 로그인합니다.
2.  우측 상단의 프로필 아이콘을 클릭하고 **Account Settings > Security**로 이동합니다.
3.  'Access Tokens' 섹션에서 기존 토큰의 상태를 확인하거나, 'New Access Token' 버튼을 클릭하여 새로운 토큰을 발급받습니다.
4.  **Permissions**를 설정할 때, 이미지를 푸시해야 하므로 반드시 **Read & Write**를 선택합니다. (필요에 따라 `Delete`도 추가할 수 있습니다.)
5.  생성된 토큰을 **즉시 복사**해둡니다. 이 창을 닫으면 다시는 토큰을 확인할 수 없습니다.

#### 2단계: GitHub 리포지토리 Secrets 설정 확인 및 업데이트

1.  해당 GitHub 리포지토리에서 **Settings > Secrets and variables > Actions** 메뉴로 이동합니다.
2.  'Repository secrets' 목록에 `DOCKER_HUB_TOKEN`이라는 이름의 시크릿이 있는지 확인합니다.
    *   없다면 'New repository secret' 버튼을 눌러 `DOCKER_HUB_TOKEN`이라는 이름으로 새로 생성하고, 'Secret' 필드에 1단계에서 복사한 Access Token을 붙여넣습니다.
    *   이미 존재한다면, 'Update'를 선택하여 만료되었을 가능성이 있는 토큰을 새로운 토큰으로 교체합니다.

#### 3단계: 워크플로우 파일에서 시크릿 참조 확인

-   `.github/workflows/ci.yml` 파일을 열어 `docker/login-action`을 사용하는 부분을 확인합니다.
-   `password` 필드가 `secrets.DOCKER_HUB_TOKEN`을 정확하게 참조하고 있는지 확인합니다.

    ```yaml
      - name: Login to Docker Hub
        uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKER_HUB_USERNAME }}
          password: ${{ secrets.DOCKER_HUB_TOKEN }} # 이 부분이 정확한지 확인
    ```

#### 4단계: 워크플로우 재실행

-   수정 사항을 커밋하고 푸시하거나, GitHub Actions 탭에서 실패했던 워크플로우를 'Re-run all jobs'를 통해 재실행하여 로그인 및 이미지 푸시가 성공하는지 확인합니다.

## 5. 검증

해결책이 제대로 적용되었는지 확인하는 방법입니다.

### 1. GitHub Actions 로그인 단계 성공 확인

GitHub Actions 워크플로우 로그에서 Docker Hub 로그인이 성공했는지 확인합니다.

```bash
# GitHub Actions 로그에서 확인할 내용:
# Login to Docker Hub
# Run docker/login-action@v3
# Login Succeeded

# 예상 결과:
# Successfully logged in as <username>
```

### 2. Docker 이미지 푸시 성공 확인

빌드된 이미지가 Docker Hub에 성공적으로 푸시되었는지 확인합니다.

```bash
# GitHub Actions 로그에서 확인:
# Pushing image to docker.io/<username>/<repository>:<tag>
# ...
# Successfully pushed docker.io/<username>/<repository>:<tag>

# Docker Hub 웹사이트에서 확인:
# Repositories > <repository> > Tags 탭에서 새로운 이미지 태그 확인
```

### 3. GitHub Secrets 설정 검증

GitHub 리포지토리에 필요한 시크릿이 올바르게 설정되어 있는지 확인합니다.

```bash
# GitHub Repository > Settings > Secrets and variables > Actions 확인
# 필요한 시크릿:
# - DOCKER_HUB_USERNAME
# - DOCKER_HUB_TOKEN

# 주의: 시크릿 값은 표시되지 않으며, 이름과 마지막 업데이트 시간만 확인 가능
```

### 4. Access Token 권한 확인

Docker Hub Access Token의 권한이 적절하게 설정되어 있는지 확인합니다.

```bash
# Docker Hub > Account Settings > Security > Access Tokens
# 사용 중인 토큰의 권한 확인:
# - Read & Write (필수) 또는
# - Read, Write & Delete (선택)

# Read-only 권한만 있는 경우 푸시 실패
```

### 5. 워크플로우 재실행 테스트

수정된 설정으로 전체 워크플로우가 성공적으로 완료되는지 테스트합니다.

```bash
# GitHub Actions 탭에서 재실행
# Re-run all jobs 클릭

# 예상 결과:
# **PASS**: Login to Docker Hub
# **PASS**: Build and push Docker image
# **PASS**: 전체 워크플로우 성공
```

## 6. 교훈

1.  **비밀번호 대신 Access Token 사용**: 보안을 위해 Docker Hub 비밀번호를 직접 사용하기보다, 제한된 권한과 유효 기간을 가진 Access Token을 사용하는 것이 훨씬 안전하고 권장되는 방식입니다.
2.  **시크릿 이름의 일관성**: `DOCKER_HUB_USERNAME`, `DOCKER_HUB_TOKEN` 등 시크릿 이름은 프로젝트 내에서 일관되게 관리해야 혼동과 오류를 줄일 수 있습니다.
3.  **최소 권한의 원칙**: Access Token을 생성할 때는 필요한 최소한의 권한(예: `Read & Write`)만 부여하여, 토큰이 유출되더라도 피해를 최소화해야 합니다.

## 관련 문서

- [시스템 아키텍처 - CI/CD Pipeline](../../02-architecture/architecture.md#4-cicd-Pipeline)
- [Secret 관리 가이드](../../04-operations/guides/SECRET_MANAGEMENT.md)

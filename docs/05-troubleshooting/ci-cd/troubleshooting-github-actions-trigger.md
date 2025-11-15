---
version: 1.0
last_updated: 2025-11-15
author: Dongju Lee
---

# [Troubleshooting] GitHub Actions CI 트리거 안 됨 문제 해결

## 1. 문제 상황

`main` 브랜치에 새로운 코드를 푸시(push)했음에도 불구하고, CI/CD 파이프라인의 첫 단계인 GitHub Actions CI 워크플로우가 전혀 실행되지 않는 문제가 발생했습니다. 이로 인해 Docker 이미지 빌드, 보안 스캔, Argo CD 매니페스트 업데이트 등 후속 프로세스가 모두 중단되었습니다.

## 2. 증상

-   로컬에서 `git push origin main` 명령어가 성공적으로 완료됩니다.
-   GitHub 리포지토리의 'Actions' 탭에 새로운 워크플로우 실행(run) 기록이 나타나지 않습니다.
-   Pull Request를 생성하거나 특정 브랜치에 푸시했을 때 예상했던 워크플로우가 트리거되지 않습니다.

## 3. 원인 분석

GitHub Actions 워크플로우가 트리거되지 않는 원인은 대부분 워크플로우 정의 파일(`.github/workflows/*.yml`)의 설정 오류에 있습니다. 주요 원인은 다음과 같습니다.

1.  **`on` 트리거 조건 오류**:
    *   가장 흔한 원인으로, 워크플로우를 실행시키기 위한 이벤트 조건이 실제 이벤트와 일치하지 않는 경우입니다.
    *   예시: `main` 브랜치에 푸시했을 때 실행되도록 의도했지만, `on: push: branches: [ master ]` 와 같이 브랜치 이름이 잘못 지정된 경우.

2.  **`paths` 또는 `paths-ignore` 필터 미매칭**:
    *   `on.<event>.paths` 필터는 특정 파일이나 디렉토리가 변경되었을 때만 워크플로우를 실행시키는 유용한 기능이지만, 이 패턴이 실제 변경된 파일 경로와 일치하지 않으면 워크플로우는 실행되지 않습니다.
    *   예시: `paths: [ 'backend/**' ]` 로 설정된 상태에서 `frontend/` 디렉토리의 파일만 변경하고 푸시하면 워크플로우는 트리거되지 않습니다.

3.  **워크플로우 비활성화**:
    *   리포지토리 설정에서 특정 워크플로우나 모든 GitHub Actions가 비활성화된 경우.
    *   워크플로우 파일 상단에 `on: workflow_dispatch`만 명시되어 있고 다른 자동 트리거 이벤트가 없는 경우, 수동으로만 실행 가능합니다.

4.  **YAML 문법 오류**:
    *   워크플로우 파일의 YAML 문법이 잘못된 경우, GitHub Actions는 파일을 올바르게 파싱할 수 없어 워크플로우를 등록하거나 실행하지 못합니다. 들여쓰기, 하이픈(-), 콜론(:) 사용 등을 주의해야 합니다.

## 4. 해결 방법

#### 1단계: 워크플로우 파일의 `on` 트리거 조건 확인

-   `.github/workflows/` 디렉토리 안에 있는 해당 워크플로우 파일(예: `ci.yml`)을 엽니다.
-   `on:` 섹션의 설정이 의도한 트리거 조건과 일치하는지 검토합니다.
    -   **브랜치 이름 확인**: `branches` 또는 `branches-ignore` 목록에 오타가 없는지, `main`이 올바르게 포함되어 있는지 확인합니다.
    -   **이벤트 타입 확인**: `push`, `pull_request`, `schedule` 등 원하는 이벤트가 올바르게 명시되어 있는지 확인합니다.

    ```yaml
    # 예시: main 브랜치에 push 되거나, main 브랜치로의 pull request가 열렸을 때 실행
    on:
      push:
        branches: [ "main" ]
      pull_request:
        branches: [ "main" ]
    ```

#### 2단계: `paths` 필터 설정 검토

-   만약 `paths`나 `paths-ignore` 필터를 사용 중이라면, 최근 커밋에서 변경된 파일들이 해당 필터 조건에 부합하는지 확인합니다.
-   테스트를 위해 잠시 `paths` 필터를 주석 처리하고 푸시하여 워크플로우가 실행되는지 확인해볼 수 있습니다. 만약 주석 처리 후 실행된다면 `paths` 필터 설정이 원인입니다.

#### 3단계: 리포지토리 설정에서 워크플로우 활성화 상태 확인

-   GitHub 리포지토리에서 **Settings > Actions > General** 메뉴로 이동합니다.
-   'Actions permissions'가 'Allow all actions and reusable workflows'로 설정되어 있는지, 비활성화(disable) 상태가 아닌지 확인합니다.
-   개별 워크플로우가 비활성화되었는지 확인하려면 **Actions** 탭으로 이동하여 왼쪽 사이드바에서 해당 워크플로우를 찾고, '...' 메뉴를 통해 활성화(Enable workflow)할 수 있습니다.

#### 4단계: YAML 문법 검사

-   VS Code와 같은 코드 에디터에서 YAML 확장 프로그램을 설치하면 실시간으로 문법 오류를 확인할 수 있습니다.
-   온라인 YAML 린터(linter)를 사용해 파일 내용을 붙여넣고 유효성을 검사하는 것도 좋은 방법입니다.

## 5. 검증

해결책이 제대로 적용되었는지 확인하는 방법입니다.

### 1. 워크플로우 트리거 확인

코드를 푸시하여 워크플로우가 자동으로 실행되는지 확인합니다.

```bash
# 1. 테스트 커밋 생성 및 푸시
git commit --allow-empty -m "test: GitHub Actions 트리거 테스트"
git push origin main

# 2. GitHub Actions 탭에서 확인
# Repository > Actions 탭 > 새로운 워크플로우 실행 확인

# 예상 결과: 푸시 후 수초 내에 새로운 워크플로우 실행이 표시됨
```

### 2. 워크플로우 파일 구문 검증

YAML 파일 구문이 올바른지 확인합니다.

```bash
# GitHub Actions 탭 확인:
# - 워크플로우가 목록에 표시되는지 확인
# - 구문 오류 시 경고 메시지 표시됨

# 로컬에서 YAML 검증:
yamllint .github/workflows/ci.yml
```

### 3. 트리거 조건 검증

워크플로우의 on 조건이 올바르게 설정되었는지 확인합니다.

```bash
# .github/workflows/ci.yml 파일 확인
cat .github/workflows/ci.yml | grep -A 5 "^on:"

# 예상 출력:
# on:
#   push:
#     branches: [ "main" ]
#   pull_request:
#     branches: [ "main" ]
```

### 4. GitHub Actions 활성화 상태 확인

리포지토리 설정에서 GitHub Actions가 활성화되어 있는지 확인합니다.

```bash
# GitHub UI에서 확인:
# Repository > Settings > Actions > General
#
# Actions permissions:
# ✅ Allow all actions and reusable workflows
```

### 5. 워크플로우 실행 로그 확인

워크플로우가 실행되면 로그를 확인하여 모든 단계가 정상 작동하는지 검증합니다.

```bash
# GitHub Actions 탭에서 확인:
# - 최근 워크플로우 실행 클릭
# - 각 job 및 step의 실행 결과 확인

# 예상 결과:
# ✅ Build
# ✅ Test
# ✅ Security scan
# ✅ Push
```

## 6. 교훈

1.  **트리거 조건은 명시적이다**: GitHub Actions는 워크플로우 파일에 정의된 조건과 정확히 일치할 때만 작동합니다. 브랜치 이름, 이벤트 타입, 파일 경로 등 모든 조건을 꼼꼼히 검토해야 합니다.
2.  **`paths` 필터는 양날의 검**: 불필요한 워크플로우 실행을 막아 비용을 절약하는 좋은 기능이지만, 잘못 설정하면 필수적인 CI/CD 파이프라인이 중단되는 원인이 될 수 있습니다. 신중하게 패턴을 설정해야 합니다.
3.  **GitHub UI는 훌륭한 디버깅 도구**: 'Actions' 탭에서는 워크플로우 실행 기록뿐만 아니라, 문법 오류 등으로 인해 등록되지 않은 워크플로우에 대한 경고도 표시될 수 있으므로 주의 깊게 살펴볼 필요가 있습니다.

## 관련 문서

- [시스템 아키텍처 - CI/CD 파이프라인](../../02-architecture/architecture.md#4-cicd-파이프라인)
- [운영 가이드](../../04-operations/guides/operations-guide.md)

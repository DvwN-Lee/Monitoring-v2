---
version: 1.0
last_updated: 2025-11-15
author: Dongju Lee
---

# [Troubleshooting] Docker 빌드 캐시 미작동 문제 해결

## 1. 문제 상황

소스 코드의 주석이나 README 파일 등 아주 작은 부분만 수정했음에도 불구하고, GitHub Actions CI Pipeline에서 `docker build` 명령이 실행될 때 모든 레이어(layer)를 처음부터 다시 빌드하는 문제가 발생했습니다. 이로 인해 매번 빌드 시간이 불필요하게 길어져(10분 이상 소요) CI 실행 효율이 크게 저하되었습니다.

## 2. 증상

-   GitHub Actions의 `docker build` 단계 로그를 확인했을 때, `RUN pip install -r requirements.txt` 와 같이 오래 걸리는 단계가 `CACHED`로 표시되지 않고 매번 새로 실행됩니다.
-   코드 변경 사항이 거의 없음에도 불구하고 빌드 시간이 줄어들지 않고 항상 비슷하게 소요됩니다.
-   로컬 환경에서는 캐시가 잘 동작하지만, GitHub Actions 환경에서만 캐시가 적용되지 않습니다.

## 3. 원인 분석

Docker 빌드 캐시가 작동하지 않는 문제는 주로 Dockerfile의 구조와 CI 환경의 특성 때문에 발생합니다.

1.  **Dockerfile 레이어 순서 비최적화**:
    *   Docker는 Dockerfile의 각 명령어를 하나의 레이어로 간주하고, 위에서부터 아래로 실행하며 각 레이어를 캐싱합니다. 만약 특정 레이어의 내용이 변경되면, 그 레이어와 그 **이후의 모든 레이어**의 캐시가 무효화(깨짐)됩니다.
    *   가장 흔한 실수는 자주 변경되는 소스 코드(`COPY . .`)를, 자주 변경되지 않는 의존성 설치(`RUN pip install ...`)보다 앞에 두는 것입니다. 이 경우 소스 코드가 조금만 바뀌어도 의존성 설치부터 모든 단계를 다시 실행하게 됩니다.

2.  **CI 실행 환경의 일시성(Ephemeral Nature)**:
    *   GitHub Actions와 같은 대부분의 CI/CD Service는 각 작업(job)을 격리된 깨끗한 가상 환경(runner)에서 실행합니다. 작업이 끝나면 해당 환경은 파기되므로, 로컬 Docker 데몬이 유지하는 빌드 캐시가 다음 작업으로 이어지지 않습니다.

3.  **`docker/build-push-action`의 캐시 설정 부재**:
    *   `docker/build-push-action`을 사용할 때, 빌드 캐시를 어디에 저장하고(`cache-to`), 어디서부터 가져올지(`cache-from`) 명시적으로 설정하지 않으면, CI 환경의 한계로 인해 캐시를 전혀 활용할 수 없습니다.

## 4. 해결 방법

#### 1단계: Dockerfile 레이어 순서 최적화

-   **가장 중요한 단계**입니다. 변경 빈도가 낮은 명령어를 Dockerfile의 위쪽으로, 변경 빈도가 높은 명령어를 아래쪽으로 재배치합니다.
-   **나쁜 예시**:
    ```dockerfile
    FROM python:3.9-slim
    WORKDIR /app
    COPY . .  # 소스 코드를 먼저 복사 -> 코드가 바뀔 때마다 아래 모든 단계 재실행
    RUN pip install -r requirements.txt
    CMD ["uvicorn", "main:app", "--host", "0.0.0.0"]
    ```
-   **좋은 예시 (최적화)**:
    ```dockerfile
    FROM python:3.9-slim
    WORKDIR /app
    # 1. 의존성 정의 파일만 먼저 복사
    COPY requirements.txt .
    # 2. 의존성 설치 (requirements.txt가 바뀌지 않으면 이 레이어는 캐시됨)
    RUN pip install -r requirements.txt
    # 3. 의존성 설치 후, 나머지 소스 코드 복사
    COPY . .
    CMD ["uvicorn", "main:app", "--host", "0.0.0.0"]
    ```
    이렇게 하면 `requirements.txt` 파일이 변경되지 않는 한, 소스 코드만 수정했을 때는 `pip install` 단계를 건너뛰고 캐시를 사용하게 됩니다.

#### 2단계: `docker/build-push-action`에 캐시 설정 추가

-   GitHub Actions 워크플로우 파일(`ci.yml`)에서 `docker/build-push-action` 부분에 `cache-from`과 `cache-to` 옵션을 추가하여 빌드 캐시를 원격에 저장하고 재사용하도록 설정합니다.
-   캐시 저장 방식은 `type=registry` (레지스트리에 캐시 메타데이터 저장) 또는 `type=gha` (GitHub Actions 캐시 API 사용) 등을 선택할 수 있습니다. `type=gha`가 설정이 더 간편합니다.

    ```yaml
    - name: Build and push Docker image
      uses: docker/build-push-action@v5
      with:
        context: ./user-service
        push: true
        tags: my-docker-hub/my-app:${{ github.sha }}
        # 캐시 설정 추가
        cache-from: type=gha
        cache-to: type=gha,mode=max
    ```
    *   `mode=max`는 모든 레이어를 캐시하여 이미지 크기가 커질 수 있지만 캐시 히트율을 극대화합니다.

#### 3단계: `buildx` 설정 확인

-   `docker/build-push-action`은 Docker의 `buildx` 플러그인을 사용합니다. 캐시 기능을 포함한 고급 빌드 기능을 사용하려면, 이 액션 이전에 `docker/setup-buildx-action`이 반드시 실행되어야 합니다.

    ```yaml
    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3 # build-push-action 이전에 위치해야 함

      - name: Login to Docker Hub
        # ...

      - name: Build and push Docker image
        # ...
    ```

## 5. 검증

해결책이 제대로 적용되었는지 확인하는 방법입니다.

### 1. GitHub Actions 빌드 로그 확인

Docker 빌드 단계의 로그에서 캐시 사용 여부를 확인합니다.

```bash
# GitHub Actions 로그에서 확인할 내용:
# [1/5] FROM docker.io/library/python:3.9-slim
# [2/5] WORKDIR /app
# [3/5] COPY requirements.txt .
# [4/5] RUN pip install -r requirements.txt  # <- "CACHED" 표시 확인
# [5/5] COPY . .
```

### 2. 빌드 시간 개선 확인

캐시 적용 전후의 빌드 시간을 비교하여 개선되었는지 확인합니다.

```bash
# GitHub Actions UI에서 확인:
# - 이전 빌드: 10분 이상
# - 캐시 적용 후: 1-2분 (70-80% 단축)

# 캐시 미스 시: 전체 빌드 소요
# 캐시 히트 시: 소스 코드 복사 및 최종 레이어만 빌드
```

### 3. 캐시 히트율 확인

GitHub Actions 캐시 사용 통계를 확인합니다.

```bash
# GitHub Actions 로그에서 캐시 관련 메시지 확인:
# - "cache hit" 또는 "cache miss" 메시지
# - buildx cache statistics

# 예상 로그:
# importing cache manifest from gha:...
# ...
# exporting cache
# exporting cache to GitHub Actions Cache
```

### 4. Dockerfile 레이어 구조 검증

Dockerfile의 레이어 순서가 최적화되었는지 확인합니다.

```bash
# 로컬에서 테스트 빌드
docker build --progress=plain -t test-image .

# 예상 출력:
# Step 3/6: COPY requirements.txt .
# Step 4/6: RUN pip install -r requirements.txt  # <- 이 단계가 COPY . . 이전에 위치
# Step 5/6: COPY . .
```

### 5. 연속 빌드 테스트

소스 코드만 수정한 후 연속으로 빌드하여 캐시가 작동하는지 확인합니다.

```bash
# 1. 소스 코드 파일 수정 (예: 주석 추가)
git commit -m "test: 캐시 동작 확인용 커밋"
git push

# 2. GitHub Actions에서 새로운 빌드 시작
# 3. 로그에서 의존성 설치 단계가 CACHED로 표시되는지 확인
```

## 6. 교훈

1.  **Dockerfile의 명령어 순서가 캐시 효율성을 결정한다**: Dockerfile을 작성할 때는 항상 '변경이 잦은 것은 아래로, 그렇지 않은 것은 위로'라는 원칙을 기억해야 합니다.
2.  **CI 환경의 캐시는 명시적으로 관리해야 한다**: 로컬 환경과 달리 CI 환경의 캐시는 자동으로 유지되지 않습니다. `cache-from`/`cache-to`와 같은 옵션을 사용하여 캐시의 저장 및 로드 전략을 명확하게 정의해야 합니다.
3.  **캐시 무효화의 전파를 이해하라**: Docker 빌드에서 특정 레이어의 캐시가 깨지면, 그 이후의 모든 레이어는 순차적으로 다시 빌드된다는 기본 동작 원리를 이해하는 것이 트러블슈팅의 핵심입니다.

## 관련 문서

- [시스템 아키텍처 - CI/CD Pipeline](../../02-architecture/architecture.md#4-cicd-Pipeline)
- [운영 가이드](../../04-operations/guides/operations-guide.md)

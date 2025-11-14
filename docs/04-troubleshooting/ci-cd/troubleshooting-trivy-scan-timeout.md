# [Troubleshooting] Trivy 보안 스캔 시간 초과 문제 해결

## 1. 문제 상황

CI 파이프라인에 통합된 `aquasecurity/trivy-action`을 이용한 Docker 이미지 보안 스캔 단계가 정상적으로 완료되지 않고, 지정된 시간을 초과하여 작업(job) 자체가 실패하는 문제가 발생했습니다. 이로 인해 보안 취약점 점검이 이루어지지 않은 채 빌드가 중단되었습니다.

## 2. 증상

GitHub Actions 워크플로우 로그에서 Trivy 스캔 단계가 10분 이상(또는 설정된 `timeout-minutes` 이상) 실행되다가 다음과 같은 메시지와 함께 종료됩니다.

```
Error: The operation was canceled.
```

또는 작업 전체가 노란색으로 표시되며 'This job was canceled'라는 주석이 달립니다. 이는 GitHub Actions가 설정된 시간 제한 내에 작업이 완료되지 않아 강제로 중단시켰음을 의미합니다.

## 3. 원인 분석

Trivy 스캔의 시간 초과는 주로 스캔 준비 과정이나 스캔 자체에 예상보다 많은 시간이 소요될 때 발생합니다.

1.  **Trivy DB 다운로드 지연 또는 실패**:
    *   Trivy는 스캔을 실행하기 전에 최신 취약점 정보가 담긴 데이터베이스(DB)를 다운로드합니다. GitHub Actions 실행기(runner)의 네트워크 환경이나 Trivy 서버의 상태에 따라 이 다운로드 과정이 매우 느려지거나 실패할 수 있습니다.

2.  **스캔할 이미지의 크기가 큼**:
    *   이미지의 크기가 수 GB에 달하거나, 레이어(layer)가 매우 많은 복잡한 이미지일수록 스캔에 소요되는 시간이 길어집니다. 특히 운영체제 기본 라이브러리가 많은 베이스 이미지를 사용할 경우 스캔 대상이 많아져 시간이 오래 걸립니다.

3.  **부족한 `timeout` 설정**:
    *   `aquasecurity/trivy-action` 자체 또는 상위 단계인 GitHub Actions 작업(job)에 설정된 `timeout-minutes` 값이 이미지 스캔을 완료하기에 충분하지 않은 경우입니다.

4.  **캐시 미활용**:
    *   매번 워크플로우가 실행될 때마다 Trivy DB를 새로 다운로드하면, 이 과정에서만 수 분이 소요될 수 있습니다. 캐시를 사용하지 않으면 이 시간이 계속 누적되어 시간 초과의 원인이 됩니다.

## 4. 해결 방법

#### 1단계: `trivy-action`에 명시적인 `timeout` 설정 추가

-   `aquasecurity/trivy-action`은 자체적으로 `timeout` 입력을 지원합니다. 기본값보다 넉넉한 시간을 설정하여 스캔이 완료될 시간을 보장해줍니다.

    ```yaml
    - name: Scan image with Trivy
      uses: aquasecurity/trivy-action@master
      with:
        image-ref: 'my-registry/my-app:${{ github.sha }}'
        format: 'table'
        exit-code: '1'
        ignore-unfixed: true
        vuln-type: 'os,library'
        severity: 'CRITICAL,HIGH'
        timeout: '15m' # <-- 타임아웃을 15분으로 명시적 설정
    ```

#### 2단계: GitHub Actions 캐시를 활용한 Trivy DB 캐싱

-   `actions/cache` 액션을 사용하여 Trivy가 사용하는 캐시 디렉토리를 저장하고 복원할 수 있습니다. `trivy-action`은 캐시가 존재하면 DB 다운로드를 건너뛰어 실행 시간을 크게 단축시킵니다.

    ```yaml
    jobs:
      build:
        runs-on: ubuntu-latest
        steps:
          # ... (checkout 등 이전 단계)

          - name: Cache Trivy DB
            uses: actions/cache@v3
            with:
              path: ~/.trivy/db
              key: trivy-db-${{ runner.os }}-${{ hashFiles('**/Gemfile.lock') }} # key는 프로젝트에 맞게 조정
              restore-keys: |
                trivy-db-${{ runner.os }}-

          - name: Scan image with Trivy
            uses: aquasecurity/trivy-action@master
            with:
              # ... (trivy 설정)
    ```
    *참고: `trivy-action` 최신 버전은 `actions/cache`와의 통합을 더 원활하게 지원하므로, 가급적 최신 버전을 사용하는 것이 좋습니다.*

#### 3단계: 이미지 크기 최적화

-   근본적인 해결책으로, Dockerfile을 최적화하여 이미지 크기를 줄입니다.
    -   **멀티-스테이지 빌드(Multi-stage builds)**를 사용하여 최종 이미지에는 런타임에 필요한 파일만 포함시킵니다.
    -   `alpine`과 같은 경량 베이스 이미지를 사용합니다.
    -   `.dockerignore` 파일을 사용하여 빌드 컨텍스트에 불필요한 파일이 포함되지 않도록 합니다.

#### 4단계: (주의) DB 업데이트 건너뛰기

-   네트워크가 불안정하여 DB 다운로드가 주된 실패 원인일 경우, `--skip-db-update` 옵션을 사용하여 DB 업데이트를 건너뛸 수 있습니다. 하지만 이 경우 최신 취약점을 놓칠 수 있으므로, 주기적으로 캐시를 갱신하는 전략과 함께 사용해야 합니다.

    ```yaml
    - name: Scan image with Trivy
      uses: aquasecurity/trivy-action@master
      with:
        # ...
        skip-db-update: 'true' # 캐시된 DB를 사용 강제
    ```

## 5. 교훈

1.  **외부 의존 작업에는 항상 `timeout`을 고려**: 보안 스캔, 대용량 파일 다운로드 등 외부 서비스나 네트워크에 의존하는 작업은 예상치 못한 지연이 발생할 수 있으므로, 기본값에 의존하기보다 명시적으로 넉넉한 `timeout`을 설정하는 것이 안정적입니다.
2.  **캐시는 CI 시간 단축의 핵심**: Trivy DB, 패키지 의존성 등 반복적으로 다운로드되는 데이터는 적극적으로 캐싱하여 CI 실행 시간을 줄이고 비용을 절약해야 합니다.
3.  **작은 이미지가 모든 면에서 유리하다**: 이미지 크기는 빌드, 푸시, 스캔, 배포 시간뿐만 아니라 저장 비용에도 영향을 미칩니다. Dockerfile 최적화는 CI/CD 파이프라인 전체의 효율성을 높이는 중요한 활동입니다.

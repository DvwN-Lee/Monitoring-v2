---
version: 1.0
last_updated: 2025-11-15
author: Dongju Lee
---

# [Troubleshooting] Argo CD Git 변경사항 미감지 문제 해결

## 1. 문제 상황

CI/CD 파이프라인을 통해 GitHub 리포지토리에 저장된 Kubernetes 매니페스트(YAML 파일)를 수정하고 `main` 브랜치에 푸시했습니다. 하지만 Argo CD UI를 확인했을 때, 해당 Application의 상태가 `Synced`로 그대로 유지되고 `OutOfSync`로 변경되지 않아 자동 동기화(auto-sync)가 트리거되지 않는 문제가 발생했습니다.

## 2. 증상

-   Git 리포지토리에는 분명히 새로운 커밋이 푸시되었습니다.
-   Argo CD UI에서 해당 Application의 상태가 계속 `Synced`로 표시되며, 'LAST SYNC' 시간도 과거에 머물러 있습니다.
-   UI에서 'REFRESH' 버튼을 **수동으로 클릭해야만** 비로소 `OutOfSync` 상태로 변경되고 변경 사항이 감지됩니다.
-   Webhook을 설정했음에도 불구하고 실시간으로 변경이 감지되지 않습니다.

## 3. 원인 분석

Argo CD가 Git 리포지토리의 변경 사항을 자동으로 감지하지 못하는 문제는 Argo CD의 변경 감지 메커니즘인 Webhook 또는 Polling 과정의 문제입니다.

1.  **Webhook 설정 오류 또는 실패**:
    *   **잘못된 Payload URL**: GitHub 리포지토리 Webhook 설정의 'Payload URL'이 Argo CD API 서버의 `/api/webhook` 엔드포인트를 정확히 가리키고 있지 않은 경우.
    *   **잘못된 Content Type**: Webhook의 'Content type'이 `application/json`으로 설정되지 않은 경우.
    *   **네트워크 문제**: 방화벽, Ingress Controller 설정, 네트워크 정책(NetworkPolicy) 등으로 인해 GitHub.com에서 보내는 Webhook 요청이 사내 네트워크나 프라이빗 클러스터의 Argo CD 서버에 도달하지 못하는 경우.

2.  **Git Polling 주기로 인한 지연**:
    *   Webhook을 사용하지 않거나 실패할 경우, Argo CD는 주기적으로 Git 리포지토리를 **폴링(polling)**하여 변경 사항을 확인합니다. 이 기본 폴링 주기는 **3분**입니다. 따라서 변경 사항이 UI에 반영되기까지 최대 3분의 지연이 발생하는 것은 정상적인 동작일 수 있습니다.

3.  **Argo CD Application 설정 오류**:
    *   Application 매니페스트(`application.yaml`)에 정의된 `spec.source.repoURL` (리포지토리 주소) 또는 `spec.source.targetRevision` (브랜치, 태그 등)이 잘못 지정되어, 실제 변경이 발생한 리포지토리나 브랜치가 아닌 다른 곳을 바라보고 있는 경우.

4.  **Argo CD 내부 캐시 문제**:
    *   Argo CD는 성능 향상을 위해 Git 리포지토리의 상태를 일정 시간 동안 캐시합니다. 드물지만 이 캐시가 어떤 이유로 갱신되지 않아 변경 사항을 인지하지 못하는 경우가 있을 수 있습니다.

## 4. 해결 방법

#### 1단계: GitHub Webhook 설정 및 전달 상태 확인

1.  GitHub 리포지토리에서 **Settings > Webhooks** 메뉴로 이동합니다.
2.  설정된 Webhook을 클릭하여 'Payload URL'이 `https://<your-argocd-domain>/api/webhook` 형식으로 올바르게 입력되었는지 확인합니다.
3.  **Recent Deliveries** 탭을 확인합니다.
    *   최근 커밋에 해당하는 Webhook 요청이 목록에 있어야 합니다.
    *   요청 옆에 녹색 체크(✅)와 `200` 응답 코드가 표시되면 Webhook은 성공적으로 Argo CD에 전달된 것입니다.
    *   만약 빨간색 느낌표(❗)와 `4xx` 또는 `5xx` 오류 코드가 보인다면, GitHub가 Argo CD 서버에 접근하지 못하는 것이므로 Ingress, 방화벽, 네트워크 설정을 점검해야 합니다.

#### 2단계: Argo CD의 Git Polling 주기 확인

-   Webhook을 사용하지 않는 경우, 변경 사항이 3분 이내에 반영되지 않는 것은 정상일 수 있습니다.
-   이 주기를 조정하고 싶다면, `argocd-cm` ConfigMap을 수정하여 `timeout.reconciliation` 값을 변경할 수 있습니다. (단, 너무 짧은 주기는 Git 서버와 Argo CD에 부하를 줄 수 있으므로 권장되지 않습니다.)

    ```bash
    kubectl edit configmap argocd-cm -n argocd
    ```
    ```yaml
    data:
      timeout.reconciliation: 180s # 기본값 3분
    ```

#### 3단계: 'Hard Refresh'로 캐시 무시하고 새로고침

-   가장 간단한 수동 해결책입니다. Argo CD UI에서 Application의 'REFRESH' 버튼 옆 드롭다운 메뉴를 열고 **Hard Refresh**를 선택합니다.
-   'Hard Refresh'는 Argo CD의 내부 캐시를 무시하고 Git 리포지토리로부터 최신 정보를 강제로 다시 가져옵니다. 만약 'Hard Refresh' 후 `OutOfSync`로 변경된다면, Webhook 실패나 Polling 주기 지연이 원인일 가능성이 높습니다.

#### 4단계: CI/CD 파이프라인에서 강제 Refresh 트리거

-   Webhook이 불안정하거나 즉각적인 동기화 보장이 필요할 때 유용한 방법입니다.
-   CI/CD 파이프라인의 마지막 단계(매니페스트 푸시 이후)에서 `kubectl patch` 명령어를 사용하여 Argo CD Application에 특정 annotation을 추가합니다. Argo CD는 이 annotation을 감지하고 즉시 'Hard Refresh'를 수행합니다.

    ```bash
    kubectl patch application <app-name> -n argocd --type merge -p '{"metadata": {"annotations": {"argocd.argoproj.io/refresh": "hard"}}}'
    ```

## 5. 검증

해결책이 제대로 적용되었는지 확인하는 방법입니다.

### 1. Webhook 동작 확인

GitHub에서 Webhook이 정상 작동하는지 확인합니다.

```bash
# GitHub Repository > Settings > Webhooks > Recent Deliveries 확인
# 최근 Webhook 전송 내역에서 200 응답 코드 확인
```

### 2. Git 변경 감지 테스트

실제로 Git 변경사항이 자동으로 감지되는지 테스트합니다.

```bash
# 1. 테스트 변경사항 커밋 및 푸시
git commit --allow-empty -m "test: ArgoCD 자동 감지 테스트"
git push origin main

# 2. ArgoCD Application 상태 모니터링 (30초~3분 이내)
kubectl get application -n argocd <app-name> -w

# 3. 예상 결과: Sync Status가 OutOfSync로 변경되어야 함
```

### 3. 자동 동기화 확인

Auto-sync가 활성화된 경우, OutOfSync 상태에서 자동으로 Synced 상태로 전환되는지 확인합니다.

```bash
# ArgoCD UI에서 확인
# - Sync Status: Synced
# - Last Sync: 최근 시간으로 업데이트
# - Sync Result: Succeeded
```

### 4. 로그 확인

ArgoCD 컨트롤러 로그에서 변경 감지 및 동기화 로그를 확인합니다.

```bash
kubectl logs -n argocd -l app.kubernetes.io/name=argocd-application-controller --tail=100 | grep <app-name>

# 예상 로그:
# "Comparing app state (desired state vs. live state)"
# "Sync operation to <revision> succeeded"
```

## 6. 교훈

1.  **GitOps의 실시간성은 Webhook에 의존**: 푸시 즉시 변경이 감지되기를 원한다면, Webhook 설정이 필수적이며 가장 먼저 점검해야 할 대상입니다. 네트워크 연결성을 반드시 확인해야 합니다.
2.  **Argo CD의 기본 동작 이해**: Argo CD의 기본 폴링 주기가 3분이라는 점을 인지하면, Webhook이 없는 환경에서 "왜 즉시 반영되지 않지?"라는 오해를 줄일 수 있습니다.
3.  **'Hard Refresh'는 최고의 디버깅 도구**: Argo CD가 Git과 상태가 맞지 않는다고 의심될 때, 'Hard Refresh'는 캐시 문제를 배제하고 실제 Git 리포지토리와의 차이점을 확인하는 가장 빠르고 효과적인 방법입니다.

## 관련 문서

- [시스템 아키텍처 - CI/CD 파이프라인](../../02-architecture/architecture.md#4-cicd-파이프라인)
- [운영 가이드 - ArgoCD 운영](../../04-operations/guides/operations-guide.md)
- [ArgoCD Health Degraded 문제](troubleshooting-argocd-health-degraded.md)

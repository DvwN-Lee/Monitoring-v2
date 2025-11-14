# [Troubleshooting] Argo CD Out of Sync 문제 해결

## 1. 문제 상황

Argo CD UI에서 관리 중인 Application의 상태가 초록색 `Synced`가 아닌 노란색 `OutOfSync`로 표시되는 문제가 발생했습니다. 이는 Git 리포지토리에 정의된 의도된 상태(Desired State)와 현재 Kubernetes 클러스터에 배포된 실제 상태(Live State)가 일치하지 않음을 의미하며, GitOps의 핵심 원칙이 깨졌다는 신호입니다.

## 2. 증상

-   Argo CD UI의 Application 카드에 노란색 `OutOfSync` 라벨이 표시됩니다.
-   Application 상세 페이지에 들어가면, 어떤 Kubernetes 리소스(Deployment, Service, ConfigMap 등)가 동기화되지 않았는지 목록으로 표시됩니다.
-   `auto-sync`가 활성화되어 있지 않은 경우, Git에 새로운 변경사항을 푸시하면 이 상태가 됩니다.
-   Git에는 변경사항이 없는데도 `OutOfSync` 상태가 되기도 합니다.

## 3. 원인 분석

`OutOfSync` 상태는 Git과 클러스터 간의 불일치를 의미하며, 다양한 원인으로 발생할 수 있습니다.

1.  **`kubectl`을 사용한 수동 변경 (가장 흔한 원인)**:
    *   Git 리포지토리를 통하지 않고, 터미널에서 `kubectl edit deployment <name>`, `kubectl scale --replicas=5 ...`, `kubectl patch ...` 등 명령어를 사용하여 클러스터의 리소스를 직접 변경한 경우입니다. 이는 GitOps 워크플로우를 우회하는 행동으로, Git에 기록된 상태와 실제 상태 간의 불일치를 즉시 유발합니다.

2.  **자동 동기화(Auto-Sync) 비활성화**:
    *   Argo CD Application에 자동 동기화(`automated`) 설정이 되어있지 않은 상태에서, Git 리포지토리에 새로운 변경사항이 푸시된 경우입니다. Argo CD는 변경을 감지하고 `OutOfSync` 상태로 전환하지만, 사용자의 수동 승인(SYNC 버튼 클릭)을 기다리게 됩니다.

3.  **다른 Kubernetes 컨트롤러에 의한 변경**:
    *   **HPA (HorizontalPodAutoscaler)**: 트래픽에 따라 Deployment의 `replicas` 수를 자동으로 조절하는 경우, Git에 정의된 `replicas` 값과 달라져 `OutOfSync`가 발생합니다.
    *   **VPA (VerticalPodAutoscaler)**: Pod의 CPU/Memory 요청(request)을 자동으로 변경하는 경우.
    *   특정 Operator가 관리하는 CRD(Custom Resource Definition)의 상태를 동적으로 변경하는 경우.

4.  **이전 동기화의 부분적 실패**:
    *   이전 동기화(Sync) 작업이 네트워크 문제, 권한 부족, 잘못된 매니페스트 등의 이유로 일부 리소스만 적용하고 실패한 경우, 클러스터는 불완전한 상태로 남아 `OutOfSync`가 될 수 있습니다.

## 4. 해결 방법

#### 1단계: 'DIFF' 기능으로 차이점 확인

-   가장 먼저 할 일은 **무엇이 다른지** 확인하는 것입니다.
-   Argo CD UI에서 `OutOfSync` 상태인 리소스를 클릭하고, 오른쪽의 **DIFF** 탭을 선택합니다.
-   왼쪽(DESIRED)에는 Git에 정의된 상태가, 오른쪽(LIVE)에는 클러스터의 실제 상태가 표시되어 어떤 필드가 다른지 명확하게 비교할 수 있습니다. 이를 통해 `kubectl`로 수정한 부분이나 HPA가 변경한 부분을 정확히 찾아낼 수 있습니다.

#### 2단계: 수동 동기화(SYNC) 실행

-   만약 `OutOfSync`의 원인이 Git의 최신 변경사항을 아직 적용하지 않았기 때문이라면, UI 상단의 **SYNC** 버튼을 클릭합니다.
-   동기화 옵션을 확인하고 'Synchronize'를 누르면 Argo CD가 Git의 상태를 클러스터에 적용하여 `Synced` 상태로 만듭니다.

#### 3단계: `selfHeal` 기능 활성화로 자동 복구 설정

-   `kubectl`을 이용한 수동 변경이나 다른 컨트롤러의 개입으로부터 Git 상태를 보호하고 싶을 때 사용하는 강력한 기능입니다.
-   Application의 동기화 정책(`syncPolicy`)에 `selfHeal: true`를 설정하면, Argo CD는 `OutOfSync` 상태를 감지했을 때 자동으로 Git의 상태로 되돌리는 동기화를 실행합니다.

    ```yaml
    # application.yaml
    spec:
      syncPolicy:
        automated:
          prune: true
          selfHeal: true # <-- selfHeal 활성화
    ```
    *주의: `selfHeal`은 의도치 않은 변경을 자동으로 롤백시키므로, HPA와 같이 의도적으로 상태를 변경하는 컨트롤러와 함께 사용할 때는 주의가 필요합니다.*

#### 4단계: 의도된 차이점 무시(`ignoreDifferences`)

-   HPA가 `replicas` 필드를 관리하는 것처럼, 특정 필드가 Git의 상태와 다른 것이 정상적인 동작일 경우, 해당 차이점을 Argo CD가 무시하도록 설정할 수 있습니다.
-   `spec.ignoreDifferences`에 무시할 리소스와 필드의 JSONPath를 지정합니다.

    ```yaml
    # application.yaml
    spec:
      ignoreDifferences:
      - group: "apps"
        kind: "Deployment"
        jsonPointers:
        - /spec/replicas # HPA가 관리하므로 이 필드의 차이는 무시
    ```

## 5. 교훈

1.  **`OutOfSync`는 GitOps 원칙 위반의 경고등**: 이 상태는 누군가 또는 무언가가 Git이 아닌 다른 방법으로 클러스터를 변경했음을 의미합니다. 클러스터의 모든 변경은 Git을 통해 이루어져야 한다는 원칙을 다시 한번 상기해야 합니다.
2.  **`kubectl` 직접 사용은 신중하게**: 긴급 장애 대응과 같은 예외적인 상황이 아니라면 `kubectl`로 리소스를 직접 수정하는 것은 지양해야 합니다. 만약 수정했다면, 최대한 빨리 해당 변경사항을 Git 리포지토리에도 반영하여 상태를 일치시켜야 합니다.
3.  **`selfHeal`은 강력하지만 이해가 필요하다**: `selfHeal`은 Git 상태와의 일관성을 강제하는 매우 유용한 기능이지만, 다른 컨트롤러와의 상호작용을 고려하지 않고 사용하면 의도치 않은 롤백을 유발할 수 있습니다. 동작 방식을 정확히 이해하고 적용해야 합니다.

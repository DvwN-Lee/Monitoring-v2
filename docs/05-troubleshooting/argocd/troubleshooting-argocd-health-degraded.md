---
version: 1.0
last_updated: 2025-11-15
author: Dongju Lee
---

# [Troubleshooting] Argo CD Health Degraded 문제 해결

## 1. 문제 상황

Argo CD Application이 성공적으로 동기화(`Synced`)되었음에도 불구하고, Application의 상태가 초록색 `Healthy`가 아닌 붉은색 `Degraded`(저하됨)로 표시되는 문제가 발생했습니다. 이는 Git 리포지토리의 매니페스트가 클러스터에 적용되기는 했으나, 그 결과로 생성된 하나 이상의 리소스가 비정상 상태에 빠졌음을 의미합니다.

## 2. 증상

-   Argo CD UI의 Application 카드에 붉은색 `Degraded` 라벨이 표시됩니다.
-   Application 상세 페이지에 들어가면, 트리의 특정 리소스(주로 Deployment, ReplicaSet, Pod)가 붉은색으로 표시되어 어떤 부분이 문제인지 시각적으로 알려줍니다.
-   애플리케이션이 정상적으로 동작하지 않거나, 일부 기능만 동작하는 등 서비스 장애로 이어질 수 있습니다.

## 3. 원인 분석

`Degraded` 상태는 Argo CD가 자체적인 상태 평가(Health Assessment) 로직에 따라 리소스의 건강 상태를 확인한 결과, '비정상'으로 판단했음을 의미합니다. Argo CD의 문제가 아니라, **배포된 애플리케이션 자체의 문제**일 가능성이 99%입니다.

주요 원인은 다음과 같습니다.

1.  **Pod 헬스체크 실패 (가장 흔한 원인)**:
    *   **`CrashLoopBackOff`**: Pod 내부의 컨테이너가 시작 직후 반복적으로 비정상 종료되고 있습니다. (애플리케이션 버그, 설정 오류 등)
    *   **`ImagePullBackOff`**: Kubernetes가 컨테이너 이미지를 레지스트리에서 가져오지 못하고 있습니다. (이미지 이름/태그 오타, 인증 실패 등)
    *   **`Pending`**: Pod가 스케줄링될 노드를 찾지 못하고 대기 중입니다. (클러스터 리소스 부족, 노드 셀렉터/어피니티 조건 불일치 등)
    *   **Liveness/Readiness Probe 실패**: 애플리케이션이 헬스체크(Probe)에 제 시간 안에 응답하지 못하여 Kubernetes가 비정상으로 판단하고 Pod를 재시작하거나 트래픽을 보내지 않습니다.

2.  **Deployment/ReplicaSet 문제**:
    *   Deployment가 목표한 `replicas` 수만큼의 `Ready` 상태인 Pod를 유지하지 못하고 있습니다. (예: 3개를 띄우도록 설정했으나 1개만 `Running`이고 2개는 `CrashLoopBackOff`인 경우)
    *   새로운 버전의 ReplicaSet으로 롤아웃(rollout)이 진행되다가 멈춘(stuck) 상태입니다.

3.  **Service/Ingress 문제**:
    *   Service가 가리키는 엔드포인트(Endpoints)가 하나도 없는 경우. (Service의 셀렉터가 Pod의 라벨과 일치하지 않음)
    *   Ingress 리소스 자체의 설정 오류 또는 관련 Ingress Controller의 문제.

4.  **PersistentVolumeClaim (PVC) 문제**:
    *   PVC가 적절한 PersistentVolume(PV)을 찾지 못해 스토리지에 바인딩되지 못하고 `Pending` 상태에 머무는 경우.

## 4. 해결 방법

`Degraded` 문제 해결의 핵심은 Argo CD UI에서 문제의 근원 리소스를 찾고, `kubectl`을 이용해 심층적인 원인을 파악하는 것입니다.

#### 1단계: Argo CD UI에서 문제 리소스 식별

-   `Degraded` 상태인 Application의 상세 페이지로 들어갑니다.
-   리소스 트리에서 붉은색으로 표시된 리소스를 찾습니다. 보통 Deployment나 ReplicaSet이 붉게 표시되고, 그 아래의 Pod 중 하나 이상이 문제의 근원입니다.
-   해당 Pod를 클릭하여 상태(예: `CrashLoopBackOff`)와 기본 이벤트 정보를 확인합니다.

#### 2단계: `kubectl describe`로 상세 이벤트 확인

-   문제의 원인으로 지목된 Pod의 이름을 확인하고, 터미널에서 `kubectl describe pod` 명령을 실행합니다.
-   이 명령어의 결과, 특히 맨 아래에 있는 **Events** 섹션은 문제 해결의 결정적인 단서를 제공합니다.
    -   `Back-off restarting failed container` -> `CrashLoopBackOff`
    -   `Failed to pull image ...` -> `ImagePullBackOff`
    -   `0/3 nodes are available: 3 Insufficient cpu` -> 리소스 부족으로 인한 `Pending`
    -   `Liveness probe failed ...` -> Liveness Probe 실패

    ```bash
    kubectl describe pod <pod-name> -n <namespace>
    ```

#### 3단계: `kubectl logs`로 애플리케이션 로그 확인

-   Pod의 상태가 `CrashLoopBackOff`인 경우, 애플리케이션 자체에 문제가 있는 것이므로 로그를 확인해야 합니다.
-   `kubectl logs` 명령어를 사용하여 컨테이너가 왜 비정상 종료되었는지 확인합니다.

    ```bash
    # 현재 컨테이너의 로그 (재시작 대기 중이라 로그가 없을 수 있음)
    kubectl logs <pod-name> -n <namespace>

    # 이전에 실패했던 컨테이너의 로그 (매우 중요!)
    kubectl logs --previous <pod-name> -n <namespace>
    ```
    로그에서 `Connection refused`, `NullPointerException`, `Config file not found` 등 구체적인 오류 메시지를 찾습니다.

#### 4단계: 원인에 따른 근본적인 조치

-   **애플리케이션 오류 (`CrashLoopBackOff`)**: 코드 버그 수정, 환경변수/ConfigMap 설정 확인 및 수정.
-   **이미지 pull 실패 (`ImagePullBackOff`)**: 이미지 이름과 태그가 올바른지, `imagePullSecrets`를 통해 프라이빗 레지스트리 인증 정보가 제대로 제공되었는지 확인.
-   **리소스 부족 (`Pending`)**: 클러스터 노드를 증설하거나, Pod의 리소스 요청(`resources.requests`)을 줄입니다.
-   **헬스체크 실패**: 애플리케이션이 헬스체크 경로로 정상 응답하는지 확인하고, Probe의 `initialDelaySeconds`, `timeoutSeconds` 등을 조정합니다.

## 5. 검증

해결책이 제대로 적용되었는지 확인하는 방법입니다.

### 1. Pod 상태 확인

모든 Pod가 Running 상태이고 재시작 없이 안정적으로 실행되는지 확인합니다.

```bash
kubectl get pods -n <namespace>

# 예상 결과:
# NAME                     READY   STATUS    RESTARTS   AGE
# app-xyz-5d4f7c9b8-abc12  1/1     Running   0          5m
```

### 2. ArgoCD Application Health 상태 확인

ArgoCD UI 또는 CLI를 통해 Application이 Healthy 상태로 전환되었는지 확인합니다.

```bash
kubectl get application -n argocd <app-name> -o jsonpath='{.status.health.status}'

# 예상 결과: Healthy
```

### 3. Deployment 롤아웃 상태 확인

Deployment의 롤아웃이 성공적으로 완료되었는지 확인합니다.

```bash
kubectl rollout status deployment/<deployment-name> -n <namespace>

# 예상 결과:
# deployment "<deployment-name>" successfully rolled out
```

### 4. 리소스 상세 이벤트 확인

이전에 발생했던 문제 이벤트가 해결되었고 새로운 정상 이벤트가 기록되었는지 확인합니다.

```bash
kubectl describe pod <pod-name> -n <namespace>

# Events 섹션에서 확인:
# - 이전 오류 이벤트(ImagePullBackOff, CrashLoopBackOff 등)가 사라짐
# - Started, Pulled, Created 등 정상 이벤트만 존재
```

### 5. 애플리케이션 기능 테스트

실제 애플리케이션이 정상적으로 동작하는지 기능 테스트를 수행합니다.

```bash
# 서비스 엔드포인트로 HTTP 요청 테스트
curl http://<service-endpoint>/health

# 예상 응답: HTTP 200 OK
```

## 6. 교훈

1.  **`Degraded`는 애플리케이션의 건강 적신호**: `Synced`가 '배포 완료'를 의미한다면, `Healthy`는 '배포 후 정상 동작'을 의미합니다. `Degraded` 상태는 Argo CD의 문제가 아니라, 배포된 애플리케이션이 아프다는 신호입니다.
2.  **Argo CD는 시작점, `kubectl`은 해결 도구**: 문제 해결은 Argo CD UI에서 시작하여 문제의 범위를 좁히고, 결국 `kubectl describe`와 `kubectl logs`라는 Kubernetes 네이티브 디버깅 도구를 통해 근본 원인을 찾아 해결하게 됩니다.
3.  **Health Assessment 로직 이해**: Argo CD가 어떤 기준으로 리소스의 건강을 판단하는지 알아두면(예: Deployment는 `availableReplicas`와 `replicas`가 일치하는지 확인), `Degraded` 상태의 원인을 더 빨리 추측할 수 있습니다.

## 관련 문서

- [시스템 아키텍처 - CI/CD 파이프라인](../../02-architecture/architecture.md#4-cicd-파이프라인)
- [운영 가이드 - ArgoCD 운영](../../04-operations/guides/operations-guide.md)
- [ArgoCD Git 감지 실패](troubleshooting-argocd-git-detection.md)
- [서비스 엔드포인트 누락](../kubernetes/troubleshooting-service-endpoint-missing.md)

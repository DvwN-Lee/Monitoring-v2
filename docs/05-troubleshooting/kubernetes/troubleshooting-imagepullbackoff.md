---
version: 1.0
last_updated: 2025-11-15
author: Dongju Lee
---

# [Troubleshooting] ImagePullBackOff 문제 해결

## 1. 문제 상황

새로운 버전의 애플리케이션을 배포했으나, Pod가 정상적으로 생성되지 않고 `ImagePullBackOff` 또는 `ErrImagePull` 상태에 머무르는 문제가 발생했습니다. 이로 인해 새로운 버전의 애플리케이션이 Cluster에 배포되지 못했습니다.

## 2. 증상

`kubectl get pods` 명령어를 실행하면, Pod의 `STATUS`가 `ImagePullBackOff` 또는 `ErrImagePull`로 나타납니다.

```bash
$ kubectl get pods
NAME                            READY   STATUS             RESTARTS   AGE
user-service-6c8f7d4f9c-abcde   0/1     ImagePullBackOff   0          5m
```

`ImagePullBackOff`는 Kubelet이 Container를 실행하기 위해 필요한 이미지를 Container 레지스트리(예: Docker Hub, Harbor, ECR)로부터 가져오는(pull) 데 실패했음을 의미합니다. Kubernetes는 재시도 정책에 따라 이미지 가져오기를 반복적으로 시도하며, 실패가 계속될 경우 `BackOff` 상태에 들어갑니다.

`kubectl describe pod` 명령어로 상세 정보를 확인하면, `Events` 섹션에서 이미지 가져오기 실패에 대한 구체적인 원인을 찾을 수 있습니다.

```bash
$ kubectl describe pod user-service-6c8f7d4f9c-abcde
...
Events:
  Type     Reason     Age                From               Message
  ----     ------     ----               ----               -------
  Normal   Scheduled  7m                 default-scheduler  Successfully assigned default/user-service-6c8f7d4f9c-abcde to node-1
  Normal   Pulling    5m (x4 over 7m)    kubelet, node-1    Pulling image "my-private-repo/user-service:v1.2-non-existent"
  Warning  Failed     5m (x4 over 7m)    kubelet, node-1    Failed to pull image "my-private-repo/user-service:v1.2-non-existent": rpc error: code = Unknown desc = Error response from daemon: manifest for my-private-repo/user-service:v1.2-non-existent not found: manifest unknown: manifest unknown
  Warning  Failed     5m (x4 over 7m)    kubelet, node-1    Error: ErrImagePull
  Normal   BackOff    4m (x6 over 7m)    kubelet, node-1    Back-off pulling image "my-private-repo/user-service:v1.2-non-existent"
  Warning  Failed     3m (x7 over 7m)    kubelet, node-1    Error: ImagePullBackOff
```

## 3. 원인 분석

`describe pod` 이벤트 로그를 통해 파악할 수 있는 주요 원인은 다음과 같습니다.

1.  **이미지 이름 또는 태그 오류**:
    *   Deployment에 지정된 이미지 이름이나 태그가 레지스트리에 실제로 존재하지 않는 경우. (예: 오타, `latest` 태그의 부재)
    *   `manifest for ... not found` 메시지는 해당 이미지:태그 조합이 레지스트리에 없음을 명확히 나타냅니다.

2.  **Private Registry 접근 권한 문제**:
    *   Private Registry(사설 레지스트리)에 접근하기 위한 인증 정보(credentials)가 Cluster에 설정되지 않은 경우.
    *   인증 정보를 담고 있는 `imagePullSecrets`가 Pod의 ServiceAccount나 Pod Spec에 제대로 명시되지 않은 경우.
    *   `describe pod` 이벤트에 `unauthorized: authentication required` 와 같은 메시지가 표시됩니다.

3.  **레지스트리 주소 오류 또는 네트워크 문제**:
    *   이미지 이름에 포함된 레지스트리 주소 자체가 잘못된 경우.
    *   Cluster Node에서 레지스트리로의 네트워크 경로에 문제가 있거나, 방화벽에 의해 접근이 차단된 경우.

4.  **Docker Hub Rate Limit 초과**: Docker Hub는 익명 사용자 또는 무료 사용자에 대해 시간당 이미지 pull 횟수를 제한합니다. Cluster에서 단시간에 많은 이미지를 pull 할 경우 이 제한에 걸려 `toomanyrequests` 오류가 발생할 수 있습니다.

## 4. 해결 방법

#### 1단계: `describe pod`로 정확한 이벤트 메시지 확인

가장 먼저 `kubectl describe pod <pod-name>`을 실행하여 `Events` 섹션의 `Failed` 이벤트 메시지를 정독합니다. `manifest not found`, `authentication required` 등 메시지를 통해 원인을 90% 이상 특정할 수 있습니다.

#### 2단계: 이미지 이름 및 태그 확인

`manifest not found` 오류인 경우, Deployment YAML 파일에 정의된 `image:` 필드의 값을 다시 한번 확인합니다.
*   이미지 이름과 태그에 오타가 없는지 확인합니다.
*   해당 이미지와 태그가 Container 레지스트리에 실제로 존재하는지 웹 UI나 CLI(예: `docker pull`)를 통해 직접 확인합니다.
*   CI/CD Pipeline에서 이미지 빌드 및 푸시가 정상적으로 완료되었는지 확인합니다.

#### 3단계: Private Registry 인증 정보(Secret) 확인 및 설정

`authentication required` 오류인 경우, 다음 절차를 따릅니다.

*   **`imagePullSecrets` 존재 확인**: Private Registry에 접근하기 위한 인증 정보를 담은 Secret이 Namespace에 존재하는지 확인합니다.

    ```bash
    kubectl get secret <my-registry-secret> -n <namespace>
    ```

*   **Secret 생성**: Secret이 없다면, `kubectl create secret docker-registry` 명령어로 생성합니다.

    ```bash
    kubectl create secret docker-registry <my-registry-secret> \
      --docker-server=<your-registry-server> \
      --docker-username=<your-username> \
      --docker-password=<your-password> \
      --docker-email=<your-email> \
      -n <namespace>
    ```

*   **Pod 또는 ServiceAccount에 Secret 연결**:
    1.  **(권장)** `default` ServiceAccount 또는 애플리케이션이 사용하는 ServiceAccount에 Secret을 연결합니다. 이렇게 하면 해당 Namespace의 모든 Pod에 자동으로 `imagePullSecrets`가 적용됩니다.
        ```bash
        kubectl patch serviceaccount default -p '{"imagePullSecrets": [{"name": "<my-registry-secret>"}]}' -n <namespace>
        ```
    2.  또는 Deployment YAML의 Pod Spec에 직접 `imagePullSecrets`를 명시할 수도 있습니다.
        ```yaml
        spec:
          template:
            spec:
              containers:
              - name: user-service
                image: ...
              imagePullSecrets:
              - name: <my-registry-secret>
        ```

#### 4단계: 검증

문제를 수정한 후, 실패했던 Pod를 삭제하여 Deployment가 새로운 Pod를 생성하도록 합니다.

```bash
kubectl delete pod <pod-name>
```

새로 생성된 Pod가 `ContainerCreating`을 거쳐 `Running` 상태로 정상 전환되는지 `kubectl get pods -w`로 확인합니다.

## 5. 교훈

1.  **`describe pod`는 필수**: `ImagePullBackOff`는 현상일 뿐, 원인은 `describe pod`의 이벤트 메시지에 명확히 드러납니다. Pod 생성 실패 시 `describe`를 가장 먼저 확인하는 것이 기본입니다.
2.  **이미지 태그는 명시적으로**: `latest` 태그는 개발 중에는 편리하지만, 운영 환경에서는 예측 불가능한 문제를 일으킬 수 있습니다. 항상 `v1.2.3`과 같이 변하지 않는(immutable) 태그를 사용하는 것이 안정적입니다.
3.  **인증은 ServiceAccount에**: `imagePullSecrets`를 개별 Pod마다 설정하는 것은 번거롭고 실수를 유발하기 쉽습니다. Namespace의 `default` ServiceAccount에 연결해두면 해당 Namespace에서는 인증 문제를 신경 쓸 필요가 없어집니다.

## 관련 문서

- [시스템 아키텍처 - Solid Cloud 구성](../../02-architecture/architecture.md#7-solid-cloud-구성)
- [Secret 관리 가이드](../../04-operations/guides/SECRET_MANAGEMENT.md)
- [DockerHub 로그인 실패](../ci-cd/troubleshooting-dockerhub-login-failure.md)

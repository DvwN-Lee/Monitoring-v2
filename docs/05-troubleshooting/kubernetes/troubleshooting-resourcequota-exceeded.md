---
version: 1.0
last_updated: 2025-11-15
author: Dongju Lee
---

# [Troubleshooting] Kubernetes ResourceQuota 초과 문제 해결

## 1. 문제 상황

새로운 Pod를 배포하거나 기존 Deployment의 `replicas` 수를 늘리는 과정에서 Pod가 생성되지 않고 `Pending` 상태에 머무르는 문제가 발생했습니다. `kubectl describe pod`를 통해 확인한 결과, 네임스페이스에 설정된 `ResourceQuota`를 초과하여 Pod 생성이 거부되고 있었습니다.

## 2. 증상

`kubectl get pods`로 확인 시 새로운 Pod가 생성되지 않거나, 생성 시도 중인 Pod가 `Pending` 상태로 남아있습니다.

`kubectl describe pod <pod-name>` 또는 `kubectl describe replicaset <replicaset-name>` 명령어를 실행하면, 이벤트(Events) 섹션에 `FailedCreate` 또는 `FailedScheduling` 이벤트와 함께 `ResourceQuota` 초과 관련 메시지가 나타납니다.

```bash
$ kubectl describe replicaset user-service-xxxxxxxx
...
Events:
  Type     Reason        Age   From                   Message
  ----     ------        ----  ----                   -------
  Warning  FailedCreate  2m    replicaset-controller  Error creating: pods "user-service-xxxxxxxx-" is forbidden: exceeded quota: project-quota, requested: limits.cpu=1, used: limits.cpu=7, limited: limits.cpu=8
```

위 메시지는 `project-quota`라는 이름의 `ResourceQuota` 오브젝트에 의해 CPU `limits`가 8로 제한되어 있는데, 이미 7을 사용 중인 상태에서 1을 추가로 요청하여 할당량을 초과했음을 의미합니다.

## 3. 원인 분석

1.  **네임스페이스 리소스 할당량 초과**: 관리자가 네임스페이스별로 리소스 사용을 제한하기 위해 설정한 `ResourceQuota`의 한도에 도달한 것이 가장 직접적인 원인입니다. Quota는 CPU/메모리의 `requests`/`limits` 총합, 스토리지(PVC) 개수, 서비스나 시크릿 같은 오브젝트 수 등 다양한 항목에 대해 설정될 수 있습니다.

2.  **Istio Sidecar의 리소스 요구량**: Istio와 같은 서비스 메쉬를 사용하는 경우, 모든 Pod에 `istio-proxy`라는 사이드카 컨테이너가 자동으로 주입됩니다. 이 사이드카는 자체적으로 CPU와 메모리 리소스를 요구(`requests`)하고 한도(`limits`)를 가집니다. 애플리케이션 컨테이너의 리소스만 고려하고 사이드카의 리소스를 간과하면 예상치 못하게 Quota를 빠르게 소진할 수 있습니다. 특히 Istio의 기본 CPU `limits`는 비교적 높게 설정되어 있을 수 있습니다.

3.  **리소스 요청/한도(requests/limits) 미설정**: `ResourceQuota`가 적용된 네임스페이스에서는 모든 컨테이너에 대해 `requests`와 `limits`를 명시적으로 설정해야 하는 경우가 많습니다. 만약 이를 누락하면 Pod 생성 자체가 거부될 수 있습니다.

## 4. 해결 방법

#### 1단계: 네임스페이스의 ResourceQuota 확인

먼저 해당 네임스페이스에 어떤 `ResourceQuota`가 적용되어 있고, 현재 사용량은 얼마인지 확인합니다.

```bash
# 네임스페이스의 모든 ResourceQuota 오브젝트 이름 확인
$ kubectl get resourcequota -n <namespace>
NAME            AGE
project-quota   30d

# 특정 ResourceQuota의 상세 내용 확인
$ kubectl describe resourcequota project-quota -n <namespace>
Name:         project-quota
Namespace:    <namespace>
Resource      Used    Hard
--------      ----    ----
limits.cpu    7       8      # CPU 한도: 총 8코어 중 7코어 사용 중
limits.memory 14Gi    16Gi   # 메모리 한도: 총 16Gi 중 14Gi 사용 중
requests.cpu  3500m   4      # CPU 요청량: 총 4코어 중 3.5코어 사용 중
pods          20      25     # Pod 개수: 총 25개 중 20개 사용 중
```

`Used`와 `Hard` 값을 비교하여 어떤 리소스가 한도에 도달했는지 정확히 파악합니다.

#### 2단계: 리소스 최적화 (권장)

Quota를 무작정 늘리기 전에, 현재 네임스페이스 내에서 리소스를 비효율적으로 사용하고 있는 Pod가 있는지 검토합니다.

*   **불필요한 Pod 정리**: 사용하지 않는 테스트용 또는 임시 Pod를 삭제합니다.
*   **리소스 요청/한도 현실화**: `kubectl top pods` 명령어로 실제 리소스 사용량을 확인하고, 과도하게 설정된 `requests`나 `limits`를 현실적인 값으로 낮춥니다. 특히 개발 환경에서는 `limits`를 `requests`와 비슷하게 설정하여 불필요한 Quota 점유를 줄일 수 있습니다.
*   **Istio Sidecar 리소스 조정**: Istio를 사용한다면, 사이드카의 리소스 요구량을 조정할 수 있습니다. 이는 `istio-proxy`의 기본 설정을 변경하거나, Pod에 어노테이션을 추가하여 개별적으로 조정할 수 있습니다.

    **Pod 어노테이션으로 사이드카 리소스 조정 예시:**
    ```yaml
    apiVersion: apps/v1
    kind: Deployment
    metadata:
      name: user-service
    spec:
      template:
        metadata:
          annotations:
            # istio-proxy 사이드카의 리소스 설정
            "sidecar.istio.io/proxyCPU": "100m"
            "sidecar.istio.io/proxyMemory": "128Mi"
            "sidecar.istio.io/proxyCPULimit": "200m"
            "sidecar.istio.io/proxyMemoryLimit": "256Mi"
    ...
    ```

#### 3단계: ResourceQuota 상향 조정

리소스 최적화 후에도 추가 리소스가 반드시 필요하다면, 클러스터 관리자에게 `ResourceQuota`의 `Hard` 한도를 늘려달라고 요청해야 합니다. 이는 일반적으로 인프라 용량과 비용에 영향을 미치므로 신중하게 결정해야 합니다.

관리자는 `kubectl edit resourcequota <quota-name> -n <namespace>` 명령어로 Quota를 수정할 수 있습니다.

**ResourceQuota YAML 수정 예시:**
```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: project-quota
spec:
  hard:
    limits.cpu: "12"      # 8에서 12로 상향 조정
    limits.memory: "24Gi" # 16Gi에서 24Gi로 상향 조정
    requests.cpu: "6"
    pods: "30"
```

#### 4단계: 검증

Quota가 조정되거나 리소스 사용량이 줄어든 후, 이전에 실패했던 Pod 배포를 다시 시도합니다. `kubectl get pods`를 통해 새로운 Pod가 정상적으로 `Running` 상태가 되는지 확인합니다.

## 5. 교훈

1.  **Quota는 공유 자원의 보호 장치**: `ResourceQuota`는 특정 팀이나 애플리케이션이 클러스터 전체 리소스를 독점하는 것을 방지하는 중요한 기능입니다. Quota 초과 오류는 '실패'가 아니라, 할당된 자원을 모두 소진했다는 '알림'으로 이해해야 합니다.
2.  **눈에 보이지 않는 비용, 사이드카**: 서비스 메쉬, 모니터링 에이전트 등 사이드카 패턴으로 주입되는 컨테이너들은 애플리케이션의 전체 리소스 요구량을 크게 증가시킬 수 있습니다. Pod 배포 시 항상 모든 컨테이너의 리소스 요구량을 종합적으로 고려해야 합니다.
3.  **최적화 우선, 증설은 차선**: 리소스 부족 문제에 직면했을 때, 가장 먼저 취해야 할 행동은 현재 상태를 최적화하는 것입니다. 불필요한 리소스를 줄이는 것만으로도 많은 경우 문제를 해결하고 비용을 절감할 수 있습니다.

## 관련 문서

- [시스템 아키텍처 - Solid Cloud 구성](../../02-architecture/architecture.md#7-solid-cloud-구성)
- [운영 가이드](../../04-operations/guides/operations-guide.md)

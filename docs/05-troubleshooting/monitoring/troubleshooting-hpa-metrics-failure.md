---
version: 1.0
last_updated: 2025-11-15
author: Dongju Lee
---

# [Troubleshooting] HPA 메트릭 수집 실패 문제 해결

## 1. 문제 상황

애플리케이션의 부하에 따라 Pod 수를 자동으로 조절하기 위해 HPA(Horizontal Pod Autoscaler)를 설정했지만, HPA가 메트릭을 수집하지 못하여 오토스케일링이 전혀 동작하지 않는 문제가 발생했습니다. `kubectl get hpa` 명령어의 `TARGETS` 필드에 `unknown` 또는 `<pending>`이 표시되었습니다.

## 2. 증상

HPA의 상태를 확인했을 때, 현재 메트릭 사용량이 표시되지 않고 `unknown`으로 나타났습니다.

```bash
$ kubectl get hpa user-service-hpa
NAME               REFERENCE                   TARGETS         MINPODS   MAXPODS   REPLICAS   AGE
user-service-hpa   Deployment/user-service     <unknown>/80%   2         10        2          5m
```

`kubectl describe hpa` 명령어로 상세 정보를 확인한 결과, HPA 컨트롤러가 메트릭을 가져오는 데 실패했다는 내용의 `Warning` 이벤트가 기록되어 있었습니다.

```bash
$ kubectl describe hpa user-service-hpa
...
Events:
  Type     Reason                        Age   From                       Message
  ----     ------                        ----  ----                       -------
  Warning  FailedGetResourceMetric       2m    horizontal-pod-autoscaler  failed to get cpu utilization: missing request for cpu on container user-service in pod user-service-xxxxxxxx-xxxxx
  Warning  FailedComputeReplicasForMetric  2m    horizontal-pod-autoscaler  invalid metrics (1 invalid out of 1), first error is: failed to get cpu utilization: missing request for cpu on container user-service in pod user-service-xxxxxxxx-xxxxx
```

또는 Metrics Server 자체가 불안정할 경우 다음과 같은 메시지가 나타날 수 있습니다.

```bash
Events:
  Type     Reason                   Age   From                       Message
  ----     ------                   ----  ----                       -------
  Warning  FailedGetResourceMetric  3m    horizontal-pod-autoscaler  did not receive metrics for any ready pods
```

## 3. 원인 분석

1.  **Pod 리소스 요청(requests) 미설정**: HPA가 CPU 또는 메모리 사용률(utilization)을 기준으로 스케일링하려면, 대상 Pod의 Container에 반드시 해당 리소스의 `requests` 값이 설정되어 있어야 합니다. HPA는 `(현재 사용량 / 요청량)` 공식을 통해 사용률을 계산하는데, `requests`가 없으면 분모가 0이 되므로 계산이 불가능합니다. `describe hpa` 이벤트의 `missing request for cpu` 메시지가 이 경우에 해당합니다.

2.  **Metrics Server 비정상 동작**: HPA는 메트릭 수집을 위해 Metrics Server에 의존합니다. 만약 Metrics Server가 Cluster에 설치되지 않았거나, 설치되었더라도 Kubelet 통신 문제, TLS 인증서 오류 등으로 정상 동작하지 않으면 HPA는 메트릭을 가져올 수 없습니다. 이 경우 `kubectl top nodes` 명령어 또한 실패합니다.

3.  **HPA와 대상 리소스 간의 레이블/이름 불일치**: HPA의 `scaleTargetRef`에 지정된 Deployment, StatefulSet 등의 이름이나 종류가 실제 대상과 일치하지 않으면 HPA는 어떤 Pod를 타겟으로 해야 할지 찾지 못합니다.

4.  **Pod가 Ready 상태가 아님**: HPA는 `Ready` 상태인 Pod들만을 대상으로 메트릭을 수집합니다. 만약 Pod들이 `CrashLoopBackOff`, `ImagePullBackOff`, 또는 Readiness Probe 실패 등으로 인해 `Ready` 상태가 아니라면 메트릭 수집 대상에서 제외되어 `did not receive metrics for any ready pods`와 같은 오류가 발생할 수 있습니다.

## 4. 해결 방법

#### 1단계: `describe hpa`로 정확한 원인 파악

가장 먼저 `kubectl describe hpa`를 실행하여 이벤트(Events) 섹션을 확인합니다. `missing request` 메시지가 있는지, 아니면 메트릭을 받지 못했다는 일반적인 실패 메시지인지 파악하는 것이 중요합니다.

#### 2단계: Pod 리소스 요청(requests) 설정

`missing request` 오류가 확인되면, HPA의 대상이 되는 Deployment(또는 StatefulSet 등)의 YAML 설정 파일을 열어 Container 스펙에 `resources.requests`를 추가하거나 수정합니다.

**Deployment YAML 수정 예시:**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: user-service
spec:
  replicas: 2
  selector:
    matchLabels:
      app: user-service
  template:
    metadata:
      labels:
        app: user-service
    spec:
      containers:
      - name: user-service
        image: my-repo/user-service:v1.0
        ports:
        - containerPort: 8080
        resources:
          requests:
            cpu: "200m"      # CPU 요청량 설정
            memory: "256Mi"  # 메모리 요청량 설정 (메모리 기반 HPA의 경우)
          limits:
            cpu: "400m"
            memory: "512Mi"
```

수정 후 `kubectl apply -f <deployment-file.yaml>` 명령어로 변경사항을 적용합니다. Pod들이 재시작된 후 HPA가 메트릭을 정상적으로 수집하기 시작합니다.

#### 3단계: Metrics Server 상태 점검

`describe hpa`에서 일반적인 메트릭 수집 실패 오류가 발생하고, 리소스 요청도 이미 설정되어 있다면 Metrics Server의 상태를 점검해야 합니다.

```bash
# 1. Metrics Server가 설치되어 있는지 확인
kubectl get deployment metrics-server -n kube-system

# 2. Metrics Server Pod가 정상 실행 중인지 확인
kubectl get pods -n kube-system -l k8s-app=metrics-server

# 3. kubectl top 명령어로 메트릭 수집 기능 자체를 테스트
kubectl top nodes
```

만약 `kubectl top nodes`가 실패한다면, 이는 HPA 문제가 아니라 Metrics Server 자체의 문제이므로 **"[Troubleshooting] Kubernetes Metrics Server 동작 불가 문제 해결"** 가이드에 따라 문제를 해결해야 합니다.

#### 4단계: 검증

모든 조치가 완료된 후, 잠시 기다렸다가 `kubectl get hpa`를 다시 실행하여 `TARGETS` 필드에 현재 CPU 사용률이 정상적으로 표시되는지 확인합니다.

```bash
$ kubectl get hpa user-service-hpa
NAME               REFERENCE                   TARGETS   MINPODS   MAXPODS   REPLICAS   AGE
user-service-hpa   Deployment/user-service     15%/80%   2         10        2          15m
```

부하 테스트 툴(예: `hey`, `k6`)을 사용하여 의도적으로 부하를 발생시켰을 때, `REPLICAS` 수가 설정한 `MAXPODS`까지 자동으로 증가하는지 최종 확인합니다.

## 5. 교훈

1.  **HPA의 전제 조건: 리소스 요청**: CPU/메모리 사용률 기반 HPA를 사용하려면 반드시 Pod Spec에 `resources.requests`를 명시해야 합니다. 이는 HPA의 가장 기본적인 요구사항이자 가장 흔한 실수 중 하나입니다.
2.  **HPA는 의존성이 높은 오브젝트**: HPA는 단독으로 동작하지 않고 API Server, Metrics Server, 그리고 대상 워크로드(Deployment 등)와 긴밀하게 연동됩니다. 문제가 발생하면 HPA 자체뿐만 아니라 관련된 모든 구성 요소의 상태를 종합적으로 점검해야 합니다.
3.  **`describe`는 최고의 디버깅 도구**: HPA 이벤트 로그는 문제의 원인을 매우 명확하게 알려주는 경우가 많습니다. `TARGETS`가 `unknown`일 때 가장 먼저 확인할 것은 `kubectl describe hpa`입니다.

## 관련 문서

- [시스템 아키텍처 - 모니터링 및 로깅](../../02-architecture/architecture.md#5-모니터링-및-로깅)
- [운영 가이드](../../04-operations/guides/operations-guide.md)
- [Metrics Server 실패](troubleshooting-metrics-server-failure.md)

---
version: 1.0
last_updated: 2025-11-15
author: Dongju Lee
---

# [Troubleshooting] Pod CrashLoopBackOff 문제 해결

## 1. 문제 상황

애플리케이션을 배포한 후 `kubectl get pods` 명령어로 상태를 확인했을 때, 특정 Pod가 `Running` 상태로 전환되지 못하고 `CrashLoopBackOff` 상태에 빠지는 현상이 발생했습니다. 이로 인해 해당 애플리케이션은 외부 요청을 전혀 처리할 수 없었습니다.

## 2. 증상

`kubectl get pods` 명령어 실행 시, `STATUS`가 `CrashLoopBackOff`로 표시되고 `RESTARTS` 횟수가 계속 증가합니다.

```bash
$ kubectl get pods
NAME                            READY   STATUS             RESTARTS   AGE
auth-service-5f7b64f8f6-z8g9h   0/1     CrashLoopBackOff   5          10m
```

`CrashLoopBackOff`는 Pod의 Container가 시작된 직후 비정상적으로 종료(crash)되어, Kubernetes가 재시작 정책에 따라 Container를 계속 다시 시작하려고 시도하지만 반복적으로 실패하는 상태를 의미합니다. Kubernetes는 재시작 시도 사이의 간격을 점차 늘리게 되는데, 이를 "BackOff"라고 합니다.

## 3. 원인 분석

`CrashLoopBackOff`는 Container 자체가 실행되지 못하는 `ImagePullBackOff`와 달리, **Container는 시작되었지만 내부의 애플리케이션이 비정상적으로 종료**될 때 발생합니다. 주요 원인은 다음과 같습니다.

1.  **애플리케이션 시작 오류**:
    *   코드 자체의 버그로 인해 시작 과정에서 처리되지 않은 예외(exception)가 발생하는 경우.
    *   필수적인 파일이나 디렉토리가 없어 애플리케이션이 시작되지 못하는 경우.

2.  **설정(Configuration) 오류**:
    *   **환경변수 누락 또는 오류**: 애플리케이션이 의존하는 필수 환경변수가 설정되지 않았거나, 값이 잘못되어 시작에 실패하는 경우.
    *   **ConfigMap/Secret 누락 또는 잘못된 마운트**: 설정 파일이나 인증서 등을 담고 있는 ConfigMap 또는 Secret이 존재하지 않거나, Pod에 잘못된 경로로 마운트되어 애플리케이션이 이를 찾지 못하는 경우.

3.  **의존 서비스 연결 실패**:
    *   데이터베이스, 캐시, 다른 Microservice 등 애플리케이션이 시작 시점에 반드시 연결해야 하는 외부 Service에 접속하지 못하는 경우. (예: 잘못된 DB 호스트 주소, 인증 실패)

4.  **리소스 부족**: Container에 할당된 메모리(`limits.memory`)가 너무 적어, 애플리케이션이 시작 중에 메모리 부족(Out of Memory)으로 인해 강제 종료(OOMKilled)되는 경우. `describe pod`에서 `Reason: OOMKilled`로 확인할 수 있습니다.

5.  **Liveness/Readiness Probe 실패**: Liveness Probe가 잘못 설정되어 정상적인 애플리케이션을 비정상으로 판단하고 계속 재시작시키는 경우.

## 4. 해결 방법

#### 1단계: `kubectl logs`로 애플리케이션 로그 확인

`CrashLoopBackOff` 문제 해결의 가장 중요한 첫 단계는 **애플리케이션의 로그를 확인**하는 것입니다. Container가 왜 비정상적으로 종료되었는지에 대한 직접적인 단서가 로그에 남아있습니다.

```bash
# 현재 비정상 종료된 Container의 로그 확인
$ kubectl logs <pod-name>

# 이전(previous)에 비정상 종료되었던 Container의 로그 확인 (매우 유용)
$ kubectl logs --previous <pod-name>
```

`--previous` 플래그는 현재 재시작을 기다리는 Container가 아니라, 바로 직전에 실패했던 Container의 로그를 보여주므로 원인 파악에 결정적입니다.

**로그 분석 예시:**
*   `Error: connect ECONNREFUSED 127.0.0.1:6379`: Redis 연결 실패
*   `FATAL: password authentication failed for user "postgres"`: 데이터베이스 인증 실패
*   `NullPointerException: Cannot invoke "String.length()" because "db.host" is null`: `db.host` 설정값이 누락됨
*   `Error: listen EADDRINUSE: address already in use :::8080`: 포트 충돌

#### 2단계: `kubectl describe pod`로 Pod 상태 및 이벤트 확인

로그만으로 원인 파악이 어렵다면, `describe pod` 명령어로 더 넓은 범위의 정보를 확인합니다.

```bash
kubectl describe pod <pod-name>
```

여기서 확인할 주요 정보는 다음과 같습니다.
*   **Events**: Pod의 생명주기 동안 발생한 이벤트들.
*   **State / Last State**: Container의 현재 상태와 이전 상태. `Last State`의 `Reason`과 `Exit Code`는 중요한 단서입니다. (예: `Reason: OOMKilled`, `Exit Code: 137` -> 메모리 부족)
*   **Environment**: Container에 설정된 환경변수들이 올바른지 확인합니다.
*   **Volumes / Mounts**: ConfigMap, Secret, PVC 등이 올바르게 마운트되었는지 경로를 확인합니다.

#### 3단계: 원인에 따른 조치

*   **설정 오류 시**:
    *   Deployment YAML 파일, ConfigMap, Secret의 값이 올바른지 다시 한번 확인하고 수정합니다.
    *   `kubectl apply`로 변경사항을 적용하여 Pod를 새로 배포합니다.

*   **의존 서비스 연결 실패 시**:
    *   연결하려는 서비스(예: `redis-service`, `postgres-db`)가 정상적으로 실행 중인지 `kubectl get pods,svc`로 확인합니다.
    *   Service의 ClusterIP나 DNS 이름이 올바른지 확인합니다. (예: `<service-name>.<namespace>.svc.cluster.local`)
    *   네트워크 정책(NetworkPolicy)에 의해 통신이 차단되지는 않았는지 확인합니다.

*   **리소스 부족(OOMKilled) 시**:
    *   Deployment YAML에서 해당 Container의 `resources.limits.memory` 값을 증설하고 재배포합니다.

#### 4단계: 검증

수정 사항을 배포한 후, `kubectl get pods -w` 명령어로 Pod의 상태 변화를 실시간으로 관찰하며 `Running` 상태로 안정적으로 전환되는지 확인합니다.

## 5. 교훈

1.  **로그, 로그, 로그**: `CrashLoopBackOff`의 원인은 90% 이상 애플리케이션 로그에 있습니다. `kubectl logs`와 `kubectl logs --previous`를 가장 먼저 확인하는 습관이 중요합니다.
2.  **`describe pod`는 종합 진단서**: 로그로 해결되지 않을 때, `describe pod`는 환경변수, 볼륨 마운트, 이벤트 등 Pod와 관련된 모든 컨텍스트를 제공하므로 종합적인 상황 파악에 필수적입니다.
3.  **CrashLoopBackOff는 결과이지 원인이 아니다**: `CrashLoopBackOff`는 "Container가 반복적으로 비정상 종료되고 있다"는 상태를 나타내는 Kubernetes의 표현일 뿐, 실제 원인은 애플리케이션 내부에 있음을 명심해야 합니다.

## 관련 문서

- [시스템 아키텍처 - Solid Cloud 구성](../../02-architecture/architecture.md#7-solid-cloud-구성)
- [운영 가이드](../../04-operations/guides/operations-guide.md)

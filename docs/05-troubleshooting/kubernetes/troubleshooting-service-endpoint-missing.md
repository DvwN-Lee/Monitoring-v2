---
version: 1.0
last_updated: 2025-11-15
author: Dongju Lee
---

# [Troubleshooting] Service Endpoint 미생성 문제 해결

## 1. 문제 상황

애플리케이션 Pod와 Service를 모두 배포했지만, Service의 ClusterIP나 DNS 이름으로 접근했을 때 연결이 되지 않는 문제가 발생했습니다. `kubectl get endpoints <service-name>` 명령어로 확인 결과, Service에 연결된 Endpoint가 아무것도 없는 것으로 나타났습니다.

## 2. 증상

`kubectl describe service` 또는 `kubectl get endpoints` 명령어로 Service의 상태를 확인했을 때, `Endpoints` 필드가 `<none>`으로 표시됩니다.

```bash
$ kubectl describe svc user-service
Name:              user-service
Namespace:         default
Labels:            <none>
Annotations:       <none>
Selector:          app=user-service
Type:              ClusterIP
IP Family Policy:  SingleStack
IP Families:       IPv4
IP:                10.100.200.1
IPs:               10.100.200.1
Port:              <unset>  80/TCP
TargetPort:        8080/TCP
Endpoints:         <none>  # Endpoint가 없음
Session Affinity:  None
Events:            <none>
```

이 상태에서는 `curl http://user-service` 또는 `curl http://10.100.200.1`과 같이 Service를 통해 Pod에 접근하려는 모든 시도가 실패합니다.

## 3. 원인 분석

Service가 Endpoint를 자동으로 생성하고 관리하기 위해서는 몇 가지 조건이 충족되어야 합니다. Endpoint가 생성되지 않는 주요 원인은 다음과 같습니다.

1.  **Service Selector와 Pod Label 불일치**: Service의 `selector`에 지정된 레이블과, 트래픽을 받아야 할 Pod들의 `metadata.labels`가 일치하지 않는 경우입니다. Kubernetes는 이 레이블 매칭을 통해 어떤 Pod들을 Service에 연결할지 결정하는데, 일치하는 Pod가 하나도 없으면 Endpoint가 생성되지 않습니다. 이는 가장 흔한 원인입니다.

2.  **Pod가 `Ready` 상태가 아님**: Service는 기본적으로 `Ready` 상태에 있는 Pod들만 Endpoint 목록에 추가합니다. 만약 Pod가 `CrashLoopBackOff`, `ImagePullBackOff` 상태에 있거나, Readiness Probe에 실패하여 `Ready` 상태가 아니라면, Service의 `selector`와 Pod의 `label`이 일치하더라도 Endpoint에 포함되지 않습니다.

3.  **Service와 Pod의 Namespace 불일치**: Service와 Pod는 반드시 같은 Namespace에 존재해야 합니다. 서로 다른 Namespace에 있는 Pod는 Service에 연결될 수 없습니다.

4.  **`targetPort` 설정 오류**: Service의 `targetPort`가 Pod의 Container가 실제로 리스닝하고 있는 `containerPort`와 일치하지 않는 경우. 이 경우 Endpoint는 생성될 수 있지만, 트래픽이 전달되지 않아 결국 연결 실패로 이어집니다.

## 4. 해결 방법

#### 1단계: Service의 Selector와 Pod의 Label 비교

가장 먼저 Service의 `selector`와 Pod의 `label`이 정확히 일치하는지 확인합니다.

```bash
# 1. Service의 selector 확인
$ kubectl get svc user-service -o yaml | grep 'selector:' -A 1
  selector:
    app: user-service

# 2. 해당 label을 가진 Pod가 있는지 확인
$ kubectl get pods --show-labels | grep 'app=user-service'
user-service-6c8f7d4f9c-abcde   1/1     Running   0          1h   app=user-service,pod-template-hash=6c8f7d4f9c
```

만약 2번 명령어의 결과가 아무것도 없다면, 둘 중 하나의 레이블이 잘못된 것입니다. Deployment(또는 Pod) YAML 파일이나 Service YAML 파일의 레이블을 수정하여 일치시킨 후 `kubectl apply`로 적용합니다.

**Service YAML 예시:**
```yaml
apiVersion: v1
kind: Service
metadata:
  name: user-service
spec:
  selector:
    app: user-service # 이 레이블과
  ports:
    - protocol: TCP
      port: 80
      targetPort: 8080
```

**Deployment YAML 예시:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: user-service
spec:
  template:
    metadata:
      labels:
        app: user-service # 이 레이블이 일치해야 함
    spec:
      containers:
      - name: user-service
        image: my-repo/user-service:v1.0
        ports:
        - containerPort: 8080
```

#### 2단계: Pod의 상태 확인

레이블이 일치하는데도 Endpoint가 없다면, Pod들이 `Ready` 상태인지 확인합니다.

```bash
$ kubectl get pods -l app=user-service
NAME                              READY   STATUS    RESTARTS   AGE
user-service-6c8f7d4f9c-abcde     1/1     Running   0          1h
```

`READY` 컬럼이 `1/1`과 같이 Container 수와 일치하고 `STATUS`가 `Running`이면 정상입니다. 만약 `0/1`이거나 `CrashLoopBackOff` 등의 상태라면, 해당 Pod의 문제를 먼저 해결해야 합니다. (관련 트러블슈팅 가이드 참조)

#### 3단계: `targetPort` 확인

Pod가 정상 `Running` 상태임에도 연결이 안 된다면, Service의 `targetPort`가 Pod의 `containerPort`와 일치하는지 확인합니다.

*   `kubectl describe svc <service-name>`으로 `TargetPort` 확인
*   `kubectl describe pod <pod-name>`으로 `Containers.Ports` 섹션의 `Port` 확인

두 포트가 다르면 Service YAML을 수정하여 맞추어 줍니다. `targetPort`는 포트 번호(예: `8080`) 또는 Pod에 정의된 포트의 `name`(예: `http`)으로 지정할 수 있습니다.

#### 4단계: 검증

수정 사항을 적용한 후, 잠시 기다렸다가 `kubectl get endpoints <service-name>` 명령어를 다시 실행하여 IP 주소가 정상적으로 등록되었는지 확인합니다.

```bash
$ kubectl get endpoints user-service
NAME           ENDPOINTS                         AGE
user-service   10.244.1.5:8080,10.244.2.7:8080   5m
```

Endpoint가 생성된 것을 확인한 후, Cluster 내 다른 Pod에서 `curl http://user-service`를 실행하여 연결이 잘 되는지 최종 검증합니다.

## 5. 교훈

1.  **레이블은 Kubernetes의 접착제**: Service와 Pod를 연결하는 `selector-label` 메커니즘은 Kubernetes 네트워킹의 가장 기본적이고 핵심적인 원리입니다. 오타 하나가 전체 서비스의 동작을 멈추게 할 수 있음을 항상 인지해야 합니다.
2.  **Service는 건강한 Pod만 상대한다**: Service는 `Ready` 상태의 Pod에게만 트래픽을 보냄으로써 자체적인 장애 격리 기능을 수행합니다. Endpoint가 없다는 것은 "연결할만한 건강한 Pod가 없다"는 신호로 해석할 수 있습니다.
3.  **`describe`로 관계를 파악하라**: `kubectl describe svc`와 `kubectl describe pod`를 함께 사용하면 Service, Endpoint, Pod 간의 관계(Selector, Label, Port, Status)를 한눈에 파악하고 불일치 지점을 쉽게 찾을 수 있습니다.

## 관련 문서

- [시스템 아키텍처 - 마이크로서비스 구조](../../02-architecture/architecture.md#3-마이크로서비스-구조)
- [운영 가이드](../../04-operations/guides/operations-guide.md)
- [API Gateway 라우팅 오류](../istio/troubleshooting-api-gateway-routing-errors.md)

# [Troubleshooting] Grafana 대시보드 접속 불가 문제 해결

## 1. 문제 상황

Solid Cloud 클러스터 환경에 배포된 Grafana Pod는 `Running` 상태로 정상 동작하는 것으로 보이나, 웹 브라우저를 통해 Grafana 대시보드에 접속할 수 없는 문제가 발생했습니다.

## 2. 증상

- **브라우저 접속 실패**: Grafana URL로 접속 시 '연결 시간 초과(Connection Timed Out)' 오류가 발생하며 페이지가 열리지 않습니다.
- **Port-forward 실패**: `kubectl port-forward` 명령어를 사용하여 로컬에서 Pod로 직접 접근을 시도했으나, 연결이 수립되지 않고 실패했습니다.
- **Curl 테스트 실패**: 클러스터 내부의 다른 Pod에서 `curl` 명령어를 이용해 Grafana Service로 요청을 보냈으나, 응답을 받지 못했습니다.

## 3. 원인 분석

초기 분석 결과, Pod 자체의 문제보다는 클러스터 네트워크 설정과 관련된 문제일 가능성이 높다고 판단했습니다. 주요 원인으로 다음 네 가지를 추정했습니다.

1.  **Service 타입 설정 오류**: Grafana Service가 외부에서 접근할 수 없는 `ClusterIP` 타입으로 설정되었을 가능성. 외부 노출을 위해서는 `NodePort` 또는 `LoadBalancer` 타입이 필요합니다.
2.  **Ingress 설정 누락 또는 오류**: `ClusterIP` 타입의 Service를 외부로 노출하기 위한 Ingress 리소스가 없거나, 규칙이 잘못 설정되었을 가능성.
3.  **네트워크 정책(NetworkPolicy) 차단**: 특정 트래픽만 허용하는 NetworkPolicy에 의해 Grafana Pod로의 Ingress 트래픽이 차단되었을 가능성.
4.  **Service Selector와 Pod Label 불일치**: Service가 트래픽을 전달할 대상을 찾지 못하는 경우로, Service의 `selector`와 Grafana Pod의 `label`이 일치하지 않을 가능성.

## 4. 해결 방법

아래 단계에 따라 문제를 진단하고 해결했습니다.

### 1단계: Service 리소스 확인

먼저 Grafana Service의 설정 상태를 확인하여 외부 접근이 가능한지 점검했습니다.

```bash
kubectl get svc -n monitoring
```

**출력 결과:**

```
NAME                    TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)    AGE
...
grafana-service         ClusterIP   10.100.200.30   <none>        3000/TCP   2h
...
```

**분석**: Service 타입이 `ClusterIP`로 설정되어 있어 클러스터 외부에서 직접 접근할 수 없는 상태였습니다. 이것이 문제의 핵심 원인 중 하나로 추정되었습니다.

### 2단계: `port-forward`를 이용한 Pod 직접 연결 테스트

네트워크 문제를 더 좁히기 위해 Service를 거치지 않고 Pod에 직접 접근을 시도했습니다.

```bash
kubectl port-forward pod/grafana-pod-xxxxx -n monitoring 8080:3000
```

**출력 결과:**

```
Forwarding from 127.0.0.1:8080 -> 3000
Handling connection for 8080
E0101 12:34:56.789123   12345 forward.go:233] error forwarding port 3000 to pod grafana-pod-xxxxx, uid ...: unable to do port forwarding: socat not found in path
```

**분석**: `port-forward`가 실패했지만, 오류 메시지를 통해 Pod 자체보다는 Service나 다른 네트워크 설정의 문제임을 재확인했습니다. 만약 여기서 연결이 성공했다면 Service 설정이 문제의 원인일 확률이 높습니다.

### 3단계: Service 타입 변경

외부 접속을 허용하기 위해 Service 타입을 `ClusterIP`에서 `LoadBalancer`로 변경했습니다. Ingress를 사용하는 방법도 있지만, 테스트를 위해 직접 노출을 선택했습니다.

```bash
kubectl edit svc grafana-service -n monitoring
```

**수정 내용:**

```yaml
apiVersion: v1
kind: Service
metadata:
  name: grafana-service
  namespace: monitoring
spec:
  type: LoadBalancer # ClusterIP -> LoadBalancer로 변경
  ports:
  - port: 80
    targetPort: 3000
    protocol: TCP
  selector:
    app: grafana
```

### 4단계: NetworkPolicy 확인 및 수정

Service 타입을 변경한 후에도 접속이 되지 않아, 네트워크 정책이 트래픽을 차단하고 있는지 확인했습니다.

```bash
kubectl get networkpolicy -n monitoring
```

**분석**: Grafana Pod로 들어오는 트래픽을 허용하는 `ingress` 규칙이 누락된 것을 확인했습니다. Prometheus에서는 트래픽을 허용하지만, Grafana에 대한 규칙이 없어 기본적으로 모든 트래픽이 차단되고 있었습니다.

**해결**: 아래와 같이 Grafana Pod에 대한 `ingress` 트래픽을 허용하는 NetworkPolicy를 추가하거나 기존 정책을 수정했습니다.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: grafana-access-policy
  namespace: monitoring
spec:
  podSelector:
    matchLabels:
      app: grafana
  policyTypes:
  - Ingress
  ingress:
  - from:
    - namespaceSelector: {} # 모든 네임스페이스에서 오는 트래픽 허용
    ports:
    - protocol: TCP
      port: 3000
```

## 5. 검증

모든 조치를 완료한 후, `LoadBalancer`에 할당된 외부 IP 주소로 브라우저를 통해 접속했습니다.

```bash
kubectl get svc grafana-service -n monitoring
```

**출력 결과:**

```
NAME              TYPE           CLUSTER-IP      EXTERNAL-IP      PORT(S)        AGE
grafana-service   LoadBalancer   10.100.200.30   52.123.45.67     80:30001/TCP   2h30m
```

`http://52.123.45.67` 주소로 접속하여 Grafana 로그인 화면이 정상적으로 나타나는 것을 확인했습니다.

## 6. 교훈

- **Service 타입 선택 기준 명확화**: 애플리케이션을 외부에 노출할지 여부에 따라 `ClusterIP`, `NodePort`, `LoadBalancer` 타입을 명확히 구분하여 사용해야 합니다. 디버깅 시에는 `NodePort`나 `LoadBalancer`로 임시 변경하여 테스트하는 것이 유용합니다.
- **`kubectl port-forward`의 디버깅 활용**: `port-forward`는 Service나 Ingress를 거치지 않고 Pod의 상태를 직접 확인할 수 있는 강력한 디버깅 도구입니다. 네트워크 문제와 애플리케이션 문제를 분리하여 분석하는 데 효과적입니다.
- **NetworkPolicy 설정 검증의 중요성**: Pod와 Service가 정상이라도 NetworkPolicy에 의해 트래픽이 차단될 수 있습니다. 특히 보안이 강화된 환경에서는 애플리케이션 배포 시 반드시 NetworkPolicy 설정을 검토하고 필요한 규칙을 추가해야 합니다.

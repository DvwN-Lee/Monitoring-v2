# [Troubleshooting] NodePort 외부 접근 불가 문제 해결

## 1. 문제 상황

클러스터 외부에서 애플리케이션에 접근하기 위해 Service를 `NodePort` 타입으로 설정했지만, `<Node-IP>:<NodePort>` 주소로 접속 시 연결 시간 초과(Connection Timed Out)가 발생하며 접근이 불가능한 문제가 발생했습니다. 클러스터 내부에서는 Service의 ClusterIP로 정상 접근이 가능한 상태였습니다.

## 2. 증상

웹 브라우저나 `curl` 명령어를 사용하여 외부에서 NodePort로 접근 시도 시, 응답을 받지 못하고 타임아웃됩니다.

```bash
# Node IP가 1.2.3.4이고 NodePort가 30080일 경우
$ curl http://1.2.3.4:30080
curl: (7) Failed to connect to 1.2.3.4 port 30080: Connection timed out
```

`kubectl get svc` 명령어로 Service를 확인하면, `TYPE`이 `NodePort`로 정상 설정되어 있고 `PORT(S)`에 NodePort 번호(기본적으로 30000-32767 범위)가 할당된 것을 볼 수 있습니다.

```bash
$ kubectl get svc my-app-service
NAME             TYPE       CLUSTER-IP      EXTERNAL-IP   PORT(S)        AGE
my-app-service   NodePort   10.100.50.200   <none>        80:30080/TCP   1h
```

## 3. 원인 분석

NodePort 접근 실패는 클러스터 외부에서 노드까지의 네트워크 경로 어딘가에서 통신이 차단될 때 주로 발생합니다.

1.  **클라우드 보안 그룹 / 방화벽 규칙**: 가장 흔한 원인입니다. AWS의 Security Group, GCP의 Firewall Rules, Azure의 Network Security Group(NSG) 등 클라우드 플랫폼에서 제공하는 방화벽이 해당 NodePort(예: `30080/TCP`)에 대한 인바운드 트래픽을 허용하지 않는 경우입니다. Solid Cloud 환경에서도 유사한 보안 그룹 설정이 존재합니다.

2.  **물리적 방화벽 또는 온프레미스 네트워크 장비**: 온프레미스(On-premise) 환경의 경우, 데이터센터의 물리적 방화벽이나 네트워크 장비(L4 스위치 등)가 해당 포트를 차단할 수 있습니다.

3.  **노드 자체의 방화벽**: 워커 노드 OS(Linux)에 `iptables`, `firewalld`, `ufw` 등의 방화벽이 실행 중이고, 해당 NodePort에 대한 접근을 막고 있을 수 있습니다.

4.  **잘못된 노드 IP 주소 사용**: 접근하려는 노드의 IP 주소가 외부에서 접근 불가능한 사설(private) IP인 경우. 외부에서 접근하려면 반드시 노드의 공인(public) IP 주소를 사용해야 합니다.

5.  **Service `type` 설정 오류**: Service의 `type`이 `NodePort`가 아닌 `ClusterIP`로 되어 있는 경우. 이 경우 NodePort 자체가 할당되지 않습니다.

## 4. 해결 방법

#### 1단계: Service 설정 및 Endpoint 상태 확인

가장 먼저 Kubernetes 내부 설정이 올바른지 확인합니다.

*   **Service 타입 확인**: `kubectl get svc <service-name>`으로 `TYPE`이 `NodePort`인지 확인합니다.
*   **Endpoint 확인**: `kubectl describe svc <service-name>`으로 `Endpoints` 필드에 Pod의 IP가 정상적으로 등록되어 있는지 확인합니다. Endpoint가 `<none>`이라면, 이는 NodePort 문제가 아니라 Service와 Pod의 연결 문제이므로 **"[Troubleshooting] Service Endpoint 미생성 문제 해결"** 가이드를 먼저 참조해야 합니다.

#### 2단계: 클라우드 플랫폼의 보안 그룹/방화벽 설정 확인

**Solid Cloud (또는 AWS, GCP, Azure 등) 환경:**

1.  Solid Cloud 콘솔에 로그인하여 Kubernetes 클러스터의 워커 노드들이 속한 **보안 그룹(Security Group)**을 찾습니다.
2.  해당 보안 그룹의 **인바운드 규칙(Inbound Rules)**을 확인합니다.
3.  접근하려는 NodePort 번호(예: `30080`)에 대해 TCP 트래픽을 허용하는 규칙이 있는지 확인합니다.
4.  규칙이 없다면, 새로운 인바운드 규칙을 추가합니다.
    *   **유형(Type)**: 사용자 지정 TCP (Custom TCP)
    *   **프로토콜(Protocol)**: TCP
    *   **포트 범위(Port Range)**: `30080` (또는 Service에 할당된 NodePort)
    *   **소스(Source)**: `0.0.0.0/0` (모든 IP에서 접근 허용) 또는 특정 IP 대역
5.  규칙을 저장하고 잠시 후 다시 접근을 시도합니다.

#### 3단계: 노드의 Public IP 주소 확인

클라우드 플랫폼의 콘솔이나 CLI를 통해 워커 노드의 **Public IP 주소**를 정확히 확인하고, 이 IP로 접근을 시도하고 있는지 다시 한번 확인합니다.

#### 4단계: 노드 OS의 방화벽 확인 (온프레미스 등)

클라우드 환경이 아니거나, OS 수준의 방화벽이 의심될 경우 노드에 직접 접속하여 방화벽 상태를 확인합니다.

```bash
# firewalld (CentOS/RHEL)
sudo firewall-cmd --list-all
sudo firewall-cmd --add-port=30080/tcp --permanent
sudo firewall-cmd --reload

# ufw (Ubuntu)
sudo ufw status
sudo ufw allow 30080/tcp

# iptables
sudo iptables -L -n | grep 30080
```

#### 5단계: 검증

방화벽 규칙을 수정한 후, 외부에서 `curl <Node-Public-IP>:<NodePort>` 명령어로 다시 접근을 시도하여 정상적으로 응답이 오는지 확인합니다.

## 5. 교훈

1.  **NodePort의 통신 흐름을 이해하라**: NodePort 접근은 `외부 -> 클라우드 방화벽 -> 노드 -> kube-proxy(iptables/IPVS) -> Pod` 순서로 이루어집니다. 문제가 발생하면 이 흐름의 각 단계를 순서대로 점검하는 것이 효율적입니다.
2.  **가장 흔한 범인은 방화벽**: 클라우드 환경에서 NodePort 접근 실패의 90%는 보안 그룹 설정 문제입니다. Kubernetes 오브젝트(`Service`, `Pod`)가 정상이라면 가장 먼저 클라우드 콘솔의 방화벽 설정을 확인해야 합니다.
3.  **NodePort는 테스트/개발용**: NodePort는 모든 노드에 포트를 열어야 하고 포트 관리도 번거로워 프로덕션 환경에는 잘 사용되지 않습니다. 프로덕션 환경에서는 `LoadBalancer` 타입의 Service나 `Ingress`를 사용하여 외부 트래픽을 처리하는 것이 일반적이고 더 안전합니다.

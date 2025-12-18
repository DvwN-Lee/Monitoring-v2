---
version: 1.0
last_updated: 2025-11-15
author: Dongju Lee
---

# [Troubleshooting] Kubernetes Metrics Server 동작 불가 문제 해결

## 1. 문제 상황

Kubernetes Cluster의 리소스 사용량을 확인하기 위해 `kubectl top nodes` 또는 `kubectl top pods` 명령어를 실행했으나, "Metrics not available" 오류가 발생하며 Metrics Server가 정상적으로 동작하지 않는 문제를 겪었습니다. 이로 인해 HPA(Horizontal Pod Autoscaler)와 같은 메트릭 기반 오토스케일링 기능 또한 작동하지 않았습니다.

## 2. 증상

`kubectl top nodes` 명령어 실행 시 다음과 같은 오류 메시지가 출력됩니다.

```bash
$ kubectl top nodes
Error from server (ServiceUnavailable): the server is currently unable to handle the request (get nodes.metrics.k8s.io)
```

Metrics Server Pod의 로그를 확인했을 때, kubelet과의 통신에서 TLS 인증서 관련 오류나 연결 거부 메시지가 발견되었습니다.

```bash
$ kubectl logs metrics-server-xxxxxxxxxx-xxxxx -n kube-system
... E1110 10:30:00.123456       1 scraper.go:139] "Failed to scrape node" err="Get \"https://<node-ip>:10250/stats/summary?only_cpu_and_memory=true\": x509: certificate signed by unknown authority" node="<node-name>"
... E1110 10:31:00.987654       1 scraper.go:139] "Failed to scrape node" err="dial tcp <node-ip>:10250: connect: connection refused" node="<node-name>"
```

## 3. 원인 분석

1.  **TLS 인증서 문제**: Metrics Server는 각 Node의 Kubelet API (`:10250`)에 접근하여 메트릭을 수집합니다. 이때 Kubelet이 사용하는 인증서가 Cluster의 API 서버가 신뢰하는 CA(Certificate Authority)에 의해 서명되지 않은 경우, Metrics Server는 TLS 핸드셰이크에 실패하여 `x509: certificate signed by unknown authority` 오류를 발생시킵니다. 이는 특히 `kubeadm`으로 Cluster를 직접 구성했거나, 인증서 자동 순환(rotation)에 문제가 생긴 경우 발생할 수 있습니다.

2.  **Kubelet 연결 문제**:
    *   **방화벽 규칙**: Node 또는 클라우드 제공업체의 방화벽/보안 그룹이 Metrics Server Pod가 Kubelet의 `10250` 포트로 접근하는 것을 차단할 수 있습니다.
    *   **잘못된 Kubelet 주소**: Metrics Server가 Node를 식별할 때 내부 IP가 아닌 외부 IP를 사용하려고 시도하거나, Kubelet이 잘못된 주소로 리스닝하고 있을 경우 연결이 실패할 수 있습니다.
    *   **Kubelet `read-only` 포트 비활성화**: 과거에는 `10255`번 `read-only` 포트를 사용했지만, 보안상의 이유로 최신 버전에서는 사용되지 않습니다. 만약 Metrics Server가 여전히 이 포트를 사용하도록 설정되어 있다면 연결이 거부됩니다.

3.  **잘못된 배포 설정**: Metrics Server 배포 시, Kubelet과의 안전하지 않은(insecure) TLS 연결을 허용하는 `--kubelet-insecure-tls` 인자가 잘못 사용된 경우, Cluster 정책에 따라 통신이 차단될 수 있습니다. 반대로, 자체 서명된 인증서를 사용하는 환경에서 이 옵션이 누락되면 인증 오류가 발생합니다.

## 4. 해결 방법

#### 1단계: Metrics Server 로그 확인으로 원인 구체화

가장 먼저 `kube-system` Namespace에 배포된 Metrics Server Pod의 로그를 확인하여 문제가 TLS 인증 때문인지, 단순 연결 실패 때문인지 파악합니다.

```bash
kubectl logs -n kube-system -l k8s-app=metrics-server
```

#### 2단계: TLS 인증 문제 해결

로그에서 `x509: certificate signed by unknown authority` 오류가 확인될 경우, Metrics Server 배포 설정에 `--kubelet-insecure-tls` 인자를 추가하여 Kubelet의 인증서를 검증하지 않도록 임시 조치할 수 있습니다. 이는 보안상 권장되지 않지만, 급하게 문제를 해결해야 할 때 유용합니다.

`metrics-server`의 Deployment를 직접 수정하거나, Helm 차트 또는 Manifest 파일을 수정합니다.

**Deployment 직접 수정:**

```bash
kubectl edit deployment metrics-server -n kube-system
```

`spec.template.spec.containers.args` 섹션에 `--kubelet-insecure-tls`를 추가합니다.

```yaml
...
spec:
  template:
    spec:
      containers:
      - args:
        - --cert-dir=/tmp
        - --secure-port=4443
        - --kubelet-preferred-address-types=InternalIP,ExternalIP,Hostname
        - --kubelet-use-node-status-port
        - --metric-resolution=15s
        - --kubelet-insecure-tls # 이 라인을 추가
...
```

**근본적인 해결책**은 Kubelet의 인증서가 Cluster의 CA에 의해 올바르게 서명되도록 `kubeadm` 설정이나 Cluster 인증서 관리 프로세스를 점검하는 것입니다.

#### 3단계: Kubelet 연결 문제 해결

*   **방화벽 확인**: Cluster Node 간 `10250/TCP` 포트 통신이 허용되어 있는지 확인합니다. Solid Cloud와 같은 클라우드 환경에서는 보안 그룹(Security Group) 또는 NACL(Network ACL) 설정을 점검해야 합니다.
*   **Node 주소 유형 설정**: Metrics Server가 올바른 Node IP 주소를 사용하도록 `kubelet-preferred-address-types` 인자를 설정합니다. 일반적으로 `InternalIP`, `ExternalIP`, `Hostname` 순으로 우선순위를 지정하는 것이 안정적입니다. (위의 YAML 예시 참조)

#### 4단계: 배포 재시작 및 검증

설정을 수정한 후, Metrics Server Pod를 재시작하여 변경사항을 적용합니다.

```bash
kubectl rollout restart deployment/metrics-server -n kube-system
```

Pod가 정상적으로 `Running` 상태가 되면, 잠시 후 `kubectl top nodes` 명령어를 다시 실행하여 메트릭이 정상적으로 수집되는지 확인합니다.

```bash
$ kubectl top nodes
NAME       CPU(cores)   CPU%   MEMORY(bytes)   MEMORY%
node-1     250m         12%    1500Mi          38%
node-2     400m         20%    2200Mi          55%
```

## 5. 교훈

1.  **Kubelet 통신은 핵심**: Metrics Server, Prometheus 등 Cluster의 상태를 모니터링하는 여러 컴포넌트는 Kubelet API를 통해 정보를 수집합니다. 따라서 Kubelet의 인증서와 네트워크 접근성은 Cluster 모니터링의 핵심 전제 조건임을 이해해야 합니다.
2.  **보안과 편의성의 트레이드오프**: `--kubelet-insecure-tls` 옵션은 문제를 빠르게 해결할 수 있지만, 중간자 공격(MITM)에 취약해질 수 있습니다. 프로덕션 환경에서는 반드시 Cluster의 PKI(Public Key Infrastructure)를 올바르게 구성하여 보안을 확보해야 합니다.
3.  **Cluster 구성 요소의 상호작용 이해**: `kubectl top`이라는 간단한 명령어가 동작하기 위해 API Server, Metrics Server, Kubelet 등 여러 컴포넌트가 어떻게 상호작용하는지 이해하면 문제 해결에 큰 도움이 됩니다.

## 관련 문서

- [시스템 아키텍처 - 모니터링 및 로깅](../../02-architecture/architecture.md#5-모니터링-및-로깅)
- [운영 가이드](../../04-operations/guides/operations-guide.md)
- [HPA 메트릭 수집 실패](troubleshooting-hpa-metrics-failure.md)

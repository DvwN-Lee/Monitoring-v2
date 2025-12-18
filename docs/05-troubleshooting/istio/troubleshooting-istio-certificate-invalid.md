---
version: 1.0
last_updated: 2025-11-15
author: Dongju Lee
---

# [Troubleshooting] Istio mTLS 인증서 유효성 문제 해결

## 문제 상황
Istio mTLS 통신 시 인증서 검증 실패로 인해 Service 간 연결이 불가능합니다.

## 증상
- Service 간 통신 시 `TLS handshake failed`, `certificate validation failed`와 같은 에러 메시지가 발생합니다.
- `kubectl logs <pod-name> -c istio-proxy` 명령으로 istio-proxy Container의 로그를 확인하면 인증서 관련 오류나 TLS 핸드셰이크 실패 메시지가 반복적으로 나타납니다.
- `istioctl proxy-config secret <pod-name>` 명령으로 확인 시 인증서가 만료되었거나 유효하지 않다고 표시될 수 있습니다.

## 원인 분석
1.  **istiod와 Sidecar 간 통신 장애로 인증서 갱신 실패**: istiod(Istio control plane)는 Sidecar에 인증서를 발급하고 갱신하는 역할을 합니다. istiod와 Sidecar 간의 네트워크 문제, istiod의 과부하 등으로 인해 Sidecar가 제때 인증서를 갱신하지 못할 수 있습니다.
2.  **인증서 만료**: Sidecar에 주입된 인증서가 만료되었지만, 어떤 이유로든 갱신되지 않아 유효성 검증에 실패할 수 있습니다. Istio 인증서는 기본적으로 90일마다 갱신됩니다.
3.  **시스템 시간 동기화 문제**: Cluster 내의 Node 간 또는 Pod 간 시스템 시간(RTC)이 동기화되지 않으면, 인증서의 유효 기간을 잘못 판단하여 유효성 검증에 실패할 수 있습니다.
4.  **Citadel/istiod 설정 오류**: Istio의 CA(Certificate Authority) 역할을 하는 Citadel(또는 istiod 내부 CA)의 설정에 오류가 있거나, 자체 서명 인증서 사용 시 루트 인증서 배포에 문제가 있을 수 있습니다.

## 해결 방법(단계별)

### 1단계: `istioctl proxy-config secret`으로 인증서 상태 확인
`istioctl proxy-config secret <pod-name> -o yaml` 명령을 사용하여 해당 Pod의 istio-proxy에 로드된 인증서의 유효 기간을 확인합니다. `notBefore`와 `notAfter` 필드를 통해 인증서의 시작 및 만료 시간을 알 수 있습니다.

### 2단계: istiod 로그 확인
`kubectl logs -n istio-system -l app=istiod` 명령을 사용하여 istiod Pod의 로그를 확인합니다. 인증서 발급 및 갱신 과정에서 발생하는 오류 메시지나 경고를 찾아 원인을 파악합니다. istiod와 Sidecar 간의 통신 문제를 나타내는 로그가 있는지 확인합니다.

### 3단계: Pod 재시작으로 인증서 재발급
가장 간단한 해결책 중 하나는 문제가 있는 Sidecar가 주입된 Pod를 재시작하는 것입니다. Pod가 재시작되면 새로운 Sidecar가 주입되고, istiod로부터 새로운 인증서를 발급받으려고 시도합니다.
```bash
kubectl rollout restart deployment <deployment-name> -n <namespace>
```
이 방법으로 문제가 해결된다면, 일시적인 통신 문제나 인증서 갱신 메커니즘의 지연이 원인이었을 가능성이 높습니다.

### 4단계: 시스템 시간 동기화 확인
Cluster Node들의 시스템 시간이 정확하게 동기화되어 있는지 확인합니다. NTP(Network Time Protocol) 서버를 통해 시간이 동기화되도록 설정되어 있는지 확인하고, 필요한 경우 `ntpdate` 또는 `chrony`와 같은 도구를 사용하여 시간을 동기화합니다. 시간 불일치는 인증서 유효성 검증 실패의 흔한 원인 중 하나입니다.

## 검증
- 해결 방법 적용 후, 해당 Pod를 재시작하거나 새로운 Pod를 배포하여 Service 간 통신이 정상적으로 이루어지는지 확인합니다.
- `istioctl proxy-config secret <pod-name>` 명령으로 인증서의 `notAfter` 시간이 현재 시간보다 미래인지 확인하여 인증서가 유효한지 검증합니다.
- `kubectl logs <pod-name> -c istio-proxy` 명령으로 istio-proxy 로그에 더 이상 인증서 관련 오류 메시지가 발생하지 않는지 확인합니다.

## 교훈
Istio mTLS 환경에서 인증서 유효성 문제는 Service Mesh의 보안과 안정성에 직접적인 영향을 미칩니다. 인증서 만료, istiod와의 통신 문제, 시스템 시간 불일치 등 다양한 원인이 있을 수 있으므로, `istioctl` 도구와 로그를 활용하여 체계적으로 문제를 진단하는 것이 중요합니다. 특히, Cluster 내 모든 구성 요소의 시간 동기화는 mTLS 환경에서 매우 중요하게 관리되어야 할 부분입니다.

## 관련 문서

- [시스템 아키텍처 - 보안 설계](../../02-architecture/architecture.md#6-보안-설계)
- [운영 가이드](../../04-operations/guides/operations-guide.md)
- [Istio mTLS 통신 오류](troubleshooting-istio-mtls-communication.md)

---
version: 1.0
last_updated: 2025-11-15
author: Dongju Lee
---

# [Troubleshooting] Istio mTLS 서비스 간 통신 실패 문제 해결

## 문제 상황
Istio `PeerAuthentication`을 `STRICT` 모드로 설정한 후, 서비스 간 통신이 실패합니다.

## 증상
- 클라이언트 서비스에서 서버 서비스로 요청 시 503 Service Unavailable 에러가 발생합니다.
- Envoy 프록시 로그에서 `upstream connect error or disconnect/reset before headers`와 같은 메시지가 나타납니다.
- `kubectl logs <pod-name> -c istio-proxy` 명령으로 istio-proxy 컨테이너의 로그를 확인하면 TLS 핸드셰이크 실패 또는 인증서 관련 오류 메시지를 발견할 수 있습니다.

## 원인 분석
1.  **DestinationRule 누락 또는 mTLS 모드 불일치**: `PeerAuthentication`이 `STRICT` 모드로 설정되면, 클라이언트 측 서비스는 서버 서비스로 요청을 보낼 때 mTLS를 사용해야 합니다. 이때 클라이언트 측에 해당 서버 서비스로의 트래픽에 대해 mTLS를 활성화하도록 지시하는 `DestinationRule`이 없거나, `mTLS` 모드가 일치하지 않으면 통신이 실패합니다.
2.  **PeerAuthentication 설정 오류**: `PeerAuthentication` 리소스의 `selector`가 잘못 지정되었거나, `mTLS` 모드가 의도와 다르게 설정되었을 수 있습니다.
3.  **일부 서비스에만 Sidecar 주입되지 않음**: 통신하려는 서비스 중 하나라도 Istio Sidecar가 주입되지 않았다면, mTLS 통신이 불가능하여 통신 실패로 이어집니다.
4.  **Istio 버전 호환성 문제**: 드물게 Istio 버전 업그레이드 후 `mTLS` 관련 설정의 변경이나 버그로 인해 통신 문제가 발생할 수 있습니다.

## 해결 방법(단계별)

### 1단계: `istioctl proxy-status`로 연결 상태 확인
`istioctl proxy-status` 명령을 사용하여 Sidecar의 상태와 `istiod`와의 연결 상태를 확인합니다. 특히 `SYNCED` 상태인지, `mTLS` 관련 설정이 올바르게 적용되었는지 간접적으로 파악할 수 있습니다.

### 2단계: DestinationRule에 mTLS 설정 추가
클라이언트 서비스가 서버 서비스로 mTLS 통신을 하도록 `DestinationRule`을 설정해야 합니다.
```yaml
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: <server-service-name>
  namespace: <namespace>
spec:
  host: <server-service-name>.<namespace>.svc.cluster.local
  trafficPolicy:
    tls:
      mode: ISTIO_MUTUAL
```
위와 같이 클라이언트 서비스가 통신하려는 서버 서비스에 대한 `DestinationRule`을 생성하거나 수정하여 `tls.mode`를 `ISTIO_MUTUAL`로 설정합니다.

### 3단계: PeerAuthentication 정책 검증
`PeerAuthentication` 리소스의 `selector`가 통신하려는 서비스의 Pod에 올바르게 적용되고 있는지 확인합니다.
```bash
kubectl get peerauthentication -n <namespace> -o yaml
```
`selector` 필드가 해당 서비스의 Pod 레이블과 일치하는지 확인하고, `mtls.mode`가 `STRICT`로 설정되어 있는지 다시 한번 확인합니다.

### 4단계: 모든 Pod의 Sidecar 주입 확인
통신에 관련된 모든 서비스의 Pod에 Istio Sidecar가 올바르게 주입되었는지 확인합니다.
```bash
kubectl get pod -n <namespace> -l app=<service-label> -o yaml | grep 'istio-proxy'
```
`istio-proxy` 컨테이너가 존재하고, Pod의 READY 상태가 `2/2`인지 확인합니다. Sidecar가 주입되지 않은 Pod가 있다면, 해당 Deployment/Pod에 Sidecar 자동 주입이 활성화되어 있는지 확인하고 필요한 경우 수동으로 주입합니다.

## 검증
- `DestinationRule` 및 `PeerAuthentication` 설정을 수정한 후, 관련 서비스의 Pod를 재시작합니다.
- 클라이언트 서비스에서 서버 서비스로 요청을 다시 보내어 503 에러가 더 이상 발생하지 않고 정상적으로 통신이 이루어지는지 확인합니다.
- `istioctl proxy-config secret <pod-name> -o yaml` 명령을 통해 Sidecar에 올바른 인증서가 로드되었는지 확인할 수 있습니다.

## 교훈
Istio에서 mTLS를 `STRICT` 모드로 설정하는 것은 서비스 간 보안을 강화하는 중요한 단계입니다. 하지만 이로 인해 통신 문제가 발생할 경우, `DestinationRule`의 `mTLS` 설정, `PeerAuthentication` 정책의 정확성, 그리고 모든 관련 서비스에 Sidecar가 올바르게 주입되었는지 여부를 체계적으로 확인해야 합니다. 특히, `DestinationRule`은 클라이언트 측에서 서버로의 트래픽에 대한 정책을 정의하므로, `PeerAuthentication`과 함께 올바르게 구성하는 것이 중요합니다.

## 관련 문서

- [시스템 아키텍처 - 보안 설계](../../02-architecture/architecture.md#6-보안-설계)
- [운영 가이드](../../04-operations/guides/operations-guide.md)
- [Istio 인증서 유효성 문제](troubleshooting-istio-certificate-invalid.md)

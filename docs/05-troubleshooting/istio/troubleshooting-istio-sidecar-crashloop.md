---
version: 1.0
last_updated: 2025-11-15
author: Dongju Lee
---

# [Troubleshooting] Istio Sidecar CrashLoopBackOff 문제 해결

## 문제 상황
Istio Sidecar 주입 후 Pod가 CrashLoopBackOff 상태로 반복 재시작됩니다.

## 증상
- Pod의 READY 상태가 1/2로 표시됩니다.
- `kubectl describe pod <pod-name>` 명령 실행 시 istio-proxy 컨테이너가 반복적으로 재시작되는 것을 확인할 수 있습니다.
- `kubectl logs <pod-name> -c istio-proxy` 명령으로 istio-proxy 컨테이너의 로그를 확인하면 특정 오류 메시지가 반복적으로 나타납니다.

## 원인 분석
1.  **애플리케이션 컨테이너와 istio-proxy 포트 충돌**: 애플리케이션 컨테이너가 이미 istio-proxy가 사용하는 포트(예: 15020, 15090 등)를 사용하고 있을 경우 충돌이 발생할 수 있습니다.
2.  **네트워크 정책 문제**: Istio Sidecar가 필요한 외부 또는 내부 서비스와 통신하지 못하도록 네트워크 정책이 구성되어 있을 수 있습니다.
3.  **리소스 제한으로 인한 OOMKilled**: istio-proxy 컨테이너에 할당된 CPU 또는 메모리 리소스가 부족하여 OOMKilled(Out Of Memory Killed) 상태로 종료되고 재시작될 수 있습니다.
4.  **istio-proxy 설정 오류**: Istio 설정(예: `ProxyConfig`)에 오류가 있거나, Sidecar 주입 시 잘못된 환경 변수 또는 설정이 적용되었을 수 있습니다.

## 해결 방법(단계별)

### 1단계: `kubectl logs`로 istio-proxy 로그 확인
가장 먼저 `kubectl logs <pod-name> -c istio-proxy` 명령을 사용하여 istio-proxy 컨테이너의 로그를 확인합니다. 로그에서 특정 오류 메시지나 재시작의 원인을 파악할 수 있는 힌트를 찾습니다. 예를 들어, `OOMKilled` 메시지나 특정 포트 바인딩 실패 메시지 등을 확인합니다.

### 2단계: 포트 충돌 확인 및 해결
애플리케이션 컨테이너가 사용하는 포트와 istio-proxy가 사용하는 포트 간의 충돌 여부를 확인합니다.
- 애플리케이션 컨테이너의 Dockerfile 또는 시작 스크립트에서 노출하는 포트를 확인합니다.
- Istio Sidecar가 사용하는 기본 포트(예: 15020, 15090)와 충돌하는지 확인합니다.
- 충돌이 발생할 경우, 애플리케이션 컨테이너의 포트를 변경하거나, Istio Sidecar의 포트 설정을 조정합니다. (일반적으로 애플리케이션 포트 변경이 권장됩니다.)

### 3단계: 리소스 제한 조정
istio-proxy 컨테이너의 리소스(CPU, Memory) 제한이 너무 낮게 설정되어 있는지 확인합니다.
- `kubectl describe pod <pod-name>` 출력에서 istio-proxy 컨테이너의 `Limits` 및 `Requests` 섹션을 확인합니다.
- `OOMKilled`가 원인으로 의심된다면, istio-proxy 컨테이너의 메모리 제한을 늘려줍니다.
- `CrashLoopBackOff`가 지속되면 CPU 제한도 함께 검토하여 조정합니다.

### 4단계: 네트워크 정책 검증
클러스터에 네트워크 정책(NetworkPolicy)이 적용되어 있다면, istio-proxy가 필요한 통신을 수행할 수 있도록 허용되어 있는지 확인합니다.
- istio-proxy는 `istiod`와의 통신, 메트릭 수집을 위한 통신 등 다양한 내부 통신이 필요합니다.
- 네트워크 정책이 이러한 통신을 차단하고 있지 않은지 검토하고, 필요한 경우 정책을 수정하여 허용합니다.

## 검증
- 해결 방법 적용 후, 해당 Pod를 재시작하거나 새로운 Pod를 배포하여 `kubectl get pod` 명령으로 READY 상태가 `2/2`가 되는지 확인합니다.
- `kubectl logs <pod-name> -c istio-proxy` 명령으로 istio-proxy 로그에 더 이상 오류 메시지가 발생하지 않는지 확인합니다.
- 애플리케이션이 정상적으로 동작하는지 테스트합니다.

## 교훈
Istio Sidecar는 애플리케이션의 네트워크 트래픽을 가로채고 처리하기 때문에, Sidecar 자체의 안정적인 동작은 서비스 메시 전체의 안정성에 매우 중요합니다. Sidecar 관련 문제 발생 시, 로그를 통한 원인 파악, 리소스 및 네트워크 정책 검토, 포트 충돌 확인 등 다각적인 접근이 필요합니다. 특히, 리소스 부족이나 포트 충돌과 같은 기본적인 인프라 문제는 Sidecar의 비정상적인 동작으로 이어질 수 있으므로 주의 깊게 관리해야 합니다.

## 관련 문서

- [시스템 아키텍처 - 전체 시스템](../../02-architecture/architecture.md#2-전체-시스템-아키텍처)
- [운영 가이드](../../04-operations/guides/operations-guide.md)
- [Pod CrashLoopBackOff](../kubernetes/troubleshooting-pod-crashloopbackoff.md)

---
version: 1.0
last_updated: 2025-12-04
author: Dongju Lee
---

# [Troubleshooting] SSH Tunnel을 통한 외부 접속 설정

## 1. 문제 상황

Phase 1+2 검증을 위해 로컬 머신에서 Solid Cloud Cluster에 배포된 서비스에 API 요청을 보내려 했으나, Connection Timeout 오류가 발생하여 접속할 수 없었습니다.

```bash
$ curl -X POST http://10.0.1.70:32491/api/users \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","email":"test@example.com","password":"test123"}'

curl: (28) Failed to connect to 10.0.1.70 port 32491 after 130057 ms: Couldn't connect to server
```

## 2. 증상

### 2.1 NodePort 직접 접속 실패

Bastion Host의 IP와 NodePort로 직접 접속 시도 시 Timeout:

```bash
# Bastion Host IP: 10.0.1.70
# Istio Ingress Gateway NodePort: 32491

$ curl -v http://10.0.1.70:32491/
* Trying 10.0.1.70:32491...
* Connection timeout after 130000 ms
```

### 2.2 kubectl 명령도 실패

```bash
$ kubectl get svc -n istio-system istio-ingressgateway

Error from server: dial tcp 10.0.11.168:6443: connect: connection refused
```

## 3. 원인 분석

### 3.1 네트워크 아키텍처

Solid Cloud 환경의 네트워크 구조:

```
[로컬 머신]
    ↓ (접근 불가)
[Bastion Host: 10.0.1.70]
    ↓ (SSH)
[Kubernetes Master: 10.0.11.168:6443]
[Worker Nodes + Ingress Gateway: 10.100.0.73:32491]
```

### 3.2 근본 원인

1. **방화벽 정책**
   - Solid Cloud 네트워크는 외부 직접 접속 차단
   - Bastion Host를 통한 SSH 접속만 허용

2. **NodePort 접근 제한**
   - Worker Node의 NodePort(32491)는 내부 네트워크에서만 접근 가능
   - 외부에서 직접 NodePort 접근 불가

3. **kubectl context 설정**
   - Kubernetes API Server(10.0.11.168:6443)도 내부 네트워크에 위치
   - 로컬에서 직접 kubectl 명령 실행 불가

### 3.3 네트워크 경로

**실제 필요한 경로**:
```
[로컬 머신:8080]
    ↓ (SSH Tunnel)
[Bastion Host:22]
    ↓ (포트 포워딩)
[Ingress Gateway:10.100.0.73:32491]
    ↓ (Istio VirtualService)
[Application Pods]
```

## 4. 해결 방법

### 4.1 SSH Tunnel 설정

#### 단계 1: Bastion Host SSH 접속 확인

```bash
# Bastion Host 접속 테스트
$ ssh user@10.0.1.70
Welcome to Ubuntu 24.04 LTS
```

#### 단계 2: Ingress Gateway ClusterIP 확인

Bastion Host에서 Ingress Gateway의 내부 IP 확인:

```bash
$ kubectl get svc -n istio-system istio-ingressgateway

NAME                   TYPE       CLUSTER-IP     EXTERNAL-IP   PORT(S)
istio-ingressgateway   NodePort   10.100.0.73    <none>        80:32491/TCP,443:32589/TCP
```

**ClusterIP**: `10.100.0.73`
**NodePort**: `32491` (HTTP), `32589` (HTTPS)

#### 단계 3: SSH Port Forwarding 설정

```bash
# 로컬 8080 포트를 Ingress Gateway 32491로 포워딩
$ ssh -L 8080:10.100.0.73:32491 user@10.0.1.70 -N

# -L: Local port forwarding
# 8080: 로컬 머신 포트
# 10.100.0.73:32491: Ingress Gateway (ClusterIP:NodePort)
# -N: 원격 명령 실행 없이 포워딩만 수행
```

**백그라운드로 실행**:
```bash
$ ssh -fL 8080:10.100.0.73:32491 user@10.0.1.70 -N

# -f: 백그라운드 실행
```

### 4.2 접속 검증

#### 1. Health Check

```bash
$ curl http://localhost:8080/health
{"status":"ok"}
```

#### 2. API Integration Test

```bash
# 1. 회원가입
$ curl -X POST http://localhost:8080/api/users \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser_phase12","email":"test@example.com","password":"test123"}'

{"user_id":4,"message":"User registered successfully"}

# 2. 로그인
$ TOKEN=$(curl -s -X POST http://localhost:8080/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser_phase12","password":"test123"}' | jq -r '.access_token')

# 3. 블로그 작성
$ curl -X POST http://localhost:8080/blog/api/posts \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"title":"Test Post","content":"Test content","category_id":1}'

{"post_id":294,"message":"Post created successfully"}
```

### 4.3 SSH Tunnel 프로세스 관리

#### Tunnel 프로세스 확인

```bash
$ ps aux | grep "ssh -"
user  12345  0.0  0.0  ssh -L 8080:10.100.0.73:32491 user@10.0.1.70 -N
```

#### Tunnel 종료

```bash
# PID로 종료
$ kill 12345

# 또는 모든 SSH 터널 종료
$ pkill -f "ssh -.*8080:10.100.0.73"
```

## 5. 교훈

### 5.1 네트워크 아키텍처 이해

1. **클라우드 환경별 접근 방식 파악**
   - Bastion Host 경유 여부 확인
   - 방화벽 정책 사전 조사

2. **Ingress 경로 명확화**
   - NodePort vs ClusterIP vs LoadBalancer
   - 각 환경별 권장 접근 방식 문서화

3. **kubectl context 분리**
   - Local Kubernetes: `~/.kube/config`
   - Solid Cloud: `~/.kube/config-solid-cloud`
   - `KUBECONFIG` 환경변수로 전환

### 5.2 대안 방법

#### 1. kubectl port-forward (일회성)

```bash
$ kubectl port-forward -n istio-system svc/istio-ingressgateway 8080:80
Forwarding from 127.0.0.1:8080 -> 8080
```

**장점**: kubectl만으로 간단 설정
**단점**: 연결 불안정, 백그라운드 실행 불편

#### 2. VPN 구성 (프로덕션 권장)

```bash
# WireGuard 또는 OpenVPN으로 VPN 터널 구성
# Bastion Host에 VPN 서버 설치
# 로컬 머신에서 VPN 연결 후 직접 접근
```

**장점**: 안정적, 모든 포트 접근 가능
**단점**: 초기 설정 복잡, VPN 서버 관리 필요

#### 3. Ingress Controller + LoadBalancer (프로덕션 권장)

```yaml
# Istio Ingress Gateway를 LoadBalancer로 변경
apiVersion: v1
kind: Service
metadata:
  name: istio-ingressgateway
spec:
  type: LoadBalancer  # NodePort → LoadBalancer
```

**장점**: 외부 IP 자동 할당, 안정적
**단점**: 클라우드 제공자 지원 필요, 비용 발생

### 5.3 자동화 스크립트

```bash
#!/bin/bash
# scripts/ssh-tunnel-setup.sh

BASTION_HOST="10.0.1.70"
INGRESS_IP="10.100.0.73"
INGRESS_PORT="32491"
LOCAL_PORT="8080"

echo "Starting SSH tunnel..."
ssh -fL ${LOCAL_PORT}:${INGRESS_IP}:${INGRESS_PORT} user@${BASTION_HOST} -N

echo "Testing connection..."
curl -s http://localhost:${LOCAL_PORT}/health | jq .

echo "SSH tunnel active on localhost:${LOCAL_PORT}"
```

## 관련 문서

- [Solid Cloud 구성 가이드](../../02-architecture/architecture.md#7-solid-cloud-구성)
- [ADR-009: Kubernetes 플랫폼으로 Solid Cloud 채택](../../02-architecture/adr/009-solid-cloud-platform.md)
- [운영 가이드 - 외부 접속](../../04-operations/guides/operations-guide.md#외부-접속)

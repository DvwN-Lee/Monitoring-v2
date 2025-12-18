# Getting Started - 로컬 환경에서 시작하기

**문서 버전**: 1.0
**작성일**: 2025년 11월 14일

---

## 개요

본 가이드는 Cloud-Native 마이크로서비스 플랫폼 v2.0 프로젝트를 시작하기 위한 A-to-Z 설정 문서입니다.

**이 가이드를 완료하면**:
- 로컬 환경(Minikube)에서 전체 마이크로서비스 스택을 실행
- 블로그 UI, Grafana, Prometheus 등 모든 서비스에 접근
- 코드 수정 시 자동 재배포(Hot Reload) 확인

**예상 소요 시간**: 30~60분

---

## 사전 요구사항

### 필수 지식
- Kubernetes 기본 개념 (Pod, Service, Deployment 이해)
- Docker 사용 경험 (이미지 빌드 및 실행)

### 시스템 요구사항
- **OS**: macOS / Linux (Ubuntu, RHEL, CentOS, Fedora)
- **CPU**: 4 cores 이상 권장
- **메모리**: 8GB 이상 권장
- **디스크**: 20GB 이상 여유 공간

---

## Step 1: 필수 도구 설치

### 자동 설치 (권장)

프로젝트 루트에서 다음 스크립트를 실행합니다:

```bash
./scripts/install-tools.sh
```

### 설치되는 도구

| 도구 | 설명 | 버전 |
|:---|:---|:---|
| `kubectl` | Kubernetes Cluster 관리 CLI | 최신 안정 버전 |
| `minikube` | 로컬 Kubernetes Cluster | 최신 안정 버전 |
| `skaffold` | 개발 워크플로우 자동화 도구 | 최신 안정 버전 |
| `terraform` | 인프라 프로비저닝 (선택사항) | 최신 안정 버전 |

### 수동 설치 (스크립트 실패 시)

스크립트가 실패하는 경우, 각 도구의 공식 설치 가이드를 참고하여 수동으로 설치합니다:

- kubectl: https://kubernetes.io/docs/tasks/tools/
- minikube: https://minikube.sigs.k8s.io/docs/start/
- skaffold: https://skaffold.dev/docs/install/

### 설치 확인

```bash
kubectl version --client
minikube version
skaffold version
```

각 명령어가 버전 정보를 출력하면 설치가 완료된 것입니다.

---

## Step 2: Minikube Cluster 시작

### Cluster 생성

권장 리소스 설정으로 Minikube를 시작합니다:

```bash
minikube start --cpus=4 --memory=8192 --disk-size=20g
```

**참고**: 시스템 사양이 충분하다면 `--cpus=6 --memory=12288`로 더 많은 리소스를 할당할 수 있습니다.

### 상태 확인

```bash
# Minikube 상태
minikube status

# Kubernetes Node 확인
kubectl get nodes
```

예상 출력:
```
NAME       STATUS   ROLES           AGE   VERSION
minikube   Ready    control-plane   1m    v1.29.7
```

Node 상태가 `Ready`이면 Cluster가 정상적으로 시작된 것입니다.

---

## Step 3: 애플리케이션 배포

### Skaffold로 배포

프로젝트 루트에서 다음 스크립트를 실행합니다:

```bash
./scripts/deploy-local.sh
```

### 배포 과정

Skaffold는 다음 작업을 자동으로 수행합니다:

1. **빌드**: 각 마이크로서비스의 Docker 이미지를 빌드
2. **푸시**: Minikube 내부 레지스트리로 이미지 푸시
3. **배포**: Kustomize로 Kubernetes 매니페스트를 생성하고 Cluster에 적용
4. **감시**: 코드 변경 감지 시 자동 재빌드 및 재배포 (Hot Reload)

### 배포 진행 상황 확인

다른 터미널 창을 열어 Pod 상태를 모니터링합니다:

```bash
watch -n 2 kubectl get pods
```

또는 `kubectl get pods` 명령어를 주기적으로 실행합니다.

---

## Step 4: 정상 동작 확인

### Pod 상태 확인

모든 Pod가 `Running` 상태가 될 때까지 대기합니다 (약 5-10분 소요):

```bash
kubectl get pods
```

예상 출력:
```
NAME                           READY   STATUS    RESTARTS   AGE
api-gateway-xxxx               1/1     Running   0          5m
auth-service-xxxx              1/1     Running   0          5m
user-service-xxxx              1/1     Running   0          5m
blog-service-xxxx              1/1     Running   0          5m
```

**참고**: 일부 Pod가 `ContainerCreating` 상태라면 이미지 다운로드 중이므로 잠시 기다립니다.

### 서비스 접속

#### Port Forward 설정

다음 명령어를 실행하여 로컬에서 서비스에 접속할 수 있도록 합니다:

```bash
# API Gateway (블로그 UI)
kubectl port-forward svc/api-gateway 8000:8000 &

# Grafana
kubectl port-forward svc/grafana 3000:3000 -n monitoring &

# Prometheus
kubectl port-forward svc/prometheus 9090:9090 -n monitoring &
```

#### 접속 확인

브라우저에서 다음 URL에 접속하여 서비스가 정상 동작하는지 확인합니다:

| 서비스 | URL | 설명 |
|:---|:---|:---|
| 블로그 UI | http://localhost:8000/blog | 블로그 게시글 목록 및 작성 |
| Grafana | http://localhost:3000 | Golden Signals 대시보드 |
| Prometheus | http://localhost:9090 | 메트릭 수집 현황 |

**Grafana 접속 정보**: `admin` / `prom-operator`

### 로그 확인

특정 Pod의 로그를 실시간으로 확인합니다:

```bash
# 특정 Pod 로그
kubectl logs -f <pod-name>

# 예시: API Gateway 로그
kubectl logs -f deployment/api-gateway
```

**참고**: Skaffold가 실행 중이라면 모든 서비스의 로그가 자동으로 표시됩니다.

---

## Step 5: 개발 워크플로우

### 코드 수정 및 Hot Reload

Skaffold는 소스 코드 변경을 자동으로 감지하여 재배포합니다:

1. 원하는 서비스의 소스 코드 수정 (예: `blog-service/blog_service.py`)
2. 파일 저장
3. Skaffold가 자동으로 감지하여 재빌드 및 재배포
4. 브라우저에서 변경 사항 확인

### 배포 중지

Skaffold 실행 중인 터미널에서 다음 키를 입력합니다:

```bash
Ctrl + C
```

---

## 문제 해결

### 문제 1: Minikube 시작 실패

**증상**: `minikube start` 실행 시 에러 발생

**원인**:
- 시스템 리소스 부족
- 이전 Minikube 인스턴스가 정리되지 않음
- 하이퍼바이저 (VirtualBox, HyperKit 등) 문제

**해결**:
```bash
# 기존 Cluster 삭제 후 재시작
minikube delete
minikube start --cpus=4 --memory=8192
```

### 문제 2: Pod가 Pending 상태

**증상**: `kubectl get pods` 실행 시 Pod가 계속 `Pending`

**원인**:
- Minikube 리소스 부족
- PersistentVolume 생성 실패

**해결**:
```bash
# Pod 상세 정보 확인
kubectl describe pod <pod-name>

# Minikube 리소스 증가
minikube stop
minikube start --cpus=6 --memory=12288
```

### 문제 3: 이미지 Pull 실패

**증상**: `ImagePullBackOff` 또는 `ErrImagePull` 에러

**원인**:
- 로컬 이미지 빌드 실패
- Minikube Docker 데몬 미사용

**해결**:
```bash
# Minikube Docker 환경 사용
eval $(minikube docker-env)

# Skaffold 재실행
./scripts/deploy-local.sh
```

### 문제 4: Port Forward 연결 실패

**증상**: `kubectl port-forward` 연결이 끊김

**원인**:
- Pod가 재시작됨
- 네트워크 타임아웃

**해결**:
```bash
# Port forward 재실행
kubectl port-forward svc/<service-name> <local-port>:<service-port>
```

---

## 다음 단계

### 프로젝트 이해하기
- [시스템 아키텍처](../02-architecture/architecture.md)
- [서비스별 README](../../) (각 서비스 디렉토리)
- [모니터링 스택](../../k8s-manifests/monitoring/README.md)

### 개발 시작하기
- [로컬 개발 가이드](../03-implementation/)
- [CI/CD Pipeline](../02-architecture/architecture.md#4-cicd-Pipeline)

### 문제 발생 시
- [트러블슈팅 가이드 인덱스](../05-troubleshooting/README.md)
- [운영 가이드](../04-operations/guides/operations-guide.md)

---

## 참고 문서

- [Kubernetes 공식 문서](https://kubernetes.io/docs/)
- [Minikube 문서](https://minikube.sigs.k8s.io/docs/)
- [Skaffold 문서](https://skaffold.dev/docs/)
- [프로젝트 아키텍처 문서](../02-architecture/architecture.md)

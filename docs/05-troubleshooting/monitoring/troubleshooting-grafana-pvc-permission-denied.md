---
version: 1.0
last_updated: 2025-11-15
author: Dongju Lee
---

# Grafana PVC 권한 거부 문제 해결

## 문제 현상

### Pod 상태
```bash
$ kubectl get pods -n monitoring
NAME                                     READY   STATUS             RESTARTS   AGE
prometheus-grafana-5f7d9b8c6d-abc12     0/1     CrashLoopBackOff   5          10m
```

### 에러 로그
```bash
$ kubectl logs prometheus-grafana-5f7d9b8c6d-abc12 -n monitoring

GF_PATHS_DATA='/var/lib/grafana' is not writable.
mkdir: cannot create directory '/var/lib/grafana/plugins': Permission denied
chown: cannot access '/var/lib/grafana': Operation not permitted
```

### 발생 상황
- Grafana Pod가 시작되지 않고 CrashLoopBackOff 상태
- PVC는 정상적으로 Bound 상태
- Prometheus는 정상 작동하지만 Grafana만 실패
- Helm chart 설치 또는 업그레이드 직후 발생

### 영향 범위
- Grafana 대시보드 접근 불가
- 모니터링 시각화 불가능
- 알림 설정 및 관리 불가

## 원인 분석

### 근본 원인

Kubernetes에서 PVC(PersistentVolumeClaim)를 마운트할 때, 볼륨의 소유권이 Pod의 실행 사용자 계정과 일치하지 않아 발생하는 권한 문제입니다.

### 기술적 배경

#### Grafana의 기본 사용자 ID
Grafana 컨테이너는 보안을 위해 root가 아닌 전용 사용자로 실행됩니다:
- User ID: `472`
- Group ID: `472`
- 사용자 이름: `grafana`

#### PVC 권한 불일치
```bash
# PVC 마운트 후 권한 확인
$ kubectl exec -it prometheus-grafana-5f7d9b8c6d-abc12 -n monitoring -- ls -la /var/lib/grafana
drwxr-xr-x 2 root root 4096 Nov 10 12:00 .

# Grafana 프로세스는 UID 472로 실행
$ kubectl exec -it prometheus-grafana-5f7d9b8c6d-abc12 -n monitoring -- id
uid=472(grafana) gid=472(grafana) groups=472(grafana)
```

UID 472의 사용자가 root 소유의 디렉토리에 쓰기를 시도하면 Permission Denied 발생.

#### Helm Chart의 initChownData

많은 Helm chart는 이 문제를 해결하기 위해 `initContainer`를 사용:

```yaml
initContainers:
- name: init-chown-data
  image: busybox
  command: ['chown', '-R', '472:472', '/var/lib/grafana']
  volumeMounts:
  - name: storage
    mountPath: /var/lib/grafana
```

**문제점**:
- 이미 데이터가 있는 PVC에서는 chown이 실패할 수 있음
- 대용량 데이터의 경우 chown 시간이 오래 걸림
- 일부 스토리지 클래스는 chown을 지원하지 않음

## 해결 방법

### 해결 방안 1: podSecurityContext 설정 (권장)

Helm `values.yaml`에서 Pod의 보안 컨텍스트를 명시적으로 설정합니다.

#### prometheus-values.yaml 수정

```yaml
grafana:
  enabled: true

  # 기존 설정...
  persistence:
    enabled: true
    size: 5Gi

  # Grafana 서버 설정
  grafana.ini:
    server:
      root_url: http://10.0.11.168:30300
      domain: 10.0.11.168

  # Pod 보안 컨텍스트 설정 (PVC 권한 문제 해결)
  podSecurityContext:
    fsGroup: 472        # 파일시스템 그룹 ID
    runAsUser: 472      # 실행 사용자 ID
    runAsGroup: 472     # 실행 그룹 ID

  # Init container chown 비활성화 (기존 PVC 사용 시)
  initChownData:
    enabled: false
```

#### 설정 설명

- `fsGroup: 472`: 마운트된 볼륨의 그룹 소유권을 472로 설정
- `runAsUser: 472`: 컨테이너를 UID 472로 실행
- `runAsGroup: 472`: 컨테이너를 GID 472로 실행
- `initChownData.enabled: false`: 불필요한 init container 비활성화

### 해결 방안 2: 수동 권한 변경 (임시 방편)

PVC에 직접 접근하여 권한 수정:

```bash
# 디버그 Pod 생성
kubectl run -it --rm debug \
  --image=busybox \
  --overrides='
{
  "spec": {
    "containers": [{
      "name": "debug",
      "image": "busybox",
      "command": ["sh"],
      "stdin": true,
      "tty": true,
      "volumeMounts": [{
        "name": "grafana-storage",
        "mountPath": "/data"
      }]
    }],
    "volumes": [{
      "name": "grafana-storage",
      "persistentVolumeClaim": {
        "claimName": "prometheus-grafana"
      }
    }]
  }
}' \
  -n monitoring

# Pod 내부에서 권한 변경
/ # chown -R 472:472 /data
/ # chmod -R 755 /data
/ # ls -la /data
drwxr-xr-x 3 472 472 4096 Nov 10 12:00 .
/ # exit
```

### 해결 방안 3: StorageClass 변경

일부 스토리지 클래스는 자동으로 권한을 처리합니다:

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: grafana-storage
provisioner: kubernetes.io/aws-ebs
parameters:
  type: gp3
  fsType: ext4
mountOptions:
  - uid=472
  - gid=472
```

## 검증 방법

### 1. Helm 업그레이드

```bash
# Helm 업그레이드
helm upgrade prometheus prometheus-community/kube-prometheus-stack \
  -f k8s-manifests/monitoring/prometheus-values.yaml \
  -n monitoring

# 배포 상태 확인
kubectl rollout status deployment/prometheus-grafana -n monitoring
```

### 2. Pod 상태 확인

```bash
# Pod가 Running 상태인지 확인
kubectl get pods -n monitoring | grep grafana
# 예상 출력:
# prometheus-grafana-5f7d9b8c6d-xyz78     1/1     Running     0          2m

# Pod 로그 확인 (에러가 없어야 함)
kubectl logs -n monitoring deployment/prometheus-grafana --tail=50
```

### 3. 권한 확인

```bash
# Grafana Pod 내부에서 권한 확인
kubectl exec -n monitoring deployment/prometheus-grafana -- sh -c "ls -la /var/lib/grafana"

# 예상 출력:
# drwxr-xr-x 3 grafana grafana 4096 Nov 10 12:00 .
# drwxr-xr-x 3 grafana grafana 4096 Nov 10 12:00 plugins
# -rw-r--r-- 1 grafana grafana  524 Nov 10 12:01 grafana.db
```

### 4. Grafana 접속 테스트

```bash
# Port forward
kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80

# 브라우저에서 접속
# http://localhost:3000

# 또는 curl로 테스트
curl -I http://localhost:3000/login
# 예상: HTTP/1.1 200 OK
```

### 5. 데이터 영속성 확인

```bash
# Grafana에서 대시보드 생성

# Pod 재시작
kubectl rollout restart deployment/prometheus-grafana -n monitoring

# 대시보드가 유지되는지 확인 (PVC가 제대로 작동하는 증거)
```

## 예방 방법

### 1. Helm Values 템플릿 작성

모든 Helm 배포에 기본 보안 컨텍스트 포함:

```yaml
# templates/helm-defaults.yaml
commonPodSecurityContext: &podSecurityContext
  fsGroup: 1000
  runAsNonRoot: true
  runAsUser: 1000
  runAsGroup: 1000

# 각 서비스에서 사용
grafana:
  podSecurityContext: *podSecurityContext
```

### 2. Pre-flight 검증 스크립트

배포 전 PVC 권한 확인:

```bash
#!/bin/bash
# scripts/check-pvc-permissions.sh

PVC_NAME=$1
NAMESPACE=$2

kubectl run -it --rm pvc-checker \
  --image=busybox \
  --overrides="{
    \"spec\": {
      \"containers\": [{
        \"name\": \"checker\",
        \"image\": \"busybox\",
        \"command\": [\"sh\", \"-c\", \"ls -la /data && touch /data/test.txt && rm /data/test.txt\"],
        \"volumeMounts\": [{
          \"name\": \"pvc\",
          \"mountPath\": \"/data\"
        }]
      }],
      \"volumes\": [{
        \"name\": \"pvc\",
        \"persistentVolumeClaim\": {
          \"claimName\": \"$PVC_NAME\"
        }
      }]
    }
  }" \
  -n $NAMESPACE

if [ $? -eq 0 ]; then
  echo "PVC $PVC_NAME is writable"
else
  echo "ERROR: PVC $PVC_NAME is not writable"
  exit 1
fi
```

사용법:
```bash
./scripts/check-pvc-permissions.sh prometheus-grafana monitoring
```

### 3. CI/CD 파이프라인 검증

```yaml
# .github/workflows/deploy.yml
- name: Validate Helm Chart
  run: |
    helm lint k8s-manifests/monitoring/prometheus-values.yaml

- name: Check PVC Configuration
  run: |
    grep -q "podSecurityContext" k8s-manifests/monitoring/prometheus-values.yaml
    if [ $? -ne 0 ]; then
      echo "ERROR: podSecurityContext not found in prometheus-values.yaml"
      exit 1
    fi
```

### 4. 문서화

```markdown
# docs/operations/storage-guide.md

## PVC 사용 시 주의사항

### 보안 컨텍스트 설정 필수
모든 StatefulSet 및 Deployment에 `podSecurityContext` 명시:
- fsGroup: 애플리케이션의 UID/GID
- runAsUser: 컨테이너 실행 사용자
- runAsGroup: 컨테이너 실행 그룹

### 권장 패턴
\`\`\`yaml
podSecurityContext:
  fsGroup: <APP_GID>
  runAsUser: <APP_UID>
  runAsGroup: <APP_GID>
\`\`\`
```

## 관련 문서

- [시스템 아키텍처 - 모니터링 및 로깅](../../02-architecture/architecture.md#5-모니터링-및-로깅)
- [운영 가이드 - 모니터링](../../04-operations/guides/operations-guide.md)


## 참고 사항

### 애플리케이션별 기본 UID/GID

| 애플리케이션 | UID | GID | 사용자 이름 |
|------------|-----|-----|-----------|
| Grafana | 472 | 472 | grafana |
| Prometheus | 65534 | 65534 | nobody |
| PostgreSQL | 999 | 999 | postgres |
| Redis | 999 | 999 | redis |
| Nginx | 101 | 101 | nginx |

### fsGroup vs runAsUser

- `fsGroup`: 볼륨 마운트 시 **파일시스템의 그룹 소유권** 설정
- `runAsUser`: 컨테이너 **프로세스 실행** 사용자 설정
- `runAsGroup`: 컨테이너 **프로세스 실행** 그룹 설정

**둘 다 설정하는 것이 권장됩니다.**

### StorageClass별 차이

#### Local Path Provisioner
- 대부분 권한 문제 발생
- `podSecurityContext` 필수

#### AWS EBS
- fsType: ext4 권장
- mountOptions로 uid/gid 설정 가능

#### NFS
- 서버 측 export 설정에 따라 다름
- `all_squash`, `root_squash` 옵션 확인 필요

#### Longhorn
- 자동으로 권한 처리
- 별도 설정 불필요 (대부분의 경우)

### 디버깅 팁

#### 1. PVC 소유권 확인
```bash
kubectl exec -it <pod> -- ls -la /mounted-path
```

#### 2. 프로세스 사용자 확인
```bash
kubectl exec -it <pod> -- id
kubectl exec -it <pod> -- ps aux
```

#### 3. initContainer 로그 확인
```bash
kubectl logs <pod> -c init-chown-data
```

#### 4. SecurityContext 확인
```bash
kubectl get pod <pod> -o jsonpath='{.spec.securityContext}'
kubectl get pod <pod> -o jsonpath='{.spec.containers[0].securityContext}'
```

### 일반적인 실수

1. **fsGroup만 설정하고 runAsUser 누락**
   ```yaml
   # Bad
   podSecurityContext:
     fsGroup: 472
   # Pod는 root로 실행되어 보안 위험
   ```

2. **initChownData 활성화 + 대용량 PVC**
   ```yaml
   # Bad: 수 GB 데이터에 chown 시도
   initChownData:
     enabled: true
   # 5분 이상 소요 가능
   ```

3. **잘못된 UID 사용**
   ```yaml
   # Bad: Grafana를 UID 1000으로 실행
   podSecurityContext:
     runAsUser: 1000
   # Grafana 이미지는 UID 472를 기대함
   ```

## 관련 커밋
- git diff의 `prometheus-values.yaml` 변경사항

## 추가 자료
- [Kubernetes Pod Security Context](https://kubernetes.io/docs/tasks/configure-pod-container/security-context/)
- [Grafana Helm Chart Documentation](https://github.com/grafana/helm-charts/tree/main/charts/grafana)
- [Linux File Permissions](https://www.linux.com/training-tutorials/understanding-linux-file-permissions/)

# Week 1 트러블슈팅 - PVC 생성 문제

## 문제 개요

### 상황

Solid Cloud 클러스터에 Terraform으로 PostgreSQL을 배포하는 과정에서 PVC(PersistentVolumeClaim)가 무한 대기 상태에 빠지는 문제 발생

**환경**:
- Solid Cloud (titanium-prod)
- Kubernetes v1.29.7
- 노드 4개 (Control Plane: 1, Worker: 3)

---

## 증상

### Terraform Apply 중 무한 대기

```bash
$ terraform apply

module.database.kubernetes_persistent_volume_claim.postgresql: Creating...
module.database.kubernetes_persistent_volume_claim.postgresql: Still creating... [10s elapsed]
module.database.kubernetes_persistent_volume_claim.postgresql: Still creating... [20s elapsed]
# ... 계속 무한 대기
```

### PVC Pending 상태

```bash
$ kubectl get pvc -n titanium-prod
NAME             STATUS    VOLUME   CAPACITY   STORAGECLASS   AGE
postgresql-pvc   Pending                                      5m11s

$ kubectl describe pvc postgresql-pvc -n titanium-prod
Events:
  Type    Reason         Message
  ----    ------         -------
  Normal  FailedBinding  no persistent volumes available for this claim and no storage class is set
```

**핵심 에러**: `no storage class is set`

---

## 근본 원인

| 원인 | 문제 내용 | 증상 |
|------|----------|------|
| **1. StorageClass 부재** | Solid Cloud에 기본 StorageClass 미제공 | `kubectl get sc` → No resources found |
| **2. Terraform 코드 누락** | PVC 매니페스트에 `storage_class_name` 미지정 | PVC 생성 실패 |
| **3. kubeconfig 오류** | terraform.tfvars에 경로 미설정 | 잘못된 클러스터에 배포 |

### 원인 1: StorageClass 확인

```bash
$ kubectl get storageclass
No resources found

$ kubectl get csidriver
No resources found
```

**핵심**: Solid Cloud는 관리형 Kubernetes가 아니므로 StorageClass를 수동 설치해야 함 (AWS EKS, GKE와 다름)

### 원인 2: Terraform 코드

```terraform
# terraform/modules/database/main.tf (문제)
resource "kubernetes_persistent_volume_claim" "postgresql" {
  spec {
    access_modes = ["ReadWriteOnce"]
    # storage_class_name 미지정
    resources {
      requests = {
        storage = var.storage_size
      }
    }
  }
}
```

### 원인 3: kubeconfig 경로

```hcl
# terraform.tfvars (문제)
# kubeconfig_path = "/path/to/kubeconfig"  # 주석 처리됨
```

→ Terraform이 기본 `~/.kube/config` (minikube)를 사용하여 잘못된 클러스터에 배포

---

## 해결 과정

### 1단계: StorageClass 설치

**선택한 솔루션**: Local Path Provisioner (rancher.io)

**선택 이유**:
- 빠른 설치 (5분 이내)
- 별도 인프라 불필요
- Week 1 검증 목적에 적합

```bash
# 1. Local Path Provisioner 설치
kubectl apply -f https://raw.githubusercontent.com/rancher/local-path-provisioner/v0.0.28/deploy/local-path-storage.yaml \
  --kubeconfig ~/.kube/kube.conf

# 2. 기본 StorageClass로 설정
kubectl patch storageclass local-path \
  -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}' \
  --kubeconfig ~/.kube/kube.conf

# 3. 확인
kubectl get storageclass
# NAME                   PROVISIONER             VOLUMEBINDINGMODE
# local-path (default)   rancher.io/local-path   WaitForFirstConsumer
```

### 2단계: Terraform 코드 수정

**파일**: [terraform/modules/database/main.tf](../../../terraform/modules/database/main.tf)

```terraform
resource "kubernetes_persistent_volume_claim" "postgresql" {
  wait_until_bound = false  # WaitForFirstConsumer 정책 대응

  metadata {
    name      = "postgresql-pvc"
    namespace = var.namespace
    labels = {
      app = "postgresql"
    }
  }

  spec {
    access_modes       = ["ReadWriteOnce"]
    storage_class_name = "local-path"  # StorageClass 지정
    resources {
      requests = {
        storage = var.storage_size
      }
    }
  }
}
```

**주요 변경**:
- `storage_class_name = "local-path"` 추가
- `wait_until_bound = false` 추가 (타임아웃 방지)

### 3단계: kubeconfig 경로 설정

**파일**: [terraform/environments/solid-cloud/terraform.tfvars](../../../terraform/environments/solid-cloud/terraform.tfvars)

```hcl
kubeconfig_path = "~/.kube/kube.conf"  # 올바른 경로 지정
```

### 4단계: Terraform State 정리 및 재배포

```bash
# 1. 잘못된 state 제거
cd terraform/environments/solid-cloud
terraform state rm module.database.kubernetes_persistent_volume_claim.postgresql

# 2. PVC 수동 생성 (올바른 kubeconfig 사용)
cat <<'EOF' | kubectl apply -f - --kubeconfig ~/.kube/kube.conf
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgresql-pvc
  namespace: titanium-prod
  labels:
    app: postgresql
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: local-path
  resources:
    requests:
      storage: 10Gi
EOF

# 3. Terraform state에 import
terraform import module.database.kubernetes_persistent_volume_claim.postgresql titanium-prod/postgresql-pvc

# 4. Terraform apply
terraform apply -auto-approve
```

### 5단계: 검증

```bash
# Pod 상태 확인
$ kubectl get pods -n titanium-prod
NAME           READY   STATUS    RESTARTS   AGE
postgresql-0   1/1     Running   0          61s

# PVC 바인딩 확인
$ kubectl get pvc -n titanium-prod
NAME             STATUS   VOLUME                                     CAPACITY
postgresql-pvc   Bound    pvc-3f6d35bd-6d47-4e42-8444-b1b078947aad   10Gi

# PostgreSQL 연결 테스트
$ kubectl exec -it postgresql-0 -n titanium-prod -- psql -U postgres -d titanium -c "\dt"
         List of relations
 Schema | Name  | Type  |  Owner
--------+-------+-------+----------
 public | posts | table | postgres
 public | users | table | postgres
(2 rows)

# CRUD 테스트
$ kubectl exec postgresql-0 -n titanium-prod -- \
  psql -U postgres -d titanium -c \
  "INSERT INTO users (username, email, password_hash) VALUES ('test', 'test@example.com', 'hashed');
   SELECT * FROM users;"

 id | username |      email       | password_hash
----+----------+------------------+---------------
  1 | test     | test@example.com | hashed
```

**모든 테스트 통과!**

---

## 최종 솔루션 요약

### 1. Local Path Provisioner 설치

```bash
kubectl apply -f https://raw.githubusercontent.com/rancher/local-path-provisioner/v0.0.28/deploy/local-path-storage.yaml

kubectl patch storageclass local-path \
  -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'
```

### 2. Terraform 코드 수정

```terraform
# terraform/modules/database/main.tf
resource "kubernetes_persistent_volume_claim" "postgresql" {
  wait_until_bound = false

  spec {
    access_modes       = ["ReadWriteOnce"]
    storage_class_name = "local-path"  # 추가
    resources {
      requests = {
        storage = var.storage_size
      }
    }
  }
}
```

### 3. kubeconfig 경로 설정

```hcl
# terraform.tfvars
kubeconfig_path = "~/.kube/kube.conf"
```

### 4. 배포 순서

```bash
cd terraform/environments/solid-cloud
terraform init -reconfigure
terraform apply -auto-approve

kubectl get pods,pvc,pv -n titanium-prod
kubectl exec -it postgresql-0 -n titanium-prod -- psql -U postgres -d titanium
```

---

## 핵심 학습 내용

### 1. WaitForFirstConsumer 볼륨 바인딩 모드

**동작 방식**:
- PVC 생성 시 즉시 바인딩하지 않음
- Pod가 PVC를 사용하려 할 때 바인딩
- 노드 친화성을 고려한 최적 배치

**Terraform 대응**:
```terraform
wait_until_bound = false  # 타임아웃 방지
```

### 2. Solid Cloud 스토리지 특징

| 항목 | 제공 여부 | 비고 |
|------|----------|------|
| 기본 StorageClass | 미제공 | 수동 설치 필요 |
| CSI 드라이버 | 미제공 | Provisioner 별도 배포 |
| 동적 프로비저닝 | 미제공 | StorageClass 설치 후 가능 |

**관리형 Kubernetes와 비교**:
- AWS EKS: `gp2`, `gp3` 기본 제공
- GKE: `standard`, `pd-ssd` 기본 제공
- Solid Cloud: 수동 설치 필요

### 3. Local Path Provisioner 특징

**장점**:
- 빠른 설치 및 설정
- 별도 스토리지 인프라 불필요
- 개발/테스트 환경 적합

**단점**:
- 데이터가 노드 로컬에 저장
- Pod 재스케줄링 시 데이터 접근 불가
- 프로덕션 환경 부적합

**프로덕션 권장 사항**:
- NFS Provisioner
- 클라우드 스토리지 (EBS, Persistent Disk)
- Rook/Ceph 분산 스토리지

### 4. Terraform State 관리

**문제 상황**:
Terraform state와 실제 클러스터 불일치

**해결 방법**:
```bash
# 1. State에서 제거
terraform state rm <resource>

# 2. 수동 생성 후 import
terraform import <resource> <id>

# 3. 재배포
terraform apply
```

### 5. 멀티 클러스터 환경 관리

**Best Practice**:
```bash
# 환경별 kubeconfig 명확히 구분
export KUBECONFIG=~/.kube/kube.conf    # Solid Cloud
export KUBECONFIG=~/.kube/config        # Minikube

# Terraform에 명시적 전달
export TF_VAR_kubeconfig_path="$KUBECONFIG"
```

---

## 추가 문제: Kustomize 리소스 중복

### 증상

```bash
$ kubectl apply -k k8s-manifests/overlays/solid-cloud

error: may not add resource with an already registered id:
ConfigMap.v1.[noGrp]/app-config.[noNs]
```

### 원인

`kustomization.yaml`에서 ConfigMap을 resources와 configMapGenerator에 중복 정의

### 해결

```yaml
# kustomization.yaml (수정 전)
resources:
  - configmap-patch.yaml  # 중복
configMapGenerator:
  - name: app-config      # 중복

# kustomization.yaml (수정 후)
resources:
  - ../../base
  - namespace.yaml
  # configmap-patch.yaml 제거

configMapGenerator:
  - name: app-config      # ✅ generator만 사용
    behavior: merge
    literals:
      - POSTGRES_HOST=postgresql-service
      - POSTGRES_PORT=5432
```

**핵심**: resources와 generator는 상호 배타적. Generator를 사용할 경우 해당 리소스를 resources에서 제거해야 함

---

## 예방 체크리스트

향후 동일 문제 방지:

- [ ] 새 클러스터 생성 시 `kubectl get sc` 확인
- [ ] Terraform 코드에 `storage_class_name` 명시
- [ ] terraform.tfvars에 `kubeconfig_path` 설정
- [ ] PVC의 `volumeBindingMode` 확인 (WaitForFirstConsumer → `wait_until_bound = false`)
- [ ] Terraform state와 실제 리소스 일치 확인
- [ ] Kustomize resources/generator 중복 확인

---

## 참고 자료

### 관련 문서
- [Week 1 구현 가이드](./week1-implementation-guide.md)
- [Week 1 요약](./week1-summary.md)
- [마이그레이션 분석](./week1-migration-analysis.md)

### 외부 리소스
- [Local Path Provisioner](https://github.com/rancher/local-path-provisioner)
- [Kubernetes StorageClass](https://kubernetes.io/docs/concepts/storage/storage-classes/)
- [Terraform Import](https://www.terraform.io/cli/import)
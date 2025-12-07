# Solid Cloud 클러스터 데이터 백업 및 재구축 가이드

## 개요

Solid Cloud 쿠버네티스 클러스터를 안전하게 백업하고, 인스턴스를 삭제한 후 새로 재구축하는 전체 시나리오입니다.

**목표**: 데이터 무손실, 다운타임 최소화, 안전한 클러스터 재구축

**적용 시나리오**:
- Solid Cloud 인스턴스 성능 문제로 재생성 필요
- 클러스터 버전 업그레이드를 위한 재구축
- 리소스 재할당 및 최적화

## 현재 인프라 구조 (2025-01-24 기준)

### 실행 중인 리소스

```
titanium-prod namespace:
├── Deployments
│   ├── prod-api-gateway-deployment (2 replicas)
│   ├── prod-user-service-deployment (2 replicas)
│   ├── prod-auth-service-deployment (2 replicas)
│   ├── prod-blog-service-deployment (2 replicas)
│   ├── prod-redis-deployment (1 replica)
│   └── load-generator (2 replicas)
│
├── StatefulSets
│   └── postgresql (1 replica)
│
├── PersistentVolumeClaims
│   ├── postgresql-pvc (10Gi, local-path)
│   └── prod-user-service-data-pvc (1Gi, local-path)
│
└── Services
    ├── postgresql-service (ClusterIP: 10.104.145.133:5432)
    ├── prod-api-gateway-service (ClusterIP: 10.99.139.221:8000)
    ├── prod-user-service (ClusterIP: 10.96.247.138:8001)
    ├── prod-auth-service (ClusterIP: 10.97.63.73:8002)
    ├── prod-blog-service (ClusterIP: 10.106.68.122:8005)
    └── prod-redis-service (ClusterIP: 10.106.146.14:6379)
```

### 데이터베이스 구조

| 테이블 | 서비스 | 주요 컬럼 | 인덱스 |
|--------|--------|----------|--------|
| **users** | user-service | id, username, email, password_hash, created_at | idx_users_username |
| **posts** | blog-service | id, title, content, author, created_at, updated_at | idx_posts_author, idx_posts_created_at |

---

## 사전 준비

### 0. 필수 권한 및 요구사항 확인

이 가이드를 실행하기 위해 다음 권한과 리소스가 필요합니다:

#### Kubernetes 권한

- [ ] 클러스터 관리자 권한 (cluster-admin)
- [ ] StatefulSet, PVC 생성/삭제 권한
- [ ] Secret, ConfigMap 읽기/쓰기 권한
- [ ] Namespace 생성/삭제 권한

```bash
# 권한 확인
kubectl auth can-i create statefulsets -n titanium-prod
kubectl auth can-i create pvc -n titanium-prod
kubectl auth can-i get secrets -n titanium-prod
kubectl auth can-i create namespace

# 현재 사용자 확인
kubectl config view --minify
```

#### Terraform 권한

- [ ] Solid Cloud API 토큰 (클러스터 생성/삭제)
- [ ] terraform state 읽기/쓰기 권한
- [ ] VPC, 네트워크 리소스 생성 권한

#### 시스템 리소스

- [ ] 로컬 디스크 여유 공간: 최소 20GB (권장 50GB)
- [ ] 네트워크 대역폭: 안정적인 인터넷 연결 (최소 10Mbps)
- [ ] kubectl, terraform, psql 명령어 설치 및 실행 권한

```bash
# 디스크 여유 공간 확인
df -h ~

# 필수 명령어 설치 확인
command -v kubectl || echo "kubectl 설치 필요"
command -v terraform || echo "terraform 설치 필요"
command -v psql || echo "postgresql-client 설치 필요"
```

#### 네트워크 접근

- [ ] Kubernetes API 서버 접근 (6443 포트)
- [ ] PostgreSQL Pod 접근 (5432 포트)
- [ ] 외부 저장소 접근 (S3, GCS 등 - 선택)

#### 예상 소요 시간 및 리소스

| 작업 | 예상 시간 | 디스크 사용량 | 네트워크 사용량 |
|------|----------|-------------|---------------|
| 백업 | 30분~1시간 | 10~20GB | 5~10GB 다운로드 |
| 클러스터 삭제 | 10~15분 | - | - |
| 클러스터 생성 | 10~15분 | - | - |
| 인프라 재구축 | 10~15분 | - | 1~2GB |
| 데이터 복구 | 30분~1시간 | 10~20GB | 5~10GB 업로드 |
| **총계** | **2~3시간** | **20~40GB** | **15~25GB** |

> **주의사항**:
> - 디스크 공간: PostgreSQL 백업은 데이터베이스 크기의 2배 이상 필요 (압축 전/후)
> - 네트워크 대역폭: 10GB 데이터 기준 약 30분 소요 (1Gbps 네트워크 환경)
> - 다운타임: 복구 중 30분~1시간 서비스 중단 예상

### 1. 로컬 환경 설정

```bash
# 백업 디렉토리 생성
mkdir -p ~/solid-cloud-backup/$(date +%Y%m%d)
cd ~/solid-cloud-backup/$(date +%Y%m%d)

# 환경 변수 설정
export BACKUP_DATE=$(date +%Y%m%d-%H%M%S)
export BACKUP_DIR=~/solid-cloud-backup/$(date +%Y%m%d)
export NAMESPACE=titanium-prod
export PG_POD=postgresql-0  # StatefulSet Pod name

# Solid Cloud 연결 확인
kubectl cluster-info
kubectl config current-context
```

### 2. PostgreSQL 연결 확인

```bash
# PostgreSQL Pod 상태 확인
kubectl get statefulset postgresql -n $NAMESPACE
kubectl get pod $PG_POD -n $NAMESPACE

# PostgreSQL 접속 테스트
kubectl exec -n $NAMESPACE $PG_POD -- psql -U postgres -d titanium -c "\dt"

# 데이터 개수 확인
kubectl exec -n $NAMESPACE $PG_POD -- psql -U postgres -d titanium -c "
SELECT
  'users' as table_name, COUNT(*) as count FROM users
UNION ALL
SELECT
  'posts' as table_name, COUNT(*) as count FROM posts;
"
```

### 3. Terraform 상태 백업

```bash
# Terraform 상태 파일 백업
cd ~/Desktop/Git/Monitoring-v2/terraform/environments/solid-cloud
terraform state pull > $BACKUP_DIR/terraform-state-$BACKUP_DATE.json

# Terraform 리소스 목록
terraform state list > $BACKUP_DIR/terraform-resources-$BACKUP_DATE.txt

# Terraform outputs 저장
terraform output -json > $BACKUP_DIR/terraform-outputs-$BACKUP_DATE.json
```

---

## Phase 1: PostgreSQL 데이터 백업

> **자동화 옵션**: 이 Phase의 모든 백업 작업은 `./scripts/backup-solid-cloud.sh` 스크립트로 자동 실행할 수 있습니다.
>
> ```bash
> # 스크립트 실행 (Phase 1 전체 자동화)
> ./scripts/backup-solid-cloud.sh
> ```
>
> **자동화 스크립트가 수행하는 작업**:
> - PostgreSQL 전체 백업 (SQL, dump 형식)
> - Redis 데이터 백업
> - Kubernetes 리소스 YAML 백업
> - Terraform state 백업
> - 백업 매니페스트 생성 및 압축
>
> 수동으로 단계별 진행을 원하시면 아래 명령어를 따라하세요.

### 1.1 pg_dump를 사용한 논리적 백업 (권장)

#### 방법 A: 전체 데이터베이스 덤프

```bash
# SQL 형식으로 전체 백업
kubectl exec -n $NAMESPACE $PG_POD -- pg_dump -U postgres -d titanium > \
  $BACKUP_DIR/titanium-full-$BACKUP_DATE.sql

# 압축 백업 (대용량 데이터)
kubectl exec -n $NAMESPACE $PG_POD -- pg_dump -U postgres -d titanium -Fc > \
  $BACKUP_DIR/titanium-full-$BACKUP_DATE.dump

# 백업 파일 확인
ls -lh $BACKUP_DIR/titanium-*
```

#### 방법 B: 테이블별 백업

```bash
# users 테이블만 백업
kubectl exec -n $NAMESPACE $PG_POD -- pg_dump -U postgres -d titanium -t users > \
  $BACKUP_DIR/users-$BACKUP_DATE.sql

# posts 테이블만 백업
kubectl exec -n $NAMESPACE $PG_POD -- pg_dump -U postgres -d titanium -t posts > \
  $BACKUP_DIR/posts-$BACKUP_DATE.sql
```

#### 방법 C: 스키마와 데이터 분리 백업

```bash
# 스키마만 백업 (테이블 구조)
kubectl exec -n $NAMESPACE $PG_POD -- pg_dump -U postgres -d titanium --schema-only > \
  $BACKUP_DIR/titanium-schema-$BACKUP_DATE.sql

# 데이터만 백업 (INSERT문)
kubectl exec -n $NAMESPACE $PG_POD -- pg_dump -U postgres -d titanium --data-only > \
  $BACKUP_DIR/titanium-data-$BACKUP_DATE.sql
```

### 1.2 PVC 물리적 백업 (선택)

#### 방법 A: PVC 스냅샷 (클라우드 스토리지 지원 시)

```bash
# VolumeSnapshot 생성 (CSI driver 필요)
cat <<EOF | kubectl apply -f -
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: postgresql-snapshot-$BACKUP_DATE
  namespace: $NAMESPACE
spec:
  volumeSnapshotClassName: csi-snapclass
  source:
    persistentVolumeClaimName: postgresql-pvc
EOF

# 스냅샷 상태 확인
kubectl get volumesnapshot -n $NAMESPACE
```

#### 방법 B: tar를 사용한 파일 백업

```bash
# PostgreSQL 데이터 디렉토리 전체 백업
kubectl exec -n $NAMESPACE $PG_POD -- tar czf /tmp/pg-data-$BACKUP_DATE.tar.gz \
  -C /var/lib/postgresql/data .

# 로컬로 복사
kubectl cp $NAMESPACE/$PG_POD:/tmp/pg-data-$BACKUP_DATE.tar.gz \
  $BACKUP_DIR/pg-data-$BACKUP_DATE.tar.gz

# 임시 파일 삭제
kubectl exec -n $NAMESPACE $PG_POD -- rm /tmp/pg-data-$BACKUP_DATE.tar.gz
```

### 1.3 Kubernetes 리소스 백업

```bash
# PostgreSQL 관련 리소스 백업
kubectl get statefulset,pvc,svc,secret,configmap -n $NAMESPACE \
  -l app=postgresql -o yaml > $BACKUP_DIR/postgresql-k8s-resources-$BACKUP_DATE.yaml

# 전체 namespace 백업
kubectl get all,pvc,configmap,secret,gateway,virtualservice,servicemonitor \
  -n $NAMESPACE -o yaml > $BACKUP_DIR/full-namespace-$BACKUP_DATE.yaml
```

---

## Phase 2: 백업 검증

### 2.1 SQL 백업 무결성 확인

```bash
cd $BACKUP_DIR

# SQL 파일 문법 검증 (PostgreSQL 컨테이너 내부)
kubectl exec -n $NAMESPACE $PG_POD -- psql -U postgres -d template1 -f - < \
  titanium-full-$BACKUP_DATE.sql --set ON_ERROR_STOP=on --dry-run 2>&1 | head -20

# 또는 로컬 PostgreSQL로 검증 (설치되어 있는 경우)
psql -U postgres -d test_restore -f titanium-full-$BACKUP_DATE.sql --set ON_ERROR_STOP=on

# 백업 파일 내용 확인
head -100 titanium-full-$BACKUP_DATE.sql
grep -c "INSERT INTO users" titanium-full-$BACKUP_DATE.sql
grep -c "INSERT INTO posts" titanium-full-$BACKUP_DATE.sql
```

### 2.2 데이터 카운트 검증

```bash
# 현재 DB 데이터 수 확인
kubectl exec -n $NAMESPACE $PG_POD -- psql -U postgres -d titanium -c "
SELECT
  'users' as table_name, COUNT(*) as count FROM users
UNION ALL
SELECT
  'posts' as table_name, COUNT(*) as count FROM posts;
" > $BACKUP_DIR/data-count-before-$BACKUP_DATE.txt

cat $BACKUP_DIR/data-count-before-$BACKUP_DATE.txt
```

### 2.3 백업 메타데이터 생성

```bash
cat > $BACKUP_DIR/BACKUP_MANIFEST.txt <<EOF
=== PostgreSQL Backup Manifest ===
Backup Date: $BACKUP_DATE
Cluster: Solid Cloud
Namespace: $NAMESPACE
PostgreSQL Version: 15-alpine

=== Database Info ===
Database: titanium
Service: postgresql-service:5432
PVC: postgresql-pvc (10Gi)

=== Backup Files ===
$(ls -lh)

=== Data Statistics ===
$(cat data-count-before-$BACKUP_DATE.txt)

=== PostgreSQL Info ===
$(kubectl exec -n $NAMESPACE $PG_POD -- psql -U postgres -d titanium -c "SELECT version();")

=== Verification ===
Date: $(date)
Verified by: $(whoami)
Status: OK
EOF

cat $BACKUP_DIR/BACKUP_MANIFEST.txt
```

### 2.4 오프사이트 백업 (필수)

```bash
# 백업 압축
cd ~/solid-cloud-backup
tar -czf backup-postgresql-$BACKUP_DATE.tar.gz $(date +%Y%m%d)/

# 외부 저장소로 복사 (예시)
# 방법 1: 외부 디스크
cp backup-postgresql-$BACKUP_DATE.tar.gz /Volumes/ExternalDisk/

# 방법 2: AWS S3
# aws s3 cp backup-postgresql-$BACKUP_DATE.tar.gz s3://your-backup-bucket/

# 방법 3: Google Cloud Storage
# gsutil cp backup-postgresql-$BACKUP_DATE.tar.gz gs://your-backup-bucket/

# 방법 4: Dropbox/Google Drive (rclone)
# rclone copy backup-postgresql-$BACKUP_DATE.tar.gz gdrive:backups/
```

---

## Phase 3: 클러스터 제거

### 3.1 최종 확인 체크리스트

```bash
cat <<EOF
=== Pre-Delete Checklist ===
[ ] PostgreSQL 전체 백업 완료 (titanium-full-*.sql)
[ ] 백업 파일 무결성 검증 완료
[ ] 데이터 카운트 기록 완료
[ ] Terraform 상태 백업 완료
[ ] Kubernetes 리소스 YAML 백업 완료
[ ] 오프사이트 백업 완료 (외부 디스크/클라우드)
[ ] Git 커밋 및 푸시 완료
[ ] 백업 매니페스트 작성 완료

백업 위치: $BACKUP_DIR
오프사이트 백업: 확인 필요

계속 진행하려면 'yes' 입력:
EOF
read CONFIRM

if [ "$CONFIRM" != "yes" ]; then
  echo "클러스터 삭제 취소됨"
  exit 1
fi
```

### 3.2 Terraform으로 리소스 제거

```bash
cd ~/Desktop/Git/Monitoring-v2/terraform/environments/solid-cloud

# Terraform plan으로 삭제 예정 리소스 확인
terraform plan -destroy

# PostgreSQL 리소스만 제거 (선택)
terraform destroy -target=module.database

# 전체 인프라 제거
terraform destroy

# 확인 프롬프트에서 'yes' 입력
```

### 3.3 수동으로 namespace 삭제 (필요 시)

```bash
# Terraform이 관리하지 않는 리소스가 있는 경우
kubectl delete namespace $NAMESPACE

# 모니터링 스택 삭제
kubectl delete namespace monitoring

# Istio 삭제
kubectl delete namespace istio-system
```

### 3.4 Solid Cloud 클러스터 삭제

```bash
# Solid Cloud 콘솔에서 클러스터 삭제
# 또는 CLI 사용:
# solid-cloud cluster delete <cluster-name>
```

---

## Phase 4: 클러스터 재구축

### 4.1 새 클러스터 생성

```bash
# Solid Cloud에서 새 클러스터 생성
# - 노드 수: 기존과 동일 (3-4개)
# - 노드 타입: 기존과 동일
# - Kubernetes 버전: v1.29.7

# kubeconfig 다운로드
export KUBECONFIG=~/Downloads/solid-cloud-new-kubeconfig.yaml

# 연결 확인
kubectl cluster-info
kubectl get nodes
```

### 4.2 Terraform으로 인프라 재구축

```bash
cd ~/Desktop/Git/Monitoring-v2/terraform/environments/solid-cloud

# Terraform 초기화 (새 클러스터)
terraform init

# kubeconfig 경로 설정
export TF_VAR_kubeconfig_path=$KUBECONFIG

# PostgreSQL 비밀번호 설정 (보안 방법)
# 옵션 1: 프롬프트로 입력 (권장 - 히스토리에 남지 않음)
read -s -p "PostgreSQL 비밀번호 입력: " TF_VAR_postgres_password
export TF_VAR_postgres_password
echo ""

# 옵션 2: 환경 변수 파일 사용 (권장)
# source .env.secrets  # .env.secrets 파일에 비밀번호 저장 (.gitignore에 포함)

# 옵션 3: terraform.tfvars 파일 사용 (권장)
# cat > terraform.tfvars <<EOF
# postgres_password = "YOUR_SECURE_PASSWORD"
# EOF
# echo "terraform.tfvars" >> .gitignore

# ⚠️ 옵션 4: 직접 export (비권장 - 히스토리에 기록됨)
# export TF_VAR_postgres_password="YOUR_SECURE_PASSWORD"
# 위 방법 사용 시 작업 후 반드시 히스토리 삭제: history -c
```

> **보안 주의사항**:
> - 비밀번호를 직접 `export` 명령어로 설정하면 셸 히스토리에 평문으로 기록됩니다
> - 운영 환경에서는 반드시 `read -s` 프롬프트 또는 `.tfvars` 파일을 사용하세요
> - `.env.secrets`, `terraform.tfvars` 파일은 반드시 `.gitignore`에 추가하세요
> - 작업 완료 후 `unset TF_VAR_postgres_password`로 환경 변수를 삭제하세요

```bash
# Plan 확인
terraform plan

# 적용
terraform apply

# 리소스 생성 확인
kubectl get statefulset,pvc,svc -n titanium-prod -l app=postgresql

# 보안: 작업 완료 후 환경 변수 삭제
unset TF_VAR_postgres_password
```

### 4.3 Istio 및 모니터링 설치

```bash
# Istio 설치
istioctl install --set profile=default -y

# Istio sidecar injection 활성화
kubectl label namespace titanium-prod istio-injection=enabled

# Prometheus + Grafana (Helm)
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

helm install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace \
  --set prometheus.prometheusSpec.retention=7d
```

### 4.4 애플리케이션 배포

```bash
cd ~/Desktop/Git/Monitoring-v2

# Kustomize로 배포
kubectl apply -k k8s-manifests/overlays/solid-cloud

# Pod 상태 확인
kubectl get pods -n titanium-prod
kubectl wait --for=condition=ready pod -l app=api-gateway -n titanium-prod --timeout=300s
```

---

## Phase 5: PostgreSQL 데이터 복구

> **자동화 옵션**: 이 Phase의 모든 복구 작업은 `./scripts/restore-solid-cloud.sh` 스크립트로 자동 실행할 수 있습니다.
>
> ```bash
> # 스크립트 실행 (Phase 5 전체 자동화)
> ./scripts/restore-solid-cloud.sh ~/solid-cloud-backup/20250124
> ```
>
> **자동화 스크립트가 수행하는 작업**:
> - Secret 및 ConfigMap 복구
> - PVC 복구 및 Bound 대기
> - PostgreSQL StatefulSet 복구
> - PostgreSQL 데이터 복구 (pg_dump에서)
> - 나머지 Deployment 및 Service 복구
> - Istio 리소스 복구
> - 모든 Pod Ready 상태 대기 및 검증
>
> 수동으로 단계별 진행을 원하시면 아래 명령어를 따라하세요.

### 5.1 PostgreSQL Pod 준비 확인

```bash
# PostgreSQL Pod Ready 대기
kubectl wait --for=condition=ready pod/$PG_POD -n $NAMESPACE --timeout=300s

# PostgreSQL 접속 확인
kubectl exec -n $NAMESPACE $PG_POD -- psql -U postgres -d titanium -c "SELECT version();"

# 현재 테이블 확인 (초기화 스크립트로 생성됨)
kubectl exec -n $NAMESPACE $PG_POD -- psql -U postgres -d titanium -c "\dt"
```

### 5.2 데이터 복구

#### 방법 A: SQL 파일로 복구 (권장)

```bash
# 기존 데이터 삭제 (초기화 스크립트가 생성한 빈 테이블)
kubectl exec -n $NAMESPACE $PG_POD -- psql -U postgres -d titanium -c "
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS posts CASCADE;
"

# SQL 백업 파일 복구
cat $BACKUP_DIR/titanium-full-$BACKUP_DATE.sql | \
  kubectl exec -i -n $NAMESPACE $PG_POD -- psql -U postgres -d titanium

# 또는 압축 백업(dump 파일)에서 복구
kubectl cp $BACKUP_DIR/titanium-full-$BACKUP_DATE.dump $NAMESPACE/$PG_POD:/tmp/restore.dump
kubectl exec -n $NAMESPACE $PG_POD -- pg_restore -U postgres -d titanium -c /tmp/restore.dump
kubectl exec -n $NAMESPACE $PG_POD -- rm /tmp/restore.dump
```

#### 방법 B: 테이블별 복구

```bash
# users 테이블 복구
cat $BACKUP_DIR/users-$BACKUP_DATE.sql | \
  kubectl exec -i -n $NAMESPACE $PG_POD -- psql -U postgres -d titanium

# posts 테이블 복구
cat $BACKUP_DIR/posts-$BACKUP_DATE.sql | \
  kubectl exec -i -n $NAMESPACE $PG_POD -- psql -U postgres -d titanium
```

#### 방법 C: COPY를 사용한 빠른 복구 (CSV 데이터)

```bash
# 백업 시 CSV 생성했다면
kubectl exec -n $NAMESPACE $PG_POD -- psql -U postgres -d titanium -c "
COPY users FROM '/tmp/users.csv' WITH CSV HEADER;
COPY posts FROM '/tmp/posts.csv' WITH CSV HEADER;
"
```

### 5.3 복구 검증

```bash
# 데이터 개수 확인
kubectl exec -n $NAMESPACE $PG_POD -- psql -U postgres -d titanium -c "
SELECT
  'users' as table_name, COUNT(*) as count FROM users
UNION ALL
SELECT
  'posts' as table_name, COUNT(*) as count FROM posts;
" > $BACKUP_DIR/data-count-after-$BACKUP_DATE.txt

# 백업 전/후 비교
echo "=== Before (Backup) ==="
cat $BACKUP_DIR/data-count-before-$BACKUP_DATE.txt
echo ""
echo "=== After (Restore) ==="
cat $BACKUP_DIR/data-count-after-$BACKUP_DATE.txt

# 샘플 데이터 확인
kubectl exec -n $NAMESPACE $PG_POD -- psql -U postgres -d titanium -c "
SELECT * FROM users LIMIT 5;
"

kubectl exec -n $NAMESPACE $PG_POD -- psql -U postgres -d titanium -c "
SELECT * FROM posts LIMIT 5;
"
```

---

## Phase 6: 애플리케이션 검증

### 6.1 서비스 Health Check

```bash
# 모든 Pod 상태 확인
kubectl get pods -n $NAMESPACE

# Istio Gateway IP 확인
export INGRESS_IP=$(kubectl get svc -n istio-system istio-ingressgateway \
  -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

echo "Ingress IP: $INGRESS_IP"

# Health check
curl http://$INGRESS_IP/api/users/health
curl http://$INGRESS_IP/blog/health
curl http://$INGRESS_IP/api/auth/health
```

### 6.2 데이터 기능 테스트

```bash
# User Service - 사용자 목록 조회
curl http://$INGRESS_IP/api/users/ | jq '.'

# Blog Service - 포스트 목록 조회
curl http://$INGRESS_IP/blog/ | jq '.'

# Blog Service - 특정 포스트 조회
curl http://$INGRESS_IP/blog/1 | jq '.'
```

### 6.3 k6 부하 테스트

```bash
cd ~/Desktop/Git/Monitoring-v2/tests/performance

# 환경 변수 설정
export INGRESS_IP=$INGRESS_IP

# Quick 테스트
k6 run quick-test.js

# 전체 부하 테스트
k6 run load-test.js
```

### 6.4 PostgreSQL 연결 모니터링

```bash
# 활성 연결 수 확인
kubectl exec -n $NAMESPACE $PG_POD -- psql -U postgres -d titanium -c "
SELECT
  datname,
  count(*) as connections,
  max(state) as state
FROM pg_stat_activity
WHERE datname = 'titanium'
GROUP BY datname;
"

# 슬로우 쿼리 확인
kubectl exec -n $NAMESPACE $PG_POD -- psql -U postgres -d titanium -c "
SELECT
  pid,
  now() - query_start as duration,
  query
FROM pg_stat_activity
WHERE state = 'active'
ORDER BY duration DESC
LIMIT 10;
"
```

---

## Phase 7: 최종 정리

### 7.1 문서 업데이트

```bash
cat >> ~/Desktop/Git/Monitoring-v2/CHANGELOG.md <<EOF

## $(date +%Y-%m-%d) - Solid Cloud Cluster Rebuild

### Summary
- Solid Cloud 클러스터 재구축 완료
- PostgreSQL 데이터 전체 복구 성공

### Backup Details
- Backup Date: $BACKUP_DATE
- Database: titanium (PostgreSQL 15)
- Tables: users, posts
- Backup Size: $(du -sh $BACKUP_DIR | cut -f1)

### Data Verification
$(cat $BACKUP_DIR/data-count-after-$BACKUP_DATE.txt)

### Issues
- None

### Next Steps
- 24시간 모니터링
- 성능 테스트
- 백업 자동화 설정
EOF
```

### 7.2 자동 백업 설정

#### CronJob으로 정기 백업

```bash
cat > k8s-manifests/base/postgresql-backup-cronjob.yaml <<'EOF'
apiVersion: batch/v1
kind: CronJob
metadata:
  name: postgresql-backup
  labels:
    app: postgresql
spec:
  schedule: "0 2 * * *"  # 매일 새벽 2시 (UTC)
  jobTemplate:
    spec:
      template:
        metadata:
          annotations:
            sidecar.istio.io/inject: "false"
        spec:
          containers:
          - name: pg-backup
            image: postgres:15-alpine
            command: ["/bin/sh", "-c"]
            args:
            - |
              BACKUP_FILE="titanium-$(date +%Y%m%d-%H%M%S).sql"
              pg_dump -h postgresql-service -U postgres -d titanium > /backup/$BACKUP_FILE
              echo "Backup created: $BACKUP_FILE"
              # TODO: S3 업로드 추가
            env:
            - name: PGPASSWORD
              valueFrom:
                secretKeyRef:
                  name: postgresql-secret
                  key: POSTGRES_PASSWORD
            volumeMounts:
            - name: backup-storage
              mountPath: /backup
          volumes:
          - name: backup-storage
            emptyDir: {}
            # TODO: S3나 PVC로 변경
          restartPolicy: OnFailure
EOF

kubectl apply -f k8s-manifests/base/postgresql-backup-cronjob.yaml -n $NAMESPACE
```

### 7.3 모니터링 알람 설정

```bash
# PostgreSQL Exporter 설치 (선택)
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install postgresql-exporter prometheus-community/prometheus-postgres-exporter \
  --namespace $NAMESPACE \
  --set config.datasource.host=postgresql-service \
  --set config.datasource.user=postgres \
  --set config.datasource.password=$TF_VAR_postgres_password
```

---

## 롤백 시나리오

### 롤백 결정 기준

다음 상황에서 즉시 롤백을 고려하세요:

#### 1. 데이터 정합성 문제

```bash
# 복구 후 데이터 카운트 확인
RESTORED_USERS=$(kubectl exec -n $NAMESPACE $PG_POD -- psql -U postgres -d titanium -t -c "SELECT COUNT(*) FROM users;" | tr -d ' ')
RESTORED_POSTS=$(kubectl exec -n $NAMESPACE $PG_POD -- psql -U postgres -d titanium -t -c "SELECT COUNT(*) FROM posts;" | tr -d ' ')

# 백업 시점 데이터와 비교
BACKUP_USERS=$(grep "users" $BACKUP_DIR/data-count-before-*.txt | awk '{print $3}')
BACKUP_POSTS=$(grep "posts" $BACKUP_DIR/data-count-before-*.txt | awk '{print $3}')

# 10% 이상 차이 발생 시 롤백 고려
echo "Users: Backup=$BACKUP_USERS, Restored=$RESTORED_USERS"
echo "Posts: Backup=$BACKUP_POSTS, Restored=$RESTORED_POSTS"
```

**롤백 조건**:
- 데이터 개수가 백업 시점 대비 10% 이상 차이
- 주요 테이블(users, posts)이 존재하지 않음
- 외래 키 제약조건이 깨져 있음

#### 2. 서비스 가용성 문제

```bash
# API Health Check (10회 테스트)
FAIL_COUNT=0
for i in {1..10}; do
  if ! curl -sf http://$INGRESS_IP/api/users/health > /dev/null; then
    ((FAIL_COUNT++))
  fi
  sleep 2
done

echo "실패율: $((FAIL_COUNT * 10))%"
```

**롤백 조건**:
- Health check 실패율 > 5% (10회 중 1회 이상 실패)
- API 응답 시간 > 5초 (정상: 100ms 이내)
- Pod가 CrashLoopBackOff 상태로 3회 이상 재시작

#### 3. 복구 시간 초과

**롤백 조건**:
- PostgreSQL 데이터 복구 시간 > 2시간 (예상: 30분~1시간)
- 전체 복구 프로세스 시간 > 6시간 (예상: 2~3시간)
- Pod Ready 대기 시간 > 30분 (예상: 5~10분)

#### 4. 리소스 부족

```bash
# 리소스 사용량 확인
kubectl top nodes
kubectl top pods -n $NAMESPACE
```

**롤백 조건**:
- 노드 CPU 사용률 > 90% 지속
- 노드 메모리 사용률 > 95% 지속
- PVC 용량 부족 (사용률 > 90%)

### 복구 중 문제 발생 시

#### 옵션 1: 백업에서 재복구

```bash
# 현재 데이터 삭제
kubectl exec -n $NAMESPACE $PG_POD -- psql -U postgres -d titanium -c "
DROP DATABASE titanium WITH (FORCE);
CREATE DATABASE titanium;
"

# 백업에서 재복구
cat $BACKUP_DIR/titanium-full-$BACKUP_DATE.sql | \
  kubectl exec -i -n $NAMESPACE $PG_POD -- psql -U postgres -d titanium
```

#### 옵션 2: Terraform 재적용

```bash
cd ~/Desktop/Git/Monitoring-v2/terraform/environments/solid-cloud

# PostgreSQL 리소스 재생성
terraform destroy -target=module.database
terraform apply -target=module.database
```

#### 옵션 3: PVC 스냅샷에서 복구 (스냅샷 생성한 경우)

```bash
# PVC를 스냅샷에서 복구
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgresql-pvc-restored
  namespace: $NAMESPACE
spec:
  dataSource:
    name: postgresql-snapshot-$BACKUP_DATE
    kind: VolumeSnapshot
    apiGroup: snapshot.storage.k8s.io
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
EOF

# StatefulSet에서 새 PVC 사용
kubectl patch statefulset postgresql -n $NAMESPACE -p '
{
  "spec": {
    "template": {
      "spec": {
        "volumes": [{
          "name": "postgresql-data",
          "persistentVolumeClaim": {
            "claimName": "postgresql-pvc-restored"
          }
        }]
      }
    }
  }
}'
```

---

## 개선 권장사항

### 단기 (1주 내)

1. **자동 백업 외부 저장소 연동**
   - S3/GCS로 pg_dump 자동 업로드
   - 현재: CronJob 예시만 작성됨
   - 목표: 매일 새벽 자동 백업 및 외부 업로드

2. **백업 복구 테스트**
   - 매월 1회 복구 훈련
   - 복구 시간 측정 (RTO)
   - 복구 성공률 검증

### 중기 (1개월 내)

1. **PostgreSQL HA 구성**
   - StatefulSet replica 증가 (1 → 3)
   - Streaming Replication 설정
   - Patroni 또는 Stolon 도입 검토

2. **Point-in-Time Recovery (PITR)**
   - WAL archiving 설정
   - 특정 시점으로 복구 가능

### 장기

1. **Multi-Region 백업**
   - 지역 장애 대비
   - Cross-region replication

2. **Managed Database 고려**
   - RDS, Cloud SQL 등
   - 백업 자동화 및 HA 내장

---

## 참고 자료

- [PostgreSQL Backup and Restore](https://www.postgresql.org/docs/current/backup.html)
- [pg_dump Documentation](https://www.postgresql.org/docs/current/app-pgdump.html)
- [Kubernetes StatefulSet](https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/)
- [Terraform PostgreSQL Provider](https://registry.terraform.io/providers/hashicorp/kubernetes/latest/docs)

---

## 체크리스트 템플릿

```markdown
## Cluster Rebuild Checklist

### Pre-Rebuild
- [ ] PostgreSQL pg_dump 백업 완료
- [ ] 백업 파일 무결성 검증
- [ ] 데이터 카운트 기록
- [ ] Terraform 상태 백업
- [ ] 오프사이트 백업 완료

### Rebuild
- [ ] 새 클러스터 생성
- [ ] Terraform apply 성공
- [ ] PostgreSQL StatefulSet Running
- [ ] PVC Bound 확인

### Post-Rebuild
- [ ] 데이터 복구 성공
- [ ] 데이터 카운트 일치 확인
- [ ] API Health Check 통과
- [ ] k6 부하 테스트 통과
- [ ] 24시간 모니터링 완료
- [ ] 문서 업데이트
- [ ] 팀 공유
```

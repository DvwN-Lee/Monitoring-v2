# Solid Cloud Cluster 재구축 빠른 시작 가이드

## 개요

Solid Cloud K8s Cluster를 백업하고 재구축하는 전체 프로세스를 자동화된 스크립트로 실행하는 가이드입니다.

## 사전 요구사항

### 필수 권한

- [ ] Kubernetes Cluster 관리자 권한 (cluster-admin)
- [ ] Solid Cloud API 토큰 (Cluster 생성/삭제)
- [ ] Terraform state 읽기/쓰기 권한

```bash
# 권한 확인
kubectl auth can-i create statefulsets -n titanium-prod
kubectl auth can-i create pvc -n titanium-prod
kubectl auth can-i get secrets -n titanium-prod
```

### 필수 도구

- [ ] kubectl (v1.28+)
- [ ] terraform (v1.5+)
- [ ] psql (PostgreSQL client)

```bash
# 도구 설치 확인
command -v kubectl || echo "kubectl 설치 필요"
command -v terraform || echo "terraform 설치 필요"
command -v psql || echo "postgresql-client 설치 필요"
```

### 시스템 리소스

- [ ] 로컬 디스크 여유 공간: 최소 20GB (권장 50GB)
- [ ] 네트워크 대역폭: 안정적인 인터넷 연결 (최소 10Mbps)
- [ ] 예상 소요 시간: 2~3시간

```bash
# 디스크 여유 공간 확인
df -h ~
```

## 전체 프로세스 요약

```
1. 백업 실행 (30분~1시간)
   └── ./scripts/backup-solid-cloud.sh

2. 백업 검증 및 오프사이트 저장

3. 기존 Cluster 삭제
   └── terraform destroy

4. 새 Cluster 생성
   └── Solid Cloud 콘솔 또는 CLI

5. 인프라 재구축
   └── terraform apply

6. 데이터 복구 (30분~1시간)
   └── ./scripts/restore-solid-cloud.sh

7. 검증 및 테스트
```

---

## Step 1: 백업 실행

### 1.1 Cluster 연결

```bash
# Solid Cloud Cluster로 연결
cd ~/Desktop/Git/Monitoring-v2

# kubectl context 전환
kubectl config use-context solid-cloud

# 연결 확인
kubectl get nodes
kubectl get pods -n titanium-prod
```

### 1.2 백업 스크립트 실행

```bash
# 백업 스크립트 실행 (30분~1시간 소요)
./scripts/backup-solid-cloud.sh
```

**스크립트가 자동으로 수행하는 작업**:
1. PostgreSQL 데이터베이스 전체 백업 (pg_dump)
2. Redis 데이터 백업 (RDB snapshot)
3. Kubernetes 리소스 YAML 백업 (Deployments, Services, PVC 등)
4. Terraform state 백업
5. 백업 매니페스트 생성
6. 전체 백업 압축 및 체크섬 생성

**백업 완료 후 출력 예시**:
```
=== 백업 완료 ===

백업 위치:
  - 디렉토리: ~/solid-cloud-backup/20250124
  - 아카이브: ~/solid-cloud-backup/solid-cloud-backup-20250124-143022.tar.gz

다음 단계:
  1. 백업 검증: cat ~/solid-cloud-backup/20250124/BACKUP_MANIFEST.txt
  2. 오프사이트 백업: 외부 저장소로 아카이브 복사
  3. Cluster 삭제: terraform destroy (백업 검증 후)
  4. 복구: ./scripts/restore-solid-cloud.sh
```

### 1.3 백업 검증

```bash
# 백업 디렉토리로 이동
cd ~/solid-cloud-backup/20250124

# 백업 매니페스트 확인
cat BACKUP_MANIFEST.txt

# 백업 파일 확인
ls -lh

# PostgreSQL 백업 파일 내용 샘플 확인
head -100 postgresql-titanium-*.sql | grep -E "CREATE|INSERT"

# 데이터 카운트 확인
cat data-count-before-*.txt
```

### 1.4 오프사이트 백업 (필수)

```bash
# 백업 아카이브를 외부 저장소로 복사

# 옵션 1: 외부 디스크
cp ~/solid-cloud-backup/solid-cloud-backup-*.tar.gz /Volumes/ExternalDisk/

# 옵션 2: AWS S3 (설정되어 있는 경우)
# aws s3 cp ~/solid-cloud-backup/solid-cloud-backup-*.tar.gz s3://your-backup-bucket/

# 옵션 3: Google Drive/Dropbox (rclone 사용)
# rclone copy ~/solid-cloud-backup/solid-cloud-backup-*.tar.gz gdrive:backups/

# 옵션 4: 다른 서버로 scp
# scp ~/solid-cloud-backup/solid-cloud-backup-*.tar.gz user@backup-server:/backups/
```

---

## Step 2: 기존 Cluster 삭제

### 2.1 최종 확인 체크리스트

```bash
cat <<EOF
=== 삭제 전 체크리스트 ===
[ ] PostgreSQL 백업 완료 및 검증
[ ] Redis 백업 완료
[ ] Kubernetes 리소스 YAML 백업 완료
[ ] Terraform state 백업 완료
[ ] 백업 아카이브 생성 완료
[ ] 오프사이트 백업 완료
[ ] 백업 매니페스트 확인 완료

모든 항목이 완료되었습니까? (yes/no)
EOF
```

### 2.2 Terraform으로 리소스 삭제

```bash
cd ~/Desktop/Git/Monitoring-v2/terraform/environments/solid-cloud

# 삭제 예정 리소스 확인
terraform plan -destroy

# 전체 인프라 삭제
terraform destroy

# 확인 프롬프트에 'yes' 입력
```

### 2.3 Solid Cloud 인스턴스 삭제

```bash
# Solid Cloud 콘솔에서 Cluster 삭제
# 또는 CLI 사용:
# solid-cloud cluster delete <cluster-name>
```

---

## Step 3: 새 Cluster 생성

### 3.1 Solid Cloud에서 새 Cluster 생성

**Solid Cloud 콘솔에서**:
1. Cluster 생성 페이지로 이동
2. Cluster 설정:
   - 이름: titanium-cluster (또는 원하는 이름)
   - 리전: kr-seoul
   - Kubernetes 버전: v1.29.7 이상
   - Node 수: 3-4개 (기존과 동일)
   - Node 타입: 기존과 동일
3. 생성 버튼 클릭
4. Cluster가 Running 상태가 될 때까지 대기 (5~10분)

### 3.2 kubeconfig 설정

```bash
# Solid Cloud에서 kubeconfig 다운로드
# (콘솔에서 다운로드 또는 CLI 사용)

# .env.k8s 파일 업데이트
# ⚠️ 보안: 직접 파일에 작성하지 말고, 보안 방법 사용
cat > ~/Desktop/Git/Monitoring-v2/.env.k8s << 'EOF'
# Solid Cloud Kubernetes Credentials (새 Cluster)
K8S_API_SERVER="https://새Cluster-api-server:6443"
K8S_TOKEN="새로운_서비스_어카운트_토큰"
K8S_CA_CERT="새로운_CA_인증서_base64"
K8S_CLUSTER_NAME="solid-cloud"
K8S_SKIP_TLS_VERIFY="false"
EOF

# kubectl context 전환
kubectl config use-context solid-cloud

# 연결 확인
kubectl cluster-info
kubectl get nodes
```

> **보안 주의사항**:
> - `.env.k8s` 파일에는 민감한 인증 정보가 포함됩니다
> - 반드시 `.gitignore`에 추가하여 Git 저장소에 커밋되지 않도록 하세요
> - 파일 권한을 `chmod 600 .env.k8s`로 설정하세요

---

## Step 4: 인프라 재구축

### 4.1 Terraform으로 인프라 생성

```bash
cd ~/Desktop/Git/Monitoring-v2/terraform/environments/solid-cloud

# Terraform 초기화 (새 Cluster용)
terraform init

# PostgreSQL 비밀번호 설정 (백업 시 사용한 것과 동일하게)
# 보안 방법 1: 프롬프트로 입력 (권장)
read -s -p "PostgreSQL 비밀번호 입력: " TF_VAR_postgres_password
export TF_VAR_postgres_password
echo ""

# 보안 방법 2: terraform.tfvars 파일 사용 (권장)
# cat > terraform.tfvars <<EOF
# postgres_password = "YOUR_SECURE_PASSWORD"
# EOF
# echo "terraform.tfvars" >> .gitignore

# Plan 확인
terraform plan

# 인프라 생성
terraform apply

# 확인 프롬프트에 'yes' 입력

# 보안: 작업 완료 후 환경 변수 삭제
unset TF_VAR_postgres_password
```

> **보안 주의사항**:
> - 비밀번호를 직접 export하면 셸 히스토리에 기록됩니다
> - `read -s` 또는 `.tfvars` 파일 사용을 권장합니다
> - 작업 후 `unset`으로 환경 변수를 삭제하세요

### 4.2 인프라 생성 확인

```bash
# Namespace 확인
kubectl get namespace titanium-prod

# PostgreSQL 리소스 확인
kubectl get statefulset,pvc,svc -n titanium-prod -l app=postgresql

# Pod 상태 확인
kubectl get pods -n titanium-prod
```

### 4.3 Istio 설치 (선택)

```bash
# Istio 설치
istioctl install --set profile=default -y

# Istio sidecar injection 활성화
kubectl label namespace titanium-prod istio-injection=enabled
```

### 4.4 모니터링 스택 설치 (선택)

```bash
# Prometheus + Grafana 설치
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

helm install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace \
  --set prometheus.prometheusSpec.retention=7d
```

---

## Step 5: 데이터 복구

### 5.1 복구 스크립트 실행

```bash
# 백업 디렉토리 경로 확인
ls -d ~/solid-cloud-backup/*/

# 복구 스크립트 실행 (30분~1시간 소요)
./scripts/restore-solid-cloud.sh ~/solid-cloud-backup/20250124
```

**스크립트가 자동으로 수행하는 작업**:
1. Namespace 생성 및 확인
2. Secret 및 ConfigMap 복구
3. PVC 복구 및 Bound 대기
4. PostgreSQL StatefulSet 복구
5. PostgreSQL 데이터 복구 (pg_dump에서)
6. 나머지 Deployment 및 Service 복구
7. Istio 리소스 복구 (있는 경우)
8. 모든 Pod Ready 대기

**복구 완료 후 출력 예시**:
```
=== 복구 완료 ===

현재 리소스 상태:
NAME                                            READY   STATUS    RESTARTS   AGE
pod/postgresql-0                                2/2     Running   0          5m
pod/prod-api-gateway-deployment-xxx             2/2     Running   0          3m
pod/prod-user-service-deployment-xxx            2/2     Running   0          3m
...

다음 단계:
  1. 데이터 검증: kubectl exec -n titanium-prod postgresql-0 -- psql -U postgres -d titanium -c 'SELECT COUNT(*) FROM users;'
  2. API 테스트: curl http://$INGRESS_IP/api/users/
  3. 모니터링: kubectl get pods -n titanium-prod -w
```

### 5.2 데이터 검증

```bash
# PostgreSQL 데이터 확인
kubectl exec -n titanium-prod postgresql-0 -- psql -U postgres -d titanium -c "
SELECT
  'users' as table_name, COUNT(*) as count FROM users
UNION ALL
SELECT
  'posts' as table_name, COUNT(*) as count FROM posts;
"

# 샘플 데이터 확인
kubectl exec -n titanium-prod postgresql-0 -- psql -U postgres -d titanium -c "
SELECT * FROM users LIMIT 5;
"

kubectl exec -n titanium-prod postgresql-0 -- psql -U postgres -d titanium -c "
SELECT * FROM posts LIMIT 5;
"
```

---

## Step 6: 검증 및 테스트

### 6.1 서비스 Health Check

```bash
# 모든 Pod 상태 확인
kubectl get pods -n titanium-prod

# Istio Gateway IP 확인 (Istio 사용하는 경우)
export INGRESS_IP=$(kubectl get svc -n istio-system istio-ingressgateway \
  -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

echo "Ingress IP: $INGRESS_IP"

# Health check
curl http://$INGRESS_IP/api/users/health
curl http://$INGRESS_IP/blog/health
curl http://$INGRESS_IP/api/auth/health
```

### 6.2 API 기능 테스트

```bash
# User Service - 사용자 목록 조회
curl http://$INGRESS_IP/api/users/ | jq '.'

# Blog Service - 포스트 목록 조회
curl http://$INGRESS_IP/blog/ | jq '.'

# Blog Service - 특정 포스트 조회
curl http://$INGRESS_IP/blog/1 | jq '.'
```

### 6.3 부하 테스트 (선택)

```bash
cd ~/Desktop/Git/Monitoring-v2/tests/performance

# 환경 변수 설정
export INGRESS_IP=$INGRESS_IP

# Quick 테스트
k6 run quick-test.js

# 전체 부하 테스트
k6 run load-test.js
```

---

## 롤백 결정 기준

복구 작업 중 다음 상황이 발생하면 즉시 롤백을 고려하세요:

### 1. 데이터 정합성 문제

```bash
# 복구 후 데이터 카운트 확인
kubectl exec -n titanium-prod postgresql-0 -- psql -U postgres -d titanium -c "
SELECT 'users' as table_name, COUNT(*) as count FROM users
UNION ALL
SELECT 'posts' as table_name, COUNT(*) as count FROM posts;
"
```

**롤백 조건**:
- [ ] 데이터 개수가 백업 시점 대비 10% 이상 차이
- [ ] 주요 테이블이 존재하지 않음
- [ ] 외래 키 제약조건이 깨져 있음

### 2. 서비스 가용성 문제

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
- [ ] Health check 실패율 > 5% (10회 중 1회 이상 실패)
- [ ] API 응답 시간 > 5초 (정상: 100ms 이내)
- [ ] Pod가 CrashLoopBackOff 상태로 3회 이상 재시작

### 3. 복구 시간 초과

**롤백 조건**:
- [ ] PostgreSQL 데이터 복구 시간 > 2시간 (예상: 30분~1시간)
- [ ] 전체 복구 프로세스 시간 > 6시간 (예상: 2~3시간)
- [ ] Pod Ready 대기 시간 > 30분 (예상: 5~10분)

### 4. 리소스 부족

```bash
# 리소스 사용량 확인
kubectl top nodes
kubectl top pods -n titanium-prod
```

**롤백 조건**:
- [ ] Node CPU 사용률 > 90% 지속
- [ ] Node 메모리 사용률 > 95% 지속
- [ ] PVC 용량 부족 (사용률 > 90%)

---

## 트러블슈팅

### 문제 1: PostgreSQL Pod가 시작되지 않음

**증상**: PostgreSQL Pod가 CrashLoopBackOff 상태

**해결**:
```bash
# 로그 확인
kubectl logs -n titanium-prod postgresql-0 --previous

# PVC 상태 확인
kubectl get pvc -n titanium-prod

# PVC가 Pending 상태인 경우
kubectl describe pvc postgresql-pvc -n titanium-prod

# StorageClass 확인
kubectl get storageclass
```

### 문제 2: 데이터 복구 실패

**증상**: SQL 백업 파일 복구 중 오류 발생

**해결**:
```bash
# 기존 데이터베이스 완전 초기화
kubectl exec -n titanium-prod postgresql-0 -- psql -U postgres -c "
DROP DATABASE IF EXISTS titanium WITH (FORCE);
CREATE DATABASE titanium;
"

# 백업 파일 재복구
cat ~/solid-cloud-backup/20250124/postgresql-titanium-*.sql | \
  kubectl exec -i -n titanium-prod postgresql-0 -- psql -U postgres -d titanium
```

### 문제 3: API 엔드포인트 접근 불가

**증상**: curl 요청 시 연결 거부 또는 타임아웃

**해결**:
```bash
# Service 확인
kubectl get svc -n titanium-prod

# Endpoint 확인
kubectl get endpoints -n titanium-prod

# Pod 네트워크 테스트
kubectl exec -n titanium-prod <api-gateway-pod> -- curl http://postgresql-service:5432

# Istio Gateway 확인 (Istio 사용하는 경우)
kubectl get gateway,virtualservice -n titanium-prod
```

---

## 자주 묻는 질문 (FAQ)

### Q1: 백업에 얼마나 시간이 걸리나요?

**A**: 데이터 크기에 따라 다르지만, 일반적으로:
- PostgreSQL 백업: 10~30분
- Redis 백업: 5분 미만
- Kubernetes 리소스 백업: 5분 미만
- 전체 압축 및 체크섬: 5~10분
- **총 소요 시간: 30분~1시간**

### Q2: 복구에 얼마나 시간이 걸리나요?

**A**: 백업과 유사하게:
- 인프라 재구축: 10~15분
- PostgreSQL 데이터 복구: 10~30분
- 나머지 리소스 복구: 10~15분
- **총 소요 시간: 30분~1시간**

### Q3: 백업 중에 서비스가 중단되나요?

**A**: 아니요. 백업은 운영 중인 Cluster에서 실행되며, 서비스는 계속 운영됩니다.
- PostgreSQL: `pg_dump`는 읽기 전용 작업으로 서비스에 영향 없음
- Redis: `SAVE` 명령은 짧은 블로킹이 발생하지만 몇 초 이내

### Q4: 백업을 얼마나 자주 해야 하나요?

**A**: 데이터 중요도에 따라 다르지만, 권장 사항:
- **매일 자동 백업** (새벽 시간대)
- **주요 변경 전 수동 백업** (Cluster 업그레이드, 마이그레이션 등)
- **월 1회 복구 테스트** (백업 유효성 검증)

### Q5: 백업 파일을 어디에 저장해야 하나요?

**A**: 다음 위치에 중복 저장 권장:
1. **로컬 디스크**: 빠른 접근 (30일 보관)
2. **외부 디스크**: 물리적 분리 (90일 보관)
3. **클라우드 스토리지**: S3, GCS 등 (1년 보관)

---

## 체크리스트

### 백업 체크리스트
- [ ] Cluster 연결 확인
- [ ] 백업 스크립트 실행 완료
- [ ] 백업 매니페스트 확인
- [ ] PostgreSQL 백업 파일 검증
- [ ] Redis 백업 파일 확인
- [ ] 백업 아카이브 생성 완료
- [ ] 오프사이트 백업 완료

### 재구축 체크리스트
- [ ] 백업 검증 완료
- [ ] 기존 Cluster 삭제 완료
- [ ] 새 Cluster 생성 완료
- [ ] kubeconfig 설정 완료
- [ ] Terraform apply 성공
- [ ] 인프라 리소스 생성 확인

### 복구 체크리스트
- [ ] 복구 스크립트 실행 완료
- [ ] PostgreSQL 데이터 복구 완료
- [ ] 데이터 카운트 일치 확인
- [ ] 모든 Pod Running 상태 확인
- [ ] API Health Check 통과
- [ ] 기능 테스트 통과
- [ ] 부하 테스트 통과 (선택)

---

## 참고 문서

- [상세 재구축 가이드](./solid-cloud-cluster-rebuild.md)
- [PostgreSQL 백업 모범 사례](https://www.postgresql.org/docs/current/backup.html)
- [Kubernetes 백업 전략](https://kubernetes.io/docs/tasks/administer-cluster/configure-upgrade-etcd/#backing-up-an-etcd-cluster)

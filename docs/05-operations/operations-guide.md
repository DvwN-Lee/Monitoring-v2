# Cloud-Native 마이크로서비스 플랫폼 운영 가이드

## 문서 정보
- **버전**: 1.0
- **작성일**: 2025년 11월 3일
- **대상**: 시스템 운영자, DevOps 엔지니어

---

## 목차
1. [시스템 개요](#시스템-개요)
2. [접속 및 인증](#접속-및-인증)
3. [일상 운영 작업](#일상-운영-작업)
4. [모니터링 및 알림](#모니터링-및-알림)
5. [배포 및 롤백](#배포-및-롤백)
6. [트러블슈팅](#트러블슈팅)
7. [보안 관리](#보안-관리)
8. [백업 및 복구](#백업-및-복구)

---

## 시스템 개요

### 아키텍처
- **환경**: Solid Cloud (단국대학교)
- **Kubernetes 버전**: v1.29.7
- **주요 네임스페이스**:
  - `titanium-prod`: 애플리케이션 서비스
  - `istio-system`: Istio 서비스 메시
  - `monitoring`: Prometheus, Grafana, Loki
  - `argocd`: Argo CD GitOps

### 주요 컴포넌트
- **애플리케이션**: API Gateway, Auth Service, User Service, Blog Service
- **데이터베이스**: PostgreSQL (StatefulSet)
- **서비스 메시**: Istio 1.20.1 (mTLS STRICT)
- **모니터링**: Prometheus + Grafana + Kiali + Loki
- **CI/CD**: GitHub Actions + Argo CD

---

## 접속 및 인증

### Kubernetes 클러스터 접속

**kubectl 설정 확인**:
```bash
# 현재 컨텍스트 확인
kubectl config current-context

# 클러스터 정보 확인
kubectl cluster-info

# 네임스페이스 목록 확인
kubectl get namespaces
```

**Token 기반 인증** (새로운 접속 설정 시):
```bash
# .env.k8s 파일에서 인증 정보 로드
source .env.k8s

# kubectl 설정
kubectl config set-cluster solid-cloud \
  --server=$K8S_API_SERVER \
  --certificate-authority=<(echo $K8S_CA_CERT | base64 -d)

kubectl config set-credentials solid-cloud-user \
  --token=$K8S_TOKEN

kubectl config set-context solid-cloud \
  --cluster=solid-cloud \
  --user=solid-cloud-user

kubectl config use-context solid-cloud
```

### 주요 서비스 접속 정보

| 서비스 | URL | 인증 |
|--------|-----|------|
| Grafana 대시보드 | http://10.0.11.168:30300 | admin/admin123 |
| 애플리케이션 | http://10.0.11.168:31304 | - |
| Argo CD | 클러스터 내부 | admin/초기비밀번호 |

**Argo CD 초기 비밀번호 확인**:
```bash
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath="{.data.password}" | base64 -d; echo
```

---

## 일상 운영 작업

### 1. 시스템 상태 확인

**전체 Pod 상태 확인**:
```bash
# 프로덕션 서비스 상태
kubectl get pods -n titanium-prod

# Istio 상태
kubectl get pods -n istio-system

# 모니터링 상태
kubectl get pods -n monitoring

# Argo CD 상태
kubectl get pods -n argocd
```

**서비스 및 엔드포인트 확인**:
```bash
# 서비스 목록
kubectl get svc -n titanium-prod

# Ingress/Gateway 확인
kubectl get gateway,virtualservice -n titanium-prod
```

**리소스 사용량 확인**:
```bash
# Node 리소스 사용량
kubectl top nodes

# Pod 리소스 사용량
kubectl top pods -n titanium-prod

# HPA 상태 확인
kubectl get hpa -n titanium-prod
```

### 2. 로그 확인

**Pod 로그 조회**:
```bash
# 특정 Pod 로그 (istio-proxy 포함 시 컨테이너 지정 필요)
kubectl logs -n titanium-prod <pod-name> -c <container-name>

# 실시간 로그 스트리밍
kubectl logs -n titanium-prod <pod-name> -c <container-name> -f

# 최근 100줄 로그
kubectl logs -n titanium-prod <pod-name> -c <container-name> --tail=100

# 타임스탬프 포함
kubectl logs -n titanium-prod <pod-name> -c <container-name> --timestamps
```

**Loki를 통한 중앙 로그 조회**:
1. Grafana 접속 (http://10.0.11.168:30300)
2. Explore 메뉴 선택
3. 데이터소스: Loki 선택
4. LogQL 쿼리 작성:
```logql
# 특정 네임스페이스 로그
{namespace="titanium-prod"}

# 특정 Pod 로그
{namespace="titanium-prod", pod=~"prod-api-gateway.*"}

# 에러 로그 필터링
{namespace="titanium-prod"} |= "error"

# 시간 범위 지정 (Last 1 hour 등)
```

### 3. 데이터베이스 관리

**PostgreSQL 접속**:
```bash
# PostgreSQL Pod 접속
kubectl exec -it -n titanium-prod postgres-0 -c postgres -- psql -U postgres

# 데이터베이스 목록 확인
\l

# 특정 데이터베이스 접속
\c blog_db

# 테이블 목록
\dt

# 쿼리 실행
SELECT * FROM users LIMIT 10;
```

**데이터베이스 백업**:
```bash
# pg_dump를 사용한 백업
kubectl exec -n titanium-prod postgres-0 -c postgres -- \
  pg_dump -U postgres blog_db > backup_$(date +%Y%m%d).sql

# 압축 백업
kubectl exec -n titanium-prod postgres-0 -c postgres -- \
  pg_dump -U postgres blog_db | gzip > backup_$(date +%Y%m%d).sql.gz
```

**데이터베이스 복구**:
```bash
# 백업 파일로부터 복구
cat backup_20251103.sql | kubectl exec -i -n titanium-prod postgres-0 -c postgres -- \
  psql -U postgres blog_db
```

### 4. 스케일링

**수동 스케일링**:
```bash
# Deployment 스케일 조정
kubectl scale deployment prod-api-gateway-deployment \
  -n titanium-prod --replicas=3

# StatefulSet 스케일 조정
kubectl scale statefulset postgres \
  -n titanium-prod --replicas=1
```

**HPA 설정 변경**:
```bash
# HPA 상태 확인
kubectl get hpa -n titanium-prod prod-api-gateway-hpa -o yaml

# HPA 수정
kubectl edit hpa -n titanium-prod prod-api-gateway-hpa

# 또는 파일 수정 후 적용
kubectl apply -f k8s-manifests/overlays/solid-cloud/hpa.yaml
```

---

## 모니터링 및 알림

### Grafana 대시보드

**접속**: http://10.0.11.168:30300

**주요 대시보드**:
1. **Golden Signals Dashboard**:
   - Latency (P95, P99 응답 시간)
   - Traffic (초당 요청 수)
   - Errors (에러율)
   - Saturation (리소스 사용률)

2. **Kubernetes Cluster Dashboard**:
   - Node 상태 및 리소스 사용량
   - Pod 상태
   - PersistentVolume 사용량

**메트릭 확인 방법**:
1. Grafana 로그인 (admin/admin123)
2. Dashboards → Browse
3. 원하는 대시보드 선택
4. 시간 범위 선택 (우측 상단)
5. 변수 선택 (서비스, 네임스페이스 등)

### Prometheus 쿼리

**Prometheus 직접 접속**:
```bash
# Port-forward로 Prometheus 접속
kubectl port-forward -n monitoring svc/prometheus-operated 9090:9090

# 브라우저에서 http://localhost:9090 접속
```

**유용한 PromQL 쿼리**:
```promql
# 서비스별 초당 요청 수
rate(istio_requests_total{namespace="titanium-prod"}[5m])

# P95 응답 시간
histogram_quantile(0.95,
  sum(rate(istio_request_duration_milliseconds_bucket{namespace="titanium-prod"}[5m])) by (le, job)
)

# 에러율
sum(rate(istio_requests_total{namespace="titanium-prod", response_code=~"5.."}[5m]))
/
sum(rate(istio_requests_total{namespace="titanium-prod"}[5m]))

# CPU 사용률
100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)

# 메모리 사용률
(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100
```

### AlertManager

**알림 규칙 확인**:
```bash
# AlertManager 상태
kubectl get pods -n monitoring -l app.kubernetes.io/name=alertmanager

# 활성 알림 확인
kubectl port-forward -n monitoring svc/prometheus-operated 9090:9090
# http://localhost:9090/alerts 접속
```

**알림 규칙 예시**:
- CPU 사용률 90% 이상
- Pod 재시작 5회 이상
- HTTP 5xx 에러율 5% 이상
- 디스크 사용률 80% 이상

---

## 배포 및 롤백

### GitOps 기반 배포 프로세스

**자동 배포 플로우**:
```
Git Push → GitHub Actions CI (빌드/스캔) → Docker Hub Push
→ GitHub Actions CD (매니페스트 업데이트) → Argo CD (자동 배포)
```

**수동 배포 (긴급 시)**:
```bash
# 이미지 태그 변경
cd k8s-manifests/overlays/solid-cloud
kubectl set image deployment/prod-api-gateway-deployment \
  api-gateway=idongju/api-gateway:v1.2.3 \
  -n titanium-prod

# Kustomize 적용
kubectl apply -k k8s-manifests/overlays/solid-cloud
```

### Argo CD를 통한 배포 관리

**Argo CD CLI 설치** (선택):
```bash
# macOS
brew install argocd

# Linux
curl -sSL -o /usr/local/bin/argocd https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64
chmod +x /usr/local/bin/argocd
```

**Argo CD 조작**:
```bash
# Port-forward로 Argo CD 접속
kubectl port-forward -n argocd svc/argocd-server 8080:443

# CLI 로그인
argocd login localhost:8080 --username admin --password <password>

# 애플리케이션 상태 확인
argocd app list
argocd app get <app-name>

# 수동 동기화
argocd app sync <app-name>

# 이전 버전으로 롤백
argocd app rollback <app-name> <revision-id>
```

### 롤백 시나리오

**방법 1: Argo CD UI 롤백**:
1. Argo CD UI 접속
2. 애플리케이션 선택
3. History 탭 이동
4. 이전 버전 선택 → Rollback 클릭

**방법 2: kubectl rollout 롤백**:
```bash
# 롤아웃 히스토리 확인
kubectl rollout history deployment/prod-api-gateway-deployment -n titanium-prod

# 이전 버전으로 롤백
kubectl rollout undo deployment/prod-api-gateway-deployment -n titanium-prod

# 특정 버전으로 롤백
kubectl rollout undo deployment/prod-api-gateway-deployment \
  -n titanium-prod --to-revision=2

# 롤아웃 상태 확인
kubectl rollout status deployment/prod-api-gateway-deployment -n titanium-prod
```

**방법 3: Git 커밋 되돌리기**:
```bash
# Git 히스토리 확인
git log k8s-manifests/overlays/solid-cloud/kustomization.yaml

# 특정 커밋으로 되돌리기
git revert <commit-hash>
git push

# Argo CD가 자동으로 감지하여 롤백
```

---

## 트러블슈팅

### 1. Pod 문제

**Pod가 시작되지 않을 때**:
```bash
# Pod 상태 확인
kubectl get pods -n titanium-prod

# 상세 정보 확인
kubectl describe pod <pod-name> -n titanium-prod

# 이벤트 확인
kubectl get events -n titanium-prod --sort-by='.lastTimestamp'

# 로그 확인
kubectl logs <pod-name> -n titanium-prod -c <container-name> --previous
```

**일반적인 문제 및 해결**:

| 상태 | 원인 | 해결 방법 |
|------|------|----------|
| ImagePullBackOff | 이미지를 가져올 수 없음 | 이미지 태그 확인, Docker Hub 자격증명 확인 |
| CrashLoopBackOff | 애플리케이션이 반복적으로 실패 | 로그 확인, 환경 변수 확인, 리소스 제한 확인 |
| Pending | 스케줄링 불가 | Node 리소스 부족, PVC 바인딩 문제 확인 |
| OOMKilled | 메모리 부족 | 메모리 제한 증가 또는 애플리케이션 최적화 |

### 2. 네트워크 문제

**서비스 간 통신 불가**:
```bash
# 서비스 엔드포인트 확인
kubectl get endpoints -n titanium-prod

# DNS 해석 테스트
kubectl run -it --rm debug --image=nicolaka/netshoot --restart=Never -- nslookup prod-user-service.titanium-prod.svc.cluster.local

# 서비스 연결 테스트
kubectl run -it --rm debug --image=nicolaka/netshoot --restart=Never -- curl http://prod-user-service.titanium-prod.svc.cluster.local:5001/health
```

**Istio 사이드카 문제**:
```bash
# Sidecar 주입 확인
kubectl get pods -n titanium-prod -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.containers[*].name}{"\n"}{end}'

# Istio Proxy 로그 확인
kubectl logs <pod-name> -n titanium-prod -c istio-proxy

# mTLS 상태 확인
istioctl x describe pod <pod-name> -n titanium-prod
```

### 3. 데이터베이스 문제

**PostgreSQL 연결 실패**:
```bash
# PostgreSQL Pod 상태 확인
kubectl get pods -n titanium-prod postgres-0

# PostgreSQL 로그 확인
kubectl logs -n titanium-prod postgres-0 -c postgres

# 연결 테스트
kubectl exec -it -n titanium-prod postgres-0 -c postgres -- psql -U postgres -c "SELECT version();"

# Secret 확인
kubectl get secret postgres-secret -n titanium-prod -o yaml
```

**데이터베이스 성능 문제**:
```sql
-- 활성 연결 확인
SELECT * FROM pg_stat_activity;

-- 느린 쿼리 확인
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;

-- 테이블 크기 확인
SELECT
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### 4. CI/CD 문제

**GitHub Actions 실패**:
1. GitHub Actions 탭에서 실패한 워크플로우 확인
2. 각 단계의 로그 확인
3. 일반적인 원인:
   - Trivy 스캔 실패 (취약점 발견)
   - Docker 빌드 실패 (Dockerfile 오류)
   - Docker Hub 푸시 실패 (자격증명 문제)

**Argo CD 동기화 실패**:
```bash
# Argo CD 애플리케이션 상태 확인
kubectl get applications -n argocd

# 상세 상태 확인
kubectl describe application <app-name> -n argocd

# Argo CD 로그 확인
kubectl logs -n argocd deployment/argocd-server
kubectl logs -n argocd deployment/argocd-application-controller
```

### 5. 모니터링 문제

**Grafana에서 메트릭이 표시되지 않을 때**:
```bash
# Prometheus 타겟 확인
kubectl port-forward -n monitoring svc/prometheus-operated 9090:9090
# http://localhost:9090/targets 접속하여 타겟 상태 확인

# ServiceMonitor 확인
kubectl get servicemonitor -n titanium-prod
kubectl get servicemonitor -n istio-system

# Prometheus Operator 로그 확인
kubectl logs -n monitoring deployment/prometheus-operator
```

**Loki 로그 수집 안 될 때**:
```bash
# Promtail DaemonSet 상태 확인
kubectl get pods -n monitoring -l app.kubernetes.io/name=promtail

# Promtail 로그 확인
kubectl logs -n monitoring -l app.kubernetes.io/name=promtail

# Loki 상태 확인
kubectl logs -n monitoring -l app.kubernetes.io/name=loki
```

---

## 보안 관리

### 1. mTLS 상태 확인

**Istio mTLS 확인**:
```bash
# PeerAuthentication 확인
kubectl get peerauthentication -n titanium-prod

# mTLS 상태 확인 (istioctl 필요)
istioctl x describe service prod-user-service -n titanium-prod

# 트래픽 암호화 확인
kubectl exec -it <pod-name> -n titanium-prod -c istio-proxy -- \
  curl -s http://localhost:15000/config_dump | grep -A 5 tls_mode
```

### 2. Secrets 관리

**Secrets 조회** (민감 정보 포함, 주의):
```bash
# Secret 목록
kubectl get secrets -n titanium-prod

# Secret 내용 확인 (Base64 디코딩)
kubectl get secret postgres-secret -n titanium-prod -o jsonpath='{.data.POSTGRES_PASSWORD}' | base64 -d
```

**Secrets 업데이트**:
```bash
# 새로운 비밀번호 생성
NEW_PASSWORD=$(openssl rand -base64 32)

# Secret 업데이트
kubectl create secret generic postgres-secret \
  --from-literal=POSTGRES_PASSWORD=$NEW_PASSWORD \
  --dry-run=client -o yaml | kubectl apply -f -

# Pod 재시작하여 새 Secret 적용
kubectl rollout restart statefulset/postgres -n titanium-prod
```

### 3. RBAC 확인

**현재 권한 확인**:
```bash
# ServiceAccount 목록
kubectl get serviceaccounts -n titanium-prod

# Role 및 RoleBinding 확인
kubectl get roles,rolebindings -n titanium-prod

# 특정 사용자의 권한 확인
kubectl auth can-i --list --as=system:serviceaccount:titanium-prod:default
```

### 4. NetworkPolicy

**NetworkPolicy 확인**:
```bash
# NetworkPolicy 목록
kubectl get networkpolicies -n titanium-prod

# 상세 정보
kubectl describe networkpolicy <policy-name> -n titanium-prod
```

### 5. 보안 스캔

**Trivy 스캔 (로컬)**:
```bash
# 컨테이너 이미지 스캔
trivy image idongju/api-gateway:latest

# 심각도 HIGH 이상만 표시
trivy image --severity HIGH,CRITICAL idongju/api-gateway:latest

# Kubernetes 매니페스트 스캔
trivy config k8s-manifests/
```

---

## 백업 및 복구

### 1. 데이터베이스 백업

**정기 백업 스크립트**:
```bash
#!/bin/bash
# backup-postgres.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups"
NAMESPACE="titanium-prod"
POD="postgres-0"

# 백업 디렉토리 생성
mkdir -p $BACKUP_DIR

# PostgreSQL 백업
kubectl exec -n $NAMESPACE $POD -c postgres -- \
  pg_dumpall -U postgres | gzip > $BACKUP_DIR/postgres_backup_$DATE.sql.gz

# 7일 이상 된 백업 삭제
find $BACKUP_DIR -name "postgres_backup_*.sql.gz" -mtime +7 -delete

echo "Backup completed: postgres_backup_$DATE.sql.gz"
```

**백업 자동화 (CronJob)**:
```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: postgres-backup
  namespace: titanium-prod
spec:
  schedule: "0 2 * * *"  # 매일 새벽 2시
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: postgres:15
            command:
            - /bin/sh
            - -c
            - pg_dump -h postgres.titanium-prod.svc.cluster.local -U postgres blog_db > /backup/backup_$(date +%Y%m%d).sql
            volumeMounts:
            - name: backup
              mountPath: /backup
          volumes:
          - name: backup
            persistentVolumeClaim:
              claimName: backup-pvc
          restartPolicy: OnFailure
```

### 2. Kubernetes 리소스 백업

**매니페스트 백업**:
```bash
# 전체 리소스 백업
kubectl get all -n titanium-prod -o yaml > titanium-prod-backup.yaml

# ConfigMap 백업
kubectl get configmaps -n titanium-prod -o yaml > configmaps-backup.yaml

# Secrets 백업 (암호화 저장 권장)
kubectl get secrets -n titanium-prod -o yaml > secrets-backup.yaml
```

### 3. 재해 복구 절차

**전체 시스템 복구**:
1. Kubernetes 클러스터 재생성 (Terraform)
2. Namespace 및 기본 리소스 생성
3. Secrets 복원
4. PostgreSQL 복원
5. 애플리케이션 배포 (Argo CD)
6. 모니터링 스택 배포

**PostgreSQL 복구**:
```bash
# 백업 파일 복원
gunzip -c postgres_backup_20251103.sql.gz | \
kubectl exec -i -n titanium-prod postgres-0 -c postgres -- \
  psql -U postgres

# 데이터 확인
kubectl exec -it -n titanium-prod postgres-0 -c postgres -- \
  psql -U postgres -c "SELECT count(*) FROM users;"
```

---

## 정기 점검 체크리스트

### 일일 점검
- [ ] 전체 Pod 상태 확인 (Running 상태인지)
- [ ] Grafana 대시보드에서 주요 메트릭 확인
- [ ] 최근 24시간 알림 확인
- [ ] CI/CD 파이프라인 성공 여부 확인

### 주간 점검
- [ ] 리소스 사용률 트렌드 분석
- [ ] 로그 검토 (에러 패턴 분석)
- [ ] 데이터베이스 백업 확인
- [ ] Trivy 보안 스캔 결과 검토
- [ ] HPA 동작 확인 (필요 시 조정)

### 월간 점검
- [ ] Kubernetes 버전 업데이트 검토
- [ ] Istio 버전 업데이트 검토
- [ ] 사용하지 않는 리소스 정리 (PVC, ConfigMap 등)
- [ ] 재해 복구 절차 테스트
- [ ] 문서 업데이트 (ADR, 운영 가이드 등)

---

## 연락처 및 에스컬레이션

### 지원 체계
- **Level 1**: 운영 담당자 - 일상 운영 및 모니터링
- **Level 2**: DevOps 엔지니어 - 복잡한 문제 해결
- **Level 3**: 개발팀 - 애플리케이션 버그 및 긴급 패치

### 긴급 연락망
- **시스템 장애**: [담당자 연락처]
- **보안 사고**: [보안팀 연락처]
- **인프라 문제**: [인프라팀 연락처]

---

## 참고 문서

- [프로젝트 README](../README.md)
- [시스템 아키텍처](./architecture.md)
- [Week 5 최종 상태 보고서](./guides/week5/week5-final-status-report.md)
- [Istio 구현 가이드](./guides/week4/istio-implementation.md)
- [트러블슈팅 가이드](./guides/week4/istio-troubleshooting.md)

---

**문서 작성자**: 이동주
**최종 수정일**: 2025년 11월 3일

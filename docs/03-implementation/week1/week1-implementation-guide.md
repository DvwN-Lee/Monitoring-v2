# Week 1 구현 가이드

**작성일**: 2025-10-27
**업데이트**: 2025-10-28
**대상**: 클라우드 인프라 구축 실습

---

## 이 문서에 대하여

Week 1에서 구현한 Terraform 기반 Kubernetes 인프라와 PostgreSQL 마이그레이션을 단계별로 실습할 수 있는 가이드입니다.

**학습 목표**:
- Terraform을 사용한 인프라 자동화
- Kustomize로 환경별 설정 관리
- 데이터베이스 마이그레이션 경험

---

## 구현 개요

### 목표
로컬 환경(Minikube + SQLite)에서 클라우드 환경(Solid Cloud + PostgreSQL)으로 전환

### 완료 기준
- [ ] Terraform으로 인프라 배포 성공
- [ ] Kubernetes 클러스터 3+ 노드 Ready
- [ ] PostgreSQL Pod Running 및 데이터 CRUD 테스트
- [ ] 서비스 정상 배포 확인

---

## 프로젝트 구조

```
Monitoring-v2/
├── terraform/
│   ├── modules/              # 재사용 가능한 모듈
│   │   ├── network/          # VPC, Subnet
│   │   ├── kubernetes/       # Cluster, Namespace
│   │   └── database/         # PostgreSQL
│   └── environments/
│       └── solid-cloud/      # 환경별 변수
│
├── k8s-manifests/
│   ├── base/                 # 공통 매니페스트
│   └── overlays/
│       ├── local/            # 로컬 환경 설정
│       └── solid-cloud/      # 클라우드 환경 설정
│
├── scripts/                  # 자동화 스크립트
└── docs/                     # 문서
```

---

## 실습 가이드

### 사전 요구사항

```bash
# 필수 도구 확인
terraform --version    # >= 1.5.0
kubectl version
kustomize version
```

---

### 실습 1: 로컬 환경 테스트

로컬에서 먼저 동작을 확인합니다.

```bash
# 1. Minikube로 환경 전환
./scripts/switch-to-local.sh

# 2. Skaffold로 배포
./scripts/deploy-local.sh

# 3. 서비스 접근 확인
minikube service load-balancer-service --url -n local
```

---

### 실습 2: 클라우드 인프라 구축

#### Step 1: Kubernetes 인증 설정

```bash
# .env.k8s 파일 생성 (Token 기반 인증)
cp .env.k8s.example .env.k8s
vi .env.k8s
```

필수 입력 항목:
- `K8S_API_SERVER`: Kubernetes API 서버 주소
- `K8S_TOKEN`: Service Account Token
- `K8S_CA_CERT`: CA Certificate (Base64)

<details>
<summary>Token 발급 방법 보기</summary>

```bash
# Service Account 생성
kubectl create serviceaccount monitoring-sa -n default

# ClusterRole 바인딩
kubectl create clusterrolebinding monitoring-sa-admin \
  --clusterrole=cluster-admin \
  --serviceaccount=default:monitoring-sa

# Token 생성 (10년 유효)
kubectl create token monitoring-sa --duration=87600h
```
</details>

#### Step 2: Terraform 변수 설정

```bash
cd terraform/environments/solid-cloud

# 변수 파일 생성
cp terraform.tfvars.example terraform.tfvars
vi terraform.tfvars
```

주요 설정:
- `cluster_name`: 클러스터 이름
- `postgres_password`: PostgreSQL 비밀번호
- `kubeconfig_path`: kubeconfig 파일 경로

#### Step 3: 인프라 배포

```bash
# 초기화
terraform init

# 계획 확인
terraform plan

# 배포 실행
terraform apply
```

**예상 소요 시간**: 약 3-5분

#### Step 4: 배포 확인

```bash
# 클러스터 노드 확인
kubectl get nodes

# Namespace 확인
kubectl get namespace

# PostgreSQL 확인
kubectl get pods,svc,pvc -n titanium-prod
```

---

### 실습 3: 애플리케이션 배포

#### Kustomize로 배포

```bash
# 클라우드 환경 적용
kubectl apply -k k8s-manifests/overlays/solid-cloud

# 배포 상태 확인
kubectl get pods -n titanium-prod
kubectl get svc -n titanium-prod
```

---

### 실습 4: PostgreSQL 테스트

```bash
# PostgreSQL Pod 접속
kubectl exec -it postgresql-0 -n titanium-prod -- \
  psql -U postgres -d titanium

# SQL 실행
titanium=# \dt                          # 테이블 목록
titanium=# SELECT * FROM users;         # 데이터 조회
titanium=# \q                           # 종료
```

#### CRUD 테스트

```bash
# 데이터 삽입
kubectl exec postgresql-0 -n titanium-prod -- \
  psql -U postgres -d titanium -c \
  "INSERT INTO users (username, email, password_hash)
   VALUES ('test', 'test@example.com', 'hashed');"

# 데이터 조회
kubectl exec postgresql-0 -n titanium-prod -- \
  psql -U postgres -d titanium -c "SELECT * FROM users;"
```

---

## 테스트 자동화

### 인프라 테스트

```bash
./scripts/test-week1-infrastructure.sh
```

**검증 항목**:
- Terraform 모듈 존재 여부
- Kubernetes 연결 상태
- PostgreSQL Pod Running
- PVC Bound 상태

### 서비스 API 테스트

```bash
./scripts/test-week1-services.sh
```

**검증 항목**:
- Health check 엔드포인트
- User 등록/로그인
- Blog CRUD 작업

---

## 문제 해결

### Q1. PVC가 Pending 상태

**원인**: StorageClass 미설치

**해결**:
```bash
# StorageClass 확인
kubectl get storageclass

# Local Path Provisioner 설치
kubectl apply -f https://raw.githubusercontent.com/rancher/local-path-provisioner/v0.0.28/deploy/local-path-storage.yaml

# 기본 StorageClass 설정
kubectl patch storageclass local-path \
  -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'
```

### Q2. Terraform이 잘못된 클러스터에 배포

**원인**: kubeconfig 경로 미지정

**해결**:
```bash
# terraform.tfvars에 명시
kubeconfig_path = "~/.kube/kube.conf"

# 또는 환경 변수로 설정
export TF_VAR_kubeconfig_path="$KUBECONFIG"
```

### Q3. Kustomize 리소스 중복 에러

**원인**: resources와 generator에 중복 정의

**해결**:
```yaml
# kustomization.yaml
resources:
  - ../../base
  # configmap-patch.yaml 제거

configMapGenerator:
  - name: app-config
    # generator만 사용
```

더 많은 문제 해결 방법은 [트러블슈팅 가이드](./week1-troubleshooting-pvc.md) 참고

---

## 참고 자료

### 관련 문서
- [Week 1 요약](./week1-summary.md)
- [마이그레이션 분석](./week1-migration-analysis.md)
- [트러블슈팅 가이드](./week1-troubleshooting-pvc.md)

### 외부 리소스
- [Terraform 공식 문서](https://www.terraform.io/docs)
- [Kustomize 튜토리얼](https://kubernetes.io/docs/tasks/manage-kubernetes-objects/kustomization/)
- [PostgreSQL on Kubernetes](https://www.postgresql.org/docs/)

---

## 체크리스트

실습 완료 후 확인:

- [ ] Terraform apply 성공
- [ ] Kubernetes 클러스터 정상 동작
- [ ] PostgreSQL Pod Running
- [ ] 데이터베이스 CRUD 테스트 통과
- [ ] 자동화 테스트 스크립트 실행 성공

---

## 다음 단계

Week 1을 완료했다면:

1. **코드 리뷰**: 작성한 Terraform 모듈 검토
2. **문서 작성**: 프로젝트 README 업데이트
3. **Week 2 준비**: GitHub Actions CI/CD 파이프라인 학습
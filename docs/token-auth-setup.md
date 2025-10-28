# Token 기반 Kubernetes 인증 설정 가이드

이 문서는 Solid Cloud 환경에서 kubeconfig 파일 없이 Service Account Token을 사용하여 Kubernetes 클러스터에 접근하는 방법을 설명합니다.

---

## 왜 Token 기반 인증을 사용하나요?

### kubeconfig 방식의 문제점
- kubeconfig 파일을 수동으로 다운로드하고 관리해야 함
- 파일 경로 설정 및 권한 문제 발생 가능
- 인스턴스 환경에서 파일 전송 및 관리가 번거로움

### Token 기반 인증의 장점
- ✅ 환경 변수만으로 간단히 설정 가능
- ✅ `.env.k8s` 파일 하나로 모든 인증 정보 관리
- ✅ CI/CD 파이프라인 및 자동화 스크립트와 잘 통합
- ✅ 인스턴스 환경에서도 쉽게 사용 가능
- ✅ Secret 관리 도구와 연동 용이

---

## 설정 방법

### 1단계: 환경 변수 파일 생성

```bash
# 프로젝트 루트 디렉토리에서 실행
cp .env.k8s.example .env.k8s
```

### 2단계: Kubernetes 정보 수집

#### 2-1. API Server URL 확인

Solid Cloud 관리자 또는 Kubernetes 관리 페이지에서 API Server URL을 확인합니다.

형식: `https://api.k8s.solid.dankook.ac.kr:6443`

#### 2-2. Service Account Token 발급

**방법 1: Kubernetes 1.24 이상 (권장)**

```bash
# 기존 클러스터에 접근 가능한 경우

# Service Account 생성
kubectl create serviceaccount monitoring-sa -n default

# Cluster Admin 권한 부여
kubectl create clusterrolebinding monitoring-sa-admin \
  --clusterrole=cluster-admin \
  --serviceaccount=default:monitoring-sa

# Token 발급 (유효 기간: 10년)
kubectl create token monitoring-sa --duration=87600h
```

**방법 2: Kubernetes 1.24 미만**

```bash
# Service Account 생성
kubectl create serviceaccount monitoring-sa -n default

# Cluster Admin 권한 부여
kubectl create clusterrolebinding monitoring-sa-admin \
  --clusterrole=cluster-admin \
  --serviceaccount=default:monitoring-sa

# Secret 이름 가져오기
TOKEN_SECRET=$(kubectl get serviceaccount monitoring-sa -o jsonpath='{.secrets[0].name}')

# Token 추출
kubectl get secret $TOKEN_SECRET -o jsonpath='{.data.token}' | base64 -d
```

**방법 3: Solid Cloud UI에서 직접 발급**

Solid Cloud 관리 콘솔에서 제공하는 Token 발급 기능을 사용합니다.

#### 2-3. CA Certificate 가져오기

**방법 1: kubectl 사용**

```bash
kubectl config view --raw -o jsonpath='{.clusters[0].cluster.certificate-authority-data}'
```

**방법 2: Secret에서 추출**

```bash
TOKEN_SECRET=$(kubectl get serviceaccount monitoring-sa -o jsonpath='{.secrets[0].name}')
kubectl get secret $TOKEN_SECRET -o jsonpath='{.data.ca\.crt}'
```

**방법 3: TLS 검증 건너뛰기 (개발 환경만)**

CA Certificate를 얻을 수 없는 경우, 개발 환경에서만 TLS 검증을 건너뛸 수 있습니다.

```bash
# .env.k8s 파일에서
K8S_SKIP_TLS_VERIFY=true
```

⚠️ **주의**: 운영 환경에서는 반드시 CA Certificate를 사용하세요!

### 3단계: .env.k8s 파일 편집

```bash
vi .env.k8s
```

**.env.k8s 예시:**
```bash
# Kubernetes API Server URL
K8S_API_SERVER=https://api.k8s.solid.dankook.ac.kr:6443

# Cluster Name (선택사항, 기본값: solid-cloud)
K8S_CLUSTER_NAME=solid-cloud

# Service Account Token
K8S_TOKEN=eyJhbGciOiJSUzI1NiIsImtpZCI6IjRZ...

# CA Certificate (Base64 encoded)
K8S_CA_CERT=LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0t...

# TLS 검증 건너뛰기 (기본값: false)
K8S_SKIP_TLS_VERIFY=false
```

### 4단계: 환경 전환 스크립트 실행

```bash
./scripts/switch-to-cloud.sh
```

스크립트가 자동으로:
1. `.env.k8s` 파일을 읽어 환경 변수 로드
2. kubectl config에 cluster, user, context 생성
3. 생성한 context로 전환
4. 연결 테스트 수행

---

## 인스턴스에서 실행하는 방법

### 시나리오: EC2/VM 인스턴스에서 프로젝트 실행

```bash
# 1. 프로젝트 클론
git clone https://github.com/your-repo/Monitoring-v2.git
cd Monitoring-v2

# 2. .env.k8s 파일 생성
cat > .env.k8s << 'EOF'
K8S_API_SERVER=https://api.k8s.solid.dankook.ac.kr:6443
K8S_CLUSTER_NAME=solid-cloud
K8S_TOKEN=eyJhbGciOiJSUzI1NiIsImtpZCI6IjRZ...
K8S_CA_CERT=LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0t...
K8S_SKIP_TLS_VERIFY=false
EOF

# 3. 환경 전환 (자동으로 kubectl 설정)
./scripts/switch-to-cloud.sh

# 4. 배포 실행
./scripts/deploy-cloud.sh

# 5. 테스트 실행
./scripts/test-week1-infrastructure.sh
```

---

## 트러블슈팅

### 문제 1: "Failed to connect to Solid Cloud"

**원인**: API Server URL이 잘못되었거나 네트워크 접근 불가

**해결**:
```bash
# API Server 접근 테스트
curl -k https://api.k8s.solid.dankook.ac.kr:6443

# .env.k8s에서 K8S_API_SERVER 확인
cat .env.k8s | grep K8S_API_SERVER
```

### 문제 2: "x509: certificate signed by unknown authority"

**원인**: CA Certificate가 잘못되었거나 설정되지 않음

**해결**:
```bash
# Option 1: CA Certificate 다시 가져오기
kubectl config view --raw -o jsonpath='{.clusters[0].cluster.certificate-authority-data}'

# Option 2: 개발 환경에서만 TLS 검증 건너뛰기
echo "K8S_SKIP_TLS_VERIFY=true" >> .env.k8s
```

### 문제 3: "Unauthorized"

**원인**: Token이 만료되었거나 권한이 부족함

**해결**:
```bash
# 새로운 Token 발급
kubectl create token monitoring-sa --duration=87600h

# .env.k8s 파일에서 K8S_TOKEN 업데이트
vi .env.k8s
```

### 문제 4: Token이 Base64 디코딩 에러

**원인**: Token 값이 이미 디코딩된 상태

**해결**:
```bash
# Token은 Base64 디코딩하지 않고 그대로 사용
# K8S_TOKEN에 바로 복사하세요
```

### 문제 5: CA Certificate 디코딩 에러

**원인**: CA Cert가 Base64 인코딩되지 않음

**해결**:
```bash
# kubectl에서 가져온 CA Cert는 이미 Base64 인코딩되어 있음
# 그대로 K8S_CA_CERT에 복사하세요

# 만약 파일로 저장된 CA Cert를 사용하는 경우:
cat ca.crt | base64 -w 0
```

---

## 보안 고려사항

### .env.k8s 파일 보호

```bash
# 파일 권한 제한 (읽기 전용, 소유자만)
chmod 600 .env.k8s

# .gitignore에 추가 (이미 설정됨)
echo ".env.k8s" >> .gitignore
```

### Token 유효 기간 관리

```bash
# Token 유효 기간 확인 (JWT 디코딩)
echo $K8S_TOKEN | cut -d. -f2 | base64 -d 2>/dev/null | jq .exp

# 만료 전 새로운 Token 발급
kubectl create token monitoring-sa --duration=87600h
```

### 권한 최소화

```bash
# Cluster Admin 대신 필요한 권한만 부여
kubectl create role monitoring-role \
  --verb=get,list,watch \
  --resource=pods,services,deployments

kubectl create rolebinding monitoring-binding \
  --role=monitoring-role \
  --serviceaccount=default:monitoring-sa \
  --namespace=titanium-prod
```

---

## FAQ

### Q1: kubeconfig 파일과 Token 기반 인증을 함께 사용할 수 있나요?

A: 네, 가능합니다. `switch-to-cloud.sh` 스크립트는 kubectl config에 새로운 context를 추가하므로, 기존 kubeconfig 설정과 공존할 수 있습니다.

### Q2: Token은 얼마나 자주 갱신해야 하나요?

A: `kubectl create token`으로 발급한 Token은 `--duration` 옵션으로 유효 기간을 설정할 수 있습니다. 기본값은 1시간이며, 최대 87600시간(10년)까지 설정 가능합니다.

### Q3: 여러 클러스터를 관리하려면 어떻게 하나요?

A: 각 클러스터별로 다른 `.env.k8s` 파일을 만들고 (예: `.env.k8s.dev`, `.env.k8s.prod`), `switch-to-cloud.sh` 스크립트를 실행할 때 파일을 지정할 수 있도록 수정하면 됩니다.

### Q4: CI/CD 파이프라인에서 어떻게 사용하나요?

A: GitHub Actions, GitLab CI 등에서 환경 변수로 `K8S_API_SERVER`, `K8S_TOKEN`, `K8S_CA_CERT`를 설정하고, `switch-to-cloud.sh` 스크립트를 실행하면 됩니다.

```yaml
# GitHub Actions 예시
env:
  K8S_API_SERVER: ${{ secrets.K8S_API_SERVER }}
  K8S_TOKEN: ${{ secrets.K8S_TOKEN }}
  K8S_CA_CERT: ${{ secrets.K8S_CA_CERT }}

steps:
  - name: Setup Kubernetes
    run: ./scripts/switch-to-cloud.sh
```

---

## 참고 자료

- [Kubernetes Authentication](https://kubernetes.io/docs/reference/access-authn-authz/authentication/)
- [Service Account Tokens](https://kubernetes.io/docs/tasks/configure-pod-container/configure-service-account/)
- [kubectl Configuration](https://kubernetes.io/docs/concepts/configuration/organize-cluster-access-kubeconfig/)

---

**작성자**: Claude AI
**최종 수정**: 2025-10-27

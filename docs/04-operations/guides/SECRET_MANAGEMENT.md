---
version: 1.0
last_updated: 2025-11-15
author: Dongju Lee
---

# Secret 관리 가이드

최종 수정일: 2025-11-05

## 개요

이 프로젝트는 보안을 위해 민감한 정보(데이터베이스 비밀번호, JWT Secret, API 키 등)를 Git 저장소에 커밋하지 않습니다. 이 문서는 개발 환경과 프로덕션 환경에서 Secret을 안전하게 관리하는 방법을 설명합니다.

## 보안 원칙

1. Secret은 절대 Git 저장소에 커밋하지 않습니다
2. 환경별로 다른 Secret 값을 사용합니다
3. Secret 값은 암호화되어 저장되어야 합니다
4. Secret 접근 권한은 최소 권한 원칙을 따릅니다

## 방법 1: 수동 Secret 관리 (개발/테스트 환경)

### 로컬 개발 환경 (Minikube)

1. Secret YAML 파일 생성:

```yaml
# k8s-manifests/overlays/local/secrets.yaml (Git에 커밋하지 않음)
apiVersion: v1
kind: Secret
metadata:
  name: prod-app-secrets
  namespace: titanium-prod
type: Opaque
stringData:
  POSTGRES_USER: postgres
  POSTGRES_PASSWORD: your-local-password
  JWT_SECRET_KEY: your-local-jwt-secret
  INTERNAL_API_SECRET: your-local-api-secret
```

2. Secret 적용:

```bash
kubectl apply -f k8s-manifests/overlays/local/secrets.yaml
```

### Solid Cloud 환경

1. Secret 파일 생성 (로컬에만 보관):

```yaml
# secrets-solid-cloud.yaml (Git에 커밋하지 않음)
apiVersion: v1
kind: Secret
metadata:
  name: prod-app-secrets
  namespace: titanium-prod
type: Opaque
stringData:
  POSTGRES_USER: postgres
  POSTGRES_PASSWORD: <SOLID_CLOUD_POSTGRES_PASSWORD>
  JWT_SECRET_KEY: <SOLID_CLOUD_JWT_SECRET>
  INTERNAL_API_SECRET: <SOLID_CLOUD_API_SECRET>
```

2. Solid Cloud 클러스터 컨텍스트로 전환:

```bash
kubectl config use-context solid-cloud
```

3. Secret 적용:

```bash
kubectl apply -f secrets-solid-cloud.yaml
```

4. Secret 파일 삭제 또는 안전한 위치로 이동:

```bash
rm secrets-solid-cloud.yaml
# 또는
mv secrets-solid-cloud.yaml ~/.kube/secrets/
```

### Secret 값 생성

강력한 Secret 값 생성 방법:

```bash
# 랜덤 JWT Secret 생성 (32바이트)
openssl rand -base64 32

# 랜덤 API Secret 생성 (32바이트)
openssl rand -base64 32

# 강력한 비밀번호 생성
openssl rand -base64 24
```

## 방법 2: External Secrets Operator (프로덕션 환경 권장)

External Secrets Operator(ESO)는 AWS Secrets Manager, Google Secret Manager, Azure Key Vault 등 외부 Secret 저장소와 Kubernetes를 연동합니다.

### 장점

- 중앙 집중식 Secret 관리
- Secret 회전(Rotation) 자동화
- 감사 로그 및 접근 제어
- 클라우드 네이티브 보안 Best Practice

### 설치 및 설정

1. External Secrets Operator 설치:

```bash
helm repo add external-secrets https://charts.external-secrets.io
helm repo update

helm install external-secrets \
  external-secrets/external-secrets \
  -n external-secrets \
  --create-namespace
```

2. AWS Secrets Manager에 Secret 저장:

```bash
aws secretsmanager create-secret \
  --name titanium/postgres \
  --description "PostgreSQL credentials for Titanium project" \
  --secret-string '{"username":"postgres","password":"<SECURE_PASSWORD>"}'

aws secretsmanager create-secret \
  --name titanium/jwt \
  --description "JWT secret key for Titanium project" \
  --secret-string '{"secretKey":"<JWT_SECRET>"}'
```

3. SecretStore 리소스 생성:

```yaml
# k8s-manifests/base/secret-store.yaml
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: aws-secret-store
  namespace: titanium-prod
spec:
  provider:
    aws:
      service: SecretsManager
      region: ap-northeast-2
      auth:
        jwt:
          serviceAccountRef:
            name: external-secrets-sa
```

4. ExternalSecret 리소스 생성:

```yaml
# k8s-manifests/base/external-secret.yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: app-secrets
  namespace: titanium-prod
spec:
  secretStoreRef:
    name: aws-secret-store
    kind: SecretStore
  target:
    name: prod-app-secrets
    creationPolicy: Owner
  data:
  - secretKey: POSTGRES_USER
    remoteRef:
      key: titanium/postgres
      property: username
  - secretKey: POSTGRES_PASSWORD
    remoteRef:
      key: titanium/postgres
      property: password
  - secretKey: JWT_SECRET_KEY
    remoteRef:
      key: titanium/jwt
      property: secretKey
```

5. 적용:

```bash
kubectl apply -f k8s-manifests/base/secret-store.yaml
kubectl apply -f k8s-manifests/base/external-secret.yaml
```

6. Secret 생성 확인:

```bash
kubectl get secret prod-app-secrets -n titanium-prod
kubectl describe externalsecret app-secrets -n titanium-prod
```

## 방법 3: Sealed Secrets (GitOps 친화적)

Sealed Secrets는 Secret을 암호화하여 Git에 안전하게 저장할 수 있게 해줍니다.

### 설치

```bash
# Controller 설치
kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.24.0/controller.yaml

# CLI 설치 (macOS)
brew install kubeseal
```

### 사용 방법

1. 일반 Secret 생성:

```bash
kubectl create secret generic prod-app-secrets \
  --from-literal=POSTGRES_PASSWORD=mypassword \
  --from-literal=JWT_SECRET_KEY=mysecret \
  --dry-run=client \
  -o yaml > secret.yaml
```

2. SealedSecret으로 변환:

```bash
kubeseal -f secret.yaml -w sealed-secret.yaml
```

3. Git에 커밋:

```bash
git add sealed-secret.yaml
git commit -m "feat: Add sealed secrets"
```

4. 클러스터에 적용:

```bash
kubectl apply -f sealed-secret.yaml
```

Sealed Secret Controller가 자동으로 복호화하여 일반 Secret을 생성합니다.

## Secret 사용 방법

애플리케이션 Deployment에서 Secret 사용:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: user-service
spec:
  template:
    spec:
      containers:
      - name: user-service
        image: dongju101/user-service:latest
        env:
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: prod-app-secrets
              key: POSTGRES_PASSWORD
        - name: JWT_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: prod-app-secrets
              key: JWT_SECRET_KEY
```

## 환경별 권장 방법

| 환경 | 권장 방법 | 이유 |
|------|----------|------|
| 로컬 개발 | 수동 Secret 관리 | 간단하고 빠름 |
| CI/CD | GitHub Secrets | GitHub Actions와 통합 용이 |
| 테스트/스테이징 | Sealed Secrets | GitOps 워크플로우와 호환 |
| 프로덕션 | External Secrets Operator | 엔터프라이즈급 보안 및 관리 |

## .gitignore 설정

다음 파일들이 Git에 커밋되지 않도록 `.gitignore`에 추가되어 있는지 확인하세요:

```gitignore
# Secrets
**/secrets.yaml
**/secrets-*.yaml
secret.yaml
secrets/

# Terraform state (may contain secrets)
*.tfstate
*.tfstate.*

# Environment files
.env
.env.local
.env.*.local
```

## 보안 체크리스트

- [ ] Secret이 Git 히스토리에 없는지 확인
- [ ] 프로덕션 환경의 Secret은 강력한 값 사용
- [ ] Secret 접근 권한은 최소 권한으로 설정
- [ ] Secret 회전 계획 수립
- [ ] Secret 변경 시 관련 서비스 재시작
- [ ] Secret 관련 감사 로그 활성화

## 문제 해결

### Secret이 적용되지 않을 때

```bash
# Secret 존재 확인
kubectl get secret prod-app-secrets -n titanium-prod

# Secret 내용 확인 (base64 디코딩)
kubectl get secret prod-app-secrets -n titanium-prod -o jsonpath='{.data.POSTGRES_PASSWORD}' | base64 -d

# Pod에서 환경 변수 확인
kubectl exec -it <pod-name> -n titanium-prod -- env | grep POSTGRES
```

### ExternalSecret 동기화 실패

```bash
# ExternalSecret 상태 확인
kubectl describe externalsecret app-secrets -n titanium-prod

# ESO Controller 로그 확인
kubectl logs -n external-secrets -l app.kubernetes.io/name=external-secrets
```

## 참고 자료

- [Kubernetes Secrets 공식 문서](https://kubernetes.io/docs/concepts/configuration/secret/)
- [External Secrets Operator](https://external-secrets.io/)
- [Sealed Secrets](https://github.com/bitnami-labs/sealed-secrets)
- [AWS Secrets Manager](https://aws.amazon.com/secrets-manager/)
- [Google Secret Manager](https://cloud.google.com/secret-manager)

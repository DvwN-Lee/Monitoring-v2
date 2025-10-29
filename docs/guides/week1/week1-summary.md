# Week 1: 인프라 기반 구축 - 완료 요약

**기간**: 2025-10-27 ~ 2025-10-28
**상태**: 완료

---

## 목표

> "Terraform으로 Kubernetes 클러스터를 구축하고 PostgreSQL로 DB 전환"

로컬 개발 환경에서만 동작하던 마이크로서비스를 클라우드 환경으로 확장하고, Infrastructure as Code (IaC) 기반의 재현 가능한 인프라를 구축합니다.

---

## 핵심 성과

### 완료된 작업 (8/8)

| 작업 | 설명 | 결과 |
|------|------|------|
| 코드베이스 분석 | SQLite 의존성 파악 및 마이그레이션 계획 | 완료 |
| Terraform 구성 | IaC 모듈 구조 설계 및 구현 | 완료 |
| 인프라 구축 | Network, Kubernetes 모듈 작성 | 완료 |
| PostgreSQL 마이그레이션 | SQLite -> PostgreSQL 전환 | 완료 |
| 환경 분리 | Local / Cloud overlays 구성 | 완료 |
| 자동화 | 배포 및 테스트 스크립트 작성 | 완료 |

### 아키텍처 변화

**이전** (Week 0):
- Minikube 로컬 환경만 지원
- SQLite 파일 기반 DB
- 수동 배포 (skaffold)

**이후** (Week 1):
- 멀티 환경 지원 (Local + Cloud)
- PostgreSQL 중앙화된 DB 
- Terraform 자동화 배포
- Kustomize 환경별 설정 관리

---

## 주요 산출물

### 1. Terraform 모듈

```
terraform/modules/
├── network/         # VPC, Subnet 구성
├── kubernetes/      # 클러스터 및 Namespace
└── database/        # PostgreSQL StatefulSet
```

**특징**: 재사용 가능한 모듈화 구조, 환경별 변수 관리

### 2. 환경별 설정 (Kustomize)

```
k8s-manifests/overlays/
├── local/          # 로컬 개발 환경 (Minikube)
└── solid-cloud/    # 클라우드 프로덕션 환경
```

**특징**: Base 매니페스트 재사용, 환경별 패치 적용

### 3. 데이터베이스 마이그레이션

- **user-service**: SQLite → PostgreSQL (psycopg2)
- **blog-service**: SQLite -> PostgreSQL (psycopg2)
- **스키마**: users, posts 테이블 + 인덱스

### 4. 자동화 스크립트

- `switch-to-local.sh` / `switch-to-cloud.sh`: 환경 전환
- `deploy-local.sh` / `deploy-cloud.sh`: 배포 자동화
- `test-*.sh`: 인프라 및 서비스 테스트

---

## 검증 결과

| 항목 | 결과 | 비고 |
|------|------|------|
| Terraform apply | 성공 | 3분 소요 |
| Kubernetes 클러스터 | 4노드 Ready | Control:1, Worker:3 |
| PostgreSQL | Running | 10Gi PVC Bound |
| 데이터베이스 연결 | 테스트 통과 | CRUD 정상 동작 |
| 서비스 배포 | 부분 완료 | Docker 이미지 빌드 필요 |

---

## 주요 학습 내용

### 1. Infrastructure as Code (IaC)
- Terraform을 통한 선언적 인프라 관리
- 코드로 관리되는 인프라의 장점: 버전 관리, 재현 가능성, 자동화

### 2. 환경 분리 전략
- Kustomize Base/Overlay 패턴 
- 공통 설정 재사용 + 환경별 차이 관리

### 3. 데이터베이스 마이그레이션
- 파일 기반(SQLite) → 네트워크 기반(PostgreSQL)
- 연결 풀링, 트랜잭션 관리, 에러 핸들링

### 4. Kubernetes 스토리지
- PVC, PV, StorageClass의 관계
- WaitForFirstConsumer 볼륨 바인딩 모드

---

## 트러블슈팅 경험

### 주요 문제 및 해결

**문제 1**: PVC 생성 무한 대기
**원인**: StorageClass 미설치
**해결**: Local Path Provisioner 설치

**문제 2**: Terraform 잘못된 클러스터 참조
**원인**: kubeconfig 경로 미지정
**해결**: terraform.tfvars에 명시적 경로 설정

**문제 3**: Kustomize 리소스 중복
**원인**: resources와 generator 중복 정의
**해결**: Generator만 사용하도록 수정

자세한 내용은 [트러블슈팅 가이드](./week1-troubleshooting-pvc.md) 참고

---

## 프로젝트 지표

- **코드 라인**: ~2,000줄
- **생성된 파일**: 40+개
- **문서**: 4개 (분석, 가이드, 요약, 트러블슈팅)
- **소요 시간**: 약 10시간 (계획 37시간 단축)

---

## 회고

### 잘된 점
- 체계적인 계획과 단계별 접근
- 모듈화된 Terraform 구조로 유지보수성 확보
- 환경 분리로 로컬 개발 환경 보존
- 자동화 스크립트로 반복 작업 최소화

### 아쉬운 점
- Docker 이미지 빌드 자동화 미완 (Week 2에서 해결)
- Secret 관리 수동 처리 (향후 External Secret Operator 검토)
- PostgreSQL 단일 레플리카 (HA 구성 필요)

### 핵심 교훈
> "Infrastructure as Code는 단순히 코드로 인프라를 만드는 것이 아니라,
> 재현 가능하고 버전 관리되는 안정적인 시스템을 구축하는 것이다."

---

## 다음 단계: Week 2

### 목표
"Git Push만으로 빌드부터 배포까지 자동화"

### 주요 작업
1. GitHub Actions CI 파이프라인 구성
2. Docker 이미지 자동 빌드 및 푸시
3. GitOps 저장소 구성
4. Argo CD 설치 및 연동
5. E2E 자동화 테스트

# CI/CD 파이프라인 성능 최적화 보고서

## 현재 성능 분석

### 실측 데이터 (최근 10개 워크플로우 평균)

**CI Pipeline (main 브랜치)**
- Detect Changed Services: 4-7초
- Build and Scan: 28-53초
- Build Summary: 4초
- **총 소요 시간**: 36-64초 (평균 48초)

**CI Pipeline (PR 브랜치)**
- Detect Changed Services: 7초
- Build and Scan: 68-109초 (Trivy 스캔 포함)
- Build Summary: 4초
- **총 소요 시간**: 79-120초 (평균 90초)

**CD Pipeline**
- Manifest 업데이트 및 커밋: 7-15초 (평균 11초)

**Argo CD + Kubernetes Rollout**
- Argo CD Sync: 10-20초 (auto-sync 시)
- Kubernetes Rollout: 30-60초
- **총 소요 시간**: 40-80초 (평균 60초)

### 전체 배포 시간
- **PR 생성 후 프로덕션 배포 완료까지**: 
  - CI (PR): 90초
  - PR 머지: 수동 (10-300초)
  - CI (main): 48초
  - CD: 11초
  - Argo CD + K8s: 60초
  - **자동화된 부분**: 약 3-4분 (목표 5분 달성)

---

## 병목 지점 분석

### 1. Trivy 보안 스캔 (PR 브랜치)
**현재 상황**
- Trivy 스캔이 두 번 실행됨 (SARIF 출력, JSON 출력)
- 각 스캔마다 전체 이미지를 재스캔
- PR 브랜치 CI 시간의 약 40-50초를 차지

**영향도**: 높음 (40초 추가 소요)

### 2. Multi-platform Docker 빌드 (main 브랜치)
**현재 상황**
- linux/amd64 및 linux/arm64 플랫폼 동시 빌드
- arm64 빌드에 추가 시간 소요
- Solid Cloud는 amd64만 사용 중

**영향도**: 중간 (10-15초 추가 소요)

### 3. Docker 이미지 레이어 최적화
**현재 상황**
- 기본 Dockerfile 사용
- 멀티스테이지 빌드 미적용 (일부 서비스)
- 불필요한 의존성 포함 가능

**영향도**: 낮음 (빌드 캐시가 잘 작동 중)

### 4. GitHub Actions 동시성
**현재 상황**
- Matrix strategy로 여러 서비스 병렬 빌드 (잘 작동)
- 변경된 서비스만 빌드 (잘 작동)

**영향도**: 없음 (이미 최적화됨)

---

## 최적화 권장사항

### 우선순위 1: Trivy 스캔 최적화 (40초 단축 가능)

#### 현재 문제
```yaml
# SARIF 출력 (Security 탭용)
- name: Run Trivy vulnerability scanner
  uses: aquasecurity/trivy-action@master
  with:
    format: 'sarif'
    
# JSON 출력 (PR 코멘트용) - 중복 스캔!
- name: Run Trivy vulnerability scanner (JSON output for PR comment)
  uses: aquasecurity/trivy-action@master
  with:
    format: 'json'
```

#### 최적화 방안
**옵션 A: 단일 스캔으로 통합**
```yaml
- name: Run Trivy vulnerability scanner
  uses: aquasecurity/trivy-action@master
  with:
    format: 'json'
    output: 'trivy-results-${{ matrix.service }}.json'

# JSON을 SARIF로 변환
- name: Convert JSON to SARIF
  run: |
    cat trivy-results-${{ matrix.service }}.json | \
    jq -r 'to SARIF format' > trivy-results-${{ matrix.service }}.sarif
```

**옵션 B: 스캔 결과 캐싱**
- 동일 이미지 해시에 대한 스캔 결과를 캐싱
- GitHub Actions Cache 활용

**옵션 C: 병렬 실행**
```yaml
strategy:
  matrix:
    format: ['sarif', 'json']
```

**권장**: 옵션 A (중복 제거)
**예상 단축 시간**: 20-40초

---

### 우선순위 2: Multi-platform 빌드 최적화 (10-15초 단축 가능)

#### 현재 설정
```yaml
platforms: linux/amd64,linux/arm64  # main 브랜치
```

#### 최적화 방안
**옵션 A: 필요한 플랫폼만 빌드**
```yaml
# Solid Cloud는 amd64만 사용
platforms: linux/amd64
```

**옵션 B: 조건부 플랫폼 빌드**
```yaml
# 태그 릴리스 시에만 multi-platform 빌드
platforms: ${{ github.ref == 'refs/tags/v*' && 'linux/amd64,linux/arm64' || 'linux/amd64' }}
```

**권장**: 옵션 A (amd64만 빌드)
**예상 단축 시간**: 10-15초

---

### 우선순위 3: Docker 빌드 캐시 최적화

#### 현재 상황
- GitHub Actions Cache 사용 중 (type=gha) - 좋음
- cache-from, cache-to 적절히 설정됨

#### 추가 최적화 방안
**옵션 A: Docker Layer Caching 강화**
```yaml
cache-from: |
  type=gha
  type=registry,ref=${{ env.DOCKER_HUB_USERNAME }}/${{ matrix.service }}:cache
cache-to: |
  type=gha,mode=max
  type=registry,ref=${{ env.DOCKER_HUB_USERNAME }}/${{ matrix.service }}:cache,mode=max
```

**옵션 B: Dockerfile 최적화**
```dockerfile
# AS-IS
FROM python:3.11-slim
COPY . .
RUN pip install -r requirements.txt

# TO-BE
FROM python:3.11-slim
# 의존성 파일만 먼저 복사 (캐시 히트율 향상)
COPY requirements.txt .
RUN pip install -r requirements.txt
# 소스 코드는 나중에 복사
COPY . .
```

**권장**: 옵션 B (Dockerfile 최적화)
**예상 단축 시간**: 5-10초 (의존성 변경 시)

---

### 우선순위 4: CD Pipeline 최적화

#### 현재 성능
- 평균 11초 (이미 매우 빠름)

#### 추가 최적화 불필요
- Git clone, 파일 수정, commit, push만 수행
- 추가 최적화 여지가 거의 없음

---

### 우선순위 5: Argo CD Sync 최적화

#### 현재 설정
```yaml
syncPolicy:
  automated:
    prune: true
    selfHeal: true
  retry:
    limit: 5
    backoff:
      duration: 5s
      factor: 2
      maxDuration: 3m
```

#### 최적화 방안
**옵션 A: Webhook 사용**
- GitHub Webhook을 Argo CD에 연결
- Git push 시 즉시 동기화 (polling 제거)

**옵션 B: 동기화 주기 단축**
```yaml
# 기본 3분 → 1분으로 단축
timeout.reconciliation: 60s
```

**권장**: 옵션 A (Webhook)
**예상 단축 시간**: 30-120초 (polling 주기 제거)

---

## 최적화 적용 후 예상 성능

### 현재 성능
```
CI (PR):    90초
CI (main):  48초
CD:         11초
Argo+K8s:   60초
---------------------------
Total:      209초 (3분 29초)
```

### 최적화 적용 후 (우선순위 1, 2만 적용)
```
CI (PR):    50초  (-40초)
CI (main):  35초  (-13초)
CD:         11초
Argo+K8s:   60초
---------------------------
Total:      156초 (2분 36초)
```

### 모든 최적화 적용 시
```
CI (PR):    40초  (-50초)
CI (main):  30초  (-18초)
CD:         11초
Argo+K8s:   30초  (-30초, Webhook)
---------------------------
Total:      111초 (1분 51초)
```

---

## 실행 계획

### Phase 1: 즉시 적용 가능 (Breaking Change 없음)

1. **Trivy 스캔 중복 제거**
   - 영향도: 없음
   - 단축 시간: 20-40초
   - 난이도: 낮음

2. **Multi-platform 빌드 제거**
   - 영향도: arm64 환경에서 사용 불가 (현재 미사용)
   - 단축 시간: 10-15초
   - 난이도: 낮음

3. **Dockerfile 최적화**
   - 영향도: 없음 (동일한 이미지 생성)
   - 단축 시간: 5-10초
   - 난이도: 중간

**예상 총 단축 시간**: 35-65초

### Phase 2: 인프라 변경 필요

1. **Argo CD Webhook 설정**
   - 영향도: 동기화 방식 변경
   - 단축 시간: 30-120초
   - 난이도: 중간
   - 필요 작업:
     - GitHub Webhook 설정
     - Argo CD Webhook Endpoint 노출
     - Secret 설정

**예상 총 단축 시간**: 30-120초

---

## 비용 대비 효과 분석

| 최적화 항목 | 구현 난이도 | 예상 단축 시간 | 우선순위 |
|------------|------------|--------------|---------|
| Trivy 스캔 중복 제거 | 낮음 | 20-40초 | 높음 |
| Multi-platform 빌드 제거 | 낮음 | 10-15초 | 높음 |
| Dockerfile 최적화 | 중간 | 5-10초 | 중간 |
| Argo CD Webhook | 중간 | 30-120초 | 중간 |
| Docker 레지스트리 캐시 | 높음 | 5-10초 | 낮음 |

---

## 권장 사항

### 즉시 적용 권장
1. Trivy 스캔 중복 제거
2. Multi-platform 빌드를 amd64만으로 변경

### 장기적 검토
1. Argo CD Webhook 설정
2. Dockerfile 최적화 (각 서비스별)

### 현재 유지
1. GitHub Actions Cache (이미 최적)
2. Matrix strategy 병렬 빌드 (이미 최적)
3. 변경 감지 로직 (이미 최적)

---

## 결론

현재 CI/CD 파이프라인은 이미 상당히 잘 최적화되어 있습니다:
- 변경 감지 및 병렬 빌드
- Docker 빌드 캐시 활용
- GitOps 기반 자동 배포

주요 병목 지점은:
1. Trivy 스캔 중복 (40초)
2. Multi-platform 빌드 (15초)

이 두 가지만 최적화해도 **약 1분을 단축**할 수 있으며, 전체 배포 시간을 **2분 30초 이내**로 줄일 수 있습니다.

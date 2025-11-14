# 성능 개선 계획서

## 1. 개요

Grafana Golden Signals 대시보드 테스트 결과 다음 두 가지 주요 성능 이슈가 발견되었습니다:
- 높은 4xx 에러율: 26.4%
- 높은 P99 레이턴시: 3.71초

본 문서는 상세 분석 결과를 바탕으로 각 이슈의 근본 원인과 해결 방안을 제시합니다.

## 2. 이슈 분석

### 2.1. 높은 4xx 에러율 (26.4%)

#### 근본 원인
Load generator가 `/api/register` 엔드포인트를 매초 호출하면서 중복된 사용자 등록을 시도하고 있습니다.

**증거**:
```bash
# load-generator 로그 샘플
[2025-11-13 02:44:31] /api/register (user1763001870) -> HTTP 400
[2025-11-13 02:44:32] /api/register (user1763001872) -> HTTP 400
[2025-11-13 02:44:34] /api/register (user1763001873) -> HTTP 400
```

**현재 설정**:
- Deployment: load-generator (titanium-prod namespace)
- Replicas: 5
- 호출 간격: 1초
- 엔드포인트: `/blog/`, `/health`, `/blog/1`, `/api/register` (병렬 실행)

#### 해결 방안

##### 방안 1: load-generator 스크립트 개선 (우선순위: 높음)

현재 운영 중인 load-generator는 파일 시스템의 설정과 다릅니다.

**목표 설정**:
```yaml
# k8s-manifests/overlays/solid-cloud/load-generator.yaml
# - 중복 등록 제거
# - 더 현실적인 트래픽 패턴 구현
```

**개선 방향**:
1. `/api/register` 호출을 제거하거나 빈도를 대폭 감소
2. 대신 인증된 사용자로 `/api/login` 테스트
3. 다양한 엔드포인트로 트래픽 분산

##### 방안 2: Rate Limiting 구현 (우선순위: 중간)

Istio Rate Limiting을 통해 과도한 등록 시도 차단:

```yaml
apiVersion: networking.istio.io/v1beta1
kind: EnvoyFilter
metadata:
  name: register-rate-limit
  namespace: titanium-prod
spec:
  workloadSelector:
    labels:
      app: prod-api-gateway
  configPatches:
  - applyTo: HTTP_ROUTE
    match:
      context: SIDECAR_INBOUND
      routeConfiguration:
        vhost:
          route:
            name: "/api/register"
    patch:
      operation: MERGE
      value:
        route:
          rateLimits:
          - actions:
            - requestHeaders:
                headerName: ":path"
                descriptorKey: "path"
```

#### 예상 효과
- 4xx 에러율: 26.4% → **1% 미만**
- 실제 시스템 장애를 나타내는 신뢰성 있는 메트릭 확보

### 2.2. 높은 P99 레이턴시 (3.71초)

#### 근본 원인
user-service에서 PBKDF2 알고리즘의 반복 횟수가 100,000회로 설정되어 있어, 고부하 상황에서 CPU 리소스를 과도하게 소모합니다.

**증거**:
```python
# user-service/database_service.py:99
password_hash = generate_password_hash(password, method='pbkdf2:sha256:100000')
```

**문제점**:
1. 100,000회 반복은 보안상 충분하지만, 높은 부하에서 병목 발생
2. auth-service가 user-service의 응답을 기다리므로 전체 레이턴시에 직접 영향
3. CPU 사용률은 낮게 보여도(1~8%), 순간적인 피크로 인한 스로틀링 가능

#### 해결 방안

##### 방안 1: PBKDF2 반복 횟수 최적화 (우선순위: 높음, 단기)

**현재**: 100,000회
**제안**: 60,000회 (보안과 성능의 균형)

```python
# user-service/database_service.py
password_hash = generate_password_hash(password, method='pbkdf2:sha256:60000')
```

**근거**:
- NIST SP 800-132 최소 권장: 10,000회
- OWASP 권장: 310,000회 (2023 기준)
- 60,000회는 보안과 성능의 적절한 균형점

##### 방안 2: Argon2로 알고리즘 전환 (우선순위: 높음, 장기)

**목표 설정**:
```python
# user-service/database_service.py
from argon2 import PasswordHasher
ph = PasswordHasher(
    time_cost=2,        # 반복 횟수
    memory_cost=65536,  # 64MB 메모리 사용
    parallelism=4,      # 병렬 스레드 수
    hash_len=32,        # 해시 길이 (bytes)
    salt_len=16         # 솔트 길이 (bytes)
)

# 해싱
password_hash = ph.hash(password)

# 검증
try:
    ph.verify(stored_hash, password)
    verified = True
except:
    verified = False
```

**장점**:
1. GPU를 사용한 크래킹에 더 강한 저항성 (메모리 집약적)
2. 동일한 보안 수준에서 더 나은 성능
3. Password Hashing Competition 2015 우승 알고리즘

**의존성 추가**:
```txt
# user-service/requirements.txt
argon2-cffi==23.1.0
```

##### 방안 3: CPU 리소스 증설 (우선순위: 중간)

현재 CPU limit 확인 및 조정:

```yaml
# k8s-manifests/base/user-service-deployment.yaml
resources:
  requests:
    cpu: "100m"  # 현재 값 확인 필요
    memory: "128Mi"
  limits:
    cpu: "500m"  # 증설 고려 (예: 500m → 1000m)
    memory: "256Mi"
```

##### 방안 4: 캐싱 전략 도입 (우선순위: 낮음, 장기)

인증 결과를 Redis에 캐싱하여 반복적인 PBKDF2 연산 감소:

```python
# user-service/auth_cache.py (신규 파일)
import redis
import json
from datetime import timedelta

class AuthCache:
    def __init__(self):
        self.redis = redis.Redis(
            host='prod-redis-service',
            port=6379,
            decode_responses=True
        )
        self.cache_ttl = timedelta(minutes=15)

    async def cache_auth_result(self, username: str, is_valid: bool):
        key = f"auth:{username}"
        self.redis.setex(key, self.cache_ttl, json.dumps({"valid": is_valid}))

    async def get_cached_auth(self, username: str) -> Optional[bool]:
        key = f"auth:{username}"
        cached = self.redis.get(key)
        if cached:
            return json.loads(cached)["valid"]
        return None
```

#### 예상 효과

| 개선 방안 | P99 레이턴시 예상 | CPU 사용률 | 구현 난이도 |
|---|---|---|---|
| PBKDF2 60,000회 | 2.2초 (-40%) | 유지 | 낮음 |
| Argon2 전환 | 0.8초 (-78%) | 유지 또는 감소 | 중간 |
| CPU 증설 | 2.5초 (-33%) | 증가 | 낮음 |
| 캐싱 도입 | 0.1초 (-97%, 캐시 히트) | 감소 | 높음 |

**권장 조합**:
1. 단기(1주): PBKDF2 60,000회 + CPU 증설
2. 중기(1개월): Argon2 전환
3. 장기(3개월): 캐싱 전략 추가

## 3. 구현 우선순위

### Phase 1: 즉시 실행 (1-2일)

1. load-generator 설정 검토 및 중복 등록 제거
2. PBKDF2 반복 횟수 100,000 → 60,000으로 감소

**예상 효과**:
- 4xx 에러율: 26.4% → 1% 미만
- P99 레이턴시: 3.71s → 2.2s

### Phase 2: 단기 개선 (1주)

1. CPU 리소스 재조정
2. 분산 추적(Jaeger/Tempo) 설정으로 병목 지점 정확한 파악

**예상 효과**:
- P99 레이턴시: 2.2s → 1.5s

### Phase 3: 중기 개선 (1개월)

1. Argon2로 비밀번호 해싱 알고리즘 전환
2. 기존 사용자 비밀번호 점진적 마이그레이션

**예상 효과**:
- P99 레이턴시: 1.5s → 0.5s 미만
- 보안 수준 향상

### Phase 4: 장기 개선 (3개월)

1. Redis 기반 인증 캐싱 구현
2. Rate Limiting 세부 조정

**예상 효과**:
- P99 레이턴시: 0.5s → 0.1s (캐시 히트 시)
- 시스템 전반적인 안정성 향상

## 4. 진단 및 검증 방법

### 4.1. 개선 전 베이스라인 측정

```bash
# Prometheus에서 현재 메트릭 수집
kubectl exec -n monitoring prometheus-prometheus-kube-prometheus-prometheus-0 -c prometheus -- sh -c '
  wget -qO- "http://localhost:9090/api/v1/query?query=histogram_quantile(0.99,sum(rate(istio_request_duration_milliseconds_bucket{destination_service_name=~\"prod-auth.*\"}[5m]))by(le))" 2>/dev/null
'

# 에러율 확인
kubectl exec -n monitoring prometheus-prometheus-kube-prometheus-prometheus-0 -c prometheus -- sh -c '
  wget -qO- "http://localhost:9090/api/v1/query?query=sum(rate(istio_requests_total{destination_service_name=~\"prod-auth.*\",response_code=~\"4..\"}[5m]))/sum(rate(istio_requests_total{destination_service_name=~\"prod-auth.*\"}[5m]))*100" 2>/dev/null
'
```

### 4.2. CPU 스로틀링 확인

```bash
kubectl top pods -n titanium-prod -l app=prod-user-service
kubectl exec -n monitoring prometheus-prometheus-kube-prometheus-prometheus-0 -c prometheus -- sh -c '
  wget -qO- "http://localhost:9090/api/v1/query?query=rate(container_cpu_cfs_throttled_seconds_total{namespace=\"titanium-prod\",pod=~\"prod-user-service.*\"}[5m])" 2>/dev/null
'
```

### 4.3. 개선 후 검증

각 Phase 완료 후:
1. Grafana 대시보드에서 P99 레이턴시 확인
2. 4xx 에러율 추이 확인
3. 7일간 메트릭 모니터링하여 안정성 검증
4. 부하 테스트로 피크 시간대 성능 확인

## 5. 롤백 계획

각 변경 사항에 대한 롤백 절차:

### PBKDF2 반복 횟수 변경 롤백
```bash
# 기존 설정으로 복원
git revert <commit-hash>
kubectl rollout restart deployment/prod-user-service -n titanium-prod
```

### Argon2 전환 롤백
```python
# 하이브리드 검증 로직으로 안전한 롤백
def verify_password(stored_hash, password):
    if stored_hash.startswith('$argon2'):
        # Argon2 검증
        return ph.verify(stored_hash, password)
    else:
        # 기존 PBKDF2 검증
        return check_password_hash(stored_hash, password)
```

## 6. 참고 자료

- OWASP Password Storage Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html
- Argon2 Documentation: https://github.com/P-H-C/phc-winner-argon2
- NIST SP 800-132: https://csrc.nist.gov/publications/detail/sp/800-132/final
- Istio Rate Limiting: https://istio.io/latest/docs/tasks/policy-enforcement/rate-limiting/

## 7. 다음 단계

1. 개발팀 리뷰 및 승인
2. Phase 1 구현 시작
3. 테스트 환경에서 검증 후 프로덕션 배포
4. 지속적인 모니터링 및 추가 최적화

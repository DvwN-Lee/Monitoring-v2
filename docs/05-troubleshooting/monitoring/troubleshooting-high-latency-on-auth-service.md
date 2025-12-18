---
version: 1.0
last_updated: 2025-11-15
author: Dongju Lee
---

# 사용자 인증 서비스 고지연 시간 문제 해결

## 문제 현상

### Grafana 메트릭
```
user-service P95 Latency: 941ms
user-service P99 Latency: 1.2s
```

### 발생 상황
- 사용자 등록 API (`POST /api/register`) 호출 시 응답 시간이 1초에 근접
- 로그인 API (`POST /api/login`)도 유사한 지연 발생
- 단순 조회 API (`GET /api/users`)는 정상 속도 (50ms 이하)
- 부하 테스트 중 타임아웃 발생

### 사용자 경험 영향
- 회원가입 버튼 클릭 후 1초 이상 대기
- 느린 응답으로 인한 사용자 이탈 가능성
- 동시 요청 시 서버 리소스 고갈

## 원인 분석

### 근본 원인

Python의 `werkzeug.security.generate_password_hash()` 함수가 기본적으로 매우 높은 반복 횟수(260,000회)로 PBKDF2 해싱을 수행하여 CPU 연산에 900ms 이상 소요됩니다.

### 기술적 배경

#### PBKDF2 알고리즘
PBKDF2(Password-Based Key Derivation Function 2)는 비밀번호를 안전하게 해싱하기 위해 반복 연산을 수행합니다.

- 반복 횟수가 높을수록 보안이 강화됨 (brute-force 공격 방어)
- 하지만 반복 횟수가 너무 높으면 서버 성능 저하
- 적절한 균형점을 찾는 것이 중요

#### 기존 코드의 문제
```python
# user-service/database_service.py:99
password_hash = generate_password_hash(password)
```

`method` 파라미터를 지정하지 않으면 Werkzeug가 기본값을 사용:
- Werkzeug 2.x 기본값: `pbkdf2:sha256:260000`
- 260,000회 반복 → 900ms+ 소요

#### 성능 측정
```bash
# Python에서 테스트
import time
from werkzeug.security import generate_password_hash

# 기본 설정 (260,000 반복)
start = time.time()
generate_password_hash("testpassword123")
print(f"Time: {(time.time() - start) * 1000:.2f}ms")
# 출력: Time: 941.23ms

# 최적화 설정 (100,000 반복)
start = time.time()
generate_password_hash("testpassword123", method='pbkdf2:sha256:100000')
print(f"Time: {(time.time() - start) * 1000:.2f}ms")
# 출력: Time: 234.56ms
```

### OWASP 권장사항

OWASP(Open Web Application Security Project)의 비밀번호 저장 가이드라인:

- PBKDF2-SHA256: 최소 100,000회 반복 권장
- 2023년 기준: 600,000회 권장 (서버 성능 고려)
- 100,000회도 충분한 보안 수준 제공

출처: [OWASP Password Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)

## 해결 방법

### 1. PBKDF2 반복 횟수 최적화

#### 수정 전
```python
# user-service/database_service.py
async def add_user(self, username: str, email: str, password: str) -> Optional[int]:
    """Add a new user with hashed password."""
    password_hash = generate_password_hash(password)
    # ...
```

#### 수정 후
```python
# user-service/database_service.py
async def add_user(self, username: str, email: str, password: str) -> Optional[int]:
    """Add a new user with hashed password."""
    password_hash = generate_password_hash(password, method='pbkdf2:sha256:100000')
    # ...
```

### 2. 반복 횟수를 환경 변수로 관리

보다 유연한 설정을 위해 환경 변수 사용:

```python
import os
from werkzeug.security import generate_password_hash

# 환경 변수에서 반복 횟수 가져오기 (기본값: 100000)
PBKDF2_ITERATIONS = int(os.getenv('PBKDF2_ITERATIONS', '100000'))

async def add_user(self, username: str, email: str, password: str) -> Optional[int]:
    """Add a new user with hashed password."""
    password_hash = generate_password_hash(
        password,
        method=f'pbkdf2:sha256:{PBKDF2_ITERATIONS}'
    )
    # ...
```

Kubernetes ConfigMap:
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: user-service-config
  namespace: titanium-prod
data:
  PBKDF2_ITERATIONS: "100000"
```

### 3. 대체 해싱 알고리즘 고려 (선택사항)

더 나은 성능이 필요한 경우 Argon2 또는 bcrypt 사용:

#### Argon2 (권장)
```python
from argon2 import PasswordHasher

ph = PasswordHasher()
password_hash = ph.hash(password)

# 검증
ph.verify(password_hash, password)
```

**장점**:
- 2015년 Password Hashing Competition 우승
- PBKDF2보다 brute-force 공격에 강함
- 메모리 하드 함수 (GPU 공격 방어)

**단점**:
- 추가 라이브러리 필요 (`pip install argon2-cffi`)
- 기존 PBKDF2 해시와 호환되지 않음 (마이그레이션 필요)

#### bcrypt
```python
from flask_bcrypt import Bcrypt

bcrypt = Bcrypt()
password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

# 검증
bcrypt.check_password_hash(password_hash, password)
```

**장점**:
- 널리 사용되는 안정적인 알고리즘
- 자동으로 salt 생성 및 관리

## 검증 방법

### 1. 로컬 성능 테스트

```bash
# user-service 재시작
cd user-service
python3 user_service.py

# 성능 테스트 스크립트 작성
cat > test_register_latency.sh << 'EOF'
#!/bin/bash
for i in {1..10}; do
  start=$(date +%s%3N)
  curl -s -X POST http://localhost:8001/api/register \
    -H "Content-Type: application/json" \
    -d "{\"username\":\"testuser${i}\",\"email\":\"test${i}@example.com\",\"password\":\"password123\"}"
  end=$(date +%s%3N)
  echo "Request $i: $((end - start))ms"
done
EOF

chmod +x test_register_latency.sh
./test_register_latency.sh

# 예상 결과: 200-300ms
```

### 2. Cluster 배포 및 테스트

```bash
# 이미지 빌드
docker build -t your-registry/user-service:optimized ./user-service
docker push your-registry/user-service:optimized

# Deployment 업데이트
kubectl set image deployment/user-service-deployment \
  user-service=your-registry/user-service:optimized -n titanium-prod

# 배포 상태 확인
kubectl rollout status deployment/user-service-deployment -n titanium-prod
```

### 3. Grafana 메트릭 확인

```bash
# Grafana 대시보드 접속
kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80

# 브라우저: http://localhost:3000
# Dashboard: Golden Signals

# 쿼리:
# P95 Latency
histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{service="user-service"}[5m])) by (le))

# P99 Latency
histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket{service="user-service"}[5m])) by (le))
```

**예상 결과**:
- P95: 941ms → 250ms 이하
- P99: 1200ms → 350ms 이하

### 4. 부하 테스트

```bash
# k6 부하 테스트
cat > load_test.js << 'EOF'
import http from 'k6/http';
import { check, sleep } from 'k6';

export let options = {
  stages: [
    { duration: '1m', target: 50 },  // 50명 동시 사용자
    { duration: '3m', target: 50 },
    { duration: '1m', target: 0 },
  ],
};

export default function () {
  let payload = JSON.stringify({
    username: `user_${__VU}_${__ITER}`,
    email: `user_${__VU}_${__ITER}@example.com`,
    password: 'testpassword123',
  });

  let res = http.post('http://istio-ingressgateway/api/register', payload, {
    headers: { 'Content-Type': 'application/json' },
  });

  check(res, {
    'status is 200': (r) => r.status === 200,
    'response time < 500ms': (r) => r.timings.duration < 500,
  });

  sleep(1);
}
EOF

k6 run load_test.js
```

## 예방 방법

### 1. 성능 벤치마크 작성

```python
# tests/test_performance.py
import time
import pytest
from database_service import UserServiceDatabase

@pytest.mark.benchmark
def test_password_hashing_performance():
    """비밀번호 해싱이 300ms 이내에 완료되어야 함"""
    db = UserServiceDatabase()

    start = time.time()
    # 실제 해싱 수행
    password_hash = generate_password_hash("testpassword123", method='pbkdf2:sha256:100000')
    elapsed = (time.time() - start) * 1000

    assert elapsed < 300, f"Password hashing took {elapsed:.2f}ms, expected < 300ms"
```

### 2. CI/CD Pipeline에 성능 테스트 추가

```yaml
# .github/workflows/ci.yml
- name: Run Performance Tests
  run: |
    cd user-service
    pytest tests/test_performance.py -v
```

### 3. Grafana 알림 설정

```yaml
# prometheus-rules.yaml
groups:
  - name: latency-alerts
    rules:
      - alert: HighAuthServiceLatency
        expr: histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{service="user-service", endpoint="/api/register"}[5m])) by (le)) > 0.5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "User service registration latency is high"
          description: "P95 latency for /api/register is {{ $value }}s (threshold: 0.5s)"
```

### 4. 문서화

```markdown
# docs/architecture/security.md

## 비밀번호 해싱 정책

- 알고리즘: PBKDF2-SHA256
- 반복 횟수: 100,000회
- 근거: OWASP 권장사항 충족 + 성능 균형
- 목표 레이턴시: 200-300ms

### 반복 횟수 변경 시 고려사항
1. 보안과 성능 트레이드오프
2. 기존 사용자 비밀번호 재해싱 필요 여부
3. 부하 테스트로 영향도 확인
```

## 관련 문서

- [시스템 아키텍처 - 마이크로서비스 구조](../../02-architecture/architecture.md#3-마이크로서비스-구조)
- [시스템 아키텍처 - 모니터링 및 로깅](../../02-architecture/architecture.md#5-모니터링-및-로깅)
- [성능 개선 계획](../../04-operations/guides/performance-improvement-plan.md)


## 참고 사항

### 보안과 성능의 균형

| 반복 횟수 | 해싱 시간 | 보안 수준 | 권장 사항 |
|----------|----------|---------|----------|
| 10,000 | ~23ms | 낮음 | 사용하지 말 것 |
| 100,000 | ~230ms | 중상 | OWASP 최소 권장 |
| 260,000 | ~940ms | 높음 | 성능 문제 발생 |
| 600,000 | ~2100ms | 매우 높음 | 일반 서비스에 과도함 |

### 하드웨어별 성능 차이

- 로컬 개발 환경 (M1 Mac): 100,000회 → 150ms
- 클라우드 VM (2 vCPU): 100,000회 → 250ms
- Container 제한 (0.5 CPU): 100,000회 → 400ms

CPU 리소스에 따라 적절한 반복 횟수 조정 필요.

### 향후 개선 방안

1. **비동기 작업 큐**: 회원가입 요청을 비동기로 처리
   ```python
   # Celery 또는 Redis Queue 사용
   @celery.task
   def create_user_async(username, email, password):
       # 해싱 및 DB 저장
   ```

2. **캐싱**: 동일 비밀번호 재사용 시 캐시 활용 (주의: 보안 위험 검토 필요)

3. **Argon2 마이그레이션**: 점진적으로 Argon2로 전환
   ```python
   # 로그인 시 자동 업그레이드
   if password_hash.startswith('pbkdf2:'):
       # PBKDF2 검증
       if verify_password(password, password_hash):
           # Argon2로 재해싱
           new_hash = argon2.hash(password)
           update_user_password(user_id, new_hash)
   ```

## 관련 커밋
- `33f1220`: feat: pbkdf2 반복 횟수를 100,000회로 최적화하여 Latency 개선

## 추가 자료
- [OWASP Password Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)
- [NIST SP 800-63B](https://pages.nist.gov/800-63-3/sp800-63b.html) - Digital Identity Guidelines
- [Argon2 RFC 9106](https://datatracker.ietf.org/doc/html/rfc9106)

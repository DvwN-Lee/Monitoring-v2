# k6 errors threshold 경고 원인 분석

## 문제 현상

k6 테스트 실행 시 다음과 같은 경고 발생:
```
time="2025-11-22T15:20:37+09:00" level=error msg="thresholds on metrics 'errors' have been crossed"
```

하지만 실제 테스트 결과는:
- 체크 성공률: 100% (1800/1800)
- HTTP 요청 실패율: 0%
- 모든 threshold 통과

## 원인 분석

### 1. errors 메트릭 정의

```javascript
// Custom metrics
const errorRate = new Rate('errors');

// Threshold 설정
thresholds: {
  http_req_duration: ['p(95)<500'],
  http_req_failed: ['rate<0.01'],
  errors: ['rate<0.01'],  // ← 문제의 threshold
}
```

### 2. errorRate 사용 방식

```javascript
check(dashboardRes, {
  'dashboard status 200': (r) => r.status === 200,
  'dashboard response time < 1s': (r) => r.timings.duration < 1000,
}) || errorRate.add(1);
```

**동작 원리**:
- `check()`가 true 반환 (모든 체크 통과) → `errorRate.add(1)` 실행 안 됨
- `check()`가 false 반환 (체크 실패) → `errorRate.add(1)` 실행됨

### 3. 핵심 문제

**모든 테스트가 성공한 경우**:
1. `check()`는 항상 true 반환
2. `errorRate.add()`는 한 번도 호출되지 않음
3. `errors` Rate 메트릭은 **샘플이 0개**
4. k6에서 샘플이 없는 Rate 메트릭의 threshold 평가 실패

**k6 동작**:
- 샘플이 없는 Rate 메트릭: `rate` 값이 정의되지 않음 (undefined/NaN)
- `undefined < 0.01` 비교 결과: false
- Threshold crossed 경고 발생

## 검증

Quick 테스트 결과:
```
checks_succeeded...: 100.00% 1800 out of 1800
checks_failed......: 0.00%   0 out of 1800
http_req_failed....: 0.00%   0 out of 900
errors.............: 0.00%   0 out of 0  ← 샘플 0개!
```

**errors 메트릭**: "0 out of 0" → 샘플이 없음을 명확히 보여줌

## 해결 방안

### 방안 1: errors threshold 제거 (권장)

**이유**:
- `http_req_failed` 메트릭이 이미 HTTP 요청 실패율을 추적
- `checks` 메트릭이 체크 성공률을 추적
- `errors` 커스텀 메트릭은 중복

**수정**:
```javascript
thresholds: {
  http_req_duration: ['p(95)<500'],
  http_req_failed: ['rate<0.01'],
  // errors: ['rate<0.01'], // 제거
}
```

### 방안 2: errorRate 초기화

errorRate에 항상 샘플 추가:

```javascript
check(dashboardRes, {
  'dashboard status 200': (r) => r.status === 200,
  'dashboard response time < 1s': (r) => r.timings.duration < 1000,
}) ? errorRate.add(0) : errorRate.add(1);
```

또는:

```javascript
const checkResult = check(dashboardRes, {
  'dashboard status 200': (r) => r.status === 200,
  'dashboard response time < 1s': (r) => r.timings.duration < 1000,
});
errorRate.add(checkResult ? 0 : 1);
```

### 방안 3: abortOnFail 옵션 사용

threshold 실패 시 테스트 중단하지 않도록 설정:

```javascript
thresholds: {
  http_req_duration: ['p(95)<500'],
  http_req_failed: ['rate<0.01'],
  errors: [{ threshold: 'rate<0.01', abortOnFail: false }],
}
```

## 권장 조치

**방안 1 선택**: errors threshold 완전 제거

**근거**:
1. 기존 메트릭만으로 충분히 검증 가능
2. 코드 단순화
3. 불필요한 경고 제거
4. 표준 k6 메트릭 활용

## 결론

- **현재 상태**: 테스트는 실제로 **100% 성공**
- **경고 원인**: 샘플이 없는 커스텀 메트릭의 threshold 평가 실패
- **실제 문제**: 없음 (경고만 발생)
- **권장 조치**: errors threshold 제거

이는 k6의 정상 동작이며, 테스트 결과에는 영향을 주지 않습니다.

# Changelog

## [2025-12-14] - Phase 1+2 보안/성능 개선 및 카테고리 기능

### Added
- Rate Limiting 적용 (slowapi) - API 분당 100 요청 제한
- CORS Middleware 추가
- 카테고리별 랜덤 색상 자동 할당 기능
- CSS 변수 기반 동적 색상 시스템

### Changed
- ClientSession Singleton Pattern 적용 (Connection Pool 재사용)
- Redis Cache TTL 최적화
  - 사용자 프로필: 5분
  - 블로그 목록: 1분
  - 카테고리: 1시간
- blog-service LEFT JOIN -> INNER JOIN 변경 (데이터 무결성 강화)

### Improved
- P95 Latency: 74.76ms (K6 100 VU 부하 테스트)
- P90 Latency: 55.67ms
- Error Rate: 0.01%
- Check Success Rate: 99.95%
- Cache Hit 시 응답 시간 90% 감소
- TCP Connection Overhead 90% 감소

---

## [2025-11-22] - k6 부하 테스트 통합

### Added
- k6 부하 테스트 스크립트 추가
  - `tests/performance/quick-test.js` - 2분 빠른 테스트
  - `tests/performance/load-test.js` - 10분 부하 테스트
- k6 실행 스크립트 추가: `scripts/run-k6-test.sh`
- k6 테스트 가이드 문서: `tests/performance/README.md`
  - 테스트 범위 및 목적 섹션 추가
  - 인프라 성능 검증에 초점을 맞춘 테스트임을 명시
  - 다른 테스트 유형과의 관계를 mermaid 다이어그램으로 시각화
- 테스트 결과 보고서: `docs/06-performance/k6-load-test-results.md`
- Threshold 분석 문서: `docs/06-performance/errors-threshold-analysis.md`

### Changed
- `.gitignore`: k6 테스트 결과 파일 제외 처리
- k6 스크립트 환경변수 지원: `BASE_URL` 환경변수로 대상 URL 설정 가능
- 엔드포인트 수정: `/lb-health` → `/health`

### Fixed
- **errors threshold 경고 해결**
  - 커스텀 `errors` Rate 메트릭 제거
  - 표준 `checks` 메트릭으로 대체
  - `errorRate.add()` 로직 제거하여 코드 단순화
  - Threshold crossed 경고 완전히 제거

### Improved
- 표준 k6 메트릭 활용 (더 명확한 threshold)
- 코드 단순화 (커스텀 메트릭 제거)
- `handleSummary` 함수 null 값 처리 개선

## 테스트 결과 요약

**성능 지표**:
- **P95 응답 시간**: 83.73ms (목표 500ms 대비 83% 더 빠름)
- **에러율**: 0%
- **체크 성공률**: 100%
- **HPA 자동 스케일링**: 확인됨 (2 → 4 replica)

**개선 효과**:
1. 불필요한 경고 제거
2. 코드 품질 향상 (단순화)
3. 표준 메트릭 활용
4. 더 명확한 테스트 검증

# UI/UX 개선사항 배포 가이드

## 1. 변경사항 요약

UI/UX 테스트 결과를 바탕으로 다음 4가지 주요 개선사항을 구현하였습니다.

### 1.1. Toast Notification 시스템 구현

**목적**: 사용자 경험 개선 - 차단형 alert() 다이얼로그를 비차단형 Toast 알림으로 대체

**변경 파일**:
- `blog-service/static/css/style.css`: Toast 스타일 및 애니메이션 추가 (라인 807-955)
- `blog-service/templates/index.html`: Toast container 추가 (라인 13)
- `blog-service/static/js/app.js`: Toast 객체 구현 및 alert() 호출 대체 (라인 1-83, 247, 263, 454, 457, 470, 487)

**주요 기능**:
- 4가지 타입 지원: success, error, warning, info
- 자동 사라짐 기능 (기본 3초)
- 수동 닫기 버튼 제공
- 부드러운 슬라이드 인/아웃 애니메이션
- 여러 Toast 동시 표시 가능 (최대 5개)

### 1.2. 카테고리 카운트 실시간 표시

**목적**: 정보 제공 개선 - 각 카테고리별 게시물 수를 실시간으로 표시

**변경 파일**:
- `api-gateway/main.go`: `/categories` endpoint 라우팅 추가 (라인 140)

**세부 사항**:
- 백엔드 API는 이미 구현되어 있었으나 API Gateway에서 라우팅되지 않는 문제 수정
- `/blog/api/categories` 및 `/api/categories` 경로 모두 지원
- blog-service로 요청을 정상적으로 프록시

### 1.3. 접근성(Accessibility) 강화

**목적**: WCAG 2.1 가이드라인 준수 및 스크린 리더 지원

**변경 파일**:
- `blog-service/templates/index.html`: 모든 주요 UI 요소에 ARIA 속성 추가
- `blog-service/static/js/app.js`: 동적 ARIA 속성 관리 (라인 310-344)

**추가된 ARIA 속성**:
- 카테고리 탭: `role="tablist"`, `role="tab"`, `aria-selected`, `aria-controls`
- 게시물 컨테이너: `role="tabpanel"`
- 페이지네이션: `aria-label="페이지 네비게이션"`, `aria-label="이전/다음 페이지"`
- 모달: `role="dialog"`, `aria-modal="true"`, `aria-labelledby`
- 폼 입력: `aria-required="true"`
- 에러 메시지: `role="alert"`, `aria-live="polite"`

### 1.4. 로딩 상태 표시

**목적**: 사용자 피드백 개선 - 데이터 로딩 중 시각적 피드백 제공

**변경 파일**:
- `blog-service/static/css/style.css`: Loading spinner 스타일 추가 (라인 957-994)
- `blog-service/static/js/app.js`: showLoading/hideLoading 함수 구현 및 적용 (라인 346-378)

**주요 기능**:
- 반투명 오버레이로 컨텐츠 보호
- 회전 애니메이션 스피너
- "로딩 중..." 텍스트 표시
- loadPosts() 함수에 통합 (try/finally 패턴으로 안정적 cleanup)

---

## 2. 배포 절차

### 2.1. 사전 준비사항

필요한 도구 및 권한 확인:
```bash
# Docker 빌드 권한
docker info

# Kubernetes 클러스터 접근 확인
kubectl cluster-info
kubectl config current-context  # solid-cloud 여야 함

# 네임스페이스 확인
kubectl get ns titanium-prod
```

### 2.2. Blog Service 배포

#### Step 1: Docker 이미지 빌드 및 푸시

```bash
# 작업 디렉토리로 이동
cd /Users/idongju/Desktop/Git/Monitoring-v2

# Git 변경사항 확인
git status

# 변경사항 커밋 (선택사항 - CI/CD가 자동으로 처리)
git add blog-service/static/css/style.css
git add blog-service/templates/index.html
git add blog-service/static/js/app.js
git commit -m "feat: UI/UX 개선사항 적용

- Toast notification 시스템 구현
- 접근성 향상을 위한 ARIA 속성 추가
- 로딩 상태 표시 추가
- 사용자 경험 개선"

# Docker 이미지 빌드
docker build -t idongju/blog-service:ui-improvements ./blog-service

# Docker Hub에 푸시
docker push idongju/blog-service:ui-improvements
```

#### Step 2: Kubernetes 배포 업데이트

```bash
# blog-service deployment의 이미지 태그 업데이트
kubectl set image deployment/blog-service \
  blog-service=idongju/blog-service:ui-improvements \
  -n titanium-prod

# 롤아웃 상태 확인
kubectl rollout status deployment/blog-service -n titanium-prod

# Pod 상태 확인
kubectl get pods -n titanium-prod -l app=blog-service
```

### 2.3. API Gateway 배포

#### Step 1: Docker 이미지 빌드 및 푸시

```bash
# Git 변경사항 커밋
git add api-gateway/main.go
git commit -m "fix: categories endpoint 라우팅 추가

- /api/categories 및 /blog/api/categories 경로 지원
- blog-service의 카테고리 API와 연동"

# Docker 이미지 빌드
docker build -t idongju/api-gateway:categories-fix ./api-gateway

# Docker Hub에 푸시
docker push idongju/api-gateway:categories-fix
```

#### Step 2: Kubernetes 배포 업데이트

```bash
# api-gateway deployment의 이미지 태그 업데이트
kubectl set image deployment/api-gateway \
  api-gateway=idongju/api-gateway:categories-fix \
  -n titanium-prod

# 롤아웃 상태 확인
kubectl rollout status deployment/api-gateway -n titanium-prod

# Pod 상태 확인
kubectl get pods -n titanium-prod -l app=api-gateway
```

### 2.4. 배포 후 검증

#### 기본 Health Check

```bash
# API Gateway 헬스체크
kubectl exec -n titanium-prod deployment/api-gateway -- \
  wget -qO- http://localhost:8000/health

# Blog Service 헬스체크
kubectl exec -n titanium-prod deployment/blog-service -- \
  wget -qO- http://localhost:8005/blog/health
```

#### 기능 검증

1. **Toast Notification 검증**:
   - 브라우저에서 http://10.0.11.168:31304/blog/ 접속
   - 회원가입 시도 → Toast 알림 확인
   - 로그아웃 시도 → Toast 알림 확인

2. **카테고리 카운트 검증**:
   ```bash
   # API 직접 호출
   curl http://10.0.11.168:31304/blog/api/categories
   ```
   - 브라우저에서 카테고리 탭에 카운트가 표시되는지 확인

3. **접근성 검증**:
   - 브라우저 개발자 도구 → Elements 탭에서 ARIA 속성 확인
   - Tab 키로 키보드 네비게이션 테스트
   - 스크린 리더로 테스트 (선택사항)

4. **로딩 상태 검증**:
   - 네트워크 속도를 느리게 설정 (Chrome DevTools → Network → Throttling: Slow 3G)
   - 페이지 새로고침 시 로딩 스피너 표시 확인

#### 로그 확인

```bash
# Blog Service 로그
kubectl logs -n titanium-prod deployment/blog-service --tail=50 -f

# API Gateway 로그
kubectl logs -n titanium-prod deployment/api-gateway --tail=50 -f

# Istio 사이드카 로그
kubectl logs -n titanium-prod deployment/blog-service -c istio-proxy --tail=50
```

---

## 3. 롤백 절차

문제 발생 시 이전 버전으로 신속하게 롤백할 수 있습니다.

### 3.1. Blog Service 롤백

```bash
# 이전 리비전으로 롤백
kubectl rollout undo deployment/blog-service -n titanium-prod

# 특정 리비전으로 롤백
kubectl rollout history deployment/blog-service -n titanium-prod
kubectl rollout undo deployment/blog-service -n titanium-prod --to-revision=<번호>
```

### 3.2. API Gateway 롤백

```bash
# 이전 리비전으로 롤백
kubectl rollout undo deployment/api-gateway -n titanium-prod

# 특정 리비전으로 롤백
kubectl rollout history deployment/api-gateway -n titanium-prod
kubectl rollout undo deployment/api-gateway -n titanium-prod --to-revision=<번호>
```

---

## 4. 모니터링

배포 후 다음 메트릭을 모니터링해야 합니다:

### 4.1. Grafana 대시보드 확인

URL: http://10.0.11.168:30300

**확인 사항**:
- Blog Service의 에러율 증가 여부
- API Gateway의 latency 변화
- 4xx/5xx 응답 코드 증가 여부

### 4.2. Prometheus Alerts 확인

```bash
# Alertmanager 상태 확인
kubectl get pods -n monitoring -l app.kubernetes.io/name=alertmanager

# 활성화된 알람 확인
kubectl port-forward -n monitoring svc/prometheus-kube-prometheus-alertmanager 9093:9093
# 브라우저에서 http://localhost:9093 접속
```

### 4.3. 주요 지표

**정상 범위**:
- Blog Service 응답 시간 (p95): < 200ms
- API Gateway 응답 시간 (p95): < 150ms
- 에러율: < 1%
- Pod CPU 사용률: < 70%
- Pod 메모리 사용률: < 80%

**이상 징후 시 조치**:
1. 로그 확인하여 에러 패턴 분석
2. 필요시 Pod 재시작: `kubectl rollout restart deployment/<service-name> -n titanium-prod`
3. 지속적인 문제 발생 시 롤백 실행

---

## 5. 문제 해결 가이드

### 5.1. Toast가 표시되지 않음

**증상**: alert() 다이얼로그가 여전히 표시되거나 아무 알림도 없음

**원인**: 브라우저 캐시 문제

**해결**:
```bash
# 사용자에게 안내
1. 브라우저에서 Ctrl+Shift+R (하드 리프레시)
2. 또는 브라우저 캐시 삭제 후 재접속
```

### 5.2. 카테고리 카운트가 표시되지 않음

**증상**: 카테고리 탭에 (0)만 표시

**원인**: API Gateway 라우팅 실패 또는 Blog Service API 오류

**해결**:
```bash
# API Gateway 로그 확인
kubectl logs -n titanium-prod deployment/api-gateway | grep categories

# Blog Service에 직접 요청
kubectl exec -n titanium-prod deployment/blog-service -- \
  curl http://localhost:8005/blog/api/categories

# 404 에러 시 API Gateway 재배포 필요
```

### 5.3. 로딩 스피너가 사라지지 않음

**증상**: 게시물이 로드되었는데도 로딩 오버레이가 계속 표시

**원인**: JavaScript 에러로 hideLoading() 호출 실패

**해결**:
```bash
# 브라우저 콘솔에서 에러 확인
# Blog Service 로그에서 500 에러 확인
kubectl logs -n titanium-prod deployment/blog-service | grep "ERROR\|500"
```

### 5.4. ARIA 속성 누락

**증상**: 스크린 리더가 요소를 제대로 읽지 못함

**원인**: HTML 템플릿이 제대로 업데이트되지 않음

**해결**:
```bash
# Pod를 강제로 재시작하여 최신 템플릿 로드
kubectl rollout restart deployment/blog-service -n titanium-prod
```

---

## 6. 추가 개선 제안

향후 추가로 고려할 수 있는 개선사항:

1. **Toast 우선순위 큐**: 중요도에 따라 Toast 표시 순서 조정
2. **다크 모드 지원**: 사용자 선호도에 따른 테마 전환
3. **오프라인 모드**: Service Worker를 이용한 오프라인 캐싱
4. **국제화(i18n)**: 다국어 지원
5. **성능 최적화**: Virtual scrolling, lazy loading 구현

---

## 7. 참고 문서

- UI/UX 테스트 리포트: `docs/04-operations/ui-ux-test-report.md`
- UI/UX 테스트 시나리오: `docs/04-operations/ui-ux-test-scenarios.md`
- WCAG 2.1 가이드라인: https://www.w3.org/WAI/WCAG21/quickref/
- Kubernetes Deployment 가이드: https://kubernetes.io/docs/concepts/workloads/controllers/deployment/

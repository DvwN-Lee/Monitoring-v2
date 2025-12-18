---
version: 1.0
last_updated: 2025-11-15
author: Dongju Lee
---

# 프로젝트 종합 테스트 체크리스트

## 개요

이 문서는 Monitoring-v2 프로젝트의 전체 구현 내용을 체계적으로 점검하기 위한 테스트 체크리스트입니다. 시스템의 테스트 전략 분석을 기반으로 작성되었습니다.

## 테스트 실행 방법

### 자동화 테스트
```bash
# 빠른 자동화 테스트 (약 5분 소요)
./scripts/comprehensive-test.sh
```

### 수동 테스트
이 문서의 체크리스트를 따라 단계별로 수행합니다.

## 예상 소요 시간
- 자동화 테스트: 5~10분
- 수동 테스트 전체: 1.5~2시간
- 선택적 테스트 포함: 2~3시간

---

## Phase 1: 인프라 및 환경 검증 (Critical)

### 1-1. Kubernetes Cluster Node 상태 확인
- [ ] **테스트 수행**
  ```bash
  kubectl get nodes
  ```
- [ ] **성공 기준**: 모든 Node의 STATUS가 `Ready`
- [ ] **결과 기록**: _____개 Node 모두 Ready 상태
- [ ] **예상 시간**: 1분

### 1-2. 핵심 Namespace 존재 여부 확인
- [ ] **테스트 수행**
  ```bash
  kubectl get ns
  ```
- [ ] **성공 기준**: `titanium-prod`, `monitoring`, `istio-system`, `argocd` 존재
- [ ] **결과 기록**:
  - [ ] titanium-prod
  - [ ] monitoring
  - [ ] istio-system
  - [ ] argocd
- [ ] **예상 시간**: 1분

### 1-3. 데이터베이스 및 캐시 Pod 상태 확인
- [ ] **테스트 수행**
  ```bash
  kubectl get pods -n titanium-prod -l "app in (postgresql, prod-redis)"
  ```
- [ ] **성공 기준**: `postgresql-0` 및 `prod-redis-xxx` Pod이 `2/2 Running`
- [ ] **결과 기록**:
  - [ ] PostgreSQL: 2/2 Running
  - [ ] Redis: 2/2 Running
- [ ] **예상 시간**: 2분

### 1-4. 영구 볼륨(PVC) 상태 확인
- [ ] **테스트 수행**
  ```bash
  kubectl get pvc -n titanium-prod
  kubectl get pvc -n monitoring
  ```
- [ ] **성공 기준**: 모든 PVC의 STATUS가 `Bound`
- [ ] **결과 기록**: _____개 PVC Bound 상태
- [ ] **예상 시간**: 2분

---

## Phase 2: 애플리케이션 배포 및 기본 기능 검증 (Critical)

### 2-1. 모든 애플리케이션 Pod 상태 확인
- [ ] **테스트 수행**
  ```bash
  kubectl get pods -n titanium-prod
  ```
- [ ] **성공 기준**: 모든 서비스 Pod이 `2/2 Running`
- [ ] **결과 기록**:
  - [ ] api-gateway: _____개 Pod (2/2 Running)
  - [ ] auth-service: _____개 Pod (2/2 Running)
  - [ ] blog-service: _____개 Pod (2/2 Running)
  - [ ] user-service: _____개 Pod (2/2 Running)
- [ ] **예상 시간**: 2분

### 2-2. 각 서비스의 시작 로그 확인
- [ ] **테스트 수행**
  ```bash
  kubectl logs -n titanium-prod -l app=prod-user-service -c user-service | tail -n 20
  kubectl logs -n titanium-prod -l app=prod-auth-service -c auth-service | tail -n 20
  kubectl logs -n titanium-prod -l app=prod-blog-service -c blog-service | tail -n 20
  kubectl logs -n titanium-prod -l app=prod-api-gateway -c api-gateway | tail -n 20
  ```
- [ ] **성공 기준**: FastAPI 서비스는 "Application startup complete", 심각한 오류 없음
- [ ] **결과 기록**:
  - [ ] user-service: 정상 시작
  - [ ] auth-service: 정상 시작
  - [ ] blog-service: 정상 시작
  - [ ] api-gateway: 정상 시작
- [ ] **예상 시간**: 5분

---

## Phase 3: 서비스 간 통신 및 라우팅 검증 (Critical)

### 3-1. Istio Ingress Gateway 외부 IP 확인
- [ ] **테스트 수행**
  ```bash
  export INGRESS_IP=$(kubectl get svc -n istio-system istio-ingressgateway -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
  echo $INGRESS_IP
  ```
- [ ] **성공 기준**: 유효한 IP 주소 출력
- [ ] **결과 기록**: INGRESS_IP = _____________________
- [ ] **예상 시간**: 1분

### 3-2. API Gateway를 통한 User-Service 라우팅 테스트
- [ ] **테스트 수행**
  ```bash
  curl -s -o /dev/null -w "%{http_code}" http://$INGRESS_IP/api/users/
  ```
- [ ] **성공 기준**: HTTP 200 또는 307 반환
- [ ] **결과 기록**: HTTP _____
- [ ] **예상 시간**: 2분

### 3-3. API Gateway를 통한 Blog-Service 라우팅 테스트
- [ ] **테스트 수행**
  ```bash
  curl -s -o /dev/null -w "%{http_code}" http://$INGRESS_IP/blog/
  ```
- [ ] **성공 기준**: HTTP 200 또는 307 반환
- [ ] **결과 기록**: HTTP _____
- [ ] **예상 시간**: 2분

### 3-4. Auth API 라우팅 테스트
- [ ] **테스트 수행**
  ```bash
  curl -s http://$INGRESS_IP/blog/api/categories
  ```
- [ ] **성공 기준**: JSON 형식의 카테고리 목록 반환
- [ ] **결과 기록**: 카테고리 _____개 반환
- [ ] **예상 시간**: 2분

---

## Phase 4: 서비스 메시 (Istio) 고급 기능 검증 (Important)

### 4-1. mTLS STRICT 모드 적용 확인
- [ ] **테스트 수행**
  ```bash
  # 실행 중인 api-gateway Pod 이름 확인
  POD=$(kubectl get pods -n titanium-prod -l app=prod-api-gateway -o jsonpath='{.items[0].metadata.name}')
  istioctl authn tls-check $POD.titanium-prod prod-user-service.titanium-prod.svc.cluster.local
  ```
- [ ] **성공 기준**: STATUS가 `OK`, SERVER가 `STRICT`
- [ ] **결과 기록**: mTLS STRICT 모드 _____ (적용됨/미적용)
- [ ] **예상 시간**: 5분

### 4-2. HPA 동작 테스트 (선택사항)
- [ ] **테스트 수행**
  ```bash
  # 1. 현재 HPA 상태 확인
  kubectl get hpa -n titanium-prod

  # 2. 부하 증폭
  kubectl scale deployment -n titanium-prod load-generator --replicas=15

  # 3. 2-3분 후 상태 관찰
  watch kubectl get hpa,pods -n titanium-prod

  # 4. 부하 원상 복구
  kubectl scale deployment -n titanium-prod load-generator --replicas=5
  ```
- [ ] **성공 기준**: HPA가 동작하여 Pod 수가 증가 후 감소
- [ ] **결과 기록**: 최대 Pod 수 _____개까지 증가
- [ ] **예상 시간**: 10분

### 4-3. API Rate Limiting 테스트 (선택사항)
- [ ] **테스트 수행**
  ```bash
  # 200개 요청을 10개 동시 연결로 전송
  for i in {1..200}; do
    curl -s -o /dev/null -w "%{http_code}\n" http://$INGRESS_IP/api/users/ &
  done | sort | uniq -c
  ```
- [ ] **성공 기준**: `429 Too Many Requests` 상태 코드 다수 관찰
- [ ] **결과 기록**: 429 에러 _____개 발생
- [ ] **예상 시간**: 5분

---

## Phase 5: 관측성 스택 검증 (Important)

### 5-1. Prometheus 메트릭 수집 대상 확인
- [ ] **테스트 수행**
  ```bash
  # Port forward
  kubectl port-forward -n monitoring svc/prometheus-kube-prometheus-prometheus 9090 &

  # 브라우저: http://localhost:9090
  # Status -> Targets 메뉴
  ```
- [ ] **성공 기준**: 4개 ServiceMonitor 엔드포인트 모두 `UP` 상태
- [ ] **결과 기록**:
  - [ ] user-service: UP
  - [ ] auth-service: UP
  - [ ] blog-service: UP
  - [ ] api-gateway: UP
- [ ] **예상 시간**: 5분
- [ ] **Port forward 종료**: `pkill -f "port-forward.*9090"`

### 5-2. Grafana 대시보드 시각화 확인
- [ ] **테스트 수행**
  ```bash
  # Port forward
  kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80 &

  # 브라우저: http://localhost:3000
  # 초기 ID/PW: admin/prom-operator
  # Dashboards -> Golden Signals
  ```
- [ ] **성공 기준**: 4개 패널(Latency, Traffic, Errors, Saturation)에 데이터 표시, "No Data" 없음
- [ ] **결과 기록**:
  - [ ] Latency 패널: 데이터 정상
  - [ ] Traffic 패널: 데이터 정상
  - [ ] Errors 패널: 데이터 정상
  - [ ] Saturation 패널: 데이터 정상
- [ ] **예상 시간**: 10분
- [ ] **Port forward 종료**: `pkill -f "port-forward.*3000"`

### 5-3. Loki 중앙 로깅 확인
- [ ] **테스트 수행**
  - Grafana (http://localhost:3000)
  - Explore 메뉴 -> 데이터 소스 `Loki`
  - Log browser: `{app="prod-user-service"}`
- [ ] **성공 기준**: 각 서비스의 로그가 실시간 표시
- [ ] **결과 기록**: _____ 개 서비스 로그 수집 확인
- [ ] **예상 시간**: 5분

### 5-4. AlertManager 규칙 및 알림 테스트 (선택사항)
- [ ] **테스트 수행**
  ```bash
  # 1. AlertManager UI 포트포워딩
  kubectl port-forward -n monitoring svc/alertmanager-operated 9093 &

  # 2. user-service 강제 다운
  kubectl scale deployment -n titanium-prod prod-user-service-deployment --replicas=0

  # 3. 1-2분 후 http://localhost:9093 에서 알림 확인

  # 4. 서비스 복구
  kubectl scale deployment -n titanium-prod prod-user-service-deployment --replicas=2
  ```
- [ ] **성공 기준**: AlertManager UI에 알림이 `firing` 후 `resolved` 상태로 변경
- [ ] **결과 기록**: 알림 발생 _____ (확인됨/확인 안 됨)
- [ ] **예상 시간**: 10분
- [ ] **Port forward 종료**: `pkill -f "port-forward.*9093"`

---

## Phase 6: CI/CD 및 GitOps Pipeline 검증 (Critical)

### 6-1. CI Pipeline 트리거 및 실행 확인 (선택사항)
- [ ] **테스트 수행**
  1. README.md 파일 간단한 수정
  2. 새 브랜치로 푸시
  3. main 브랜치로 PR 생성
- [ ] **성공 기준**: GitHub Actions CI 워크플로우 자동 실행, 모든 Job 성공
- [ ] **결과 기록**: CI Pipeline _____ (성공/실패)
- [ ] **예상 시간**: 15분

### 6-2. Argo CD 상태 확인
- [ ] **테스트 수행**
  ```bash
  kubectl get application -n argocd titanium-app -o yaml
  ```
- [ ] **성공 기준**: health.status = `Healthy`, sync.status = `Synced`
- [ ] **결과 기록**:
  - Health: _____
  - Sync: _____
- [ ] **예상 시간**: 5분

### 6-3. Argo CD UI 확인 (선택사항)
- [ ] **테스트 수행**
  ```bash
  kubectl port-forward -n argocd svc/argocd-server 8080:443 &

  # 브라우저: https://localhost:8080
  # 초기 비밀번호: kubectl get secret -n argocd argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d
  ```
- [ ] **성공 기준**: titanium-app이 `Healthy` 및 `Synced` 상태
- [ ] **결과 기록**: Argo CD UI 상태 _____
- [ ] **예상 시간**: 5분
- [ ] **Port forward 종료**: `pkill -f "port-forward.*8080"`

---

## Phase 7: 통합 시나리오 및 성능 테스트 (Critical)

### 7-1. End-to-End 사용자 시나리오 테스트
- [ ] **테스트 수행**
  ```bash
  # 1. 회원가입
  curl -X POST -H "Content-Type: application/json" \
    -d '{"username":"tester","email":"tester@example.com","password":"password123"}' \
    http://$INGRESS_IP/api/register

  # 2. 로그인
  TOKEN=$(curl -s -X POST -H "Content-Type: application/json" \
    -d '{"username":"tester","password":"password123"}' \
    http://$INGRESS_IP/blog/api/login | jq -r .access_token)

  echo "Token: $TOKEN"

  # 3. 블로그 글 작성 (토큰 필요 시)
  curl -X POST -H "Content-Type: application/json" \
    -H "Authorization: Bearer $TOKEN" \
    -d '{"title":"Test Post","content":"This is a test","category_id":1}' \
    http://$INGRESS_IP/blog/api/posts

  # 4. 게시글 목록 조회
  curl -s http://$INGRESS_IP/blog/api/posts | jq .
  ```
- [ ] **성공 기준**: 모든 요청이 성공(200 또는 201), 게시글 생성 확인
- [ ] **결과 기록**: E2E 시나리오 _____ (성공/실패)
- [ ] **예상 시간**: 5분

### 7-2. 부하 테스트 및 성능 지표 확인 (선택사항)
- [ ] **테스트 수행**
  - load-generator를 통한 지속적 부하 관찰
  - Grafana에서 Golden Signals 대시보드 모니터링

  ```bash
  # Load generator 상태 확인
  kubectl get pods -n titanium-prod -l app=load-generator

  # Grafana 대시보드에서 30분 동안 관찰
  # - P95 Latency < 300ms
  # - Error Rate < 1%
  # - CPU/Memory 사용률
  ```
- [ ] **성공 기준**:
  - user-service P95 Latency ≤ 300ms
  - Error Rate < 1%
  - HPA 동작 확인
- [ ] **결과 기록**:
  - P95 Latency: _____ ms
  - Error Rate: _____ %
  - HPA 동작: _____ (예/아니오)
- [ ] **예상 시간**: 15~30분

---

## 테스트 결과 요약

### 전체 통계
- 전체 테스트 항목: _____개
- 성공: _____개
- 실패: _____개
- 건너뜀: _____개
- 성공률: _____%

### Critical 항목 결과
- Phase 1 (인프라): _____ / _____
- Phase 2 (애플리케이션): _____ / _____
- Phase 3 (통신/라우팅): _____ / _____
- Phase 7 (통합 시나리오): _____ / _____

### Important 항목 결과
- Phase 4 (서비스 메시): _____ / _____
- Phase 5 (관측성): _____ / _____
- Phase 6 (CI/CD): _____ / _____

### 실패한 테스트
1. _____________________________________
2. _____________________________________
3. _____________________________________

### 주요 발견 사항
- _____________________________________
- _____________________________________
- _____________________________________

### 권장 사항
- _____________________________________
- _____________________________________
- _____________________________________

---

## 참고 자료

- 자동화 스크립트: `scripts/comprehensive-test.sh`
- Troubleshooting 문서: `docs/05-troubleshooting/`
- Architecture 문서: `docs/02-architecture/architecture.md`
- Gemini 테스트 전략 분석: `/tmp/gemini_test_strategy.md`

## 테스트 환경

- 테스트 날짜: _____________________
- 테스트 담당자: _____________________
- Kubernetes 버전: _____________________
- Istio 버전: 1.20.1
- Cluster Node 수: _____개

## 주의사항

1. **Cluster 접근 권한**: kubeconfig가 올바르게 설정되어 있어야 함
2. **외부 의존성**: Docker Hub, GitHub Actions 등 외부 서비스 상태에 영향받을 수 있음
3. **리소스 사용량**: HPA 및 부하 테스트는 일시적으로 CPU/메모리 사용량 증가
4. **상태 변경**: 테스트 과정에서 데이터 생성 및 시스템 상태 변경됨
5. **Rate Limiting**: 429 에러는 정상적인 Rate Limiting 동작의 증거

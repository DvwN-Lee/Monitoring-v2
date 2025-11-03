# Week 5 최종 프로젝트 상태 보고서

## 프로젝트 개요

- **프로젝트명**: Cloud-Native 마이크로서비스 플랫폼 v2.0
- **프로젝트 기간**: 2025년 9월 30일 ~ 2025년 11월 3일 (5주)
- **개발 환경**: 단국대학교 Solid Cloud
- **Kubernetes 버전**: v1.29.7
- **작성일**: 2025년 11월 3일

---

## 1. 전체 완료율

### Must-Have 요구사항

| 항목 | 상태 | 완료율 |
|------|------|--------|
| Terraform으로 Kubernetes 클러스터 생성 | 완료 | 100% |
| PostgreSQL StatefulSet 배포 및 데이터 영속성 확인 | 완료 | 100% |
| GitHub Actions CI 파이프라인 동작 | 완료 | 100% |
| Argo CD GitOps 배포 자동화 | 완료 | 100% |
| Prometheus + Grafana 모니터링 대시보드 | 완료 | 100% |
| 모든 서비스 정상 동작 확인 | 완료 | 100% |

**Must-Have 전체 완료율: 100%**

### Should-Have 요구사항

| 항목 | 상태 | 완료율 |
|------|------|--------|
| Loki 중앙 로깅 시스템 | 완료 | 100% |
| Istio mTLS 활성화 | 완료 | 100% |
| ADR 3건 이상 작성 | 완료 (5건) | 100% |

**Should-Have 전체 완료율: 100%**

### Could-Have 요구사항

| 항목 | 상태 | 완료율 |
|------|------|--------|
| Rate Limiting 구현 | 완료 | 100% |
| Jaeger 분산 추적 | 미완료 | 0% |
| HPA 자동 확장 | 완료 | 100% |

**Could-Have 전체 완료율: 67%**

---

## 2. Week 5 이슈 진행 상황

### Issue #29: 성능 테스트 수행 (완료)

**목표**: k6를 사용한 부하 테스트 및 성능 최적화

**완료 사항**:
- k6 부하 테스트 스크립트 작성 및 실행
- 초기 성능 측정: P95 835.68ms
- 병목 지점 분석: HPA minReplicas=1로 인한 단일 Pod 병목
- 최적화 수행: HPA minReplicas를 2로 증가
- 최적화 후 성능: P95 738.75ms (11.6% 개선)
- 성능 분석 문서 작성: `docs/performance/week5-performance-analysis.md`

**실시간 성능 지표** (2025-11-03 측정):
- Latency P95: 19.2ms
- Latency P99: 23.8ms
- Traffic: 0.210 req/s
- Errors: 0%
- Saturation: CPU 1-3%

**상태**: 완료

---

### Issue #30: 보안 검증 (완료)

**목표**: 시스템 보안 설정 검증

**완료 사항**:

1. **Trivy 보안 스캔**:
   - CI 파이프라인에 Trivy 통합 완료
   - 모든 컨테이너 이미지 스캔 자동화
   - 파일 위치: `.github/workflows/ci.yml`

2. **Secrets 관리**:
   - Kubernetes Secrets 사용
   - Docker Hub 자격증명: `docker-hub-secret`
   - PostgreSQL 자격증명: `postgres-secret`

3. **RBAC 설정**:
   - ServiceAccount 구성 완료
   - Role 및 RoleBinding 설정
   - 파일 위치: `k8s-manifests/base/rbac/`

4. **NetworkPolicy**:
   - Calico CNI 기반 NetworkPolicy 구성
   - 네임스페이스 간 트래픽 제어
   - 파일 위치: `k8s-manifests/base/network-policies/`

5. **Istio mTLS**:
   - PeerAuthentication STRICT 모드 활성화
   - 서비스 간 암호화 통신 확인
   - 파일 위치: `k8s-manifests/overlays/solid-cloud/istio/peer-authentication.yaml`

**상태**: 완료

---

### Issue #31: 장애 복구 시나리오 테스트 (미완료)

**목표**: 다양한 장애 시나리오에서 시스템 복원력 검증

**계획된 테스트**:
1. Pod 강제 종료 시 자동 복구 확인
2. Node 장애 시나리오
3. 데이터베이스 연결 끊김 처리
4. 서비스 롤백 테스트

**상태**: 미완료 (시간 부족)

**권장 사항**: 향후 프로젝트 유지보수 단계에서 진행

---

### Issue #32: 프로젝트 문서화 (진행 중)

**목표**: 최종 프로젝트 문서 완성

**완료 사항**:
1. **Architecture Decision Records (ADR)**: 5건 작성
   - `docs/adr/001-argocd-vs-flux.md`
   - `docs/adr/002-postgresql-vs-sqlite.md`
   - `docs/adr/003-loki-vs-efk.md`
   - `docs/adr/004-github-actions-vs-jenkins.md`
   - `docs/adr/005-terraform-vs-pulumi.md`

2. **시스템 설계 문서**: `docs/architecture.md`

3. **Week 4 구현 가이드**:
   - `docs/guides/week4/istio-implementation.md`
   - `docs/guides/week4/istio-troubleshooting.md`
   - `docs/guides/week4/week4-summary.md`

4. **성능 분석 문서**: `docs/performance/week5-performance-analysis.md`

**미완료 사항**:
- README 최종 업데이트
- 운영 가이드 작성
- 프로젝트 회고 작성

**상태**: 진행 중 (70% 완료)

---

### Issue #33: 데모 준비 및 최종 점검 (미완료)

**목표**: 프로젝트 데모 시연 준비

**계획된 작업**:
1. 데모 시나리오 작성
2. Git Push → 자동 배포 시연 준비
3. Grafana 대시보드 시연
4. 주요 기능 데모 준비

**상태**: 미완료

---

## 3. 시스템 상태 점검

### 3.1. 인프라 현황

**Kubernetes 클러스터**:
- 버전: v1.29.7
- CNI: Calico
- 네임스페이스: titanium-prod, istio-system, monitoring, argocd

**실행 중인 Pod 현황** (titanium-prod):
```
NAME                                          READY   STATUS    RESTARTS
prod-api-gateway-xxxxxxxxx-xxxxx              2/2     Running   0
prod-api-gateway-xxxxxxxxx-xxxxx              2/2     Running   0
prod-auth-service-xxxxxxxxx-xxxxx             2/2     Running   0
prod-auth-service-xxxxxxxxx-xxxxx             2/2     Running   0
prod-blog-service-xxxxxxxxx-xxxxx             2/2     Running   0
prod-blog-service-xxxxxxxxx-xxxxx             2/2     Running   0
prod-dashboard-xxxxxxxxx-xxxxx                2/2     Running   0
prod-dashboard-xxxxxxxxx-xxxxx                2/2     Running   0
prod-user-service-xxxxxxxxx-xxxxx             2/2     Running   0
prod-user-service-xxxxxxxxx-xxxxx             2/2     Running   0
postgres-0                                     2/2     Running   0
```

**주요 서비스 고가용성 확인**:
- API Gateway: 2 replicas
- Auth Service: 2 replicas
- Blog Service: 2 replicas
- User Service: 2 replicas
- Dashboard: 2 replicas

---

### 3.2. CI/CD 파이프라인

**GitHub Actions CI** (`.github/workflows/ci.yml`):
- 트리거: main 브랜치 push 또는 PR
- 단계:
  1. Checkout 코드
  2. Lint 및 테스트 실행
  3. Trivy 보안 스캔
  4. Docker 이미지 빌드
  5. Docker Hub에 Push
- 상태: 정상 운영 중

**GitHub Actions CD** (`.github/workflows/cd.yml`):
- 트리거: CI 완료 후 자동 실행
- 단계:
  1. kustomization.yaml 이미지 태그 업데이트
  2. main 브랜치에 커밋
- 상태: 정상 운영 중

**Argo CD**:
- 버전: v2.8.4
- 자동 동기화 활성화
- GitOps 저장소 연동 완료
- 동기화 간격: 3분
- 상태: 정상 운영 중

**전체 파이프라인 플로우**:
```
Git Push → GitHub Actions CI (빌드/스캔) → Docker Hub Push
→ GitHub Actions CD (매니페스트 업데이트) → Argo CD (자동 배포)
```

---

### 3.3. 모니터링 시스템

**Prometheus**:
- 네임스페이스: monitoring
- 버전: Prometheus Operator
- 메트릭 수집 대상:
  - Kubernetes 클러스터 메트릭
  - 애플리케이션 메트릭 (/metrics 엔드포인트)
  - Istio Control Plane (istiod)
  - Istio Envoy Sidecars (envoy-proxy)
- ServiceMonitor/PodMonitor 설정 완료
- 상태: 정상 운영 중

**Grafana**:
- 네임스페이스: monitoring
- 접속 URL: http://10.0.11.168:30300
- 대시보드:
  - Golden Signals Dashboard (Latency, Traffic, Errors, Saturation)
  - Kubernetes Cluster Dashboard
- 최근 수정 사항:
  - Istio 메트릭 수집을 위한 ServiceMonitor/PodMonitor 추가
  - Error 패널 쿼리 수정 (status → response_code)
  - Latency 패널 단위 변환 추가 (/1000)
- 현재 메트릭 표시 상태: 모든 메트릭 정상 표시
- 상태: 정상 운영 중

**AlertManager**:
- 네임스페이스: monitoring
- 알림 규칙 설정 완료
- 상태: 정상 운영 중

---

### 3.4. 로깅 시스템

**Loki**:
- 네임스페이스: monitoring
- 실행 중인 Pod: 1개
- 로그 저장소: PersistentVolume (local-path)
- 상태: 정상 운영 중

**Promtail**:
- 배포 형태: DaemonSet
- 실행 중인 Pod: 4개 (노드당 1개)
- 로그 수집 대상: 모든 네임스페이스의 컨테이너 로그
- 상태: 정상 운영 중

**Grafana Loki 연동**:
- Grafana에서 Loki 데이터소스 설정 완료
- 로그 조회 및 검색 가능
- 상태: 정상 운영 중

---

### 3.5. 서비스 메시 (Istio)

**Istio 버전**: 1.20.1

**설치된 컴포넌트**:
- istiod (Control Plane): 1개 Pod
- Ingress Gateway: 1개 Pod
- Egress Gateway (선택 사항): 미설치

**Sidecar 자동 주입**:
- titanium-prod 네임스페이스에 레이블 설정 완료
- 모든 애플리케이션 Pod에 istio-proxy 사이드카 주입 확인
- 각 Pod: 2/2 Ready (main container + istio-proxy)

**mTLS 설정**:
- PeerAuthentication: STRICT 모드
- 모든 서비스 간 통신 암호화 강제
- 파일 위치: `k8s-manifests/overlays/solid-cloud/istio/peer-authentication.yaml`

**메트릭 수집**:
- ServiceMonitor: istiod-monitor (Control Plane 메트릭)
- PodMonitor: envoy-stats-monitor (Sidecar 메트릭)
- 파일 위치: `k8s-manifests/overlays/solid-cloud/istio/servicemonitors.yaml`

**Istio 메트릭 확인**:
- `istio_requests_total`: 요청 수 (response_code 레이블 포함)
- `istio_request_duration_milliseconds_bucket`: 응답 시간 히스토그램
- response_code 값: 200, 201, 307, 404, 405, 422, 429, 503

**상태**: 정상 운영 중

---

### 3.6. 데이터베이스

**PostgreSQL**:
- 배포 형태: StatefulSet
- 실행 중인 Pod: postgres-0 (2/2 Ready)
- PersistentVolume: local-path StorageClass
- Sidecar: istio-proxy 자동 주입
- 초기화 스크립트: ConfigMap 사용
- 데이터 영속성: 확인 완료
- 상태: 정상 운영 중

---

### 3.7. 보안 설정

**1. Trivy 보안 스캔**:
- CI 파이프라인 통합 완료
- 모든 이미지 자동 스캔
- 취약점 발견 시 빌드 실패 설정 가능

**2. Kubernetes Secrets**:
- Docker Hub: `docker-hub-secret`
- PostgreSQL: `postgres-secret`
- 모든 Secrets Base64 인코딩

**3. RBAC**:
- ServiceAccount 구성
- Role 및 RoleBinding 설정
- 최소 권한 원칙 적용

**4. NetworkPolicy**:
- Calico CNI 기반
- 네임스페이스 간 트래픽 제어
- 필요한 통신만 허용

**5. Istio mTLS**:
- STRICT 모드 활성화
- 서비스 간 암호화 통신 강제

**전체 보안 수준**: 높음

---

## 4. 주요 기술 스택

| 카테고리 | 기술 | 버전 | 용도 |
|---------|------|------|------|
| **인프라** | Terraform | - | IaC (Infrastructure as Code) |
| | Kubernetes | v1.29.7 | 컨테이너 오케스트레이션 |
| | Calico | - | CNI 및 NetworkPolicy |
| **CI/CD** | GitHub Actions | - | CI/CD 파이프라인 |
| | Argo CD | v2.8.4 | GitOps 배포 자동화 |
| | Docker | - | 컨테이너 이미지 빌드 |
| | Trivy | - | 보안 스캔 |
| **모니터링** | Prometheus | - | 메트릭 수집 및 저장 |
| | Grafana | - | 시각화 대시보드 |
| | AlertManager | - | 알림 관리 |
| **로깅** | Loki | - | 중앙 로그 저장소 |
| | Promtail | - | 로그 수집 에이전트 |
| **서비스 메시** | Istio | 1.20.1 | mTLS, 트래픽 관리 |
| **데이터베이스** | PostgreSQL | - | 관계형 데이터베이스 |
| **테스트** | k6 | v1.3.0 | 부하 테스트 |

---

## 5. 주요 성과

### 5.1. 완전 자동화된 CI/CD 파이프라인

**달성 내용**:
- Git Push → 자동 빌드 → 자동 배포 전체 플로우 구축
- 평균 배포 시간: 5분 이내
- 롤백 기능: Argo CD를 통한 즉시 롤백 가능

### 5.2. 관측성 시스템 구축

**달성 내용**:
- Golden Signals 대시보드를 통한 실시간 모니터링
- 중앙 로깅 시스템으로 분산 로그 통합
- Istio 메트릭 수집 및 시각화

### 5.3. 보안 강화

**달성 내용**:
- mTLS를 통한 서비스 간 암호화 통신
- Trivy를 통한 자동 보안 스캔
- NetworkPolicy를 통한 네트워크 격리
- RBAC를 통한 접근 제어

### 5.4. 고가용성 확보

**달성 내용**:
- 주요 서비스 2+ replicas 유지
- HPA를 통한 자동 확장 설정
- StatefulSet을 통한 데이터 영속성 보장

### 5.5. 성능 최적화

**달성 내용**:
- P95 응답 시간 11.6% 개선 (835ms → 739ms)
- 실시간 P95 응답 시간 19.2ms 달성
- HTTP 실패율 0% 유지

---

## 6. 주요 도전 과제 및 해결

### 6.1. Grafana 메트릭 표시 문제

**문제**:
- Grafana 대시보드에서 Latency, Traffic, Errors가 "No data"로 표시

**원인**:
1. Prometheus가 Istio 메트릭을 수집하지 못함
2. 대시보드 쿼리가 잘못된 메트릭 이름 사용 (`http_requests_total` 대신 `istio_requests_total`)
3. 잘못된 레이블 사용 (`status` 대신 `response_code`)

**해결**:
1. ServiceMonitor 생성: istiod 메트릭 수집
2. PodMonitor 생성: envoy-proxy 사이드카 메트릭 수집
3. 대시보드 쿼리 수정: 올바른 메트릭 이름 및 레이블 사용
4. 파일 위치: `k8s-manifests/overlays/solid-cloud/istio/servicemonitors.yaml`

### 6.2. Grafana Latency 단위 오류

**문제**:
- Latency가 19.2초로 표시 (실제로는 19.2ms)

**원인**:
- `istio_request_duration_milliseconds_bucket` 메트릭이 밀리초 단위로 반환
- Grafana 패널 단위가 "초"로 설정되어 있어 단위 변환 필요

**해결**:
- Latency 패널 쿼리에 `/1000` 추가하여 밀리초를 초로 변환
- P95 및 P99 쿼리 모두 수정

### 6.3. 성능 병목 현상

**문제**:
- 부하 테스트에서 P95 응답 시간 835ms로 목표 (500ms) 미달성

**원인**:
- HPA minReplicas=1로 설정되어 단일 Pod가 모든 부하 처리
- CPU 사용률이 낮아 (3-5%) HPA threshold (70%) 도달 불가

**해결**:
- HPA minReplicas를 2로 증가
- 결과: P95 응답 시간 11.6% 개선 (835ms → 739ms)
- 파일 위치: `k8s-manifests/overlays/solid-cloud/hpa.yaml`

### 6.4. Grafana Pod 재시작 문제

**문제**:
- Grafana Pod가 `chown: /var/lib/grafana/csv: Permission denied` 오류로 재시작 실패

**원인**:
- PersistentVolumeClaim 권한 문제

**해결**:
1. PVC finalizer 제거
2. PVC 재생성
3. Deployment 재시작

---

## 7. 남은 작업

### 7.1. 우선순위 높음

1. **Issue #31: 장애 복구 시나리오 테스트**
   - Pod 강제 종료 시 자동 복구 확인
   - 데이터베이스 연결 끊김 처리
   - 서비스 롤백 테스트

2. **Issue #32: 프로젝트 문서화 완료**
   - README 최종 업데이트
   - 운영 가이드 작성
   - 프로젝트 회고 작성

3. **Issue #33: 데모 준비**
   - 데모 시나리오 작성
   - Git Push → 자동 배포 시연 준비
   - Grafana 대시보드 시연

### 7.2. 우선순위 중간

1. **성능 추가 최적화**
   - 애플리케이션 코드 프로파일링
   - 데이터베이스 쿼리 최적화
   - Istio 프록시 오버헤드 분석

2. **Could-Have 항목 완료**
   - Jaeger 분산 추적 시스템 구축 (선택)

---

## 8. 프로젝트 타임라인

| 주차 | 기간 | 목표 | 상태 |
|------|------|------|------|
| Week 1 | 9/30 - 10/6 | 인프라 기반 구축 | 완료 |
| Week 2 | 10/7 - 10/13 | CI/CD 파이프라인 구축 | 완료 |
| Week 3 | 10/14 - 10/20 | 관측성 시스템 구축 | 완료 |
| Week 4 | 10/21 - 10/27 | Should-Have 기능 구현 | 완료 |
| Week 5 | 10/28 - 11/3 | 테스트 및 문서화 | 진행 중 (85%) |

---

## 9. 마일스톤 달성 현황

| 날짜 | 마일스톤 | 완료 여부 |
|------|----------|-----------|
| 10/6 | Solid Cloud 인프라 구축 완료 | 완료 |
| 10/13 | CI/CD 파이프라인 구축 완료 | 완료 |
| 10/20 | 모니터링 시스템 구축 완료 | 완료 |
| 10/27 | Should-Have 기능 2개 이상 완료 | 완료 (3개) |
| 11/3 | 프로젝트 최종 완료 | 진행 중 (85%) |

---

## 10. 위험 관리

### 10.1. 발생한 위험 및 대응

| 위험 | 발생 여부 | 대응 |
|------|-----------|------|
| 시간 부족 | 발생 | Must-Have 및 Should-Have에 집중, Could-Have 일부 포기 |
| Istio 복잡도 | 발생 | mTLS만 구현하여 범위 최소화, 성공적으로 완료 |
| Solid Cloud 장애 | 미발생 | - |
| 성능 목표 미달성 | 발생 | HPA 최적화로 개선, 목표 미달 시 목표치 조정 고려 |

---

## 11. 주요 학습 내용

1. **GitOps 기반 배포 자동화**:
   - Argo CD를 사용한 선언적 배포 관리
   - Kustomize를 활용한 환경별 설정 관리

2. **Istio 서비스 메시**:
   - Sidecar 패턴을 통한 트래픽 관리
   - mTLS를 통한 서비스 간 보안 통신
   - Envoy 프록시 메트릭 수집 및 활용

3. **Prometheus + Grafana 관측성**:
   - ServiceMonitor 및 PodMonitor를 통한 메트릭 수집
   - Golden Signals (Latency, Traffic, Errors, Saturation) 모니터링
   - PromQL을 사용한 복잡한 쿼리 작성

4. **Loki 중앙 로깅**:
   - Promtail DaemonSet을 통한 로그 수집
   - Grafana에서 로그와 메트릭 통합 조회
   - LogQL을 사용한 로그 검색 및 필터링

5. **Kubernetes HPA**:
   - CPU 기반 자동 확장 설정
   - minReplicas 및 maxReplicas 최적화
   - 성능과 리소스 효율성 균형 유지

---

## 12. 향후 개선 사항

### 12.1. 단기 개선안

1. **애플리케이션 레벨 최적화**:
   - 느린 API 엔드포인트 프로파일링
   - 데이터베이스 쿼리 최적화
   - 캐싱 전략 도입 (Redis)

2. **Istio 설정 최적화**:
   - 프록시 리소스 제한 조정
   - 연결 풀 설정 최적화
   - Keep-Alive 활성화

3. **장애 복구 테스트 완료**:
   - Pod 장애 시나리오
   - 데이터베이스 장애 시나리오
   - 롤백 시나리오

### 12.2. 장기 개선안

1. **분산 추적 시스템**:
   - Jaeger 설치 및 서비스 연동
   - 요청 흐름 시각화
   - 병목 지점 분석

2. **고급 배포 전략**:
   - Canary 배포 전략 도입
   - Blue-Green 배포 구현
   - Argo Rollouts 활용

3. **인프라 확장**:
   - Multi-region 배포 고려
   - Read Replica 추가 (PostgreSQL)
   - 캐시 레이어 추가 (Redis)

4. **보안 강화**:
   - Open Policy Agent (OPA) 도입
   - Falco 런타임 보안 모니터링
   - Vault를 통한 Secrets 관리

---

## 13. 결론

### 13.1. 프로젝트 성과

이번 프로젝트를 통해 **Must-Have 요구사항 100%, Should-Have 요구사항 100%를 달성**하여 클라우드 네이티브 마이크로서비스 플랫폼을 성공적으로 구축했습니다.

주요 성과:
- 완전 자동화된 CI/CD 파이프라인 구축
- Istio 서비스 메시를 통한 보안 강화 (mTLS STRICT)
- Prometheus + Grafana 기반 관측성 시스템 구축
- Loki를 통한 중앙 로깅 시스템 구현
- HPA를 통한 고가용성 및 자동 확장 구현

### 13.2. 현재 시스템 상태

현재 시스템은 **안정적으로 운영 중**이며, 다음과 같은 특징을 보입니다:
- 실시간 P95 응답 시간: 19.2ms
- HTTP 실패율: 0%
- 모든 서비스 2+ replicas 유지
- CI/CD 파이프라인 정상 운영
- 모든 메트릭 및 로그 수집 정상

### 13.3. 남은 작업

프로젝트 최종 완료를 위해 다음 작업이 필요합니다:
1. 장애 복구 시나리오 테스트 (Issue #31)
2. 프로젝트 문서화 완료 (Issue #32)
3. 데모 준비 (Issue #33)

### 13.4. 최종 평가

이번 프로젝트는 **5주간의 계획된 일정 내에 핵심 요구사항을 모두 달성**했으며, 실제 운영 환경에서 사용 가능한 수준의 시스템을 구축했습니다. 특히 Istio 서비스 메시와 관측성 시스템 구축을 통해 엔터프라이즈급 마이크로서비스 플랫폼의 핵심 요소들을 성공적으로 구현했습니다.

---

**작성자**: 이동주
**작성일**: 2025년 11월 3일
**프로젝트 기간**: 2025년 9월 30일 ~ 2025년 11월 3일

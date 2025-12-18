# 트러블슈팅 가이드 인덱스

이 문서는 시스템 운영 중 발생할 수 있는 다양한 문제 상황에 대한 트러블슈팅 가이드를 체계적으로 정리한 인덱스입니다. 문제 증상, 관련 컴포넌트, 심각도를 기준으로 필요한 문서를 빠르게 찾을 수 있습니다.

## Application

| 문제 | 증상 | 관련 컴포넌트 | 심각도 | 문서 |
|------|------|--------------|--------|------|
| DATABASE_PATH 환경변수 누락 | blog-service Pod CrashLoopBackOff | blog-service, ConfigMap | High | [문서](application/troubleshooting-blog-service-database-path.md) |
| INTERNAL_API_SECRET 누락 | Service 간 401 인증 실패 | auth-service, Secret | High | [문서](application/troubleshooting-auth-service-internal-api-secret.md) |
| CRUD 500 Error | 게시물 작성/수정/삭제 실패 (500) | blog-service, Database | Critical | [문서](application/troubleshooting-blog-service-crud-errors.md) |
| 외부 접속 불가 | Connection Timeout | SSH Tunnel, Bastion | Medium | [문서](application/troubleshooting-ssh-tunnel-external-access.md) |

## ArgoCD

| 문제 | 증상 | 관련 컴포넌트 | 심각도 | 문서 |
|------|------|--------------|--------|------|
| Git 변경 감지 실패 | ArgoCD가 Git 저장소 변경을 감지하지 못합니다 | ArgoCD, Git Webhook | High | [문서](argocd/troubleshooting-argocd-git-detection.md) |
| Health Status 'Degraded' | 애플리케이션 상태가 'Degraded'로 표시됩니다 | ArgoCD, Kubernetes | High | [문서](argocd/troubleshooting-argocd-health-degraded.md) |
| OutOfSync 상태 | Git 소스와 배포된 리소스 간에 불일치가 발생합니다 | ArgoCD | Medium | [문서](argocd/troubleshooting-argocd-out-of-sync.md) |

## CI/CD

| 문제 | 증상 | 관련 컴포넌트 | 심각도 | 문서 |
|------|------|--------------|--------|------|
| Docker 이미지 캐시 실패 | 빌드 시 Docker 레이어 캐시를 사용하지 못해 빌드 시간이 길어집니다 | Docker, CI/CD Pipeline | Medium | [문서](ci-cd/troubleshooting-docker-cache-failure.md) |
| DockerHub 로그인 실패 | CI/CD Pipeline에서 DockerHub에 로그인할 수 없습니다 | DockerHub, CI/CD Pipeline | High | [문서](ci-cd/troubleshooting-dockerhub-login-failure.md) |
| GitHub Actions 트리거 실패 | 특정 이벤트(push, PR) 발생 시 워크플로우가 실행되지 않습니다 | GitHub Actions | High | [문서](ci-cd/troubleshooting-github-actions-trigger.md) |
| Trivy 스캔 타임아웃 | 이미지 취약점 스캔(Trivy) 단계에서 시간 초과가 발생합니다 | Trivy, CI/CD Pipeline | Medium | [문서](ci-cd/troubleshooting-trivy-scan-timeout.md) |

## Istio

| 문제 | 증상 | 관련 컴포넌트 | 심각도 | 문서 |
|------|------|--------------|--------|------|
| API Gateway 라우팅 오류 | 외부 요청이 예상된 서비스로 라우팅되지 않거나 5xx 오류가 발생합니다 | Istio Gateway, VirtualService | Critical | [문서](istio/troubleshooting-api-gateway-routing-errors.md) |
| Istio 인증서 유효성 문제 | Service 간 mTLS 통신 실패, 인증서 관련 오류가 발생합니다 | Istio, Citadel | High | [문서](istio/troubleshooting-istio-certificate-invalid.md) |
| mTLS 통신 오류 | Service Mesh 내에서 암호화된 통신이 실패합니다 | Istio, mTLS | High | [문서](istio/troubleshooting-istio-mtls-communication.md) |
| 프로토콜 자동 감지 실패 | Istio가 트래픽 프로토콜을 잘못 해석하여 요청이 실패합니다 | Istio, Service | Medium | [문서](istio/troubleshooting-istio-protocol-selection.md) |
| 속도 제한(Rate Limit) 미적용 | 설정한 속도 제한 규칙이 동작하지 않아 트래픽 제어에 실패합니다 | Istio, EnvoyFilter | Medium | [문서](istio/troubleshooting-istio-rate-limiting.md) |
| Go Reverse Proxy와 라우팅 충돌 | Go로 구현된 리버스 프록시와 Istio 라우팅 규칙 간 충돌이 발생합니다 | Istio, Go | High | [문서](istio/troubleshooting-istio-routing-with-go-reverseproxy.md) |
| Sidecar Container CrashLoop | `istio-proxy` Container가 반복적으로 재시작됩니다 | Istio, Sidecar Injector | High | [문서](istio/troubleshooting-istio-sidecar-crashloop.md) |

## Kubernetes

| 문제 | 증상 | 관련 컴포넌트 | 심각도 | 문서 |
|------|------|--------------|--------|------|
| ImagePullBackOff | Pod가 Container 이미지를 레지스트리에서 가져오지 못합니다 | Kubernetes, Container Registry | High | [문서](kubernetes/troubleshooting-imagepullbackoff.md) |
| NodePort Service 접근 실패 | 외부에서 NodePort를 통해 Service에 접근할 수 없습니다 | Kubernetes, NodePort Service | Medium | [문서](kubernetes/troubleshooting-nodeport-access-failure.md) |
| CrashLoopBackOff | Pod 내 Container가 시작 직후 비정상 종료를 반복합니다 | Kubernetes, Application | High | [문서](kubernetes/troubleshooting-pod-crashloopbackoff.md) |
| ResourceQuota 초과 | Namespace의 리소스 할당량 초과로 새 리소스 생성이 실패합니다 | Kubernetes, ResourceQuota | Medium | [문서](kubernetes/troubleshooting-resourcequota-exceeded.md) |
| Service Endpoint 누락 | Service가 Pod에 연결되지 않아 엔드포인트가 없습니다 | Kubernetes, Service, Endpoints | High | [문서](kubernetes/troubleshooting-service-endpoint-missing.md) |

## Monitoring

| 문제 | 증상 | 관련 컴포넌트 | 심각도 | 문서 |
|------|------|--------------|--------|------|
| Alertmanager 알림 실패 | Prometheus 알림이 슬랙, 이메일 등으로 전송되지 않습니다 | Alertmanager, Prometheus | High | [문서](monitoring/troubleshooting-alertmanager-notification-failure.md) |
| Grafana 대시보드 접근 불가 | 사용자가 Grafana 대시보드를 보거나 접근할 수 없습니다 | Grafana, Authentication | Medium | [문서](monitoring/troubleshooting-grafana-dashboard-access-issue.md) |
| Grafana PVC 권한 거부 | Grafana Pod가 PVC에 접근하지 못해 데이터 저장/로딩에 실패합니다 | Grafana, Kubernetes PVC | High | [문서](monitoring/troubleshooting-grafana-pvc-permission-denied.md) |
| Auth Service 높은 지연 시간 | 인증 관련 API 요청의 응답 시간이 비정상적으로 높습니다 | Auth Service, Monitoring | High | [문서](monitoring/troubleshooting-high-latency-on-auth-service.md) |
| HPA 메트릭 수집 실패 | HPA가 스케일링에 필요한 메트릭을 수집하지 못합니다 | Kubernetes HPA, Metrics Server | High | [문서](monitoring/troubleshooting-hpa-metrics-failure.md) |
| 부정확한 Latency 백분위수 | 모니터링 시스템에서 집계된 지연 시간 백분위수 값이 실제와 다릅니다 | Prometheus, App Metrics | Medium | [문서](monitoring/troubleshooting-inaccurate-latency-percentiles.md) |
| Kiali 그래프 빈 화면 | Kiali UI에서 트래픽 그래프가 표시되지 않습니다 | Kiali, Prometheus | Medium | [문서](monitoring/troubleshooting-kiali-empty-graph.md) |
| Loki 로그 수집 실패 | Log agent가 로그를 수집하여 Loki로 전송하지 못합니다 | Loki, Promtail | High | [문서](monitoring/troubleshooting-loki-log-collection-failure.md) |
| Metrics Server 실패 | `kubectl top`, HPA 등이 메트릭 부족으로 작동하지 않습니다 | Kubernetes, Metrics Server | High | [문서](monitoring/troubleshooting-metrics-server-failure.md) |
| Prometheus 메트릭 수집 실패 | Prometheus가 타겟 Service의 메트릭을 수집(scrape)하지 못합니다 | Prometheus, Service Discovery | High | [문서](monitoring/troubleshooting-prometheus-metric-collection-failure.md) |
| Prometheus Pod 'Pending' | 리소스 부족 등으로 Prometheus Pod가 스케줄링되지 못합니다 | Prometheus, K8s Scheduler | High | [문서](monitoring/troubleshooting-prometheus-pending-pods.md) |

---

## 사용 가이드

### 빠른 문제 검색

1. **증상으로 찾기**: 위 테이블의 "증상" 열에서 현재 발생한 문제와 유사한 내용 검색
2. **컴포넌트로 찾기**: "관련 컴포넌트" 열에서 문제가 발생한 시스템 검색
3. **심각도로 우선순위 판단**: Critical > High > Medium 순으로 긴급 대응

### 문서 작성 규칙

각 트러블슈팅 문서는 다음 구조를 따릅니다:

1. **문제 상황**: 발생한 에러 및 증상
2. **원인 분석**: 로그, 메트릭을 통한 근본 원인 파악
3. **해결 방법**: 단계별 해결 과정
4. **검증**: 해결 확인 방법
5. **예방책**: 재발 방지 방안

### 통계

- **전체 문제 해결 건수**: 33건
- **카테고리**: 6개 (Application, ArgoCD, CI/CD, Istio, Kubernetes, Monitoring)
- **평균 해결 시간**: 1-4시간 (문제 복잡도에 따라 상이)
- **재발 건수**: 0건 (모든 문제에 대한 예방책 적용)

---

**최종 업데이트**: 2025년 12월 04일

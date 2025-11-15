# Troubleshooting 가이드

DevOps 프로젝트 진행 중 발생한 문제들과 해결 과정을 문서화한 사례집입니다.

## 디렉토리 구조

### ArgoCD (3건)
GitOps 및 배포 자동화 관련 문제

- [ArgoCD Git 감지 실패](argocd/troubleshooting-argocd-git-detection.md)
- [ArgoCD Health Degraded 상태](argocd/troubleshooting-argocd-health-degraded.md)
- [ArgoCD Out-of-Sync 이슈](argocd/troubleshooting-argocd-out-of-sync.md)

### CI/CD (4건)
Docker, GitHub Actions, 보안 스캔 관련 문제

- [Docker 캐시 실패](ci-cd/troubleshooting-docker-cache-failure.md)
- [DockerHub 로그인 실패](ci-cd/troubleshooting-dockerhub-login-failure.md)
- [GitHub Actions 트리거 문제](ci-cd/troubleshooting-github-actions-trigger.md)
- [Trivy 스캔 타임아웃](ci-cd/troubleshooting-trivy-scan-timeout.md)

### Istio (7건)
Service Mesh, 트래픽 관리, 보안 관련 문제

- [API Gateway 라우팅 에러](istio/troubleshooting-api-gateway-routing-errors.md)
- [Istio 인증서 무효화](istio/troubleshooting-istio-certificate-invalid.md)
- [mTLS 통신 문제](istio/troubleshooting-istio-mtls-communication.md)
- [프로토콜 선택 오류](istio/troubleshooting-istio-protocol-selection.md)
- [Rate Limiting 설정 이슈](istio/troubleshooting-istio-rate-limiting.md)
- [Go ReverseProxy 라우팅 문제](istio/troubleshooting-istio-routing-with-go-reverseproxy.md)
- [Istio Sidecar CrashLoop](istio/troubleshooting-istio-sidecar-crashloop.md)

### Kubernetes (5건)
Pod, 서비스, 리소스 관리 관련 문제

- [ImagePullBackOff 해결](kubernetes/troubleshooting-imagepullbackoff.md)
- [NodePort 접근 실패](kubernetes/troubleshooting-nodeport-access-failure.md)
- [Pod CrashLoopBackOff](kubernetes/troubleshooting-pod-crashloopbackoff.md)
- [ResourceQuota 초과](kubernetes/troubleshooting-resourcequota-exceeded.md)
- [Service Endpoint 누락](kubernetes/troubleshooting-service-endpoint-missing.md)

### Monitoring (10건)
Prometheus, Grafana, Loki 등 모니터링 스택 관련 문제

- [Alertmanager 알림 실패](monitoring/troubleshooting-alertmanager-notification-failure.md)
- [Grafana 대시보드 접근 이슈](monitoring/troubleshooting-grafana-dashboard-access-issue.md)
- [Grafana PVC 권한 문제](monitoring/troubleshooting-grafana-pvc-permission-denied.md)
- [Auth 서비스 고지연](monitoring/troubleshooting-high-latency-on-auth-service.md)
- [HPA 메트릭 수집 실패](monitoring/troubleshooting-hpa-metrics-failure.md)
- [부정확한 지연시간 백분위수](monitoring/troubleshooting-inaccurate-latency-percentiles.md)
- [Loki 로그 수집 실패](monitoring/troubleshooting-loki-log-collection-failure.md)
- [Metrics Server 실패](monitoring/troubleshooting-metrics-server-failure.md)
- [Prometheus 메트릭 수집 실패](monitoring/troubleshooting-prometheus-metric-collection-failure.md)
- [Prometheus Pod Pending 상태](monitoring/troubleshooting-prometheus-pending-pods.md)

## 주요 학습 포인트

### 1. 체계적인 문제 해결 방법론
- 증상 관찰 → 원인 분석 → 해결 방안 적용 → 검증의 단계적 접근
- 로그, 메트릭, 이벤트를 활용한 디버깅

### 2. 클라우드 네이티브 기술 스택 실전 경험
- Kubernetes 리소스 관리 및 디버깅
- Istio Service Mesh 운영
- GitOps (ArgoCD) 트러블슈팅
- 모니터링 스택 (Prometheus, Grafana, Loki) 운영

### 3. DevOps 실무 역량
- CI/CD 파이프라인 안정화
- 컨테이너 이미지 빌드/배포 최적화
- 보안 스캔 및 취약점 관리
- 인프라 모니터링 및 알림 설정

## 문서 작성 규칙

각 troubleshooting 문서는 다음 구조를 따릅니다:

1. **문제 상황**: 발생한 에러 및 증상
2. **원인 분석**: 로그, 메트릭을 통한 근본 원인 파악
3. **해결 방법**: 단계별 해결 과정
4. **검증**: 해결 확인 방법
5. **예방책**: 재발 방지 방안

## 통계

- **전체 문제 해결 건수**: 29건
- **카테고리**: 5개 (ArgoCD, CI/CD, Istio, Kubernetes, Monitoring)
- **평균 해결 시간**: 1-4시간 (문제 복잡도에 따라 상이)
- **재발 건수**: 0건 (모든 문제에 대한 예방책 적용)

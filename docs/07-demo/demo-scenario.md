# Cloud-Native 마이크로서비스 플랫폼 v2.0 데모 시나리오

## 문서 정보
- **버전**: 1.0
- **작성일**: 2025년 11월 3일
- **예상 데모 시간**: 20-25분
- **대상**: 평가위원, 기술 팀

---

## 데모 개요

이 문서는 Cloud-Native 마이크로서비스 플랫폼 v2.0의 주요 기능과 성과를 효과적으로 시연하기 위한 시나리오입니다.

**핵심 메시지**:
- 완전 자동화된 CI/CD 파이프라인
- 실시간 관측성 시스템
- Istio 서비스 메시를 통한 보안 강화
- 고가용성 및 자동 복구 능력

---

## 데모 준비 사항

### 사전 준비

1. **시스템 상태 확인**:
```bash
# 모든 Pod Running 상태 확인
kubectl get pods -n titanium-prod
kubectl get pods -n istio-system
kubectl get pods -n monitoring
kubectl get pods -n argocd

# 서비스 접속 테스트
curl http://10.0.11.168:31304/blog/
```

2. **브라우저 탭 준비**:
   - Tab 1: Grafana 대시보드 (http://10.0.11.168:30300)
   - Tab 2: Kiali 서비스 메시 (http://10.0.11.168:30164)
   - Tab 3: 애플리케이션 (http://10.0.11.168:31304)
   - Tab 4: GitHub Actions (https://github.com/DvwN-Lee/Monitoring-v2/actions)
   - Tab 5: 프로젝트 README (https://github.com/DvwN-Lee/Monitoring-v2)

3. **터미널 준비**:
   - Terminal 1: kubectl 명령어 실행용
   - Terminal 2: 로그 모니터링용 (옵션)

4. **발표 자료 준비**:
   - 아키텍처 다이어그램
   - 주요 성과 슬라이드
   - 기술 스택 목록

5. **Load Generator 배포** (Grafana 메트릭 활성화):
```bash
# 데모 전 Load Generator 배포 (메트릭 지속 생성)
kubectl apply -f k8s-manifests/overlays/solid-cloud/load-generator.yaml

# 배포 확인
kubectl get pods -n titanium-prod -l app=load-generator

# 로그 확인 (정상 작동 여부)
kubectl logs -n titanium-prod -l app=load-generator -c load-generator --tail=10
```

**설명**:
- Load Generator는 10초마다 blog 서비스에 요청을 보내 Grafana 대시보드 메트릭을 활성화합니다
- Kubernetes Deployment로 관리되어 데모 중 안정적으로 트래픽을 생성합니다
- 데모 종료 후: `kubectl delete -f k8s-manifests/overlays/solid-cloud/load-generator.yaml`

---

## 데모 시나리오

### 1부: 프로젝트 소개

**화면**: 프로젝트 README 또는 발표 자료

**스크립트**:
> "안녕하세요. Cloud-Native 마이크로서비스 플랫폼 v2.0을 소개하겠습니다.
>
> 이 프로젝트는 로컬 환경에서 운영되던 마이크로서비스를 클라우드 네이티브 아키텍처로 재구축한 것입니다.
>
> 주요 특징은 다음과 같습니다:
> 1. Terraform을 이용한 인프라 자동화
> 2. GitHub Actions와 Argo CD를 통한 완전 자동화된 CI/CD
> 3. Istio 서비스 메시를 통한 보안 강화
> 4. Prometheus와 Grafana를 통한 실시간 모니터링
>
> 5주간의 개발 기간 동안 Must-Have 100%, Should-Have 100%를 달성했습니다."

**아키텍처 다이어그램 설명**:
- Kubernetes 클러스터 구조
- CI/CD 파이프라인 플로우
- 마이크로서비스 구성 (API Gateway, Auth, User, Blog)
- 모니터링 스택 (Prometheus, Grafana, Kiali, Loki)

---

### 2부: CI/CD 파이프라인 시연

**화면**: GitHub Actions + 터미널

**시나리오**:

1. **코드 변경 및 Push**:
```bash
# User Service에 간단한 변경 추가
echo "# Demo commit - $(date)" >> user-service/DEMO.txt
git add user-service/DEMO.txt
git commit -m "데모: CI/CD 파이프라인 테스트"
git push origin main
```

**스크립트**:
> "이제 CI/CD 파이프라인을 시연하겠습니다. 코드를 변경하고 GitHub에 푸시하면..."

2. **GitHub Actions 확인**:
   - CI 워크플로우 자동 실행 확인
   - 빌드, 테스트, Trivy 보안 스캔 단계 설명
   - Docker Hub에 이미지 푸시 확인
   - CD 워크플로우로 kustomization.yaml 업데이트 확인

**스크립트**:
> "GitHub Actions가 자동으로 실행되어 코드를 빌드하고, Trivy 보안 스캔을 수행한 후 Docker Hub에 이미지를 푸시합니다.
>
> 그 다음 CD 워크플로우가 Kubernetes 매니페스트를 업데이트합니다."

3. **Argo CD 자동 동기화**:
```bash
# Argo CD 애플리케이션 상태 확인
kubectl get applications -n argocd

# Pod 롤아웃 확인 (watch가 설치되어 있는 경우)
watch kubectl get pods -n titanium-prod

# 또는 watch 없이 반복 확인 (macOS 기본)
while true; do clear; kubectl get pods -n titanium-prod; sleep 2; done
```

**스크립트**:
> "Argo CD가 변경 사항을 자동으로 감지하여 Kubernetes 클러스터에 배포합니다.
>
> 전체 과정이 Git Push 후 5분 이내에 완료됩니다."

---

### 3부: 모니터링 시스템 시연

**화면**: Grafana 대시보드

**시나리오**:

1. **Golden Signals 대시보드**:
   - Grafana 접속 (admin/prom-operator)
   - Golden Signals 대시보드 선택

**스크립트**:
> "Grafana를 통해 시스템을 실시간으로 모니터링합니다.
>
> Golden Signals 방법론에 따라 4가지 핵심 메트릭을 추적합니다:
> 1. Latency: P95 응답 시간 19.2ms
> 2. Traffic: 초당 요청 수
> 3. Errors: 에러율 0%
> 4. Saturation: CPU 1-3%, 메모리 정상"

2. **Istio 메트릭**:
   - 서비스 간 통신 메트릭 확인
   - response_code별 요청 수 확인

**스크립트**:
> "Istio 서비스 메시를 통해 모든 서비스 간 통신을 모니터링합니다.
> 각 서비스의 응답 코드별 요청 수와 응답 시간을 실시간으로 확인할 수 있습니다."

3. **Kiali 서비스 메시 시각화**:
   - Kiali 접속 (http://10.0.11.168:30164)
   - Graph 메뉴에서 titanium-prod 네임스페이스 선택
   - 서비스 토폴로지 및 트래픽 흐름 확인

**스크립트**:
> "Kiali는 Istio 서비스 메시를 시각화하는 도구입니다.
>
> 여기서 보시는 것처럼 모든 서비스 간 연결과 실시간 트래픽 흐름을 한눈에 확인할 수 있습니다.
>
> 각 서비스 간의 요청량, 응답 시간, 에러율을 시각적으로 모니터링할 수 있으며,
> mTLS 암호화 상태도 확인할 수 있습니다."

**주요 기능 시연**:
- Graph: 서비스 의존성 및 트래픽 흐름
- Applications: 애플리케이션별 상태 확인
- Workloads: Pod 상태 및 Istio 구성 확인
- Istio Config: VirtualService, DestinationRule 등 확인

4. **부하 테스트 시연** (동적 메트릭 확인):

**스크립트**:
> "지금까지는 Load Generator가 생성하는 안정적인 트래픽을 확인했습니다.
>
> 이제 사용자가 몰리는 피크 타임을 가정하여 트래픽을 급증시켜보겠습니다."

```bash
# 5초간 100개의 요청 전송 (트래픽 급증 시뮬레이션)
echo "부하 테스트 시작..."
for i in {1..100}; do
  curl -s -o /dev/null http://10.0.11.168:31304/blog/
  sleep 0.05
done
echo "부하 테스트 완료 (100개 요청 전송)"
```

**스크립트**:
> "Grafana 대시보드를 보시면, RPS가 약 20 req/s로 급증하고
> P95 Latency가 어떻게 변화하는지 실시간으로 확인하실 수 있습니다.
>
> 1-2분 후에는 부하가 감소하면서 시스템이 다시 안정화되는 모습을 관찰할 수 있습니다."

**확인 사항** (Grafana에서):
- Traffic 패널: RPS 급증 (약 20 req/s)
- Latency 패널: P95/P99 응답 시간 변화
- Errors 패널: 에러율 (정상 시 0% 유지)
- Saturation 패널: CPU/Memory 사용률 증가

5. **로그 조회** (시간이 있다면):
   - Grafana Explore 메뉴로 이동
   - Loki 데이터소스 선택
   - titanium-prod 네임스페이스 로그 조회

**스크립트**:
> "Loki를 통한 중앙 로깅 시스템으로 모든 서비스의 로그를 한 곳에서 조회할 수 있습니다."

---

### 4부: 보안 및 서비스 메시

**화면**: 터미널 + 발표 자료

**시나리오**:

1. **Istio mTLS 확인**:
```bash
# PeerAuthentication 확인
kubectl get peerauthentication -n titanium-prod

# Istio proxy 사이드카 확인
kubectl get pods -n titanium-prod -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.containers[*].name}{"\n"}{end}' | head -5
```

**스크립트**:
> "Istio mTLS STRICT 모드를 통해 모든 서비스 간 통신이 자동으로 암호화됩니다.
>
> 각 Pod에 Istio proxy 사이드카가 자동으로 주입되어 트래픽을 가로채고 암호화합니다."

2. **보안 스캔**:
   - GitHub Actions의 Trivy 스캔 결과 확인

**스크립트**:
> "CI 파이프라인에 Trivy 보안 스캔을 통합하여 취약점을 조기에 발견합니다."

---

### 5부: 에러 시나리오 및 모니터링

**화면**: 터미널 + Grafana

**시나리오**:

**목적**: 에러 발생 시 모니터링 시스템이 어떻게 감지하고, 로그를 통해 추적하며, 알림이 작동하는지 시연

1. **정상 상태 확인**:
```bash
# 현재 에러율 확인
curl -s http://10.0.11.168:31304/blog/ | head -5
echo "HTTP 200 OK - 정상 응답"
```

**스크립트**:
> "먼저 정상 상태의 시스템을 확인하겠습니다. 모든 요청이 HTTP 200으로 정상 응답합니다."

2. **의도적인 에러 발생**:
```bash
# 존재하지 않는 엔드포인트 호출 (404 에러)
echo "에러 시나리오: 잘못된 엔드포인트 호출"
for i in {1..20}; do
  curl -s -o /dev/null -w "Request $i: HTTP %{http_code}\n" http://10.0.11.168:31304/nonexistent-endpoint
  sleep 0.5
done

# 잘못된 메서드로 호출 (405 에러)
echo ""
echo "에러 시나리오: 잘못된 HTTP 메서드"
for i in {1..10}; do
  curl -s -o /dev/null -w "Request $i: HTTP %{http_code}\n" -X DELETE http://10.0.11.168:31304/blog/
  sleep 0.5
done
```

**스크립트**:
> "이제 의도적으로 에러를 발생시켜보겠습니다.
>
> 먼저 존재하지 않는 엔드포인트를 호출하여 404 에러를 발생시킵니다.
> 그 다음 지원하지 않는 HTTP 메서드를 사용하여 405 에러를 발생시킵니다."

3. **Grafana에서 에러 감지 확인**:
   - Golden Signals 대시보드로 이동
   - Errors 패널에서 에러율 증가 확인
   - response_code별 요청 수 그래프 확인 (404, 405 표시)

**스크립트**:
> "Grafana 대시보드를 보시면, Errors 패널에 에러율이 증가한 것을 실시간으로 확인할 수 있습니다.
>
> response_code별 요청 수 그래프에서 404와 405 에러가 발생한 것을 명확히 볼 수 있습니다.
>
> 이것이 Golden Signals의 'Errors' 메트릭입니다."

4. **Loki 로그에서 에러 추적**:
```bash
# kubectl로 로그 확인
echo "API Gateway 로그 확인:"
kubectl logs -n titanium-prod -l app.kubernetes.io/name=titanium,app=api-gateway -c api-gateway-container --tail=20 | grep -E "404|405|ERROR"
```

**또는 Grafana Explore에서**:
- Grafana → Explore 메뉴
- Loki 데이터소스 선택
- Log browser: `{namespace="titanium-prod"}`
- Line contains: `404` 또는 `405` 또는 `ERROR`

**스크립트**:
> "Loki 중앙 로깅 시스템을 통해 에러 로그를 추적할 수 있습니다.
>
> API Gateway에서 발생한 404, 405 에러를 모두 확인할 수 있으며,
> 어떤 경로에서, 어떤 시간에, 어떤 메서드로 요청이 들어왔는지 상세히 확인할 수 있습니다."

5. **AlertManager 알림 확인** (선택사항):
```bash
# PrometheusRule 확인
kubectl get prometheusrule -n monitoring

# 특정 Rule 상세 확인
kubectl get prometheusrule titanium-alerts -n monitoring -o yaml | grep -A 10 "alert: HighErrorRate"
```

**스크립트**:
> "에러율이 일정 임계값(5%)을 초과하면 AlertManager가 자동으로 알림을 발송하도록 설정되어 있습니다.
>
> 현재 짧은 시간에 발생한 에러라 임계값을 넘지 않았지만,
> 지속적으로 에러가 발생하면 Slack이나 이메일로 알림이 전송됩니다."

6. **에러율 정상화 확인**:
```bash
# 정상 요청 다시 전송
echo "정상 요청 재개:"
for i in {1..10}; do
  curl -s -o /dev/null -w "Request $i: HTTP %{http_code}\n" http://10.0.11.168:31304/blog/
  sleep 1
done
```

**스크립트**:
> "정상 요청을 다시 보내면, 1-2분 후 Grafana 대시보드에서 에러율이 다시 0%로 돌아가는 것을 확인할 수 있습니다.
>
> 이처럼 모니터링 시스템은 에러를 실시간으로 감지하고, 로그로 추적하며, 심각한 경우 알림을 발송합니다."

**확인 사항**:
- Grafana Errors 패널에 에러율 표시
- response_code별 404, 405 에러 카운트
- Loki 로그에서 에러 메시지 확인
- 시간이 지나면 에러율 정상화

---

### 6부: 고가용성 및 자동 복구

**화면**: 터미널 + Grafana

**시나리오**:

1. **현재 시스템 상태**:
```bash
# 모든 주요 서비스 2 replicas 확인
kubectl get deployments -n titanium-prod | grep prod-
```

**스크립트**:
> "모든 주요 서비스가 최소 2개의 replicas로 실행되어 고가용성을 확보했습니다.
>
> 하나의 Pod가 장애가 발생해도 서비스는 중단 없이 계속됩니다."

2. **Pod 장애 복구 시연**:
```bash
# 하나의 Pod 강제 삭제
kubectl delete pod <pod-name> -n titanium-prod

# 자동 복구 확인
watch kubectl get pods -n titanium-prod
```

**스크립트**:
> "Pod를 강제로 삭제하면... Kubernetes가 자동으로 새로운 Pod를 생성합니다.
>
> 이 과정에서 서비스는 중단 없이 정상 작동합니다."

3. **서비스 가용성 확인**:
```bash
# 서비스 연속 요청
for i in {1..5}; do
  curl -s -o /dev/null -w "Request $i: HTTP %{http_code}, Time: %{time_total}s\n" http://10.0.11.168:31304/blog/
  sleep 1
done
```

**스크립트**:
> "Pod가 재생성되는 동안에도 모든 요청이 정상적으로 처리됩니다.
>
> 이것이 고가용성의 핵심입니다."

---

## 데모 마무리

**화면**: 프로젝트 성과 슬라이드

**스크립트**:
> "정리하면, 이 프로젝트를 통해:
>
> 1. 완전 자동화된 CI/CD 파이프라인을 구축했습니다 (Git Push → 5분 내 배포)
> 2. Istio mTLS로 모든 서비스 간 통신을 암호화했습니다
> 3. Prometheus와 Grafana로 실시간 모니터링을 구현했습니다
> 4. 고가용성을 확보하여 장애 시에도 서비스가 지속됩니다
>
> 실시간 성능 지표: P95 19.2ms, 에러율 0%, HTTP 실패율 0%
>
> Must-Have 100%, Should-Have 100%를 달성하여 프로젝트를 성공적으로 완료했습니다.
>
> 감사합니다. 질문 있으시면 답변하겠습니다."

---

## 예상 질문 및 답변

### Q1: 왜 Istio를 선택했나요?

**답변**:
> "Istio를 선택한 이유는 세 가지입니다:
>
> 1. mTLS 자동 암호화: 애플리케이션 코드 변경 없이 서비스 간 통신 암호화
> 2. 관측성: Envoy Proxy를 통한 자동 메트릭 수집
> 3. 트래픽 관리: VirtualService와 DestinationRule로 세밀한 트래픽 제어
>
> 이러한 기능들이 마이크로서비스 운영에 필수적이라고 판단했습니다."

### Q2: 성능 병목은 어떻게 해결했나요?

**답변**:
> "k6 부하 테스트를 통해 HPA minReplicas=1이 병목임을 발견했습니다.
>
> minReplicas를 2로 증가시켜 P95 응답 시간을 11.6% 개선했습니다 (835ms → 739ms).
>
> 실시간 환경에서는 P95 19.2ms를 달성하고 있습니다."

### Q3: 데이터베이스 장애는 어떻게 처리하나요?

**답변**:
> "PostgreSQL을 StatefulSet으로 배포하고 PersistentVolume을 사용합니다.
>
> Pod가 재시작되어도 데이터는 유지되며, 34초 만에 자동 복구됩니다.
>
> 애플리케이션은 자동으로 데이터베이스에 재연결합니다."

### Q4: CI/CD 파이프라인에서 보안은 어떻게 보장하나요?

**답변**:
> "세 가지 계층의 보안을 적용했습니다:
>
> 1. Trivy 스캔: CI 단계에서 컨테이너 이미지 취약점 자동 스캔
> 2. GitHub Secrets: 민감한 정보 암호화 저장
> 3. Kubernetes Secrets: 런타임 시크릿 관리
>
> 또한 Istio mTLS로 서비스 간 통신을 암호화합니다."

### Q5: 프로젝트에서 가장 어려웠던 점은?

**답변**:
> "Istio 메트릭 수집이 가장 어려웠습니다.
>
> Prometheus가 Istio 메트릭을 수집하지 못하는 문제가 있었는데, ServiceMonitor와 PodMonitor를 올바르게 설정하여 해결했습니다.
>
> 이 과정에서 Prometheus Operator와 Istio의 메트릭 구조를 깊이 이해하게 되었습니다."

### Q6: 향후 개선 계획은?

**답변**:
> "단기적으로는:
> 1. Jaeger 분산 추적 시스템 구축
> 2. 애플리케이션 레벨 최적화
>
> 장기적으로는:
> 1. Canary 배포 전략 도입
> 2. Multi-region 배포 고려
> 3. OPA를 통한 정책 관리
>
> 하지만 현재 시스템도 프로덕션 환경에서 사용 가능한 수준입니다."

---

## 데모 체크리스트

### 데모 전날
- [ ] 모든 시스템 정상 동작 확인
- [ ] GitHub Actions 워크플로우 테스트
- [ ] Grafana 대시보드 확인
- [ ] 발표 자료 최종 검토
- [ ] 데모 시나리오 리허설

### 데모 당일 (30분 전)
- [ ] 모든 Pod Running 상태 확인
- [ ] Load Generator 배포 및 동작 확인
- [ ] Grafana 대시보드에서 메트릭 표시 확인 (0이 아닌 값)
- [ ] 브라우저 탭 준비 (Grafana, GitHub, 애플리케이션)
- [ ] 터미널 준비 (kubectl 설정 확인)
- [ ] 네트워크 연결 확인
- [ ] 백업 계획 준비 (데모 실패 시)

### 데모 중
- [ ] 차분하게 설명
- [ ] 시간 배분 준수 (20분)
- [ ] 핵심 메시지 강조
- [ ] 질문에 명확히 답변

### 데모 후
- [ ] 피드백 수집
- [ ] 개선 사항 기록
- [ ] 데모 결과 정리

---

## 비상 계획

### 시나리오 1: 네트워크 연결 실패
**대응**:
- 사전 녹화된 스크린샷/비디오 준비
- 아키텍처 다이어그램과 문서로 설명
- 주요 코드와 설정 파일 직접 보여주기

### 시나리오 2: Pod 장애 발생
**대응**:
- kubectl describe로 문제 진단 시연
- 로그 확인 과정 시연
- 자동 복구 대기 (일반적으로 30초 이내)

### 시나리오 3: CI/CD 파이프라인 실패
**대응**:
- 이전 성공한 워크플로우 실행 기록 보여주기
- GitHub Actions 로그 설명
- 문제 해결 프로세스 시연

---

## 추가 시연 가능 항목 (시간 여유 시)

1. **Loki 로그 조회**:
   - 특정 서비스 로그 필터링
   - 에러 로그 검색
   - 로그 시간대별 조회

2. **HPA 동작 확인**:
   ```bash
   kubectl get hpa -n titanium-prod
   kubectl describe hpa prod-api-gateway-hpa -n titanium-prod
   ```

3. **NetworkPolicy 확인**:
   ```bash
   kubectl get networkpolicies -n titanium-prod
   kubectl describe networkpolicy <policy-name> -n titanium-prod
   ```

4. **롤백 시연**:
   ```bash
   kubectl rollout history deployment/prod-api-gateway-deployment -n titanium-prod
   kubectl rollout undo deployment/prod-api-gateway-deployment -n titanium-prod
   ```

---

**작성자**: 이동주
**작성일**: 2025년 11월 3일
--- 

## 부록: Grafana 및 Kiali 대시보드 상세 가이드

### 1. Grafana Golden Signals Dashboard

#### 접속 정보
- **URL**: http://10.0.11.168:30300
- **계정**: admin / prom-operator
- **경로**: Dashboards → Browse → "Golden Signals Dashboard"

---

##### 1.1. Panel 1 - Latency (응답 시간)

**패널 제목**: Latency (Response Time)

**확인 가능한 메트릭**:
- **P95 (95th Percentile)**: 95% 사용자가 경험하는 응답 시간
  - 목표: < 100ms
  - 정상 범위: 10-50ms
  - 주의: 50-100ms
  - 위험: > 100ms

- **P99 (99th Percentile)**: 99% 사용자가 경험하는 응답 시간 (최악 케이스)
  - 목표: < 200ms
  - 정상 범위: 20-100ms
  - 주의: 100-200ms
  - 위험: > 200ms

**그래프 해석**:
- 시간에 따른 백분위수 응답 시간 추이를 선 그래프로 표시
- 선이 평평하면 안정적인 상태
- 급격한 스파이크는 일시적 부하
- 지속적 상승은 시스템 문제 신호

**데모 시 강조 포인트**:
- "P95가 20ms 이하로 매우 빠른 응답 속도를 보입니다"
- "P99도 100ms 이하로 대부분 사용자가 빠른 경험을 합니다"

---

##### 1.2. Panel 2 - Traffic (처리량)

**패널 제목**: Traffic (Requests per Second)

**확인 가능한 메트릭**:
- 서비스별 초당 요청 수 (RPS)
- 스택 영역 차트(Stacked Area Chart) 형태로 표시

**정상 범위**:
- 평상시: 5-20 RPS
- 부하 테스트 시: 50-100 RPS

**문제 신호**:
- 모든 서비스 0 RPS: Prometheus 메트릭 수집 문제
- 특정 서비스만 0 RPS: 해당 서비스 다운 또는 라우팅 문제

---

##### 1.3. Panel 3 - Errors (에러율)

**패널 제목**: Errors (Error Rate %)

**확인 가능한 메트릭**:
- **4xx 에러**: 클라이언트 에러 발생률 (%)
- **5xx 에러**: 서버 에러 발생률 (%)

**HTTP 상태 코드별 의미**:
- **5xx (서버 에러)**:
  - 목표: 0%
  - 허용: < 0.1%
  - 위험: > 1%

**문제 진단**:
- 5xx 에러 지속 발생: 백엔드 서비스 문제
- 4xx 에러 급증: API 호출 방식 변경 또는 클라이언트 버그

---

##### 1.4. Panel 4 - Saturation (리소스 포화도)

**패널 제목**: Saturation (Resource Usage)

**확인 가능한 메트릭**:
- **CPU 사용률 (%)**: Pod별 CPU 사용 비율
- **Memory 사용률 (%)**: Pod별 메모리 사용 비율

**문제 신호**:
- CPU 지속적 > 80%: 리소스 부족, replica 증가 필요
- Memory 지속적 증가: 메모리 누수 가능성

---

### 2. Kiali Service Mesh Dashboard

#### 접속 정보
- **URL**: http://10.0.11.168:30164
- **인증**: 자동 로그인 (인증 설정 없음)
- **네임스페이스**: titanium-prod 선택

---

##### 2.1. Graph 메뉴 (핵심 기능)

**Display 옵션**:
- Traffic Animation: 실시간 트래픽 흐름 애니메이션
- Service Nodes: 서비스 노드 표시
- Security: mTLS 잠금 아이콘 표시

**서비스 토폴로지 확인**:
- **istio-ingressgateway**: 외부 트래픽 진입점
- **prod-auth-service, prod-user-service, prod-blog-service**: 마이크로서비스
- **postgresql-service, prod-redis-service**: 데이터베이스 및 캐시 (mTLS 비활성화)

**트래픽 흐름 분석**:
- **초록색 화살표**: 정상 요청 (HTTP 2xx)
- **빨간색 화살표**: 서버 에러 (HTTP 5xx)

---

##### 2.2. Istio Config 메뉴

**리소스 목록**:
- **VirtualService**: 라우팅 규칙
- **DestinationRule**: 트래픽 정책 및 mTLS 설정
- **PeerAuthentication**: mTLS 모드 (STRICT, PERMISSIVE, DISABLE)
- **Gateway**: 외부 노출 포트 및 프로토콜

**Config Validation**:
- "0 errors found, 0 warnings found" 확인 → 모든 설정이 유효함

---


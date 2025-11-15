# 데모 시나리오

## 문서 정보
- **버전**: 2.0
- **최종 수정일**: 2025년 11월 14일
- **예상 소요 시간**: 20-25분

---

## 데모 개요

이 문서는 Cloud-Native 마이크로서비스 플랫폼 v2.0의 핵심 기능을 시연하기 위한 시나리오입니다. 전체 시스템의 안정성, 자동화, 관측성을 효과적으로 보여주는 것을 목표로 합니다.

**핵심 메시지**:
- 완전 자동화된 CI/CD 파이프라인 (Git Push → 5분 내 배포)
- 실시간 관측성 시스템 (Prometheus + Grafana + Loki)
- Istio 서비스 메시를 통한 보안 강화 (mTLS STRICT)
- 고가용성 및 자동 복구 능력

---

## 사전 준비

### 시스템 상태 확인

```bash
# 모든 Pod Running 상태 확인
kubectl get pods -n titanium-prod
kubectl get pods -n istio-system
kubectl get pods -n monitoring

# 서비스 접속 테스트
curl http://10.0.11.168:31304/blog/
```

### 브라우저 탭 준비

- **Tab 1**: Grafana 대시보드 (http://10.0.11.168:30300)
- **Tab 2**: Kiali 서비스 메시 (http://10.0.11.168:30164)
- **Tab 3**: 애플리케이션 (http://10.0.11.168:31304)
- **Tab 4**: GitHub Actions

### Load Generator 배포

```bash
# 메트릭 지속 생성을 위한 Load Generator 배포
kubectl apply -f k8s-manifests/overlays/solid-cloud/load-generator.yaml

# 배포 확인
kubectl get pods -n titanium-prod -l app=load-generator
```

---

## 시연 흐름

### 1. 프로젝트 소개 (3분)

**주요 내용**:
- 프로젝트 배경 및 목표
- v1.0 대비 v2.0 개선 사항
- 기술 스택 소개 (Terraform, GitOps, Istio, Prometheus)
- 5주간 개발 성과 (Must-Have 100%, Should-Have 100%)

### 2. CI/CD 파이프라인 시연 (5분)

**시연 내용**:
1. 코드 변경 및 Git Push
2. GitHub Actions 자동 실행 확인
   - 빌드 및 테스트
   - Trivy 보안 스캔
   - Docker Hub 이미지 푸시
3. Argo CD 자동 동기화
4. Kubernetes Pod 롤아웃 확인

```bash
# 코드 변경
echo "# Demo commit - $(date)" >> user-service/DEMO.txt
git add user-service/DEMO.txt
git commit -m "데모: CI/CD 파이프라인 테스트"
git push origin main

# Pod 롤아웃 확인
while true; do clear; kubectl get pods -n titanium-prod; sleep 2; done
```

### 3. 모니터링 시스템 시연 (7분)

**시연 내용**:
1. **Grafana Golden Signals 대시보드**
   - Latency: P95 응답 시간
   - Traffic: 초당 요청 수
   - Errors: 에러율
   - Saturation: CPU/메모리 사용률

2. **Kiali 서비스 메시 시각화**
   - 서비스 간 통신 토폴로지
   - 실시간 트래픽 흐름
   - mTLS 암호화 상태 확인

3. **부하 테스트**
   ```bash
   # 트래픽 급증 시뮬레이션
   for i in {1..100}; do
     curl -s -o /dev/null http://10.0.11.168:31304/blog/
     sleep 0.05
   done
   ```
   - Grafana에서 RPS 급증 확인
   - P95 Latency 변화 관찰

4. **Loki 로그 조회** (시간이 있다면)
   - Grafana Explore에서 titanium-prod 로그 조회
   - 특정 서비스 로그 필터링

### 4. 보안 및 서비스 메시 (3분)

**시연 내용**:
1. **Istio mTLS 확인**
   ```bash
   kubectl get peerauthentication -n titanium-prod
   kubectl get pods -n titanium-prod -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.containers[*].name}{"\n"}{end}' | head -5
   ```

2. **보안 스캔**
   - GitHub Actions의 Trivy 스캔 결과 확인

### 5. 에러 시나리오 (선택사항, 3분)

**시연 내용**:
1. 의도적인 에러 발생
   ```bash
   # 404 에러 발생
   for i in {1..20}; do
     curl -s -o /dev/null -w "HTTP %{http_code}\n" http://10.0.11.168:31304/nonexistent
     sleep 0.5
   done
   ```

2. Grafana에서 에러율 증가 확인
3. Loki에서 에러 로그 추적

### 6. 고가용성 및 자동 복구 (선택사항, 2분)

**시연 내용**:
1. 현재 시스템 상태 확인 (모든 서비스 2+ replicas)
2. Pod 강제 삭제 및 자동 재생성 확인
   ```bash
   kubectl delete pod <pod-name> -n titanium-prod
   watch kubectl get pods -n titanium-prod
   ```

---

## 마무리 (2분)

**강조 포인트**:
- Git Push 후 5분 내 자동 배포
- Istio mTLS로 모든 서비스 간 통신 암호화
- 실시간 성능: P95 19.2ms, 에러율 0%
- 고가용성: 주요 서비스 2+ replicas 유지
- Must-Have 100%, Should-Have 100% 달성

---

## 상세 시나리오

데모 진행을 위한 상세 스크립트, 예상 질문 및 답변, 비상 계획은 아래 Notion 페이지를 참고하세요:

**[Notion: 상세 데모 시나리오](https://www.notion.so/leestories/2ab6a7ec472880c2928ff9a86195f455)**

---

## 접속 정보

- **Grafana**: http://10.0.11.168:30300 (admin / prom-operator)
- **Kiali**: http://10.0.11.168:30164
- **애플리케이션**: http://10.0.11.168:31304
- **Prometheus**: http://10.0.11.168:30090

---

**작성자**: 이동주
**최종 수정일**: 2025년 11월 14일

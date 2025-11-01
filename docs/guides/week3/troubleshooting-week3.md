# Week 3 트러블슈팅 가이드 - 관측성 시스템

이 문서는 Week 3 (관측성 시스템) 구축 중 발생할 수 있는 문제들과 해결 방법을 정리합니다.

## 목차
- [Prometheus & Grafana 설치](#prometheus--grafana-설치)
- [애플리케이션 메트릭 수집](#애플리케이션-메트릭-수집)
- [Grafana 대시보드](#grafana-대시보드)
- [Loki 로깅 시스템](#loki-로깅-시스템)
- [AlertManager 알림](#alertmanager-알림)
- [통합 문제](#통합-문제)
- [일반적인 디버깅 명령어](#일반적인-디버깅-명령어)
- [추가 리소스](#추가-리소스)

---

## Prometheus & Grafana 설치

### 1.1 Grafana CrashLoopBackOff - 중복 datasource

**문제**: Grafana pod가 CrashLoopBackOff 상태

**증상**:
```bash
kubectl get pods -n monitoring

NAME                                  READY   STATUS             RESTARTS
prometheus-grafana-746b9489b9-nrp7k   2/3     CrashLoopBackOff   7
```

**로그**:
```
level=error msg="Datasource provisioning error: datasource.yaml config is invalid.
Only one datasource per organization can be marked as default"
```

**원인**: prometheus-values.yaml에서 수동으로 datasource를 설정했는데, kube-prometheus-stack이 이미 자동으로 Prometheus datasource를 생성

**해결 방법**:

prometheus-values.yaml에서 datasource 설정 제거:
```yaml
grafana:
  enabled: true
  adminPassword: admin123

  # [비권장] 이 부분 제거
  # datasources:
  #   datasources.yaml:
  #     apiVersion: 1
  #     datasources:
  #     - name: Prometheus

  # [권장] 대신 주석으로 설명만
  # Prometheus 데이터 소스는 Helm chart가 자동 설정
  # (kube-prometheus-stack이 자동으로 Prometheus 연결)
```

**검증**:
```bash
kubectl get pods -n monitoring -l app.kubernetes.io/name=grafana
# STATUS: Running
```

---

### 1.2 Prometheus Operator TLS 오류

**문제**: Prometheus Operator pod가 ContainerCreating 상태에서 멈춤

**증상**:
```bash
kubectl describe pod prometheus-kube-prometheus-operator-xxx -n monitoring

Events:
  Warning  FailedMount  MountVolume.SetUp failed for volume "tls-secret":
  secret "prometheus-kube-prometheus-admission" not found
```

**원인**:
- admission webhook을 비활성화했지만
- operator가 여전히 TLS secret을 찾으려 함

**해결 방법**:

prometheus-values.yaml 수정:
```yaml
prometheusOperator:
  enabled: true

  # Admission Webhook 완전히 비활성화
  admissionWebhooks:
    enabled: false
    patch:
      enabled: false  # [필수] 이것도 추가

  # TLS 비활성화
  tls:
    enabled: false  # [필수] 이것도 추가
```

**재설치**:
```bash
helm uninstall prometheus -n monitoring
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --values k8s-manifests/monitoring/prometheus-values.yaml
```

---

### 1.3 PVC 생성 실패

**문제**: Prometheus나 Grafana PVC가 Pending 상태

**증상**:
```bash
kubectl get pvc -n monitoring

NAME                                    STATUS    VOLUME   CAPACITY
prometheus-prometheus-kube-...-db-0     Pending
```

**이벤트**:
```
no persistent volumes available for this claim and no storage class is set
```

**원인**:
- Solid Cloud 환경에 기본 StorageClass가 없음
- 또는 StorageClass가 있지만 PV가 부족

**해결 방법**:

**옵션 1**: 기본 StorageClass 확인 및 사용
```bash
kubectl get storageclass

# 기본 StorageClass 설정
kubectl patch storageclass YOUR-STORAGE-CLASS \
  -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'
```

**옵션 2**: hostPath 사용 (개발 환경)
```yaml
# prometheus-values.yaml
prometheus:
  prometheusSpec:
    storageSpec:
      volumeClaimTemplate:
        spec:
          storageClassName: ""  # 비워두기
          accessModes: ["ReadWriteOnce"]
          resources:
            requests:
              storage: 10Gi
```

**옵션 3**: emptyDir 사용 (임시 데이터)
```yaml
prometheus:
  prometheusSpec:
    storageSpec: {}  # 제거
```

---

### 1.4 NodePort 접근 불가

**문제**: NodePort로 Grafana 접근 시도 시 연결 거부

**증상**:
```bash
curl http://NODE_IP:30300
curl: (7) Failed to connect to NODE_IP port 30300: Connection refused
```

**원인**: Solid Cloud 환경에서는 노드에 외부 IP가 없음

**해결 방법**:

**옵션 1**: kubectl port-forward (로컬 개발)
```bash
kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80

# 브라우저에서 http://localhost:3000 접속
# ID: admin, PW: admin123
```

**옵션 2**: Ingress 사용 (프로덕션)
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: grafana-ingress
  namespace: monitoring
spec:
  rules:
  - host: grafana.your-domain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: prometheus-grafana
            port:
              number: 80
```

**옵션 3**: LoadBalancer (클라우드)
```yaml
grafana:
  service:
    type: LoadBalancer  # NodePort 대신
```

---

## 애플리케이션 메트릭 수집

### 2.1 메트릭 엔드포인트 404

**문제**: /metrics 엔드포인트가 404 Not Found

**증상**:
```bash
kubectl exec -n titanium-prod deploy/prod-user-service-deployment -- \
  python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/metrics')"

urllib.error.HTTPError: HTTP Error 404: Not Found
```

**원인**: prometheus-fastapi-instrumentator가 설치되지 않음

**해결 방법**:

1. requirements.txt 업데이트:
```txt
prometheus-client
prometheus-fastapi-instrumentator
```

2. 코드 수정:
```python
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI()

# Prometheus 메트릭 설정
Instrumentator().instrument(app).expose(app)
```

3. 재배포:
```bash
git add user-service/requirements.txt user-service/user_service.py
git commit -m "feat: add Prometheus metrics to user-service"
git push
```

4. CI/CD 완료 후 검증:
```bash
kubectl exec -n titanium-prod deploy/prod-user-service-deployment -- \
  python3 -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8001/metrics').read().decode()[:500])"
```

---

### 2.2 ServiceMonitor가 타겟을 발견하지 못함

**문제**: Prometheus targets에서 ServiceMonitor가 0/0으로 표시

**증상**:
```bash
# Prometheus UI → Targets
# ServiceMonitor: user-service (0/0)
```

**원인**: ServiceMonitor의 selector와 Service의 labels가 일치하지 않음

**해결 방법**:

1. Service 레이블 확인:
```bash
kubectl get svc prod-user-service -n titanium-prod --show-labels

LABELS
app=user-service,app.kubernetes.io/name=titanium,...
```

2. ServiceMonitor 확인:
```yaml
# servicemonitor-user-service.yaml
spec:
  selector:
    matchLabels:
      app: user-service  # [필수] Service의 app 레이블과 일치해야 함
```

3. 불일치 시 수정:
```yaml
# 옵션 A: ServiceMonitor 수정
spec:
  selector:
    matchLabels:
      app: user-service  # Service 레이블에 맞춤

# 옵션 B: Service에 레이블 추가
metadata:
  labels:
    app: user-service
```

**검증**:
```bash
kubectl get servicemonitor -n titanium-prod user-service -o yaml | grep -A 3 "matchLabels"
kubectl get svc prod-user-service -n titanium-prod -o yaml | grep -A 5 "labels:"
```

---

### 2.3 포트 이름 불일치

**문제**: ServiceMonitor의 port와 Service의 port name이 다름

**증상**:
```
no endpoints available for service
```

**원인**: ServiceMonitor가 "http"라는 이름의 포트를 찾지만 Service에는 다른 이름

**해결 방법**:

1. Service의 포트 이름 확인:
```bash
kubectl get svc prod-user-service -n titanium-prod -o yaml | grep -A 5 "ports:"
```

2. 포트 이름 통일:
```yaml
# Service
spec:
  ports:
  - name: http  # [필수] 이름 통일
    port: 8001
    targetPort: http

# ServiceMonitor
spec:
  endpoints:
  - port: http  # [필수] Service의 port name과 일치
    path: /metrics
```

**또는 targetPort 사용**:
```yaml
# ServiceMonitor
spec:
  endpoints:
  - targetPort: 8001  # port name 대신 번호 사용
    path: /metrics
```

---

### 2.4 메트릭 수집이 안 됨 (selector 문제)

**문제**: ServiceMonitor를 만들었지만 Prometheus가 인식하지 못함

**증상**:
```bash
kubectl get servicemonitor -n titanium-prod
# NAME           AGE
# user-service   10m

# 하지만 Prometheus UI에서 보이지 않음
```

**원인**: Prometheus의 serviceMonitorSelectorNilUsesHelmValues가 true

**해결 방법**:

prometheus-values.yaml 수정:
```yaml
prometheus:
  prometheusSpec:
    # ServiceMonitor 자동 감지 활성화
    serviceMonitorSelectorNilUsesHelmValues: false  # [필수]
    podMonitorSelectorNilUsesHelmValues: false      # [필수]
```

Helm 업그레이드:
```bash
helm upgrade prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --values k8s-manifests/monitoring/prometheus-values.yaml
```

---

## Grafana 대시보드

### 3.1 대시보드 자동 로드 안 됨

**문제**: ConfigMap을 만들었지만 Grafana sidecar가 감지하지 못함

**증상**:
```bash
kubectl logs -n monitoring prometheus-grafana-xxx -c grafana-sc-dashboard

# 대시보드 로드 로그가 없음
```

**원인**: ConfigMap에 올바른 레이블이 없음

**해결 방법**:

ConfigMap에 레이블 추가:
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-dashboard-golden-signals
  namespace: monitoring
  labels:
    grafana_dashboard: "1"  # [필수] 이 레이블 필수!
data:
  golden-signals.json: |
    {...}
```

**검증**:
```bash
kubectl logs -n monitoring prometheus-grafana-xxx -c grafana-sc-dashboard --tail=20

# 출력:
# Writing /tmp/dashboards/golden-signals.json (ascii)
# Dashboards config reloaded - 200 OK
```

---

### 3.2 대시보드 JSON 파싱 오류

**문제**: Grafana가 대시보드를 로드하지 못함

**증상**:
```
Error: invalid JSON
```

**원인**: JSON 형식 오류

**해결 방법**:

1. JSON validator로 검증:
```bash
# jq 사용
cat golden-signals-dashboard.json | jq .

# 또는 온라인 validator: https://jsonlint.com/
```

2. 일반적인 오류:
```json
{
  "title": "Dashboard",
  "panels": [
    {
      "id": 1,
      "title": "Panel"  // [비권장] 마지막 항목 뒤에 쉼표 없어야 함
    }
  ]
}
```

3. ConfigMap의 들여쓰기 확인:
```yaml
data:
  dashboard.json: |
    {              # [권장] 4 spaces indent
      "title": ""  # [권장] 6 spaces indent
    }
```

---

### 3.3 쿼리 결과가 없음 (No data)

**문제**: 대시보드 패널에 "No data" 표시

**증상**: 패널이 비어있거나 "No data" 메시지

**원인**:
1. 잘못된 PromQL 쿼리
2. 네임스페이스 필터 오류
3. 메트릭이 실제로 수집되지 않음

**해결 방법**:

1. Prometheus UI에서 쿼리 테스트:
```
http://localhost:9090 (port-forward)
→ Graph 탭
→ 쿼리 입력 및 Execute
```

2. 네임스페이스 확인:
```promql
# [비권장] 잘못된 예
http_requests_total{namespace="prod"}

# [권장] 올바른 예
http_requests_total{namespace="titanium-prod"}
```

3. 메트릭 존재 여부 확인:
```promql
# 단순 쿼리로 먼저 테스트
up{namespace="titanium-prod"}

# 레이블 확인
http_requests_total
```

4. 시간 범위 확인:
- Last 1 hour로 설정했는데 메트릭이 최근에 없을 수 있음
- Last 5 minutes로 변경하여 테스트

---

### 3.4 변수가 작동하지 않음

**문제**: 대시보드 변수 드롭다운이 비어있음

**증상**:
```
Service: [No options found]
```

**원인**:
1. 변수 쿼리가 잘못됨
2. datasource가 지정되지 않음

**해결 방법**:

변수 설정 확인:
```json
{
  "templating": {
    "list": [
      {
        "name": "service",
        "type": "query",
        "datasource": "Prometheus",  // [필수] 필수
        "query": {
          "query": "label_values(http_requests_total{namespace=\"titanium-prod\"}, job)",
          "refId": "StandardVariableQuery"
        },
        "refresh": 1  // [필수] on dashboard load
      }
    ]
  }
}
```

**검증**:
1. Grafana UI → Dashboard Settings → Variables
2. Preview of values 확인
3. 값이 표시되어야 함

---

## Loki 로깅 시스템

### 4.1 Promtail read-only file system 오류

**문제**: Promtail 로그에 지속적으로 오류 발생

**증상**:
```bash
kubectl logs -n monitoring loki-promtail-xxx

level=error msg="error writing positions file"
error="open /tmp/.positions.yaml7530213760312687384: read-only file system"
```

**원인**:
- Promtail이 /tmp에 positions 파일을 쓰려 하는데 권한 없음
- 하지만 기능에는 영향 없음 (메모리에 position 유지)

**해결 방법**:

**옵션 1**: 무시 (권장)
- 로그 수집은 정상 작동
- positions 파일은 재시작 시 offset을 기억하는 용도
- DaemonSet이므로 재시작이 드물어서 큰 문제 없음

**옵션 2**: Volume 추가 (완전 해결)
```yaml
# loki-stack-values.yaml
promtail:
  extraVolumes:
  - name: positions
    emptyDir: {}

  extraVolumeMounts:
  - name: positions
    mountPath: /tmp
```

**검증**: 기능 확인이 중요
```bash
# Loki에서 로그 조회
kubectl exec -n monitoring loki-0 -- \
  wget -q -O- 'http://localhost:3100/loki/api/v1/query?query={namespace="titanium-prod"}&limit=10'

# 결과가 나오면 정상 작동
```

---

### 4.2 Loki 연결 거부 (Connection refused)

**문제**: Promtail이 Loki에 연결하지 못함

**증상**:
```
level=warn msg="error sending batch, will retry"
error="Post \"http://loki:3100/loki/api/v1/push\": dial tcp 10.106.209.75:3100: connect: connection refused"
```

**원인**:
1. Loki pod가 아직 시작 중
2. Loki Service가 없음
3. 네트워크 문제

**해결 방법**:

1. Loki 상태 확인:
```bash
kubectl get pods -n monitoring -l app=loki

NAME     READY   STATUS    RESTARTS   AGE
loki-0   1/1     Running   0          5m
```

2. Loki ready 확인:
```bash
kubectl exec -n monitoring loki-0 -- wget -q -O- "http://localhost:3100/ready"
# 출력: ready
```

3. Service 확인:
```bash
kubectl get svc -n monitoring -l app=loki

NAME              TYPE        CLUSTER-IP      PORT(S)
loki              ClusterIP   10.106.209.75   3100/TCP
```

4. 시간 경과 후 자동 해결:
- Loki가 완전히 시작되면 Promtail이 자동으로 연결
- 일반적으로 1-2분 소요

**검증**:
```bash
# Promtail 로그에서 성공 메시지 확인
kubectl logs -n monitoring loki-promtail-xxx --tail=20 | grep -v "connection refused"
```

---

### 4.3 로그가 수집되지 않음

**문제**: Loki에 로그가 없음

**증상**:
```bash
kubectl exec -n monitoring loki-0 -- \
  wget -q -O- 'http://localhost:3100/loki/api/v1/query?query={namespace="titanium-prod"}'

# 결과: {"status":"success","data":{"resultType":"streams","result":[]}}
```

**원인**:
1. Promtail의 네임스페이스 필터
2. 잘못된 log path
3. relabel_configs 오류

**해결 방법**:

1. Promtail config 확인:
```yaml
# loki-stack-values.yaml
promtail:
  config:
    scrape_configs:
    - job_name: kubernetes-pods
      relabel_configs:
      # 네임스페이스 필터 확인
      - source_labels: [__meta_kubernetes_namespace]
        regex: (titanium-prod|monitoring)  # [필수] 올바른 네임스페이스
        action: keep
```

2. Promtail이 로그 파일을 찾는지 확인:
```bash
kubectl logs -n monitoring loki-promtail-xxx | grep "Seeked"
```

3. 로그 경로 확인:
```yaml
relabel_configs:
- source_labels: [__meta_kubernetes_pod_uid, __meta_kubernetes_pod_container_name]
  target_label: __path__
  separator: /
  replacement: /var/log/pods/*$1/*.log  # [필수] Kubernetes 표준 경로
```

4. 직접 로그 파일 확인:
```bash
# Promtail이 실행 중인 노드에서
kubectl exec -n monitoring loki-promtail-xxx -- ls /var/log/pods/titanium-prod*/
```

---

### 4.4 로그 retention 설정이 적용되지 않음

**문제**: 디스크가 가득 참

**증상**:
```bash
kubectl exec -n monitoring loki-0 -- df -h /data

Filesystem      Size  Used Avail Use% Mounted on
/dev/sda1        10G   10G     0 100% /data
```

**원인**: retention이 활성화되지 않음

**해결 방법**:

loki-stack-values.yaml 확인:
```yaml
loki:
  config:
    table_manager:
      retention_deletes_enabled: true  # [필수] 필수
      retention_period: 168h           # 7일

    chunk_store_config:
      max_look_back_period: 168h       # retention과 일치
```

재설치:
```bash
helm upgrade loki grafana/loki-stack \
  --namespace monitoring \
  --values k8s-manifests/monitoring/loki-stack-values.yaml
```

**수동 정리** (긴급):
```bash
# Loki pod 재시작 (데이터 일부 손실 가능)
kubectl delete pod loki-0 -n monitoring

# 또는 PVC 크기 증가
kubectl patch pvc loki -n monitoring \
  -p '{"spec":{"resources":{"requests":{"storage":"20Gi"}}}}'
```

---

## AlertManager 알림

### 5.1 PrometheusRule이 로드되지 않음

**문제**: PrometheusRule을 만들었지만 Prometheus가 인식하지 못함

**증상**:
```bash
kubectl get prometheusrule -n monitoring titanium-alerts
# NAME              AGE
# titanium-alerts   10m

# 하지만 Prometheus UI → Alerts에서 보이지 않음
```

**원인**: PrometheusRule의 레이블이 Prometheus의 ruleSelector와 일치하지 않음

**해결 방법**:

1. Prometheus의 ruleSelector 확인:
```bash
kubectl get prometheus -n monitoring prometheus-kube-prometheus-prometheus \
  -o yaml | grep -A 5 "ruleSelector"

# 출력:
# ruleSelector:
#   matchLabels:
#     release: prometheus
```

2. PrometheusRule에 레이블 추가:
```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: titanium-alerts
  namespace: monitoring
  labels:
    release: prometheus  # [필수] 필수 레이블
spec:
  groups:
  - name: titanium.rules
    rules:
    - alert: HighErrorRate
      ...
```

3. 재적용:
```bash
kubectl apply -f k8s-manifests/monitoring/prometheus-rules.yaml
```

**검증**: 1-2분 후
```bash
# Prometheus UI → Alerts
# 또는
kubectl exec -n monitoring loki-0 -- \
  wget -q -O- "http://prometheus-kube-prometheus-prometheus:9090/api/v1/rules" | \
  python3 -c "import sys, json; print(len([g for g in json.load(sys.stdin)['data']['groups'] if 'titanium' in g['name']]))"
```

---

### 5.2 알림 규칙 문법 오류

**문제**: PrometheusRule은 생성되었지만 규칙이 작동하지 않음

**증상**:
```
# Prometheus UI → Alerts
# 규칙 이름이 빨간색으로 표시
# "bad_data: parse error at char 10: ..."
```

**원인**: PromQL 쿼리 문법 오류

**해결 방법**:

1. Prometheus UI에서 쿼리 테스트:
```
http://localhost:9090 → Graph
```

2. 일반적인 오류:

**오류 A**: 레이블 selector 문법
```promql
# [비권장] 잘못된 예
http_requests_total{status="500"}

# [권장] 올바른 예
http_requests_total{status=~"5.."}  # 정규표현식
```

**오류 B**: 연산자 순서
```promql
# [비권장] 잘못된 예
sum(rate(http_requests_total[5m])) by (job) / 100 * sum(rate(http_requests_total[5m]))

# [권장] 올바른 예
(sum(rate(http_requests_total{status=~"5.."}[5m])) by (job)
/
sum(rate(http_requests_total[5m])) by (job)) * 100
```

**오류 C**: 시간 범위
```promql
# [비권장] 잘못된 예
rate(http_requests_total[5])  # 단위 없음

# [권장] 올바른 예
rate(http_requests_total[5m])  # 5 minutes
```

3. 규칙 문법 검증:
```bash
# promtool 사용 (로컬)
promtool check rules k8s-manifests/monitoring/prometheus-rules.yaml
```

---

### 5.3 알림이 발송되지 않음

**문제**: 알림이 firing 상태지만 실제로 받지 못함

**증상**:
```
# Prometheus UI → Alerts
# HighErrorRate: FIRING (for 5m)

# 하지만 이메일/Slack 알림을 받지 못함
```

**원인**: AlertManager에 receiver가 설정되지 않음

**해결 방법**:

AlertManager config 확인:
```bash
kubectl get secret -n monitoring alertmanager-prometheus-kube-prometheus-alertmanager \
  -o jsonpath='{.data.alertmanager\.yaml}' | base64 -d
```

기본 설정은 알림을 보내지 않음:
```yaml
route:
  receiver: 'null'  # [비권장] 알림 버림

receivers:
- name: 'null'
```

Slack receiver 추가 (예시):
```yaml
# alertmanager-config.yaml
apiVersion: v1
kind: Secret
metadata:
  name: alertmanager-prometheus-kube-prometheus-alertmanager
  namespace: monitoring
stringData:
  alertmanager.yaml: |
    global:
      resolve_timeout: 5m

    route:
      group_by: ['alertname', 'namespace']
      group_wait: 10s
      group_interval: 10s
      repeat_interval: 12h
      receiver: 'slack'  # [권장] Slack으로 전송

    receivers:
    - name: 'slack'
      slack_configs:
      - api_url: 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL'
        channel: '#alerts'
        title: '{{ .CommonAnnotations.summary }}'
        text: '{{ .CommonAnnotations.description }}'
```

적용:
```bash
kubectl apply -f alertmanager-config.yaml
```

**검증**: 테스트 알림
```bash
# AlertManager UI (port-forward 필요)
kubectl port-forward -n monitoring svc/prometheus-kube-prometheus-alertmanager 9093:9093

# http://localhost:9093 접속
# Silence 기능으로 테스트
```

---

### 5.4 알림 중복 발송

**문제**: 동일한 알림을 여러 번 받음

**증상**:
- 같은 알림이 2-3번 발송됨
- 특히 Prometheus가 HA 구성인 경우

**원인**:
- 여러 Prometheus replica가 각각 알림 전송
- AlertManager deduplication 설정 누락

**해결 방법**:

1. AlertManager cluster 설정:
```yaml
# prometheus-values.yaml
alertmanager:
  alertmanagerSpec:
    replicas: 1  # [권장] 단일 replica로 설정
```

2. 또는 AlertManager clustering:
```yaml
alertmanager:
  alertmanagerSpec:
    replicas: 3
    externalUrl: http://alertmanager.monitoring.svc:9093
```

3. 알림 그룹화:
```yaml
# alertmanager config
route:
  group_by: ['alertname', 'namespace', 'pod']  # [권장] 그룹화
  group_wait: 30s       # 같은 그룹 알림을 30초 대기
  group_interval: 5m    # 그룹 알림은 5분마다 전송
  repeat_interval: 12h  # 동일 알림은 12시간마다
```

---

## 통합 문제

### 6.1 메모리 부족 (OOMKilled)

**문제**: 모니터링 pod가 OOMKilled로 재시작

**증상**:
```bash
kubectl get pods -n monitoring

NAME                    READY   STATUS      RESTARTS
prometheus-xxx          1/2     OOMKilled   5
```

**원인**: 메모리 limit이 낮음

**해결 방법**:

1. 현재 사용량 확인:
```bash
kubectl top pods -n monitoring
```

2. resources 증가:
```yaml
# prometheus-values.yaml
prometheus:
  prometheusSpec:
    resources:
      requests:
        memory: 2Gi   # 기존 400Mi에서 증가
      limits:
        memory: 4Gi   # 기존 2Gi에서 증가
```

3. 또는 데이터 보존 기간 단축:
```yaml
prometheus:
  prometheusSpec:
    retention: 3d  # 7d → 3d
```

---

### 6.2 디스크 부족

**문제**: Prometheus나 Loki의 PVC가 가득 참

**증상**:
```bash
kubectl exec -n monitoring prometheus-xxx -- df -h

Filesystem      Size  Used Avail Use%
/dev/sda1        10G   10G     0 100%
```

**해결 방법**:

**옵션 1**: PVC 크기 증가
```bash
kubectl patch pvc prometheus-prometheus-kube-prometheus-prometheus-db-prometheus-prometheus-kube-prometheus-prometheus-0 \
  -n monitoring \
  -p '{"spec":{"resources":{"requests":{"storage":"20Gi"}}}}'
```

**옵션 2**: retention 기간 단축
```yaml
# Prometheus
retention: 3d  # 7d → 3d

# Loki
retention_period: 72h  # 168h → 72h
```

**옵션 3**: 데이터 압축 활성화
```yaml
# Prometheus
storageSpec:
  volumeClaimTemplate:
    spec:
      resources:
        requests:
          storage: 10Gi
# Loki는 기본적으로 압축됨
```

---

### 6.3 네트워크 정책으로 통신 차단

**문제**: Promtail이 Loki에 연결하지 못함

**증상**:
```
no route to host
```

**원인**: NetworkPolicy가 네임스페이스 간 통신을 차단

**해결 방법**:

1. NetworkPolicy 확인:
```bash
kubectl get networkpolicy -n monitoring
kubectl get networkpolicy -n titanium-prod
```

2. 필요한 통신 허용:
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-monitoring
  namespace: titanium-prod
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: monitoring
```

---

## 일반적인 디버깅 명령어

### 로그 확인
```bash
# Pod 로그
kubectl logs -n NAMESPACE POD_NAME

# 이전 컨테이너 로그 (재시작된 경우)
kubectl logs -n NAMESPACE POD_NAME --previous

# 특정 컨테이너 로그 (multi-container pod)
kubectl logs -n NAMESPACE POD_NAME -c CONTAINER_NAME

# 실시간 로그
kubectl logs -n NAMESPACE POD_NAME -f
```

### 리소스 확인
```bash
# Pod 상태
kubectl get pods -n NAMESPACE -o wide

# Pod 상세 정보
kubectl describe pod -n NAMESPACE POD_NAME

# Events 확인
kubectl get events -n NAMESPACE --sort-by='.lastTimestamp'

# 리소스 사용량
kubectl top pods -n NAMESPACE
kubectl top nodes
```

### 네트워크 디버깅
```bash
# Service 확인
kubectl get svc -n NAMESPACE

# Endpoint 확인
kubectl get endpoints -n NAMESPACE

# 네트워크 테스트
kubectl run -it --rm debug --image=curlimages/curl:latest --restart=Never -- sh
```

### ConfigMap/Secret 확인
```bash
# ConfigMap 내용
kubectl get configmap -n NAMESPACE NAME -o yaml

# Secret 내용 (base64 decode)
kubectl get secret -n NAMESPACE NAME -o jsonpath='{.data.KEY}' | base64 -d
```

---

## 추가 리소스

### 공식 문서
- [Prometheus Operator](https://github.com/prometheus-operator/prometheus-operator)
- [Grafana Documentation](https://grafana.com/docs/)
- [Loki Documentation](https://grafana.com/docs/loki/latest/)
- [kube-prometheus-stack](https://github.com/prometheus-community/helm-charts/tree/main/charts/kube-prometheus-stack)

### 유용한 도구
- [Lens](https://k8slens.dev/) - Kubernetes IDE
- [k9s](https://k9scli.io/) - Terminal UI
- [stern](https://github.com/stern/stern) - Multi pod log tailing
- [kubectx/kubens](https://github.com/ahmetb/kubectx) - Context/namespace 전환

---

**작성일**: 2025-10-31
**작성자**: 이동주
**버전**: 1.0

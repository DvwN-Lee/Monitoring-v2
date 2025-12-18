---
version: 1.0
last_updated: 2025-11-15
author: Dongju Lee
---

# [Troubleshooting] Prometheus Alertmanager 알림 전송 실패 문제 해결

## 1. 문제 상황

Prometheus에 정의된 알림 규칙(Alerting Rule)이 임계값을 초과하여 'Firing' 상태로 전환되었지만, 지정된 채널(Slack, 이메일 등)로 알림이 전송되지 않는 문제가 발생했습니다. 이로 인해 시스템의 잠재적 문제를 실시간으로 인지하지 못하는 상황이 발생할 수 있습니다.

## 2. 증상

- **Prometheus UI**: 'Alerts' 탭에서 특정 알림이 빨간색 'Firing' 상태로 표시됩니다.
- **Alertmanager UI**:
    - 'Alerts' 탭에 Prometheus로부터 알림이 수신되지 않았거나, 들어왔더라도 'Silenced' 상태로 표시됩니다.
    - 'Silences' 탭에 의도치 않은 Silence 규칙이 활성화되어 있을 수 있습니다.
- **Slack/이메일**: 알림 메시지가 수신되지 않습니다.

## 3. 원인 분석

Solid Cloud Cluster 환경에서 발생한 이 문제의 원인은 다음과 같이 추정되었습니다.

1.  **Prometheus-Alertmanager 연결 오류**: Prometheus 설정 파일(`prometheus.yml`)에 Alertmanager의 서비스 주소가 잘못 설정되었거나, 네트워크 정책(Network Policy)에 의해 통신이 차단되었을 수 있습니다.
2.  **Alertmanager 라우팅(Routing) 설정 오류**: Alertmanager의 `config.yml`에서 `route` 설정이 잘못되어 Firing된 알림이 적절한 `receiver`로 전달되지 못했을 수 있습니다. 예를 들어, `match` 또는 `match_re` 조건이 레이블과 일치하지 않는 경우입니다.
3.  **Receiver 설정 오류**: `receivers` 섹션에 정의된 Slack Webhook URL, 이메일 서버(SMTP) 주소, 또는 인증 정보가 잘못되었을 수 있습니다.
4.  **Silence 규칙 적용**: 의도치 않게 광범위한 조건의 Silence 규칙이 설정되어, 발생한 알림이 의도적으로 무시되었을 수 있습니다.
5.  **네트워크 문제**: Alertmanager Pod가 외부 서비스(Slack, SMTP 서버 등)로 나가는 Egress 트래픽에 대한 네트워크 접근 권한이 없거나, DNS 해석에 실패했을 수 있습니다.

## 4. 해결 방법

아래 단계를 순서대로 진행하여 문제를 해결했습니다.

### 1단계: Prometheus UI에서 Alertmanager 연결 상태 확인

- Prometheus UI의 **Status → Targets** 페이지로 이동하여 `alertmanagers` 섹션을 확인합니다.
- Alertmanager의 엔드포인트가 'UP' 상태인지 확인합니다. 만약 'DOWN' 상태라면, Prometheus 설정의 `static_configs`에 Alertmanager 서비스 주소(`alertmanager-operated.monitoring.svc.cluster.local:9093`)가 올바르게 기재되었는지 검토합니다.

### 2단계: Alertmanager UI에서 알림 수신 여부 확인

- Alertmanager UI에 접속하여 'Alerts' 탭을 확인합니다.
- Prometheus에서 Firing된 알림이 이곳에 표시되는지 확인합니다. 만약 알림이 보이지 않는다면 1단계의 연결 문제를 다시 점검합니다.
- 알림이 'Silenced' 상태로 표시된다면, 'Silences' 탭으로 이동하여 어떤 규칙에 의해 차단되었는지 확인하고 불필요한 규칙을 제거합니다.

### 3단계: Alertmanager ConfigMap의 Route 및 Receiver 설정 검증

- Kubernetes Cluster에서 Alertmanager의 ConfigMap을 확인합니다. (`alertmanager-main` 등)
- `data.alertmanager.yml` 파일의 내용을 검토합니다.
    - `route`의 `group_by`, `group_wait`, `group_interval` 등 기본 설정을 확인합니다.
    - 하위 `routes`에서 알림의 레이블(예: `severity`, `alertname`)과 `match` 조건이 올바르게 설정되어 원하는 `receiver`로 연결되는지 검증합니다.
    - `receiver` 이름이 `receivers` 섹션에 정의된 이름과 일치하는지 확인합니다.

```yaml
# 예시: alertmanager.yml의 route 설정
route:
  receiver: 'default-receiver'
  group_by: ['alertname', 'job']
  routes:
    - receiver: 'slack-notifications'
      match:
        severity: 'critical' # 'critical' 심각도를 가진 알림은 slack-notifications로 라우팅
    - receiver: 'email-notifications'
      match_re:
        service: 'database|backend'
  
receivers:
  - name: 'default-receiver'
    # ...
  - name: 'slack-notifications'
    # ...
  - name: 'email-notifications'
    # ...
```

### 4단계: Slack Webhook 또는 SMTP 설정 테스트

- `receivers` 섹션의 Slack `api_url` 또는 이메일 `smtp_*` 설정이 정확한지 확인합니다.
- 특히 Secret을 통해 Webhook URL이나 비밀번호를 주입하는 경우, Secret이 올바르게 마운트되었고 값이 정확한지 확인합니다.
- 간단한 `curl` 명령을 사용하여 Alertmanager Pod 내부에서 Webhook URL로 테스트 메시지를 전송하여 외부 통신이 가능한지 확인합니다.

```bash
# Alertmanager Pod에 접속하여 실행
curl -X POST -H 'Content-type: application/json' --data '{"text":"Test message from Alertmanager pod"}' <SLACK_WEBHOOK_URL>
```

### 5단계: Alertmanager Pod 로그 확인 및 설정 수정

- 위의 단계로 해결되지 않으면, Alertmanager Pod의 로그를 확인하여 구체적인 오류 메시지를 찾습니다.

```bash
kubectl logs -n monitoring -l app.kubernetes.io/name=alertmanager
```

- 로그에서 "dial tcp: i/o timeout", "no such host"와 같은 네트워크 오류나, "bad request to slack"과 같은 설정 오류 메시지를 확인하고, 해당 문제를 수정합니다.
- ConfigMap 수정 후에는 Alertmanager Pod를 재시작하여 변경 사항을 적용합니다.

## 5. 검증

- 모든 설정이 완료된 후, 의도적으로 테스트 알림을 발생시킵니다. Prometheus `prometheus-rules`에 임시로 항상 참이 되는 규칙을 추가하거나, 기존 규칙의 임계값을 낮추어 알림을 트리거합니다.
- 잠시 후 Slack 채널 또는 이메일로 알림이 정상적으로 수신되는지 확인합니다.

## 6. 교훈

- **Alertmanager 라우팅 규칙의 중요성**: Alertmanager의 핵심 기능은 라우팅입니다. `match`와 `match_re`를 활용하여 알림의 특성에 따라 적절한 담당자나 채널로 알림을 보내는 규칙 설계가 매우 중요합니다.
- **Receiver 설정 사전 테스트**: 새로운 Receiver를 추가할 때는 Pod 내에서 `curl` 등을 이용해 외부 서비스와의 통신을 미리 테스트하여 설정 오류를 조기에 발견하는 것이 효율적입니다.
- **Silence 규칙의 체계적 관리**: 임시로 추가한 Silence 규칙이 방치되지 않도록 만료 시간을 설정하고, 주기적으로 검토하여 불필요한 규칙을 정리해야 합니다.

## 관련 문서

- [시스템 아키텍처 - 모니터링 및 로깅](../../02-architecture/architecture.md#5-모니터링-및-로깅)
- [운영 가이드 - 모니터링](../../04-operations/guides/operations-guide.md)
- [Prometheus 메트릭 수집 실패](troubleshooting-prometheus-metric-collection-failure.md)

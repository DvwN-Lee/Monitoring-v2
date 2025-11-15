---
version: 1.0
last_updated: 2025-11-15
author: Dongju Lee
---

# Loki Log Volume 문제 해결 가이드

**작성일:** 2025-11-14
**문제:** Grafana에서 Loki 로그 조회는 정상이나 Log Volume 차트에서 파싱 에러 발생
**에러 메시지:** `Failed to load log volume for this query - parse error at line 1, col 84: syntax error: unexpected IDENTIFIER`

## 1. 문제 분석

### 1.1 증상
- LogQL 쿼리 `{namespace="titanium-prod"}` 실행 시:
  - 로그 조회: 정상 동작
  - Log Volume 차트: 파싱 에러 발생

### 1.2 현재 버전 정보
```bash
# Loki 버전 확인
kubectl get pod loki-0 -n monitoring -o jsonpath='{.spec.containers[0].image}'
# 결과: grafana/loki:2.6.1

# Grafana 버전 확인
kubectl get pod -n monitoring -l app.kubernetes.io/name=grafana -o jsonpath='{.items[0].spec.containers[?(@.name=="grafana")].image}'
# 결과: docker.io/grafana/grafana:12.2.1
```

### 1.3 근본 원인
- **Loki 2.6.1**: 2022년 릴리스 (약 3년 전)
- **Grafana 12.2.1**: 2025년 최신 릴리스
- Grafana 12의 Log Volume 기능이 내부적으로 생성하는 `count_over_time()` 메트릭 쿼리가 Loki 2.6.1과 호환되지 않음
- Grafana는 최신 Loki API를 기대하지만, Loki 2.6.1은 구버전 API 사용

## 2. 시도한 해결 방법

### 2.1 데이터소스 설정 변경 (실패)
Loki 데이터소스 설정에 호환성 옵션 추가 시도:

```yaml
apiVersion: 1
datasources:
  - name: Loki
    type: loki
    access: proxy
    url: http://loki:3100
    jsonData:
      maxLines: 1000
      timeout: 60
      httpMethod: GET
      derivedFields: []
    editable: true
```

**결과:** Log Volume 에러 지속 발생

**적용 명령:**
```bash
kubectl patch configmap grafana-datasource-loki -n monitoring --type merge -p '{"data":{"loki-datasource.yaml":"..."}}'
kubectl rollout restart deployment prometheus-grafana -n monitoring
```

## 3. 권장 해결 방법

### 3.1 해결책 1: Loki 업그레이드 (권장)
Loki를 최신 버전 (3.x)으로 업그레이드하여 Grafana 12와 호환성 확보

**장점:**
- 근본적인 문제 해결
- 최신 기능 및 성능 개선 활용
- 보안 패치 적용

**단점:**
- 마이그레이션 필요
- 설정 변경 가능성

**업그레이드 단계:**
1. 현재 Loki 설정 백업
   ```bash
   kubectl get statefulset loki -n monitoring -o yaml > loki-backup.yaml
   kubectl get configmap -n monitoring -l app=loki -o yaml > loki-configmap-backup.yaml
   ```

2. Helm을 사용하여 Loki 업그레이드 (Helm으로 설치된 경우)
   ```bash
   helm repo update
   helm upgrade loki grafana/loki -n monitoring --version 6.x.x
   ```

3. 또는 새 버전 StatefulSet 배포
   ```bash
   # loki-upgrade.yaml 작성 (이미지를 grafana/loki:3.0.0 등으로 변경)
   kubectl apply -f loki-upgrade.yaml
   ```

4. 데이터 마이그레이션 확인
   ```bash
   kubectl logs loki-0 -n monitoring
   kubectl exec -it loki-0 -n monitoring -- wget -qO- http://localhost:3100/ready
   ```

### 3.2 해결책 2: Grafana 다운그레이드 (비권장)
Grafana를 Loki 2.6.1과 호환되는 구버전으로 다운그레이드

**장점:**
- Loki 변경 불필요

**단점:**
- 최신 Grafana 기능 사용 불가
- 보안 업데이트 누락 가능성
- 장기적으로 유지보수 어려움

**권장하지 않는 이유:**
- Grafana는 UI/시각화 도구로 최신 버전 유지가 유리
- Loki는 데이터 저장소로 업그레이드가 더 안전

### 3.3 해결책 3: 현상 유지 (임시)
Log Volume 기능 없이 로그 조회 기능만 사용

**장점:**
- 즉시 사용 가능
- 변경 작업 불필요

**단점:**
- Log Volume 차트 미사용
- 시각적 로그 볼륨 트렌드 확인 불가

**현재 상태:**
- 로그 조회 및 필터링: 정상
- 실시간 로그 스트리밍: 정상
- LogQL 쿼리: 정상
- Log Volume 차트: 에러

## 4. 테스트 및 검증

### 4.1 업그레이드 후 검증 절차
1. Loki 서비스 정상 동작 확인
   ```bash
   kubectl get pods -n monitoring | grep loki
   kubectl logs loki-0 -n monitoring --tail=50
   ```

2. Grafana에서 Loki 데이터소스 테스트
   - Grafana UI → Connections → Data sources → Loki
   - "Save & test" 클릭
   - "Successfully queried the Loki API" 확인

3. Log Volume 기능 테스트
   - Grafana → Explore
   - 쿼리: `{namespace="titanium-prod"}`
   - "Run query" 실행
   - Log Volume 차트 정상 표시 확인

4. 기존 로그 데이터 조회 확인
   ```bash
   # Loki API 직접 호출
   kubectl port-forward svc/loki -n monitoring 3100:3100
   curl -G -s "http://localhost:3100/loki/api/v1/query" --data-urlencode 'query={namespace="titanium-prod"}' | jq
   ```

## 5. 백업 및 롤백 계획

### 5.1 백업
```bash
# Loki 데이터 백업 (PVC 스냅샷)
kubectl get pvc -n monitoring | grep loki
# PV/PVC 백업은 클라우드 제공자의 스냅샷 기능 활용

# Loki 설정 백업
kubectl get statefulset loki -n monitoring -o yaml > /tmp/loki-backup-$(date +%Y%m%d).yaml
kubectl get configmap -n monitoring -l app=loki -o yaml > /tmp/loki-cm-backup-$(date +%Y%m%d).yaml
kubectl get secret -n monitoring -l app=loki -o yaml > /tmp/loki-secret-backup-$(date +%Y%m%d).yaml
```

### 5.2 롤백
```bash
# 백업된 설정으로 복원
kubectl apply -f /tmp/loki-backup-YYYYMMDD.yaml
kubectl apply -f /tmp/loki-cm-backup-YYYYMMDD.yaml
kubectl apply -f /tmp/loki-secret-backup-YYYYMMDD.yaml

# Pod 재시작
kubectl rollout restart statefulset loki -n monitoring
```

## 6. 참고 문서

- [Loki Release Notes](https://github.com/grafana/loki/releases)
- [Loki Upgrade Guide](https://grafana.com/docs/loki/latest/upgrade/)
- [Grafana-Loki Compatibility Matrix](https://grafana.com/docs/loki/latest/setup/install/)
- [LogQL Query Language](https://grafana.com/docs/loki/latest/query/)

## 7. 결론

현재 Loki 2.6.1과 Grafana 12.2.1 간의 버전 차이로 인해 Log Volume 기능에 호환성 문제가 발생하고 있습니다. 로그 조회 기능은 정상 작동하므로 운영에 큰 영향은 없으나, 완전한 기능 활용을 위해 **Loki를 최신 버전 (3.x)으로 업그레이드**하는 것을 권장합니다.

업그레이드 시 백업 및 테스트를 철저히 수행하여 서비스 중단을 최소화해야 합니다.

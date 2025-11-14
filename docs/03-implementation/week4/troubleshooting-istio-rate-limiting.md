# [Troubleshooting] Istio EnvoyFilter Rate Limiting 미작동 문제 해결

## 문제 상황
EnvoyFilter를 사용하여 Rate Limiting을 설정했으나, 실제 서비스에 적용되지 않고 모든 요청이 정상 처리됩니다.

## 증상
- 대량의 요청을 서비스로 보냈을 때, 429 Too Many Requests 응답이 반환되지 않고 모든 요청이 200 OK로 처리됩니다.
- `kubectl describe envoyfilter <envoyfilter-name>` 명령으로 EnvoyFilter 리소스의 상태를 확인해도 특별한 오류는 보이지 않습니다.
- `istioctl proxy-config routes` 또는 `istioctl proxy-config listeners` 명령으로 Envoy 프록시 설정을 확인해도 Rate Limiting 관련 설정이 보이지 않거나 잘못 적용된 것처럼 보입니다.

## 원인 분석
1.  **EnvoyFilter의 `workloadSelector` 레이블 불일치**: EnvoyFilter는 `workloadSelector`를 통해 어떤 워크로드(Pod)에 적용될지 결정합니다. 이 셀렉터의 레이블이 대상 Pod의 레이블과 정확히 일치하지 않으면 EnvoyFilter가 적용되지 않습니다.
2.  **EnvoyFilter 설정 문법 오류**: EnvoyFilter의 `configPatch` 부분에 YAML 문법 오류나 EnvoyFilter API 스펙에 맞지 않는 설정이 있을 경우, Envoy 프록시에 적용되지 않고 무시될 수 있습니다.
3.  **ConfigPatch 적용 순서 문제**: 여러 EnvoyFilter가 존재하거나, 특정 패치가 다른 패치에 의존하는 경우 적용 순서에 따라 의도한 대로 동작하지 않을 수 있습니다. `applyTo` 및 `match` 필드를 통해 적용 대상을 정확히 지정해야 합니다.
4.  **Istio 버전과 EnvoyFilter API 버전 불일치**: 사용 중인 Istio 버전과 EnvoyFilter 리소스의 API 버전(`networking.istio.io/v1alpha3`, `v1beta1` 등)이 호환되지 않거나, EnvoyFilter 내에서 사용된 Envoy API(`envoy.config.filter.http.rate_limit.v2.RateLimit` 등)가 현재 Istio 버전에 포함된 Envoy 버전에 맞지 않을 수 있습니다.

## 해결 방법(단계별)

### 1단계: EnvoyFilter 리소스 확인
먼저 EnvoyFilter 리소스 자체에 오타나 기본적인 YAML 문법 오류가 없는지 확인합니다.
```bash
kubectl get envoyfilter <envoyfilter-name> -n <namespace> -o yaml
```
리소스가 정상적으로 생성되었는지, `spec` 부분이 의도한 대로 작성되었는지 육안으로 검토합니다.

### 2단계: `workloadSelector` 레이블 검증
EnvoyFilter가 적용되어야 할 대상 Pod의 레이블과 EnvoyFilter의 `workloadSelector`에 지정된 레이블이 정확히 일치하는지 확인합니다.
```bash
kubectl get pod -n <namespace> -l <key>=<value> # 대상 Pod의 레이블 확인
```
만약 `workloadSelector`가 잘못되었다면, EnvoyFilter가 어떤 Pod에도 적용되지 않습니다.

### 3단계: `istioctl proxy-config`로 Envoy 설정 확인
대상 Pod의 Envoy 프록시에 Rate Limiting 설정이 실제로 적용되었는지 확인합니다.
```bash
istioctl proxy-config routes <pod-name> -n <namespace> -o json
istioctl proxy-config listeners <pod-name> -n <namespace> -o json
```
`routes` 또는 `listeners` 출력에서 Rate Limiting 관련 필드(예: `rate_limits`)가 존재하는지, 그리고 설정값이 올바른지 확인합니다. 만약 설정이 보이지 않는다면 EnvoyFilter가 적용되지 않았거나, 잘못된 위치에 패치되었을 가능성이 높습니다.

### 4단계: EnvoyFilter 재적용 및 Pod 재시작
위 단계들을 통해 EnvoyFilter 설정에 문제가 없다고 판단되면, EnvoyFilter를 삭제 후 재적용하고 대상 Pod를 재시작하여 변경 사항이 완전히 반영되도록 합니다.
```bash
kubectl delete envoyfilter <envoyfilter-name> -n <namespace>
kubectl apply -f <envoyfilter-file.yaml> -n <namespace>
kubectl rollout restart deployment <deployment-name> -n <namespace>
```
이 과정에서 Istio control plane이 EnvoyFilter 변경 사항을 감지하고 Sidecar에 새로운 설정을 푸시하게 됩니다.

## 검증
- EnvoyFilter 재적용 및 Pod 재시작 후, 다시 대량의 요청을 서비스로 보내어 Rate Limiting이 정상적으로 동작하는지 (429 응답이 반환되는지) 확인합니다.
- `istioctl proxy-config routes` 또는 `listeners` 명령으로 Envoy 프록시 설정을 다시 확인하여 Rate Limiting 관련 설정이 올바르게 반영되었는지 최종 검증합니다.
- `kubectl logs <pod-name> -c istio-proxy` 명령으로 istio-proxy 로그에 Rate Limiting 관련 오류나 경고가 없는지 확인합니다.

## 교훈
EnvoyFilter는 Istio의 강력한 확장 기능이지만, 세밀한 설정이 필요하며 디버깅이 까다로울 수 있습니다. Rate Limiting과 같은 기능을 EnvoyFilter로 구현할 때는 `workloadSelector`의 정확성, `configPatch`의 문법 및 Envoy API 스펙 준수, 그리고 적용 순서 등을 면밀히 검토해야 합니다. `istioctl proxy-config` 명령은 Envoy 프록시의 실제 설정을 확인하는 데 매우 유용하므로, 문제 해결 과정에서 적극적으로 활용해야 합니다.

# [Troubleshooting] Prometheus/Grafana Pod Pending 상태 문제 해결

## 1. 문제 상황

Solid Cloud 클러스터 환경에 `kube-prometheus-stack` 헬름 차트를 사용하여 Prometheus와 Grafana를 배포하는 과정에서, 관련 Pod들이 `Pending` 상태에 머무르며 정상적으로 실행되지 않는 문제가 발생했습니다. 이로 인해 모니터링 시스템이 동작하지 않았고, 메트릭 수집 및 시각화가 불가능했습니다.

## 2. 증상

`kubectl` 명령어를 사용하여 `monitoring` 네임스페이스의 Pod 상태를 확인했을 때, `prometheus-prometheus-kube-prometheus-prometheus-0` Pod와 `prometheus-grafana-xxxxxxxxxx-xxxxx` Pod가 `Pending` 상태로 나타났습니다.

```bash
$ kubectl get pods -n monitoring
NAME                                                        READY   STATUS    RESTARTS   AGE
alertmanager-prometheus-kube-prometheus-alertmanager-0      2/2     Running   0          10m
prometheus-grafana-78d6487c9b-n5ggh                          0/3     Pending   0          5m
prometheus-kube-prometheus-operator-7cdd6f7c64-jzm2b        1/1     Running   0          10m
prometheus-kube-state-metrics-6dbd499b78-v9ggr              1/1     Running   0          10m
prometheus-prometheus-kube-prometheus-prometheus-0          0/2     Pending   0          5m
prometheus-prometheus-node-exporter-2v6fg                   1/1     Running   0          10m
prometheus-prometheus-node-exporter-8b2t5                   1/1     Running   0          10m
```

`kubectl describe pod` 명령어로 Pod의 상세 상태를 확인한 결과, `Events` 섹션에서 `FailedScheduling` 이벤트가 기록된 것을 확인했습니다. 이벤트 메시지는 "0/2 nodes are available: 2 Insufficient cpu, 2 Insufficient memory" 와 같이 클러스터 내 리소스 부족을 명확히 나타내고 있었습니다.

```bash
$ kubectl describe pod prometheus-prometheus-kube-prometheus-prometheus-0 -n monitoring

...
Events:
  Type     Reason            Age   From               Message
  ----     ------            ----  ----               -------
  Warning  FailedScheduling  2m    default-scheduler  0/2 nodes are available: 2 Insufficient cpu, 2 Insufficient memory.
  Warning  FailedScheduling  1m    default-scheduler  0/2 nodes are available: 2 Insufficient cpu, 2 Insufficient memory.
```

또 다른 경우, PVC(PersistentVolumeClaim)와 관련된 문제로 인해 `Pending` 상태가 발생할 수 있습니다. `describe` 결과에서 다음과 같은 PVC 바인딩 실패 메시지가 나타날 수 있습니다.

```bash
Events:
  Type     Reason            Age   From               Message
  ----     ------            ----  ----               -------
  Warning  FailedScheduling  3m    default-scheduler  persistentvolumeclaim "prometheus-db" is not bound
```

## 3. 원인 분석

`describe` 명령어의 이벤트 로그를 통해 파악한 주요 원인은 다음과 같습니다.

1.  **클러스터 리소스 부족 (CPU, 메모리)**: Prometheus 및 Grafana Pod가 필요로 하는 리소스(`requests`) 양에 비해, 현재 클러스터의 가용 가능한 노드 리소스가 부족한 상태였습니다. 스케줄러는 Pod를 할당할 적절한 노드를 찾지 못해 `Pending` 상태로 대기시킵니다.
2.  **PVC 바인딩 실패**: Prometheus 서버는 데이터를 저장하기 위해 PersistentVolume(PV)을 요구합니다. 이때 사용되는 PVC가 적절한 PV와 바인딩되지 않으면 Pod는 시작될 수 없습니다. 주요 원인은 다음과 같습니다.
    *   **잘못된 StorageClass 이름**: PVC에 명시된 `storageClassName`이 Solid Cloud 클러스터에 존재하지 않거나 잘못 지정된 경우.
    *   **PV 프로비저닝 실패**: 동적 프로비저닝(Dynamic Provisioning)이 설정된 경우, StorageClass에 문제가 있어 PV 생성이 실패하는 경우.
3.  **노드 가용 용량 부족**: 특정 노드에 이미 많은 Pod가 할당되어 있어 추가적인 Pod를 스케줄링할 CPU, 메모리, 또는 스토리지 용량이 없는 경우입니다.

## 4. 해결 방법

#### 1단계: `kubectl describe pod`로 정확한 원인 파악

가장 먼저 `Pending` 상태의 Pod를 `describe`하여 이벤트(Events)를 확인합니다. 이 단계에서 리소스 부족 문제인지, PVC 문제인지, 또는 다른 스케줄링 제약 조건 때문인지 명확히 파악할 수 있습니다.

```bash
# CPU, 메모리 부족 메시지 확인
$ kubectl describe pod prometheus-grafana-78d6487c9b-n5ggh -n monitoring
...
Events:
  Type     Reason            Age   From               Message
  ----     ------            ----  ----               -------
  Warning  FailedScheduling  5m    default-scheduler  0/2 nodes are available: 1 Insufficient memory, 1 node(s) had taints that the pod didn't tolerate.

# PVC 바인딩 실패 메시지 확인
$ kubectl describe pod prometheus-prometheus-kube-prometheus-prometheus-0 -n monitoring
...
Events:
  Type     Reason            Age   From               Message
  ----     ------            ----  ----               -------
  Warning  FailedScheduling  2m    default-scheduler  persistentvolumeclaim "prometheus-db" is not bound
```

#### 2단계: 노드 리소스 상태 확인

원인이 리소스 부족으로 추정될 경우, `kubectl top nodes` 명령어로 각 노드의 현재 CPU 및 메모리 사용량을 확인하여 클러스터의 전반적인 리소스 현황을 파악합니다.

```bash
$ kubectl top nodes
NAME        CPU(cores)   CPU%   MEMORY(bytes)   MEMORY%
node-1      450m         22%    2800Mi          70%
node-2      1800m        90%    3500Mi          88%
```

위 결과에서 `node-2`는 이미 리소스 사용량이 높아 추가 Pod를 할당하기 어려운 상태임을 알 수 있습니다.

#### 3단계: PVC 상태 확인

원인이 PVC 바인딩 실패로 추정될 경우, `kubectl get pvc` 명령어로 PVC의 상태(`STATUS`)를 확인합니다. `Pending` 상태라면 해당 PVC가 PV와 바인딩되지 못했음을 의미합니다.

```bash
$ kubectl get pvc -n monitoring
NAME                                STATUS    VOLUME   CAPACITY   ACCESS MODES   STORAGECLASS   AGE
prometheus-kube-prometheus-db-0     Pending                                     standard       8m
```

`describe pvc` 명령어로 더 상세한 원인을 파악할 수 있습니다. `storageClassName`이 잘못되었거나, 해당 클래스를 지원하는 프로비저너가 없는 경우 관련 이벤트가 표시됩니다.

```bash
$ kubectl describe pvc prometheus-kube-prometheus-db-0 -n monitoring
...
Events:
  Type     Reason         Age                From                         Message
  ----     ------         ----               ----                         -------
  Warning  ProvisioningFailed 2m (x17 over 8m)   persistentvolume-controller  storageclass "standard" not found
```

#### 4단계: 원인에 따른 조치 수행

*   **리소스 부족 시: 리소스 요청량 조정**
    `kube-prometheus-stack` 헬름 차트의 `values.yaml` 파일에서 Prometheus와 Grafana의 리소스 요청량(`requests`)과 한도(`limits`)를 Solid Cloud 클러스터 환경에 맞게 하향 조정합니다.

    **`values.yaml` 수정 예시:**
    ```yaml
    prometheus:
      prometheusSpec:
        resources:
          requests:
            cpu: 200m
            memory: 512Mi
          limits:
            cpu: 500m
            memory: 1Gi

    grafana:
      resources:
        requests:
          cpu: 100m
          memory: 256Mi
        limits:
          cpu: 200m
          memory: 512Mi
    ```

    수정 후 `helm upgrade` 명령어로 변경사항을 적용합니다.

*   **PVC 문제 시: StorageClass 설정 확인 및 수정**
    `values.yaml` 파일에서 PVC 관련 설정, 특히 `storageClassName`이 클러스터에서 사용 가능한 이름과 일치하는지 확인하고 수정합니다. 만약 특정 StorageClass를 사용하지 않으려면 `storageClassName`을 `null` 또는 `""`로 설정하여 기본 StorageClass를 사용하도록 할 수 있습니다.

    **`values.yaml` 수정 예시:**
    ```yaml
    prometheus:
      prometheusSpec:
        storageSpec:
          volumeClaimTemplate:
            spec:
              storageClassName: solid-cloud-storage # 클러스터에 맞는 StorageClass 이름으로 변경
              accessModes: ["ReadWriteOnce"]
              resources:
                requests:
                  storage: 20Gi
    ```

## 5. 검증

위 조치를 수행한 후, 다시 `kubectl get pods` 명령어를 실행하여 모든 관련 Pod들이 `Running` 상태로 전환되었는지 확인합니다.

```bash
$ kubectl get pods -n monitoring
NAME                                                        READY   STATUS    RESTARTS   AGE
alertmanager-prometheus-kube-prometheus-alertmanager-0      2/2     Running   0          25m
prometheus-grafana-78d6487c9b-abcde                          3/3     Running   0          2m
prometheus-kube-prometheus-operator-7cdd6f7c64-jzm2b        1/1     Running   0          25m
prometheus-kube-state-metrics-6dbd499b78-v9ggr              1/1     Running   0          25m
prometheus-prometheus-kube-prometheus-prometheus-0          2/2     Running   0          2m
prometheus-prometheus-node-exporter-2v6fg                   1/1     Running   0          25m
prometheus-prometheus-node-exporter-8b2t5                   1/1     Running   0          25m
```

모든 Pod가 정상적으로 실행되면, Grafana 대시보드에 접속하여 메트릭이 수집되고 있는지 최종적으로 확인합니다.

## 6. 교훈

1.  **리소스 요청/한도 설정의 중요성**: Pod 배포 시 리소스 `requests`와 `limits`는 클러스터의 가용 용량에 맞춰 신중하게 설정해야 합니다. 특히 개발 또는 테스트 환경에서는 프로덕션 수준의 높은 값 대신 환경에 맞는 최소한의 값으로 시작하는 것이 효율적입니다.
2.  **PVC와 StorageClass 사전 검증**: 상태 저장 애플리케이션(Stateful Application) 배포 시, PVC가 요구하는 `storageClassName`이 대상 클러스터에 실제로 존재하는지, 그리고 정상적으로 동작하는지 사전에 `kubectl get sc` 명령 등으로 검증하는 절차가 필수적입니다.
3.  **`describe` 명령어의 생활화**: `Pending`, `Error`, `CrashLoopBackOff` 등 비정상 상태의 쿠버네티스 오브젝트를 진단할 때 `kubectl describe` 명령어는 문제의 원인을 파악할 수 있는 가장 기본적인 단서를 제공하므로 습관적으로 사용하는 것이 좋습니다.

package test

import (
	"fmt"
	"strings"
	"testing"
	"time"

	"github.com/gruntwork-io/terratest/modules/k8s"
	"github.com/gruntwork-io/terratest/modules/retry"
	"github.com/gruntwork-io/terratest/modules/terraform"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// TestTerraformGCPDeployment는 실제 GCP에 infrastructure를 배포하고 검증합니다
// 주의: 이 테스트는 실제 GCP 리소스를 생성하므로 비용이 발생합니다
func TestTerraformGCPDeployment(t *testing.T) {
	// 병렬 실행 방지 (GCP quota 문제)
	// t.Parallel()

	// 환경 변수에서 프로젝트 ID 가져오기
	projectID := "titanium-k3s-1765951764"

	terraformOptions := &terraform.Options{
		TerraformDir: "../",

		Vars: map[string]interface{}{
			"project_id":           projectID,
			"region":               "asia-northeast3",
			"zone":                 "asia-northeast3-a",
			"cluster_name":         "terratest-k3s",
			"worker_count":         1,
			"master_machine_type":  "e2-medium",
			"worker_machine_type":  "e2-standard-2",
			"postgres_password":    "terratest-password-12345",
		},

		// 실행 시간 제한 (30분)
		MaxRetries:         2,
		TimeBetweenRetries: 5 * time.Second,
	}

	// 테스트 종료 시 리소스 정리
	defer terraform.Destroy(t, terraformOptions)

	// Terraform init 및 apply
	terraform.InitAndApply(t, terraformOptions)

	// Infrastructure 검증
	t.Run("VerifyInfrastructure", func(t *testing.T) {
		testInfrastructureOutputs(t, terraformOptions)
	})

	// k3s Cluster 접근성 검증
	t.Run("VerifyK3sCluster", func(t *testing.T) {
		testK3sClusterAccess(t, terraformOptions)
	})

	// ArgoCD Applications 검증
	t.Run("VerifyArgoCDApplications", func(t *testing.T) {
		testArgoCDApplications(t, terraformOptions)
	})

	// Monitoring Stack 검증
	t.Run("VerifyMonitoringStack", func(t *testing.T) {
		testMonitoringStack(t, terraformOptions)
	})

	// Grafana Datasource 검증 (방금 수정한 부분)
	t.Run("VerifyGrafanaDatasource", func(t *testing.T) {
		testGrafanaDatasource(t, terraformOptions)
	})
}

// testInfrastructureOutputs는 Terraform outputs을 검증합니다
func testInfrastructureOutputs(t *testing.T, opts *terraform.Options) {
	// Master External IP 검증
	masterIP := terraform.Output(t, opts, "master_external_ip")
	assert.NotEmpty(t, masterIP, "Master external IP should not be empty")
	assert.Regexp(t, `^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$`, masterIP, "Master IP should be valid IPv4")

	// Cluster Endpoint 검증
	clusterEndpoint := terraform.Output(t, opts, "cluster_endpoint")
	assert.Contains(t, clusterEndpoint, masterIP, "Cluster endpoint should contain master IP")
	assert.Contains(t, clusterEndpoint, "6443", "Cluster endpoint should contain k8s API port")

	// Service URLs 검증
	argoCDURL := terraform.Output(t, opts, "argocd_url")
	assert.Contains(t, argoCDURL, masterIP, "ArgoCD URL should contain master IP")
	assert.Contains(t, argoCDURL, "30080", "ArgoCD URL should contain correct port")

	grafanaURL := terraform.Output(t, opts, "grafana_url")
	assert.Contains(t, grafanaURL, masterIP, "Grafana URL should contain master IP")
	assert.Contains(t, grafanaURL, "31300", "Grafana URL should contain correct port")
}

// testK3sClusterAccess는 k3s cluster 접근성을 검증합니다
func testK3sClusterAccess(t *testing.T, opts *terraform.Options) {
	// Bootstrap 완료 대기 (최대 10분)
	maxRetries := 60
	sleepBetweenRetries := 10 * time.Second

	retry.DoWithRetry(t, "Wait for k3s cluster to be ready", maxRetries, sleepBetweenRetries, func() (string, error) {
		// kubeconfig 경로 설정
		kubeconfigPath := "~/.kube/config-gcp"

		// kubectl get nodes 명령 실행
		options := k8s.NewKubectlOptions("", kubeconfigPath, "")

		nodes, err := k8s.RunKubectlAndGetOutputE(t, options, "get", "nodes", "--no-headers")
		if err != nil {
			return "", fmt.Errorf("failed to get nodes: %w", err)
		}

		// 최소 2개의 노드가 있어야 함 (master + 1 worker)
		nodeLines := strings.Split(strings.TrimSpace(nodes), "\n")
		if len(nodeLines) < 2 {
			return "", fmt.Errorf("expected at least 2 nodes, got %d", len(nodeLines))
		}

		// 모든 노드가 Ready 상태인지 확인
		for _, line := range nodeLines {
			if !strings.Contains(line, "Ready") {
				return "", fmt.Errorf("node not ready: %s", line)
			}
		}

		return fmt.Sprintf("Found %d ready nodes", len(nodeLines)), nil
	})
}

// testArgoCDApplications는 ArgoCD applications 상태를 검증합니다
func testArgoCDApplications(t *testing.T, opts *terraform.Options) {
	kubeconfigPath := "~/.kube/config-gcp"
	options := k8s.NewKubectlOptions("", kubeconfigPath, "argocd")

	// Bootstrap 완료 대기
	time.Sleep(2 * time.Minute)

	// 모든 ArgoCD Applications가 생성되었는지 확인
	expectedApps := []string{
		"titanium-prod",
		"loki-stack",
		"istio-base",
		"istiod",
		"istio-ingressgateway",
		"kube-prometheus-stack",
		"kiali",
	}

	for _, appName := range expectedApps {
		retry.DoWithRetry(t, fmt.Sprintf("Wait for ArgoCD app %s", appName), 30, 10*time.Second, func() (string, error) {
			app, err := k8s.RunKubectlAndGetOutputE(t, options, "get", "application", appName, "-o", "jsonpath={.status.health.status}")
			if err != nil {
				return "", fmt.Errorf("app %s not found: %w", appName, err)
			}

			// Healthy 또는 Progressing 상태 허용
			if app != "Healthy" && app != "Progressing" {
				return "", fmt.Errorf("app %s is not healthy: %s", appName, app)
			}

			return fmt.Sprintf("App %s is %s", appName, app), nil
		})
	}
}

// testMonitoringStack는 monitoring stack pods 상태를 검증합니다
func testMonitoringStack(t *testing.T, opts *terraform.Options) {
	kubeconfigPath := "~/.kube/config-gcp"
	options := k8s.NewKubectlOptions("", kubeconfigPath, "monitoring")

	// 모든 pods가 Running 상태가 될 때까지 대기 (최대 10분)
	retry.DoWithRetry(t, "Wait for monitoring pods to be ready", 60, 10*time.Second, func() (string, error) {
		pods, err := k8s.RunKubectlAndGetOutputE(t, options, "get", "pods", "--no-headers")
		if err != nil {
			return "", fmt.Errorf("failed to get pods: %w", err)
		}

		podLines := strings.Split(strings.TrimSpace(pods), "\n")
		notRunningCount := 0

		for _, line := range podLines {
			if !strings.Contains(line, "Running") && !strings.Contains(line, "Completed") {
				notRunningCount++
			}
		}

		if notRunningCount > 0 {
			return "", fmt.Errorf("%d pods are not running yet", notRunningCount)
		}

		return fmt.Sprintf("All %d monitoring pods are running", len(podLines)), nil
	})
}

// testGrafanaDatasource는 Grafana datasource 설정을 검증합니다
// 이 테스트는 방금 수정한 datasource 충돌 문제가 해결되었는지 확인합니다
func testGrafanaDatasource(t *testing.T, opts *terraform.Options) {
	kubeconfigPath := "~/.kube/config-gcp"
	options := k8s.NewKubectlOptions("", kubeconfigPath, "monitoring")

	// Grafana pod 이름 가져오기
	grafanaPod, err := k8s.RunKubectlAndGetOutputE(t, options, "get", "pods", "-l", "app.kubernetes.io/name=grafana", "-o", "jsonpath={.items[0].metadata.name}")
	require.NoError(t, err, "Failed to get Grafana pod name")
	require.NotEmpty(t, grafanaPod, "Grafana pod should exist")

	// Grafana pod가 Running 상태이고 restart가 없는지 확인
	retry.DoWithRetry(t, "Wait for Grafana to be stable", 30, 10*time.Second, func() (string, error) {
		podStatus, err := k8s.RunKubectlAndGetOutputE(t, options, "get", "pod", grafanaPod, "-o", "jsonpath={.status.phase}")
		if err != nil {
			return "", err
		}

		if podStatus != "Running" {
			return "", fmt.Errorf("Grafana pod is not running: %s", podStatus)
		}

		// Restart count 확인
		restarts, err := k8s.RunKubectlAndGetOutputE(t, options, "get", "pod", grafanaPod, "-o", "jsonpath={.status.containerStatuses[0].restartCount}")
		if err != nil {
			return "", err
		}

		if restarts != "0" {
			return "", fmt.Errorf("Grafana pod has restarted %s times", restarts)
		}

		return "Grafana is running without restarts", nil
	})

	// Grafana log에서 datasource 에러 확인
	logs, err := k8s.RunKubectlAndGetOutputE(t, options, "logs", grafanaPod, "-c", "grafana")
	require.NoError(t, err, "Failed to get Grafana logs")

	// Datasource 충돌 에러가 없어야 함
	assert.NotContains(t, logs, "Only one datasource per organization can be marked as default",
		"Grafana should not have datasource conflict error")

	// Datasource sidecar ConfigMap이 생성되지 않았는지 확인
	configMaps, err := k8s.RunKubectlAndGetOutputE(t, options, "get", "configmap", "-l", "grafana_datasource=1", "--no-headers")
	if err == nil && configMaps != "" {
		t.Errorf("Datasource sidecar ConfigMap should not exist, but found: %s", configMaps)
	}

	t.Log("✓ Grafana datasource configuration is correct (no conflicts)")
}

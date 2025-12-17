# Outputs for Solid Cloud Environment - Complete GitOps Automation

# Network Outputs
output "network_id" {
  description = "CloudStack Network ID"
  value       = module.network.network_id
}

output "public_ip" {
  description = "Public IP address for k3s cluster access"
  value       = module.instance.master_public_ip
}

output "master_private_ip" {
  description = "Master node private IP"
  value       = module.instance.master_ip
}

# Cluster Access
output "cluster_endpoint" {
  description = "Kubernetes cluster API endpoint"
  value       = "https://${module.instance.master_public_ip}:6443"
}

output "argocd_url" {
  description = "ArgoCD UI URL"
  value       = "http://${module.instance.master_public_ip}:30080"
}

# Instructions
output "deployment_status" {
  description = "Deployment status and next steps"
  value = <<-EOT
    ✅ Infrastructure Deployment Complete!

    🚀 Automated Bootstrap In Progress:
    The k3s cluster is being automatically configured via cloud-init. This includes:
    - k3s installation (Master + ${var.worker_count} Workers)
    - ArgoCD installation
    - GitOps application deployment
    - PostgreSQL secret creation

    ⏱️  Bootstrap Timeline:
    - k3s installation: ~2-3 minutes
    - ArgoCD installation: ~3-5 minutes
    - Application sync: ~2-3 minutes
    Total: ~10 minutes for complete deployment

    📋 Access Information:

    1. Kubernetes API:
       ${module.instance.master_public_ip}:6443

       Kubeconfig: ~/.kube/config-solid-cloud (template created)
       To get actual kubeconfig with credentials:
       ssh -i ~/.ssh/titanium-key ubuntu@${module.instance.master_public_ip} "sudo cat /etc/rancher/k3s/k3s.yaml" | sed "s/127.0.0.1/${module.instance.master_public_ip}/g" > ~/.kube/config-solid-cloud

    2. ArgoCD UI:
       http://${module.instance.master_public_ip}:30080

       Get admin password:
       kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d

    3. Monitor bootstrap progress:
       ssh -i ~/.ssh/titanium-key ubuntu@${module.instance.master_public_ip}
       tail -f /var/log/k3s-bootstrap.log

    📦 Deployed Applications (via ArgoCD GitOps):
    - titanium-prod: Main application stack
    - loki-stack: Logging and monitoring

    🔍 Verify Deployment:
    # Wait for bootstrap to complete (check log)
    ssh -i ~/.ssh/titanium-key ubuntu@${module.instance.master_public_ip} "tail -f /var/log/k3s-bootstrap.log"

    # Check ArgoCD applications
    kubectl get applications -n argocd

    # Check all pods
    kubectl get pods --all-namespaces

    🎯 All applications are managed by ArgoCD!
    Any changes to https://github.com/DvwN-Lee/Monitoring-v2.git will be automatically synced.
  EOT
}

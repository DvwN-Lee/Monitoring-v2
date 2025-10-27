# Outputs for Solid Cloud Environment

# Network Outputs
output "vpc_id" {
  description = "VPC ID"
  value       = module.network.vpc_id
}

output "public_subnet_ids" {
  description = "Public subnet IDs"
  value       = module.network.public_subnet_ids
}

output "private_subnet_ids" {
  description = "Private subnet IDs"
  value       = module.network.private_subnet_ids
}

# Kubernetes Outputs
output "cluster_endpoint" {
  description = "Kubernetes cluster endpoint"
  value       = module.kubernetes.cluster_endpoint
}

output "namespaces" {
  description = "Created Kubernetes namespaces"
  value       = module.kubernetes.namespaces
}

# Database Outputs
output "postgresql_service" {
  description = "PostgreSQL service details"
  value = {
    name          = module.database.service_name
    port          = module.database.service_port
    database_name = module.database.database_name
  }
}

output "connection_info" {
  description = "Connection information for services"
  value = {
    postgres_host = "${module.database.service_name}.${module.kubernetes.namespaces.titanium_prod}.svc.cluster.local"
    postgres_port = module.database.service_port
    database_name = module.database.database_name
  }
  sensitive = false
}

# Instructions
output "next_steps" {
  description = "Next steps after Terraform apply"
  value = <<-EOT
    ✅ Terraform Apply Complete!

    📋 Next Steps:
    1. Verify PostgreSQL is running:
       kubectl get pods -n ${module.kubernetes.namespaces.titanium_prod}

    2. Test PostgreSQL connection:
       kubectl exec -it postgresql-0 -n ${module.kubernetes.namespaces.titanium_prod} -- psql -U postgres -d titanium -c "\dt"

    3. Update application ConfigMap with PostgreSQL connection:
       POSTGRES_HOST: ${module.database.service_name}
       POSTGRES_PORT: ${module.database.service_port}
       POSTGRES_DB: ${module.database.database_name}

    4. Apply Kustomize overlays:
       kubectl apply -k ../../k8s-manifests/overlays/solid-cloud

    5. Check service status:
       kubectl get pods,svc -n ${module.kubernetes.namespaces.titanium_prod}
  EOT
}

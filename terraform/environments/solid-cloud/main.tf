# Solid Cloud Environment - Main Configuration
# CloudStack API + k3s Self-Managed Kubernetes Cluster

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    cloudstack = {
      source  = "cloudstack/cloudstack"
      version = "~> 0.6"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.12"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
  }

  # Backend configuration for remote state (optional)
  # backend "s3" {
  #   bucket = "titanium-terraform-state"
  #   key    = "solid-cloud/terraform.tfstate"
  #   region = "us-east-1"
  # }
}

# CloudStack Provider Configuration
provider "cloudstack" {
  api_url    = var.cloudstack_api_url
  api_key    = var.cloudstack_api_key
  secret_key = var.cloudstack_secret_key
}

# Network Module - CloudStack Isolated Network
module "network" {
  source = "../../modules/network"

  network_name     = "${var.cluster_name}-network"
  cidr             = var.network_cidr
  zone             = var.zone
  network_offering = var.network_offering
}

# Instance Module - k3s Cluster (1 Master + 2 Workers)
module "instance" {
  source = "../../modules/instance"

  cluster_name     = var.cluster_name
  zone             = var.zone
  service_offering = var.service_offering
  template         = var.template
  network_id       = module.network.network_id
  ssh_keypair      = var.ssh_keypair
  worker_count     = var.worker_count

  depends_on = [module.network]
}

# Kubernetes Provider - Connect to k3s Cluster
provider "kubernetes" {
  config_path = "~/.kube/config-solid-cloud"
}

provider "helm" {
  kubernetes {
    config_path = "~/.kube/config-solid-cloud"
  }
}

# Kubernetes Module - Namespaces and Resource Quotas
module "kubernetes" {
  source = "../../modules/kubernetes"

  cluster_name       = var.cluster_name
  node_count         = var.worker_count + 1  # master + workers
  node_instance_type = var.service_offering

  # Application Secrets
  postgres_password   = var.postgres_password
  jwt_secret_key      = var.jwt_secret_key
  internal_api_secret = var.internal_api_secret
  redis_password      = var.redis_password

  depends_on = [module.instance]
}

# PostgreSQL Database Module
module "database" {
  source = "../../modules/database"

  namespace         = module.kubernetes.namespaces.titanium_prod
  postgres_version  = var.postgres_version
  storage_size      = var.postgres_storage_size
  postgres_password = var.postgres_password

  depends_on = [module.kubernetes]
}

# Monitoring Stack Module (Loki, Promtail)
module "monitoring" {
  source = "../../modules/monitoring"

  namespace          = "monitoring"
  loki_version       = "2.10.2"
  loki_storage_size  = "10Gi"

  depends_on_resources = [module.kubernetes]
}

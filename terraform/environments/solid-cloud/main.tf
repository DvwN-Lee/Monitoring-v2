# Solid Cloud Environment - Main Configuration
# Week 1: Infrastructure Foundation

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"
    }
  }

  # Backend configuration for remote state (optional)
  # backend "s3" {
  #   bucket = "titanium-terraform-state"
  #   key    = "solid-cloud/terraform.tfstate"
  #   region = "us-east-1"
  # }
}

# Provider Configuration
# kubeconfig path can be supplied via TF_VAR_kubeconfig_path or defaults to ~/.kube/config
locals {
  resolved_kubeconfig_path = length(trimspace(var.kubeconfig_path)) > 0 ? pathexpand(var.kubeconfig_path) : pathexpand("~/.kube/config")
}

provider "kubernetes" {
  # Option 1: Use kubeconfig file
  config_path = local.resolved_kubeconfig_path

  # Option 2: Use explicit configuration
  # host                   = var.kubernetes_host
  # client_certificate     = var.kubernetes_client_certificate
  # client_key             = var.kubernetes_client_key
  # cluster_ca_certificate = var.kubernetes_cluster_ca_certificate
}

# Network Module
# Note: Currently using placeholder, implement based on Solid Cloud provider
module "network" {
  source = "../../modules/network"

  cluster_name         = var.cluster_name
  vpc_cidr             = var.vpc_cidr
  public_subnet_cidrs  = var.public_subnet_cidrs
  private_subnet_cidrs = var.private_subnet_cidrs
}

# Kubernetes Cluster Module
module "kubernetes" {
  source = "../../modules/kubernetes"

  cluster_name        = var.cluster_name
  node_count          = var.node_count
  node_instance_type  = var.node_instance_type
}

# PostgreSQL Database Module
module "database" {
  source = "../../modules/database"

  namespace         = module.kubernetes.namespaces.titanium_prod
  postgres_version  = var.postgres_version
  storage_size      = var.postgres_storage_size
  postgres_password = var.postgres_password

  # Ensure namespace is created first
  depends_on = [module.kubernetes]
}

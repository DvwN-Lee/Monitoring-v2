# Solid Cloud Environment - Complete GitOps Automation
# Terraform manages only infrastructure (VMs, network)
# k3s + ArgoCD + Applications are bootstrapped via cloud-init

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    cloudstack = {
      source  = "cloudstack/cloudstack"
      version = "~> 0.6"
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

# Network Module - CloudStack Isolated Network with Egress Firewall
module "network" {
  source = "../../modules/network"

  network_name     = "${var.cluster_name}-network"
  cidr             = var.network_cidr
  zone             = var.zone
  network_offering = var.network_offering
}

# Instance Module - k3s Cluster with Complete Bootstrap
# This module creates VMs and runs cloud-init to install:
# - k3s cluster
# - ArgoCD
# - ArgoCD Applications (GitOps)
# - PostgreSQL secret
module "instance" {
  source = "../../modules/instance"

  cluster_name      = var.cluster_name
  zone              = var.zone
  service_offering  = var.service_offering
  template          = var.template
  network_id        = module.network.network_id
  ssh_keypair       = var.ssh_keypair
  worker_count      = var.worker_count
  postgres_password = var.postgres_password

  depends_on = [module.network]
}

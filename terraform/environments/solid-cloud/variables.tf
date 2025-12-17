# Variables for Solid Cloud Environment

# CloudStack API Configuration
variable "cloudstack_api_url" {
  description = "CloudStack API endpoint URL"
  type        = string
}

variable "cloudstack_api_key" {
  description = "CloudStack API key"
  type        = string
  sensitive   = true
}

variable "cloudstack_secret_key" {
  description = "CloudStack secret key"
  type        = string
  sensitive   = true
}

# Cluster Configuration
variable "cluster_name" {
  description = "Name of the Kubernetes cluster"
  type        = string
  default     = "solid-cloud-k3s"
}

variable "zone" {
  description = "CloudStack zone name"
  type        = string
  default     = "DKU"
}

variable "service_offering" {
  description = "CloudStack service offering for nodes"
  type        = string
  default     = "Medium"
}

variable "template" {
  description = "CloudStack template name for Ubuntu 22.04"
  type        = string
}

variable "ssh_keypair" {
  description = "CloudStack SSH keypair name"
  type        = string
}

variable "worker_count" {
  description = "Number of worker nodes"
  type        = number
  default     = 2
}

# Network Configuration
variable "network_cidr" {
  description = "CIDR block for isolated network"
  type        = string
  default     = "10.100.0.0/24"
}

variable "network_offering" {
  description = "CloudStack network offering name"
  type        = string
}

# PostgreSQL Configuration
variable "postgres_version" {
  description = "PostgreSQL version"
  type        = string
  default     = "15-alpine"
}

variable "postgres_storage_size" {
  description = "Storage size for PostgreSQL"
  type        = string
  default     = "10Gi"
}

variable "postgres_password" {
  description = "PostgreSQL root password"
  type        = string
  sensitive   = true
}

# Application Secrets Configuration
variable "jwt_secret_key" {
  description = "JWT secret key for authentication"
  type        = string
  sensitive   = true
  default     = "jwt-signing-key"
}

variable "internal_api_secret" {
  description = "Internal API secret for service communication"
  type        = string
  sensitive   = true
  default     = "api-secret-key"
}

variable "redis_password" {
  description = "Redis password"
  type        = string
  sensitive   = true
  default     = "redis-password"
}

# Environment Tags
variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "project" {
  description = "Project name"
  type        = string
  default     = "titanium"
}

variable "managed_by" {
  description = "Tool managing the infrastructure"
  type        = string
  default     = "terraform"
}

# Kubernetes Configuration
variable "kubeconfig_path" {
  description = "Path to kubeconfig file for k3s cluster"
  type        = string
  default     = "~/.kube/config-solid-cloud"
}

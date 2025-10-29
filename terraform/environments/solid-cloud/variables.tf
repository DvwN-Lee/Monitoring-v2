# Variables for Solid Cloud Environment

# Cluster Configuration
variable "cluster_name" {
  description = "Name of the Kubernetes cluster"
  type        = string
  default     = "titanium-cluster"
}

variable "node_count" {
  description = "Number of nodes in the Kubernetes cluster"
  type        = number
  default     = 3
}

variable "node_instance_type" {
  description = "Instance type for Kubernetes nodes"
  type        = string
  default     = "t3.medium"
}

# Network Configuration
variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets"
  type        = list(string)
  default     = ["10.0.11.0/24", "10.0.12.0/24", "10.0.13.0/24"]
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

# Kubernetes Provider Configuration
variable "kubeconfig_path" {
  description = "Path to kubeconfig file"
  type        = string
  default     = ""
}

variable "kubernetes_host" {
  description = "Kubernetes API server host (if not using kubeconfig)"
  type        = string
  default     = ""
}

variable "kubernetes_client_certificate" {
  description = "Kubernetes client certificate"
  type        = string
  default     = ""
  sensitive   = true
}

variable "kubernetes_client_key" {
  description = "Kubernetes client key"
  type        = string
  default     = ""
  sensitive   = true
}

variable "kubernetes_cluster_ca_certificate" {
  description = "Kubernetes cluster CA certificate"
  type        = string
  default     = ""
  sensitive   = true
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

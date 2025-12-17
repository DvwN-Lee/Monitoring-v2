# GCP Environment - Complete GitOps Automation
# Terraform manages infrastructure (VPC, VMs)
# k3s + ArgoCD + Applications are bootstrapped via startup script

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
  }
}

# GCP Provider Configuration
provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

# VPC Network
resource "google_compute_network" "vpc" {
  name                    = "${var.cluster_name}-vpc"
  auto_create_subnetworks = false
}

# Subnet
resource "google_compute_subnetwork" "subnet" {
  name          = "${var.cluster_name}-subnet"
  ip_cidr_range = var.subnet_cidr
  region        = var.region
  network       = google_compute_network.vpc.id
}

# Firewall Rules - Allow SSH, k8s API, HTTP, Dashboards
resource "google_compute_firewall" "allow_ssh" {
  name    = "${var.cluster_name}-allow-ssh"
  network = google_compute_network.vpc.name

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["k3s-master"]
}

resource "google_compute_firewall" "allow_k8s_api" {
  name    = "${var.cluster_name}-allow-k8s-api"
  network = google_compute_network.vpc.name

  allow {
    protocol = "tcp"
    ports    = ["6443"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["k3s-master"]
}

resource "google_compute_firewall" "allow_dashboards" {
  name    = "${var.cluster_name}-allow-dashboards"
  network = google_compute_network.vpc.name

  allow {
    protocol = "tcp"
    ports    = ["80", "30080", "31200", "31300", "32491"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["k3s-master"]
}

# Internal communication between cluster nodes
resource "google_compute_firewall" "allow_internal" {
  name    = "${var.cluster_name}-allow-internal"
  network = google_compute_network.vpc.name

  allow {
    protocol = "tcp"
    ports    = ["0-65535"]
  }

  allow {
    protocol = "udp"
    ports    = ["0-65535"]
  }

  allow {
    protocol = "icmp"
  }

  source_ranges = [var.subnet_cidr]
}

# Generate random token for k3s cluster
resource "random_password" "k3s_token" {
  length  = 32
  special = false
}

# External IP for master node
resource "google_compute_address" "master_external_ip" {
  name = "${var.cluster_name}-master-ip"
}

# k3s Master Node
resource "google_compute_instance" "k3s_master" {
  name         = "${var.cluster_name}-master"
  machine_type = var.master_machine_type
  zone         = var.zone

  tags = ["k3s-master"]

  boot_disk {
    initialize_params {
      image = var.os_image
      size  = 50
      type  = "pd-standard"
    }
  }

  network_interface {
    subnetwork = google_compute_subnetwork.subnet.id

    access_config {
      nat_ip = google_compute_address.master_external_ip.address
    }
  }

  metadata = {
    ssh-keys = "ubuntu:${file(var.ssh_public_key_path)}"
  }

  metadata_startup_script = templatefile("${path.module}/scripts/k3s-server.sh", {
    k3s_token         = random_password.k3s_token.result
    postgres_password = var.postgres_password
  })

  service_account {
    scopes = ["cloud-platform"]
  }
}

# k3s Worker Nodes
resource "google_compute_instance" "k3s_worker" {
  count        = var.worker_count
  name         = "${var.cluster_name}-worker-${count.index + 1}"
  machine_type = var.worker_machine_type
  zone         = var.zone

  tags = ["k3s-worker"]

  boot_disk {
    initialize_params {
      image = var.os_image
      size  = 30
      type  = "pd-standard"
    }
  }

  network_interface {
    subnetwork = google_compute_subnetwork.subnet.id
  }

  metadata = {
    ssh-keys = "ubuntu:${file(var.ssh_public_key_path)}"
  }

  metadata_startup_script = templatefile("${path.module}/scripts/k3s-agent.sh", {
    master_ip = google_compute_instance.k3s_master.network_interface[0].network_ip
    k3s_token = random_password.k3s_token.result
  })

  service_account {
    scopes = ["cloud-platform"]
  }

  depends_on = [google_compute_instance.k3s_master]
}

# Create local kubeconfig template
resource "null_resource" "create_kubeconfig" {
  depends_on = [google_compute_instance.k3s_master]

  provisioner "local-exec" {
    command = <<-EOT
      mkdir -p ~/.kube
      cat > ~/.kube/config-gcp <<'KUBE'
apiVersion: v1
kind: Config
clusters:
- cluster:
    insecure-skip-tls-verify: true
    server: https://${google_compute_address.master_external_ip.address}:6443
  name: gcp-k3s
contexts:
- context:
    cluster: gcp-k3s
    user: gcp-k3s-admin
  name: gcp-k3s
current-context: gcp-k3s
users:
- name: gcp-k3s-admin
  user:
    username: admin
    password: placeholder
KUBE
      echo "Kubeconfig template created at ~/.kube/config-gcp"
      echo "Note: This is a placeholder. Access cluster after k3s bootstrap completes (~5-10 min)"
      echo "To get actual kubeconfig, SSH into master and run: sudo cat /etc/rancher/k3s/k3s.yaml"
    EOT
  }

  triggers = {
    master_ip = google_compute_address.master_external_ip.address
  }
}

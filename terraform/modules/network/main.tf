# Network Module - CloudStack Isolated Network

terraform {
  required_providers {
    cloudstack = {
      source  = "cloudstack/cloudstack"
      version = "~> 0.6"
    }
  }
}

resource "cloudstack_network" "main" {
  name             = var.network_name
  cidr             = var.cidr
  network_offering = var.network_offering
  zone             = var.zone
  gateway          = cidrhost(var.cidr, 1)
  startip          = cidrhost(var.cidr, 10)
  endip            = cidrhost(var.cidr, 250)
}

# Egress Firewall Rules - Allow outbound internet access
resource "cloudstack_egress_firewall" "allow_all" {
  network_id = cloudstack_network.main.id

  rule {
    protocol   = "all"
    cidr_list  = ["0.0.0.0/0"]
  }
}

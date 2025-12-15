#!/bin/bash
set -e

# k3s Server Installation Script
# This script runs on the master node via cloud-init

# Get private and public IP addresses
PRIVATE_IP=$(hostname -I | awk '{print $1}')

# Wait for metadata service to be available and get public IP
echo "Retrieving public IP from metadata..."
for i in {1..30}; do
  PUBLIC_IP=$(curl -sf -H "DomainId: 1" http://data-server.cloudstack.internal/latest/meta-data/public-ipv4 2>/dev/null || echo "")
  if [ -n "$PUBLIC_IP" ]; then
    echo "Public IP: $PUBLIC_IP"
    break
  fi
  echo "Waiting for metadata service... attempt $i/30"
  sleep 2
done

# Install k3s server with both private and public IPs as TLS SANs
if [ -n "$PUBLIC_IP" ]; then
  echo "Installing k3s with TLS SAN for $PRIVATE_IP and $PUBLIC_IP"
  curl -sfL https://get.k3s.io | K3S_TOKEN="${k3s_token}" sh -s - server \
    --write-kubeconfig-mode 644 \
    --disable traefik \
    --tls-san "$PRIVATE_IP" \
    --tls-san "$PUBLIC_IP"
else
  echo "Public IP not available, installing k3s with only private IP"
  curl -sfL https://get.k3s.io | K3S_TOKEN="${k3s_token}" sh -s - server \
    --write-kubeconfig-mode 644 \
    --disable traefik \
    --tls-san "$PRIVATE_IP"
fi

# Wait for k3s to be ready
echo "Waiting for k3s server to be ready..."
sleep 30

# Verify k3s is running
systemctl status k3s || true

# Mark installation complete
echo "k3s-server-ready" > /tmp/k3s-status

echo "k3s server installation completed"

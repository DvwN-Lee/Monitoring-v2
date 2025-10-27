# Solid Cloud Overlay

Kustomize overlay for Solid Cloud production environment.

## 🔐 Setup Instructions

### 1. Create Secret File

**IMPORTANT**: The `secret-patch.yaml` file is gitignored for security. You must create it manually:

```bash
cd k8s-manifests/overlays/solid-cloud

# Copy the example file
cp secret-patch.yaml.example secret-patch.yaml

# Edit with actual values
vi secret-patch.yaml
```

### 2. Generate Base64 Encoded Secrets

```bash
# PostgreSQL User
echo -n "postgres" | base64
# Output: cG9zdGdyZXM=

# PostgreSQL Password (use a strong password!)
echo -n "YOUR_SECURE_PASSWORD_HERE" | base64

# JWT Secret Key
echo -n "production-jwt-secret-key-$(openssl rand -hex 32)" | base64

# Internal API Secret
echo -n "production-api-secret-$(openssl rand -hex 32)" | base64
```

### 3. Update secret-patch.yaml

Replace the placeholder values in `secret-patch.yaml` with your generated base64 values.

### 4. Deploy to Kubernetes

```bash
# From project root
kubectl apply -k k8s-manifests/overlays/solid-cloud

# Verify deployment
kubectl get pods -n titanium-prod
kubectl get svc -n titanium-prod
```

## 📋 What's Configured

### Namespace
- `titanium-prod`: Production namespace

### ConfigMap Patches
- PostgreSQL connection settings
- Production service URLs (with `prod-` prefix)
- Environment set to `production`

### Secret Patches
- PostgreSQL credentials
- JWT signing key
- Internal API secrets

### Service Patches
- Load Balancer service type for external access

### Deployment Patches
- PostgreSQL environment variables for user-service
- PostgreSQL environment variables for blog-service
- Removed SQLite volumes and mounts

## 🧪 Testing

```bash
# Test PostgreSQL connection
kubectl exec -it postgresql-0 -n titanium-prod -- psql -U postgres -d titanium

# Check service endpoints
kubectl get svc -n titanium-prod

# View logs
kubectl logs -f deployment/prod-user-service-deployment -n titanium-prod
kubectl logs -f deployment/prod-blog-service-deployment -n titanium-prod
```

## 🔄 Updating

```bash
# After making changes to manifests
kubectl apply -k k8s-manifests/overlays/solid-cloud

# Force rollout restart
kubectl rollout restart deployment/prod-user-service-deployment -n titanium-prod
kubectl rollout restart deployment/prod-blog-service-deployment -n titanium-prod
```

## 🗑️ Cleanup

```bash
# Delete all resources
kubectl delete -k k8s-manifests/overlays/solid-cloud

# Delete namespace (will delete all resources in it)
kubectl delete namespace titanium-prod
```

## 🔒 Security Notes

- **Never commit `secret-patch.yaml`** to version control
- Use strong, randomly generated passwords
- Rotate secrets regularly
- Use Kubernetes RBAC to limit access to secrets
- Consider using external secret management (e.g., Vault, AWS Secrets Manager)

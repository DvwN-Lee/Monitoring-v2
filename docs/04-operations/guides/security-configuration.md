# Security Configuration Guide

**Phase:** Phase 4 (Operations & Hardening)
**Applied Components:** Application, API Gateway, Infrastructure

---

## 1. CORS (Cross-Origin Resource Sharing)

웹 브라우저 보안 정책을 강화하기 위해 Wildcard(`*`)를 제거하고 명시적인 도메인만 허용하도록 변경했습니다.

### 1.1. 설정 내용
- **환경 변수:** `ALLOWED_ORIGINS`
- **허용 도메인 (Production):** `https://titanium.example.com`
- **적용 대상:** Blog Service, Auth Service

### 1.2. 구현 코드 (Example)
```python
# blog-service/blog_service.py
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)
```

---

## 2. Istio mTLS (Mutual TLS)

Service 간 통신 암호화를 위해 Istio Service Mesh의 mTLS를 강화했습니다.

### 2.1. 설정 상태
- **Mode:** `STRICT` (권장)
- **Namespace:** `titanium-prod`
- **Injection:** `istio-injection=enabled` 라벨 적용 완료

### 2.2. 예외 처리
Database(PostgreSQL)와 같은 외부 서비스나 Sidecar가 없는 서비스와의 통신을 위해 `DestinationRule`을 사용하여 적절한 TLS 모드(DISABLE or PERMISSIVE)를 설정할 수 있습니다.

---

## 3. Secret 관리

민감 정보(Password, API Key)의 코드 내 하드코딩을 제거했습니다.

### 3.1. Terraform
- **조치:** `terraform.tfvars` 내의 민감 값을 제거하고, 환경 변수(`TF_VAR_...`)를 통해 주입받도록 변경했습니다.
- **관리 대상:** CloudStack API Key/Secret, VM Password, JWT Secret.

### 3.2. Kubernetes
- **조치:** Application Secret을 Kubernetes `Secret` 리소스로 관리하며, Pod에는 환경 변수로 마운트됩니다.

---

## 4. Dashboard 접근 제어 (Monitoring)

Grafana 및 Kiali 대시보드는 Public Internet에 직접 노출하지 않고, 제한된 접근 경로를 제공합니다.

### 4.1. Port Forwarding
CloudStack의 Port Forwarding 기능을 사용하여 특정 포트만 외부로 노출했습니다.
- **Grafana:** Port `31300`
- **Kiali:** Port `31200`

### 4.2. Firewall (CIDR Restriction)
`terraform/environments/solid-cloud/variables.tf`의 `allowed_ssh_cidrs` 변수를 사용하여, 승인된 IP 대역(VPN 등)에서만 관리 포트(SSH, Dashboard)에 접근할 수 있도록 방화벽 규칙을 적용했습니다.

```hcl
# main.tf (Firewall Rule)
resource "cloudstack_firewall" "master" {
  ip_address_id = cloudstack_ipaddress.master_public_ip.id
  rule {
    protocol  = "tcp"
    cidr_list = var.allowed_ssh_cidrs # Restricted IP List
    ports     = ["22", "6443", "31300", "31200"]
  }
}
```

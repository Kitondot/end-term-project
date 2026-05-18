# End Term Project — SRE Microservices System

## Services
| Service              | Port |
|----------------------|------|
| Auth Service         | 8001 |
| Product Service      | 8002 |
| Order Service        | 8003 |
| User Service         | 8004 |
| Payment Service      | 8006 |
| Notification Service | 8007 |
| Frontend             | 80   |
| Prometheus           | 9090 |
| Grafana              | 3000 |

## Quick Start

### 1. Run with Docker Compose
```bash
docker compose up --build -d
docker compose ps
```

### 2. Docker Swarm
```bash
docker swarm init
docker stack deploy -c docker-compose.yml myapp
docker service ls
```

### 3. Kubernetes
```bash
minikube start
kubectl apply -f kubernetes/namespace.yml
kubectl apply -f kubernetes/configmap.yml
kubectl apply -f kubernetes/postgres.yml
kubectl apply -f kubernetes/auth-service.yml
kubectl apply -f kubernetes/order-service.yml
kubectl apply -f kubernetes/payment-service.yml
kubectl get pods -n microservices
```

### 4. Terraform
```bash
cd terraform
terraform init
terraform plan
terraform apply
```

### 5. Ansible
```bash
cd ansible
ansible-playbook -i inventory.ini playbook.yml
```

## Monitoring
- Grafana: http://localhost:3000 — admin / admin123
- Prometheus: http://localhost:9090
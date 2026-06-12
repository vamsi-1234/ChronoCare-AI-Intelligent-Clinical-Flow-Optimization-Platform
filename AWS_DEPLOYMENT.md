
# ChronoCare AI – Deployment Guide

## Local Docker Compose (quickest end-to-end test)

```bash
# 1. Copy env template and set a real DB password
cp .env.example .env
#    edit .env → set POSTGRES_PASSWORD and CORS_ORIGINS

# 2. Train models (first time only – produces models/*.pkl)
python scripts/generate_data.py --n 5000
python scripts/train_models.py

# 3. Start the full stack (API + frontend + Postgres + Redis)
docker compose up --build
```

Frontend: http://localhost:3000  
API docs: http://localhost:8000/docs

---

## AWS ECS / Fargate (recommended production path)

### Prerequisites
- AWS CLI configured (`aws configure`)
- Docker installed locally
- An ECR registry per image (backend + frontend)

### 1 – Build & push backend image

```bash
REGION=us-east-1
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
BACKEND_REPO=$ACCOUNT.dkr.ecr.$REGION.amazonaws.com/chronocare-api

aws ecr create-repository --repository-name chronocare-api --region $REGION
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $BACKEND_REPO

docker build -t chronocare-api .
docker tag  chronocare-api:latest $BACKEND_REPO:latest
docker push $BACKEND_REPO:latest
```

### 2 – Build & push frontend image

```bash
FRONTEND_REPO=$ACCOUNT.dkr.ecr.$REGION.amazonaws.com/chronocare-frontend
aws ecr create-repository --repository-name chronocare-frontend --region $REGION

docker build -t chronocare-frontend ./frontend
docker tag  chronocare-frontend:latest $FRONTEND_REPO:latest
docker push $FRONTEND_REPO:latest
```

### 3 – Infrastructure checklist

| Resource | Notes |
|---|---|
| **RDS PostgreSQL 15** | Store `DATABASE_URL` in AWS Secrets Manager |
| **ElastiCache Redis 7** | Store `REDIS_URL` in Secrets Manager |
| **ECS Cluster (Fargate)** | Run backend task; pass secrets as env vars via task definition |
| **ALB** | HTTPS listener (ACM cert) → target group on port 8000 (API) and 3000 (frontend) |
| **S3 + CloudFront** | Alternative: deploy frontend `dist/` as a static site; set `VITE_API_URL` build arg to the ALB URL |
| **EFS / S3** | Mount `models/` volume so trained `.pkl` files survive task restarts |
| **ECR lifecycle policy** | Keep last 5 images to control storage costs |

### 4 – Environment variables (task definition)

Set these in the ECS task definition (sourced from Secrets Manager or Parameter Store):

```
DATABASE_URL          → postgresql://chronocare:<password>@<rds-endpoint>:5432/chronocare
REDIS_URL             → redis://<elasticache-endpoint>:6379
CORS_ORIGINS          → https://your-frontend-domain.com
LOG_LEVEL             → INFO
ENABLE_AUTH           → true
API_KEYS              → <generate with: python -c "import secrets; print(secrets.token_urlsafe(32))">
POSTGRES_PASSWORD     → (same password used in DATABASE_URL)
```

### 5 – Model storage

Trained `.pkl` files must be available to the container at startup.  
Two options:

**A. Bake into image** (simple, rebuild on retrain):
```dockerfile
COPY models/ /app/models/
```

**B. S3 mount** (recommended for production):
```bash
# Upload after training
aws s3 cp models/duration_model.pkl s3://your-bucket/models/
aws s3 cp models/noshow_model.pkl   s3://your-bucket/models/

# Download at container startup (add to Dockerfile CMD or entrypoint):
aws s3 sync s3://your-bucket/models/ /app/models/
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 6 – Enable authentication

```bash
# Generate a secure key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Set in task definition
ENABLE_AUTH=true
API_KEYS=<generated-key>

# Frontend passes key automatically if you set in the Vite build:
# VITE_API_KEY=<generated-key>
```

---

## EC2 + Docker (simpler, single instance)

```bash
# On a fresh Ubuntu 22.04 EC2 instance (t3.medium or larger):
sudo apt update && sudo apt install -y docker.io docker-compose-v2 git
sudo usermod -aG docker ubuntu && newgrp docker

git clone <your-repo-url> && cd ChronoCare-AI-Intelligent-Clinical-Flow-Optimization-Platform
cp .env.example .env  # then edit .env with production values

python3 scripts/generate_data.py --n 5000
python3 scripts/train_models.py

docker compose up -d --build
```

Open ports 80/443 in the EC2 security group. Use **nginx** or **Caddy** as a reverse proxy for TLS.

---

## What's NOT production-ready (known limitations)

| Item | Impact | Fix |
|---|---|---|
| **In-memory appointments store** | Appointments reset on restart | Persist to the PostgreSQL DB using the existing ORM models |
| **No test suite** | Regressions undetected | Add `pytest` tests under `app/tests/` |
| **No-show AUC 0.64** | Model is indicative, not clinical-grade | Retrain on real EHR data |
| **Single uvicorn worker in dev** | Low throughput | `--workers 4` is set in the production Dockerfile |
| **Frontend bundle 998 KB** | Slower initial load | Add `React.lazy` / dynamic imports for each page |


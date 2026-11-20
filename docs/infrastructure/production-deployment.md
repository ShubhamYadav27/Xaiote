# Production Deployment Runbook

## 1. Pre-Deployment Verification Checklist

Before initiating a production release:
- [ ] All unit, STT, and regression tests pass locally: `pytest`.
- [ ] No git diff in uncommitted local files.
- [ ] Local schema matches latest Alembic revision: `alembic current` == `alembic heads`.
- [ ] No hardcoded API keys, JWTs, or passwords in source code.
- [ ] Docker daemon is running with multi-platform support (`linux/amd64`).
- [ ] AWS CLI configured with active credentials for AWS account `394920712303` (region: `ap-south-1`).

---

## 2. Step-by-Step Deployment Procedure

### Step 1: Build & Tag Container Image
Production containers run on AWS Fargate (`linux/amd64`). Build using standard multi-arch build commands:
```powershell
cd c:\Xaiote\backend

# Define version tag based on Git commit SHA
$GIT_SHA = (git rev-parse --short HEAD)
$ECR_REPO = "394920712303.dkr.ecr.ap-south-1.amazonaws.com/xaiote-backend"

# Build image for x86_64 Fargate
docker build --platform linux/amd64 -t "${ECR_REPO}:${GIT_SHA}" -t "${ECR_REPO}:latest" .
```

### Step 2: Authenticate to ECR & Push Image
```powershell
aws ecr get-login-password --region ap-south-1 | docker login --username AWS --password-stdin 394920712303.dkr.ecr.ap-south-1.amazonaws.com

# Push both commit SHA and latest tags
docker push "${ECR_REPO}:${GIT_SHA}"
docker push "${ECR_REPO}:latest"
```

### Step 3: Execute Controlled Alembic Database Migration
*Execute schema migration once as an isolated task before updating the long-running ECS service:*
```powershell
# Run one-off ECS migration task or execute via bastion using backend venv:
cd c:\Xaiote\backend
alembic upgrade head
```
Verify output:
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
Running upgrade ... -> f33a7c860f9c, add_alert_eval_job_retry_audit
```
Confirm current revision matches HEAD:
```powershell
alembic current
```

### Step 4: Register Updated ECS Task Definition
If environment variables or IAM role mappings changed, register a new task definition revision:
```powershell
cd c:\Xaiote
aws ecs register-task-definition --cli-input-json file://task-def.json --region ap-south-1
```

### Step 5: Trigger Canary Deployment on ECS Service
```powershell
aws ecs update-service `
  --cluster default `
  --service xaiote-backend `
  --force-new-deployment `
  --region ap-south-1
```

### Step 6: Monitor Deployment & Canary Bake Window
ECS routes 5% of traffic to the new task revision for 3 minutes. Monitor CloudWatch logs:
```powershell
aws logs tail /ecs/xaiote-backend --follow --region ap-south-1
```
Check rollout status:
```powershell
aws ecs describe-services --cluster default --services xaiote-backend --region ap-south-1 --query "services[0].deployments"
```
Wait until the primary deployment achieves status `PRIMARY` with 100% traffic allocation.

### Step 7: Execute Production API Smoke Test
Run the automated production verification script against `https://api.xaiote.com`:
```powershell
cd c:\Xaiote\backend
python test_regression.py
```
Expected output:
```
login: 200
me: 200
customers: 200
plants: 200
machines: 200
products: 200
work_orders: 200
manufacturing_events: 200
incidents: 200
```

### Step 8: Deploy Frontend via AWS Amplify
The frontend automatically triggers a build upon pushing to the production branch:
```powershell
git push origin main
```
Alternatively, trigger a manual build in the AWS Amplify Console under `xaiote-frontend`.
Once built, verify [https://xaiote.com](https://xaiote.com) and [https://xaiote.com/incidents](https://xaiote.com/incidents).

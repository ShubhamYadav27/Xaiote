# Cloud Infrastructure & Deployment Architecture

## 1. Cloud Architecture Overview

Xaiote's production infrastructure is deployed in the **AWS Asia Pacific (Mumbai) region (`ap-south-1`)**. The platform utilizes a decoupled, cloud-native architecture combining serverless container compute, edge-hosted frontend assets, managed relational clustering, and managed object storage.

```mermaid
flowchart TD
    subgraph PublicInternet ["Public Internet & Client Traffic"]
        UserClients["Shop Floor Operators & Plant Managers"]
        WhatsAppWebhook["Meta WhatsApp Cloud API Webhook"]
    end

    subgraph DNSLayer ["DNS & TLS (AWS Route 53 & ACM)"]
        ApexDNS["xaiote.com / www.xaiote.com (Route 53)"]
        ApiDNS["api.xaiote.com (Route 53 CNAME)"]
    end

    subgraph FrontendHosting ["Frontend Hosting (AWS Amplify Hosting)"]
        AmplifyEdge["AWS Amplify Edge Network (Node.js 20, Next.js 15)"]
    end

    subgraph IngressLayer ["Ingress & Load Balancing (AWS VPC ap-south-1)"]
        ALB["AWS Application Load Balancer<br/>Listeners: HTTPS:443 (ACM Certificate)<br/>Rule: Host-Header 'api.xaiote.com'"]
        TG_Blue["Target Group A: ecs-gateway-tg-49020a939b828ba4c"]
        TG_Green["Target Group B: ecs-gateway-tg-26e95a9adce6e9370"]
    end

    subgraph ComputeLayer ["Serverless Container Compute (AWS ECS Fargate)"]
        subgraph ECSCluster ["ECS Cluster: default"]
            ECSService["ECS Service: xaiote-backend<br/>Strategy: CANARY (5% bake 3m)<br/>Deployment Circuit Breaker: Active"]
            Task1["Fargate Task Replica 1 (512 CPU / 1024 MB)<br/>FastAPI API + Asyncio Worker Pool"]
        end
    end

    subgraph ConfigSecurity ["Security & Identity (AWS IAM & Secrets Manager)"]
        SecretsMgr["AWS Secrets Manager:<br/>arn:...:secret:xaiote/production-aAx408"]
        TaskRole["IAM Task Role:<br/>xaiote-backend-task-role"]
        ExecRole["IAM Execution Role:<br/>ecsTaskExecutionRole"]
        CWLogs["CloudWatch Logs:<br/>/ecs/xaiote-backend"]
    end

    subgraph DataStorageLayer ["Data Tier & External Services"]
        SupabaseDB[("PostgreSQL 15 Managed Cluster<br/>(Supabase AWS ap-south-1 Pooler)")]
        ObjectStore[("S3 / MinIO Object Storage<br/>(Bucket: xaiote-evidence)")]
        SarvamCloud["Sarvam AI Cloud (saaras:v4)"]
        OpenAICloud["OpenAI API (gpt-4o-mini)"]
    end

    UserClients -->|"HTTPS (xaiote.com)"| ApexDNS --> AmplifyEdge
    UserClients -->|"API Requests (api.xaiote.com)"| ApiDNS --> ALB
    WhatsAppWebhook -->|"POST Webhook"| ApiDNS --> ALB

    ALB -->|"Port 8000 (Round Robin)"| TG_Blue & TG_Green
    TG_Blue --> Task1
    TG_Green --> Task1

    SecretsMgr -.->|"Inject Secrets at Task Boot"| Task1
    Task1 -->|"Ship Redacted Logs"| CWLogs
    Task1 -->|"Transactional SQL (Port 5432)"| SupabaseDB
    Task1 -->|"Presigned PUT / GET"| ObjectStore
    Task1 -->|"REST Audio Stream"| SarvamCloud
    Task1 -->|"Structured Extraction"| OpenAICloud
```

---

## 2. Infrastructure Inventory & Provisioned Resources

| Component | AWS Resource Identifier / ARN | Specification / Capacity |
| :--- | :--- | :--- |
| **AWS Region** | `ap-south-1` | Asia Pacific (Mumbai) |
| **Frontend Host** | AWS Amplify Hosting (`amplify.yml`) | Next.js 15.2 App Router, Node.js 20 build pipeline |
| **Public API Host**| `api.xaiote.com` | Route 53 Alias to Application Load Balancer |
| **Load Balancer** | `arn:aws:elasticloadbalancing:ap-south-1:...` | Internet-facing Application Load Balancer (ALB) |
| **Target Groups** | `ecs-gateway-tg-49020a939b828ba4c`<br/>`ecs-gateway-tg-26e95a9adce6e9370` | HTTP on Port 8000; Health check path: `/health` |
| **ECS Cluster** | `arn:aws:ecs:ap-south-1:394920712303:cluster/default` | AWS ECS Fargate Serverless Cluster |
| **ECS Service** | `xaiote-backend` | Desired count: 1; Max: 200%; Min healthy: 100% |
| **Task Definition**| `family/default-xaiote-backend` | 0.5 vCPU (512), 1 GB RAM (1024 MB), `awsvpc` network |
| **ECR Registry** | `394920712303.dkr.ecr.ap-south-1.amazonaws.com/xaiote-backend` | Immutable Docker image repository |
| **IAM Task Role** | `arn:aws:iam::394920712303:role/xaiote-backend-task-role` | S3 read/write permissions for audio evidence |
| **Execution Role**| `arn:aws:iam::394920712303:role/service-role/ecsTaskExecutionRole` | Pull ECR images and fetch Secrets Manager secrets |
| **Secrets Manager**| `arn:aws:secretsmanager:ap-south-1:394920712303:secret:xaiote/production-aAx408` | Encrypted production keys and connection strings |
| **CloudWatch Logs**| `/ecs/xaiote-backend` | 30-day retention, encrypted log group |
| **Rollback Alarm**| `default/xaiote-backend/RollbackAlarm` | Triggers automated deployment rollback on 5xx spike |

---

## 3. ECS Deployment Configuration & Canary Rollout

The `xaiote-backend` ECS service implements an automated Canary release strategy with circuit-breaker protection:
- **Deployment Strategy:** `CANARY`
- **Canary Percentage:** `5.0%` of traffic routed to the newly deployed task revision.
- **Bake Time:** 3 minutes (`canaryBakeTimeInMinutes: 3`).
- **CloudWatch Rollback Alarm:** Monitored during bake time. If HTTP 5xx errors or container crash-loops occur during the 3-minute window, ECS terminates the canary task and rolls back to the prior stable task definition.
- **Circuit Breaker:** Enabled with automatic rollback (`rollback: true`) if task initialization fails healthy threshold checks.

---

## 4. Ingress Routing & Target Group Health Checks

The Application Load Balancer routes incoming traffic via listener rules:
1. **Rule 1 (`api.xaiote.com`):** Directs traffic to the active ECS target group.
2. **Health Check Probe:**
   - **Protocol:** HTTP
   - **Path:** `/health`
   - **Port:** 8000
   - **Interval:** 15 seconds
   - **Healthy Threshold:** 2 consecutive successes
   - **Unhealthy Threshold:** 3 consecutive failures
   - **Timeout:** 5 seconds
   - **Expected Status Code:** `200`

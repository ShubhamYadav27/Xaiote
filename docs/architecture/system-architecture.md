# System Architecture — Xaiote Manufacturing Intelligence

## 1. System Overview & Product Vision

Xaiote is an enterprise Manufacturing Intelligence platform designed to bridge the operational gap between factory-floor physical reality and enterprise resource systems. Modern discrete and batch manufacturing plants suffer from persistent information friction: machine breakdowns, process deviations, tool wear, and operational halts are communicated informally (via verbal exchanges, SMS, or WhatsApp channels) long before they are formally recorded in ERP (Enterprise Resource Planning) or CMMS (Computerized Maintenance Management System) databases.

This latency between floor reality and recorded data results in:
- Silent production schedule drift.
- Unanticipated work order delivery slippage.
- Downstream supply chain and customer penalty escalations.
- Inability to trace true root-cause provenance.

Xaiote captures informal manufacturing evidence directly from shop-floor personnel via multimodal channels (voice audio, text, telemetry), transforms noisy shop-floor vernacular into deterministic, canonical manufacturing events through an AI-assisted pipeline, correlates events into incidents, calculates blast-radius impacts on active work orders, and recommends mitigations under strict human-in-the-loop governance.

---

## 2. High-Level System Architecture

The following diagram illustrates the end-to-end component topology, data flows, and infrastructure boundaries across Xaiote's production environment.

```mermaid
flowchart TD
    subgraph ClientLayer ["Client & Ingestion Layer"]
        UserBrowser["Web Browser (Production Operator / Plant Lead)"]
        WhatsAppClient["Meta WhatsApp Business / Webhook Sender"]
    end

    subgraph EdgeLayer ["Edge & CDN Layer (AWS ap-south-1)"]
        AmplifyEdge["AWS Amplify Hosting (Next.js 15.2 App Router)"]
        ALB["AWS Application Load Balancer (api.xaiote.com)"]
    end

    subgraph ComputeLayer ["Compute Layer (AWS ECS Fargate)"]
        FastAPISvc["FastAPI Application (Python 3.12, Uvicorn)"]
        
        subgraph WorkerPool ["Asyncio In-Process Worker Pool (Lifespan Context)"]
            EvidenceWorker["Evidence Worker (Payload Ingestion)"]
            MediaWorker["Media Worker (Meta API & Storage)"]
            STTWorker["STT Worker (Mutagen & Sarvam/OpenAI)"]
            ExtractionWorker["Extraction Worker (LLM Parsing)"]
            ResolutionWorker["Entity Resolution Worker (DB Master Data)"]
            CanonicalizationWorker["Canonicalization Worker (Event & Impact Creation)"]
            AlertWorker["Alert Worker (Policy Evaluator)"]
        end
    end

    subgraph DataLayer ["Data & Storage Layer"]
        SupabasePG[("PostgreSQL 15 (Supabase Connection Pooler)")]
        ObjectStorage[("S3 / MinIO Object Storage (Bucket: xaiote-evidence)")]
    end

    subgraph ExternalServices ["External Intelligence & Communications APIs"]
        MetaGraph["Meta WhatsApp Cloud API (Graph v19.0)"]
        SarvamAPI["Sarvam AI REST API (Saaras:v4 STT)"]
        OpenAIAPI["OpenAI API (GPT-4o-mini & Whisper Fallback)"]
    end

    UserBrowser -->|"HTTPS (xaiote.com)"| AmplifyEdge
    UserBrowser -->|"REST API / Bearer Token"| ALB
    WhatsAppClient -->|"Webhook POST / HMAC-SHA256"| ALB

    ALB -->|"HTTP / Container Port 8000"| FastAPISvc
    FastAPISvc -->|"Async SQLAlchemy / asyncpg"| SupabasePG
    FastAPISvc -->|"Boto3 SDK"| ObjectStorage

    FastAPISvc --- WorkerPool
    WorkerPool -->|"SELECT ... FOR UPDATE SKIP LOCKED"| SupabasePG
    MediaWorker -->|"Download Media"| MetaGraph
    MediaWorker -->|"Stream Media"| ObjectStorage
    STTWorker -->|"Audio Buffer Stream"| SarvamAPI
    STTWorker -.->|"Fallback"| OpenAIAPI
    ExtractionWorker -->|"Structured Event Extraction"| OpenAIAPI
    WorkerPool -->|"Fetch Master Data & Correlate"| SupabasePG
```

---

## 3. Core Subsystems & Responsibilities

| Subsystem | Implemented Technology | Primary Responsibility | Status |
| :--- | :--- | :--- | :--- |
| **Frontend Web Console** | Next.js 15.2, React 19.2, TypeScript 5, Tailwind CSS v4, Lucide Icons | Multi-tenant plant dashboard, incident monitoring, event triage, approval workflows, and master data management. | `IMPLEMENTED` |
| **API Gateway / Ingress** | AWS Application Load Balancer (ALB), AWS Amplify | Path-based and host-header routing, SSL termination, and rate bounding. | `IMPLEMENTED` |
| **Backend API Service** | Python 3.12, FastAPI 0.111, Uvicorn 0.30 | REST endpoints for authentication, master entities, webhooks, query filtering, and role enforcement. | `IMPLEMENTED` |
| **Database & Queue Core** | PostgreSQL 15 (Supabase Pooler), SQLAlchemy 2.0 Async, `asyncpg` | Relational source of truth, transactional row locks (`FOR UPDATE SKIP LOCKED`) serving as durable queues. | `IMPLEMENTED` |
| **Evidence & Media Storage** | MinIO (local dev), AWS S3 (production) | Durable, immutable object storage for raw voice audio (.ogg, .mp4, .wav) and uploaded master spreadsheets. | `IMPLEMENTED` |
| **Speech-to-Text (STT) Engine** | Sarvam AI SDK (`saaras:v4`), OpenAI Whisper-1 fallback, Mutagen | Audio duration validation (<=30s REST, >30s review gating), language detection, and transcription. | `IMPLEMENTED` |
| **Extraction Engine** | OpenAI API (`gpt-4o-mini`), JSON Schema validation | Extraction of domain entities (machine, symptom, downtime, severity) with explicit provenance tracking. | `IMPLEMENTED` |
| **Entity Resolution Engine** | SQL Trigram matching (`pg_trgm`), Levenshtein similarity | Fuzzy matching shop-floor machine aliases to canonical plant master records. | `IMPLEMENTED` |
| **Canonicalization Engine** | Python state machine, SQLAlchemy transactions | Gating of unverified models, human-in-the-loop confirmations, and immutable event lineage. | `IMPLEMENTED` |
| **Risk & Impact Engine** | Graph-style relation evaluation, backward scheduling | Evaluating blast radius on work orders, customer deliveries, and machine capacity. | `IMPLEMENTED` |
| **Execution Gateway** | REST Webhooks, CMMS Adapter | Dispatching approved remediation actions to external maintenance management systems. | `PARTIALLY IMPLEMENTED` |

---

## 4. Frontend-to-Backend Request Lifecycle

Every user-driven transaction originates from the Next.js client component architecture:

```mermaid
sequenceDiagram
    autonumber
    actor Operator as Plant Operator
    participant UI as Next.js 15 Client (Browser)
    participant ALB as AWS Application Load Balancer
    participant API as FastAPI Backend (ECS Fargate)
    participant Auth as Auth Dependency (PyJWT)
    participant DB as PostgreSQL (Supabase)

    Operator->>UI: Interacts with Incident / Risk Table
    UI->>UI: Check localStorage for access_token
    alt Token expired / missing
        UI->>UI: Call POST /api/auth/refresh with refresh_token
        alt Refresh invalid
            UI->>Operator: Redirect to /login
        end
    end
    UI->>ALB: GET https://api.xaiote.com/api/v1/incidents?limit=50<br/>Header: Authorization: Bearer <JWT>
    ALB->>API: Route to ECS Task on port 8000
    API->>Auth: Validate JWT signature (HS256) & expiry
    Auth->>Auth: Extract sub (user_id) and company_id
    Auth->>DB: Query User record & active Company status
    DB-->>Auth: User & Company models returned
    API->>API: Execute get_incidents(db, company_id=company.id, ...)
    API->>DB: SELECT * FROM incidents WHERE company_id = :cid ORDER BY created_at DESC LIMIT 50
    DB-->>API: Result rows
    API-->>ALB: HTTP 200 OK + PaginatedIncidentResponse JSON
    ALB-->>UI: Forward response body
    UI->>Operator: Render incident items without page refresh
```

---

## 5. Architectural Invariants & Tenets

1. **Zero Raw Audio Deletion:** Voice evidence captured from the shop floor is considered legal and audit evidence. Raw audio stored in Object Storage is immutable and retained indefinitely.
2. **Strict Multi-Tenant Isolation:** `company_id` is derived strictly from the cryptographically validated JWT server-side. No API route allows tenant impersonation via query params or request payload.
3. **No External Message Broker Dependency:** Background task reliability is guaranteed through ACID transactions in PostgreSQL using `FOR UPDATE SKIP LOCKED`. Worker state survives container restarts and scale-in events.
4. **Uncertainty Transparency:** The platform explicitly separates model-derived inferences (`MODEL_DERIVED`) from explicit human ground truth (`EXPLICIT`). Low confidence or ambiguous signals fail closed into `NEEDS_REVIEW` queues.
5. **Fail-Closed Plant Authorization:** Multi-plant enterprises isolate operator permissions to designated facilities unless explicitly provisioned with `OWNER` or `ADMIN` enterprise credentials.

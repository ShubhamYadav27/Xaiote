# Local Development & Environment Setup Guide

## 1. Prerequisites & Tooling

Before configuring Xaiote on a local workstation, ensure the following runtimes and utilities are installed:

| Tool | Recommended Version | Minimum Version | Verification Command |
| :--- | :--- | :--- | :--- |
| **Operating System** | Windows 11 / Ubuntu 22.04 / macOS 14 | Any 64-bit OS | `[System.Environment]::OSVersion` / `uname -a` |
| **Python** | `3.12.x` | `3.12.0` | `python --version` |
| **Node.js** | `20.x LTS` | `20.10.0` | `node --version` |
| **npm** | `10.x` | `10.2.0` | `npm --version` |
| **Docker Desktop** | `26.x+` (with Compose v2) | `24.0.0` | `docker --version` |
| **Git** | `2.40+` | `2.30.0` | `git --version` |

---

## 2. Repository Architecture Overview

```
c:\Xaiote\
├── docker-compose.yml     # Local orchestration (PostgreSQL, MinIO, Backend, Frontend)
├── backend/               # FastAPI asynchronous API service & background workers
│   ├── .env.example       # Template for backend environment variables
│   └── requirements.txt   # Pinned Python dependencies
└── frontend/              # Next.js 15 App Router web console
    └── .env.local.example # Template for frontend client variables
```

---

## 3. Quick Start via Docker Compose (Recommended)

Docker Compose provides a complete, self-contained development environment including PostgreSQL 15, MinIO (S3-compatible storage), FastAPI backend, and Next.js frontend.

### Step 1: Start Container Stack
Open Windows PowerShell in the repository root:
```powershell
docker compose up -d
```

### Step 2: Verify Running Containers
```powershell
docker compose ps
```
Expected output:
```
NAME                COMMAND                  SERVICE    STATUS                 PORTS
xaiote-backend-1    "uvicorn app.main:ap…"   backend    Up (healthy)           0.0.0.0:8000->8000/tcp
xaiote-db-1         "docker-entrypoint.s…"   db         Up (healthy)           0.0.0.0:5433->5432/tcp
xaiote-frontend-1   "docker-entrypoint.s…"   frontend   Up                     0.0.0.0:3000->3000/tcp
xaiote-storage-1    "/usr/bin/docker-ent…"   storage    Up (healthy)           0.0.0.0:9000-9001->9000-9001/tcp
```

### Step 3: Local Port Mappings & Service Endpoints
- **Frontend Console:** [http://localhost:3000](http://localhost:3000)
- **Backend API Docs (Swagger):** [http://localhost:8000/docs](http://localhost:8000/docs)
- **API Health Check:** [http://localhost:8000/health](http://localhost:8000/health)
- **MinIO Storage Console:** [http://localhost:9001](http://localhost:9001) (User: `minioadmin`, Pass: `minioadmin`)

---

## 4. Native Local Setup (Hybrid / Development Mode)

For active backend or frontend development with local debuggers and fast hot-reloading:

### 1. Database & Storage Infrastructure
Run only PostgreSQL and MinIO in Docker:
```powershell
docker compose up -d db storage
```

### 2. Backend Service Setup (Python 3.12)
Navigate to the `backend` directory:
```powershell
cd c:\Xaiote\backend

# Create virtual environment
python -m venv .venv

# Activate virtual environment (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Upgrade pip and install pinned dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt
```

#### Backend Environment Configuration
Copy `.env.example` to `.env`:
```powershell
Copy-Item .env.example .env
```
Populate `.env` with local development credentials:
```ini
# Local PostgreSQL (Port 5433 mapped by docker-compose)
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5433/xaiote

# Security Keys (Generate high-entropy strings for local testing)
JWT_SECRET=local-jwt-secret-for-development-must-be-32-chars-long
JWT_REFRESH_SECRET=local-jwt-refresh-secret-for-development
SECRET_ENCRYPTION_KEY=AQIDBAUGBwgJCgsMDQ4PEBESExQVFhcYGRobHB0eHyA=

# Local MinIO Storage
MINIO_ENDPOINT=http://localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=xaiote-evidence

# STT Configuration (Sarvam AI with Saaras:v4 or OpenAI Whisper fallback)
STT_PROVIDER=sarvam
STT_MODEL=saaras:v4
SARVAM_API_KEY=your-sarvam-api-key-here

# WhatsApp Webhook Verification
WHATSAPP_VERIFY_TOKEN=local-dev-verify-token
```

#### Run Database Migrations
Apply all schema migrations to update the local database to `HEAD`:
```powershell
alembic upgrade head
```

#### Start FastAPI Development Server
```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

### 3. Frontend Setup (Next.js 15)
In a separate terminal, navigate to the `frontend` directory:
```powershell
cd c:\Xaiote\frontend

# Install dependencies cleanly
npm ci
```

#### Frontend Environment Configuration
Copy `.env.local.example` to `.env.local`:
```powershell
Copy-Item .env.local.example .env.local
```
Ensure `NEXT_PUBLIC_API_URL` points to your local FastAPI backend:
```ini
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

#### Start Next.js Development Server
```powershell
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 5. Verification & Health Probes

Verify the entire environment is operating correctly:

### 1. Backend Probe
```powershell
curl http://localhost:8000/health
```
Expected response:
```json
{"status":"ok"}
```

### 2. Database Connection Test
From the backend directory:
```powershell
python -c "import asyncio, asyncpg; asyncio.run(asyncpg.connect('postgresql://user:password@localhost:5433/xaiote'))"
```
If no output or errors are returned, the database connection succeeded.

### 3. MinIO Bucket Initialization
MinIO automatically creates buckets on demand when `S3Storage.upload` is first invoked. To verify MinIO connectivity:
```powershell
curl http://localhost:9000/minio/health/live
```
Expected status: HTTP `200 OK`.

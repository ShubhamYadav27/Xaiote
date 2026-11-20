# Xaiote — Backend Engine & Processing Core

The Xaiote backend is an asynchronous, high-throughput manufacturing intelligence engine built on Python 3.12, FastAPI, and SQLAlchemy 2.0 Async (`asyncpg`). It runs in AWS ECS Fargate (`ap-south-1`) behind an Application Load Balancer (`https://api.xaiote.com`).

---

## 1. Core Architectural Capabilities

- **Webhook Ingress (`app/api/routes/webhooks.py`):** Ingests Meta WhatsApp Cloud API payloads with HMAC-SHA256 constant-time verification.
- **Transactional Async Workers (`app/workers/`):** PostgreSQL `SELECT ... FOR UPDATE SKIP LOCKED` state-machine workers running as background `asyncio` tasks in the FastAPI lifespan context.
- **Multimodal STT (`app/infrastructure/stt/`):** Sarvam AI REST STT (`saaras:v4`) for Hindi/Hinglish/English manufacturing speech transcription with OpenAI Whisper-1 fallback. Enforces a strict <=30s duration ceiling; >30s gates to `NEEDS_REVIEW`.
- **Entity Resolution (`app/services/resolution_engine.py`):** Resolves noisy vernacular shop-floor aliases to master database entities using PostgreSQL trigram similarity (`pg_trgm`).
- **Blast-Radius & Risk Engine (`app/services/risk_service.py`):** Correlates failure events to active incidents and calculates backward-scheduled delays on active production work orders.
- **Data Redaction (`app/core/logging_scrubber.py`):** Automatically redacts Bearer tokens, secrets, API keys, and passwords from all log handlers.

---

## 2. Directory Structure

```
backend/
├── app/
│   ├── main.py                  # FastAPI app, CORS, lifespan, router registry
│   ├── api/
│   │   ├── dependencies/        # get_current_user, get_current_company, plant auth
│   │   └── routes/              # REST controllers (/api/auth, /api/v1/...)
│   ├── core/                    # config.py, security.py, logging_scrubber.py, prompts.py
│   ├── infrastructure/          # Database session, S3/MinIO, STT providers, LLM clients
│   ├── models/                  # Declarative SQLAlchemy models
│   ├── schemas/                 # Pydantic v2 schemas
│   ├── services/                # Business logic, incident correlation, risk evaluator
│   └── workers/                 # Durable asyncio background polling workers
├── alembic/                     # Database migrations (cacd70128399 -> f33a7c860f9c)
├── tests/                       # Pytest unit, worker, eval, and integration tests
├── Dockerfile                   # Python 3.12-slim production container definition
├── requirements.txt             # Pinned production dependencies
├── pytest.ini                  # Pytest async configuration
└── .env.example                 # Environment template
```

---

## 3. Local Development Quick Start

### 1. Prerequisites
- Python 3.12+
- Docker (for PostgreSQL & MinIO)

### 2. Setup Virtual Environment
```powershell
cd c:\Xaiote\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 3. Environment Configuration
```powershell
Copy-Item .env.example .env
```
Ensure `.env` contains:
```ini
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5433/xaiote
JWT_SECRET=local-jwt-secret-for-development-must-be-32-chars-long
JWT_REFRESH_SECRET=local-jwt-refresh-secret-for-development
SECRET_ENCRYPTION_KEY=AQIDBAUGBwgJCgsMDQ4PEBESExQVFhcYGRobHB0eHyA=
MINIO_ENDPOINT=http://localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=xaiote-evidence
STT_PROVIDER=sarvam
STT_MODEL=saaras:v4
SARVAM_API_KEY=your-api-key-here
WHATSAPP_VERIFY_TOKEN=local-dev-verify-token
```

### 4. Run Migrations & Start Server
```powershell
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)  
Health Check: [http://localhost:8000/health](http://localhost:8000/health)

---

## 4. Running Tests

```powershell
# Run full backend test suite
pytest

# Run STT provider & duration gating tests
pytest tests/test_stt_providers.py tests/test_stt_worker2.py

# Run live real-speech Sarvam integration test
$env:SARVAM_API_KEY="your-active-key"
pytest tests/integration/test_sarvam_real_speech.py -v -s
```

For complete technical documentation, refer to the root [README.md](../README.md) and [docs/](../docs/).

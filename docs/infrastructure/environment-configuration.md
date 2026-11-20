# Environment Configuration Reference

## 1. Configuration Principles

Xaiote follows the **Twelve-Factor App** configuration methodology. Configuration is decoupled from source code and strictly injected via runtime environment variables.

- **Development:** Loaded locally from `.env` (backend) and `.env.local` (frontend).
- **Production (Backend):** Injected directly into the AWS ECS Fargate container task via **AWS Secrets Manager** (`arn:aws:secretsmanager:ap-south-1:394920712303:secret:xaiote/production-aAx408`).
- **Production (Frontend):** Injected at build time in AWS Amplify Hosting via `NEXT_PUBLIC_API_URL`.

---

## 2. Backend Environment Variables (`backend/app/core/config.py`)

| Variable Name | Type | Required | Default Value | Description |
| :--- | :--- | :--- | :--- | :--- |
| **`PROJECT_NAME`** | `string` | No | `"Xaiote Manufacturing Intelligence"` | Title displayed in OpenAPI docs and server logs |
| **`DATABASE_URL`** | `string` | **Yes** | — | PostgreSQL connection URI. Must use `postgresql+asyncpg://` protocol |
| **`JWT_SECRET`** | `string` | **Yes** | — | High-entropy secret key for HMAC-SHA256 JWT access token signing |
| **`JWT_REFRESH_SECRET`** | `string` | **Yes** | — | Cryptographic secret for hashing refresh tokens |
| **`JWT_ACCESS_EXPIRE_MINUTES`** | `integer` | No | `30` | Access token lifespan in minutes before requiring refresh |
| **`JWT_REFRESH_EXPIRE_DAYS`** | `integer` | No | `7` | Refresh token duration in days before requiring re-login |
| **`MINIO_ENDPOINT`** | `string` | **Yes** | — | URL endpoint for S3/MinIO storage (`http://storage:9000` or AWS S3 URI) |
| **`MINIO_ACCESS_KEY`** | `string` | No | `"minioadmin"` | S3 API access key ID |
| **`MINIO_SECRET_KEY`** | `string` | No | `"minioadmin"` | S3 API secret access key |
| **`MINIO_BUCKET`** | `string` | No | `"xaiote-evidence"` | Target bucket for voice audio attachments and uploaded spreadsheets |
| **`SECRET_ENCRYPTION_KEY`** | `string` | **Yes** | — | 32-byte URL-safe base64 Fernet key used to encrypt tenant secrets at rest |
| **`STT_PROVIDER`** | `string` | No | `"sarvam"` | Active speech-to-text provider (`sarvam` or `openai`) |
| **`STT_MODEL`** | `string` | No | `"saaras:v4"` | Target model identifier (`saaras:v4` for Sarvam, `whisper-1` for OpenAI) |
| **`SARVAM_API_KEY`** | `string` | **Yes*** | — | Official subscription key for Sarvam AI REST API (*when STT_PROVIDER=sarvam) |
| **`STT_API_KEY`** | `string` | No | — | OpenAI API key (*when STT_PROVIDER=openai) |
| **`WHATSAPP_VERIFY_TOKEN`** | `string` | **Yes** | — | Verification token matching Meta WhatsApp Cloud API webhook configuration |
| **`TESTING`** | `string` | No | `"false"` | When set to `"true"`, disables background worker loops during test collection |

---

## 3. Frontend Environment Variables (`frontend/src/lib/api.ts`)

| Variable Name | Required | Default (Development) | Production Value | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **`NEXT_PUBLIC_API_URL`** | **Yes** | `http://localhost:8000/api/v1` | `https://api.xaiote.com/api/v1` | Base URL prefix for all client-side API requests |

### Production Configuration Safety Assertion
In `frontend/src/lib/api.ts`, the frontend enforces a compile/runtime assertion:
```typescript
if (process.env.NODE_ENV === 'production') {
  if (configuredUrl && configuredUrl.includes('localhost')) {
    throw new Error("PRODUCTION CONFIGURATION ERROR: NEXT_PUBLIC_API_URL cannot point to localhost in production.");
  }
}
```
This protects production static bundles from accidentally shipping with `localhost` endpoints.

---

## 4. Production Secret Injection (AWS Secrets Manager)

In AWS ECS Fargate, secrets are fetched dynamically during container task initialization. The ECS execution role retrieves values from `xaiote/production-aAx408` and injects them as environment variables into the container runtime.

### Task Definition Secret Mapping (`td.json`):
```json
{
  "name": "Main",
  "secrets": [
    {
      "name": "DATABASE_URL",
      "valueFrom": "arn:aws:secretsmanager:ap-south-1:394920712303:secret:xaiote/production-aAx408:DATABASE_URL::"
    },
    {
      "name": "JWT_SECRET",
      "valueFrom": "arn:aws:secretsmanager:ap-south-1:394920712303:secret:xaiote/production-aAx408:JWT_SECRET::"
    },
    {
      "name": "JWT_REFRESH_SECRET",
      "valueFrom": "arn:aws:secretsmanager:ap-south-1:394920712303:secret:xaiote/production-aAx408:JWT_REFRESH_SECRET::"
    },
    {
      "name": "SECRET_ENCRYPTION_KEY",
      "valueFrom": "arn:aws:secretsmanager:ap-south-1:394920712303:secret:xaiote/production-aAx408:SECRET_ENCRYPTION_KEY::"
    },
    {
      "name": "MINIO_ENDPOINT",
      "valueFrom": "arn:aws:secretsmanager:ap-south-1:394920712303:secret:xaiote/production-aAx408:MINIO_ENDPOINT::"
    },
    {
      "name": "MINIO_ACCESS_KEY",
      "valueFrom": "arn:aws:secretsmanager:ap-south-1:394920712303:secret:xaiote/production-aAx408:MINIO_ACCESS_KEY::"
    },
    {
      "name": "MINIO_SECRET_KEY",
      "valueFrom": "arn:aws:secretsmanager:ap-south-1:394920712303:secret:xaiote/production-aAx408:MINIO_SECRET_KEY::"
    },
    {
      "name": "MINIO_BUCKET",
      "valueFrom": "arn:aws:secretsmanager:ap-south-1:394920712303:secret:xaiote/production-aAx408:MINIO_BUCKET::"
    }
  ]
}
```
*At no point are secret values written to disk, included in Git commits, or embedded in Docker container layers.*

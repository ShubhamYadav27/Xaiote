# Security Architecture & Risk Posture

## 1. Security Philosophy

Xaiote processes sensitive operational data: factory production volumes, machine run-rates, customer work orders, and floor-level voice recordings. A breach could expose proprietary manufacturing parameters or allow malicious disruption of plant operations.

The security architecture operates on the principle of **Defense-in-Depth**:
- Zero trust between client and API: all identity claims must be cryptographically proven.
- Multi-tenant isolation enforced at the database query level.
- Multi-tier secret redaction preventing accidental data exfiltration into logs or client bundles.
- Cryptographic verification of all external webhooks.

---

## 2. Threat Vector Analysis & Implemented Countermeasures

| Threat Vector | Risk Description | Implemented Countermeasure | Code Reference |
| :--- | :--- | :--- | :--- |
| **Cross-Tenant Data Leakage** | Tenant A queries or mutates Work Orders/Incidents belonging to Tenant B. | Mandatory `company_id` filter derived from verified JWT `sub`/`company_id` claims on every SQL statement. | `app/api/dependencies/auth.py` |
| **Credential & Key Exposure in Logs** | API keys (Sarvam/OpenAI), JWTs, or passwords dumped into CloudWatch. | Global `SensitiveDataFilter` regex log scrubber redacts Bearer tokens, passwords, and API keys. | `app/core/logging_scrubber.py` |
| **Webhook Spoofing** | Adversary sends fake WhatsApp audio/text to create false plant disruptions. | HMAC-SHA256 signature verification on raw request bytes using tenant's decrypted app secret. | `app/api/routes/webhooks.py` |
| **Timing Attacks on Webhooks** | Attacker uses response latency deltas to deduce valid HMAC signatures. | Constant-time string comparison using `hmac.compare_digest`. | `app/api/routes/webhooks.py` |
| **Password Database Compromise** | Database dump exposes user passwords to offline cracking. | Argon2id memory-hard password hashing via `passlib.context.CryptContext`. | `app/core/security.py` |
| **Stolen Refresh Token Reuse** | Refresh token intercepted from client localStorage or wire. | Single-use rotation; database stores only SHA-256 hash (`hash_token`); token revoked upon refresh. | `app/api/routes/auth.py` |
| **Integration Secret Compromise** | Database dump exposes WhatsApp App Secrets or CMMS API keys. | AES-128-CBC encryption at rest using Fernet with `SECRET_ENCRYPTION_KEY`. | `app/core/security.py` |
| **Audio File Bomb / Denial of Service** | Malicious actor posts 10 GB file to overwhelm storage or STT workers. | Bounded 50 MB file size limit and 15-minute ceiling; headers verified via `mutagen` before processing. | `app/workers/stt_worker.py` |
| **Cross-Origin API Abuse** | Malicious third-party website makes authenticated browser API calls. | CORS restricted to `localhost:3000`, `localhost:3001`, `xaiote.com`, `www.xaiote.com`. | `app/main.py` |

---

## 3. Cryptographic Implementation Details

### 1. Secret Scrubber (`app/core/logging_scrubber.py`)
Active across all logging facilities (Uvicorn, FastAPI, SQLAlchemy, Application loggers):
```python
class SensitiveDataFilter(logging.Filter):
    def __init__(self):
        super().__init__()
        self.patterns = [
            (re.compile(r"(?i)(bearer\s+)[A-Za-z0-9\-\._~\+\/]+=*"), r"\1[REDACTED]"),
            (re.compile(r"(?i)(api[_-]?key['\"]?\s*[:=]\s*['\"]?)[A-Za-z0-9\-]+"), r"\1[REDACTED]"),
            (re.compile(r"(?i)(secret['\"]?\s*[:=]\s*['\"]?)[A-Za-z0-9\-]+"), r"\1[REDACTED]"),
            (re.compile(r"(?i)(password['\"]?\s*[:=]\s*['\"]?)[^&'\" ]+"), r"\1[REDACTED]")
        ]
```

### 2. Encryption at Rest (`app/core/security.py`)
Integration credentials (such as WhatsApp App Secrets) are stored encrypted:
```python
fernet = Fernet(settings.SECRET_ENCRYPTION_KEY.encode())

def encrypt_secret(secret: str) -> str:
    return fernet.encrypt(secret.encode()).decode()

def decrypt_secret(encrypted_secret: str) -> str:
    return fernet.decrypt(encrypted_secret.encode()).decode()
```

---

## 4. Known Security Limitations & Pending Work

While the core platform implements robust foundational security, the following improvements are recorded for production hardening:

| Security Domain | Current Implementation | Planned Hardening / Target State | Priority |
| :--- | :--- | :--- | :--- |
| **Rate Limiting** | Handled at ALB layer | Application-level rate limiting (`slowapi` or Redis token bucket) on `/api/auth/login` and `/api/auth/register` to prevent credential stuffing. | `HIGH` |
| **Token Storage** | Client `localStorage` with `xaiote_auth` cookie signal | Migrate access and refresh tokens to secure `HttpOnly`, `SameSite=Strict`, `Secure` cookies to eliminate XSS token theft vectors. | `MEDIUM` |
| **Key Rotation** | Static `SECRET_ENCRYPTION_KEY` in AWS Secrets Manager | AWS KMS integration with automated envelope encryption and annual key rotation. | `MEDIUM` |
| **Dependency Audits** | Manual pip and npm checks | Automated Dependabot and Snyk scanning in CI/CD pipeline. | `MEDIUM` |
| **WAF Rules** | Standard AWS ALB | AWS WAF integration with rate bounding, SQL injection, and XSS managed rule sets. | `HIGH` |

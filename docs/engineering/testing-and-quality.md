# Testing & Quality Engineering Architecture

## 1. Testing Philosophy & Test Pyramid

Xaiote's testing strategy is built around manufacturing data reliability:
1. **Zero External Credit Burn in CI/CD:** Unit and worker test suites mock external neural APIs (Sarvam AI, OpenAI Whisper, OpenAI GPT-4o-mini). Unit tests must execute rapidly without network dependencies or billing impact.
2. **Deterministic Data Lineage:** Tests verify that raw evidence records are never mutated, that entity resolution states transition monotonically, and that models cannot silently bypass human confirmation.
3. **Tenant Boundary Assertion:** Negative tests explicitly attempt cross-tenant resource reads and modifications, ensuring 100% fail-closed authorization.
4. **Isolated Integration Gates:** Dedicated live verification test scripts exist separately to validate live credentials without affecting automated regression passes.

---

## 2. Test Suite Architecture

```
backend/tests/
├── pytest.ini                            # Pytest configuration (asyncio_mode = auto)
├── conftest.py                           # Fixtures: async engine, test DB session, auth tokens
├── eval/                                 # Accuracy & extraction evaluation harnesses
│   ├── test_llm_extraction.py            # Prompt accuracy on manufacturing terminology
│   └── test_stt_evaluation.py           # Audio WER / CER evaluation
├── integration/                          # Live service integration tests
│   ├── test_concurrency.py               # Concurrent SKIP LOCKED worker contention
│   ├── test_sarvam_integration.py       # Live Sarvam REST STT verification (skipped if no key)
│   └── test_sarvam_real_speech.py        # Real Hinglish manufacturing speech transcription
├── test_auth.py                          # Password hashing, JWT creation, token refresh
├── test_masters.py                       # Plant, Machine, Customer, Vendor CRUD
├── test_work_orders.py                   # Work order scheduling and status changes
├── test_imports.py                       # Bulk CSV/Excel staging, parsing, and audits
├── test_communication.py                 # Webhook receipts, payload validation, HMAC
├── test_evidence_pipeline.py             # Evidence worker payload extraction
├── test_stt_providers.py                 # Unit tests for Sarvam and OpenAI STT classes (Mocked)
├── test_stt_worker.py / test_stt_worker2.py # STT worker leasing, duration gating, state flow
├── test_extraction_worker.py             # LLM worker leasing, JSON schema validation
├── test_resolution_worker.py             # Trigram matching, alias resolution, ambiguous states
├── test_canonicalization_worker.py      # Plant conflict detection, matrix checks, event creation
├── test_manufacturing_events.py          # Lineage inspection, revision logging
├── test_phase_4a_impact.py               # Work order delay estimation, backward scheduling
├── test_phase_4b_risk.py / test_phase_4b_api.py # Risk transitions and dashboard aggregates
├── test_phase_4c_incidents.py            # Event correlation, linking/unlinking, resolution
├── test_phase_4d_analysis.py             # Root cause intelligence, assessments
├── test_phase_4e_*.py                    # Alert policies, evaluation jobs, retry semantics
└── test_phase_5*.py                      # Remediation actions, approvals, CMMS execution
```

---

## 3. Test Execution Runbook

### 1. Running Backend Unit & Worker Tests
From the `backend` directory:

```powershell
cd c:\Xaiote\backend

# Run complete core test suite
pytest

# Run tests with verbose output and duration profiling
pytest -v --durations=10

# Run specific domain test suites
pytest tests/test_stt_providers.py tests/test_stt_worker2.py
pytest tests/test_phase_4a_impact.py tests/test_phase_4c_incidents.py
pytest tests/test_phase_4b_risk.py tests/test_phase_4b_api.py
```

### 2. Running Live Sarvam STT Verification
Live integration tests verify real API credentials against Sarvam's production endpoints. These tests require a valid `SARVAM_API_KEY` in the environment:

```powershell
# Set key for the active session (never commit keys to source code)
$env:SARVAM_API_KEY="your-active-api-key"

# Execute real-speech Hinglish integration test
pytest tests/integration/test_sarvam_real_speech.py -v -s
```
Expected output:
```
Audio duration: 7.24s
Provider: Sarvam AI (saaras:v4)
Language detected: hi-IN
Transcript: "सीएनसी टू बैंड हो गई है, स्पिंडल फेलियर है और मेंटेनेंस वाले बोल रहे हैं आठ घंटे लगेंगे।"
Result: PASS (Manufacturing terminology CNC, spindle, maintenance accurately transcribed)
```

### 3. Frontend Quality & Type Checks
From the `frontend` directory:

```powershell
cd c:\Xaiote\frontend

# Run ESLint validation
npm run lint

# Run Next.js production type-checking and build
npm run build
```

### 4. Python Static Analysis & Formatting
The codebase enforces strict Ruff, Black, and Mypy standards:

```powershell
cd c:\Xaiote\backend

# Ruff linting
ruff check app/

# Black code format verification
black --check app/

# Mypy static type checking
mypy app/
```

---

## 4. Test Baseline & Verified Metrics

| Test Suite | Total Items | Passed | Skipped | Status | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **STT Provider & Worker Suite** | 20 | 20 | 0 | `100% PASS` | Sarvam REST STT, duration gating (>30s), OpenAI fallback |
| **Core Regression Suite (Phase 3F-5)**| 126 | 126 | 0 | `100% PASS` | Revisions, impacts, risk evaluation, incidents, alerts |
| **Full Repository Test Session** | 401 | 379 | 7 | `BASELINE` | 379 passed, 7 skipped, 1 failed (media webhook), 14 errors (legacy fixture dependency in older phase 5a/5b tests) |
| **Production API Integration Suite** | 10 | 10 | 0 | `100% PASS` | Authenticated smoke test across all production `/api/v1` routes |

---

## 5. Mocking Strategy & Fixtures

### 1. Mocking External Neural Providers
In unit tests, `sarvamai` and `openai` network clients are intercepted using `unittest.mock.patch` or `pytest-mock`:
```python
@pytest.fixture
def mock_sarvam_client(monkeypatch):
    class MockSarvamResponse:
        transcript = "CNC 2 breakdown, 8 hours downtime"
        language_code = "hi-IN"
        
    def mock_post(*args, **kwargs):
        return MockSarvamResponse()
        
    monkeypatch.setattr("sarvamai.SarvamAI.speech_to_text", mock_post)
```

### 2. Fast Async Test DB Engine (`NullPool`)
In `app/infrastructure/database/session.py`, tests run with `TESTING=true`:
```python
if is_testing:
    engine = create_async_engine(db_url, echo=False, poolclass=NullPool)
```
Using `NullPool` prevents connection pooling leaks and race conditions between concurrent asynchronous test functions.

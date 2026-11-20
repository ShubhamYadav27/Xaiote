# Xaiote REST API Reference

## 1. API Architecture Overview

The Xaiote backend exposes an asynchronous RESTful API partitioned into two top-level route namespaces:
- **Authentication Routes (`/api/auth/*`):** Public and token-refresh endpoints governing tenant onboarding, user login, token refresh, and identity introspection.
- **Application Routes (`/api/v1/*`):** Authenticated, tenant-scoped operational endpoints for manufacturing intelligence, plant master data, and event pipelines.

### Standard Request Headers
```http
Authorization: Bearer <ACCESS_TOKEN>
Content-Type: application/json
```

### Standard Response Envelopes
1. **Object Envelope:**
   ```json
   {
     "data": { ... }
   }
   ```
2. **Paginated List Envelope:**
   ```json
   {
     "items": [ ... ],
     "total": 42
   }
   ```
3. **Error Envelope:**
   ```json
   {
     "error": {
       "code": "INTERNAL_SERVER_ERROR",
       "message": "Human-readable error description"
     }
   }
   ```

---

## 2. Authentication API (`/api/auth`)

### 1. Register User & Company
- **HTTP Method:** `POST`
- **Route:** `/api/auth/register`
- **Auth:** Public
- **Request Body:**
  ```json
  {
    "email": "lead@factory.com",
    "password": "SecurePassword123!",
    "full_name": "Suresh Sharma",
    "company_name": "Precision Auto Components Ltd",
    "industry": "Automotive Tier 1",
    "revenue_range": "50Cr - 100Cr"
  }
  ```
- **Response Status:** `200 OK`
- **Response Body:**
  ```json
  {
    "data": {
      "message": "User and company created successfully"
    }
  }
  ```

### 2. User Login
- **HTTP Method:** `POST`
- **Route:** `/api/auth/login`
- **Auth:** Public
- **Request Body:**
  ```json
  {
    "email": "lead@factory.com",
    "password": "SecurePassword123!"
  }
  ```
- **Response Status:** `200 OK` (or `401 Unauthorized` on mismatch)
- **Response Body:**
  ```json
  {
    "data": {
      "access_token": "eyJhbGciOi...",
      "refresh_token": "550e8400-e29b-41d4-a716-446655440000"
    }
  }
  ```

### 3. Refresh Access Token
- **HTTP Method:** `POST`
- **Route:** `/api/auth/refresh`
- **Auth:** Public
- **Request Body:**
  ```json
  {
    "refresh_token": "550e8400-e29b-41d4-a716-446655440000"
  }
  ```
- **Response Status:** `200 OK` (or `401 Unauthorized` if expired/revoked)
- **Response Body:**
  ```json
  {
    "data": {
      "access_token": "eyJhbGciOi...",
      "refresh_token": "e6ba4a5a-..."
    }
  }
  ```

### 4. User Logout
- **HTTP Method:** `POST`
- **Route:** `/api/auth/logout`
- **Auth:** Public
- **Request Body:** `{"refresh_token": "..."}`
- **Response Status:** `200 OK`

### 5. Identity Introspection
- **HTTP Method:** `GET`
- **Route:** `/api/auth/me`
- **Auth:** `Bearer <TOKEN>`
- **Response Status:** `200 OK`
- **Response Body:**
  ```json
  {
    "data": {
      "id": "usr-uuid",
      "email": "lead@factory.com",
      "full_name": "Suresh Sharma",
      "company_id": "comp-uuid",
      "role": "OWNER"
    }
  }
  ```

---

## 3. Master Data APIs (`/api/v1/...`)

### Plants (`/api/v1/plants`)
- `POST /api/v1/plants`: Create a manufacturing plant. Body: `{"name": "Pune Plant 1", "code": "PUN-01", "location": "Chakan MIDC"}`.
- `GET /api/v1/plants`: List tenant plants. Returns: `[{"id": "...", "name": "...", "code": "..."}]`.
- `GET /api/v1/plants/{plant_id}`: Retrieve detailed facility record.

### Machines (`/api/v1/machines`)
- `POST /api/v1/machines`: Create a machine asset. Body: `{"plant_id": "...", "code": "CNC-02", "name": "5-Axis VMC", "model": "Haas VF-2"}`.
- `GET /api/v1/machines`: List company machines with optional filter `?plant_id=...`.

### Work Orders (`/api/v1/work-orders`)
- `POST /api/v1/work-orders`: Create production order. Body:
  ```json
  {
    "plant_id": "plant-uuid",
    "work_order_number": "WO-2026-9041",
    "product_id": "prod-uuid",
    "machine_id": "mach-uuid",
    "target_quantity": 500,
    "planned_start_date": "2026-10-01T06:00:00Z",
    "planned_end_date": "2026-10-03T18:00:00Z"
  }
  ```
- `GET /api/v1/work-orders`: List orders with pagination and filtering (`status`, `plant_id`, `limit`, `offset`).

### Customers & Vendors
- `POST /api/v1/customers` | `GET /api/v1/customers`: Master accounts for finished goods delivery.
- `POST /api/v1/vendors` | `GET /api/v1/vendors`: Supplier & tooling contractor registry.

---

## 4. Ingestion & Webhooks (`/api/v1/webhooks`)

### Meta WhatsApp Webhook Handshake
- **HTTP Method:** `GET`
- **Route:** `/api/v1/webhooks/whatsapp`
- **Auth:** Public (Verifies `hub.verify_token` against `settings.WHATSAPP_VERIFY_TOKEN`).
- **Response:** Plaintext challenge string or `403 Forbidden`.

### WhatsApp Message Ingestion
- **HTTP Method:** `POST`
- **Route:** `/api/v1/webhooks/whatsapp`
- **Auth:** Public (Verifies `X-Hub-Signature-256` HMAC header against registered secret).
- **Behavior:** Persists payload into `communication_messages` with status `RECEIVED`. Returns HTTP `200 OK` in < 50ms.

---

## 5. Manufacturing Events & Lineage (`/api/v1/events`)

### 1. List Canonical Events
- **HTTP Method:** `GET`
- **Route:** `/api/v1/events/`
- **Query Params:** `plant_id`, `status`, `from_time`, `to_time`, `limit`, `offset`.
- **Response Status:** `200 OK`
- **Response Body:** List of canonical manufacturing events with verified provenance.

### 2. Event Detail & Audit Lineage
- **HTTP Method:** `GET`
- **Route:** `/api/v1/events/{event_id}`
- **Auth:** `Bearer <TOKEN>`
- **Response Body:** Complete provenance tree including candidate extraction, entity resolution match scores, linked raw transcript, and audio storage URI.

### 3. Human Confirmation & Revisions
- **HTTP Method:** `POST`
- **Route:** `/api/v1/events/{event_id}/revisions`
- **Purpose:** Operator manually overrides a model-derived field (e.g. adjusts downtime from 480m to 360m).
- **Body:** `{"field_name": "downtime_minutes", "new_value": 360, "reason": "Shift handover confirmation"}`.
- **Audit:** Records human override with `EXPLICIT` provenance and archives previous revision.

---

## 6. Incidents & Blast-Radius Impacts (`/api/v1/incidents`)

### 1. List Incidents
- **HTTP Method:** `GET`
- **Route:** `/api/v1/incidents`
- **Query Params:** `status` (`ACTIVE`, `MONITORING`, `RESOLVED`, `CLOSED`), `plant_id`, `limit`, `offset`.
- **Response Status:** `200 OK`
- **Response Body:**
  ```json
  {
    "items": [
      {
        "id": "inc-uuid",
        "company_id": "comp-uuid",
        "plant_id": "plant-uuid",
        "machine_id": "mach-uuid",
        "title": "CNC-02 Spindle Bearing Failure",
        "status": "ACTIVE",
        "created_at": "2026-09-29T10:15:00Z",
        "updated_at": "2026-09-29T10:20:00Z",
        "resolved_at": null
      }
    ],
    "total": 1
  }
  ```

### 2. Incident Detail & Correlated Events
- **HTTP Method:** `GET`
- **Route:** `/api/v1/incidents/{id}`
- **Response Body:** Incident record, linked event array, and affected work order impact list.

### 3. Event Linking & Resolution
- `POST /api/v1/incidents/{id}/link-event`: Link additional failure event to active incident.
- `POST /api/v1/incidents/{id}/unlink-event`: Remove incorrectly correlated event.
- `POST /api/v1/incidents/{id}/resolve`: Mark incident `RESOLVED`. Triggers atomic risk recalculation.

---

## 7. Production Risk & Dashboards (`/api/v1/risk`)

### 1. Work Order Risk State
- **HTTP Method:** `GET`
- **Route:** `/api/v1/work-orders/{id}/risk`
- **Response:** `{"work_order_id": "...", "current_risk": "CRITICAL_DELAY", "delay_minutes": 480}`.

### 2. Plant Risk Dashboard
- **HTTP Method:** `GET`
- **Route:** `/api/v1/risk/dashboard`
- **Query Params:** `plant_id`
- **Response:** Aggregate risk distribution: total orders on time, at risk, critical, and top affected customers.

### 3. Risk Audit History
- **HTTP Method:** `GET`
- **Route:** `/api/v1/work-orders/{id}/risk/history`
- **Response:** Chronological ledger of state transitions and triggering events.

---

## 8. Operational Context & Chronology (`/api/v1`)

### 1. Unified Event Timeline
- **HTTP Method:** `GET`
- **Route:** `/api/v1/timeline`
- **Query Params:**
  - `entity_type`: `incident` or `work_order`
  - `entity_id`: UUID
  - `chronology`: `operational` (by occurrence time) or `audit` (by system insertion time)
  - `limit`: Default `50`
  - `cursor`: Keyset pagination cursor
- **Response:** Unified event stream merging physical events, risk shifts, and human decisions.

---

## 9. Alerts & Notification Policies (`/api/v1/alerts`)

- `GET /api/v1/alerts`: List active and acknowledged alert instances.
- `GET /api/v1/alerts/{alert_id}`: Alert detail with linked evidence references.
- `POST /api/v1/alerts/{alert_id}/transition`: State transitions (`ACKNOWLEDGE`, `RESOLVE`, `SNOOZE`).
- `POST /api/v1/alerts/jobs/{job_id}/retry`: Manually re-trigger a failed evaluation job.

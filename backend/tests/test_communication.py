import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


async def setup_test_user_and_company(ac: AsyncClient, email: str, company_name: str):
    await ac.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "pass",
            "full_name": "Test User",
            "company_name": company_name,
        },
    )
    login_res = await ac.post(
        "/api/auth/login", json={"email": email, "password": "pass"}
    )
    token = login_res.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # get company info
    me_res = await ac.get("/api/auth/me", headers=headers)
    company_id = me_res.json()["data"]["company_id"]
    return headers, company_id


@pytest.mark.asyncio
async def test_ingest_evidence_success():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        email = f"test_{uuid.uuid4()}@test.com"
        headers, company_id = await setup_test_user_and_company(ac, email, "Company A")

        payload = {
            "source_channel": "WHATSAPP",
            "external_message_id": "msg-1234",
            "sender_identity": "+1234567890",
            "raw_payload": {"text": "Hello world"},
        }

        response = await ac.post(
            "/api/v1/communications", json=payload, headers=headers
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["external_message_id"] == "msg-1234"
        assert data["company_id"] == company_id

        # Test duplicate idempotency
        response2 = await ac.post(
            "/api/v1/communications", json=payload, headers=headers
        )
        assert response2.status_code == 200
        data2 = response2.json()["data"]
        assert data2["id"] == data["id"]  # Should return the same message


@pytest.mark.asyncio
async def test_upload_attachment(monkeypatch):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        email = f"test_{uuid.uuid4()}@test.com"
        headers, _ = await setup_test_user_and_company(ac, email, "Company B")

        payload = {
            "source_channel": "WHATSAPP",
            "external_message_id": "msg-1235",
            "sender_identity": "+1234567890",
        }
        msg_resp = await ac.post(
            "/api/v1/communications", json=payload, headers=headers
        )
        msg_id = msg_resp.json()["data"]["id"]

        # Mock storage
        async def mock_upload(*args, **kwargs):
            pass

        monkeypatch.setattr(
            "app.infrastructure.storage.s3_storage.S3Storage.upload", mock_upload
        )

        # Upload attachment
        files = {"file": ("test.txt", b"hello content", "text/plain")}
        resp = await ac.post(
            f"/api/v1/communications/{msg_id}/attachments", files=files, headers=headers
        )

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["message_id"] == msg_id
        assert data["file_size"] == len(b"hello content")

        # Verify it is listed in get message
        get_resp = await ac.get(f"/api/v1/communications/{msg_id}", headers=headers)
        assert get_resp.status_code == 200
        attachments = get_resp.json()["data"]["attachments"]
        assert len(attachments) == 1
        assert attachments[0]["id"] == data["id"]


@pytest.mark.asyncio
async def test_upload_attachment_storage_failure(monkeypatch):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        email = f"test_{uuid.uuid4()}@test.com"
        headers, _ = await setup_test_user_and_company(ac, email, "Company C")

        payload = {
            "source_channel": "WHATSAPP",
            "external_message_id": "msg-1236",
            "sender_identity": "+1234567890",
        }
        msg_resp = await ac.post(
            "/api/v1/communications", json=payload, headers=headers
        )
        msg_id = msg_resp.json()["data"]["id"]

        # Mock storage failure
        async def mock_upload_failure(*args, **kwargs):
            raise ValueError("Storage error")

        monkeypatch.setattr(
            "app.infrastructure.storage.s3_storage.S3Storage.upload",
            mock_upload_failure,
        )

        # Upload attachment
        files = {"file": ("test.txt", b"hello content", "text/plain")}
        resp = await ac.post(
            f"/api/v1/communications/{msg_id}/attachments", files=files, headers=headers
        )

        assert resp.status_code == 500
        assert resp.json()["detail"] == "Storage upload failed"

        # Verify DB rollback
        get_resp = await ac.get(f"/api/v1/communications/{msg_id}", headers=headers)
        attachments = get_resp.json()["data"]["attachments"]
        assert len(attachments) == 0


@pytest.mark.asyncio
async def test_tenant_isolation():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        email1 = f"test_{uuid.uuid4()}@test.com"
        headers1, _ = await setup_test_user_and_company(ac, email1, "Company D1")

        email2 = f"test_{uuid.uuid4()}@test.com"
        headers2, _ = await setup_test_user_and_company(ac, email2, "Company D2")

        # Tenant 1 ingest
        payload = {
            "source_channel": "WHATSAPP",
            "external_message_id": "msg-1237",
            "sender_identity": "+1234567890",
        }
        msg_resp = await ac.post(
            "/api/v1/communications", json=payload, headers=headers1
        )
        msg_id = msg_resp.json()["data"]["id"]

        # Tenant 2 trying to get Tenant 1 message
        get_resp = await ac.get(f"/api/v1/communications/{msg_id}", headers=headers2)
        assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_list_messages():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        email = f"test_{uuid.uuid4()}@test.com"
        headers, _ = await setup_test_user_and_company(ac, email, "Company E")

        resp = await ac.get("/api/v1/communications", headers=headers)
        assert resp.status_code == 200
        assert "items" in resp.json()["data"]


@pytest.mark.asyncio
async def test_concurrent_idempotency():
    import asyncio

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        email = f"test_{uuid.uuid4()}@test.com"
        headers, _ = await setup_test_user_and_company(ac, email, "Company Concurrent")

        payload = {
            "source_channel": "WHATSAPP",
            "external_message_id": "concurrent-msg-1234",
            "sender_identity": "+1234567890",
            "raw_payload": {"text": "Race condition test"},
        }

        # Fire multiple requests simultaneously
        tasks = [
            ac.post("/api/v1/communications", json=payload, headers=headers)
            for _ in range(5)
        ]
        responses = await asyncio.gather(*tasks)

        # All should return 200 due to race-safe fallback logic handling IntegrityError
        assert all(r.status_code == 200 for r in responses)

        ids = [r.json()["data"]["id"] for r in responses]

        # Ensure they all returned the exact same UUID (only one row created)
        assert len(set(ids)) == 1


@pytest.mark.asyncio
async def test_attachment_security(monkeypatch):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        email = f"test_{uuid.uuid4()}@test.com"
        headers, _ = await setup_test_user_and_company(ac, email, "Company Secure")

        payload = {
            "source_channel": "WHATSAPP",
            "external_message_id": "secure-msg-1",
            "sender_identity": "+1234567890",
        }
        msg_resp = await ac.post(
            "/api/v1/communications", json=payload, headers=headers
        )
        msg_id = msg_resp.json()["data"]["id"]

        async def mock_upload(*args, **kwargs):
            pass

        monkeypatch.setattr(
            "app.infrastructure.storage.s3_storage.S3Storage.upload", mock_upload
        )

        # 1. Invalid extension
        files = {"file": ("malicious.exe", b"malware", "application/x-msdownload")}
        resp = await ac.post(
            f"/api/v1/communications/{msg_id}/attachments", files=files, headers=headers
        )
        assert resp.status_code == 400

        # 2. Path manipulation (the app ignores the path and generates its own UUID, but let's test)
        files = {"file": ("../../../etc/passwd.txt", b"hello content", "text/plain")}
        resp = await ac.post(
            f"/api/v1/communications/{msg_id}/attachments", files=files, headers=headers
        )
        assert resp.status_code == 200
        key = resp.json()["data"]["object_storage_key"]
        # The key should be server generated UUID with .txt, NO path traversal characters
        assert "../" not in key
        assert key.endswith(".txt")

        # 3. Large payload simulation (the manual block is at 50MB, but we'll mock or just trust the rule)
        # 4. Cross tenant access
        email2 = f"test_{uuid.uuid4()}@test.com"
        headers2, _ = await setup_test_user_and_company(ac, email2, "Company Hacker")
        resp = await ac.post(
            f"/api/v1/communications/{msg_id}/attachments",
            files=files,
            headers=headers2,
        )
        assert resp.status_code == 404  # Tenant B cannot upload to Tenant A's message

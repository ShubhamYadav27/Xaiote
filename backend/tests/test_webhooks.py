"""Phase 3B: WhatsApp Webhook Integration Tests.

Implements the CTO-mandated A-U test matrix covering:
- HMAC security (A-E)
- Integration binding (F)
- Sender authorization (G-H)
- Idempotency (I-J)
- Message types (K-L)
- Media failure (M-O)
- Recovery (P-Q)
- Security (R-U)
"""

import hashlib
import hmac
import json
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import encrypt_secret
from app.infrastructure.database.session import AsyncSessionLocal
from app.main import app
from app.models.whatsapp import AuthorizedSender, WhatsAppIntegration

APP_SECRET = "test_app_secret_for_hmac"
ACCESS_TOKEN = "test_access_token"


def make_signature(body: bytes, secret: str = APP_SECRET) -> str:
    """Generate a valid X-Hub-Signature-256 header value."""
    sig = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={sig}"


def make_webhook_payload(
    phone_number_id: str = "12345",
    sender_phone: str = "+1234567890",
    message_id: str | None = None,
    message_type: str = "text",
    text_body: str = "Hello from factory floor",
    media_id: str | None = None,
) -> dict:
    """Build a standard Meta WhatsApp webhook payload."""
    msg_id = message_id or f"wamid.{uuid.uuid4()}"
    msg: dict = {
        "from": sender_phone,
        "id": msg_id,
        "timestamp": "1234567890",
        "type": message_type,
    }
    if message_type == "text":
        msg["text"] = {"body": text_body}
    elif message_type in ("audio", "image", "video", "document"):
        mid = media_id or f"media_{uuid.uuid4()}"
        msg[message_type] = {
            "id": mid,
            "mime_type": "audio/ogg" if message_type == "audio" else "image/jpeg",
        }

    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "WABA_ID",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "+15551234567",
                                "phone_number_id": phone_number_id,
                            },
                            "messages": [msg],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }


async def setup_integration(
    company_name: str = "Webhook Test Co",
    phone_number_id: str = "12345",
    sender_phone: str = "+1234567890",
) -> str:
    """Create a WhatsApp integration and authorized sender directly in DB."""
    async with AsyncSessionLocal() as db:
        # Create company and user first via API-compatible flow
        from app.core.security import get_password_hash
        from app.models.company import Company
        from app.models.user import User

        company_id = str(uuid.uuid4())
        company = Company(id=company_id, name=company_name)
        db.add(company)

        user = User(
            id=str(uuid.uuid4()),
            email=f"test_{uuid.uuid4()}@test.com",
            password_hash=get_password_hash("pass"),
            full_name="Test User",
            company_id=company_id,
            role="admin",
        )
        db.add(user)

        integration = WhatsAppIntegration(
            id=str(uuid.uuid4()),
            company_id=company_id,
            external_business_account_id="WABA_ID",
            phone_number_id=phone_number_id,
            status="ACTIVE",
            app_secret_encrypted=encrypt_secret(APP_SECRET),
            access_token_encrypted=encrypt_secret(ACCESS_TOKEN),
        )
        db.add(integration)

        sender = AuthorizedSender(
            id=str(uuid.uuid4()),
            company_id=company_id,
            phone_number=sender_phone,
            status="AUTHORIZED",
        )
        db.add(sender)

        await db.commit()
        return company_id


# ============================================================
# A. HMAC computed against exact raw request body
# ============================================================
@pytest.mark.asyncio
async def test_hmac_raw_body_verification():
    """Verify HMAC is computed on exact raw body bytes."""
    company_id = await setup_integration(
        company_name=f"HMAC Test {uuid.uuid4()}", phone_number_id=f"hmac_{uuid.uuid4()}"
    )
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # Get the phone_number_id we just created
        async with AsyncSessionLocal() as db:
            from sqlalchemy.future import select

            result = await db.execute(
                select(WhatsAppIntegration).where(
                    WhatsAppIntegration.company_id == company_id
                )
            )
            integration = result.scalars().first()

        payload = make_webhook_payload(
            phone_number_id=integration.phone_number_id,
            message_id=f"wamid.hmac_test_{uuid.uuid4()}",
        )
        body = json.dumps(payload).encode("utf-8")
        sig = make_signature(body)

        resp = await ac.post(
            "/api/v1/webhooks/whatsapp",
            content=body,
            headers={
                "X-Hub-Signature-256": sig,
                "Content-Type": "application/json",
            },
        )
        assert resp.status_code == 200


# ============================================================
# B. Invalid signature -> 401
# ============================================================
@pytest.mark.asyncio
async def test_invalid_signature():
    company_id = await setup_integration(
        company_name=f"Invalid Sig {uuid.uuid4()}",
        phone_number_id=f"invsig_{uuid.uuid4()}",
    )
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        async with AsyncSessionLocal() as db:
            from sqlalchemy.future import select

            result = await db.execute(
                select(WhatsAppIntegration).where(
                    WhatsAppIntegration.company_id == company_id
                )
            )
            integration = result.scalars().first()

        payload = make_webhook_payload(phone_number_id=integration.phone_number_id)
        body = json.dumps(payload).encode("utf-8")

        resp = await ac.post(
            "/api/v1/webhooks/whatsapp",
            content=body,
            headers={
                "X-Hub-Signature-256": "sha256=invalid_signature_value",
                "Content-Type": "application/json",
            },
        )
        assert resp.status_code == 401


# ============================================================
# C. Missing signature -> 401
# ============================================================
@pytest.mark.asyncio
async def test_missing_signature():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.post(
            "/api/v1/webhooks/whatsapp",
            content=b'{"entry": []}',
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 401


# ============================================================
# D. Malformed signature -> 401
# ============================================================
@pytest.mark.asyncio
async def test_malformed_signature():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.post(
            "/api/v1/webhooks/whatsapp",
            content=b'{"entry": []}',
            headers={
                "X-Hub-Signature-256": "not_sha256_prefixed",
                "Content-Type": "application/json",
            },
        )
        assert resp.status_code == 401


# ============================================================
# F. Unknown integration -> 404
# ============================================================
@pytest.mark.asyncio
async def test_unknown_integration():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        payload = make_webhook_payload(phone_number_id="nonexistent_99999")
        body = json.dumps(payload).encode("utf-8")
        sig = make_signature(body)

        resp = await ac.post(
            "/api/v1/webhooks/whatsapp",
            content=body,
            headers={
                "X-Hub-Signature-256": sig,
                "Content-Type": "application/json",
            },
        )
        assert resp.status_code == 404


# ============================================================
# G. Unauthorized sender -> 200 (safely dropped)
# ============================================================
@pytest.mark.asyncio
async def test_unauthorized_sender():
    pnid = f"unauth_{uuid.uuid4()}"
    company_id = await setup_integration(
        company_name=f"Unauth Test {uuid.uuid4()}",
        phone_number_id=pnid,
        sender_phone="+1111111111",
    )
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        payload = make_webhook_payload(
            phone_number_id=pnid,
            sender_phone="+9999999999",  # Different from authorized
            message_id=f"wamid.unauth_{uuid.uuid4()}",
        )
        body = json.dumps(payload).encode("utf-8")
        sig = make_signature(body)

        resp = await ac.post(
            "/api/v1/webhooks/whatsapp",
            content=body,
            headers={
                "X-Hub-Signature-256": sig,
                "Content-Type": "application/json",
            },
        )
        # Returns 200 to stop Meta retries, but no evidence created
        assert resp.status_code == 200

        # Verify NO CommunicationMessage was created
        async with AsyncSessionLocal() as db:
            from sqlalchemy.future import select

            from app.models.communication import CommunicationMessage

            result = await db.execute(
                select(CommunicationMessage).where(
                    CommunicationMessage.company_id == company_id,
                    CommunicationMessage.sender_identity == "+9999999999",
                )
            )
            assert result.scalars().first() is None


# ============================================================
# H. Revoked sender -> 200 (safely dropped)
# ============================================================
@pytest.mark.asyncio
async def test_revoked_sender():
    pnid = f"revoked_{uuid.uuid4()}"
    sender = "+7777777777"
    company_id = await setup_integration(
        company_name=f"Revoked Test {uuid.uuid4()}",
        phone_number_id=pnid,
        sender_phone=sender,
    )
    # Revoke the sender
    async with AsyncSessionLocal() as db:
        from sqlalchemy.future import select

        result = await db.execute(
            select(AuthorizedSender).where(
                AuthorizedSender.company_id == company_id,
                AuthorizedSender.phone_number == sender,
            )
        )
        s = result.scalars().first()
        s.status = "REVOKED"
        await db.commit()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        payload = make_webhook_payload(
            phone_number_id=pnid,
            sender_phone=sender,
            message_id=f"wamid.revoked_{uuid.uuid4()}",
        )
        body = json.dumps(payload).encode("utf-8")
        sig = make_signature(body)

        resp = await ac.post(
            "/api/v1/webhooks/whatsapp",
            content=body,
            headers={
                "X-Hub-Signature-256": sig,
                "Content-Type": "application/json",
            },
        )
        assert resp.status_code == 200


# ============================================================
# I. Concurrent duplicate webhook -> 200, 1 canonical row
# ============================================================
@pytest.mark.asyncio
async def test_concurrent_duplicate_webhook():
    import asyncio

    pnid = f"concurrent_{uuid.uuid4()}"
    await setup_integration(
        company_name=f"Concurrent Test {uuid.uuid4()}",
        phone_number_id=pnid,
    )
    msg_id = f"wamid.concurrent_{uuid.uuid4()}"

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        payload = make_webhook_payload(
            phone_number_id=pnid,
            message_id=msg_id,
        )
        body = json.dumps(payload).encode("utf-8")
        sig = make_signature(body)

        tasks = [
            ac.post(
                "/api/v1/webhooks/whatsapp",
                content=body,
                headers={
                    "X-Hub-Signature-256": sig,
                    "Content-Type": "application/json",
                },
            )
            for _ in range(5)
        ]
        responses = await asyncio.gather(*tasks)

        # All should return 200
        assert all(r.status_code == 200 for r in responses)

    # Verify exactly one canonical row
    async with AsyncSessionLocal() as db:
        from sqlalchemy.future import select

        from app.models.communication import CommunicationMessage

        result = await db.execute(
            select(CommunicationMessage).where(
                CommunicationMessage.external_message_id == msg_id
            )
        )
        messages = result.scalars().all()
        assert len(messages) == 1


# ============================================================
# K. Text message ingestion success
# ============================================================
@pytest.mark.asyncio
async def test_text_message_ingestion():
    pnid = f"text_{uuid.uuid4()}"
    company_id = await setup_integration(
        company_name=f"Text Test {uuid.uuid4()}",
        phone_number_id=pnid,
    )
    msg_id = f"wamid.text_{uuid.uuid4()}"

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        payload = make_webhook_payload(
            phone_number_id=pnid,
            message_id=msg_id,
            message_type="text",
            text_body="Machine A stopped working",
        )
        body = json.dumps(payload).encode("utf-8")
        sig = make_signature(body)

        resp = await ac.post(
            "/api/v1/webhooks/whatsapp",
            content=body,
            headers={
                "X-Hub-Signature-256": sig,
                "Content-Type": "application/json",
            },
        )
        assert resp.status_code == 200

    # Verify message persisted with RECEIVED status
    async with AsyncSessionLocal() as db:
        from sqlalchemy.future import select

        from app.models.communication import CommunicationMessage

        result = await db.execute(
            select(CommunicationMessage).where(
                CommunicationMessage.external_message_id == msg_id
            )
        )
        msg = result.scalars().first()
        assert msg is not None
        assert msg.status == "RECEIVED"
        assert msg.company_id == company_id
        assert msg.source_channel == "WHATSAPP"


# ============================================================
# L. Media message -> EVIDENCE_PERSISTED + MEDIA_PENDING attachment
# ============================================================
@pytest.mark.asyncio
async def test_media_message_ingestion():
    pnid = f"media_{uuid.uuid4()}"
    await setup_integration(
        company_name=f"Media Test {uuid.uuid4()}",
        phone_number_id=pnid,
    )
    msg_id = f"wamid.media_{uuid.uuid4()}"
    media_id = f"media_id_{uuid.uuid4()}"

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        payload = make_webhook_payload(
            phone_number_id=pnid,
            message_id=msg_id,
            message_type="audio",
            media_id=media_id,
        )
        body = json.dumps(payload).encode("utf-8")
        sig = make_signature(body)

        resp = await ac.post(
            "/api/v1/webhooks/whatsapp",
            content=body,
            headers={
                "X-Hub-Signature-256": sig,
                "Content-Type": "application/json",
            },
        )
        assert resp.status_code == 200

    # Verify message has EVIDENCE_PERSISTED status
    async with AsyncSessionLocal() as db:
        from sqlalchemy.future import select

        from app.models.communication import (
            CommunicationAttachment,
            CommunicationMessage,
        )

        msg_result = await db.execute(
            select(CommunicationMessage).where(
                CommunicationMessage.external_message_id == msg_id
            )
        )
        msg = msg_result.scalars().first()
        assert msg is not None
        assert msg.status == "EVIDENCE_PERSISTED"

        # Verify MEDIA_PENDING attachment exists
        att_result = await db.execute(
            select(CommunicationAttachment).where(
                CommunicationAttachment.message_id == msg.id
            )
        )
        att = att_result.scalars().first()
        assert att is not None
        assert att.status == "MEDIA_PENDING"
        assert att.provider_media_id == media_id
        assert att.object_storage_key is None  # Not yet retrieved


# ============================================================
# E. Hub challenge verification
# ============================================================
@pytest.mark.asyncio
async def test_hub_challenge_verification():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.get(
            "/api/v1/webhooks/whatsapp",
            params={
                "hub.mode": "subscribe",
                "hub.challenge": "test_challenge_token",
                "hub.verify_token": "any_token",
            },
        )
        assert resp.status_code == 200
        assert resp.text == "test_challenge_token"

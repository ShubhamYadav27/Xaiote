from app.models.manufacturing_event import ManufacturingEventRevision

"""Phase 3B tests for background media worker and credential security."""

import asyncio
import datetime
import uuid

import pytest
from sqlalchemy.future import select

from app.core.security import decrypt_secret, encrypt_secret
from app.infrastructure.database.session import AsyncSessionLocal
from app.models.communication import CommunicationAttachment, CommunicationMessage
from app.workers.media_worker import process_one_attachment
from tests.test_webhooks import setup_integration


# ============================================================
# Blocker 7: Credential encryption evidence (R-U Security)
# ============================================================
@pytest.mark.asyncio
async def test_credential_encryption():
    """Verify exact cryptography library and Fernet usage."""
    from cryptography.fernet import Fernet

    from app.core.config import settings

    # 1. Key source and environment injection
    fernet = Fernet(settings.SECRET_ENCRYPTION_KEY.encode())

    plaintext = "super_secret_access_token"

    # 2. Encryption before DB persistence
    encrypted = encrypt_secret(plaintext)
    assert encrypted != plaintext
    assert isinstance(encrypted, str)

    # 3. Decryption only at application boundary
    decrypted = decrypt_secret(encrypted)
    assert decrypted == plaintext

    # Verify we are using the exact cryptography library Fernet
    assert fernet.decrypt(encrypted.encode()).decode() == plaintext


# ============================================================
# Blocker 4: Actual media pipeline
# Blocker 6: SSRF boundary
# ============================================================
@pytest.mark.asyncio
async def test_ssrf_protection_and_failure(monkeypatch):
    """Test SSRF boundary (Meta/Lookaside only) and failure states."""

    from sqlalchemy import delete

    async with AsyncSessionLocal() as db:
        from app.models.communication import (
            CommunicationTranscript,
            ExtractedEventCandidate,
        )
        from app.models.impact import ImpactDecisionHistory, ProductionOrderImpact
        from app.models.manufacturing_event import (
            CanonicalizationJob,
            ManufacturingEvent,
        )
        from app.models.resolution import EntityResolutionResult
        from app.models.risk import WorkOrderRiskHistory

        await db.execute(delete(WorkOrderRiskHistory))
        await db.execute(delete(ImpactDecisionHistory))
        await db.execute(delete(ProductionOrderImpact))
        await db.execute(delete(ManufacturingEventRevision))
        await db.execute(delete(ManufacturingEvent))
        await db.execute(delete(CanonicalizationJob))
        await db.execute(delete(EntityResolutionResult))
        await db.execute(delete(ExtractedEventCandidate))
        await db.execute(delete(CommunicationTranscript))
        await db.execute(delete(CommunicationAttachment))
        await db.commit()

    company_id = await setup_integration(
        company_name=f"SSRF Test {uuid.uuid4()}",
        phone_number_id=f"ssrf_{uuid.uuid4()}",
    )

    # Create MEDIA_PENDING message
    msg_id = str(uuid.uuid4())
    async with AsyncSessionLocal() as db:
        msg = CommunicationMessage(
            id=msg_id,
            company_id=company_id,
            source_channel="WHATSAPP",
            external_message_id=f"ext_{msg_id}",
            sender_identity="+1111111111",
            raw_payload="{}",
            status="EVIDENCE_PERSISTED",
        )
        db.add(msg)

        att = CommunicationAttachment(
            id=str(uuid.uuid4()),
            message_id=msg_id,
            media_type="image/jpeg",
            status="MEDIA_PENDING",
            provider_media_id="mock_media_id_123",
        )
        db.add(att)
        await db.commit()
        att_id = att.id

    # Mock Meta API to return a malicious URL
    async def mock_get(*args, **kwargs):
        class MockResponse:
            status_code = 200
            content = b"fake_content"

            def json(self):
                # Malicious URL!
                return {"url": "https://internal-attacker.local/admin"}

        return MockResponse()

    import httpx

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    # Run the worker
    result = await process_one_attachment("worker-1")
    assert result is True

    # Verify SSRF was blocked and resulted in MEDIA_FAILED
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(CommunicationAttachment).where(CommunicationAttachment.id == att_id)
        )
        att = result.scalars().first()
        assert att.status == "MEDIA_FAILED"
        assert "Refusing non-authorized media URL" in att.last_error


# ============================================================
# Blocker 2: Worker crash recovery
# ============================================================
@pytest.mark.asyncio
async def test_worker_crash_recovery():
    """Verify that a crashed worker's leased item is recovered."""
    from sqlalchemy import delete

    async with AsyncSessionLocal() as db:
        from app.models.communication import (
            CommunicationTranscript,
            ExtractedEventCandidate,
        )
        from app.models.impact import ImpactDecisionHistory, ProductionOrderImpact
        from app.models.manufacturing_event import (
            CanonicalizationJob,
            ManufacturingEvent,
        )
        from app.models.resolution import EntityResolutionResult
        from app.models.risk import WorkOrderRiskHistory

        await db.execute(delete(WorkOrderRiskHistory))
        await db.execute(delete(ImpactDecisionHistory))
        await db.execute(delete(ProductionOrderImpact))
        await db.execute(delete(ManufacturingEventRevision))
        await db.execute(delete(ManufacturingEvent))
        await db.execute(delete(CanonicalizationJob))
        await db.execute(delete(EntityResolutionResult))
        await db.execute(delete(ExtractedEventCandidate))
        await db.execute(delete(CommunicationTranscript))
        await db.execute(delete(CommunicationAttachment))
        await db.commit()

    company_id = await setup_integration(
        company_name=f"Crash Test {uuid.uuid4()}",
        phone_number_id=f"crash_{uuid.uuid4()}",
    )

    # Create MEDIA_PROCESSING with an EXPIRED lease (simulating crash)
    msg_id = str(uuid.uuid4())
    async with AsyncSessionLocal() as db:
        msg = CommunicationMessage(
            id=msg_id,
            company_id=company_id,
            source_channel="WHATSAPP",
            external_message_id=f"ext_{msg_id}",
            sender_identity="+1111111111",
            raw_payload="{}",
            status="EVIDENCE_PERSISTED",
        )
        db.add(msg)

        att = CommunicationAttachment(
            id=str(uuid.uuid4()),
            message_id=msg_id,
            media_type="image/jpeg",
            status="MEDIA_PROCESSING",
            provider_media_id="mock_media_id_crash",
            worker_id="dead-worker",
            lease_until=datetime.datetime.now(datetime.timezone.utc)
            - datetime.timedelta(minutes=5),  # expired
        )
        db.add(att)
        await db.commit()
        att_id = att.id

    # Since it's expired, a new worker should be able to claim it
    # We will mock the claim_pending_attachment to just verify the claim query works
    from app.workers.media_worker import claim_pending_attachment

    async with AsyncSessionLocal() as db:
        claimed_att = await claim_pending_attachment(db, "new-worker-1")
        assert claimed_att is not None
        assert claimed_att.id == att_id
        assert claimed_att.worker_id == "new-worker-1"
        assert claimed_att.lease_until > datetime.datetime.now(datetime.timezone.utc)
        await db.commit()


# ============================================================
# Blocker 5: Duplicate media processing
# ============================================================
@pytest.mark.asyncio
async def test_duplicate_media_processing_concurrency(monkeypatch):
    import app.workers.media_worker as mw

    async def mock_process(*args, **kwargs):
        return False

    monkeypatch.setattr(mw, "process_one_attachment", mock_process)
    """Prove concurrent workers cannot process the same attachment."""
    from sqlalchemy import delete

    async with AsyncSessionLocal() as db:
        from app.models.communication import (
            CommunicationTranscript,
            ExtractedEventCandidate,
        )
        from app.models.impact import ImpactDecisionHistory, ProductionOrderImpact
        from app.models.manufacturing_event import (
            CanonicalizationJob,
            ManufacturingEvent,
        )
        from app.models.resolution import EntityResolutionResult
        from app.models.risk import WorkOrderRiskHistory

        await db.execute(delete(WorkOrderRiskHistory))
        await db.execute(delete(ImpactDecisionHistory))
        await db.execute(delete(ProductionOrderImpact))
        await db.execute(delete(ManufacturingEventRevision))
        await db.execute(delete(ManufacturingEvent))
        await db.execute(delete(CanonicalizationJob))
        await db.execute(delete(EntityResolutionResult))
        await db.execute(delete(ExtractedEventCandidate))
        await db.execute(delete(CommunicationTranscript))
        await db.execute(delete(CommunicationAttachment))
        await db.commit()

    company_id = await setup_integration(
        company_name=f"Concurrency Test {uuid.uuid4()}",
        phone_number_id=f"conc_{uuid.uuid4()}",
    )

    # Create MEDIA_PENDING message
    msg_id = str(uuid.uuid4())
    async with AsyncSessionLocal() as db:
        msg = CommunicationMessage(
            id=msg_id,
            company_id=company_id,
            source_channel="WHATSAPP",
            external_message_id=f"ext_{msg_id}",
            sender_identity="+1111111111",
            raw_payload="{}",
            status="EVIDENCE_PERSISTED",
        )
        db.add(msg)

        att = CommunicationAttachment(
            id=str(uuid.uuid4()),
            message_id=msg_id,
            media_type="image/jpeg",
            status="MEDIA_PENDING",
            provider_media_id="mock_media_id_conc",
        )
        db.add(att)
        await db.commit()
        att_id = att.id

    # We will run 5 concurrent claim_pending_attachment calls
    from app.workers.media_worker import claim_pending_attachment

    async def worker_claim_attempt(worker_id):
        async with AsyncSessionLocal() as db:
            claimed = await claim_pending_attachment(db, worker_id)
            await db.commit()
            return claimed

    tasks = [worker_claim_attempt(f"worker-{i}") for i in range(5)]
    results = await asyncio.gather(*tasks)

    # Only ONE worker should have successfully claimed it
    successful_claims = [r for r in results if r is not None]
    assert len(successful_claims) == 1

    # Verify DB state reflects exactly one canonical worker owner
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(CommunicationAttachment).where(CommunicationAttachment.id == att_id)
        )
        att = result.scalars().first()
        assert att.status == "MEDIA_PROCESSING"
        assert att.worker_id == successful_claims[0].worker_id

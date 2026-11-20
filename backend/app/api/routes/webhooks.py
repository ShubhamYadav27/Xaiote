"""Phase 3B: WhatsApp Webhook Integration.

Implements the durable evidence envelope pattern:
1. Read raw HTTP body bytes
2. Verify HMAC-SHA256 signature on raw bytes
3. Resolve integration -> tenant
4. Authorize sender
5. Persist durable communication envelope
6. PostgreSQL COMMIT
7. HTTP 200 OK

Media retrieval happens asynchronously via the PostgreSQL-backed media worker.
"""

import hashlib
import hmac as hmac_mod
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.security import decrypt_secret
from app.infrastructure.database.session import get_db
from app.models.communication import CommunicationAttachment, CommunicationMessage
from app.models.whatsapp import AuthorizedSender, WhatsAppIntegration

router = APIRouter()
logger = logging.getLogger(__name__)

MAX_MEDIA_TYPES = {"image", "video", "audio", "document"}


from app.core.config import settings

@router.get("/whatsapp")
async def verify_whatsapp_webhook(request: Request) -> Response:
    """Meta webhook verification handshake."""
    hub_mode = request.query_params.get("hub.mode")
    hub_challenge = request.query_params.get("hub.challenge")
    hub_verify_token = request.query_params.get("hub.verify_token")

    if hub_mode == "subscribe" and hub_challenge:
        if hub_verify_token != settings.WHATSAPP_VERIFY_TOKEN:
            raise HTTPException(status_code=403, detail="Invalid verification token")
        return Response(content=hub_challenge, media_type="text/plain")

    raise HTTPException(status_code=400, detail="Invalid verify request")


@router.post("/whatsapp")
async def handle_whatsapp_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Process incoming WhatsApp webhook.

    Sequence:
    1. Read raw body bytes
    2. Check signature header exists
    3. Parse JSON to extract phone_number_id for integration lookup
    4. Lookup integration, decrypt app_secret
    5. Verify HMAC-SHA256 on raw body bytes with constant-time comparison
    6. Authorize sender
    7. Persist durable envelope
    8. Return 200 OK
    """
    # Step 1: Read exact raw body bytes - NEVER modify these
    raw_body = await request.body()

    # Step 2: Check signature header presence
    signature_header = request.headers.get("X-Hub-Signature-256")
    if not signature_header:
        raise HTTPException(status_code=401, detail="Missing signature")

    if not signature_header.startswith("sha256="):
        raise HTTPException(status_code=401, detail="Malformed signature")

    # Step 3: Parse JSON for integration lookup ONLY
    try:
        data = json.loads(raw_body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # Extract phone_number_id for integration resolution
    try:
        entry = data["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]
        phone_number_id = value["metadata"]["phone_number_id"]
    except (KeyError, IndexError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid payload structure")

    # Step 4: Lookup integration by phone_number_id
    integration_result = await db.execute(
        select(WhatsAppIntegration).where(
            WhatsAppIntegration.phone_number_id == phone_number_id,
            WhatsAppIntegration.status == "ACTIVE",
        )
    )
    integration = integration_result.scalars().first()
    if not integration:
        raise HTTPException(status_code=404, detail=f"Unknown integration for {phone_number_id}")

    # Step 5: Verify HMAC-SHA256 on the EXACT RAW BODY BYTES
    app_secret = decrypt_secret(integration.app_secret_encrypted)
    expected_hash = hmac_mod.new(
        app_secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    expected_signature = f"sha256={expected_hash}"

    if not hmac_mod.compare_digest(expected_signature, signature_header):
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Step 6: Extract messages from validated payload
    messages = value.get("messages", [])
    if not messages:
        # Status update or other non-message webhook - acknowledge safely
        return Response(content="OK", status_code=200)

    msg = messages[0]
    sender_phone = msg.get("from", "")
    external_message_id = msg.get("id", "")

    if not sender_phone or not external_message_id:
        return Response(content="OK", status_code=200)

    # Step 7: Authorize sender
    company_id = integration.company_id
    sender_result = await db.execute(
        select(AuthorizedSender).where(
            AuthorizedSender.company_id == company_id,
            AuthorizedSender.phone_number == sender_phone,
            AuthorizedSender.status == "AUTHORIZED",
        )
    )
    sender = sender_result.scalars().first()

    if not sender:
        # Unauthorized sender: return 200 to stop Meta retries,
        # but do NOT create any evidence records
        logger.warning(
            "Unauthorized sender dropped",
            extra={
                "phone_number": sender_phone,
                "company_id": company_id,
                "integration_id": integration.id,
            },
        )
        return Response(content="OK", status_code=200)

    # Step 8: Determine message type and status
    message_type = msg.get("type", "text")
    has_media = message_type in MAX_MEDIA_TYPES
    initial_status = "RECEIVED"

    # Step 9: Persist durable communication envelope
    # Store raw_payload as the exact raw JSON string for provenance
    comm_msg = CommunicationMessage(
        company_id=company_id,
        source_channel="WHATSAPP",
        external_message_id=external_message_id,
        sender_identity=sender_phone,
        raw_payload=raw_body.decode("utf-8"),
        status=initial_status,
    )
    db.add(comm_msg)

    try:
        await db.flush()
    except IntegrityError:
        # Duplicate webhook / provider retry - safe idempotent response
        await db.rollback()
        logger.info(
            "Duplicate webhook safely deduplicated",
            extra={"external_message_id": external_message_id},
        )
        return Response(content="OK", status_code=200)

    # Step 11: COMMIT the durable envelope
    await db.commit()

    logger.info(
        "Webhook evidence persisted",
        extra={
            "message_id": comm_msg.id,
            "company_id": company_id,
            "external_message_id": external_message_id,
            "source_channel": "WHATSAPP",
            "status": initial_status,
            "has_media": has_media,
        },
    )

    # Step 12: Return 200 OK - media retrieval will happen asynchronously
    return Response(content="OK", status_code=200)

import os
path = 'backend/app/api/routes/webhooks.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

replacement = """    if has_media:
        media_data = msg.get(message_type, {})
        provider_media_id = media_data.get("id", "")
        mime_type = media_data.get("mime_type", "application/octet-stream")

        if provider_media_id:
            attachment = CommunicationAttachment(
                message_id=comm_msg.id,
                media_type=mime_type,
                status="MEDIA_PENDING",
                provider_media_id=provider_media_id,
            )
            db.add(attachment)
    else:
        import uuid
        from app.models.communication import CommunicationTranscript, ExtractedEventCandidate
        text_body = msg.get("text", {}).get("body", "")
        if text_body:
            attachment = CommunicationAttachment(
                id=str(uuid.uuid4()),
                message_id=comm_msg.id,
                media_type="text/plain",
                status="MEDIA_PERSISTED",
                file_size=len(text_body)
            )
            db.add(attachment)
            
            transcript = CommunicationTranscript(
                id=str(uuid.uuid4()),
                company_id=company_id,
                attachment_id=attachment.id,
                provider="META_WHATSAPP_TEXT",
                model="DIRECT",
                language="en",
                status="COMPLETED",
                provider_transcript=text_body,
                corrected_transcript=text_body
            )
            db.add(transcript)
            
            candidate = ExtractedEventCandidate(
                id=str(uuid.uuid4()),
                company_id=company_id,
                transcript_id=transcript.id,
                processing_status="PENDING"
            )
            db.add(candidate)"""

import re
new_content = re.sub(r'    if has_media:.*?            db.add\(attachment\)', replacement, content, flags=re.DOTALL)

with open(path, 'w', encoding='utf-8') as f:
    f.write(new_content)

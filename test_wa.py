import hmac
import hashlib
import json
import requests

secret = b"9e9d911208e93bd3fe22c5fdd924cf8d"
payload = {
    "object": "whatsapp_business_account",
    "entry": [{
        "id": "1084709697348460",
        "changes": [{
            "value": {
                "messaging_product": "whatsapp",
                "metadata": {
                    "display_phone_number": "1234567890",
                    "phone_number_id": "8303357161"
                },
                "contacts": [{"profile": {"name": "Test User"}, "wa_id": "12345"}],
                "messages": [{
                    "from": "12345",
                    "id": "wamid.00002",
                    "timestamp": "1710000000",
                    "text": {"body": "CNC 2 band ho gayi hai, spindle failure hai. Maintenance ko lagbhag 8 ghante lagenge."},
                    "type": "text"
                }]
            },
            "field": "messages"
        }]
    }]
}

body = json.dumps(payload).encode("utf-8")
signature = hmac.new(secret, body, hashlib.sha256).hexdigest()

headers = {
    "Content-Type": "application/json",
    "X-Hub-Signature-256": f"sha256={signature}"
}

r = requests.post("http://localhost:8000/api/v1/webhooks/whatsapp", data=body, headers=headers)
print(r.status_code, r.text)

import hmac
import hashlib
import json
import urllib.request
import urllib.error

APP_SECRET = '9e9d911208e93bd3fe22c5fdd924cf8d'
PHONE_NUMBER_ID = '8303357161'

payload = json.dumps({
    "object": "whatsapp_business_account",
    "entry": [{
        "id": "1084709697348460",
        "changes": [{
            "value": {
                "messaging_product": "whatsapp",
                "metadata": {
                    "display_phone_number": "1234567890",
                    "phone_number_id": PHONE_NUMBER_ID
                },
                "messages": [{
                    "from": "1234567890",
                    "id": "wamid.test1234",
                    "timestamp": "1234567890",
                    "type": "text",
                    "text": {"body": "Test message"}
                }]
            },
            "field": "messages"
        }]
    }]
}).encode('utf-8')

signature = 'sha256=' + hmac.new(APP_SECRET.encode('utf-8'), payload, hashlib.sha256).hexdigest()

req = urllib.request.Request('https://api.xaiote.com/api/v1/webhooks/whatsapp', data=payload, headers={'Content-Type': 'application/json', 'X-Hub-Signature-256': signature})
try:
    res = urllib.request.urlopen(req)
    print("STATUS:", res.status)
    print("BODY:", res.read().decode('utf-8'))
except urllib.error.HTTPError as e:
    print("ERROR STATUS:", e.code)
    print("ERROR BODY:", e.read().decode('utf-8'))

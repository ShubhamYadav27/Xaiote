import asyncio
import os
import json
import uuid
import sys
from cryptography.fernet import Fernet
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from dotenv import load_dotenv

# Load env but we will override SECRET_ENCRYPTION_KEY
load_dotenv('backend/.env')

aws_secret_string = json.loads('''{"DATABASE_URL": "postgresql+asyncpg://postgres.vyksaiqqwlltlvnlhlnl:Xaiote%2327!Aspect%40S7y%2427@aws-0-ap-south-1.pooler.supabase.com:5432/postgres", "JWT_SECRET": "7q9FjuSXxmCIzkHsmVay05qioFokiBYI+jQiovvmBiXRusHNE0VYCTATLtdt7+tluEZ7gUaSAAtAwKtA4iyVrA==", "JWT_REFRESH_SECRET": "S1wITzvv8g4VqAL59KFqAh/TETFQp0Z+Otjg9pmi+JGtyRDpkkd/wIxmkuEvFyUjLLDtJYCZ7GnDcpTiCdrHsQ==", "SECRET_ENCRYPTION_KEY": "Fbe0NKKhU4cAzYA6T3bZYoNkLGgAeePBDhxWdN/t47A=", "MINIO_ENDPOINT": "https://s3.ap-south-1.amazonaws.com", "MINIO_ACCESS_KEY": "", "MINIO_SECRET_KEY": "", "MINIO_BUCKET": "xaiote-evidence", "WHATSAPP_VERIFY_TOKEN": "XaioteWA_Verify_9f82Kp31_2026", "STT_PROVIDER": "openai"}''')

SECRET_ENCRYPTION_KEY = aws_secret_string["SECRET_ENCRYPTION_KEY"]
DATABASE_URL = aws_secret_string["DATABASE_URL"]
COMPANY_ID = '549e04ae-a2dd-468a-ad7e-8cba949b7294'
WABA_ID = os.getenv('WHATSAPP_BUSINESS_ACCOUNT_ID')
PHONE_NUMBER_ID = os.getenv('WHATSAPP_PHONE_NUMBER_ID')
APP_SECRET = os.getenv('META_APP_SECRET')
ACCESS_TOKEN = os.getenv('WHATSAPP_ACCESS_TOKEN')

if not all([WABA_ID, PHONE_NUMBER_ID, APP_SECRET, ACCESS_TOKEN]):
    print("MISSING CREDENTIALS")
    sys.exit(1)

# Ensure encrypt_secret matches app.core.security
fernet = Fernet(SECRET_ENCRYPTION_KEY.encode())
def encrypt_secret(secret: str) -> str:
    return fernet.encrypt(secret.encode()).decode()

def decrypt_secret(encrypted_secret: str) -> str:
    return fernet.decrypt(encrypted_secret.encode()).decode()

async def main():
    engine = create_async_engine(DATABASE_URL)
    async with engine.connect() as conn:
        # Check company
        res = await conn.execute(text("SELECT id FROM companies WHERE id = :id"), {"id": COMPANY_ID})
        if not res.scalar():
            print("COMPANY_ID_NOT_FOUND")
            return
            
        # Check phone number
        res = await conn.execute(text("SELECT id FROM whatsapp_integrations WHERE phone_number_id = :ph"), {"ph": PHONE_NUMBER_ID})
        if res.scalar():
            print("PHONE_NUMBER_ALREADY_REGISTERED")
            return
            
        app_secret_encrypted = encrypt_secret(APP_SECRET)
        access_token_encrypted = encrypt_secret(ACCESS_TOKEN)
        
        await conn.execute(text('''
            INSERT INTO whatsapp_integrations (
                id, company_id, external_business_account_id, phone_number_id,
                status, app_secret_encrypted, access_token_encrypted, created_at, updated_at
            ) VALUES (
                gen_random_uuid(), :cid, :waba, :ph, 'ACTIVE', :asec, :atoc, NOW(), NOW()
            )
        '''), {
            "cid": COMPANY_ID,
            "waba": WABA_ID,
            "ph": PHONE_NUMBER_ID,
            "asec": app_secret_encrypted,
            "atoc": access_token_encrypted
        })
        await conn.commit()
        
        # Verify
        res = await conn.execute(text("SELECT id, status, app_secret_encrypted, access_token_encrypted FROM whatsapp_integrations WHERE phone_number_id = :ph"), {"ph": PHONE_NUMBER_ID})
        row = res.fetchone()
        if not row:
            print("INSERTION_FAILED")
            return
            
        print("RECORD_INSERTED")
        print(f"Status: {row[1]}")
        
        # Test decryption
        try:
            dec1 = decrypt_secret(row[2])
            dec2 = decrypt_secret(row[3])
            if dec1 == APP_SECRET and dec2 == ACCESS_TOKEN:
                print("DECRYPTION_SUCCESS")
            else:
                print("DECRYPTION_MISMATCH")
        except Exception as e:
            print("DECRYPTION_ERROR")

asyncio.run(main())

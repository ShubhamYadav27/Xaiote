from datetime import datetime, timedelta, timezone

import jwt
from cryptography.fernet import Fernet
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
fernet = Fernet(settings.SECRET_ENCRYPTION_KEY.encode())


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.JWT_ACCESS_EXPIRE_MINUTES
    )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm="HS256")
    return encoded_jwt


def encrypt_secret(secret: str) -> str:
    return fernet.encrypt(secret.encode()).decode()


def decrypt_secret(encrypted_secret: str) -> str:
    return fernet.decrypt(encrypted_secret.encode()).decode()

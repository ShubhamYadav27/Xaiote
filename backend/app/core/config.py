from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "Xaiote Manufacturing Intelligence"
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/xaiote"
    JWT_SECRET: str
    JWT_REFRESH_SECRET: str
    JWT_ACCESS_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_EXPIRE_DAYS: int = 7
    MINIO_ENDPOINT: str
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "xaiote-evidence"
    SECRET_ENCRYPTION_KEY: str

    # Phase 3C: Speech-to-Text Configuration
    STT_PROVIDER: str = "openai"
    STT_MODEL: str = "whisper-1"
    STT_API_KEY: str = "sk-mock-key-for-tests"
    SARVAM_API_KEY: str = ""
    
    # Phase 3B: WhatsApp Configuration
    WHATSAPP_VERIFY_TOKEN: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()  # type: ignore

from pydantic_settings import BaseSettings, SettingsConfigDict

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

    STT_PROVIDER: str = "openai"
    STT_MODEL: str = "whisper-1"
    STT_API_KEY: str = "sk-mock-key-for-tests"
    SARVAM_API_KEY: str = ""
    
    WHATSAPP_VERIFY_TOKEN: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()

import os

dirs = [
    "backend/app",
    "backend/app/api",
    "backend/app/api/routes",
    "backend/app/api/dependencies",
    "backend/app/core",
    "backend/app/domain",
    "backend/app/domain/entities",
    "backend/app/domain/enums",
    "backend/app/models",
    "backend/app/schemas",
    "backend/app/repositories",
    "backend/app/services",
    "backend/app/infrastructure",
    "backend/app/infrastructure/database",
    "backend/app/infrastructure/storage",
    "backend/app/infrastructure/ai",
    "backend/app/middleware",
    "backend/app/exceptions",
    "backend/tests",
]

for d in dirs:
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "__init__.py"), "w") as f:
        pass

files = {
    "backend/requirements.txt": """fastapi==0.111.0
uvicorn==0.30.1
sqlalchemy==2.0.30
asyncpg==0.29.0
alembic==1.13.1
pydantic==2.7.4
pydantic-settings==2.3.4
pyjwt==2.8.0
passlib==1.7.4
argon2-cffi==23.1.0
pytest==8.2.2
pytest-asyncio==0.23.7
httpx==0.27.0
python-multipart==0.0.9
boto3==1.34.129
""",
    "backend/app/core/config.py": """from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Xaiote Manufacturing Intelligence"
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/xaiote"
    JWT_SECRET: str = "supersecret"
    JWT_REFRESH_SECRET: str = "supersecretrefresh"
    JWT_ACCESS_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_EXPIRE_DAYS: int = 7
    MINIO_ENDPOINT: str = "http://localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "xaiote-evidence"
    
    class Config:
        env_file = ".env"

settings = Settings()
""",
    "backend/app/infrastructure/database/session.py": """from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
""",
}

for path, content in files.items():
    with open(path, "w") as f:
        f.write(content)

print("Backend structure created.")

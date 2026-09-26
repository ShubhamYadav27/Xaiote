import os
import shutil

# Scaffolding all remaining backend files
files = {
    "backend/Dockerfile": """FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
""",
    "backend/alembic.ini": """[alembic]
script_location = alembic
prepend_sys_path = .
version_path_separator = os
sqlalchemy.url = postgresql+asyncpg://user:password@localhost:5432/xaiote
[post_write_hooks]
[loggers]
keys = root,sqlalchemy,alembic
[handlers]
keys = console
[formatters]
keys = generic
[logger_root]
level = WARN
handlers = console
qualname =
[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine
[logger_alembic]
level = INFO
handlers =
qualname = alembic
[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic
[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
""",
    "backend/alembic/env.py": """import asyncio
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

from app.infrastructure.database.session import Base
from app.core.config import settings

# Import all models to ensure they are registered with Base.metadata
import app.models

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    url = settings.DATABASE_URL
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()

async def run_async_migrations() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = settings.DATABASE_URL
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()

def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
""",
    "backend/app/main.py": """from fastapi import FastAPI, Depends, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import auth, company, plants, health

app = FastAPI(title="Xaiote API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "INTERNAL_SERVER_ERROR", "message": "An unexpected error occurred."}}
    )

app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(company.router, prefix="/api/company", tags=["company"])
app.include_router(plants.router, prefix="/api/plants", tags=["plants"])
""",
    "backend/app/api/routes/health.py": """from fastapi import APIRouter

router = APIRouter()

@router.get("")
async def health():
    return {"status": "ok"}

@router.get("/live")
async def live():
    return {"status": "alive"}

@router.get("/ready")
async def ready():
    # In a real app, check DB and storage here
    return {"status": "ready"}
""",
    "backend/app/core/security.py": """from passlib.context import CryptContext
import jwt
from datetime import datetime, timedelta
from app.core.config import settings

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm="HS256")
    return encoded_jwt
""",
    "backend/app/schemas/auth.py": """from pydantic import BaseModel, EmailStr

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    company_name: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class RefreshRequest(BaseModel):
    refresh_token: str
""",
    "backend/app/api/dependencies/auth.py": """from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.config import settings
from app.infrastructure.database.session import get_db
from app.models.user import User
from app.models.company import Company

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: AsyncSession = Depends(get_db)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user

async def get_current_company(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Company).where(Company.id == current_user.company_id))
    company = result.scalars().first()
    if company is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Company not found")
    return company
""",
    "backend/app/api/routes/auth.py": """from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import uuid
import datetime

from app.infrastructure.database.session import get_db
from app.schemas.auth import UserRegister, UserLogin, TokenResponse, RefreshRequest
from app.models.user import User
from app.models.company import Company
from app.models.refresh_token import RefreshToken
from app.core.security import get_password_hash, verify_password, create_access_token
from app.api.dependencies.auth import get_current_user

router = APIRouter()

@router.post("/register")
async def register(user_in: UserRegister, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == user_in.email))
    if result.scalars().first():
        return {"error": {"code": "EMAIL_EXISTS", "message": "Email already registered"}}
        
    company = Company(name=user_in.company_name)
    db.add(company)
    await db.flush()
    
    user = User(
        email=user_in.email,
        password_hash=get_password_hash(user_in.password),
        full_name=user_in.full_name,
        company_id=company.id,
        role="OWNER"
    )
    db.add(user)
    await db.commit()
    return {"data": {"message": "User and company created successfully"}}

@router.post("/login")
async def login(user_in: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == user_in.email))
    user = result.scalars().first()
    if not user or not verify_password(user_in.password, user.password_hash):
        return {"error": {"code": "INVALID_CREDENTIALS", "message": "Incorrect email or password"}}
        
    access_token = create_access_token({"sub": str(user.id), "company_id": str(user.company_id)})
    refresh_token = str(uuid.uuid4())
    
    rt_record = RefreshToken(
        user_id=user.id,
        token=refresh_token,
        expires_at=datetime.datetime.utcnow() + datetime.timedelta(days=7)
    )
    db.add(rt_record)
    await db.commit()
    
    return {"data": {"access_token": access_token, "refresh_token": refresh_token}}

@router.post("/refresh")
async def refresh(req: RefreshRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RefreshToken).where(RefreshToken.token == req.refresh_token))
    rt_record = result.scalars().first()
    
    if not rt_record or rt_record.expires_at < datetime.datetime.utcnow():
        return {"error": {"code": "INVALID_TOKEN", "message": "Refresh token is invalid or expired"}}
        
    result_user = await db.execute(select(User).where(User.id == rt_record.user_id))
    user = result_user.scalars().first()
    
    if not user:
        return {"error": {"code": "USER_NOT_FOUND", "message": "User no longer exists"}}
        
    access_token = create_access_token({"sub": str(user.id), "company_id": str(user.company_id)})
    new_refresh_token = str(uuid.uuid4())
    
    rt_record.token = new_refresh_token
    rt_record.expires_at = datetime.datetime.utcnow() + datetime.timedelta(days=7)
    await db.commit()
    
    return {"data": {"access_token": access_token, "refresh_token": new_refresh_token}}

@router.post("/logout")
async def logout(req: RefreshRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RefreshToken).where(RefreshToken.token == req.refresh_token))
    rt_record = result.scalars().first()
    if rt_record:
        await db.delete(rt_record)
        await db.commit()
    return {"data": {"message": "Logged out"}}

@router.get("/me")
async def read_users_me(current_user: User = Depends(get_current_user)):
    return {"data": {"email": current_user.email, "full_name": current_user.full_name, "company_id": current_user.company_id}}
""",
    "backend/app/schemas/plant.py": """from pydantic import BaseModel

class PlantCreate(BaseModel):
    name: str
    code: str
    address: str | None = None
    timezone: str | None = None
""",
    "backend/app/api/routes/company.py": """from fastapi import APIRouter, Depends
from app.models.company import Company
from app.api.dependencies.auth import get_current_company

router = APIRouter()

@router.get("")
async def get_company(current_company: Company = Depends(get_current_company)):
    return {"data": {"id": current_company.id, "name": current_company.name}}
""",
    "backend/app/api/routes/plants.py": """from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.infrastructure.database.session import get_db
from app.models.plant import Plant
from app.models.company import Company
from app.schemas.plant import PlantCreate
from app.api.dependencies.auth import get_current_company

router = APIRouter()

@router.post("")
async def create_plant(plant_in: PlantCreate, current_company: Company = Depends(get_current_company), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Plant).where(Plant.company_id == current_company.id, Plant.code == plant_in.code))
    if result.scalars().first():
        return {"error": {"code": "PLANT_EXISTS", "message": "Plant code already exists in this company"}}
        
    plant = Plant(
        company_id=current_company.id,
        name=plant_in.name,
        code=plant_in.code,
        address=plant_in.address,
        timezone=plant_in.timezone
    )
    db.add(plant)
    await db.commit()
    await db.refresh(plant)
    return {"data": {"id": plant.id, "name": plant.name, "code": plant.code}}

@router.get("")
async def list_plants(current_company: Company = Depends(get_current_company), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Plant).where(Plant.company_id == current_company.id))
    plants = result.scalars().all()
    return {"data": [{"id": p.id, "name": p.name, "code": p.code} for p in plants]}

@router.get("/{plant_id}")
async def get_plant(plant_id: str, current_company: Company = Depends(get_current_company), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Plant).where(Plant.id == plant_id, Plant.company_id == current_company.id))
    plant = result.scalars().first()
    if not plant:
        return {"error": {"code": "NOT_FOUND", "message": "Plant not found"}}
    return {"data": {"id": plant.id, "name": plant.name, "code": plant.code}}
""",
    "backend/tests/test_auth.py": """import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_register_and_login():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Register
        response = await ac.post("/api/auth/register", json={
            "email": "test@example.com",
            "password": "password123",
            "full_name": "Test User",
            "company_name": "Test Corp"
        })
        assert response.status_code == 200
        assert "data" in response.json()
        
        # Login
        response = await ac.post("/api/auth/login", json={
            "email": "test@example.com",
            "password": "password123"
        })
        assert response.status_code == 200
        data = response.json().get("data", {})
        assert "access_token" in data
        assert "refresh_token" in data
        
        # Get Me
        token = data["access_token"]
        response = await ac.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        me_data = response.json().get("data", {})
        assert me_data["email"] == "test@example.com"
        
        # Logout
        refresh_token = data["refresh_token"]
        response = await ac.post("/api/auth/logout", json={"refresh_token": refresh_token})
        assert response.status_code == 200
        
        # Refresh should fail now
        response = await ac.post("/api/auth/refresh", json={"refresh_token": refresh_token})
        assert response.json().get("error") is not None
""",
    "backend/conftest.py": """import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.infrastructure.database.session import Base, get_db
from app.main import app

# Use in-memory SQLite for testing to avoid dependencies on external DB during simple unit tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="session", autouse=True)
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(autouse=True)
async def prepare_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
"""
}

os.makedirs("backend/alembic", exist_ok=True)
for path, content in files.items():
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)

print("Backend files generated successfully.")

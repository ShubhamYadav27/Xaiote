import os

# 1. Update models to use token_hash
model_refresh_token = """from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
import uuid
import datetime
from app.infrastructure.database.session import Base

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String, nullable=False, unique=True, index=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    user = relationship("User", back_populates="refresh_tokens")
"""

# 2. Update auth routes to hash refresh tokens
auth_routes = """from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import uuid
import datetime
import hashlib

from app.infrastructure.database.session import get_db
from app.schemas.auth import UserRegister, UserLogin, TokenResponse, RefreshRequest
from app.models.user import User
from app.models.company import Company
from app.models.refresh_token import RefreshToken
from app.core.security import get_password_hash, verify_password, create_access_token
from app.api.dependencies.auth import get_current_user

router = APIRouter()

def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

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
    raw_refresh_token = str(uuid.uuid4())
    
    rt_record = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(raw_refresh_token),
        expires_at=datetime.datetime.utcnow() + datetime.timedelta(days=7)
    )
    db.add(rt_record)
    await db.commit()
    
    return {"data": {"access_token": access_token, "refresh_token": raw_refresh_token}}

@router.post("/refresh")
async def refresh(req: RefreshRequest, db: AsyncSession = Depends(get_db)):
    hashed_rt = hash_token(req.refresh_token)
    result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == hashed_rt))
    rt_record = result.scalars().first()
    
    if not rt_record or rt_record.expires_at < datetime.datetime.utcnow():
        return {"error": {"code": "INVALID_TOKEN", "message": "Refresh token is invalid or expired"}}
        
    result_user = await db.execute(select(User).where(User.id == rt_record.user_id))
    user = result_user.scalars().first()
    
    if not user:
        return {"error": {"code": "USER_NOT_FOUND", "message": "User no longer exists"}}
        
    # Revoke old token by deleting it (rotation)
    await db.delete(rt_record)
    
    access_token = create_access_token({"sub": str(user.id), "company_id": str(user.company_id)})
    new_raw_refresh_token = str(uuid.uuid4())
    
    new_rt_record = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(new_raw_refresh_token),
        expires_at=datetime.datetime.utcnow() + datetime.timedelta(days=7)
    )
    db.add(new_rt_record)
    await db.commit()
    
    return {"data": {"access_token": access_token, "refresh_token": new_raw_refresh_token}}

@router.post("/logout")
async def logout(req: RefreshRequest, db: AsyncSession = Depends(get_db)):
    hashed_rt = hash_token(req.refresh_token)
    result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == hashed_rt))
    rt_record = result.scalars().first()
    if rt_record:
        await db.delete(rt_record)
        await db.commit()
    return {"data": {"message": "Logged out"}}

@router.get("/me")
async def read_users_me(current_user: User = Depends(get_current_user)):
    return {"data": {"email": current_user.email, "full_name": current_user.full_name, "company_id": current_user.company_id}}
"""

# 3. Update conftest.py
conftest = """import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.infrastructure.database.session import Base, get_db
from app.main import app

# IMPORT ALL MODELS to register with Base
from app.models.company import Company
from app.models.plant import Plant
from app.models.user import User
from app.models.refresh_token import RefreshToken

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="session")
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

# 4. Auth and Tenant isolation tests
test_auth = """import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_auth_lifecycle():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Register
        res = await ac.post("/api/auth/register", json={
            "email": "test@test.com", "password": "pass", "full_name": "Test", "company_name": "C1"
        })
        assert res.status_code == 200, res.json()
        assert "data" in res.json()
        
        # Duplicate register
        res2 = await ac.post("/api/auth/register", json={
            "email": "test@test.com", "password": "pass", "full_name": "Test", "company_name": "C1"
        })
        assert "error" in res2.json()
        
        # Login
        res_login = await ac.post("/api/auth/login", json={"email": "test@test.com", "password": "pass"})
        data = res_login.json()["data"]
        access_token = data["access_token"]
        refresh_token = data["refresh_token"]
        
        # Get Me
        res_me = await ac.get("/api/auth/me", headers={"Authorization": f"Bearer {access_token}"})
        assert res_me.json()["data"]["email"] == "test@test.com"
        
        # Refresh
        res_ref = await ac.post("/api/auth/refresh", json={"refresh_token": refresh_token})
        new_data = res_ref.json()["data"]
        new_access = new_data["access_token"]
        new_refresh = new_data["refresh_token"]
        
        # Old refresh token should fail (revoked/rotated)
        res_ref_old = await ac.post("/api/auth/refresh", json={"refresh_token": refresh_token})
        assert "error" in res_ref_old.json()
        
        # Logout
        res_logout = await ac.post("/api/auth/logout", json={"refresh_token": new_refresh})
        assert res_logout.status_code == 200
        
        # Refresh after logout should fail
        res_ref_logout = await ac.post("/api/auth/refresh", json={"refresh_token": new_refresh})
        assert "error" in res_ref_logout.json()

@pytest.mark.asyncio
async def test_tenant_isolation():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Setup Company A
        await ac.post("/api/auth/register", json={"email": "a@a.com", "password": "p", "full_name": "A", "company_name": "CA"})
        login_a = await ac.post("/api/auth/login", json={"email": "a@a.com", "password": "p"})
        token_a = login_a.json()["data"]["access_token"]
        
        # Setup Company B
        await ac.post("/api/auth/register", json={"email": "b@b.com", "password": "p", "full_name": "B", "company_name": "CB"})
        login_b = await ac.post("/api/auth/login", json={"email": "b@b.com", "password": "p"})
        token_b = login_b.json()["data"]["access_token"]
        
        # Company A creates Plant A
        plant_a_res = await ac.post("/api/plants", json={"name": "Plant A", "code": "PA"}, headers={"Authorization": f"Bearer {token_a}"})
        plant_a_id = plant_a_res.json()["data"]["id"]
        
        # Company B creates Plant B
        plant_b_res = await ac.post("/api/plants", json={"name": "Plant B", "code": "PB"}, headers={"Authorization": f"Bearer {token_b}"})
        plant_b_id = plant_b_res.json()["data"]["id"]
        
        # Company A accesses Plant A (PASS)
        assert (await ac.get(f"/api/plants/{plant_a_id}", headers={"Authorization": f"Bearer {token_a}"})).status_code == 200
        
        # Company B accesses Plant B (PASS)
        assert (await ac.get(f"/api/plants/{plant_b_id}", headers={"Authorization": f"Bearer {token_b}"})).status_code == 200
        
        # Company A accesses Plant B (DENIED)
        res_denied_1 = await ac.get(f"/api/plants/{plant_b_id}", headers={"Authorization": f"Bearer {token_a}"})
        assert "error" in res_denied_1.json()
        
        # Company B accesses Plant A (DENIED)
        res_denied_2 = await ac.get(f"/api/plants/{plant_a_id}", headers={"Authorization": f"Bearer {token_b}"})
        assert "error" in res_denied_2.json()
"""

import sys
with open("backend/app/models/refresh_token.py", "w") as f: f.write(model_refresh_token)
with open("backend/app/api/routes/auth.py", "w") as f: f.write(auth_routes)
with open("backend/conftest.py", "w") as f: f.write(conftest)
with open("backend/tests/test_auth.py", "w") as f: f.write(test_auth)
print("Files rewritten successfully.")

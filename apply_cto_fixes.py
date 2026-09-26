import os
import re

# 1. Update Company Model
company_model = """import datetime
import uuid

from sqlalchemy import Column, DateTime, String
from sqlalchemy.orm import relationship

from app.infrastructure.database.session import Base

class Company(Base):
    __tablename__ = "companies"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    industry = Column(String, nullable=True)
    revenue_range = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc), onupdate=lambda: datetime.datetime.now(datetime.timezone.utc))
    
    users = relationship("User", back_populates="company")
    plants = relationship("Plant", back_populates="company")
"""
with open("backend/app/models/company.py", "w") as f: f.write(company_model)

# 2. Update Plant Model
plant_model = """import datetime
import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.infrastructure.database.session import Base

class Plant(Base):
    __tablename__ = "plants"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    name = Column(String, nullable=False)
    location = Column(String, nullable=True)
    timezone = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc), onupdate=lambda: datetime.datetime.now(datetime.timezone.utc))
    
    company = relationship("Company", back_populates="plants")
"""
with open("backend/app/models/plant.py", "w") as f: f.write(plant_model)

# 3. Update User Model
user_model = """import datetime
import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship

from app.infrastructure.database.session import Base

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc), onupdate=lambda: datetime.datetime.now(datetime.timezone.utc))
    
    company = relationship("Company", back_populates="users")
    refresh_tokens = relationship("RefreshToken", back_populates="user")
"""
with open("backend/app/models/user.py", "w") as f: f.write(user_model)

# 4. Update RefreshToken Model
rt_model = """import datetime
import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship

from app.infrastructure.database.session import Base

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String, nullable=False, unique=True, index=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    
    user = relationship("User", back_populates="refresh_tokens")
"""
with open("backend/app/models/refresh_token.py", "w") as f: f.write(rt_model)

# 5. Fix Models __init__.py F401
models_init = """from .company import Company
from .plant import Plant
from .refresh_token import RefreshToken
from .user import User

__all__ = ["Company", "Plant", "RefreshToken", "User"]
"""
with open("backend/app/models/__init__.py", "w") as f: f.write(models_init)

# 6. Fix schemas/plant.py
schemas_plant = """from pydantic import BaseModel

class PlantCreate(BaseModel):
    name: str
    location: str | None = None
    timezone: str | None = None

class PlantResponse(BaseModel):
    id: str
    company_id: str
    name: str
    location: str | None = None
    timezone: str | None = None
"""
with open("backend/app/schemas/plant.py", "w") as f: f.write(schemas_plant)

# 7. Fix schemas/auth.py
schemas_auth = """from pydantic import BaseModel, EmailStr

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    company_name: str
    industry: str | None = None
    revenue_range: str | None = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str

class RefreshRequest(BaseModel):
    refresh_token: str
"""
with open("backend/app/schemas/auth.py", "w") as f: f.write(schemas_auth)

# 8. Fix app/api/routes/auth.py utcnow and registration params
with open("backend/app/api/routes/auth.py", "r") as f:
    auth_code = f.read()

auth_code = auth_code.replace("company = Company(name=user_in.company_name)", "company = Company(name=user_in.company_name, industry=user_in.industry, revenue_range=user_in.revenue_range)")
auth_code = auth_code.replace("datetime.datetime.utcnow()", "datetime.datetime.now(datetime.timezone.utc)")
with open("backend/app/api/routes/auth.py", "w") as f: f.write(auth_code)

# 9. Fix app/core/security.py utcnow
with open("backend/app/core/security.py", "r") as f:
    sec_code = f.read()
sec_code = sec_code.replace("from datetime import datetime, timedelta", "from datetime import datetime, timedelta, timezone")
sec_code = sec_code.replace("datetime.utcnow()", "datetime.now(timezone.utc)")
with open("backend/app/core/security.py", "w") as f: f.write(sec_code)

# 10. Fix app/api/routes/plants.py to not use code
with open("backend/app/api/routes/plants.py", "r") as f:
    plants_code = f.read()
plants_code = plants_code.replace("plant = Plant(company_id=current_company.id, name=plant_in.name, code=plant_in.code)", "plant = Plant(company_id=current_company.id, name=plant_in.name, location=plant_in.location, timezone=plant_in.timezone)")
with open("backend/app/api/routes/plants.py", "w") as f: f.write(plants_code)

# 11. Fix tests/test_auth.py
test_auth = """import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

@pytest.mark.asyncio
async def test_auth_lifecycle():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/api/auth/register", json={
            "email": "test@test.com", "password": "pass", "full_name": "Test", "company_name": "C1", "industry": "Auto", "revenue_range": "50Cr-100Cr"
        })
        assert res.status_code == 200, res.json()
        
        res_login = await ac.post("/api/auth/login", json={"email": "test@test.com", "password": "pass"})
        data = res_login.json()["data"]
        access_token = data["access_token"]
        refresh_token = data["refresh_token"]
        
        res_me = await ac.get("/api/auth/me", headers={"Authorization": f"Bearer {access_token}"})
        assert res_me.json()["data"]["email"] == "test@test.com"
        
        res_ref = await ac.post("/api/auth/refresh", json={"refresh_token": refresh_token})
        new_data = res_ref.json()["data"]
        new_access = new_data["access_token"]
        new_refresh = new_data["refresh_token"]
        
        # USE the new_access token to fix F841 and verify it works
        res_me2 = await ac.get("/api/auth/me", headers={"Authorization": f"Bearer {new_access}"})
        assert res_me2.json()["data"]["email"] == "test@test.com"
        
        res_ref_old = await ac.post("/api/auth/refresh", json={"refresh_token": refresh_token})
        assert "error" in res_ref_old.json()
        
        res_logout = await ac.post("/api/auth/logout", json={"refresh_token": new_refresh})
        assert res_logout.status_code == 200
        
        res_ref_logout = await ac.post("/api/auth/refresh", json={"refresh_token": new_refresh})
        assert "error" in res_ref_logout.json()

@pytest.mark.asyncio
async def test_tenant_isolation():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.post("/api/auth/register", json={"email": "a@a.com", "password": "p", "full_name": "A", "company_name": "CA"})
        login_a = await ac.post("/api/auth/login", json={"email": "a@a.com", "password": "p"})
        token_a = login_a.json()["data"]["access_token"]
        
        await ac.post("/api/auth/register", json={"email": "b@b.com", "password": "p", "full_name": "B", "company_name": "CB"})
        login_b = await ac.post("/api/auth/login", json={"email": "b@b.com", "password": "p"})
        token_b = login_b.json()["data"]["access_token"]
        
        plant_a_res = await ac.post("/api/plants", json={"name": "Plant A", "location": "L1"}, headers={"Authorization": f"Bearer {token_a}"})
        plant_a_id = plant_a_res.json()["data"]["id"]
        
        plant_b_res = await ac.post("/api/plants", json={"name": "Plant B", "location": "L2"}, headers={"Authorization": f"Bearer {token_b}"})
        plant_b_id = plant_b_res.json()["data"]["id"]
        
        assert (await ac.get(f"/api/plants/{plant_a_id}", headers={"Authorization": f"Bearer {token_a}"})).status_code == 200
        assert (await ac.get(f"/api/plants/{plant_b_id}", headers={"Authorization": f"Bearer {token_b}"})).status_code == 200
        
        res_denied_1 = await ac.get(f"/api/plants/{plant_b_id}", headers={"Authorization": f"Bearer {token_a}"})
        assert "error" in res_denied_1.json()
        
        res_denied_2 = await ac.get(f"/api/plants/{plant_a_id}", headers={"Authorization": f"Bearer {token_b}"})
        assert "error" in res_denied_2.json()
"""
with open("backend/tests/test_auth.py", "w") as f: f.write(test_auth)

# 12. Fix B008 globally in ruff
pyproject = """[tool.ruff]
line-length = 120

[tool.ruff.lint]
ignore = ["B008"]
"""
with open("backend/pyproject.toml", "w") as f: f.write(pyproject)

print("Files updated successfully")

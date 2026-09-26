import os

files = {
    "backend/app/models/__init__.py": """from .company import Company
from .plant import Plant
from .user import User
from .refresh_token import RefreshToken
""",
    "backend/app/models/company.py": """from sqlalchemy import Column, String, DateTime
from sqlalchemy.orm import relationship
import uuid
import datetime
from app.infrastructure.database.session import Base

class Company(Base):
    __tablename__ = "companies"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    legal_name = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    timezone = Column(String, default="UTC")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    plants = relationship("Plant", back_populates="company")
    users = relationship("User", back_populates="company")
""",
    "backend/app/models/plant.py": """from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
import uuid
import datetime
from app.infrastructure.database.session import Base

class Plant(Base):
    __tablename__ = "plants"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String, ForeignKey("companies.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    code = Column(String, nullable=False, index=True)
    address = Column(String, nullable=True)
    timezone = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    company = relationship("Company", back_populates="plants")
    
    __table_args__ = (
        UniqueConstraint("company_id", "code", name="uq_company_plant_code"),
    )
""",
    "backend/app/models/user.py": """from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
import uuid
import datetime
from app.infrastructure.database.session import Base

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String, ForeignKey("companies.id"), nullable=False, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(String, nullable=False, default="VIEWER")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    company = relationship("Company", back_populates="users")
    refresh_tokens = relationship("RefreshToken", back_populates="user")
""",
    "backend/app/models/refresh_token.py": """from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
import uuid
import datetime
from app.infrastructure.database.session import Base

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    token = Column(String, nullable=False, unique=True, index=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    user = relationship("User", back_populates="refresh_tokens")
"""
}

for path, content in files.items():
    with open(path, "w") as f:
        f.write(content)

print("Models created.")

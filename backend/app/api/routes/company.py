from fastapi import APIRouter, Depends

from app.api.dependencies.auth import get_current_company
from app.models.company import Company

router = APIRouter()


@router.get("")
async def get_company(current_company: Company = Depends(get_current_company)):
    return {"data": {"id": current_company.id, "name": current_company.name}}


from fastapi import Depends
from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from app.infrastructure.database.session import Base, get_db


class PilotLead(Base):
    __tablename__ = "pilot_leads"
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    company_name = Column(String, nullable=False)
    team_size = Column(String)
    role = Column(String)
    primary_challenge = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


from pydantic import BaseModel


class PilotRequest(BaseModel):
    full_name: str
    email: str
    company_name: str
    team_size: str | None = None
    role: str | None = None
    primary_challenge: str | None = None


@router.post("/pilot")
async def request_pilot(pilot_in: PilotRequest, db: AsyncSession = Depends(get_db)):
    db_lead = PilotLead(
        full_name=pilot_in.full_name,
        email=pilot_in.email,
        company_name=pilot_in.company_name,
        team_size=pilot_in.team_size,
        role=pilot_in.role,
        primary_challenge=pilot_in.primary_challenge,
    )
    db.add(db_lead)
    await db.commit()
    await db.refresh(db_lead)
    return {"data": {"message": "Pilot request received", "id": db_lead.id}}

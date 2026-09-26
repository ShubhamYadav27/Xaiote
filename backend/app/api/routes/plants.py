from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.dependencies.auth import get_current_company
from app.infrastructure.database.session import get_db
from app.models.company import Company
from app.models.plant import Plant
from app.schemas.plant import PlantCreate

router = APIRouter()


@router.post("")
async def create_plant(
    plant_in: PlantCreate,
    current_company: Company = Depends(get_current_company),
    db: AsyncSession = Depends(get_db),
):
    plant = Plant(
        company_id=current_company.id,
        name=plant_in.name,
        location=plant_in.location,
        timezone=plant_in.timezone,
    )
    db.add(plant)
    await db.commit()
    await db.refresh(plant)
    return {
        "data": {
            "id": plant.id,
            "company_id": plant.company_id,
            "name": plant.name,
            "location": plant.location,
            "timezone": plant.timezone,
        }
    }


@router.get("")
async def list_plants(
    current_company: Company = Depends(get_current_company),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Plant).where(Plant.company_id == current_company.id)
    )
    plants = result.scalars().all()
    return {
        "data": [
            {
                "id": p.id,
                "company_id": p.company_id,
                "name": p.name,
                "location": p.location,
                "timezone": p.timezone,
            }
            for p in plants
        ]
    }


@router.get("/{plant_id}")
async def get_plant(
    plant_id: str,
    current_company: Company = Depends(get_current_company),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Plant).where(
            Plant.id == plant_id, Plant.company_id == current_company.id
        )
    )
    plant = result.scalars().first()
    if not plant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plant not found or access denied",
        )
    return {
        "data": {
            "id": plant.id,
            "company_id": plant.company_id,
            "name": plant.name,
            "location": plant.location,
            "timezone": plant.timezone,
        }
    }

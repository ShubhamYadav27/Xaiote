from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.dependencies.auth import get_current_company
from app.infrastructure.database.session import get_db
from app.models.company import Company
from app.models.masters import Machine
from app.models.plant import Plant
from app.schemas.masters import MachineCreate, MachineResponse

router = APIRouter()


@router.post("")
async def create_machine(
    machine_in: MachineCreate,
    current_company: Company = Depends(get_current_company),
    db: AsyncSession = Depends(get_db),
):
    # Verify plant_id belongs to company
    plant_check = await db.execute(
        select(Plant).where(
            Plant.id == machine_in.plant_id, Plant.company_id == current_company.id
        )
    )
    if not plant_check.scalars().first():
        raise HTTPException(status_code=404, detail="Plant not found")

    if machine_in.external_id:
        existing = await db.execute(
            select(Machine).where(
                Machine.company_id == current_company.id,
                Machine.plant_id == machine_in.plant_id,
                Machine.external_id == machine_in.external_id,
            )
        )
        if existing.scalars().first():
            raise HTTPException(
                status_code=400,
                detail="Machine with this external_id already exists in this plant",
            )

    machine = Machine(
        company_id=current_company.id,
        plant_id=machine_in.plant_id,
        name=machine_in.name,
        category=machine_in.category,
        external_id=machine_in.external_id,
    )
    db.add(machine)
    await db.commit()
    await db.refresh(machine)

    return {"data": MachineResponse.model_validate(machine)}


@router.get("")
async def list_machines(
    plant_id: str | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_company: Company = Depends(get_current_company),
    db: AsyncSession = Depends(get_db),
):
    base_query = select(Machine).where(Machine.company_id == current_company.id)
    if plant_id:
        base_query = base_query.where(Machine.plant_id == plant_id)

    count_query = select(func.count()).select_from(base_query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = base_query.order_by(Machine.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    machines = result.scalars().all()

    return {
        "data": {
            "items": [MachineResponse.model_validate(m) for m in machines],
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    }

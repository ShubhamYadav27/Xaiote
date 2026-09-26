from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.dependencies.auth import get_current_company
from app.infrastructure.database.session import get_db
from app.models.company import Company
from app.models.masters import Vendor
from app.schemas.masters import VendorCreate, VendorResponse

router = APIRouter()


@router.post("")
async def create_vendor(
    vendor_in: VendorCreate,
    current_company: Company = Depends(get_current_company),
    db: AsyncSession = Depends(get_db),
):
    if vendor_in.external_id:
        existing = await db.execute(
            select(Vendor).where(
                Vendor.company_id == current_company.id,
                Vendor.external_id == vendor_in.external_id,
            )
        )
        if existing.scalars().first():
            raise HTTPException(
                status_code=400, detail="Vendor with this external_id already exists"
            )

    vendor = Vendor(
        company_id=current_company.id,
        name=vendor_in.name,
        external_id=vendor_in.external_id,
    )
    db.add(vendor)
    await db.commit()
    await db.refresh(vendor)

    return {"data": VendorResponse.model_validate(vendor)}


@router.get("")
async def list_vendors(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_company: Company = Depends(get_current_company),
    db: AsyncSession = Depends(get_db),
):
    base_query = select(Vendor).where(Vendor.company_id == current_company.id)
    count_query = select(func.count()).select_from(base_query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = base_query.order_by(Vendor.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    vendors = result.scalars().all()

    return {
        "data": {
            "items": [VendorResponse.model_validate(v) for v in vendors],
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    }
